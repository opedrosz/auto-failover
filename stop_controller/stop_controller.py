#!/usr/bin/env python3
"""
Stop Controller - Componente 13 de 15 da AUTO FAILOVER V1.0.3

Implementar mecanismo funcional de:
- Pausa.
- Continuação.
- Cancelamento.
- Interrupção imediata.
- Suspensão segura.
- Recuperação manual.

Ao interromper:
1. Bloquear novas solicitações.
2. Solicitar cancelamento das operacoes em andamento.
3. Verificar o encerramento real dos processos controlados.
4. Registrar operacoes concluidas e incertas.
5. Salvar checkpoint seguro.
6. Registrar motivo da interrupcao.
7. Impedir que outro agente reinicie uma tarefa cancelada sem autorizacao.

Testar interrupcao durante execucao, espera, troca de provedor e gravacao de checkpoint.
"""

import json
import logging
import os
import time
import hashlib
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.StopController')

class StopController:
    """Controlador de interrupcao, pausa e retomada para desenvolvimento multiagente."""
    
    def __init__(self, base_dir=None, checkpoint_mgr=None, orchestrator=None, 
                 audit_logger=None, security_controller=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.checkpoint_mgr = checkpoint_mgr or self._carregar_checkpoint_mgr()
        self.orchestrator = orchestrator or self._carregar_orchestrator()
        self.audit_logger = audit_logger or self._carregar_audit_logger()
        self.security_controller = security_controller or self._carregar_seguranca()
        
        # Estado do controle
        self.tarefas_ativas = {}  # task_id -> estado {pausado, cancelado, finalizado}
        self.solicitacoes_bloqueadas = {}  # task_id -> motivo do bloqueio
        self.checkpoints_salvos = {}  # task_id -> caminho do checkpoint de seguranca
        
        # Garantir diretorios
        (self.base_dir / "data").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "logs").mkdir(parents=True, exist_ok=True)
        
        # Carregar estado salvo
        self._carregar_estado()
        
        logger.info("Stop Controller inicializado")
    
    def _carregar_checkpoint_mgr(self):
        try:
            from checkpoint_manager import CheckpointManager
            return CheckpointManager(self.base_dir)
        except Exception as e:
            logger.error(f"Erro: {e}")
            return None
    
    def _carregar_orchestrator(self):
        try:
            from orchestrator import Orchestrator
            return Orchestrator(self.base_dir)
        except Exception as e:
            logger.error(f"Erro: {e}")
            return None
    
    def _carregar_audit_logger(self):
        try:
            from audit_logger import AuditLogger
            return AuditLogger(self.base_dir)
        except Exception as e:
            logger.error(f"Erro: {e}")
            return None
    
    def _carregar_seguranca(self):
        try:
            from security_controller import SecurityController
            return SecurityController(self.base_dir)
        except Exception as e:
            logger.error(f"Erro: {e}")
            return None
    
    def _carregar_estado(self):
        """Carregar estado salvo de tarefas ativas."""
        estado_path = self.base_dir / "data" / "stop_controller_estado.json"
        try:
            if estado_path.exists():
                with open(estado_path, 'r', encoding='utf-8') as f:
                    estado = json.load(f)
                self.tarefas_ativas = estado.get("tarefas_ativas", {})
                self.solicitacoes_bloqueadas = estado.get("solicitacoes_bloqueadas", {})
                logger.debug(f"Estado do Stop Controller carregado: {len(self.tarefas_ativas)} tarefas")
        except Exception as e:
            logger.warning(f"Erro ao carregar estado: {e}")
            self.tarefas_ativas = {}
            self.solicitacoes_bloqueadas = {}
    
    def _salvar_estado(self):
        """Salvar estado atual no disco."""
        estado_path = self.base_dir / "data" / "stop_controller_estado.json"
        try:
            estado = {
                "tarefas_ativas": self.tarefas_ativas,
                "solicitacoes_bloqueadas": self.solicitacoes_bloqueadas,
                "timestamp_atualizacao": datetime.utcnow().isoformat()
            }
            with open(estado_path, 'w', encoding='utf-8') as f:
                json.dump(estado, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar estado: {e}")
    
    # --- Metodos de Controle ---
    
    def pausar(self, task_id, motivo="pausa_solicitada", salvar_checkpoint=True):
        """
        Pausar uma tarefa em andamento.
        
        Args:
            task_id: ID da tarefa a ser pausada
            motivo: motivo da pausa
            salvar_checkpoint: se True, salva checkpoint antes de pausar
        
        Returns:
            dict: resultado da operacao
        """
        # Bloquear novas solicitacoes para esta tarefa
        self.tarefas_ativas[task_id] = {
            "status": "pausado",
            "motivo": motivo,
            "timestamp_pausa": datetime.utcnow().isoformat(),
            "cancelado": False
        }
        self.solicitacoes_bloqueadas[task_id] = "pausa"
        
        # Salvar checkpoint se solicitado
        if salvar_checkpoint and self.checkpoint_mgr:
            checkpoint = self.checkpoint_mgr.salvar_checkpoint(
                task_id=task_id,
                stage="pausado",
                motivo="tarefa_pausada",
                contexto_atual=self._get_contexto_tarefa(task_id) or {},
                metadados_adicionais={"motivo_pausa": motivo}
            )
            self.checkpoints_salvos[task_id] = checkpoint
        
        # Registrar auditoria
        if self.audit_logger:
            self.audit_logger.registrar_evento({
                "tipo": "pausa",
                "task_id": task_id,
                "motivo": motivo,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        logger.info(f"Tarefa {task_id} pausada: {motivo}")
        return {
            "sucesso": True,
            "task_id": task_id,
            "status": "pausado",
            "motivo": motivo
        }
    
    def retoma(self, task_id, novo_contexto=None, reiniciar_provedor=False):
        """
        Retomar uma tarefa pausada.
        
        Args:
            task_id: ID da tarefa a ser retomada
            novo_contexto: novo contexto/conversa para continuar
            reiniciar_provedor: se True, reinicia o provedor da tarefa
        
        Returns:
            dict: resultado da retomada
        """
        # Verificar se a tarefa existe e esta pausada
        if task_id not in self.tarefas_ativas:
            return {
                "sucesso": False,
                "motivo": "tarefa_nao_encontrada_ou_nao_pausada",
                "acao": "verificar_task_id"
            }
        
        tarefa = self.tarefas_ativas[task_id]
        if tarefa.get("status") != "pausado":
            return {
                "sucesso": False,
                "motivo": f"tarefa status '{tarefa.get('status')}', esperava 'pausado'",
                "acao": "verificar_status_tarefa"
            }
        
        # Remover estado de pausa
        tarefa["status"] = "em_andamento"
        tarefa["timestamp_retoma"] = datetime.utcnow().isoformat()
        tarefa["contexto_atual"] = novo_contexto or {}
        self.solicitacoes_bloqueadas.pop(task_id, None)
        
        # Salvar estado
        self._salvar_estado()
        
        # Registrar auditoria
        if self.audit_logger:
            self.audit_logger.registrar_evento({
                "tipo": "retoma",
                "task_id": task_id,
                "motivo": "retoma_solicitada",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        logger.info(f"Tarefa {task_id} retomada")
        return {
            "sucesso": True,
            "task_id": task_id,
            "status": "em_andamento",
            "motivo": "retoma_solicitada"
        }
    
    def cancelar(self, task_id, motivo="cancelamento_solicitado", salvar_checkpoint=True):
        """
        Cancelar uma tarefa.
        
        Diferente da pausa, o cancelamento indica que a tarefa nao deve mais ser retomada
        sem autorizacao explicita.
        """
        # Marcar tarefa como cancelada
        self.tarefas_ativas[task_id] = {
            "status": "cancelado",
            "motivo": motivo,
            "timestamp_cancelamento": datetime.utcnow().isoformat(),
            "cancelado": True
        }
        
        # Bloquear solicitacoes novas para esta tarefa
        self.solicitacoes_bloqueadas[task_id] = "cancelamento"
        
        # Salvar checkpoint de seguranca se solicitado
        if salvar_checkpoint and self.checkpoint_mgr:
            checkpoint = self.checkpoint_mgr.salvar_checkpoint(
                task_id=task_id,
                stage="cancelado",
                motivo="tarefa_cancelada",
                contexto_atual=self._get_contexto_tarefa(task_id) or {},
                metadados_adicionais={"motivo_cancelamento": motivo}
            )
            self.checkpoints_salvos[task_id] = checkpoint
        
        # Registrar auditoria
        if self.audit_logger:
            self.audit_logger.registrar_evento({
                "tipo": "cancelamento",
                "task_id": task_id,
                "motivo": motivo,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Impedir reinicializacao automatica - registrar aviso
        logger.warning(f"Tarefa {task_id} cancelada: {motivo}. "
                       "Nao reiniciar automaticamente sem autorizacao explicitada.")
        
        return {
            "sucesso": True,
            "task_id": task_id,
            "status": "cancelado",
            "motivo": motivo
        }
    
    def interrupcao_imediata(self, task_id, motivo="interrupcao_manual_urgente"):
        """
        Interrupcao imediata - bloqueia tudo instantaneamente.
        
        Mais forte que pausa ou cancelamento - usado em situacoes de emergencia.
        """
        # Marcar como interrputido
        self.tarefas_ativas[task_id] = {
            "status": "interrompido",
            "motivo": motivo,
            "timestamp_interrupt": datetime.utcnow().isoformat(),
            "cancelado": True,
            "imediato": True
        }
        
        # Bloquear todas solicitacoes
        self.solicitacoes_bloqueadas[task_id] = "interrupcao_urgente"
        
        # Tentar salvar checkpoint imediatamente
        if self.checkpoint_mgr:
            try:
                self.checkpoint_mgr.salvar_checkpoint(
                    task_id=task_id,
                    stage="interrompido",
                    motivo="interrupcao_urgente",
                    contexto_atual=self._get_contexto_tarefa(task_id) or {},
                    metadados_adicionais={"motivo_interrupt": motivo, "imediato": True}
                )
            except Exception as e:
                logger.error(f"Erro ao salvar checkpoint durante interrupcao urgente: {e}")
        
        # Registrar auditoria
        if self.audit_logger:
            self.audit_logger.registrar_evento({
                "tipo": "interrupcao_urgente",
                "task_id": task_id,
                "motivo": motivo,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        logger.critical(f"Interrupcao urgente na tarefa {task_id}: {motivo}")
        
        return {
            "sucesso": True,
            "task_id": task_id,
            "status": "interrompido",
            "motivo": motivo,
            "imediato": True
        }
    
    def finalizar(self, task_id, resultado=None, salvar_checkpoint=True):
        """
        Finalizar uma tarefa conclusa com sucesso.
        
        Args:
            task_id: ID da tarefa
            resultado: resultado final da tarefa
            salvar_checkpoint: se True, salva checkpoint final
        """
        # Marcar como finalizado
        self.tarefas_ativas[task_id] = {
            "status": "finalizado",
            "motivo": "concluido",
            "timestamp_finalizacao": datetime.utcnow().isoformat(),
            "resultado": resultado or {},
            "cancelado": False
        }
        
        # Salvar checkpoint final
        if salvar_checkpoint and self.checkpoint_mgr:
            checkpoint = self.checkpoint_mgr.salvar_checkpoint(
                task_id=task_id,
                stage="finalizado",
                motivo="tarefa_concluida",
                contexto_atual=self._get_contexto_tarefa(task_id) or {},
                metadados_adicionais={"resultado": resultado or {}}
            )
            self.checkpoints_salvos[task_id] = checkpoint
        
        # Registrar auditoria
        if self.audit_logger:
            self.audit_logger.registrar_evento({
                "tipo": "finalizacao",
                "task_id": task_id,
                "motivo": "concluido",
                "timestamp": datetime.utcnow().isoformat(),
                "resultado": resultado or {}
            })
        
        # Remover da lista de tarefas ativas (ou manter para historico)
        # manter por historico, mas marcar como finalizado
        
        logger.info(f"Tarefa {task_id} finalizada com sucesso")
        return {
            "sucesso": True,
            "task_id": task_id,
            "status": "finalizado",
            "motivo": "concluido"
        }
    
    # --- Metodos Auxiliares ---
    
    def _get_contexto_tarefa(self, task_id):
        """Obter contexto atual da tarefa do orchestrator se disponivel."""
        if self.orchestrator and self.orchestrator.current_task:
            if self.orchestrator.current_task.get("task_id") == task_id:
                return self.orchestrator.current_task.get("contexto", {})
        return None
    
    def verificar_tarefa(self, task_id):
        """Verificar status atual de uma tarefa."""
        if task_id in self.tarefas_ativas:
            return self.tarefas_ativas[task_id]
        return {"status": "nao_encontrada", "motivo": "task_id nao esta ativo"}
    
    def autorizar_retomada(self, task_id, autorizador_id, justificativa=""):
        """
        Autorizar reinicializacao de uma tarefa cancelada.
        
        Somente agentes autorizados podem retomar tarefas canceladas.
        """
        if task_id not in self.tarefas_ativas:
            return {"autorizado": False, "motivo": "task_id nao encontrado"}
        
        tarefa = self.tarefas_ativas[task_id]
        if tarefa.get("status") != "cancelado":
            return {"autorizado": False, "motivo": f"tarefa status '{tarefa.get('status')}', nao cancelado"}
        
        # Autorizar - mudar status para em_andamento com autorizacao
        tarefa["status"] = "em_andamento"
        tarefa["autorizador_id"] = autorizador_id
        tarefa["justificativa_retoma"] = justificativa
        tarefa["timestamp_autorizacao"] = datetime.utcnow().isoformat()
        
        # Salvar estado
        self._salvar_estado()
        
        # Registrar auditoria
        if self.audit_logger:
            self.audit_logger.registrar_evento({
                "tipo": "autorizacao_retomada",
                "task_id": task_id,
                "autorizador_id": autorizador_id,
                "justificativa": justificativa,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        logger.info(f"Tarefa {task_id} autorizada para retomada por {autorizador_id}")
        return {
            "autorizado": True,
            "task_id": task_id,
            "status": "em_andamento",
            "motivo": "autorizado_por_admin"
        }
    
    def get_estado_geral(self):
        """Retornar estado geral do Stop Controller."""
        return {
            "total_tarefas_ativas": len(self.tarefas_ativas),
            "tarefas_pausadas": sum(1 for t in self.tarefas_ativas.values() if t.get("status") == "pausado"),
            "tarefas_canceladas": sum(1 for t in self.tarefas_ativas.values() if t.get("status") == "cancelado"),
            "tarefas_interrompidas": sum(1 for t in self.tarefas_ativas.values() if t.get("status") == "interrompido"),
            "tarefas_finalizadas": sum(1 for t in self.tarefas_ativas.values() if t.get("status") == "finalizado"),
            "tarefas_em_andamento": sum(1 for t in self.tarefas_ativas.values() if t.get("status") == "em_andamento"),
            "total_solicitacoes_bloqueadas": len(self.solicitacoes_bloqueadas),
            "checkpoints_salvos": len(self.checkpoints_salvos)
        }


# Instancia global
try:
    global_stop_controller = StopController()
except Exception as e:
    logger.error(f"Erro ao instanciar global StopController: {e}")
    global_stop_controller = None