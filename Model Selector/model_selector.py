#!/usr/bin/env python3
"""
Model Selector - Componente 3 de 15 da AUTO FAILOVER V1.0.2

Seleção inteligente conforme a tarefa, custo, disponibilidade e compatibilidade.
Decide qual modelo/provedor usar baseado nas requisições da tarefa e no
estado atual da infraestrutura.

Princípios:
- Zero custo por default
- Compatibilidade com requisitos da tarefa
- Verificar compatibilidade antes de selecionar
- NÃO selecionar modelos pagos se houver alternativa gratuita
- Usar recursos nativos do OpenCode antes de criações redundantes
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.ModelSelector')

class ModelSelector:
    """Seletor inteligente de modelos baseado em requisitos da tarefa."""
    
    def __init__(self, base_dir=None, registry=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.registry = registry or self._carregar_registro()
        self.config_dir = self.base_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Carregar config de selecao
        self.config = self._carregar_configuracao_selecao()
        
        logger.info(f"Model Selector inicializado. {len(self.registry.provedores)} provedores "
                     f"disponíveis no registro.")
    
    def _carregar_registro(self):
        """Carregar Provider Registry."""
        from provider_registry import ProviderRegistry
        try:
            return ProviderRegistry(self.base_dir)
        except Exception as e:
            logger.error(f"Erro ao carregar Provider Registry: {e}")
            # Retornar objeto minimos
            class MinimalRegistry:
                provedores = {}
                modelos = {}
            return MinimalRegistry()
    
    def _carregar_configuracao_selecao(self):
        """Carregar configuração de seleção de modelos."""
        config_path = self.config_dir / "model_selector_config.json"
        default_config = {
            "priority_strategy": "custo_primeiro",  # custo_primeiro ou desempenho_primeiro
            "min_cost_usd": 0.0,  # Custo minimo aceitavel
            "max_cost_usd": 0.0,  # Custo maximo (0 = zero custo por default)
            "privacy_mode": "local-first",  # local-first, opt-in-cloud, qualquer
            "requisitos_padrao": {
                "ferramentas": False,
                "visao": False,
                "programacao": True,
                "contexto_maximo_minimo": 1024,
                "privado": True
            },
            "preferir_nativo_opencode": True,
            "evitar_modelos_pagos": True,  # Se True, nao selecionar pago se ha gratuito
            "fallback_automatico": True,
            "max_tentativas_fallback": 6  # Igual ao do Orchestrator
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                for key, value in user_config.items():
                    default_config[key] = value
                logger.info("Configuração de seleção carregada do arquivo")
            except Exception as e:
                logger.warning(f"Erro ao carregar config de selecao: {e}")
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
        else:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            logger.info("Configuração de seleção padrão criada")
        
        return default_config
    
    def selecionar_modelo(self, task_id, requisitos=None, exclude_provedores=None,
                          preferir_provedor=None):
        """
        Selecionar o melhor modelo/provedor para uma tarefa.
        
        Args:
            task_id: ID da tarefa atual
            requisitos: dict com requisitos da tarefa (ferramentas, visao, etc.)
            exclude_provedores: lista de aliases para excluir (já tentados)
            preferir_provedor: alias de provedor preferido (para forçar ou priorizar)
        
        Returns:
            dict com: modelo_selecionado, provedor_selecionado, razao, custos_estimados
        """
        if requisitos is None:
            requisitos = self.config.get("requisitos_padrao", {
                "ferramentas": False,
                "visao": False,
                "programacao": True,
                "contexto_maximo_minimo": 1024,
                "privado": True
            })
        
        exclude_provedores = exclude_provedores or []
        preferir_provedor = preferir_provedor or None
        
        logger.info(f"Selecionando modelo para tarefa {task_id}")
        logger.info(f"Requisitos: {requisitos}")
        logger.info(f"Provedores a excluir: {exclude_provedores}")
        
        # 1. Se ha preferencia explicita, verificar primeiro
        if preferir_provedor:
            logger.info(f"Verificando provedor preferido: {preferir_provedor}")
            resultado = self._avaliar_provedor(preferir_provedor, requisitos, exclude_provedores)
            if resultado["compativel"]:
                logger.info(f"Provedor preferido {preferir_provedor} e compatível")
                return self._criar_resultado_selecao(
                    provedor=preferir_provedor, 
                    modelo=None,  # Selecionar modelo top da lista
                    motivo="preferencia_explicita",
                    custo_estimado=0.0
                )
            else:
                logger.warning(f"Provedor preferido {preferir_provedor} nao e compativel")
                # Remover da lista de exclusao e continuar
                if preferir_provedor not in exclude_provedores:
                    exclude_provedores.append(preferir_provedor)
        
        # 2. Verificar compatibilidade de todos os provedores registrados
        provedores_elegiveis = []
        
        for alias_provedor, prov in self.registry.provedores.items():
            # Pular se estiver na lista de exclusao
            if alias_provedor in exclude_provedores:
                logger.debug(f"Pulando provedor excluido: {alias_provedor}")
                continue
            
            # Verificar compatibilidade
            compatibilidade = self.verificar_compatibilidade(alias_provedor, requisitos)
            
            if compatibilidade["compativel"]:
                # Calcular custo estimado
                custo_estimado = self._calcular_custo(alias_provedor, prov)
                
                # Verificar politica de custo (nao selecionar pago se ha gratuito)
                if self.config.get("evitar_modelos_pagos", True) and custo_estimado > 0:
                    # Verificar se ha alguma alternativa gratuita
                    # Por enquanto, permitir se for o unico option ou modo privacy nao exija local
                    modo_privacy = self.config.get("privacy_mode", "local-first")
                    if not prov.get("privado", True) and modo_privacy == "local-first":
                        # Modo local-first e esse provedor nao e local -> pular
                        logger.debug(f"Pulando {alias_provedor} por politica de privacidade local-first")
                        continue
                
                logger.debug(f"Provedor {alias_provedor} compativel, custo estimado: ${custo_estimado}")
                provedores_elegiveis.append({
                    "provedor": alias_provedor,
                    "provedor_info": prov,
                    "compatibilidade": compatibilidade,
                    "custo_estimado": custo_estimado
                })
        
        if not provedores_elegiveis:
            logger.error("Nenhum provedor compatível encontrado com os requisitos atuais")
            return {
                "sucesso": False,
                "motivo": "nenhum_provedor_compativel",
                "modelo_selecionado": None,
                "provedor_selecionado": None,
                "razao": "Nenhum dos provedores registrados satisfaz os requisitos atuais. "
                         "Verifique: requisitos da tarefa, politica de privacidade, "
                         "e se ha modelos pagos gratuitamente disponiveis."
            }
        
        # 3. Classificar e selecionar o melhor
        # Critérios de classificacao (em ordem de importancia):
        # A. Custo zero (gratuitos)
        # B. Privacidade (local-first)
        # C. Capacidades (ferramentas, visao, programacao)
        # D. Desempenho/qualidade (benchmarks)
        
        def classificar_provedor(p):
            score = 0
            prov = p["provedor_info"]
            
            # Pontuar custo zero
            if p["custo_estimado"] == 0.0:
                score += 100  # Altissimo prioridade custo zero
            
            # Pontuar privacidade local
            if prov.get("privado", True):
                score += 50
            
            # Ferramentas somam
            if prov.get("ferramentas_suportadas", False):
                score += 20
            
            # Visao soma
            visao = prov.get("visao", "").lower()
            if visao and visao != "nao_suportado":
                score += 20
            
            # Programacao
            prog = prov.get("programacao", "").lower()
            if prog and prog != "nao_info":
                score += 10
            
            return (score, p["custo_estimado"], p["provedor"])
        
        # Classificar e ordenar
        provedores_classificados = sorted(
            [classificar_provedor(p) for p in provedores_elegiveis],
            key=lambda x: (-x[0], x[1])  # Maior score primeiro; menor custo empatando
        )
        
        # Selecionar o melhor
        melhor_score, melhor_custo, melhor_provedor = provedores_classificados[0]
        
        logger.info(f"Melhor selecao: {melhor_provedor} (score={melhor_score}, custo=${melhor_custo})")
        
        # Obter modelo deste provedor
        modelos_disponiveis = self.registry.obter_modelos(melhor_provedor)
        modelo_selecionado = None
        
        if modelos_disponiveis:
            # Selecionar modelo prioritario: preferir gratuito, depois compatibilidade
            for m in modelos_disponiveis:
                if m.get("gratuito", False):
                    modelo_selecionado = m
                    break
            if not modelo_selecionado and modelos_disponiveis:
                # Fallback: primeiro da lista
                modelo_selecionado = modelos_disponiveis[0]
            
            # Se ainda nao tem modelo (lista vazia), criar placeholder
            if not modelo_selecionado:
                modelo_selecionado = {
                    "nome": "modelo_nao_especificado",
                    "identificador": f"{melhor_provedor}:default",
                    "gratuito": True,
                    "confirmado": "N_CONFIRMADO"
                }
        
        # Montar razao da selecao
        razao = self._gerar_razao_selecao(melhor_provedor, modelo_selecionado, requisitos, melhor_custo)
        
        custo_total = self._calcular_custo_total(alias_provedor=melhor_provedor)
        
        logger.info(f"Modelo selecionado: {modelo_selecionado.get('nome', 'N/A') if modelo_selecionado else 'N/A'} "
                     f"de {melhor_provedor}. Razao: {razao}")
        
        return {
            "sucesso": True,
            "modelo_selecionado": modelo_selecionado,
            "provedor_selecionado": melhor_provedor,
            "razao": razao,
            "custo_estimado": melhor_custo,
            "compatibilidade": self.verificar_compatibilidade(melhor_provedor, requisitos),
            "modelos_disponiveis": modelos_disponiveis,
            "estrategia_usada": "custo_primeiro" if melhor_custo == 0 else "melhor_disponivel"
        }
    
    def _avaliar_provedor(self, alias_provedor, requisitos, exclude_list=None):
        """Avaliar se um provedor e compatível com os requisitos."""
        if exclude_list is None:
            exclude_list = []
        
        if alias_provedor in exclude_list:
            return {"compativel": False, "motivo": "provedor_excluido"}
        
        prov = self.registry.provedores.get(alias_provedor)
        if not prov:
            return {"compativel": False, "motivo": f"Provedor {alias_provedor} nao cadastrado"}
        
        compatibilidade = self.registry.verificar_compatibilidade(alias_provedor, requisitos)
        custo = self._calcular_custo(alias_provedor, prov)
        
        return {
            "compativel": compatibilidade["compativel"],
            "motivo": compatibilidade.get("restricoes", ["Nenhuma restriao especifica"]),
            "custo_estimado": custo,
            "provedor_info": prov
        }
    
    def _calcular_custo(self, alias_provedor, prov=None):
        """Calcular custo estimado para um provedor."""
        if prov is None:
            prov = self.registry.provedores.get(alias_provedor)
        
        if not prov:
            return -1  # Erro
        
        # Verificar se gratuito
        if prov.get("gratuito", False):
            return 0.0
        
        # Modelos pagos: estimativa baseada em preços publicos aproximados
        # Esses valores sao referenciais apenas; uso real deve ser medido
        modelo_nome = prov.get("nome_exibicao", "").lower()
        
        # Precos referenciais (2026) - apenas para estimativa, nao para cobranca automatica
        precos_referencia = {
            "gpt-4o": 0.005,     # por 1K tokens entrada
            "gpt-4o-mini": 0.00015,
            "gpt-6-luna": 0.015,  # estimativa OpenAI premium
            "claude-3-haiku": 0.0025,
            "gemini-3.5-flash": 0.0001,
            "gemini-3.5-flash-lite": 0.0,  # gratuito na conta
        }
        
        # Verificar se tem preco referenciado
        for key, preco in precos_referencia.items():
            if key in modelo_nome:
                return preco  # Retornar custo entrada por 1K tokens
        
        # Padrao: retorna custo medio se nao encontrou referencia especifica
        # (marcador para chamar usuario confirmar antes de prosseguir)
        return 0.10  # Custo estimado medio - usuario deve confirmar
    
    def _calcular_custo_total(self, alias_provedor):
        """Calcular custo total do provedor (alias para _calcular_custo)."""
        return self._calcular_custo(alias_provedor)
    
    def _gerar_razao_selecao(self, provedor_alias, modelo_selecionado, requisitos, custo):
        """Gerar texto explicativo da razao da selecao."""
        linhas = []
        
        prov = self.registry.provedores.get(provedor_alias, {})
        linhas.append(f"Provedor: {prov.get('nome_exibicao', provedor_alias)}")
        linhas.append(f"Tipo: {prov.get('tipo', 'desconhecido')}")
        
        if custo == 0:
            linhas.append("Custo: Gratuito (zero custo)")
        else:
            linhas.append(f"Custo: Estimado ${custo:.4f} (consultar antes de prosseguir)")
        
        # Verificar requisitos atendidos
        requisitos_atendidos = []
        requisitos_nao_atendidos = []
        
        if requisitos.get("ferramentas") and prov.get("ferramentas_suportadas", False):
            requisitos_atendidos.append("Ferramentas")
        elif requisitos.get("ferramentas"):
            requisitos_nao_atendidos.append("Ferramentas")
        
        if requisitos.get("visao") and prov.get("visao", "").lower() not in ["nao_suportado", "nao_info"]:
            requisitos_atendidos.append("Visao/Multimodal")
        elif requisitos.get("visao"):
            requisitos_nao_atendidos.append("Visao/Multimodal")
        
        if requisitos.get("programacao"):
            prog = prov.get("programacao", "").lower()
            if prog and prog != "nao_info":
                requisitos_atendidos.append("Programacao")
        
        if requisitos.get("privado") and prov.get("privado", True):
            requisitos_atendidos.append("Privacidade local")
        elif requisitos.get("privado") and not prov.get("privado", True):
            requisitos_nao_atendidos.append("Privacidade local (dados externos)")
        
        if requisitos_atendidos:
            linhas.append(f"Requisitos atendidos: {', '.join(requisitos_atendidos)}")
        if requisitos_nao_atendidos:
            linhas.append(f"Requisitos nao atendidos: {', '.join(requisitos_nao_atendidos)}")
        
        if modelo_selecionado:
            linhas.append(f"Modelo: {modelo_selecionado.get('nome', 'N/A')}")
            linhas.append(f"Identificador: {modelo_selecionado.get('identificador', 'N/A')}")
            linhas.append(f"Gratuito: {modelo_selecionado.get('gratuito', False)}")
        
        return " | ".join(linhas)
    
    def verificar_compatibilidade(self, alias_provedor, requisitos):
        """Compatibilidade com alias para compatibilidade com Interface antiga."""
        return self.registry.verificar_compatibilidade(alias_provedor, requisitos)
    
    def obter_relatorio_selecao(self, task_id, requisitos=None):
        """Gerar relatorio detalhado da selecao para auditoria."""
        from datetime import datetime
        
        if requisitos is None:
            requisitos = self.config.get("requisitos_padrao", {})
        
        resultado = self.selecionar_modelo(task_id, requisitos=requisitos)
        
        relatorio = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "requisitos_solicitados": requisitos,
            "resultado": resultado,
            "configuracao": self.config
        }
        
        # Salvar relatorio
        relatorios_dir = self.base_dir / "audit" / "selecoes"
        relatorios_dir.mkdir(parents=True, exist_ok=True)
        relatorio_path = relatorios_dir / f"selecao_{task_id}_{int(time.time())}.json"
        
        try:
            with open(relatorio_path, 'w', encoding='utf-8') as f:
                json.dump(relatorio, f, ensure_ascii=False, indent=2)
            logger.info(f"Relatorio de selecao salvo: {relatorio_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar relatorio: {e}")
        
        return relatorio


# Instancia global (opcional)
try:
    global_selector = ModelSelector()
except Exception as e:
    logger.error(f"Erro ao instanciar global selector: {e}")
    global_selector = None