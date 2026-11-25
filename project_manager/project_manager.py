#!/usr/bin/env python3
"""
Project Manager - Componente 15 de 15 da AUTO FAILOVER V1.0.2

Separacao de contexto, arquivos, memoria e permissoes entre projetos.
Garantir que Orion, Editor-Video, Codex Skills Integration e desenvolvimento de sites
tenham contexto isolado e independente.

Princípios:
- Contexto independente por projeto
- Memoria compartilhada vs memoria privada
- permissoes concedidas por projeto
- Nao misturar arquivos/estado entre projetos
- Checkpoints rotulados por projeto
"""

import json
import logging
import os
import hashlib
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.ProjectManager')

class ProjectManager:
    """Gerenciador de projetos: contexto, memoria, permissoes e arquivos isolados."""
    
    def __init__(self, base_dir=None, registry=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.registry = registry or self._carregar_registro()
        self.config_dir = self.base_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Diretorio base para projetos (so como referencia, Nao modificar)
        self.projetos_base = Path(r'C:\Users\Pedro')
        
        # Arquivos de configuracao de projetos
        self.config_arquivo = self.config_dir / "project_manager_config.json"
        self.historico_projetos = self.base_dir / "data" / "historico_projetos.jsonl"
        
        # Carregar configuracao
        self.config = self._carregar_configuracao()
        
        # Garantir diretorios
        (self.base_dir / "data").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "logs").mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Project Manager inicializado. "
                     f"Projetos gerenciados: {len(self.config.get('projetos', {}))}")
    
    def _carregar_registro(self):
        try:
            from provider_registry import ProviderRegistry
            return ProviderRegistry(self.base_dir)
        except Exception as e:
            logger.error(f"Erro: {e}")
            class MinimalRegistry:
                provedores = {}
            return MinimalRegistry()
    
    def _carregar_configuracao(self):
        """Carregar configuracao do Project Manager."""
        if self.config_arquivo.exists():
            try:
                with open(self.config_arquivo, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info("Configuracao de Project Manager carregada")
                return config
            except Exception as e:
                logger.warning(f"Erro ao carregar configuracao: {e}")
        
        # Configuracao padrao: projetos conhecidos
        configuracao_padrao = {
            "projetos": {
                "Orion": {
                    "id": "orion_2026_11",
                    "contexto_privado": True,
                    "memoria_compartilhada": False,
                    "permissoes": {
                        "ler_orion_docs": True,
                        "escrever_orion_checkpoints": True,
                        "modificar_orion_config": False
                    },
                    "arquivos_separados": True,
                    "checkpoint_prefix": "orion_"
                },
                "Editor-Video": {
                    "id": "editor_video_2026_11",
                    "contexto_privado": True,
                    "memoria_compartilhada": False,
                    "permissoes": {
                        "ler_editor_docs": True,
                        "escrever_editor_checkpoints": True,
                        "modificar_editor_config": False
                    },
                    "arquivos_separados": True,
                    "checkpoint_prefix": "editor_video_"
                },
                "Codex-Skills-Integration": {
                    "id": "codex_skills_2026_11",
                    "contexto_privado": True,
                    "memoria_compartilhada": False,
                    "permissoes": {
                        "ler_codex_docs": True,
                        "escrever_codex_checkpoints": True,
                        "modificar_codex_config": False
                    },
                    "arquivos_separados": True,
                    "checkpoint_prefix": "codex_skills_"
                },
                "Desenvolvimento-Sites": {
                    "id": "dev_sites_2026_11",
                    "contexto_privado": True,
                    "memoria_compartilhada": False,
                    "permissoes": {
                        "ler_docs_dev": True,
                        "escrever_checkpoints_dev": True,
                        "modificar_config_dev": False
                    },
                    "arquivos_separados": True,
                    "checkpoint_prefix": "dev_sites_"
                }
            },
            "memoria_compartilhada_global": {
                "objetivo_original": "Desenvolvimento multiagente autonomo",
                "regras_projeto": "Cada projeto tem suas proprias regras; memoria global so para objetivos gerais",
                "acesso": "todos_projetos"
            }
        }
        
        with open(self.config_arquivo, 'w', encoding='utf-8') as f:
            json.dump(configuracao_padrao, f, ensure_ascii=False, indent=2)
        
        logger.info("Configuracao padrao de Project Manager criada")
        return configuracao_padrao
    
    def registrar_projeto(self, nome_projeto, id_projeto=None, **kwargs):
        """
        Registrar um novo projeto no gerenciador.
        
        Args:
            nome_projeto: Nome humano legivel
            id_projeto: ID unico (gerado se nao fornecido)
            **kwargs: configuracao adicional (sobreescreve defaults)
        """
        if id_projeto is None:
            import time
            id_projeto = f"{nome_projeto.lower().replace(' ', '_')}_{int(time.time())}"
        
        # Defaults por tipo de projeto
        defaults = {
            "Orion": {
                "contexto_privado": True,
                "memoria_compartilhada": False,
                "permissoes": {"ler_orion_docs": True, "escrever_orion_checkpoints": True,
                              "modificar_orion_config": False},
                "arquivos_separados": True,
                "checkpoint_prefix": "orion_"
            },
            "Editor-Video": {
                "contexto_privado": True,
                "memoria_compartilhada": False,
                "permissoes": {"ler_editor_docs": True, "escrever_editor_checkpoints": True,
                              "modificar_editor_config": False},
                "arquivos_separados": True,
                "checkpoint_prefix": "editor_video_"
            },
            "Codex-Skills-Integration": {
                "contexto_privado": True,
                "memoria_compartilhada": False,
                "permissoes": {"ler_codex_docs": True, "escrever_codex_checkpoints": True,
                              "modificar_codex_config": False},
                "arquivos_separados": True,
                "checkpoint_prefix": "codex_skills_"
            },
            "Desenvolvimento-Sites": {
                "contexto_privado": True,
                "memoria_compartilhada": False,
                "permissoes": {"ler_docs_dev": True, "escrever_checkpoints_dev": True,
                              "modificar_config_dev": False},
                "arquivos_separados": True,
                "checkpoint_prefix": "dev_sites_"
            }
        }
        
        # Detectar tipo basico a partir do nome
        tipo_detectado = "Orion"  # Default
        nome_lower = nome_projeto.lower()
        if "video" in nome_lower:
            tipo_detectado = "Editor-Video"
        elif "codex" in nome_lower or "skills" in nome_lower:
            tipo_detectado = "Codex-Skills-Integration"
        elif "site" in nome_lower or "web" in nome_lower:
            tipo_detectado = "Desenvolvimento-Sites"
        
        defaults_tipo = defaults.get(tipo_detectado, defaults["Orion"])
        
        # Mesclar com kwargs fornecidos
        configuracao = {}
        for key, valor in defaults_tipo.items():
            configuracao[key] = kwargs.get(key, valor)
        
        # Adicionar o tipo detectado
        configuracao["tipo_detectado"] = tipo_detectado
        
        # Salvar
        self.config["projetos"][id_projeto] = configuracao
        
        try:
            with open(self.config_arquivo, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            # Registrar no historico
            self._registrar_historico({
                "acao": "registrar_projeto",
                "id_projeto": id_projeto,
                "nome_projeto": nome_projeto,
                "tipo_detectado": tipo_detectado,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Projeto registrado: {nome_projeto} (ID: {id_projeto}, tipo: {tipo_detectado})")
            return id_projeto
        except Exception as e:
            logger.error(f"Erro ao registrar projeto: {e}")
            return None
    
    def _registrar_historico(self, entry):
        """Registrar entrada no historico de projetos."""
        try:
            with open(self.historico_projetos, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Erro no historico de projetos: {e}")
    
    def obter_contexto_projeto(self, id_projeto):
        """
        Obter o contexto configurado para um projeto.
        
        Returns:
            dict: Contexto do projeto ( permissoes, prefixos, etc.)
        """
        projetos = self.config.get("projetos", {})
        return projetos.get(id_projeto, None)
    
    def verificar_permissao(self, id_projeto, permisao):
        """
        Verificar se um projeto tem uma permissa especifica.
        """
        projeto = self.obter_contexto_projeto(id_projeto)
        if not projeto:
            return False
        
        permissoes = projeto.get("permissoes", {})
        return permissoes.get(permisao, False)
    
    def checkpoint_rotulado(self, task_id, projeto_id, etapa, motivo, 
                            contexto_atual, contexto_anterior=None):
        """
        Criar um checkpoint rotulado por projeto.
        
        Isso garante que checkpoints do Orion nao se misturem com os do Editor-Video,
        mesmo usando a mesma infraestrutura de checkpoint do Auto-Failover.
        """
        # Obter configuracao do projeto
        projeto_config = self.obter_contexto_projeto(id_projeto)
        if not projeto_config:
            logger.error(f"Projeto {id_projeto} nao encontrado")
            return None
        
        # Adicionar metadados de projeto ao checkpoint
        checkpoint_base = {
            "task_id": task_id,
            "projeto_id": id_projeto,
            "projeto_nome": id_projeto,  # Em implementacao real, mapear ID para nome
            "etapa": etapa,
            "motivo": motivo,
            "timestamp": datetime.utcnow().isoformat(),
            "projeto_prefixo": projeto_config.get("checkpoint_prefix", "default_")
        }
        
        # Adicionar contexto (filtrado se necessario)
        if contexto_atual:
            checkpoint_base["contexto_atual"] = contexto_atual
        if contexto_anterior:
            checkpoint_base["contexto_anterior"] = contexto_anterior
        
        # O checksum sera gerado pelo CheckpointManager
        # Aqui so montamos a estrutura com rotulagem de projeto
        
        logger.debug(f"Checkpoint rotulado para projeto {id_projeto} - stage: {etapa}")
        return checkpoint_base
    
    def separar_contexto_multiprojeto(self, contexto_geral, projetos_ativos):
        """
        Separar um contexto geral em contextos individuais por projeto.
        
        Args:
            contexto_geral: Contexto unico que pode ter informacoes de varios projetos
            projetos_ativos: Lista de IDs de projetos ativos
        
        Returns:
            dict: { id_projeto: contexto_individual }
        """
        contextos_separados = {}
        
        for proj_id in projetos_ativos:
            proj_config = self.obter_contexto_projeto(proj_id)
            if not proj_config:
                continue
            
            # Em implementacao real, isso cruzaria o contexto com as regras do projeto
            # Para agora, atribuimos pedacos baseados em indicadores no contexto
            contexto_proj = {
                "projeto_id": proj_id,
                "projeto_nome": proj_config.get("tipo_detectado", proj_id),
                "contexto_filtrado": {},  # Filtrado baseado em regras do projeto
                "permissoes": proj_config.get("permissoes", {}),
                "eh_privado": proj_config.get("contexto_privado", True)
            }
            
            # Tentar extrair partes relevantes do contexto geral
            if isinstance(contexto_geral, dict):
                # Verificar se contexto tem indicadores de projeto
                for key, value in contexto_geral.items():
                    # Lógica simplificada: atribuir tudo ao primeiro projeto se nao houver
                    # separacao explicitra no contexto
                    if not contextos_separados:
                        contextos_separados[proj_id] = {}
                    contextos_separados[proj_id][key] = value
            
            contextos_separados[proj_id]["regras_aplicadas"] = {
                "contexto_privado": proj_config.get("contexto_privado", True),
                "arquivos_separados": proj_config.get("arquivos_separados", True)
            }
        
        return contextos_separados if contextos_separados else None
    
    def get_estado_projetos(self):
        """Retornar estado resumido de todos os projetos."""
        projetos = self.config.get("projetos", {})
        
        estado = {
            "total_projetos": len(projetos),
            "projetos": {}
        }
        
        for id_projeto, config in projetos.items():
            estado["projetos"][id_projeto] = {
                "nome_tipo": config.get("tipo_detectado", "desconhecido"),
                "contexto_privado": config.get("contexto_privado", True),
                "memoria_compartilhada": config.get("memoria_compartilhada", False),
                "tem_checkpoints": False,  # Seria verificado counting checkpoints com prefixo
                "permissoes": list(config.get("permissoes", {}).keys())
            }
        
        return estado


# Instancia global
try:
    global_project_manager = ProjectManager()
except Exception as e:
    logger.error(f"Erro ao instanciar global ProjectManager: {e}")
    global_project_manager = None