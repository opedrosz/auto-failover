#!/usr/bin/env python3
"""
Security Controller - Componente 10 de 15 da AUTO FAILOVER V1.0.3

Camada central de segurança independente das decisoes do modelo.
Validar permissoes antes de cada acao relevante.
Nao permitir que um agente amplie suas proprias permissoes.

Princípios:
- Diferenciar validacao logica de isolamento efetivamente imposto pelo SO/executor
- Nao alegar que um modulo Python constitui sandbox inviolavel
- Preservar o Safety Gate e o Capability Registry do Orion
- Nao modificarlos nesta fase
"""

import json
import logging
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.SecurityController')

class SecurityController:
    """Camada central de seguranca para desenvolvimento multiagente."""
    
    def __init__(self, base_dir=None, project_manager=None, checkpoint_mgr=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.project_manager = project_manager or self._carregar_project_manager()
        self.checkpoint_mgr = checkpoint_mgr or self._carregar_checkpoint_mgr()
        self.registry = self._carregar_registro()
        
        # Diretorios autorizados por projeto (obtidos do Project Manager)
        self.diretorio_proibido = set()  # Caminhos que nao podem ser acessados
        self.permissoes_globais = {}
        
        # Garantir diretorios
        (self.base_dir / "data").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "logs").mkdir(parents=True, exist_ok=True)
        
        # Carregar configuracoes de seguranca
        self.config = self._carregar_config_seguranca()
        
        logger.info("Security Controller inicializado")
    
    def _carregar_project_manager(self):
        try:
            from project_manager import ProjectManager
            return ProjectManager(self.base_dir)
        except Exception as e:
            logger.error(f"Erro: {e}")
            return None
    
    def _carregar_checkpoint_mgr(self):
        try:
            from checkpoint_manager import CheckpointManager
            return CheckpointManager(self.base_dir)
        except Exception as e:
            logger.error(f"Erro: {e}")
            return None
    
    def _carregar_registro(self):
        try:
            from provider_registry import ProviderRegistry
            return ProviderRegistry(self.base_dir)
        except Exception as e:
            logger.error(f"Erro: {e}")
            return None
    
    def _carregar_config_seguranca(self):
        """Carregar configuracoes de seguranca do arquivo ou usar defaults."""
        config_path = self.base_dir / "config" / "security_config.json"
        defaults = {
            "proibir_prompt_injection": True,
            "proibir_escrita_fora_projeto": True,
            "proibir_leitura_credenciais": True,
            "proibir_modificacao_admin": True,
            "proibir_instalacao_programas": True,
            "proibir_execucao_comandos_nao_autorizados": True,
            "diretorios_permitidos": [],  # Serao preenchidos pelo project_manager
            "max_tamanho_arquivo_mb": 100,
            "requer_assinatura_para_modificacoes": True
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # Mesclar com defaults (user config sobrescreve default)
                for key, value in user_config.items():
                    defaults[key] = value
                logger.info("Configuracao de seguranca carregada do arquivo")
            except Exception as e:
                logger.warning(f"Erro ao carregar configuracao: {e}")
        else:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(defaults, f, ensure_ascii=False, indent=2)
            logger.info("Configuracao de seguranca padrao criada")
        
        return defaults
    
    def validar_acao(self,acao, contexto):
        """
        Validar se uma acao pode ser executada.
        
        Args:
            acao: dict com chaves 'tipo', 'descricao', 'caminho_arquivo' (se aplicavel)
            contexto: dict com informacoes do contexto atual (projeto, task_id, agente, etc.)
            
        Returns:
            dict: { "autorizada": bool, "motivo": str, "restricoes": [...], "acao_sugerida": ... }
        """
        tipo = acao.get("tipo", "")
        descricao = acao.get("descricao", "")
        caminho = aco.get("caminho_arquivo", "") if "caminho" in acao else ""
        
        restricoes = []
        autorizada = True
        motivo = "Acao autorizada"
        
        # 1. Verificar prompt injection
        if self.config.get("proibir_prompt_injection", True):
            if self._detectar_prompt_injection(descricao):
                autorizada = False
                restricoes.append("detetou_prompt_injection")
                motivo = "Bloqueado: possivel injection de prompt detectada"
        
        # 2. Verificar escrita fora do projeto
        if self.config.get("proibir_escrita_fora_projeto", True) and caminho:
            if caminho and self._caminho_fora_projeto(caminho, contexto):
                autorizada = False
                restricoes.append("escrita_fora_projeto")
                motivo = f"Bloqueado: escrita fora dos limites do projeto {contexto.get('projeto_id', 'N/A')}"
        
        # 3. Verificar leitura de credenciais
        if self.config.get("proibir_leitura_credenciais", True):
            if self._contem_credenciais(descricao):
                autorizada = False
                restricoes.append("leitura_credenciais")
                motivo = "Bloqueado: tentativa de leitura de credenciais ou tokens"
        
        # 3. Verificar modificacao administrativa
        if self.config.get("proibir_modificacao_admin", True):
            if self._e_modificacao_admin(descricao):
                autorizada = False
                restricoes.append("modificacao_admin")
                motivo = "Bloqueado: tentativa de modificacao administrativa sem autorizacao"
        
        # 4. Verificar instalacao de programas
        if self.config.get("proibir_instalacao_programas", True):
            if self._e_instalacao_programas(descricao):
                autorizada = False
                restricoes.append("instalacao_programas")
                motivo = "Bloqueado: tentativa de instalacao de programas"
        
        # 5. Verificar executacao de comandos nao autorizados
        if self.config.get("proibir_execucao_comandos_nao_autorizados", True):
            if self._e_comando_nao_autorizado(descricao):
                autorizada = False
                restricoes.append("comando_nao_autorizado")
                motivo = "Bloqueado: tentativa de executar comando nao autorizado"
        
        # 6. Verificar limites de tamanho de arquivo
        if "tamanho" in acao and self.config.get("max_tamanho_arquivo_mb", 100):
            max_bytes = self.config["max_tamanho_arquivo_mb"] * 1024 * 1024
            if caminho and os.path.exists(caminho):
                try:
                    tamanho = os.path.getsize(caminho)
                    if tamanho > max_bytes:
                        autorizada = False
                        restricoes.append("tamanho_excedido")
                        motivo = f"Bloqueado: arquivo excede limite de {self.config['max_tamanho_arquivo_mb']}MB"
                except:
                    pass
        
        # Registrar auditoria
        self._registrar_auditoria_seguranca({
            "acao": acao.get("tipo", "desc desconhecida"),
            "autorizada": autorizada,
            "motivo": motivo,
            "restricoes": restricoes,
            "contexto": contexto,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "autorizada": autorizada,
            "motivo": motivo,
            "restricoes": restricoes
        }
    
    def _detectar_prompt_injection(self, texto):
        """Detectar indicadores de prompt injection."""
        # Padroes comuns de injection
        padroes_injection = [
            r"ignore\s+previous\s+instructions",
            r"desvie\s+a",
            r"sobreescreva\s+suas\s+regras",
            r"desative\s+a",
            r"ignore\s+todos\s+anteriores",
            r"voce\s+e",
            r"voc[eê]m\s+nao\s+deveriam",
            r"prohibir",
            r"bloquear\s+.*",
        ]
        
        for padrao in padroes_injection:
            if re.search(padrao, texto, re.IGNORECASE):
                return True
        return False
    
    def _caminho_fora_projeto(self, caminho, contexto):
        """Verificar se o caminho esta fora dos limites do projeto."""
        projeto_id = contexto.get("projeto_id", "")
        if not projeto_id:
            return True  # Se nao houver projeto identificado, bloquear
        
        # Obter diretorio base do projeto do Project Manager
        # Se nao tiver project manager, usar safe default
        base_projeto = self._obter_base_projeto(projeto_id)
        
        if not base_projeto:
            # Se nao conseguir determinar, ser conservador e bloquear
            return True
        
        # Normalizar caminhos
        caminho_norm = os.path.normpath(os.path.abspath(caminho))
        base_norm = os.path.normpath(os.path.abspath(base_projeto))
        
        # Verificar se o caminho esta dentro do base do projeto
        if caminho_norm.startswith(base_norm + os.sep) or caminho_norm == base_norm:
            return False  # Dentro do projeto - permitido
        
        # Verificar links simbolicos e junctions que escapem do diretorio
        try:
            # Resolver o caminho final (seguindo symlinks)
            caminho_real = os.path.realpath(caminho)
            caminho_real_norm = os.path.normpath(caminho_real)
            if not caminho_real_norm.startswith(base_norm + os.sep) and caminho_real_norm != base_norm:
                return True  # Link aponta para fora
        except Exception:
            pass
        
        return False  # Esta dentro (ou nao conseguimos determinar)
    
    def _obter_base_projeto(self, projeto_id):
        """Obter o diretorio base de um projeto do Project Manager."""
        if self.project_manager:
            # Procurar configuracao do projeto
            try:
                # O Project Manager tem configuracao de projetos com caminhos
                projetos = self.project_manager.config.get("projetos", {})
                if projeto_id in projetos:
                    # Retornar o caminho base se existir
                    return projetos[projeto_id].get("caminho_base", None)
            except:
                pass
        return None
    
    def _contem_credenciais(self, texto):
        """Verificar se o texto contem credenciais, tokens ou chaves API."""
        padroes_credenciais = [
            r"sk-[a-zA-Z0-9]{8,}",  # OpenAI API keys
            r"[a-zA-Z]{3,}:[a-zA-Z0-9]{32,}",  # chaves genericas
            r"Bearer\s+[a-zA-Z0-9\-._~+/]+",  # tokens portador
            r"(?i)api_key\s*=\s*['\"][^'\"]{8,}['\"]",  # api_key assignments
            r"(?i)auth_token\s*=\s*['\"][^'\"]{10,}['\"]",  # auth tokens
        ]
        
        for padrao in padroes_credenciais:
            if re.search(padrao, texto):
                return True
        return False
    
    def _e_modificacao_admin(self, descricao):
        """Verificar se eh uma modificacao administrativa."""
        padroes_admin = [
            r"chmod\s+777",
            r"chown",
            r"sudo\s+",
            r"aplicar\s+acl",
            r"reseta.*acl",
            r"inheritance:r",
        ]
        
        for padrao in padroes_admin:
            if re.search(padrao, descricao, re.IGNORECASE):
                return True
        return False
    
    def _e_instalacao_programas(self, descricao):
        """Verificar se eh tentativa de instalacao de programas."""
        padroes_instal = [
            r"pip\s+install",
            r"npm\s+install",
            r"apt-get\s+install",
            r"yum\s+install",
            r"powershell.*install",
            r"co\.install",
        ]
        
        for padrao in padroes_instal:
            if re.search(padrao, descricao, re.IGNORECASE):
                return True
        return False
    
    def _e_comando_nao_autorizado(self, descricao):
        """Verificar se eh comando nao autorizado."""
        padroes_comando = [
            r"rm\s+-rf",
            r">\s*/etc/passwd",
            r">\s*&>/dev/null",
            r"dsf",
            r":\(\s*>",
            r"format",
            r"del\s+/f/q",
        ]
        
        for padrao in padroes_comando:
            if re.search(padrao, descricao, re.IGNORECASE):
                return True
        return False
    
    def _registrar_auditoria_seguranca(self, entry):
        """Registrar entrada no log de seguranca."""
        log_path = self.base_dir / "logs" / "security_audit.jsonl"
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Erro no log de seguranca: {e}")


# Instancia global
try:
    global_security_controller = SecurityController()
except Exception as e:
    logger.error(f"Erro ao instanciar global SecurityController: {e}")
    global_security_controller = None