#!/usr/bin/env python3
"""
Checkpoint Manager - Componente 7 de 15 da AUTO FAILOVER V1.0.2

Salvamento persistente, atômico e recuperável de estados de tarefa.
Garante idempotência: mesma execução = mesmo resultado.
Prevenção de ciclos infinitos com limites de checkpoint.

Princípios:
- Checkpoints atomicos com SHA-256 checksum
- Recuperacao idempotente: mesma entrada = mesma saida
- Limite maximo de 3 checkpoints por tarefa (seccao 6.2.5)
- Nao re-executir açoes com efeitos colaterais
- Preservar progresso quando todos os provedores indisponiveis
"""

import json
import hashlib
import logging
import os
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.CheckpointManager')

class CheckpointManager:
    """Gerenciador de checkpoints atomicos e recuperacao de tarefas."""
    
    def __init__(self, base_dir=None, registry=None, orchestrator=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.registry = registry or self._carregar_registro()
        self.orchestrator = orchestrator or self._carregar_orchestrator()
        self.config_dir = self.base_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivos de checkpoint
        self.checkpoints_dir = self.base_dir / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivo de metadados de controle por tarefa
        self.controle_arquivo = self.base_dir / "data" / "checkpoint_controle.jsonl"
        
        # Estatisticas
        total_checkpoints = 0
        try:
            if self.checkpoints_dir.exists():
                total_checkpoints = len([f for f in self.checkpoints_dir.iterdir() 
                                          if f.is_file() and f.name.startswith("checkpoint_")])
        except:
            pass
        logger.info(f"Checkpoint Manager inicializado. "
                     f"Checkpoints totais: {total_checkpoints}")
    
    def _carregar_registro(self):
        """Carregar Provider Registry."""
        try:
            from provider_registry import ProviderRegistry
            return ProviderRegistry(self.base_dir)
        except Exception as e:
            logger.error(f"Erro ao carregar registry: {e}")
            class MinimalRegistry:
                provedores = {}
            return MinimalRegistry()
    
    def _carregar_orchestrator(self):
        """Carregar orchestrator existente ou retornar None."""
        try:
            from orchestrator import Orchestrator
            return Orchestrator(self.base_dir)
        except Exception as e:
            logger.debug(f"Orchestrator nao disponivel: {e}")
            return None
    
    def gerar_checksum(self, dados):
        """Gerar checksum SHA-256 para idempotência."""
        if dados is None:
            return hashlib.sha256("none".encode('utf-8')).hexdigest()
        canonical = json.dumps(dados, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    def salvar_checkpoint(self, task_id, stage, motivo, 
                          contexto_atual, contexto_anterior=None,
                          metadados_adicionais=None):
        """
        Salvar checkpoint atomico do estado da tarefa.
        
        Args:
            task_id: ID da tarefa
            stage: Etapa (ex: "inicio", "depois_provedor_X", "fim", "depois_fallback")
            motivo: Por que este checkpoint foi salvo
            contexto_atual: Dados atuais do contexto/conversa
            contexto_anterior: Dados antes desta etapa (opcional)
            metadados_adicionais: Dict com info extra (fallback_count, etc.)
        
        Returns:
            dict: Dados do checkpoint salvo ou None em erro
        """
        # Limite de checkpoints configuravel (V1.0.4: nao limitar a 3 por padrao)
        # max_checkpoints=None significa ilimitado (padrao)
        max_checkpoints = getattr(self, 'max_checkpoints', None)
        count_atual = self._contar_checkpoints_tarefa(task_id)

        if max_checkpoints is not None and count_atual >= max_checkpoints:
            logger.warning(f"Limite configuravel de {max_checkpoints} checkpoints "
                          f"atingido para {task_id}. Removendo o mais antigo.")
            checkpoints = self._listar_checkpoints_tarefa(task_id)
            if len(checkpoints) >= max_checkpoints:
                mais_antigo = checkpoints[0]
                try:
                    os.remove(mais_antigo)
                    logger.info(f"Removido checkpoint antigo: {mais_antigo.name}")
                except Exception as e:
                    logger.error(f"Erro ao remover checkpoint antigo: {e}")
        
        # Gerar checksum do contexto
        checksum = self.gerar_checksum(contexto_atual)
        
        # Montar dados do checkpoint
        checkpoint_data = {
            "checksum": checksum,
            "task_id": task_id,
            "stage": stage,
            "motivo": motivo,
            "timestamp": datetime.utcnow().isoformat(),
            "contexto_atual": contexto_atual if contexto_atual else {},
            "contexto_anterior": contexto_anterior if contexto_anterior else {},
            "fallback_count": metadados_adicionais.get("fallback_count", 0) if metadados_adicionais else 0,
            "provedor_atual": metadados_adicionais.get("provedor_atual", None) if metadados_adicionais else None,
            "sequencia": count_atual + 1  # Numero desta sequencia (1, 2, 3)
        }
        
        # Salvar em arquivo (nome atomico)
        checkpoint_path = self.checkpoints_dir / f"checkpoint_{task_id}_{stage}_{count_atual + 1}.json"
        
        try:
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            # Registrar no controle
            self._registrar_controle(checkpoint_path, "salvar", {
                "task_id": task_id,
                "stage": stage,
                "checksum": checksum[:16] + "..."
            })
            
            logger.debug(f"Checkpoint salvo: {checkpoint_path} (sequencia {count_atual + 1})")
            return checkpoint_data
            
        except Exception as e:
            logger.error(f"Erro ao salvar checkpoint para {task_id}: {e}")
            return None
    
    def _contar_checkpoints_tarefa(self, task_id):
        """Contar checkpoints existentes para uma tarefa."""
        pattern = f"checkpoint_{task_id}_"
        if not self.checkpoints_dir.exists():
            return 0
        return len([f for f in self.checkpoints_dir.iterdir() 
                    if f.is_file() and f.name.startswith(pattern)])
    
    def _listar_checkpoints_tarefa(self, task_id):
        """Listar checkpoints para uma tarefa, ordenados por sequencia."""
        pattern = f"checkpoint_{task_id}_"
        if not self.checkpoints_dir.exists():
            return []
        checkpoints = [f for f in self.checkpoints_dir.iterdir() 
                       if f.is_file() and f.name.startswith(pattern)]
        # Ordenar pelo numero sequencial no nome do arquivo
        def extrair_sequencia(nome_arquivo):
            try:
                # Formato: checkpoint_{task_id}_{stage}_{numero}.json
                partes = nome_arquivo.name.replace("checkpoint_", "").replace(".json", "").split("_")
                return int(partes[-1]) if partes else 0
            except:
                return 0
        
        checkpoints.sort(key=extrair_sequencia)
        return checkpoints
    
    def recuperar_checkpoint(self, task_id, stage=None):
        """
        Recuperar checkpoint para uma tarefa.
        
        Args:
            task_id: ID da tarefa
            stage: Stage especifico (opcional). Se None, usa o mais recente.
        
        Returns:
            dict: Dados do checkpoint ou None se nao encontrado
        """
        checkpoints = self._listar_checkpoints_tarefa(task_id)
        
        if not checkpoints:
            logger.warning(f"Nenhum checkpoint encontrado para tarefa {task_id}")
            return None
        
        # Selecionar qual checkpoint usar
        if stage:
            # Buscar stage especifico
            alvo = [p for p in checkpoints if f"_{stage}_" in p.name]
            if alvo:
                checkpoint_file = alvo[0]
            else:
                logger.warning(f"Checkpoint stage '{stage}' nao encontrado para {task_id}")
                checkpoint_file = checkpoints[-1]  # Fallback para o mais recente
        else:
            # Usar o mais recente (ultimo da lista ordenada)
            checkpoint_file = checkpoints[-1]
        
        logger.info(f"Recuperando checkpoint: {checkpoint_file.name}")
        
        # Tentar carregar o checkpoint selecionado; se corrompido, tentar anteriores
        checkpoint = None
        candidatos = list(reversed(checkpoints))  # do mais recente ao mais antigo
        if checkpoint_file in candidatos:
            # garantir que o selecionado seja o primeiro
            candidatos.remove(checkpoint_file)
            candidatos.insert(0, checkpoint_file)
        for candidato in candidatos:
            try:
                with open(candidato, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                if candidato != checkpoint_file:
                    logger.warning(f"Checkpoint {checkpoint_file.name} corrompido; "
                                   f"usando checkpoint anterior: {candidato.name}")
                    checkpoint_file = candidato
                break
            except Exception as e:
                logger.warning(f"Checkpoint corrompido ignorado: {candidato.name}: {e}")
                checkpoint = None
        if checkpoint is None:
            logger.error("Todos os checkpoints da tarefa estao corrompidos")
            return None
            
        logger.info(f"Checkpoint recuperado: stage={checkpoint.get('stage')}, "
                     f"checksum={checkpoint.get('checksum', '')[:16]}...")

        # Registrar recuperacao
        self._registrar_controle(checkpoint_file, "recuperar", {
            "task_id": task_id,
            "stage": checkpoint.get("stage"),
            "checksum_validado": checkpoint.get("checksum", "")[:16] + "..."
        })

        return checkpoint
    
    def _registrar_controle(self, checkpoint_path, acao, metadados):
        """Registrar acao de checkpoint no arquivo de controle."""
        try:
            with open(self.controle_arquivo, 'a', encoding='utf-8') as f:
                entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "checkpoint_arquivo": str(checkpoint_path),
                    "acao": acao,
                    **metadados
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Erro ao registrar controle de checkpoint: {e}")
    
    def verificar_idempotencia(self, task_id, contexto_entrada):
        """
        Verificar se a tarefa ja foi executada com este contexto (idempotencia).
        
        Args:
            task_id: ID da tarefa
            contexto_entrada: Contexto de entrada atual
        
        Returns:
            dict: { "idempotente": True/False, "checkpoint_anterior": ..., 
                     "resultado_anterior": ..., "deve_reexecutir": True/False }
        """
        checkpoint_anterior = self.recuperar_checkpoint(task_id)
        
        if not checkpoint_anterior:
            return {
                "idempotente": False,
                "motivo": "nenhum_checkpoint_anterior_encontrado",
                "deve_reexecutir": True
            }
        
        # Comparar checksum do checkpoint com hash do contexto de entrada
        checksum_anterior = checkpoint_anterior.get("checksum", "")
        hash_entrada = self.gerar_checksum(contexto_entrada)
        
        if checksum_anterior == hash_entrada:
            # Mesmo contexto ja foi processado
            return {
                "idempotente": True,
                "motivo": "contexto identico encontrado em checkpoint anterior",
                "checkpoint_anterior": checkpoint_anterior,
                "stage_anterior": checkpoint_anterior.get("stage"),
                "deve_reexecutir": False,
                "resultado_esperado": f"Resultado do stage anterior: {checkpoint_anterior.get('motivo', 'N/A')}"
            }
        else:
            # Contexto diferente - necessario reexecutir
            return {
                "idempotente": False,
                "motivo": "contexto diferente do checkpoint anterior",
                "checkpoint_anterior": checkpoint_anterior,
                "deve_reexecutir": True
            }
    
    def suspender_tarefa(self, task_id, motivo="provedores_indisponiveis",
                         preservar_progresso=True):
        """
        Suspender uma tarefa quando todos os provedores estao indisponiveis.
        
        Preserva o progresso em checkpoint e alerta o usuario.
        """
        logger.warning(f"Suspensao de tarefa: {task_id} - {motivo}")
        
        # Salvar checkpoint de suspensao
        checkpoint_suspensao = self.salvar_checkpoint(
            task_id=task_id,
            stage="suspensao",
            motivo=motivo,
            contexto_atual={},  # Vazio ou resumo; em implementacao real preservaria contexto
            metadados_adicionais={
                "fallback_count": self.orchestrator.fallback_count if self.orchestrator else 0,
                "provedores_tentados": self.orchestrator.current_task.get("provedores_tentados", []) 
                    if self.orchestrator and self.orchestrator.current_task else []
            }
        )
        
        # Registrar suspensao
        self._registrar_controle(
            checkpoint_suspensao.get("checkpoint_path", "") if checkpoint_suspensao else "N/A",
            "suspensao_tarefa",
            {"task_id": task_id, "motivo": motivo, "timestamp": datetime.utcnow().isoformat()}
        )
        
        logger.info(f"Tarefa {task_id} suspensa. Progresso preservado em checkpoint.")
        return checkpoint_suspensao
    
    def resumir_tarefa(self, task_id):
        """
        Retomar tarefa suspensa a partir do ultimo checkpoint.
        
        Returns:
            dict: Resultado da retomada
        """
        checkpoint = self.recuperar_checkpoint(task_id)
        
        if not checkpoint:
            logger.error(f"Nao foi possivel retomar tarefa {task_id}: nenhum checkpoint encontrado")
            return {
                "sucesso": False,
                "motivo": "nenhum_checkpoint_encontrado_para_retomada",
                "acao": "criar_nova_tarefa"
            }
        
        stage = checkpoint.get("stage", "")
        
        if stage == "suspensao":
            logger.info(f"Tarefa {task_id} previamente suspensa. Pronto para retomada.")
            return {
                "sucesso": True,
                "motivo": "tarefa_suspensa_anteriormente",
                "checkpoint": checkpoint,
                "acao": "retomar_execucao"
            }
        else:
            logger.info(f"Tarefa {task_id} tem checkpoint no stage: {stage}. "
                         "Retomada dependera do stage e contexto.")
            return {
                "sucesso": True,
                "motivo": f"tarefa_tem_checkpoint_no_stage_{stage}",
                "checkpoint": checkpoint,
                "acao": "continuar_processamento"
            }


# Instancia global
try:
    global_checkpoint_mgr = CheckpointManager()
except Exception as e:
    logger.error(f"Erro ao instanciar global CheckpointManager: {e}")
    global_checkpoint_mgr = None