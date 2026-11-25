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
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

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
            except Exception:
                pass
        return {"tarefas": {}, "historico": []}

    def _salvar_estado(self):
        self.state_file.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2), encoding='utf-8')

    def iniciar_processo(self, cmd, task_id, cwd=None):
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
            'pid': proc.pid, 'cmd': cmd,
            'iniciado_em': datetime.utcnow().isoformat(),
            'status': 'em_andamento',
        }
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
                'finalizado_em': datetime.utcnow().isoformat(),
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
            proc.wait(timeout=10)
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

    def get_estado(self):
        return {
            "processo_ativo": self.child_process is not None and self.child_process.poll() is None,
            "tarefas": list(self.state['tarefas'].keys()),
            "total_historico": len(self.state.get('historico', [])),
        }
