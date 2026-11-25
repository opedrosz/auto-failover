#!/usr/bin/env python3
"""
Supervisor Independente - AUTO FAILOVER V1.0.4

Processo supervisor separado da sessao de IA que executa a tarefa.
Permanece capaz de detectar interrupcao, recuperar checkpoint e reiniciar
a execucao com outro modelo mesmo que a sessao do OpenCode tenha perdido cota
ou sido encerrada.

Compativel com Windows: usa subprocess.Popen para processos filhos.
Nao depende do modelo ativo para decidir a troca (logica deterministica).
"""

import json
import logging
import os
import re
import tempfile
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger('AutoFailover.Supervisor')

class Supervisor:
    """Supervisor de processos para continuidade multiagente."""

    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE',
                           r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover'))
        self.state_file = self.base_dir / 'data' / 'supervisor_state.json'
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.child_process = None
        self.state = self._carregar_estado()

    def _carregar_estado(self):
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding='utf-8'))
            except (ValueError, OSError) as error:
                raise RuntimeError("Estado do supervisor indisponivel; reconciliacao necessaria") from error
        return {"tarefas": {}, "historico": []}

    def _salvar_estado(self):
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self.state_file.parent, delete=False
        ) as stream:
            temp_path = Path(stream.name)
            try:
                json.dump(self.state, stream, ensure_ascii=False, indent=2)
                stream.close()
                temp_path.replace(self.state_file)
            finally:
                stream.close()
                temp_path.unlink(missing_ok=True)

    def iniciar_processo(self, cmd, task_id, cwd=None, *, registrar_comando=True):
        """Iniciar um processo filho controlado (opencode run)."""
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(
            cmd, cwd=cwd or str(self.base_dir),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, creationflags=creationflags,
        )
        self.child_process = proc
        self.state['tarefas'][task_id] = {
            'pid': proc.pid,
            'iniciado_em': datetime.now(timezone.utc).isoformat(),
            'status': 'em_andamento',
        }
        if registrar_comando:
            self.state['tarefas'][task_id]['cmd'] = cmd
        self._salvar_estado()
        logger.info(f"Processo filho iniciado para {task_id} (PID {proc.pid})")
        return proc

    def verificar_processo(self, task_id, timeout=0):
        """Verificar se o processo filho terminou e capturar saida."""
        info = self.state['tarefas'].get(task_id, {})
        proc = self.child_process
        if proc is None:
            return {"status": "sem_processo", "task_id": task_id}
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            code = proc.returncode
            status = 'concluido' if code == 0 else 'falhou'
            self.state['tarefas'][task_id].update({
                'status': status, 'returncode': code,
                'stdout': stdout[-4000:], 'stderr': stderr[-2000:],
                'finalizado_em': datetime.now(timezone.utc).isoformat(),
            })
            self._salvar_estado()
            return {
                "status": status, "returncode": code,
                "stdout": stdout, "stderr": stderr,
                "task_id": task_id
            }
        except subprocess.TimeoutExpired:
            return {"status": "em_andamento", "task_id": task_id}

    def encerrar_processo(self, task_id, force=False):
        """Encerrar o processo filho controlado."""
        proc = self.child_process
        if proc is None or proc.poll() is not None:
            return {"encerrado": True, "motivo": "processo_ja_finalizado"}
        try:
            if sys.platform == 'win32' and not force:
                proc.terminate()
            else:
                proc.kill()
            proc.communicate(timeout=10)
            self.state['tarefas'][task_id]['status'] = 'interrompido'
            self._salvar_estado()
            return {"encerrado": True, "motivo": "terminate" if not force else "kill"}
        except Exception as e:
            return {"encerrado": False, "erro": str(e)}

    def supervisionar(self, task_id, cmd, cwd=None, timeout=120):
        """Ciclo completo: iniciar -> aguardar -> detectar -> registrar."""
        self.iniciar_processo(cmd, task_id, cwd)
        resultado = self.verificar_processo_seguro(task_id, timeout)
        return resultado

    def verificar_processo_seguro(self, task_id, timeout):
        """Wrapper com tratamento de timeout."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = self.verificar_processo(task_id, timeout=5)
            if r['status'] != 'em_andamento':
                return r
        return {"status": "timeout", "task_id": task_id,
                "motivo": "tempo_limite_supervisao_excedido"}

    def supervisionar_failover(self, task_id, selector, comando, validar, *, cwd,
                               requisitos=None, timeout=120, max_tentativas=3,
                               capturar_progresso=None, controle_interrupcao=None):
        """Run trusted local worker commands in sequence in a dedicated workspace.

        Exit 75 is the worker protocol for a retryable provider failure after
        committing progress. Other exit codes and timeouts require reconciliation.
        The caller supplies only local, non-spawning workers and a final validator.
        """
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", task_id):
            raise ValueError("Identificador de tarefa invalido")
        if type(max_tentativas) is not int or not 1 <= max_tentativas <= 6:
            raise ValueError("Limite de tentativas invalido")
        if timeout <= 0:
            raise ValueError("Timeout invalido")

        workspace = Path(cwd).resolve(strict=True)
        lock_path = workspace / ".auto-failover.lock"
        with lock_path.open("x", encoding="utf-8") as lock:
            lock.write(str(os.getpid()))
        try:
            return self._executar_tentativas(
                task_id, selector, comando, validar, workspace, requisitos, timeout, max_tentativas,
                capturar_progresso, controle_interrupcao
            )
        finally:
            # Keep the lock for manual reconciliation if termination failed.
            if self.child_process is None or self.child_process.poll() is not None:
                lock_path.unlink()

    def _executar_tentativas(self, task_id, selector, comando, validar, cwd,
                             requisitos, timeout, max_tentativas, capturar_progresso, controle_interrupcao):
        if self.get_estado()["processo_ativo"]:
            raise RuntimeError("Supervisor ja possui processo ativo")
        if task_id in self.state["tarefas"]:
            raise RuntimeError("Tarefa existente requer reconciliacao")
        tentativas = []
        excluidos = set()
        grupos = set()
        resultado = {"status": "suspenso", "motivo": "limite_tentativas",
                     "task_id": task_id, "tentativas": tentativas}
        for _ in range(max_tentativas):
            selecao = selector.selecionar_modelo(
                task_id, {**(selector.config["requisitos_padrao"] if requisitos is None else requisitos),
                          "privado": True},
                exclude_provedores=excluidos, grupos_excluidos=grupos
            )
            if not selecao["sucesso"]:
                resultado.update(motivo=selecao["motivo"], rejeicoes=selecao["rejeicoes"])
                break
            if controle_interrupcao is not None and controle_interrupcao(task_id):
                resultado["motivo"] = "interrupcao_solicitada"
                break
            provedor = selecao["provedor_selecionado"]
            modelo = selecao["modelo_selecionado"]["identificador"]
            processo = self.iniciar_processo(comando(selecao), task_id, cwd, registrar_comando=False)
            try:
                processo.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                encerramento = self.encerrar_processo(task_id, force=True)
                resultado["motivo"] = "timeout" if encerramento["encerrado"] else "processo_ativo"

            tentativa = {"provedor": provedor, "modelo": modelo, "pid": processo.pid,
                         "returncode": processo.poll(), "finalizado_em": datetime.now(timezone.utc).isoformat()}
            if tentativa["returncode"] == 75 and resultado["motivo"] == "limite_tentativas":
                tentativa["falha"] = "indisponibilidade_declarada_pelo_worker"
                tentativa["checkpoint"] = capturar_progresso() if capturar_progresso else None
            tentativas.append(tentativa)
            self.state["tarefas"][task_id].update(status="suspenso", tentativas=tentativas)
            self._salvar_estado()
            if tentativa["returncode"] == 0 and resultado["motivo"] == "limite_tentativas":
                aprovado = validar()
                resultado.update(status="concluido" if aprovado else "falhou",
                                 motivo="validado" if aprovado else "validacao_falhou")
                break
            if tentativa["returncode"] != 75 or resultado["motivo"] != "limite_tentativas":
                if resultado["motivo"] == "limite_tentativas":
                    resultado["motivo"] = "falha_requer_reconciliacao"
                break
            if tentativa["checkpoint"] is None:
                resultado["motivo"] = "checkpoint_ausente"
                break
            excluidos.add(provedor)
            if selecao["grupo_cota"] is not None:
                grupos.add(selecao["grupo_cota"])

        self.state["tarefas"].setdefault(task_id, {}).update(resultado)
        self._salvar_estado()
        return resultado

    def get_estado(self):
        return {
            "processo_ativo": self.child_process is not None and self.child_process.poll() is None,
            "tarefas": list(self.state['tarefas'].keys()),
            "total_historico": len(self.state.get('historico', [])),
        }
