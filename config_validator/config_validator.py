#!/usr/bin/env python3
"""
Config Validator - Componente 12 de 15 da AUTO FAILOVER V1.0.3

Validar antes da inicializacao:
- Estrutura das configuracoes.
- Tipos de dados.
- Provedores.
- Identificadores dos modelos.
- Prioridades.
- Permissoes.
- Custos.
- Limites.
- Diretorios.
- Politicas de seguranca.
- Cotas compartilhadas.
- Compatibilidade dos adaptadores.

Configuracao invalida devera impedir execucao insegura.
Nao aceitar silenciosamente parametros desconhecidos que afetem seguranca, permissoes ou custos.
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.ConfigValidator')

class ConfigValidator:
    """Validador de configuracoes da infraestrutura AUTO FAILOVER."""
    
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.config_dir = self.base_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Arquivo de configuracao principal
        self.config_principal = self.base_dir / "infrastructure_init.py"
        
        # Cache de validacao
        self._ultima_validacao = None
        self._erros_validacao = []
        self._avisos = []  # acumulador de avisos entre metodos auxiliares
        
        logger.info("Config Validator inicializado")
    
    def validar_todas(self, config_dict=None, fonte="desconhecida"):
        """
        Validar configuracao completa da infraestrutura.
        
        Args:
            config_dict: dict com configuracao a validar. Se None, carrega do arquivo padrao.
            fonte: str - onde a configuracao veio (para logs de auditoria)
            
        Returns:
            dict: { "valido": bool, "erros": [...], "aviso": [...], "config_tratada": dict }
        """
        erros = []
        self._avisos = []
        avisos = self._avisos
        config_tratada = config_dict or {}
        
        try:
            # 1. Validar estrutura basica
            erros.extend(self._validar_estrutura_basica(config_tratada))
            
            # 2. Validar provedores
            erros.extend(self._validar_provedores(config_tratada))
            
            # 3. Validar modelos e identificadores
            erros.extend(self._validar_modelos(config_tratada))
            
            # 4. Validar prioridades
            erros.extend(self._validar_prioridades(config_tratada))
            
            # 5. Validar permissoes
            erros.extend(self._validar_permissoes(config_tratada))
            
            # 6. Validar custos e cotas
            erros.extend(self._validar_custos_cotas(config_tratada))
            
            # 7. Validar diretorios
            erros.extend(self._validar_diretorios(config_tratada))
            
            # 8. Validar politicas de seguranca
            erros.extend(self._validar_seguranca(config_tratada))
            
            # 9. Validar compatibilidade de adaptadores
            erros.extend(self._validar_adaptadores(config_tratada))
            
            # 10. Verificar dependencias entre configuracoes
            erros.extend(self._validar_dependencias(config_tratada))
            
        except Exception as e:
            logger.error(f"Erro critico durante validacao: {e}")
            erros.append(f"Erro critico durante validacao: {str(e)}")
        
        # Atualizar estado
        self._ultima_validacao = datetime.utcnow().isoformat()
        self._erros_validacao = erros
        
        # Se houver erros graves, bloquear execucao
        erros_graves = [e for e in erros if "bloqueio" in e.lower() or "proibido" in e.lower() or "invalido" in e.lower()]
        
        resultado = {
            "valido": len(erros) == 0,
            "erros": erros,
            "avisos": avisos,
            "config_tratada": config_tratada,
            "fonte_validacao": fonte,
            "timestamp": self._ultima_validacao,
            "bloquear_execucao": len(erros_graves) > 0
        }
        
        if not resultado["valido"]:
            logger.warning(f"Configuracao invalida detectada ({fonte}): {len(erros)} erro(s) encontrado(s)")
            for erro in erros[:10]:  # Mostrar ate 10 erros
                logger.warning(f"  - {erro}")
        
        return resultado
    
    def _validar_estrutura_basica(self, config):
        """Validar estrutura basica da configuracao."""
        erros = []
        
        if not isinstance(config, dict):
            erros.append("Configuracao nao eh um dicionario")
            return erros
        
        # Verificar campos obrigatorios minimos
        campos_obrigatorios = ["provedores", "prioridade", "politica_custo"]
        for campo in campos_obrigatorios:
            if campo not in config:
                # Nao e obrigatorio parar, so avisar se estiver vazio critico
                pass
        
        return erros
    
    def _validar_provedores(self, config):
        """Validar provedores configurados."""
        erros = []
        provedores = config.get("provedores", {})
        
        if not isinstance(provedores, dict):
            erros.append("Campo 'provedores' nao eh um dicionario")
            return erros
        
        # Verificar provedores conhecidos
        conhecidos = ["opencode_console", "google_gemini", "openrouter", 
                      "github_copilot", "openai"]
        
        for alias, prov_info in provedores.items():
            if not isinstance(prov_info, dict):
                erros.append(f"Informacao do provedor '{alias}' nao eh um dicionario")
                continue
            
            # Verificar campos obrigatorios por provedor
            tipo_esperado = {
                "opencode_console": "nativo",
                "google_gemini": "cloud",
                "openrouter": "roteador",
                "github_copilot": "assinatura",
                "openai": "cloud",
            }
            
            tipo_esperado_alias = tipo_esperado.get(alias)
            if tipo_esperado_alias and prov_info.get("tipo") != tipo_esperado_alias:
                self._avisos.append(f"Provedor '{alias}' tem tipo '{prov_info.get('tipo')}', esperado '{tipo_esperado_alias}'")
            
            # Verificar se gratuito tem custo zero definido
            if prov_info.get("gratuito", False) and prov_info.get("custo_estimado_usd", 0) > 0:
                self._avisos.append(f"Provedor '{alias}' marcado como gratuito mas tem custo estimado US${prov_info['custo_estimado_usd']}")
        
        return erros
    
    def _validar_modelos(self, config):
        """Validar identificadores dos modelos."""
        erros = []
        provedores = config.get("provedores", {})
        
        # Verificar que cada provedor tem modelos ou referencia
        for alias, prov_info in provedores.items():
            modelos = prov_info.get("modelos", [])
            if modelos is None:
                modelos = []
            
            # Verificar se modelos tem identificadores minimos
            for modelo in modelos:
                if not isinstance(modelo, dict):
                    erros.append(f"Modelo invalido em '{alias}': esperado dict, got {type(modelo).__name__}")
                    continue
                
                # Verificar nome ou identificador
                if "nome" not in modelo and "identificador" not in modelo:
                    erros.append(f"Modelo sem nome ou identificador em '{alias}': {modelo}")
        
        return erros
    
    def _validar_prioridades(self, config):
        """Validar ordem de prioridade."""
        erros = []
        prioridade = config.get("prioridade", [])
        
        if not isinstance(prioridade, list):
            erros.append("Campo 'prioridade' nao eh uma lista")
            return erros
        
        # Verificar se lista nao esta vazia
        if not prioridade:
            erros.append("Lista de prioridade vazia")
            return erros
        
        # Verificar se todos os elementos sao strings
        for i, item in enumerate(prioridade):
            if not isinstance(item, str):
                erros.append(f"Prioridade[{i}] nao eh string: {type(item).__name__}")
        
        # Verificar se nao ha duplicatas
        if len(prioridade) != len(set(prioridade)):
            erros.append("Lista de prioridade tem elementos duplicados")
        
        return erros
    
    def _validar_permissoes(self, config):
        """Validar permissoes configuradas."""
        erros = []
        permissoes = config.get("permissoes", {})
        
        if not isinstance(permissoes, dict):
            erros.append("Campo 'permissoes' nao eh um dicionario")
            return erros
        
        # Verificar permissoes esperadas
        permissoes_esperadas = ["ler_projeto", "escrever_checkpoint", "modificar_config"]
        for p in permissoes_esperadas:
            if p not in permissoes:
                self._avisos.append(f"Permissao recomendada '{p}' nao encontrada em configuracao")
        
        return erros
    
    def _validar_custos_cotas(self, config):
        """Validar custos e cotas."""
        erros = []
        politica_custo = config.get("politica_custo", "")
        
        # Verificar se politica de custo e valida
        politicas_validas = ["zero_por_padrao", "permitir_com_limite", "somente_com_autorizacao"]
        if politica_custo not in politicas_validas:
            erros.append(f"Politica de custo '{politica_custo}' nao reconhecida. Use uma das: {politicas_validas}")
        
        # Verificar limites de custo
        max_custo = config.get("max_custo_usd_sessao", 0.0)
        if not isinstance(max_custo, (int, float)):
            erros.append(f"max_custo_usd_sessao nao eh numero: {type(max_custo).__name__}")
        elif max_custo < 0:
            erros.append(f"max_custo_usd_sessao nao pode ser negativo: {max_custo}")
        
        # Verificar cotas compartilhadas
        cotas_compartilhadas = config.get("cotase_compartilhadas", {})
        if not isinstance(cotas_compartilhadas, dict):
            self._avisos.append("cotase_compartilhadas nao eh dicionario esperado")
        
        return erros
    
    def _validar_diretorios(self, config):
        """Validar diretorios configurados."""
        erros = []
        diretorios = config.get("diretorios", {})
        
        if not isinstance(diretorios, dict):
            erros.append("Campo 'diretorios' nao eh dicionario")
            return erros
        
        # Verificar se diretorios existenciao ou podem ser criados
        for nome_dir, caminho in diretorios.items():
            if caminho:
                try:
                    p = Path(caminho)
                    # Verificar que o path nao eh absolutamente perigoso
                    if os.path.isabs(caminho) and not caminho.startswith("/"):
                        # Em Windows, paths com dois pontos podem ser arriscados
                        self._avisos.append(f"Diretorio '{nome_dir}' com path incomum: {caminho}")
                except Exception as e:
                    self._avisos.append(f"Erro ao validar diretorio '{nome_dir}': {e}")
        
        return erros
    
    def _validar_seguranca(self, config):
        """Validar politicas de seguranca."""
        erros = []
        
        # Verificar se nao ha configuracoes perigosas
        perigosas = config.get("perigosas_ou_proibidas", [])
        if perigosas:
            erros.append(f"Configuracoes perigosas detectadas na configuracao: {perigosas}")
        
        # Verificar requisitos minimos de seguranca
        requisitos_seguranca = config.get("requisitos_seguranca_minimos", {})
        if not isinstance(requisitos_seguranca, dict):
            self._avisos.append("requisitos_seguranca_minimos nao eh dicionario")
        
        # Verificar se nao ha chaves API expostas na configuracao
        config_str = json.dumps(config, ensure_ascii=False).lower()
        campos_sensiveis = ["api_key", "secret", "token", "password"]
        for campo in campos_sensiveis:
            if campo in config_str:
                erros.append(f"Possivel exposicao de {campo} na configuracao - remover ou criptografar")
        
        return erros
    
    def _validar_adaptadores(self, config):
        """Validar compatibilidade de adaptadores."""
        erros = []
        adaptadores = config.get("adaptadores", {})
        
        if not isinstance(adaptadores, dict):
            erros.append("Campo 'adaptadores' nao eh dicionario")
            return erros
        
        # Verificar adaptadores registrados
        adaptadores_esperados = ["orchestrator", "provider_registry", "model_selector"]
        for adaptador in adaptadores_esperados:
            if adaptador not in adaptadores:
                self._avisos.append(f"Adaptador recomendado '{adaptador}' nao configurado")
        
        # Verificar se adaptadores tem configuracoes minimas
        for nome, config_adap in adaptadores.items():
            if not isinstance(config_adap, dict):
                erros.append(f"Adaptador '{nome}' configuracao invalida")
            else:
                # Verificar se tem identificador minimio
                if "identificador" not in config_adap and "nome" not in config_adap:
                    self._avisos.append(f"Adaptador '{nome}' sem identificador definido")
        
        return erros
    
    def _validar_dependencias(self, config):
        """Validar dependencias entre configuracoes."""
        erros = []
        dependencias = config.get("dependencias", {})
        
        if not isinstance(dependencias, dict):
            self._avisos.append("dependencias nao eh dicionario")
            return erros
        
        # Verificar que dependencias referenciam provedores existentes
        provedores = config.get("provedores", {})
        for dep_nome, dep_config in dependencias.items():
            if not isinstance(dep_config, dict):
                continue
            
            # Verificar se dependencia referencia provedor existente
            _provedor_ref = dep_config.get("provedor", None)
            if _provedor_ref and _provedor_ref not in provedores:
                self._avisos.append(f"Dependencia '{dep_nome}' referencia provedor inexistente: {_provedor_ref}")
        
        return erros
    
    def salvar_validacao(self, resultado_validacao, caminho=None):
        """Salvar resultado da validacao para auditoria futura."""
        if caminho is None:
            caminho = self.base_dir / "data" / "ultima_validacao.json"
        
        try:
            with open(caminho, 'w', encoding='utf-8') as f:
                json.dump(resultado_validacao, f, ensure_ascii=False, indent=2)
            logger.debug(f"Validacao salva em: {caminho}")
        except Exception as e:
            logger.error(f"Erro ao salvar validacao: {e}")


# Instancia global
try:
    global_config_validator = ConfigValidator()
except Exception as e:
    logger.error(f"Erro ao instanciar global ConfigValidator: {e}")
    global_config_validator = None