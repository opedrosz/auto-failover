#!/usr/bin/env python3
"""
Skills Integration - Componente 14 de 15 da AUTO FAILOVER V1.0.2

Compatibilidade com Skills existentes (browser, memory, philosophy, safety, etc.),
SEM modificar suas instalações originais.

Princípios:
- Skills permanecem inalteradas em suas localizações originais
- Fronteira de privacidade respeitada (nenhum dado local enviado cloud sem consentimento)
- Checkpoints usam apenas campos textuais compatíveis com todos os provedores
- Fallback nao tenta enviar tools/functions para provedores que nao suportem (ou exija consentimento)
- Integracao via interfaces publicas, modificacao interna proibida
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.SkillsIntegration')

class SkillsIntegration:
    """Integracao compativel com Skills existentes do Orion e projetos associados."""
    
    def __init__(self, base_dir=None, registry=None, orchestrator=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.registry = registry or self._carregar_registro()
        self.orchestrator = orchestrator or self._carregar_orchestrator()
        
        # Caminhos dos skills existentes (apenas leitura - nao modificar)
        # Orion skills
        self.home_dir = Path(r'C:\Users\Pedro\Orion')
        self.scripts_dir = self.home_dir / "scripts"
        self.scripts_dir.mkdir(parents=True, exist_ok=True)
        
        # Skills mapeadas: nome -> alias/arquivo correspondente
        # Estas sao mapeamentos de compatibilidade APENAS LEITURA
        self.skills_map = {
            "browser_controller": {
                "arquivo": "browser_controller.py",
                "provedor_necessario": "opencode_console",  # Texto simples apenas
                "compatibilidade": "textos_simples",
                "ferramentas_suportadas": False,  # No cloud por defeito
                "modificado": False  # Nao modificar
            },
            "philosophy_library": {
                "arquivo": "philosophy_library.py",
                "provedor_necessario": "opencode_console",
                "compatibilidade": "textos_simples",
                "ferramentas_suportadas": False,
                "modificado": False
            },
            "memory_store": {
                "arquivo": "memory_store.py",
                "provedor_necessario": "opencode_console",
                "compatibilidade": "textos_simples",
                "ferramentas_suportadas": False,
                "modificado": False
            },
            "safety_gate": {
                "arquivo": "safety_gate.py",
                "provedor_necessario": "opencode_console",
                "compatibilidade": "textos_simples",
                "ferramentas_suportadas": False,
                "modificado": False
            },
            "polystrata_router": {
                "arquivo": "polystrata_router.py",
                "provedor_necessario": "opencode_console",
                "compatibilidade": "textos_simples",
                "ferramentas_suportadas": False,
                "modificado": False
            },
            "model_router": {
                "arquivo": "model_router.py",
                "provedor_necessario": "opencode_console",
                "compatibilidade": "textos_simples + aliases cloud",
                "ferramentas_suportadas": True,  # Quando orion_cloud_consent=True
                "modificado": False
            }
        }
        
        # Verificar quais skills estao disponiveis
        self.skills_disponiveis = self._verificar_skills_disponiveis()
        
        logger.info(f"Skills Integration inicializado. "
                     f"Skills mapeadas: {len(self.skills_map)}")
        logger.info(f"Skills disponiveis para uso: {list(self.skills_disponiveis.keys())}")
    
    def _carregar_registro(self):
        try:
            from provider_registry import ProviderRegistry
            return ProviderRegistry(self.base_dir)
        except Exception as e:
            logger.error(f"Erro: {e}")
            class MinimalRegistry:
                provedores = {}
            return MinimalRegistry()
    
    def _carregar_orchestrator(self):
        try:
            from orchestrator import Orchestrator
            return Orchestrator(self.base_dir)
        except Exception as e:
            logger.error(f"Erro: {e}")
            return None
    
    def _verificar_skills_disponiveis(self):
        """Verificar quais skills do Orion estao disponiveis (apenas leitura)."""
        skills = {}
        
        # Verificar cada skill mapeada
        for skill_name, skill_info in self.skills_map.items():
            arquivo_path = self.scripts_dir / skill_info["arquivo"]
            if arquivo_path.exists():
                skills[skill_name] = {
                    "disponivel": True,
                    "caminho": str(arquivo_path),
                    "tamanho_bytes": arquivo_path.stat().st_size,
                    "ultima_modificacao": datetime.fromtimestamp(
                        arquivo_path.stat().st_mtime
                    ).isoformat() if arquivo_path.exists() else None
                }
            else:
                skills[skill_name] = {
                    "disponivel": False,
                    "caminho": str(arquivo_path) if arquivo_path.exists() else "N/A",
                    "motivo": "Arquivo nao encontrado (pode estar em instalacao diferente)"
                }
        
        return skills
    
    def verificar_compatibilidade_provedor(self, alias_provedor, skill_name):
        """
        Verificar se um provedor e compativel com uma skill especifica.
        
        Returns:
            dict: { "compativel": bool, "motivo": str, "limites": {...} }
        """
        skill_info = self.skills_map.get(skill_name)
        if not skill_info:
            return {"compativel": False, "motivo": f"Skill '{skill_name}' nao mapeada"}
        
        if not skill_info.get("disponivel", False):
            return {"compativel": False, "motivo": f"Skill '{skill_name}' nao disponivel"}
        
        prov = self.registry.provedores.get(alias_provedor) if self.registry else None
        if not prov:
            return {"compativel": False, "motivo": f"Provedor '{alias_provedor}' nao cadastrado"}
        
        # Verificar compatibilidade baseada nas caracteristicas do provedor
        compatibilidade = {
            "compativel": True,
            "motivo": "Compatibilidade verificada",
            "limites": {
                "ferramentas_bloqueadas": not prov.get("ferramentas_suportadas", False),
                "visao_bloqueada": prov.get("visao", "").lower() in ["nao_suportado", "nao_info"],
                "contexto_maximo": prov.get("contexto_maximo", "variavel"),
                "politica_privacidade": prov.get("politica_privacidade", "nao_info")
            }
        }
        
        # Skills que so aceitam texto simples nao sao compativeis com ferramentas/cloud por defeito
        if not skill_info.get("ferramentas_suportadas", False) and not prov.get("ferramentas_suportadas", False):
            # Ambos nao suportam ferramentas - compativel no sentido de "texto simples"
            compatibilidade["compativel"] = True
            compatibilidade["motivo"] = ("Skill aceita apenas texto simples; "
                                         "provedor nao envia tools - compativel por design")
            # Mas se a skill precisar de tools e o provedor tambem, entao compativel
        elif skill_info.get("ferramentas_suportadas", False) and prov.get("ferramentas_suportadas", False):
            # Ambos suportam tools - verificar consentimento
            compatibilidade["motivo"] = ("Skill suporta tools; requer orion_cloud_consent=True "
                                        "para envio a provedores cloud")
        
        return compatibilidade
    
    def get_skill_context_limites(self, skill_name):
        """
        Obter os limites de contexto para uma skill especifica.
        Isso ajuda o Model Selector a escolher um modelo com contexto adequado.
        """
        skill_info = self.skills_map.get(skill_name)
        if not skill_info:
            return None
        
        # Retornar limites baseados na skill
        return {
            "skill": skill_name,
            "arquivo": skill_info["arquivo"],
            "ferramentas_suportadas": skill_info.get("ferramentas_suportadas", False),
            "compatibilidade_provedor": skill_info.get("compatibilidade", "textos_simples"),
            "provedor_recomendado": skill_info["provedor_necessario"]
        }
    
    def gerar_checkpoint_skill_compativel(self, skill_name, contexto_atual, 
                                          provedor_atual=None):
        """
        Gerar um checkpoint compativel com uma skill especifica.
        Isso garante que o checkpoint possa ser usado posteriormente com a mesma skill.
        
        Returns:
            dict: Checkpoint formatado para compatibilidade com a skill
        """
        skill_info = self.skills_map.get(skill_name)
        if not skill_info:
            logger.error(f"Skill '{skill_name}' nao mapeiada")
            return None
        
        # Filtrar contexto para apenas campos compataveis com todos os provedores
        # (texto simples, sem tools/functions/attachments/files/images por defeito)
        contexto_filtrado = self._filtrar_contexto_para_provedor(
            contexto_atual, 
            provedor_atual or "opencode_console"
        )
        
        checkpoint = {
            "skill_nome": skill_name,
            "skill_arquivo": skill_info["arquivo"],
            "contexto_filtrado": contexto_filtrado,
            "provedor_origem": provedor_atual or "opencode_console",
            "timestamp": datetime.utcnow().isoformat(),
            "compatibilidade": skill_info["compatibilidade"]
        }
        
        logger.debug(f"Checkpoint compativel gerado para skill {skill_name}")
        return checkpoint
    
    def _filtrar_contexto_para_provedor(self, contexto, alias_provedor):
        """Filtrar contexto para ser compativel com as restricoes de um provedor."""
        # Em implementacao real, isso removeria tools, functions, attachments, etc.
        # Com base nas politicas do proxy Orion (contains_non_text_content)
        
        # Por enquanto, apenas validar que o contexto e um dict valido
        # e remover chaves conhecidas como problematicas para cloud boundary
        resultado = contexto.copy() if isinstance(contexto, dict) else {}
        
        # Remover chaves que sao exclusivas do proxy Orion e nao sao 
        # seguranca enviar a cloud sem consentimento
        chaves_remover = ["tools", "tool_choice", "functions", "function_call"]
        for chave in chaves_remover:
            resultado.pop(chave, None)
        
        # Verificar attachments/files/images
        if "attachments" in resultado:
            del resultado["attachments"]
        if "files" in resultado:
            del resultado["files"]
        if "images" in resultado:
            del resultado["images"]
        
        return resultado
    
    def listar_skills_compativeis_com(self, alias_provedor):
        """Listar quais skills sao compativeis com um provedor especificado."""
        compativeis = []
        
        for skill_name, skill_info in self.skills_map.items():
            compat = self.verificar_compatibilidade_provedor(alias_provedor, skill_name)
            if compat.get("compativel"):
                compativeis.append({
                    "skill": skill_name,
                    "arquivo": skill_info["arquivo"],
                    "motivo": compat.get("motivo", "Compatibilidade desconhecida"),
                    "limites": compat.get("limites", {})
                })
        
        return compativeis


# Instancia global
try:
    global_skills_integration = SkillsIntegration()
except Exception as e:
    logger.error(f"Erro ao instanciar global SkillsIntegration: {e}")
    global_skills_integration = None