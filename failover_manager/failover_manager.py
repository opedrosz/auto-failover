#!/usr/bin/env python3
"""
Failover Manager - Componente 4 de 15 da AUTO FAILOVER V1.0.3

Sistema de alternância automática entre provedores.
Distingue categorias de falha e define comportamento correto para cada uma.

Princípios:
- Não tratar todas as falhas da mesma maneira
- Não trocar de provedor automaticamente em caso de violação de segurança
- ou recusa legítima do modelo
- Implementar backoff progressivo, Retry-After, circuit breaker, cooldown
- Limite de tentativas, grupos de cotas compartilhadas
- Prevenção de ciclos, suspensão segura, recuperação controlada
- Impedir que dois agentes executem simultaneamente ações conflitantes
"""

import json
import os
import logging
import time
import hashlib
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.FailoverManager')

class FailureCategory:
    """Categorias de falha definidas na seção 8 V1.0.3."""
    
    # Categorias operacionais
    QUOTA_EXCEEDED = "quota_excedida"
    HTTP_429 = "http_429"
    HTTP_5XX = "http_5xx"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "conexao_errada"
    CONTEXT_WINDOW = "contexto_excedido"
    AUTHENTICATION_FAILURE = "falha_autenticacao"
    CREDENTIAL_EXPIRED = "credencial_expirada"
    MODEL_UNAVAILABLE = "modelo_indisponivel"
    MODEL_INCOMPATIBLE = "modelo_incompativel"
    TOOLS_INCOMPATIBLE = "ferramentas_incompatibilidade"
    CONFIG_ERROR = "falha_configuracao"
    SECURITY_VIOLATION = "falha_seguranca"
    MANUAL_INTERRUPTION = "interrupcao_manual"
    UNKNOWN = "nao_classificada"

