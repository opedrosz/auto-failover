# AUTO FAILOVER V1.0.4

### V1.0.6

Execute `python cli.py test` e `python cli.py demo-local` no Windows com Python 3.9 ou superior. A demo usa dois provedores simulados, processos Python reais e templates públicos. Uma falha controlada dispara a troca automática. A homologação com inferência externa está pendente.

Veja [Configuração](#configuração) e o [relatório V1.0.6](reports/AUTO-FAILOVER-V1.0.6-FINAL-REPORT.md).

#### Configuração

Use `.env.example` como referência para configurar `AUTO_FAILOVER_BASE` na sessão. A CLI não lê o arquivo automaticamente. Em uma base exclusiva, copie `examples/model_selector_config.example.json` para `config/model_selector_config.json` e `examples/provider_registry.example.json` para `data/provider_registry.json`, sempre dentro dessa base. Execute a demo para validar os dois exemplos sem escrever na instalação original.


Infraestrutura universal de desenvolvimento multiagente com failover automatico.

## Local
C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover

## Comandos
python cli.py doctor     - diagnostico
python cli.py validate   - validar configuracao
python cli.py providers  - listar provedores
python cli.py models     - listar modelos
python cli.py status     - estado atual
python cli.py test       - executar 70 cenarios
python cli.py demo       - demonstracao multiagente
python cli.py pause/resume/stope/recover <task_id>

## Scripts Windows
Iniciar-AutoFailover.bat, Status-AutoFailover.bat, Parar-AutoFailover.bat, Testar-AutoFailover.bat

## Seguranca
Orcamento padrao R$ 0,00. Apenas modelos comprovadamente gratuitos. Dados sinteticos. Sem credenciais em logs.
