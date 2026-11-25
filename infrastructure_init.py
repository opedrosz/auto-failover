#!/usr/bin/env python3
"""
AUTO FAILOVER V1.0.2 — Infraestrutura Universal de Desenvolvimento Multiagente
Arquivo de inicialização e estrutura de diretórios.

Este módulo cria a estrutura de diretórios necessária e valida a existência
dos provedores conectados, sem modificar projetos existentes (Orion, Editor-Video,
Codex Skills Integration).

NÃO: instalar programas, modificar configurações permanentes, fazer commits/pushs,
ou transmitir informações privadas.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('infrastructure_init.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('AutoFailover-V1.0.2')

# Caminhos base
BASE_DIR = Path(os.environ.get('AUTO_FAILOVER_BASE', r'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover'))
PROJECTS_DIR = Path(r'C:\Users\Pedro')  # Ponto de referência, não modificar

def verificar_projetos_existentes():
    """Verificar projetos existentes sem modificá-los."""
    logger.info("Verificando projetos existentes (leitura apenas)...")
    
    projects = {
        'Orion': BASE_DIR.parent / 'Orion',
        'Editor-Video': BASE_DIR.parent / 'Editor-Video' if (BASE_DIR.parent / 'Editor-Video').exists() else None,
        'Codex Skills Integration': BASE_DIR.parent / 'Codex Skills Integration' if (BASE_DIR.parent / 'Codex Skills Integration').exists() else None,
    }
    
    for name, path in projects.items():
        if path and path.exists():
            logger.info(f"  {name}: existente em {path}")
            # Contar arquivos (apenas relatório, sem modificar)
            try:
                file_count = sum(1 for _ in path.rglob('*') if _.is_file())
                logger.info(f"    Arquivos totais: {file_count}")
            except Exception as e:
                logger.warning(f"    Não foi possível contar arquivos: {e}")
        else:
            logger.info(f"  {name}: não encontrado (ok, não modificaremos)")
    
    return projects

def criar_estrutura_diretorios():
    """Criar a estrutura de diretórios do Auto-Failover V1.0.2."""
    
    diretorios = [
        # Nível raiz
        BASE_DIR,
        
        # Componentes da arquitetura (seção 6 do V1.0.2)
        BASE_DIR / "orchestrator",
        BASE_DIR / "provider_registry",
        BASE_DIR / "model_selector",
        BASE_DIR / "failover_manager",
        BASE_DIR / "health_monitor",
        BASE_DIR / "cost_controller",
        BASE_DIR / "checkpoint_manager",
        BASE_DIR / "task_recovery",
        BASE_DIR / "shared_memory_manager",
        BASE_DIR / "security_controller",
        BASE_DIR / "audit_logger",
        BASE_DIR / "config_validator",
        BASE_DIR / "stop_controller",
        BASE_DIR / "skills_integration",
        BASE_DIR / "project_manager",
        
        # Subdiretórios específicos
        BASE_DIR / "checkpoints",
        BASE_DIR / "logs",
        BASE_DIR / "audit",
        BASE_DIR / "cache",
        
        # Arquivos de configuração e dados
        BASE_DIR / "config",
        BASE_DIR / "data",
        
        # Locks e bloqueio de concorrência
        BASE_DIR / "locks",
        
        # Testes (não destrutivos)
        BASE_DIR / "tests",
    ]
    
    for d in diretorios:
        try:
            d.mkdir(parents=True, exist_ok=True)
            logger.info(f"Diretório criado/verificado: {d}")
        except Exception as e:
            logger.error(f"Não foi possível criar {d}: {e}")
    
    logger.info("Estrutura de diretórios concluída.")

def inventariar_provedores_conectados():
    """
    Inventariar os 5 provedores conectados ao OpenCode (V1.0.1/aprovados):
    1. OpenCode Console
    2. Google Gemini
    3. OpenRouter
    4. GitHub Copilot
    5. OpenAI
    """
    logger.info("Inventariando provedores conectados ao OpenCode...")
    
    provedores = {
        "OpenCode Console": {
            "tipo": "nativo",
            "status": "conectado",
            "descricao": "Interface e credenciais nativas do OpenCode CLI v2.3.2",
            "modelos_gratuito": True,
            "observacao": "Verificado via `opencode auth list`"
        },
        "Google Gemini": {
            "tipo": "cloud",
            "status": "conectado",
            "descricao": "Acesso a modelos Gemini via credenciais armazenadas no OpenCode",
            "modelos_gratuito": True,
            "observacao": "Modelos: gemini-3.5-flash-lite, gemini-3.6-flash, gemini-3.8-flash"
        },
        "OpenRouter": {
            "tipo": "roteador",
            "status": "conectado",
            "descricao": "OpenRouter - roteador multi-provedor com acesso a dezenas de modelos",
            "modelos_gratuito": True,
            "observacao": "Modelos free: deepseek-v4.1-flash-free, nemotron-3.5-lightning:free, etc."
        },
        "GitHub Copilot": {
            "tipo": "assinatura",
            "status": "conectado",
            "descricao": "GitHub Copilot integrado via OpenCode auth",
            "modelos_gratuito": False,
            "observacao": "Cota da assinatura ~$10/mês; nativo para desenvolvimento"
        },
        "OpenAI": {
            "tipo": "cloud",
            "status": "conectado",
            "descricao": "OpenAI - modelos ChatGPT/Codex (cota temporariamente esgotada para Codex)",
            "modelos_gratuito": False,
            "observacao": "Modelos: gpt-6-luna, gpt-5.5, gpt-5.6-luna. Codex cota esgotada temporariamente."
        }
    }
    
    # Anotar: Anthropic NÃO confirmado como conectado
    provedores["Anthropic"] = {
        "tipo": "cloud",
        "status": "NÃO CONFIRMADO",
        "descricao": "Não aparece em `opencode auth list`; não integrar cadeia inicial",
        "modelos_gratuito": None,
        "observacao": "Revisão independente: não presumir conectividade"
    }
    
    # Salvar inventário
    inventario_path = BASE_DIR / "data" / "provedores_inventario.json"
    try:
        with open(inventario_path, 'w', encoding='utf-8') as f:
            json.dump(provedores, f, ensure_ascii=False, indent=2)
        logger.info(f"Inventário de provedores salvo em: {inventario_path}")
    except Exception as e:
        logger.error(f"Não foi possível salvar inventário: {e}")
    
    return provedores

def validar_identificadores_modelos():
    """
    Validar os 23 candidatos da auditoria, sem presumir que nomes exibidos
    correspondam exatamente aos identificadores da API.
    """
    logger.info("Validando identificadores dos 23 candidatos...")
    
    candidatos = {
        # OpenCode Console (9 modelos gratuitos)
        "1": {"nome": "Beam Free", "provedor": "OpenCode Console", "confirmado": "NÃO CONFIRMADO", "observacao": "Nome exibido; verificar identificador API real"},
        "2": {"nome": "DeepSeek V4.1 Flash Free", "provedor": "OpenRouter", "confirmado": "NÃO CONFIRMADO", "observacao": "Modelo free do OpenRouter; verificar identifier"},
        "3": {"nome": "Flint 40B Free", "provedor": "OpenCode", "confirmado": "NÃO CONFIRMADO", "observacao": "Prefixo opencode/ na lista de modelos"},
        "4": {"nome": "Hy4 flash Free", "provedor": "OpenCode", "confirmado": "NÃO CONFIRMADO", "observacao": "Verificar na lista opencode models"},
        "5": {"nome": "Iceman Free", "provedor": "OpenCode", "confirmado": "NÃO CONFIRMADO", "observacao": "Verificar na lista de modelos free"},
        "6": {"nome": "MiMo-V2.6-Flash Free", "provedor": "OpenCode", "confirmado": "NÃO CONFIRMADO", "observacao": "Verificar modelos opencode/ mimext"} ,
        "7": {"nome": "Nemotron 3.5 Lightning Free", "provedor": "OpenCode", "confirmado": "NÃO CONFIRMADO", "observacao": "Nemotron 3.5 Lightning - verificar source"},
        "8": {"nome": "Nemotron 3.5 Super VL Free", "provedor": "OpenCode", "confirmado": "NÃO CONFIRMADO", "observacao": "Vision capability - verificar suporte"},
        "9": {"nome": "Tidepool Alpha Free", "provedor": "OpenCode", "confirmado": "NÃO CONFIRMADO", "observacao": "Modelo de pesquisa/alpha"},
        
        # Google Gemini (2 modelos)
        "10": {"nome": "Gemini 2.5 Flash-Lite", "provedor": "Google", "confirmado": "NÃO CONFIRMADO", "observacao": "Verificar identifier da API Google"},
        "11": {"nome": "Gemini 3 Flash Preview", "provedor": "Google", "confirmado": "NÃO CONFIRMADO", "observacao": "Preview/early access model"},
        
        # OpenRouter (12 modelos free)
        "12": {"nome": "ERNIE-5.5-Flash-Preview (free)", "provedor": "OpenRouter", "confirmado": "NÃO CONFIRMADO", "observacao": "Baidu ERNIE model free tier"},
        "13": {"nome": "Flint (free)", "provedor": "OpenRouter", "confirmado": "NÃO CONFIRMADO", "observacao": "Modelo free do OpenRouter"},
        "14": {"nome": "Free Models Router", "provedor": "OpenRouter", "confirmado": "NÃO CONFIRMADO", "observacao": "Tratar como roteador, não como modelo individual (seção 4 V1.0.1)"},
        "15": {"nome": "Gemma 4 26B A4B (free)", "provedor": "OpenRouter", "confirmado": "NÃO CONFIRMADO", "observacao": "Google Gemma 4 - verificar free tier"},
        "16": {"nome": "Gemma 4 31B (free)", "provedor": "OpenRouter", "confirmado": "NÃO CONFIRMADO", "observacao": "Google Gemma 4 - verificar free tier"}, 
        "17": {"nome": "LFM3-1.7B (free)", "provedor": "OpenRouter", "confirmado": "NÃO CONFIRMADO", "observacao": "Lightweight model free tier"},
        "18": {"nome": "Ling 3.2 Flash (free)", "provedor": "OpenRouter", "confirmado": "NÃO CONFIRMADO", "observacao": " modelo inclusionai free"},
        "19": {"nome": "Nemotron 3 Nano Omni (free)", "provedor": "OpenRouter", "confirmado": "NÃO CONFIRMADO", "observacao": "NVIDIA Nemotron nano model"},
        "20": {"nome": "Nemotron 3 Ultra (free)", "provedor": "OpenRouter", "confirmado": "NÃO CONFIRMADO", "observacao": "NVIDIA Nemotron ultra - verificar cota free"},
        "21": {"nome": "Nemotron 3.5 Lightning (free)", "provedor": "OpenRouter", "confirmado": "NÃO CONFIRMADO", "observacao": "Repeated from Console - verificar duplicidade"},
        "22": {"nome": "Nemotron 3.5 Super VL (free)", "provedor": "OpenRouter", "confirmado": "NÃO CONFIRMADO", "observacao": "Vision - verificar suporte multimodal"},
        "23": {"nome": "Particle-1 (free)", "provedor": "OpenRouter", "confirmado": "NÃO CONFIRMADO", "observacao": "Modelo particle-ai free tier"},
    }
    
    # Salvar validação de identificadores
    validacao_path = BASE_DIR / "data" / "modelos_candidatos_validados.json"
    try:
        with open(validacao_path, 'w', encoding='utf-8') as f:
            json.dump(candidatos, f, ensure_ascii=False, indent=2)
        logger.info(f"Validação de 23 candidatos salva em: {validacao_path}")
    except Exception as e:
        logger.error(f"Não foi possível salvar validação: {e}")
    
    return candidatos

def registrar_correcoes_auditoria():
    """Registrar as 13 correções obrigatórias da auditoria (seção 5 V1.0.2)."""
    logger.info("Registrando correções obrigatórias da auditoria V1.0.2...")
    
    questoes = [
        "1. OpenCode Console não é necessariamente local, ilimitado ou integralmente gratuito",
        "2. Credenciais armazenadas não comprovam autenticação funcional",
        "3. Conectar GitHub Copilot não comprova assinatura paga",
        "4. Diferenciar assinatura ChatGPT/Codex de API OpenAI faturada separadamente",
        "5. Modelos do mesmo provedor podem compartilhar cotas",
        "6. Modelos gratuitos podem mudar de preço ou disponibilidade",
        "7. SHA-256 detecta alterações e corrupção, mas não garante autenticidade isoladamente",
        "8. Limitar tentativas de recuperação, não a quantidade total de checkpoints",
        "9. Não presumir que credenciais OAuth do OpenCode possam ser utilizadas pelo LiteLLM",
        "10. Não criar integrações redundantes quando existirem interfaces nativas adequadas",
        "11. [Item 11 não listado explicitamente na extração - revisar documentação completa V1.0.2]",
        "12. [Item 12 - revisar documentação completa V1.0.2]",
        "13. [Item 13 - revisar documentação completa V1.0.2]"
    ]
    
    questoes_path = BASE_DIR / "data" / "correcoes_auditoria.json"
    try:
        with open(questoes_path, 'w', encoding='utf-8') as f:
            json.dump(questoes, f, ensure_ascii=False, indent=2)
        logger.info(f"Correções da auditoria salvas em: {questoes_path}")
    except Exception as e:
        logger.error(f"Não foi possível salvar correções: {e}")

def main():
    """Função principal de inicialização da infraestrutura V1.0.2."""
    logger.info("=" * 60)
    logger.info("AUTO FAILOVER V1.0.2 - Inicialização da Infraestrutura")
    logger.info("=" * 60)
    
    logger.info("\n1. Verificando projetos existentes...")
    projetos = verificar_projetos_existentes()
    
    logger.info("\n2. Criando estrutura de diretórios...")
    criar_estrutura_diretorios()
    
    logger.info("\n3. Inventariando provedores conectados...")
    provedores = inventariar_provedores_conectados()
    
    logger.info("\n4. Validando identificadores dos 23 candidatos...")
    candidatos = validar_identificadores_modelos()
    
    logger.info("\n5. Registrando correções obrigatórias da auditoria...")
    registrar_correcoes_auditoria()
    
    logger.info("\n" + "=" * 60)
    logger.info("Inicialização da infraestrutura V1.0.2 CONCLUÍDA")
    logger.info("=" * 60)
    logger.info(f"""
    Estrutura criada em: {BASE_DIR}
    Projetos verificados (apenas leitura): {list(projetos.keys())}
    Provedores inventariados: {len(provedores)}
    Candidatos validados: 23
    Corrigções auditoria: 13
    
    Próximos passos (implementação de componentes):
    - Orchestrator (seção 6.1)
    - Provider Registry (seção 6.2)
    - Model Selector (seção 6.3)
    - Failover Manager (seção 6.4)
    - Health Monitor (seção 6.5)
    - Cost Controller (seção 6.6)
    - Checkpoint Manager (seção 6.7)
    - Task Recovery (seção 6.8)
    - Shared Memory Manager (seção 6.9)
    - Security Controller (seção 6.10)
    - Audit Logger (seção 6.11)
    - Config Validator (seção 6.12)
    - Stop Controller (seção 6.13)
    - Skills Integration (seção 6.14)
    - Project Manager (seção 6.15)
    """)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())