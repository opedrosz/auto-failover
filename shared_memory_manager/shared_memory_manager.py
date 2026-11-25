#!/usr/bin/env python3
"""
Shared Memory Manager - Componente 9 de 15 da AUTO FAILOVER V1.0.3

Memória persistente universal independente do agente utilizado.
Permite que o próximo agente compreenda o contexto completo sem perder informações.

Princípios:
- Preservar: objetivo original, requisitos, instruções do usuário, regras do projeto,
  permissoes concedidas, restricoes, decisoes arquiteturais, tarefas concluídas,
  tarefas pendentes, arquivos modificados, estado do Git, resultados dos testes,
  erros identificados
- Separar: memoria universal de regras/procedimentos, memoria especifica de cada projeto,
  memoria de cada tarefa, historico de execucao, checkpoints, registro de auditoria
- Nao misturar contextos de projetos diferentes
- Nao transformar automaticamente informacoes em instrucoes privilegiadas
- Na armazenar credenciais, tokens ou chaves de API
- Na transmitir automaticamente toda memoria local para outros provedores

Estruturas:
1. Memoria universal de regras e procedimentos
2. Memoria especifica de cada projeto
3. Memoria de cada tarefa
4. Historico de execucao
5. Checkpoints
6. Registros de auditoria
7. Permissoes autorizadas
"""

import json
import hashlib
import logging
import os
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.SharedMemory')

