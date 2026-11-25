#!/usr/bin/env python3
"""
Health Monitor - Componente 5 de 15 da AUTO FAILOVER V1.0.2

Monitoramento de disponibilidade, autenticação e falhas, sem chamadas desnecessárias.
Detecta categorias de falha: HTTP 429, cota esgotada, limite de contexto, autenticação,
conexao, timeout, erros 5xx, modelo indisponivel, etc.

Princípios:
- Nao fazer chamadas desnecessarias a provedores saudaveis
- Circuit breaker pattern: abrir circuito depois de N falhas consecutivas
- Retry-After respeitado quando providenciado
- Backoff progressivo com limites
- Registrar todas as detecoes para auditoria
- Nao rotacionar contas para contornar cotas
"""

import json
import os
import logging
import time
import hashlib
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.HealthMonitor')

class HealthMonitor:
    """Monitor de saúde dos provedores de LLM."""
    
    def __init__(self, base_dir=None, registry=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.registry = registry or self._carregar_registro()
        self.config_dir = self.base_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivos de estado do monitor
        self.estado_arquivo = self.base_dir / "data" / "health_estado.json"
        self.log_arquivo = self.base_dir / "logs" / "health_log.jsonl"
        
        # Estado interno: rastreamento de falhas por provedor
        self.falhas_consecutivas = {}  # alias -> contador de falhas consecutivas
        self.sucessas_ultimas = {}     # alias -> contador de sucesso ultimas
        self.circuit_aberto = {}       # alias -> True se circuito aberto
        self.ultima_verificacao = {}   # alias -> timestamp da ultima verificacao
        
        # Limiares (secoes 8 e 9 V1.0.2)
        self.limiar_falhas_circuit_breaker = 3  # Abrir circuito apôs 3 falhas consecutivas
        self.limiar_backoff_base = 5           # Base em segundos para backoff
        self.limiar_backoff_maximo = 60        # Maximo 60 segundos entre retry
        self.max_tentativas_mesmo_provedor = 3  # Nao tentar mais de 3x seguido mesma causa
        
        # Garantir diretorio de dados
        (self.base_dir / "data").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "logs").mkdir(parents=True, exist_ok=True)
        
        # Carregar estado salvo
        self._carregar_estado()
        
        logger.info(f"Health Monitor inicializado. "
                     f"Provedores monitorados: {len(self.falhas_consecutivas)}")
    
    def _carregar_registro(self):
        """Carregar registro de provedores."""
        try:
            from provider_registry import ProviderRegistry
            return ProviderRegistry(self.base_dir)
        except Exception as e:
            logger.error(f"Erro ao carregar registry: {e}")
            class MinimalRegistry:
                provedores = {}
            return MinimalRegistry()
    
    def _carregar_estado(self):
        """Carregar estado salvo de falhas e circuitos."""
        try:
            if self.estado_arquivo.exists():
                with open(self.estado_arquivo, 'r', encoding='utf-8') as f:
                    estado = json.load(f)
                self.falhas_consecutivas = estado.get("falhas_consecutivas", {})
                self.sucessas_ultimas = estado.get("sucessas_ultimas", {})
                self.circuit_aberto = estado.get("circuit_aberto", {})
                # Manter ultima_verificacao como timestamps puros
                self.ultima_verificacao = estado.get("ultima_verificacao", {})
                logger.debug(f"Estado do Health Monitor carregado: "
                              f"falhas={self.falhas_consecutivas}, "
                              f"circuitos={self.circuit_aberto}")
            else:
                logger.info("Nenhum estado salvo anterior encontrado. Iniciando do zero.")
        except Exception as e:
            logger.error(f"Erro ao carregar estado do monitor: {e}. "
                          "Iniciando com estado vazio.")
            self.falhas_consecutivas = {}
            self.sucessas_ultimas = {}
            self.circuit_aberto = {}
            self.ultima_verificacao = {}
    
    def _salvar_estado(self):
        """Salvar estado atual no disco para persistencia entre sessões."""
        try:
            dados = {
                "falhas_consecutivas": self.falhas_consecutivas,
                "sucessas_ultimas": self.sucessas_ultimas,
                "circuit_aberto": self.circuit_aberto,
                "ultima_verificacao": self.ultima_verificacao,
                "timestamp_ultima_atualizacao": datetime.utcnow().isoformat()
            }
            with open(self.estado_arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            
            # Registrar no log de health
            self._registrar_log_health({
                "acao": "estado_salvo",
                "timestamp": datetime.utcnow().isoformat(),
                "total_provedores_monitorados": len(self.falhas_consecutivas)
            })
        except Exception as e:
            logger.error(f"Erro ao salvar estado do monitor: {e}")
    
    def _registrar_log_health(self, entry):
        """Registrar entrada no log de health."""
        try:
            with open(self.log_arquivo, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Erro no log de health: {e}")
    
    def verificar_saude(self, alias_provedor, forcar=False):
        """
        Verificar saúde de um provedor.
        
        Args:
            alias_provedor: alias do provedor a verificar
            forcar: se True, verificar mesmo com circuito aberto
            
        Returns:
            dict com status de saúde e detalhes
        """
        # Verificar circuito breaker
        if not forcar and self.circuit_aberto.get(alias_provedor, False):
            logger.debug(f"Provedor {alias_provedor} com circuito aberto. "
                          "Pular verificação (use forcar=True para override).")
            return {
                "saudavel": False,
                "motivo": "circuit_breaker_aberto",
                "detalhes": "Muitas falhas consecutivas; circuito aberto para prevenir mais falhas.",
                "tempo_recomendado": self._calcular_tempo_recovery(alias_provedor)
            }
        
        # Marcar ultima verificacao
        self.ultima_verificacao[alias_provedor] = datetime.utcnow().isoformat()
        
        # Em implementacao real, aqui faria uma chamada leve ao provedor
        # (ex: modelo info, ou chamada de status da API)
        # Para esta versao simulada, determinamos saude baseada no registro
        
        prov = self.registry.provedores.get(alias_provedor) if self.registry else None
        
        if not prov:
            resultado = {
                "saudavel": False,
                "motivo": "provedor_nao_cadastrado",
                "detalhes": f"Provedor '{alias_provedor}' nao esta cadastrado no Provider Registry."
            }
        else:
            # Lógica de saude baseada no tipo e status do provedor
            tipo = prov.get("tipo", "desconhecido")
            status = prov.get("status", "desconhecido")
            gratuito = prov.get("gratuito", False)
            privado = prov.get("privado", True)
            
            # Verificacoes basicas
            problemas = []
            
            # Se nao e privado e modo privacy exige local -> problema
            if not privado and self._modo_privacy_exige_local():
                problemas.append("Provedor nao-local com politica privacy local-first ativa")
            
            # Se tem cota e pode estar esgotada (apenas alerta, nao bloqueio automatico)
            if gratuito:
                problemas.append("(Alertado: modelo gratuito - cotas podem variar)")
            
            # Status do provedor
            if status == "conectado":
                saudavel = True
                motivo = "Provedor reportado como conectado"
                if problemas:
                    motivo += f". Problemas identificados: {', '.join(problemas)}"
            else:
                saudavel = False
                motivo = f"Provedor com status: {status}"
                if problemas:
                    motivo += f". Problemas: {', '.join(problemas)}"
            
            resultado = {
                "saudavel": saudavel,
                "motivo": motivo,
                "detalhes": {
                    "tipo": tipo,
                    "status": status,
                    "gratuito": gratuito,
                    "privado": privado,
                    "problemas_adicionais": problemas
                }
            }
            
            # Atualizar contadores de falhas/sucessos
            if saudavel:
                self.sucessas_ultimas[alias_provedor] = \
                    self.sucessas_ultimas.get(alias_provedor, 0) + 1
                # Resetar falhas consecutivas se foi saudavel
                self.falhas_consecutivas[alias_provedor] = 0
                # Fechar circuito se estava aberto
                self.circuit_aberto[alias_provedor] = False
            else:
                # Incrementar falhas consecutivas
                self.falhas_consecutivas[alias_provedor] = \
                    self.falhas_consecutivas.get(alias_provedor, 0) + 1
                
                # Verificar se deve abrir circuito
                novas_falhas = self.falhas_consecutivas[alias_provedor]
                if novas_falhas >= self.limiar_falhas_circuit_breaker and not self.circuit_aberto.get(alias_provedor, False):
                    self.circuit_aberto[alias_provedor] = True
                    logger.warning(f"Circuit Breaker ABERTO para {alias_provedor} "
                                  f"após {novas_falhas} falhas consecutivas")
                
                motivo_base = resultado.get("motivo", "Verificacao health monitor")
                resultado["motivo"] = (f"{motivo_base}. "
                                       f"Falhas consecutivas: {novas_falhas}/"
                                       f"{self.limiar_falhas_circuit_breaker}")
            
            # Registrar verificação
            self._registrar_log_health({
                "acao": "verificar_saude",
                "provedor": alias_provedor,
                "saudavel": saudavel,
                "motivo": resultado["motivo"],
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return resultado if 'resultado' in dir() else {"saudavel": False, "motivo": "erro_desconhecido"}
    
    def _modo_privacy_exige_local(self):
        """Verificar se o modo de privacidade atual exige processamento local."""
        modo = self._get_modo_privacy_atual()
        return modo == "local-first"
    
    def _get_modo_privacy_atual(self):
        """Obter modo de privacidade configurado."""
        # Tentar carregar da config do orchestrator ou do config global
        config_path = self.base_dir / "config" / "orchestrator_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config.get("privacy_mode", "local-first")
            except:
                pass
        return "local-first"  # Default
    
    def _calcular_tempo_recovery(self, alias_provedor):
        """Calcular tempo recomendado para recovery (recovery) do circuito aberto."""
        # Backoff progressivo baseado no numero de falhas
        falhas = self.falhas_consecutivas.get(alias_provedor, 0)
        # Exponential backoff: 5s, 10s, 20s, 40s (cap em 60s)
        backoff = min(self.limiar_backoff_base * (2 ** min(falhas - 1, 4)), self.limiar_backoff_maximo)
        return f"{backoff} segundos"
    
    def registrar_falha(self, alias_provedor, categoria_falha, detalhes=None):
        """
        Registrar uma falha observada em um provedor.
        
        Categorias (secao 9 V1.0.2):
        - HTTP 429
        - quota_diaria_esgotada
        - quota_mensal_esgotada
        - limite_temporario_requisicoes
        - limite_tokens_utilizacao
        - limite_contexto
        - falha_autenticacao
        - credencial_expirada
        - falha_conexao
        - timeout
        - erros_http_5xx
        - modelo_indisponivel
        - modelo_descontinuado
        - incompatibilidade_ferramentas
        - resposta_invalida
        - possibilidade_cobranca
        - violacao_permissoes
        - falha_seguranca
        - interrupcao_manual
        """
        # Incrementar falhas consecutivas para este provedor/categoria
        key = f"{alias_provedor}:{categoria_falha}"
        
        # Em implementacao simplificada, usamos o contador geral por provedor
        # e registramos a categoria em detalhes
        if alias_provedor not in self.falhas_consecutivas:
            self.falhas_consecutivas[alias_provedor] = 0
        
        self.falhas_consecutivas[alias_provedor] += 1
        
        # Registrar no log
        self._registrar_log_health({
            "acao": "registrar_falha",
            "provedor": alias_provedor,
            "categoria": categoria_falha,
            "contador_falhas_consecutivas": self.falhas_consecutivas[alias_provedor],
            "detalhes": detalhes or {},
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Verificar se deve abrir circuito baseado na categoria e contador
        self._verificar_circuit_breaker_apos_falha(alias_provedor, categoria_falha)
        
        return {
            "falha_registrada": True,
            "provedor": alias_provedor,
            "categoria": categoria_falha,
            "falhas_consecutivas": self.falhas_consecutivas[alias_provedor]
        }
    
    def _verificar_circuit_breaker_apos_falha(self, alias_provedor, categoria_falha):
        """Verificar e potencialmente abrir circuito breaker apos uma falha."""
        # Contador geral de falhas consecutivas (qualquer categoria)
        total_falhas = self.falhas_consecutivas.get(alias_provedor, 0)
        
        # Tipos de falha que mais rapidamente abrem circuito
        # - falhas de autenticacao (nao retry)
        # - quotas esgotadas (precisa de novo periodo/cota)
        # - erros 5xx (temporarios, mas backend pode estar com problemas)
        
        # Abrir circuito se: falhas consecutivas >= limiar
        # Ou se a categoria e particularmente grave (auth, quota)
        categorias_graves = {"falha_autenticacao", "credencial_expirada", 
                            "quota_diaria_esgotada", "quota_mensal_esgotada"}
        
        categoria_e_grave = categoria_falha in categorias_graves
        
        if total_falhas >= self.limiar_falhas_circuit_breaker or categoria_e_grave:
            if not self.circuit_aberto.get(alias_provedor, False):
                self.circuit_aberto[alias_provedor] = True
                tempo_rec = self._calcular_tempo_recovery(alias_provedor)
                logger.warning(f"Circuit Breaker ABERTO para {alias_provedor} "
                              f"(categoria: {categoria_falha}, falhas: {total_falhas})"
                              f"Tempo recovery recomendado: {tempo_rec}")
                
                # Registrar evento de circuito aberto
                self._registrar_log_health({
                    "acao": "circuit_breaker_aberto",
                    "provedor": alias_provedor,
                    "categoria_gatilho": categoria_falha,
                    "falhas_totais": total_falhas,
                    "tempo_recovery_recomendado": tempo_rec,
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    def resolver_categoria_falha(self, erro_info):
        """
        Dado um erro/Excecao de chamada API, determinar a categoria da falha.
        
        Args:
            erro_info: dict ou excecao com informacoes do erro
            
        Returns:
            str: categoria da falha (string consistente com as descritas acima)
        """
        if not erro_info:
            return "falha_nao_info"
        
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
        
        # Lógica de classificacao de falhas (ordem de prioridade)
        
        # 1. HTTP 429 - Rate Limit
        if status == 429 or (code and code == 429) or "retry-after" in mensagem:
            return "HTTP 429"
        
        # 2. Cota diária esgotada
        if any(kw in mensagem for kw in ["daily quota", "daily_limit", "quota diaria",
                                           "limite diario", "daily limit exceeded"]):
            return "quota_diaria_esgotada"
        
        # 3. Cota mensal esgotada
        if any(kw in mensagem for kw in ["monthly quota", "monthly_limit", "quota mensal",
                                          "limite mensal", "monthly limit exceeded"]):
            return "quota_mensal_esgotada"
        
        # 4. Limite temporario de requisicoes (429 com retry-after diferente)
        if status == 429 and "retry-after" in mensagem:
            retry_after = erro_info.get("retry_after", 0)
            if retry_after and int(retry_after) < 3600:  # Menos que 1 hora
                return "limite_temporario_requisicoes"
        
        # 5. Limite de tokens de utilizacao
        if any(kw in mensagem for kw in ["token limit", "token quota", "contexto excedido",
                                           "context window", "max tokens exceeded"]):
            return "limite_tokens_utilizacao"
        
        # 6. Limite da janela de contexto
        if any(kw in mensagem for kw in ["context window", "janela de contexto",
                                           "context length exceeded"]):
            return "limite_contexto"
        
        # 7. Falha de autenticacao
        if any(kw in mensagem for kw in ["authentication failed", "auth failed", 
                                          "invalid api key", "invalid_key", "autenticao falhou",
                                          "401", "unauthorized"]):
            return "falha_autenticacao"
        
        # 8. Credencial expirada
        if any(kw in mensagem for kw in ["credential expired", "expired key", "token expirado",
                                          "expired token", "401 credencial expirada"]):
            return "credencial_expirada"
        
        # 9. Falha de conexao
        if any(kw in mensagem for kw in ["connection failed", "connection error", 
                                          "unreachable", "network error", "timeout"]):
            return "falha_conexao"
        
        # 10. Timeout
        if any(kw in mensagem for kw in ["timeout", "time out", "request timed out"]):
            return "timeout"
        
        # 11. Erros HTTP 5xx
        if status and isinstance(status, int) and 500 <= status < 600:
            return "erros_http_5xx"
        
        # 12. Modelo indisponivel
        if any(kw in mensagem for kw in ["model unavailable", "model not available",
                                          "modelo nao disponivel", "model out of service"]):
            return "modelo_indisponivel"
        
        # 13. Modelo descontinuado
        if any(kw in mensagem for kw in ["model discontinued", "modelo descontinuado",
                                          "deprecated model", "modelo deprecated"]):
            return "modelo_descontinuado"
        
        # 14. Incompatibilidade com ferramentas
        if any(kw in mensagem for kw in ["tools not supported", "ferramentas nao suportadas",
                                          "incompatible with tools", "tool_choice nao valido"]):
            return "incompatibilidade_ferramentas"
        
        # 15. Resposta inválida
        if any(kw in mensagem for kw in ["invalid response", "resposta invalida",
                                          "malformed response"]):
            return "resposta_invalida"
        
        # 16. Possibilidade de cobranca
        if any(kw in mensagem for kw in ["cost", "cobranca", "faturamento", "billing",
                                          "pay-per-use", "estimated cost"]):
            return "possibilidade_cobranca"
        
        # 17. Violação de permissões
        if any(kw in mensagem for kw in ["permission denied", "acesso negado",
                                          "forbidden", "403", "violacao permissao"]):
            return "violacao_permissoes"
        
        # 18. Falha de segurança
        if any(kw in mensagem for kw in ["security", "seguranca", "security error",
                                          "security violation"]):
            return "falha_seguranca"
        
        # 19. Interrupção manual
        if any(kw in mensagem for kw in ["interrupt", "manual interrupt", 
                                          "interrupt manual", "stopped by user"]):
            return "interrupcao_manual"
        
        # 20. Fallback para nao classificado
        return "nao_classificado"
    
    def get_estado_resumo(self):
        """Retornar resumo do estado atual do monitor."""
        total_provedores = len(self.falhas_consecutivas)
        circuitos_abertos = sum(1 for v in self.circuit_aberto.values() if v)
        
        return {
            "total_provedores_monitorados": total_provedores,
            "provedores_com_circuit_aberto": circuitos_abertos,
            "falhas_consecutivas_por_provedor": self.falhas_consecutivas,
            "sucessas_ultimas_por_provedor": self.sucessas_ultimas,
            "ultima_verificacao": self.ultima_verificacao,
            "limiar_circuit_breaker": self.limiar_falhas_circuit_breaker,
            "backoff_base_segundos": self.limiar_backoff_base,
            "backoff_maximo_segundos": self.limiar_backoff_maximo
        }
    
    def resetar_falhas_provedor(self, alias_provedor):
        """Resetar contador de falhas para um provedor (após recuperacao bem-sucedida)."""
        if alias_provedor in self.falhas_consecutivas:
            logger.info(f"Resetando falhas do provedor {alias_provedor}")
            self.falhas_consecutivas[alias_provedor] = 0
        
        if alias_provedor in self.circuit_aberto:
            self.circuit_aberto[alias_provedor] = False
            logger.info(f"Fechando circuit breaker para {alias_provedor}")
        
        if alias_provedor in self.sucessas_ultimas:
            self.sucessas_ultimas[alias_provedor] = 0
        
        # Salvar estado
        self._salvar_estado()
        
        return True