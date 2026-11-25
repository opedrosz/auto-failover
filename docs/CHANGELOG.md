# CHANGELOG — AUTO FAILOVER

## V1.0.4 (25/11/2026) — CONSOLIDAÇÃO ATUAL

### Correções (17 bugs reais)
- 6 erros de sintaxe em failover_manager, cost_controller, health_monitor,
  config_validator, stop_controller, task_recovery
- `import os` ausente em 10 módulos
- `hashlib` ausente no orchestrator
- métodos com nomes inválidos (espaços, duplo underscore)
- `avisos` não definido no ConfigValidator (11 ocorrências)
- recuperação de checkpoint corrompido (usa anterior)
- limite fixo de 3 checkpoints → configurável/ilimitado
- aliases `opencode`/`google` no Provider Registry
- modelos `opencode/*-free` reconhecidos como gratuitos
- categorização de falhas 401/403

### Funcionalidades adicionadas
- Supervisor independente (`supervisor/`) com subprocess Windows
- Adaptador real OpenCode (`adapters/opencode_adapter.py`) com 9 verificações financeiras
- CLI funcional (`cli.py`) + 4 scripts BAT
- Suíte de 70 cenários (`tests/test_scenarios_v104.py`)
- Demonstração multiagente real (`demo/`)
- Homologação externa limitada (2 chamadas reais, custo $0)
- `.gitignore` para proteção de dados sensíveis
- Documentos STATUS, HANDOFF, DECISIONS

### Evidências
- 70/70 testes aprovados
- 2 provedores homologados (modelos hy4-flash-free, beam-free)
- Demo multiagente concluída com sucesso
- 0 modificações em projetos externos

## V1.0.3 (24/11/2026)
- 15 componentes declarados, mas 6 não compilavam (descoberto na V1.0.4)
- 15 documentos alegados, mas ausentes (criados na V1.0.4)
- "48 testes aprovados, 2 avisos" sem evidência verificável

## V1.0.2 (24/11/2026)
- Protótipo inicial em `C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover\`
- 9 diretórios de componentes

## V1.0.1 (24/11/2026)
- Auditoria corrigida: provedores reais, Anthropic fora da cadeia, prioridade zero-custo

## V1.0.0 (24/11/2026)
- Auditoria inicial (escopo corrigido posteriormente)