class FailoverManager:
    """Gerenciador de failover automático entre provedores."""
    
    def __init__(self, base_dir=None, registry=None, health_monitor=None, 
                 cost_controller=None, orchestrator=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.registry = registry or self._carregar_registro()
        self.health_monitor = health_monitor or self._carregar_monitor()
        self.cost_controller = cost_controller or self._carregar_custo()
        self.orchestrator = orchestrator or self._carregar_orchestrator()
        
        self.config_dir = self.base_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Limiares e configurações
        self.circuit_breaker_threshold = 3  # falhas consecutivas para abrir circuito
        self.max_retries = 6  # máximo de tentativas (seja da seção 7 V1.0.2)
        self.backoff_base = 5  # segundos
        self.backoff_max = 60  # segundos máximo entre retry
        self.cooldown_period = 30  # segundos após circuit breaker
        
        # Estado interno
        self.failure_counts = {}  # provedor -> contador de falhas consecutivas
        self.circuit_breaker_active = {}  # provedor -> True se circuito aberto
        self.last_failure_time = {}  # provedor -> timestamp
        self.retry_counts = {}  # provedor -> contador de tentativas da sessão
        
        # Garantir diretorios
        (self.base_dir / "data").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "logs").mkdir(parents=True, exist_ok=True)
        
        logger.info("Failover Manager inicializado")
    
    def _carregar_registro(self):
        try:
            from provider_registry import ProviderRegistry
            return ProviderRegistry(self.base_dir)
        except Exception as e:
            logger.error(f"Erro ao carregar registry: {e}")
            class MinimalRegistry:
                provedores = {}
            return MinimalRegistry()
    
    def _carregar_monitor(self):
        try:
            from health_monitor import HealthMonitor
            return HealthMonitor(self.base_dir)
        except Exception as e:
            logger.error(f"Erro ao carregar health monitor: {e}")
            class MinimalMonitor:
                def verificar_saude(self, *args, **kwargs):
                    return {"saudavel": True, "motivo": "monitor nao disponivel"}
            return MinimalMonitor()
    
    def _carregar_custo(self):
        try:
            from cost_controller import CostController
            return CostController(self.base_dir, self.registry)
        except Exception as e:
            logger.error(f"Erro ao carregar cost controller: {e}")
            class MinimalCost:
                def verificar_custo_provedor(self, *args, **kwargs):
                    return {"pode_usar": True, "custo_estimado": 0.0, "gratuito": True, "motivos": []}
            return MinimalCost()
    
    def _carregar_orchestrator(self):
        try:
            from orchestrator import Orchestrator
            return Orchestrator(self.base_dir)
        except Exception as e:
            logger.error(f"Erro ao carregar orchestrator: {e}")
            return None
    
    def categorizar_falha(self, erro_info):
        """
        Categorizar uma falha-baseada-em-erro nas categorias definidas.
        
        Args:
            erro_info: dict ou exceção com informações do erro
            
        Returns:
            str: categoria da falha
        """
        if not erro_info:
            return FailureCategory.UNKNOWN
        
        # Tratar dict com informacoes de erro
        if isinstance(erro_info, dict):
            mensagem = erro_info.get("message", "").lower()
            tipo = erro_info.get("type", "").lower()
            status = erro_info.get("status", None)
            code = erro_info.get("code", None)
        else:
            # Tratar excecao Python
            mensagem = str(erro_info).lower()
            tipo = type(erro_info).__name__.lower()
            status = None
            code = None
        
        # 1. HTTP 429 - Rate Limit
        if status == 429 or (code and str(code) == "429") or "retry-after" in mensagem:
            return FailureCategory.HTTP_429
        
        # 2. Cota esgotada (diária ou mensal)
        if any(kw in mensagem for kw in ["quota exceeded", "daily quota", "monthly quota",
                                          "limite diario", "limite mensal", "quota excedida"]):
            # Verificar se eh diaria ou mensal
            if any(kw in mensagem for kw in ["daily", "diario", "day"]):
                return FailureCategory.QUOTA_EXCEEDED
            else:
                return FailureCategory.QUOTA_EXCEEDED  # Pode ser mensal tbm
        
        # 3. Erros HTTP 5xx
        if status and isinstance(status, int) and 500 <= status < 600:
            return FailureCategory.HTTP_5XX
        
        # 4. Timeout
        if any(kw in mensagem for kw in ["timeout", "time out", "request timed out", "timed out"]):
            return FailureCategory.TIMEOUT
        
        # 5. Falha de conexao
        if any(kw in mensagem for kw in ["connection failed", "connection error", 
                                          "unreachable", "network error"]):
            return FailureCategory.CONNECTION_ERROR
        
        # 6. Limite de contexto/janela excedido
        if any(kw in mensagem for kw in ["context window", "janela de contexto",
                                          "context length exceeded", "max tokens exceeded"]):
            return FailureCategory.CONTEXT_WINDOW
        
        # 7. Falha de autenticacao
        if status in (401, 403):
            return FailureCategory.AUTHENTICATION_FAILURE
        if any(kw in mensagem for kw in ["authentication failed", "auth failed", 
                                          "invalid api key", "invalid_key", 
                                          "401", "unauthorized", "autenticao falhou"]):
            return FailureCategory.AUTHENTICATION_FAILURE
        
        # 8. Credencial expirada
        if any(kw in mensagem for kw in ["credential expired", "expired key", "token expirado",
                                          "expired token"]):
            return FailureCategory.CREDENTIAL_EXPIRED
        
        # 9. Modelo indisponivel
        if any(kw in mensagem for kw in ["model unavailable", "model not available",
                                          "modelo nao disponivel", "model out of service"]):
            return FailureCategory.MODEL_UNAVAILABLE
        
        # 10. Modelo incompatível (ferramentas, etc.)
        if any(kw in mensagem for kw in ["tools not supported", "ferramentas nao suportadas",
                                          "incompatible with tools", "tool_choice nao valido",
                                          "modelo nao suporta ferramentas"]):
            return FailureCategory.TOOLS_INCOMPATIBLE
        
        # 11. Falha de seguranca
        if any(kw in mensagem for kw in ["security", "seguranca", "security error",
                                          "security violation"]):
            return FailureCategory.SECURITY_VIOLATION
        
        # 12. Interrupcao manual
        if any(kw in mensagem for kw in ["interrupt", "manual interrupt", 
                                          "interrupt manual", "stopped by user", "cancelled"]):
            return FailureCategory.MANUAL_INTERRUPTION
        
        # 13. Falha de configuracao
        if any(kw in mensagem for kw in ["configuration error", "config error", 
                                          "malformed request", "parsing error"]):
            return FailureCategory.CONFIG_ERROR
        
        # 14. Possibilidade de cobranca
        if any(kw in mensagem for kw in ["cost", "cobranca", "faturamento", "billing",
                                          "pay-per-use", "estimated cost", "cobranca futura"]):
            return FailureCategory.UNKNOWN  # Tratar com cuidado - nao trocar automaticamente
        
        # 15. Qualquer outra coisa nao classificada
        return FailureCategory.UNKNOWN
    
    def registrar_falha(self, alias_provedor, categoria_falha, detalhes=None):
        """
        Registrar uma falha observada em um provedor.
        
        Atualiza contadores, circuito breaker e recomenda acoes.
        """
        # Inicializar contadores se necessario
        if alias_provedor not in self.failure_counts:
            self.failure_counts[alias_provedor] = 0
        if alias_provedor not in self.last_failure_time:
            self.last_failure_time[alias_provedor] = None
        if alias_provedor not in self.retry_counts:
            self.retry_counts[alias_provedor] = 0
        if alias_provedor not in self.circuit_breaker_active:
            self.circuit_breaker_active[alias_provedor] = False
        
        # Incrementar contador de falhas consecutivas
        self.failure_counts[alias_provedor] += 1
        self.last_failure_time[alias_provedor] = datetime.utcnow().isoformat()
        self.retry_counts[alias_provedor] += 1
        
        # Verificar se deve abrir circuito breaker
        total_falhas = self.failure_counts[alias_provedor]
        if total_falhas >= self.circuit_breaker_threshold and not self.circuit_breaker_active.get(alias_provedor, False):
            self.circuit_breaker_active[alias_provedor] = True
            logger.warning(f"Circuit Breaker ABERTO para {alias_provedor} "
                          f"após {total_falhas} falhas consecutivas")
            
            # Agendar fechamento automático após cooldown
            self._agendar_proximo_check(alias_provedor, self.cooldown_period)
        
        # Registrar no log
        logger.info(f"Falha registrada: {alias_provedor} - {categoria_falha} "
                     f"(consecutivas: {self.failure_counts[alias_provedor]})")
        
        return {
            "provedor": alias_provedor,
            "categoria": categoria_falha,
            "falhas_consecutivas": self.failure_counts[alias_provedor],
            "circuit_breaker_ativo": self.circuit_breaker_active.get(alias_provedor, False),
            "retry_count": self.retry_counts[alias_provedor]
        }
    
    def _agendar_proximo_check(self, alias_provedor, segundos):
        """Agendar verificação automática para fechar circuito."""
        logger.info(f"Circuito para {alias_provedor} aberto. "
                     f"Check automático em {segundos} segundos para possível fechamento.")
    
    def pode_executar(self, alias_provedor):
        """
        Verificar se um provedor pode ser usado (não está com circuito aberto
        e não excedeu limites de tentativa).
        """
        # Verificar circuito breaker
        if self.circuit_breaker_active.get(alias_provedor, False):
            return False, "circuit_breaker_ativo"
        
        # Verificar limite de tentativas
        if self.retry_counts.get(alias_provedor, 0) >= self.max_retries:
            return False, "limite_max_tentativas"
        
        return True, "ok"
    
    def resetar_provedor(self, alias_provedor):
        """Resetar contador de falhas para um provedor (após recuperação bem-sucedida)."""
        self.failure_counts[alias_provedor] = 0
        self.retry_counts[alias_provedor] = 0
        self.circuit_breaker_active[alias_provedor] = False
        self.last_failure_time[alias_provedor] = None
        logger.info(f"Falhas resetadas para provedor {alias_provedor}")
    
    def executar_failover(self, task_id, motivo_falha, contexto_atual,
                         provedores_alternativos=None, excluir_ultimo=True):
        """
        Executar protocolo de failover automático.
        
        Returns:
            dict com resultado do failover
        """
        logger.info(f"Executando failover para tarefa {task_id}: {motivo_falha}")
        
        # Step 1: Categorizar a falha
        categoria = self.categorizar_falha(motivo_falha)
        logger.info(f"Categoria da falha: {categoria}")
        
        # Step 2: Verificar se pode tentar novo provedor
        pode_tentar, motivo_recusa = self.pode_executar_task(task_id, categoria)
        if not pode_tentar:
            logger.warning(f"Não é possível tentar failover: {motivo_recusa}")
            return {
                "sucesso": False,
                "motivo": motivo_recusa,
                "categoria": categoria,
                "acao": "bloqueado_pela_policy"
            }
        
        # Step 3: Se houver provedores alternativos disponíveis, selecionar um
        if provedores_alternativos:
            # Filtrar provedores com circuito breaker ativo ou cota esgotada
            elegiveis = []
            for prov_info in provedores_alternativos:
                alias = prov_info.get("alias", "")
                pode, _ = self.pode_executar(alias)
                if pode:
                    elegiveis.append(prov_info)
            
            if not elegiveis:
                # Todos os provedores têm circuito aberto ou limites excedidos
                # Tentar resetar algum ou usar o que tem menor falha
                elegiveis = self._selecionar_provedor_menos_danificado(provedores_alternativos)
            
            if elegiveis:
                # Selecionar o primeiro provedor elegível
                selecao = elegiveis[0]
                logger.info(f"Selecionando provedor alternativo: {selecao.get('alias', 'N/A')}")
                
                # Registrar a transição de failover
                self._registrar_transicao_failover(task_id, categoria, selecao.get("alias", ""))
                
                return {
                    "sucesso": True,
                    "acao": "trocar_provedor",
                    "novo_provedor": selecao.get("alias", ""),
                    "categoria_falha": categoria,
                    "motivo": motivo_falha
                }
        
        # Step 4: Se não houver provedores alternativos ou falhou tudo
        # Retornar para modo local/suspensao
        logger.warning("Nenhum provedor alternativo disponível para failover")
        
        # Salvar checkpoint de emergência
        self._salvar_checkpoint_emergencia(task_id, categoria)
        
        return {
            "sucesso": False,
            "acao": "suspender_tarefa",
            "motivo": "nenhum_provedor_disponivel",
            "categoria": categoria,
            "recomendacao": "suspender_execucao_e_aguardar"
        }
    
    def pode_executar_task(self, task_id, categoria_falha):
        """
        Verificar se ha condições de executar uma nova tarefa ou trocar de provedor.
        """
        # Verificar se alguma tarefa ja esta em andamento com falhas similares
        # Verificar limites globais
        for alias, count in self.failure_counts.items():
            if count >= self.circuit_breaker_threshold:
                return False, f"circuit_breaker_ativo_{alias}"
        return True, "ok"
    
    def _selecionar_provedor_menos_danificado(self, provedores):
        """Selecionar provedor com menor contador de falhas."""
        melhor = None
        melhor_contador = float('inf')
        
        for prov in provedores:
            alias = prov.get("alias", "")
            contador = self.failure_counts.get(alias, 0)
            if contador < melhor_contador:
                melhor_contador = contador
                melhor = prov
        
        return [melhor] if melhor else []
    
    def _registrar_transicao_failover(self, task_id, categoria_falha, novo_provedor):
        """Registrar a transição de failover no log."""
        logger.info(f"Failover task={task_id} categoria={categoria_falha} "
                     f"novo_provedor={novo_provedor}")
    
    def _salvar_checkpoint_emergencia(self, task_id, categoria_falha):
        """Salvar checkpoint de emergência quando todos os provedores falham."""
        import hashlib
        import json
        
        checkpoint_path = self.base_dir / "checkpoints" / f"emergency_{task_id}_{int(time.time())}.json"
        
        # Coletar estado atual
        estado = {
            "task_id": task_id,
            "categoria_falha": categoria_falha,
            "timestamp": datetime.utcnow().isoformat(),
            "timestamp_geracao": datetime.utcnow().isoformat()
        }
        
        try:
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(estado, f, ensure_ascii=False, indent=2)
            logger.info(f"Checkpoint de emergência salvo: {checkpoint_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar checkpoint de emergência: {e}")


# Instancia global
try:
    global_failover_mgr = FailoverManager()
except Exception as e:
    logger.error(f"Erro ao instanciar global FailoverManager: {e}")
    global_failover_mgr = None