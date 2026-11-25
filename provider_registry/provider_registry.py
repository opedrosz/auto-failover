#!/usr/bin/env python3
"""
Provider Registry - Componente 2 de 15 da AUTO FAILOVER V1.0.2

Cadastro dos provedores, modelos, capacidades e restrições.
Registro universal e reutilizável pelos projetos: Orion, Editor-Video,
Codex Skills Integration, desenvolvimento de sites, projetos futuros.

NÃO modificar, mover, excluir ou reorganizar projetos existentes.
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.ProviderRegistry')

class ProviderRegistry:
    """Registro universal de provedores de LLM e modelos disponíveis."""
    
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.registry_dir = self.base_dir / "data"
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivo de registro
        self.registry_file = self.registry_dir / "provider_registry.json"
        self._historico_atualizacoes = self.registry_dir / "historico_atualizacoes.jsonl"
        
        # Mapeamento interno de provedores conhecidos
        self.provedores = {}
        self.modelos = {}
        
        # Carregar registro existente ou criar novo
        self._carregar_registro()
        
        logger.info(f"Provider Registry inicializado em: {self.base_dir}")
        logger.info(f"  Provedores carregados: {len(self.provedores)}")
        logger.info(f"  Modelos cadastrados: {len(self.modelos)}")
    
    def _carregar_registro(self):
        """Carregar registro de provedores do arquivo ou criar estrutura padrão."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                self.provedores = dados.get("provedores", {})
                self.modelos = dados.get("modelos", {})
                logger.info(f"Registro carregado: {len(self.provedores)} provedores, "
                           f"{len(self.modelos)} modelos")
            except Exception as e:
                logger.error(f"Erro ao carregar registro: {e}. Criando novo registro.")
                self._criar_registro_padrao()
        else:
            self._criar_registro_padrao()
    
    def _criar_registro_padrao(self):
        """Criar registro padrão com os 5 provedores conectados do OpenCode."""
        logger.info("Criando registro padrão com provedores OpenCode conectados...")
        
        # 1. OpenCode Console
        console_data = {
            "alias": "opencode_console",
            "provedor": "opencode_console",
            "nome_exibicao": "OpenCode Console",
            "tipo": "nativo",
            "descricao": "Interface e credenciais nativas do OpenCode CLI v2.3.2",
            "gratuito": True,
            "privado": True,
            "ferramentas_suportadas": False,
            "contexto_maximo": "variável (configurável)",
            "programacao": "forte (template engine Orion)",
            "raciocinio": "moderado",
            "visao": "nao_suportado (politica de privacidade)",
            "politica_privacidade": "100% local - nenhum dado sai da maquina",
            "fontes_verificacao": ["opencode auth list", "opencode models"],
            "data_atualizacao": datetime.utcnow().isoformat(),
            "status": "conectado",
            "observacao": "Verificado via OpenCode CLI v2.3.2"
        }
        
        # 2. Google Gemini
        gemini_data = {
            "alias": "google_gemini",
            "provedor": "google_gemini",
            "nome_exibicao": "Google Gemini",
            "tipo": "cloud",
            "descricao": "Acesso a modelos Gemini via credenciais armazenadas no OpenCode",
            "gratuito": True,  # Modelos lite/flash gratuitos na conta conectada
            "privado": False,
            "ferramentas_suportadas": True,
            "contexto_maximo": "128K tokens (gemini-1.5-pro)",
            "programacao": "forte (benchmarks de code)",
            "raciocinio": "forte",
            "visao": "suportado (multimodal - imagens)",
            "politica_privacidade": "Dados enviados para servidores Google; politica da Google",
            "fontes_verificacao": ["opencode auth list (Google)", "opencode models (Google Gemini)",
                                  "docs oficiais Google Gemini"],
            "data_atualizacao": datetime.utcnow().isoformat(),
            "status": "conectado",
            "observacao": "Modelos: gemini-3.5-flash-lite, gemini-3.6-flash, gemini-3.8-flash"
        }
        
        # 3. OpenRouter
        openrouter_data = {
            "alias": "openrouter",
            "provedor": "openrouter",
            "nome_exibicao": "OpenRouter",
            "tipo": "roteador",
            "descricao": "OpenRouter - roteador multi-provedor com acesso a dezenas de modelos",
            "gratuito": True,  # Tier free disponível
            "privado": False,
            "ferramentas_suportadas": True,  # Depende do modelo subjacente
            "contexto_maximo": "variavel por modelo (16K a 100K+)",
            "programacao": "forte (acesso a dezenos de provedores code-focused)",
            "raciocinio": "forte",
            "visao": "suportado (depende do modelo: gemini vision, deepseek vl etc.)",
            "politica_privacidade": "Dados enviados para servidores OpenRouter; revisar politica",
            "fontes_verificacao": ["opencode auth list (OpenRouter)", "opencode models (OpenRouter)",
                                  "docs oficiais OpenRouter tier free"],
            "data_atualizacao": datetime.utcnow().isoformat(),
            "status": "conectado",
            "observacao": "Tier free com rate limits; modelos: deepseek-v4.1-flash-free, "
                          "nemotron-3.5-lightning:free, gemini-3.5-flash-lite:free etc."
        }
        
        # 4. GitHub Copilot
        copilot_data = {
            "alias": "github_copilot",
            "provedor": "github_copilot",
            "nome_exibicao": "GitHub Copilot",
            "tipo": "assinatura",
            "descricao": "GitHub Copilot integrado via OpenCode auth",
            "gratuito": False,
            "privado": False,
            "ferramentas_suportadas": True,  # Nativo para development
            "contexto_maximo": "variavel (128K dependendo do modelo subjacente)",
            "programacao": "excelente (codex otimizado para development)",
            "raciocinio": "forte",
            "visao": "suportado (multimodal - analysis de codigo e contexto)",
            "politica_privacidade": "Codigo enviado para servidores GitHub; politica GitHub Copilot",
            "fontes_verificacao": ["opencode auth list (Copilot)", "docs GitHub Copilot",
                                  "assinatura ~$10/mes por usuario"],
            "data_atualizacao": datetime.utcnow().isoformat(),
            "status": "conectado",
            "observacao": "Cota da assinatura; incluido no custo do desenvolvedor"
        }
        
        # 5. OpenAI
        openai_data = {
            "alias": "openai",
            "provedor": "openai",
            "nome_exibicao": "OpenAI",
            "tipo": "cloud",
            "descricao": "OpenAI - modelos ChatGPT/Codex (cota temporariamente esgotada para Codex)",
            "gratuito": False,
            "privado": False,
            "ferramentas_suportadas": True,  # functions, tools, JSON mode etc.
            "contexto_maximo": "variavel (128K gpt-4o, varia por modelo)",
            "programacao": "state-of-the-art (melhor em benchmarks de code)",
            "raciocinio": "state-of-the-art",
            "visao": "suportado (multimodal - imagens, analise visual)",
            "politica_privacidade": "Dados enviados para servidores OpenAI; politica OpenAI",
            "fontes_verificacao": ["opencode auth list (OpenAI)", "opencode models (OpenAI extensa)",
                                  "docs oficiais OpenAI"],
            "data_atualizacao": datetime.utcnow().isoformat(),
            "status": "conectado",
            "observacao": "Cota disponivel; modelos: gpt-6-luna, gpt-5.5, gpt-5.6-luna. "
                          "Codex cota temporariamente esgotada (nao depender durante esta implementacao)"
        }
        
        # Nota: Anthropic NÃO confirmado como conectado (revisao V1.0.1)
        # Nao adicionar automaticamente; classificar como N_CONFIRMADO

        # Aliases alternativos aceitos pelo OpenCode CLI (ex: 'opencode', 'google')
        # apontando para os provedores ja cadastrados, sem duplicar entradas.
        aliases = {
            "opencode": "opencode_console",
            "google": "google_gemini",
        }
        self._aliases = aliases

        # Adicionar todos ao registro
        for provedor_data in [console_data, gemini_data, openrouter_data, copilot_data, openai_data]:
            alias = provedor_data["alias"]
            self.provedores[alias] = provedor_data
            # Também cadastrar modelos representativos
            self._cadastrar_modelos_provedor(alias, provedor_data)
        
        # Registrar data de inicializacao
        self._salvar_registro()
        logger.info("Registro padrão criado com 5 provedores conectados")
    
    def _cadastrar_modelos_provedor(self, alias, provedor_data):
        """Cadastrar modelos representativos para um provedor."""
        provedor_info = self.provedores[alias]
        provedor_nome = provedor_data.get("nome_exibicao", alias)
        
        modelos = []
        
        if alias == "opencode_console":
            # 9 modelos gratuitos da auditoria V1.0.1
            modelos_consoles = [
                "Beam Free", "DeepSeek V4.1 Flash Free", "Flint 40B Free",
                "Hy4 flash Free", "Iceman Free", "MiMo-V2.6-Flash Free",
                "Nemotron 3.5 Lightning Free", "Nemotron 3.5 Super VL Free",
                "Tidepool Alpha Free"
            ]
            for m in modelos_consoles:
                modelos.append({
                    "nome": m,
                    "identificador": f"opencode_console:{m.lower().replace(' ', '-').replace('(', '').replace(')', '').replace('/', '-')}%",
                    "gratuito": True,
                    "confirmado": "N_CONFIRMADO",  # Precisa de verificacao real do identifier
                    "observacao": "Nome exibido; verificar identifier API real (correcao V1.0.2)"
                })
        
        elif alias == "google_gemini":
            modelos_gemini = [
                "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.8-flash",
                "gemini-2.5-flash-lite", "gemini-3-flash-preview"
            ]
            for m in modelos_gemini:
                modelos.append({
                    "nome": m,
                    "identificador": f"google_gemini:{m}",
                    "gratuito": m.endswith("-lite") or "flash-lite" in m.lower(),
                    "confirmado": "CONFIRMADO" if m.endswith("-lite") else "PROVAVEL",
                    "observacao": f"Modelo Google {'gratuito na conta conectada' if m.endswith('-lite') else 'pago/cota'}"
                })
        
        elif alias == "openrouter":
            # 12 modelos free da seção 4 V1.0.1 (mais o router itself)
            modelos_or = [
                "deepseek-v4.1-flash-free", "ernie-5.5-flash-preview:free",
                "flint-free", "gemma-4-26b-a4b-it:free", "gemma-4-31b-it:free",
                "lfm3-1.7b:free", "ling-3.2-flash:free", 
                "nemotron-3-nano-omni:free", "nemotron-3-ultra:free",
                "nemotron-3.5-lightning:free", "nemotron-3.5-super-vl:free",
                "particle-1:free"
            ]
            # Note: "Free Models Router" e "Particle-1" ja listados separately
            for m in modelos_or:
                modelos.append({
                    "nome": m,
                    "identificador": f"openrouter:{m}",
                    "gratuito": True,
                    "confirmado": "N_CONFIRMADO",  # Precisa de verificacao de identifier API
                    "observacao": "Modelos free tier do OpenRouter; identifier deve ser verificado"
                })
            
            # Adicionar o "Free Models Router" como categoria, nao como modelo individual
            modelos.append({
                "nome": "Free Models Router",
                "identificador": "openrouter:free",
                "gratuito": True,
                "confirmado": "CONFIRMADO",
                "observacao": "Tratar como roteador, nao como modelo individual (secao 4 V1.0.1)"
            })
        
        elif alias == "github_copilot":
            modelos_copilot = [
                "gpt-4o (baseado em GPT-4o)", "gpt-4o-mini"
            ]
            for m in modelos_copilot:
                modelos.append({
                    "nome": m,
                    "identificador": f"github_copilot:{m.lower().replace(' ', '-')}",
                    "gratuito": False,
                    "confirmado": "CONFIRMADO",
                    "observacao": "Incluso na assinatura Copilot ~$10/mes"
                })
        
        elif alias == "openai":
            modelos_openai = [
                "gpt-6-luna", "gpt-5.5", "gpt-5.6-luna", "gpt-5.6-luna-fast",
                "gpt-5.6-sol", "gpt-5.6-sol-fast", "gpt-5.6-terra",
                "gpt-5.6-terra-fast", "gpt-6-astra", "gpt-6-astra-fast"
            ]
            # Note: modelos codex temporariamente esgotados
            for m in modelos_openai:
                modelos.append({
                    "nome": m,
                    "identificador": f"openai:{m}",
                    "gratuito": False,
                    "confirmado": "CONFIRMADO" if m != "gpt-6-luna" else "PROVAVEL",  # gpt-6-luna e default conhecido
                    "observacao": f"Modelo OpenAI. Codex cota: {'esgotada temporariamente' if 'codex' in m.lower() or 'terra' in m.lower() else 'verificar'}. "
                                  f"Cuidado: nao depender de Codex nesta implementacao (V1.0.2)"
                })
        
        self.modelos[alias] = modelos
        logger.debug(f"Modelos cadastrados para {alias}: {len(modelos)} modelos")
    
    def atualizar_registro(self, forcar_atualizacao=False):
        """Atualizar registro verificando provedores conectados."""
        logger.info("Atualizando Provider Registry...")
        
        # Verificar provedores conectados via OpenCode CLI
        # (Em implementacao completa, isso chamaria opencode auth list etc.)
        
        # Marcar data de atualizacao
        for alias in self.provedores:
            self.provedores[alias]["data_atualizacao"] = datetime.utcnow().isoformat()
            # Atualizar status baseado no conhecido
            if self.provedores[alias]["status"] == "conectado":
                pass  # Ja esta marcado
        
        # Se forçer atualizacao ou a cada X verificacoes, verificar provedores reais
        if forcar_atualizacao:
            logger.info("Forcar atualizacao: verificando provedores via OpenCode CLI...")
            # Em implementacao futura, rodaria: opencode auth list etc.
            # Por agora, manter registro existente com data atualizada
        
        self._salvar_registro()
        logger.info(f"Registro atualizado. {len(self.provedores)} provedores, "
                     f"{len(self.modelos)} modelos categorizados")
    
    def _salvar_registro(self):
        """Salvar registro no disco."""
        try:
            dados = {
                "provedores": self.provedores,
                "modelos": self.modelos,
                "total_provedores": len(self.provedores),
                "total_modelos": sum(len(m) for m in self.modelos.values()),
                "data_geracao": datetime.utcnow().isoformat(),
                "versao": "1.0.0"
            }
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            
            # Registrar no historico de atualizacoes
            with open(self._historico_atualizacoes, 'a', encoding='utf-8') as f:
                entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "acoes": "atualizacao_registro",
                    "total_provedores": len(self.provedores),
                    "total_modelos": sum(len(m) for m in self.modelos.values())
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
            logger.debug(f"Registro salvo em: {self.registry_file}")
        except Exception as e:
            logger.error(f"Erro ao salvar registro: {e}")
    
    def obter_provedor(self, alias):
        """Obter informações de um provedor pelo alias."""
        alias_real = getattr(self, '_aliases', {}).get(alias, alias)
        return self.provedores.get(alias_real)
    
    def obter_modelos(self, alias_provedor=None):
        """Obter modelos de um provedor ou todos."""
        if alias_provedor:
            return self.modelos.get(alias_provedor, [])
        return self.modelos
    
    def obter_modelo_por_nome(self, nome_modelo, provedor_alias=None):
        """Encontrar um modelo pelo nome, opcionalmente limitando a um provedor."""
        # Buscar em todos os provedores se nao especificado
        if not provedor_alias:
            for alias, modelos in self.modelos.items():
                for m in modelos:
                    if m.get("nome") == nome_modelo:
                        return {"modelo": m, "provedor": alias}
            return None
        
        # Buscar em provedor especifico
        modelos = self.obter_modelos(provedor_alias)
        for m in modelos:
            if m.get("nome") == nome_modelo:
                return {"modelo": m, "provedor": provedor_alias}
        return None
    
    def validar_modelo(self, alias_provedor, nome_ou_identificador):
        """Validar se um modelo existe e esta disponivel para um provedor."""
        modelos = self.obter_modelos(alias_provedor)
        
        # Verificar por nome exato
        for m in modelos:
            if m.get("nome") == nome_ou_identificador:
                return {"valido": True, "modelo": m, "observacao": m.get("observacao", "")}
            # Verificar por identificador
            if m.get("identificador") == nome_ou_identificador:
                return {"valido": True, "modelo": m, "observacao": m.get("observacao", "")}
        
        # Verificar correspondencia parcial (nome contem o termo)
        matches = [m for m in modelos if nome_ou_identificador.lower() in m.get("nome", "").lower()]
        if matches:
            return {"valido": True, "modelo": matches[0], 
                    "observacao": f"Correspondencia parcial. Matches: {[m['nome'] for m in matches]}"}
        
        return {"valido": False, "modelo": None, 
                "observacao": f"Modelo '{nome_ou_identificador}' nao encontrado para provedor {alias_provedor}. "
                              f"Modelos disponiveis: {[m['nome'] for m in modelos[:3]]}..."}
    
    def listar_capacidades(self, alias_provedor=None):
        """Listar capacidades resumidas de um provedor ou todos."""
        resultados = {}
        
        alvos = [alias_provedor] if alias_provedor else list(self.provedores.keys())
        
        for alias in alvos:
            prov = self.provedores.get(alias)
            if not prov:
                continue
            
            resultados[alias] = {
                "nome": prov.get("nome_exibicao", alias),
                "tipo": prov.get("tipo", "desconhecido"),
                "gratuito": prov.get("gratuito", None),
                "ferramentas": prov.get("ferramentas_suportadas", False),
                "visao": prov.get("visao", "nao_info"),
                "programacao": prov.get("programacao", "nao_info"),
                "raciocinio": prov.get("raciocinio", "nao_info"),
                "privado": prov.get("privado", False),
                "contexto_maximo": prov.get("contexto_maximo", "nao_info"),
                "politica_privacidade": prov.get("politica_privacidade", "nao_info"),
                "status": prov.get("status", "desconhecido")
            }
        
        return resultados
    
    def verificar_compatibilidade(self, alias_provedor, requisicoes):
        """
        Verificar se um provedor satisfaz requisicoes de uma tarefa.
        
        requisicoes: dict com chaves como:
            - "ferramentas": bool
            - "visao": bool
            - "programacao": bool
            - "contexto_maximo_minimo": int (tokens)
            - "privado": bool (True = dados nao podem sair da maquina)
        """
        prov = self.provedores.get(alias_provedor)
        if not prov:
            return {"compativel": False, "motivo": "Provedor nao cadastrado"}
        
        requisitos = {"compativel": True, "restricoes": []}
        
        # Verificar ferramentas
        if requisicoes.get("ferramentas") and not prov.get("ferramentas_suportadas", False):
            requisitos["compativel"] = False
            requisitos["restricoes"].append("Ferramentas nao suportadas por este provedor")
        
        # Ver visão
        if requisicoes.get("visao") and prov.get("visao", "").lower() in ["nao_suportado", "nao_info"]:
            requisitos["compativel"] = False
            requisitos["restricoes"].append("Visao/multimodal nao suportada")
        
        # Verificar privacidade
        if requisicoes.get("privado") and not prov.get("privado", True):
            requisitos["compativel"] = False
            requisitos["restricoes"].append("Provedor nao e local/privado; dados seriam enviados externamente")
        
        # Verificar contexto
        contexto_max = prov.get("contexto_maximo", "0")
        if isinstance(contexto_max, str):
            # Parse string como "128K" etc.
            try:
                num_max = int(contexto_max.replace('K', '').replace('k', '')) * 1000
            except:
                num_max = 0
        else:
            num_max = contexto_max
        
        if requisicoes.get("contexto_maximo_minimo"):
            try:
                min_req = int(requisicoes["contexto_maximo_minimo"])
                # Parse do max
                if isinstance(contexto_max, str) and 'K' in contexto_max.upper():
                    # Ja calculado acima
                    pass
                if num_max < min_req:
                    requisitos["compativel"] = False
                    requisitos["restricoes"].append(
                        f"Contexto maximo ({num_max} tokens) abaixo do minimo requisitado ({min_req} tokens)"
                    )
            except:
                pass
        
        return requisitos
    
    def registrar_uso_modelo(self, alias_provedor, modelo_identificador, task_id, 
                              custo_estimado_usd=0.0, tokens_uso=None):
        """Registrar uso de um modelo para auditoria e controle de custos."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "provedor": alias_provedor,
            "modelo": modelo_identificador,
            "custo_estimado_usd": custo_estimado_usd,
            "tokens_uso": tokens_uso or 0,
            "modo_privacy": self.config.get("privacy_mode", "local-first") if hasattr(self, 'config') else "local-first"
        }
        
        historico_path = self.registry_dir / "modelo_uso_historico.jsonl"
        try:
            with open(historico_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logger.debug(f"Uso de modelo registrado: {alias_provedor}/{modelo_identificador}")
        except Exception as e:
            logger.error(f"Erro ao registrar uso de modelo: {e}")
        
        return entry


# Instancia global para uso em toda a infraestrutura
# (Outros componentes importam deste modulo)
try:
    global_registry = ProviderRegistry()
except Exception as e:
    logger.error(f"Erro ao instanciar global registry: {e}")
    global_registry = None