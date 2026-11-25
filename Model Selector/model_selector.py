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
import time
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
        self.registry = registry if registry is not None else self._carregar_registro()
        self.config_dir = self.base_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Carregar config de selecao
        self.config = self._carregar_configuracao_selecao()
        
        logger.info(f"Model Selector inicializado. {len(self.registry.provedores)} provedores "
                     f"disponíveis no registro.")
    
    def _carregar_registro(self):
        """Carregar Provider Registry."""
        from provider_registry import ProviderRegistry
        return ProviderRegistry(self.base_dir)
    
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
                    if key == "requisitos_padrao":
                        default_config[key].update(value)
                    else:
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
                           preferir_provedor=None, *, excluir_modelos=(), pode_executar=None,
                           provedores_autorizados=None, grupos_excluidos=()):
        """Select a concrete model with an auditable list of rejections."""
        if requisitos is None:
            requisitos = self.config["requisitos_padrao"]

        rejeicoes = {}
        elegiveis = []
        for alias, provedor in self.registry.provedores.items():
            motivos = rejeicoes.setdefault(alias, {})
            if (alias in (exclude_provedores or ()) or
                (provedores_autorizados is not None and alias not in provedores_autorizados)):
                motivos["*"] = ["provedor excluido ou nao autorizado"]
                continue
            if provedor.get("status") != "conectado" or (
                pode_executar is not None and not pode_executar(alias)
            ):
                motivos["*"] = ["provedor indisponivel ou circuito aberto"]
                continue
            modelos = self.registry.obter_modelos(alias)
            if not modelos:
                motivos["*"] = ["nenhum modelo cadastrado"]
            for modelo in modelos:
                identificador = modelo.get("identificador")
                compatibilidade = self.registry.verificar_compatibilidade(alias, requisitos, modelo)
                restricoes = compatibilidade["restricoes"]
                if not identificador or (alias, identificador) in excluir_modelos:
                    restricoes.append("modelo sem identificador ou ja tentado")
                if modelo.get("disponivel") is False or modelo.get("autorizado") is False:
                    restricoes.append("modelo indisponivel ou nao autorizado")
                grupo = modelo.get("grupo_cota", provedor.get("grupo_cota"))
                if grupo in grupos_excluidos or modelo.get("cota_disponivel") is False:
                    restricoes.append("cota indisponivel")
                custo = 0 if modelo.get("gratuito") is True else modelo.get("custo_estimado_usd")
                if modelo.get("privado", provedor.get("privado")) is not True:
                    if modelo.get("custo_verificado") is not True:
                        restricoes.append("custo remoto nao verificado")
                if type(custo) not in (int, float) or not 0 <= custo <= self.config["max_cost_usd"]:
                    restricoes.append("custo desconhecido ou acima do limite")
                elif custo and self.config["evitar_modelos_pagos"]:
                    restricoes.append("modelo pago bloqueado")
                if restricoes:
                    motivos[identificador or "?"] = restricoes
                else:
                    privado = modelo.get("privado", provedor.get("privado")) is True
                    ordem = (alias != preferir_provedor, custo, not privado, alias, identificador)
                    elegiveis.append((ordem, alias, modelo, compatibilidade, grupo))
            if not motivos:
                del rejeicoes[alias]

        if not elegiveis:
            return {"sucesso": False, "motivo": "nenhum_provedor_compativel",
                    "modelo_selecionado": None, "provedor_selecionado": None,
                    "razao": "Nenhum modelo atende aos requisitos e politicas.",
                    "rejeicoes": rejeicoes}

        ordem, alias, modelo, compatibilidade, grupo = min(elegiveis, key=lambda item: item[0])
        logger.info("Selecao para %s: %s / %s", task_id, alias, modelo["identificador"])
        return {"sucesso": True, "provedor_selecionado": alias,
                "modelo_selecionado": modelo, "custo_estimado": ordem[1],
                "compatibilidade": compatibilidade, "rejeicoes": rejeicoes, "grupo_cota": grupo,
                "modelos_disponiveis": self.registry.obter_modelos(alias),
                "estrategia_usada": "custo_primeiro",
                "razao": "Modelo elegivel pela preferencia, custo, privacidade e identificador."}

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