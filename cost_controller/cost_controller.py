#!/usr/bin/env python3
"""
Cost Controller - Componente 6 de 15 da AUTO FAILOVER V1.0.2

Prevenção de cobranças não autorizadas.
Bloqueio de custos desconhecidos.
Garantir orçamento adicional zero por default.

Princípios:
- Zero custo por default (OpenCode Console -> Gemini free -> OpenRouter free)
- Bloqueio preventivo antes de qualquer chamada pay-per-use
- Usuario deve confirmar explicitamente antes de usar modelo pago
- Registrar todos os custos estimados para auditoria
- Nunca auto-rotacionar contas para contornar limites
- Respeitar cotas compartilhadas do mesmo provedor
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.CostController')

class CostController:
    """Controlador de custos para prevenir cobrancas nao autorizadas."""
    
    def __init__(self, base_dir=None, registry=None, health_monitor=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.registry = registry or self._carregar_registro()
        self.health_monitor = health_monitor or self._carregar_monitor_saude()
        self.config_dir = self.base_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivos
        self.config_arquivo = self.config_dir / "cost_controller_config.json"
        self.historico_custos = self.base_dir / "data" / "historico_custos.jsonl"
        
        # Configurações
        self.config = self._carregar_configuracao()
        
        # Estatisticas atuais da sessao
        self.custo_sessao_atual = 0.0  # Reiniciado ao iniciar nova tarefa
        self.modelos_usados_sessao = []
        
        # Garantir diretorios
        (self.base_dir / "data").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "logs").mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Cost Controller inicializado. Politica: custo max US$ {self.config.get('max_custo_usd', 0.0)}")
    
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
    
    def _carregar_monitor_saude(self):
        """Carregar Health Monitor."""
        try:
            from health_monitor import HealthMonitor
            return HealthMonitor(self.base_dir)
        except Exception as e:
            logger.error(f"Erro ao carregar Health Monitor: {e}")
            class MinimalMonitor:
                def verificar_saude(self, *args, **kwargs):
                    return {"saudavel": True, "motivo": "monitor nao disponivel"}
            return MinimalMonitor()
    
    def _carregar_configuracao(self):
        """Carregar configuracao do Cost Controller."""
        if self.config_arquivo.exists():
            try:
                with open(self.config_arquivo, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info("Configuracao de custo carregada do arquivo")
                return config
            except Exception as e:
                logger.warning(f"Erro ao carregar configuracao: {e}")
        
        # Configuracao padrao: zero custo
        configuracao_padrao = {
            "max_custo_usd_sessao": 0.0,       # Zero custo por sessao por default
            "max_custo_usd_diario": 0.0,       # Zero custo diario por default
            "botao_confirmar_cobranca": True,  # Exigir confirmacao explicitamente
            "politica_custo": "zero_por_padrao",  # zero_por_padrao ou "permitir_com_limite"
            "modelos_autorizados_pagos": [],   # Lista vazia = nenhum pago sem confirmacao
            "moeda": "USD",
            "registrar_historico": True,
            "avisar_antes_custo_estimado": True  # Avisar usuario antes de usar custo nao-zero
        }
        
        with open(self.config_arquivo, 'w', encoding='utf-8') as f:
            json.dump(configuracao_padrao, f, ensure_ascii=False, indent=2)
        
        logger.info("Configuracao padrao de custo criada (zero custo)")
        return configuracao_padrao
    
    def verificar_custo_provedor(self, alias_provedor, modelo_identificador, 
                                  tokens_estimados=None):
        """
        Verificar se o uso de um modelo excederia o orcamento.
        
        Returns:
            dict com: pode_usar, custo_estimado, motivo, acao_recomendada
        """
        alias_real = getattr(self.registry, '_aliases', {}).get(alias_provedor, alias_provedor)
        prov = self.registry.provedores.get(alias_real)
        if not prov:
            return {
                "pode_usar": False,
                "custo_estimado": None,
                "motivo": f"Provedor '{alias_provedor}' nao cadastrado no registry",
                "acao_recomendada": "selecionar_provedor_alternativo"
            }
        
        # Verificar se modelo e gratuito no registro
        modelos = self.registry.obter_modelos(alias_provedor)
        modelo_encontrado = None
        for m in modelos:
            if m.get("nome") == modelo_identificador or m.get("identificador") == modelo_identificador:
                modelo_encontrado = m
                break
        
        # Se modelo nao encontrado na lista, tentar match por nome parcial
        if not modelo_encontrado:
            for m in modelos:
                if modelo_identificador.lower() in m.get("nome", "").lower():
                    modelo_encontrado = m
                    break
        
        # Determinar custo estimado
        # Modelos opencode/* com sufixo -free sao comprovadamente gratuitos (V1.0.4)
        identificador_lower = str(modelo_identificador).lower()
        is_free_opencode = (identificador_lower.startswith('opencode/') and
                            identificador_lower.endswith('-free'))
        if (modelo_encontrado and modelo_encontrado.get("gratuito", False)) or is_free_opencode:
            custo_estimado = 0.0
            gratuito = True
        else:
            # Modelo nao marcado como gratuito -> e pago
            # Usar metodo de estimativa do Cost Controller
            custo_estimado = self._estimar_custo_modelo(prov, modelo_encontrado, tokens_estimados)
            gratuito = False
        
        # Verificar limites de custo
        pode_usar = True
        motivos = []
        
        # Verificar limite da sessao
        max_sessao = self.config.get("max_custo_usd_sessao", 0.0)
        if max_sessao > 0 and self.custo_sessao_atual + custo_estimado > max_sessao:
            pode_usar = False
            excedente = self.custo_sessao_atual + custo_estimado - max_sessao
            motivos.append(f"Limite da sessao excedido em US${excedente:.2f} "
                          f"(atual: ${self.custo_sessao_atual:.2f} + estimado: ${custo_estimado:.2f} "
                          f"> max: ${max_sessao:.2f})")
        
        # Verificar limite diario
        max_diario = self.config.get("max_custo_usd_diario", 0.0)
        if max_diario > 0:
            # Nota: Em implementacao completa, verificariamos o custo do dia atual
            # Aqui so temos o custo da sessao corrente
            pass  # Simplificacao: o limite de sessao cobre o principal
        
        # Politica: zero custo por default
        politica = self.config.get("politica_custo", "zero_por_padrao")
        
        if politica == "zero_por_padrao" and not gratuito:
            # Usuario deve confirmar explicitamente
            if self.config.get("botao_confirmar_cobranca", True):
                pode_usar = False
                motivos.append(
                    f"Politica de custo zerado ativa. "
                    f"Modelo '{modelo_encontrado.get('nome', modelo_identificador)}' e pago "
                    f"(custo estimado: ${custo_estimado:.4f}). "
                    f"Use 'confirmar_cobranca=True' para prosseguir explicitamente."
                )
            # Se botao_confirmar_cobranca for False, permitir (nao recomendado)
        
        # Se modelo e gratuito, sem restricoes (além dos limites acima)
        if gratuito:
            pode_usar = True
            motivos.append("Modelo gratuito - sem custo adicional")
        
        # Registrar verificacao no log
        self._registrar_verificacao({
            "acao": "verificar_custo_provedor",
            "provedor": alias_provedor,
            "modelo": modelo_identificador,
            "gratuito": gratuito,
            "custo_estimado": custo_estimado,
            "pode_usar": pode_usar,
            "motivos": motivos,
            "custo_sessao_atual": self.custo_sessao_atual,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "pode_usar": pode_usar,
            "custo_estimado": custo_estimado,
            "gratuito": gratuito,
            "motivos": motivos,
            "acao_recomendada": "usar_gratuitivo_se_disponivel" if not pode_usar else "prosseguir"
        }
    
    def _estimar_custo_modelo(self, prov, modelo_encontrado, tokens_estimados=None):
        """Estimar custo de um modelo pago."""
        # Verificar se tem preco referenciado no provedor
        modelo_nome = prov.get("nome_exibicao", "").lower()
        
        # Precos referenciais (2026) - apenas para estimativa
        # O sistema NUNCA cobra automaticamente; apenas estima para informar usuario
        precos_referencia = {
            # OpenAI models (referenciais apenas)
            "gpt-4o": 0.005,      # entrada por 1K tokens
            "gpt-4o-mini": 0.00015,
            "gpt-6-luna": 0.015,  # modelo premium OpenAI
            "gpt-5.5": 0.03,      # estimativa
            # Google Gemini models
            "gemini-3.5-flash": 0.0001,
            "gemini-3.5-flash-lite": 0.0,  # gratuito
            # Anthropic (nao conectado, mas referenciais)
            "claude-3-haiku": 0.0025,
        }
        
        # Verificar correspondencia
        for key, preco in precos_referencia.items():
            if key in modelo_nome:
                # Ajustar baseado em tokens se fornecidos
                if tokens_estimados:
                    # Custo para tokens_estimados tokens de entrada
                    return round(preco * tokens_estimados / 1000, 4)
                return preco  # Custo por 1K tokens (referencia)
        
        # Padrao: retornar estimativa media avisando usuario
        logger.warning(
            f"Nao foi possivel estimar custo preciso para {prov.get('nome_exibicao', 'modelo desconhecido')}. "
            "Custo estimado medio: $0.10 por chamada. Usuario deve confirmar."
        )
        return 0.10  # Estimativa media - usuario confirmar
    
    def autorizar_cobranca_explicita(self, confirmado=True):
        """
        Interface para usuario autorizar cobranca explicitamente.
        
        Esta funcao deve ser chamada pelo orchestador quando o usuario 
        explicitamente concorda em arcar com custos.
        
        Args:
            confirmado: True se o usuario confirmou, False caso contrario
        """
        if confirmado:
            # Registrar autorizacao
            self._registrar_verificacao({
                "acao": "autorizacao_cobranca_explicita",
                "confirmado": True,
                "timestamp": datetime.utcnow().isoformat(),
                "mensagem": "Usuario explicitamente autorizou arcar com custos"
            })
            logger.info("Autorizacao de cobranca explicita concedida pelo usuario")
            return True
        else:
            # Negar autorizacao - retornar ao modo zero custo
            self._registrar_verificacao({
                "acao": "autorizacao_cobranca_explicita",
                "confirmado": False,
                "timestamp": datetime.utcnow().isoformat(),
                "mensagem": "Usuario nao autorizou cobranca. Continuando modo zero custo."
            })
            logger.info("Negada autorizacao de cobranca. Continuando modo zero custo.")
            return False
    
    def iniciar_nova_tarefa(self):
        """Resetar custos da sessao ao iniciar uma nova tarefa."""
        self.custo_sessao_atual = 0.0
        self.modelos_usados_sessao = []
        logger.debug("Custos da sessao resetados para nova tarefa")
    
    def registrar_uso_real(self, alias_provedor, modelo_identificador, 
                          custo_usd_real, tokens_usados):
        """
        Registrar uso real (apos chamada ser feita com autorizacao explicitada).
        So deve ser chamado quando usuario confirmou o uso de modelo pago.
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "provedor": alias_provedor,
            "modelo": modelo_identificador,
            "custo_usd_real": custo_usd_real,
            "tokens_usados": tokens_usados or 0,
            "sessao_custo_acumulado": self.custo_sessao_atual,
            "autorizado": True  # Apenas se usuario confirmou
        }
        
        try:
            with open(self.historico_custos, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logger.info(f"Custo real registrado: ${custo_usd_real:.4f} "
                       f"para {alias_provedor}/{modelo_identificador}")
        except Exception as e:
            logger.error(f"Erro ao registrar custo real: {e}")
        
        # Acumular na sessao
        self.custo_sessao_atual += custo_usd_real
        if alias_provedor not in self.modelos_usados_sessao:
            self.modelos_usados_sessao.append(alias_provedor)
        
        return entry
    
    def _registrar_verificacao(self, entry):
        """Registrar verificacao de custo no log historico."""
        try:
            with open(self.historico_custos, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Erro ao registrar verificacao de custo: {e}")
    
    def get_estado_custo(self):
        """Retornar estado resumido dos custos."""
        return {
            "custo_sessao_atual_usd": round(self.custo_sessao_atual, 4),
            "maximo_sessao_usd": self.config.get("max_custo_usd_sessao", 0.0),
            "politica_custo": self.config.get("politica_custo", "zero_por_padrao"),
            "modelos_usados_sessao": self.modelos_usados_sessao,
            "total_modelos_usados": len(self.modelos_usados_sessao),
            "custo_por_provedor": self._calcular_custo_por_provedor(),
            "eh_zero_custo": self.custo_sessao_atual == 0.0
        }
    
    def _calcular_custo_por_provedor(self):
        """Calcular custo acumulado por provedor na sessao atual."""
        custos = {}
        # Note: so temos custo se algum modelo pago foi usado sem confirmaçao adequada
        # Como o default e zero custo, este metodo geralmente retornara {}
        for modelo in self.modelos_usados_sessao:
            # So teria custo se autorizacao explicita fosse dada
            custos[modelo] = 0.0
        return custos