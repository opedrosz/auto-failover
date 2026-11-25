#!/usr/bin/env python3
"""
Audit Logger - Componente 11 de 15 da AUTO FAILOVER V1.0.3

Registros estruturados contendo:
- Data e hora.
- Projeto.
- Identificador da tarefa.
- Agente.
- Provedor.
- Modelo.
- Evento.
- Motivo da transição.
- Estado anterior.
- Estado posterior.
- Resultado.
- Identificador do checkpoint.
- Consumo estimado.
- Decisões de segurança.

Sanitizar informações sensíveis.
Nunca registrar: chaves de API, tokens OAuth, senhas, cookies, cabecalhos de autenticacao,
informacoes privadas desnecessarias.
"""

import json
import os
import logging
import hashlib
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('AutoFailover.AuditLogger')

class AuditLogger:
    """Logger de auditoria estruturada para todas as operacoes do sistema."""
    
    def __init__(self, base_dir=None, config=None):
        self.base_dir = Path(base_dir) if base_dir else Path(
            os.environ.get('AUTO_FAILOVER_BASE', 
                          r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover')
        )
        self.config = config or self._carregar_config()
        self.log_dir = self.base_dir / "logs" / "audit"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Tipo de log atual (pode ser rotacionado)
        self.log_tipo_atual = "operacoes"
        self.counter_dia = 0
        self.data_limite = datetime.utcnow().date()
        
        # Caracteristicas de seguranca
        self.campos_proibidos_registro = {
            "api_key", "token", "senha", "oauth", "cookie", 
            "auth_header", "credencial", "secret_key"
        }
        
        logger.info("Audit Logger inicializado")
    
    def _carregar_config(self):
        """Carregar configuracao do Audit Logger."""
        config_path = self.base_dir / "config" / "audit_logger_config.json"
        defaults = {
            "rotacao_dia": True,
            "retencao_dias": 30,
            "sanitizar_dados": True,
            "log_todos_eventos": True,
            "campos_ocultos": ["api_key", "token", "senha"]
        }
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                for key, value in user_config.items():
                    defaults[key] = value
            except:
                pass
        else:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(defaults, f, ensure_ascii=False, indent=2)
        
        return defaults
    
    def _sanitizar_dado(self, dado):
        """Remover ou mascarar informacoes sensiveis de um dicionario."""
        if not isinstance(dado, dict):
            return dado
        
        resultado = {}
        for chave, valor in dado.items():
            # Verificar se a chave indica dado sensivel
            chave_lower = chave.lower()
            is_sensitive = any(p in chave_lower for p in self.campos_proibidos_registro)
            
            if is_sensitive:
                resultado[chave] = "****SANITIZADO****"
            elif isinstance(valor, dict):
                resultado[chave] = self._sanitizar_dado(valor)
            elif isinstance(valor, list):
                resultado[chave] = [self._sanitizar_dado(item) if isinstance(item, dict) else item for item in valor]
            else:
                resultado[chave] = valor
        
        return resultado
    
    def _gerar_nome_arquivo(self):
        """Gerar nome de arquivo baseado na data para rotacao."""
        hoje = datetime.utcnow().date()
        if hoje != self.data_limite:
            self.counter_dia = 0
            self.data_limite = hoje
        nome = f"audit_{hoje.isoformat()}_{self.counter_dia:03d}.jsonl"
        self.counter_dia += 1
        return nome
    
    def registrar_evento(self, evento_dict):
        """
        Registrar um evento de auditoria.
        
        Args:
            evento_dict: dicionario contendo os campos do evento
                - projeto: str
                - task_id: str
                - agente: str
                - provedor: str
                - modelo: str
                - evento: str (descricao do evento)
                - motivo: str (opcional)
                - estado_anterior: dict (opcional)
                - estado_posterior: dict (opcional)
                - resultado: dict (opcional)
                - checkpoint_id: str (opcional)
                - custo_estimado: float (opcional)
                - decisao_seguranca: dict (opcional)
        
        Returns:
            str: caminho do arquivo onde o evento foi registrado
        """
        # Sanitizar dados antes de registrar
        sanitizado = self._sanitizar_dado(evento_dict)
        
        # Adicionar metadados de rotulagem
        sanitizado["_timestamp"] = datetime.utcnow().isoformat()
        sanitizado["_log_tipo"] = self.log_tipo_atual
        sanitizado["_linha_numero"] = self.counter_dia
        
        # Gerar nome de arquivo e escrever
        nome_arquivo = self._gerar_nome_arquivo()
        caminho = self.log_dir / nome_arquivo
        
        try:
            with open(caminho, 'a', encoding='utf-8') as f:
                f.write(json.dumps(sanitizado, ensure_ascii=False) + "\n")
            
            # Atualizar counter
            self.counter_dia += 1
            
            return str(caminho)
        except Exception as e:
            logger.error(f"Erro ao registrar evento de auditoria: {e}")
            return None
    
    def registrar_transicao(self, evento_dict):
        """
        Registrar especificamente uma transicao de agente/provedor/modelo.
        
        Este e um wrapper para registrar_evento com tipo 'transicao'.
        """
        evento_dict["tipo"] = "transicao"
        return self.registrar_evento(evento_dict)
    
    def registrar_checkpoint(self, checkpoint_dict):
        """
        Registrar especificamente a criacao de um checkpoint.
        
        Args:
            checkpoint_dict: dicionario com dados do checkpoint
                - task_id: str
                - stage: str
                - checksum: str
                - motivo: str
                - etc.
        """
        checkpoint_dict["tipo"] = "checkpoint"
        return self.registrar_evento(checkpoint_dict)
    
    def registrar_falha(self, falha_dict):
        """
        Registrar especificamente uma falha.
        
        Args:
            falha_dict: dicionario com informacoes da falha
                - task_id: str
                - provedor: str
                - categoria: str
                - etc.
        """
        falha_dict["tipo"] = "falha"
        return self.registrar_evento(falha_dict)
    
    def get_logs_por_projeto(self, projeto_id, dias=None):
        """Retornar logs filtrados por projeto e periodo."""
        # Procurar nos arquivos de log
        resultados = []
        
        if not self.log_dir.exists():
            return resultados
        
        from datetime import timedelta
        if dias:
            data_limite = datetime.utcnow() - timedelta(days=dias)
        else:
            data_limite = None
        
        for arquivo in self.log_dir.glob("*.jsonl"):
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            # Filtrar por projeto se informado
                            if projeto_id and entry.get("projeto") != projeto_id:
                                continue
                            # Filtrar por data se informado
                            if data_limite:
                                ts = entry.get("_timestamp", "")
                                if ts:
                                    try:
                                        from datetime import datetime as dt
                                        dt_evento = dt.fromisoformat(ts)
                                        if dt_evento < data_limite:
                                            continue
                                    except:
                                        pass
                            resultados.append(entry)
                        except json.JSONDecodeError:
                            continue
            except Exception:
                continue
        
        return resultados
    
    def get_estatisticas(self):
        """Retornar estatisticas resumidas do logger."""
        total_eventos = 0
        tipos_eventos = {}
        projetos = set()
        
        if not self.log_dir.exists():
            return {"total_eventos": 0, "tipos": {}, "projetos": []}
        
        for arquivo in self.log_dir.glob("*.jsonl"):
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            total_eventos += 1
                            
                            # Contar tipos
                            tipo = entry.get("tipo", "desconhecido")
                            tipos_eventos[tipo] = tipos_eventos.get(tipo, 0) + 1
                            
                            # Coletar projetos
                            projeto = entry.get("projeto", None)
                            if projeto:
                                projetos.add(projeto)
                        except json.JSONDecodeError:
                            continue
            except Exception:
                continue
        
        return {
            "total_eventos": total_eventos,
            "tipos_eventos": tipos_eventos,
            "projetos": sorted(list(projetos))
        }


# Instancia global
try:
    global_audit_logger = AuditLogger()
except Exception as e:
    logger.error(f"Erro ao instanciar global AuditLogger: {e}")
    global_audit_logger = None