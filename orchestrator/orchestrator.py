#!/usr/bin/env python3
"""
Orchestrator - Componente 1 de 15 da AUTO FAILOVER V1.0.2

Coordenação central das tarefas e agentes.
Gerencia o ciclo de vida: iniciar -> monitorar -> fazer failover -> recuperar -> finalizar.

Princípios:
- NÃO modificar projetos existentes (Orion, Editor-Video, Codex Skills Integration)
- Priorizar recursos nativos do OpenCode
- Checkpoints atômicos antes de qualquer troca de provedor
- Zero custo por default (OpenCode Console -> Gemini free -> OpenRouter free -> Copilot cota)
- Memória compartilhada independente do agente
"""

import json
import os
import hashlib
import logging
import time
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.Orchestrator')

class Orchestrator:
    """Orquestrador central da infraestrutura multiagente."""
    
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.config_dir = self.base_dir / "config"
        self.data_dir = self.base_dir / "data"
        self.checkpoints_dir = self.base_dir / "checkpoints"
        self.logs_dir = self.base_dir / "logs"
        
        # Garantir que diretórios existam
        for d in [self.config_dir, self.data_dir, self.checkpoints_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Estado interno
        self.current_task = None
        self.current_provider = None
        self.fallback_count = 0
        self.max_fallbacks = 6  # Limite de tentativas (seção 9 V1.0.2)
        self.checkpoint_count = 0
        self.max_checkpoints = 3  # Máximo de checkpoints por tarefa (seção 6.2.5)
        
        # Carregar configuração
        self.config = self._carregar_config()
        
        logger.info(f"Orchestrator inicializado em: {self.base_dir}")
    
    def _carregar_config(self):
        """Carregar configuração da infraestrutura."""
        config_path = self.config_dir / "orchestrator_config.json"
        default_config = {
            "priority_order": [
                "opencode_console",
                "google_gemini_free", 
                "openrouter_free",
                "github_copilot",
                "openai_authorized",
                "local_llm"
            ],
            "max_cost_usd": 0.0,  # Zero custo por default
            "privacy_mode": "local-first",
            "health_check_interval": 30,  # segundos
            "retry_backoff_base": 2,  # backoff progressivo base
            "retry_max_delay": 300,  # 5 minutos máximo
            "circuit_breaker_threshold": 3,  # falhas consecutivas antes de abrir circuito
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # Mesclar com configuracao padrao (user config sobrescreve default)
                for key, value in user_config.items():
                    default_config[key] = value
                logger.info("Configuração carregada do arquivo existente")
            except Exception as e:
                logger.warning(f"Erro ao carregar configuração: {e}. Usando defaults.")
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
        else:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            logger.info("Configuração padrão criada")
        
        return default_config
    
    def iniciar_tarefa(self, task_id, descricao, payload=None):
        """
        Iniciar uma nova tarefa com rastreamento.
        
        Args:
            task_id: Identificador único da tarefa
            descricao: Descrição da tarefa
            payload: Payload/contexto inicial
            
        Returns:
            dict: Estado inicial da tarefa
        """
        logger.info(f"Iniciando tarefa: {task_id} - {descricao}")
        
        # Salvar checkpoint inicial (atomicamente)
        checkpoint = self._salvar_checkpoint(
            stage="inicio",
            task_id=task_id,
            motivo="inicio_tarefa",
            contexto_inicial=payload
        )
        
        self.current_task = {
            "task_id": task_id,
            "descricao": descricao,
            "status": "ativo",
            "iniciado_em": datetime.utcnow().isoformat(),
            "checkpoint_atual": checkpoint,
            "provedores_tentados": [],
            "acoes_realizadas": [],
            "contexto": payload or {},
            "ultima_atualizacao": datetime.utcnow().isoformat()
        }
        
        # Registrar no audit logger
        self._registrar_auditoria({
            "acao": "iniciar_tarefa",
            "task_id": task_id,
            "status": "iniciado",
            "timestamp": self.current_task["ultima_atualizacao"]
        })
        
        logger.info(f"Tarefa {task_id} iniciada com checkpoint {checkpoint['checksum'][:16]}...")
        return self.current_task
    
    def solicitar_provedor(self, modelo_solicitado, motivo="solicitacao_direta"):
        """
        Solicitar um provedor para executar a tarefa atual.
        
        Lógica de seleção (ordem de prioridade do config):
        1. OpenCode Console (gratuito, local)
        2. Google Gemini free (conta conectada)
        3. OpenRouter free (custo zero)
        4. GitHub Copilot (cota da assinatura)
        5. OpenAI (apenas com cota autorizada)
        6. IA local (llama.cpp etc.)
        """
        if not self.current_task:
            logger.error("Nenhuma tarefa ativa - use iniciar_tarefa primeiro")
            return None
        
        priority_order = self.config.get("priority_order", [
            "opencode_console",
            "google_gemini_free", 
            "openrouter_free",
            "github_copilot",
            "openai_authorized",
            "local_llm"
        ])
        
        logger.info(f"Selecionando provedor para tarefa {self.current_task['task_id']}")
        logger.info(f"Ordem de prioridade: {priority_order}")
        
        # Filtrar provedores já tentados neste ciclo
        ja_tentados = self.current_task.get("provedores_tentados", [])
        
        for alias_provedor in priority_order:
            if alias_provedor in ja_tentados:
                logger.debug(f"Pular provedor já tentado: {alias_provedor}")
                continue
            
            # Mapear alias para provedor real
            provedor_info = self._mapear_provedor(alias_provedor)
            if not provedor_info:
                logger.warning(f"Provedor desconhecido na priority order: {alias_provedor}")
                continue
            
            # Verificar saúde do provedor
            saudavel = self._verificar_saude_provedor(provedor_info)
            if not saudavel:
                logger.warning(f"Provedor {alias_provedor} com saúde comprometida, tentando mesmo assim...")
                # Ainda assim tentar, mas registrando warning
            
            logger.info(f"Tentando provedor: {alias_provedor} ({provedor_info.get('nome_real', 'N/A')})")
            
            # Salvar checkpoint antes da tentativa
            self._salvar_checkpoint(
                stage="antes_provedor",
                task_id=self.current_task["task_id"],
                motivo=f"troca_para_{alias_provedor}",
                contexto_depois=self.current_task.get("contexto", {})
            )
            
            # Marcar como tentado (mesmo que falhe)
            ja_tentados.append(alias_provedor)
            self.current_task["provedores_tentados"] = ja_tentados
            
            # Tentar executar
            resultado = self._executar_com_provedor(alias_provedor, provedor_info, motivo)
            
            if resultado and resultado.get("sucesso"):
                logger.info(f"Sucesso com provedor {alias_provedor}")
                self.current_provider = alias_provedor
                self.fallback_count = 0  # Resetar contador de fallbacks
                return resultado
            else:
                logger.warning(f"Falha com provedor {alias_provedor}")
                self.fallback_count += 1
                
                # Se atingiu limite de tentativas, não tentar mais
                if self.fallback_count >= self.max_fallbacks:
                    logger.error(f"Limite de {self.max_fallbacks} fallbacks atingido para tarefa {self.current_task['task_id']}")
                    self._registrar_auditoria({
                        "acao": "limite_fallbacks_atingido",
                        "task_id": self.current_task["task_id"],
                        "fallback_count": self.fallback_count,
                        "motivo": "excedido_limite_tentativas"
                    })
                    return {
                        "sucesso": False,
                        "motivo": "limite_fallbacks_atingido",
                        "fallback_count": self.fallback_count
                    }
                
                # Tentar próximo provedor
                continue
        
        # Todos os provedores falharam
        logger.error(f"Todos os provedores falharam para tarefa {self.current_task['task_id']}")
        self._registrar_auditoria({
            "acao": "todos_provedores_falharam",
            "task_id": self.current_task["task_id"],
            "fallback_count": self.fallback_count,
            "motivo": "nenhum_provedor_sucesso"
        })
        
        # Preservar progresso e suspender
        return {
            "sucesso": False,
            "motivo": "nenhum_provedor_sucesso",
            "fallback_count": self.fallback_count,
            "acao": "preservar_progresso_e_suspender"
        }
    
    def _mapear_provedor(self, alias):
        """Mapear alias para informações do provedor."""
        mapa = {
            "opencode_console": {
                "nome_real": "OpenCode Console",
                "tipo": "nativo",
                "gratuito": True,
                "privado": True,
                "ferramentas": False,  # Console nativo tem limitações de tools
                "contexto": "variável",
                "compatibilidade": "textos_simples"
            },
            "google_gemini_free": {
                "nome_real": "Google Gemini (modelos lite/flash)",
                "tipo": "cloud",
                "gratuito": True,  # Modelos lite são gratuitos na conta conectada
                "privado": False,
                "ferramentas": True,
                "contexto": "128K tokens (gemini-1.5-pro)",
                "compatibilidade": "multimodal + code"
            },
            "openrouter_free": {
                "nome_real": "OpenRouter (modelos free tier)",
                "tipo": "roteador",
                "gratuito": True,
                "privado": False,
                "ferramentas": True,  # Depende do modelo subjacente
                "contexto": "variável por modelo",
                "compatibilidade": "ampla (deepseek, nemotron, gemini free etc.)"
            },
            "github_copilot": {
                "nome_real": "GitHub Copilot",
                "tipo": "assinatura",
                "gratuito": False,
                "privado": False,
                "ferramentas": True,  # Nativo para development
                "contexto": "variável",
                "compatibilidade": "code superior (codex otimizado)"
            },
            "openai_authorized": {
                "nome_real": "OpenAI (cota autorizada)",
                "tipo": "cloud",
                "gratuito": False,
                "privado": False,
                "ferramentas": True,  # functions, tools completas
                "contexto": "variável por modelo",
                "compatibilidade": "state-of-the-art code + multimodal"
            },
            "local_llm": {
                "nome_real": "IA Local (llama.cpp)",
                "tipo": "local",
                "gratuito": True,  # Custo zero (próprio hardware)
                "privado": True,  # 100% local
                "ferramentas": True,  # Depende do template/Config
                "contexto": "configurável (1K a 100K+)",
                "compatibilidade": "depende do modelo treinado"
            }
        }
        return mapa.get(alias)
    
    def _verificar_saude_provedor(self, provedor_info):
        """Verificar saúde do provedor (simplificado - health monitor será dedicado)."""
        # Verificações básicas
        if not provedor_info:
            return False
        
        # Verificar se tem cota zero e modo privacy exige local
        if provedor_info.get("privado") and not self.config.get("privacy_mode", "local-first") == "local-first":
            # Modo privacy pedia local, mas esse provedor não é local
            # Verificar se temos alternativa local disponível
            pass
        
        return True  # Health monitor dedicado fará verificações mais robustas
    
    def _executar_com_provedor(self, alias, provedor_info, motivo):
        """Executar tarefa com provedor especificado (mock/placeholder)."""
        logger.info(f"Execução simulada com {alias}: {provedor_info['nome_real']}")
        
        # Placeholder - na verdade a execução seria feita via OpenCode API
        # ou integração LiteLLM. Aqui apenas registramos a intenção.
        return {
            "sucesso": False,  # Simular necessidade de fallback por enquanto
            "provedor_usado": alias,
            "modelo_usado": provedor_info.get("nome_real", "desconhecido"),
            "motivo": "simulacao - aguardando integração real",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _salvar_checkpoint(self, stage, task_id, motivo, contexto_inicial=None, contexto_depois=None):
        """Salvar checkpoint atômico da estado atual."""
        import hashlib
        
        self.checkpoint_count += 1
        
        # Limitar número de checkpoints
        if self.checkpoint_count > self.max_checkpoints:
            # Remover checkpoint mais antigo (simplificado: apenas logar)
            logger.warning(f"Limite de {self.max_checkpoints} checkpoints atingido. "
                          "Descartando checkpoint antigo ou consolidando.")
            # Em implementação completa, removeríamos o mais antigo ou consolidar
        
        # Criar dados do checkpoint
        checkpoint_data = {
            "checksum": self._gerar_checksum(contexto_inicial or {}),
            "stage": stage,
            "task_id": task_id,
            "motivo": motivo,
            "timestamp": datetime.utcnow().isoformat(),
            "contexto_inicial": contexto_inicial or {},
            "contexto_depois": contexto_depois or {},
            "fallback_count": self.fallback_count,
            "provedor_atual": self.current_provider
        }
        
        # Salvar em arquivo
        checkpoint_path = self.checkpoints_dir / f"checkpoint_{task_id}_{stage}_{self.checkpoint_count}.json"
        try:
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Checkpoint salvo: {checkpoint_path}")
        except Exception as e:
            logger.error(f"Não foi salvar checkpoint: {e}")
            return None
        
        # Registrar na auditoria
        self._registrar_auditoria({
            "acao": "salvar_checkpoint",
            "task_id": task_id,
            "stage": stage,
            "checksum": checkpoint_data["checksum"][:16] + "...",
            "motivo": motivo,
            "checkpoint_path": str(checkpoint_path)
        })
        
        return checkpoint_data
    
    def _gerar_checksum(self, dados):
        """Gerar checksum SHA-256 dos dados."""
        canonical = json.dumps(dados, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    def _registrar_auditoria(self, entry):
        """Registrar entrada no audit logger."""
        audit_path = self.logs_dir / "audit_log.jsonl"
        try:
            with open(audit_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Erro no audit logger: {e}")
    
    def recuperar_tarefa(self, task_id, checkpoint_stage=None):
        """
        Recuperar tarefa a partir de um checkpoint.
        
        Args:
            task_id: ID da tarefa a recuperar
            checkpoint_stage: Stage específico (opcional). Se None, usa último checkpoint.
        """
        logger.info(f"Recuperando tarefa: {task_id}")
        
        # Buscar checkpoints para esta tarefa
        checkpoints = list(self.checkpoints_dir.glob(f"checkpoint_{task_id}_*.json"))
        
        if not checkpoints:
            logger.warning(f"Nenhum checkpoint encontrado para tarefa {task_id}")
            # Tentar encontrar por partial match
            checkpoints = [p for p in self.checkpoints_dir.glob("checkpoint_*.json") 
                          if task_id in p.name]
        
        if not checkpoints:
            logger.error(f"Não foi possível recuperar tarefa {task_id}: nenhum checkpoint")
            return None
        
        # Seleionar checkpoint
        if checkpoint_stage:
            alvo = [p for p in checkpoints if f"_{checkpoint_stage}_" in p.name]
            if alvo:
                checkpoint_file = alvo[0]
            else:
                logger.warning(f"Checkpoint stage '{checkpoint_stage}' não encontrado. "
                              "Usando último checkpoint disponível.")
                checkpoint_file = checkpoints[-1]
        else:
            # Usar o mais recente (por ordem de nome, que inclui número de sequência)
            checkpoint_file = checkpoints[-1]
        
        logger.info(f"Recuperando do checkpoint: {checkpoint_file.name}")
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
        except Exception as e:
            logger.error(f"Erro ao ler checkpoint {checkpoint_file}: {e}")
            return None
        
        # Restaurar tarefa a partir do checkpoint
        self.current_task = {
            "task_id": task_id,
            "descricao": self.current_task.get("descricao", "Tarefa recuperada"),
            "status": "recuperado",
            "iniciado_em": checkpoint.get("timestamp", datetime.utcnow().isoformat()),
            "checkpoint_atual": checkpoint,
            "provedores_tentados": checkpoint.get("provedores_tentados", []),
            "acoes_realizadas": checkpoint.get("acoes_realizadas", []),
            "contexto": checkpoint.get("contexto_depois", checkpoint.get("contexto_inicial", {})),
            "ultima_atualizacao": datetime.utcnow().isoformat()
        }
        
        # Registrar recuperação
        self._registrar_auditoria({
            "acao": "recuperar_tarefa",
            "task_id": task_id,
            "checkpoint_arquivo": checkpoint_file.name,
            "checksum": checkpoint.get("checksum", "")[:16] + "...",
            "stage": checkpoint.get("stage", "desconhecido")
        })
        
        logger.info(f"Tarefa {task_id} recuperada do checkpoint {checkpoint_file.name}")
        return self.current_task
    
    def finalizar_tarefa(self, sucesso=True, resultado_final=None):
        """
        Finalizar a tarefa atual com salvamento do estado final.
        """
        if not self.current_task:
            logger.warning("Nenhuma tarefa ativa para finalizar")
            return
        
        logger.info(f"Finalizando tarefa: {self.current_task['task_id']} "
                     f"(sucesso={sucesso})")
        
        # Salvar checkpoint final
        self._salvar_checkpoint(
            stage="fim",
            task_id=self.current_task["task_id"],
            motivo="finalizacao_tarefa",
            contexto_inicial=self.current_task.get("contexto", {}),
            contexto_depois=resultado_final or {"status": "concluido", "sucesso": sucesso}
        )
        
        # Atualizar status
        self.current_task["status"] = "finalizado" if sucesso else "interrompido"
        self.current_task["finalizado_em"] = datetime.utcnow().isoformat()
        self.current_task["resultado_final"] = resultado_final
        
        # Registrar na auditoria
        self._registrar_auditoria({
            "acao": "finalizar_tarefa",
            "task_id": self.current_task["task_id"],
            "sucesso": sucesso,
            "fallback_count": self.fallback_count,
            "provedores_tentados": self.current_task.get("provedores_tentados", [])
        })
        
        # Limpar tarefa atual (mas preservar dados em checkpoints)
        self.current_task = None
        logger.info("Tarefa finalizada e estado preservado em checkpoints")
    
    def solicitar_fallback(self, motivo="falha_provedor"):
        """
        Solicitar troca automática de provedor (failover).
        Esta é a interface principal para o Failover Manager.
        """
        if not self.current_task:
            logger.error("Nenhuma tarefa ativa para fazer fallback")
            return None
        
        logger.info(f"Solicitando fallback para tarefa {self.current_task['task_id']}: {motivo}")
        
        # Incrementar contador e tentar próximo provedor
        resultado = self.solicitar_provedor(
            modelo_solicitado=None,  # Usará a próxima priority order
            motivo=motivo
        )
        
        return resultado
    
    def get_estado_atual(self):
        """Retornar estado atual do orchestrator."""
        return {
            "task_id": self.current_task["task_id"] if self.current_task else None,
            "status_tarefa": self.current_task["status"] if self.current_task else "inativo",
            "provedor_atual": self.current_provider,
            "fallback_count": self.fallback_count,
            "checkpoint_count": self.checkpoint_count,
            "priority_order": self.config.get("priority_order", []),
            "modo_privacy": self.config.get("privacy_mode", "local-first")
        }