class SharedMemory:
    """Gerenciador de memoria persistente universal para desenvolvimento multiagente."""
    
    def __init__(self, base_dir=None, project_manager=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.project_manager = project_manager or self._carregar_project_manager()
        self.config_dir = self.base_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Caminhos das diferentes camadas de memoria
        self.data_dir = self.base_dir / "data"
        self.memory_dir = self.data_dir / "memory"
        self.universal_dir = self.memory_dir / "universal"
        self.projects_dir = self.memory_dir / "projects"
        self.tasks_dir = self.memory_dir / "tasks"
        self.history_dir = self.memory_dir / "history"
        
        # Garantir diretorios
        self._garantir_diretorios()
        
        # Memoria cache em memoria (para velocidade)
        self.cache = {}
        
        logger.info("Shared Memory Manager inicializado com 4 camadas de persistencia")
    
    def _carregar_project_manager(self):
        """Carregar Project Manager existente ou retornar None."""
        try:
            from project_manager import ProjectManager
            return ProjectManager(self.base_dir)
        except Exception as e:
            logger.debug(f"Project Manager nao disponivel: {e}")
            return None

    def _garantir_diretorios(self):
        """Criar todos os diretorios de memoria necessarios."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.universal_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
    
    # --- Camada 1: Memoria Universal de Regras e Procedimentos ---
    
    def salvar_regra_universal(self, chave, valor, fonte="system", meta=None):
        """Salvar regra universal que se aplica a todos os projetos."""
        meta = meta or {}
        dados = {
            "chave": chave,
            "valor": valor,
            "fonte": fonte,
            "timestamp": datetime.utcnow().isoformat(),
            "meta": meta
        }
        caminho = self.universal_dir / "regras.json"
        try:
            # Carregar regras existentes
            regras = self._carregar_arquivo(self.universal_dir / "regras.json", {})
            regras[chave] = dados
            self._salvar_arquivo(caminho, regras)
            logger.debug(f"Regra universal salva: {chave}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar regra universal: {e}")
            return False
    
    def carregar_regra_universal(self, chave):
        """Carregar regra universal."""
        regras = self._carregar_arquivo(self.universal_dir / "regras.json", {})
        return regras.get(chave, {}).get("valor", None)
    
    # --- Camada 2: Memoria Especifica de Cada Projeto ---
    
    def salvar_memoria_projeto(self, projeto_id, chave, valor, metadados=None):
        """Salvar memoria específica de um projeto."""
        metadados = metadados or {}
        dados = {
            "projeto_id": projeto_id,
            "chave": chave,
            "valor": valor,
            "timestamp": datetime.utcnow().isoformat(),
            "metadados": metadados
        }
        pasta = self.projects_dir / projeto_id
        pasta.mkdir(parents=True, exist_ok=True)
        caminho = pasta / "memoria.json"
        
        try:
            # Carregar memoria existente do projeto
            memoria = self._carregar_arquivo(caminho, {})
            memoria[chave] = dados
            self._salvar_arquivo(caminho, memoria)
            logger.debug(f"Memoria de projeto {projeto_id} salva: {chave}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar memoria de projeto: {e}")
            return False
    
    def carregar_memoria_projeto(self, projeto_id, chave=None):
        """Carregar memoria de um projeto especifico."""
        pasta = self.projects_dir / projeto_id
        if not pasta.is_file():
            # Arquivo nao existe ainda, return None
            # Actually pasta.is_dir() check
            if not pasta.exists():
                return {}
        
        memoria = self._carregar_arquivo(pasta / "memoria.json", {})
        
        if chave:
            return memoria.get(chave, {}).get("valor", None)
        return memoria
    
    # --- Camada 3: Memoria de Cada Tarefa ---
    
    def salvar_memoria_tarefa(self, task_id, conteudo, metadados=None):
        """Salvar memoria de uma tarefa específica."""
        dados = {
            "task_id": task_id,
            "conteudo": conteudo,
            "timestamp": datetime.utcnow().isoformat(),
            "metadados": metadados or {}
        }
        caminho = self.tasks_dir / f"tarefa_{task_id}.json"
        
        try:
            self._salvar_arquivo(caminho, dados)
            logger.debug(f"Memoria de tarefa {task_id} salva")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar memoria de tarefa: {e}")
            return False
    
    def carregar_memoria_tarefa(self, task_id):
        """Carregar memoria de uma tarefa."""
        caminho = self.tasks_dir / f"tarefa_{task_id}.json"
        return self._carregar_arquivo(caminho, {})
    
    # --- Camada 4: Historico de Execucao ---
    
    def registrar_execucao(self, task_id, agente, provedor, modelo, evento, 
                          motivo=None, estado_anterior=None, estado_posterior=None,
                          resultado=None, erro=None, checkpoint_id=None):
        """Registrar um evento no historico de execucao."""
        dado = {
            "task_id": task_id,
            "agente": agente,
            "provedor": provedor,
            "modelo": modelo,
            "evento": evento,
            "motivo": motivo,
            "timestamp": datetime.utcnow().isoformat(),
            "estado_anterior": estado_anterior or {},
            "estado_posterior": estado_posterior or {},
            "resultado": resultado or {},
            "erro": erro or {},
            "checkpoint_id": checkpoint_id
        }
        
        caminho = self.history_dir / f"execucao_{task_id}.jsonl"
        
        try:
            # Carregar historico existente ou criar novo
            if caminho.exists():
                # Append mode - adicionar nova linha
                with open(caminho, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(dado, ensure_ascii=False) + "\n")
            else:
                # Criar novo arquivo
                with open(caminho, 'w', encoding='utf-8') as f:
                    f.write(json.dumps(dado, ensure_ascii=False) + "\n")
            
            # Also add to cache
            self.cache[f"execucao_{task_id}"] = dado
            return True
        except Exception as e:
            logger.error(f"Erro ao registrar execucao: {e}")
            return False
    
    def carregar_historico_execucao(self, task_id):
        """Carregar todo historico de execucao de uma tarefa."""
        caminho = self.history_dir / f"execucao_{task_id}.jsonl"
        historico = []
        
        if caminho.exists():
            try:
                with open(caminho, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                historico.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.error(f"Erro ao carregar historico: {e}")
        
        return historico
    
    # --- Utilitarios ---
    
    def _carregar_arquivo(self, caminho, default=None):
        """Carregar arquivo JSON, retornando default se nao existir."""
        try:
            if caminho.exists():
                with open(caminho, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, Exception):
            pass
        return default if default is not None else {}
    
    def _salvar_arquivo(self, caminho, dados):
        """Salvar dados como JSON atomico."""
        try:
            # Write atomico: escrever para arquivo temporario e renomear
            tmp_path = caminho.with_suffix('.tmp')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            # Substituir atomicamente
            os.replace(tmp_path, caminho)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo atomico {caminho}: {e}")
            # Fallback: salvar diretamente
            try:
                with open(caminho, 'w', encoding='utf-8') as f:
                    json.dump(dados, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e2:
                logger.error(f"Falha critica ao salvar {caminho}: {e2}")
                return False
    
    def gerar_checksum(self, dados):
        """Gerar checksum SHA-256 para integridade."""
        if dados is None:
            return hashlib.sha256("none".encode('utf-8')).hexdigest()
        canonical = json.dumps(dados, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    def validar_integridade(self, dados_originais, dados_atualizados):
        """Validar integridade dos dados usando checksum."""
        checksum_antigo = self.gerar_checksum(dados_originais)
        checksum_novo = self.gerar_checksum(dados_atualizados)
        return checksum_antigo, checksum_novo
    
    def get_estado_memoria(self):
        """Retornar estado resumido de toda a memoria."""
        return {
            "universal_regras": len(list(self.universal_dir.glob("*.json"))) if self.universal_dir.exists() else 0,
            "projetos": {p.name: len(list((self.projects_dir / p.name).glob("*.json"))) 
                        for p in self.projects_dir.iterdir() if p.is_dir()},
            "tarefas": len(list(self.tasks_dir.glob("*.json"))) if self.tasks_dir.exists() else 0,
            "historico_registros": len(list(self.history_dir.glob("*.jsonl"))) if self.history_dir.exists() else 0,
            "cache_itens": len(self.cache)
        }


# Instancia global
try:
    global_shared_memory = SharedMemory()
except Exception as e:
    logger.error(f"Erro ao instanciar global SharedMemory: {e}")
    global_shared_memory = None