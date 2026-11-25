# Criar scripts BAT e documentacao V1.0.4
$root = 'C:\Users\Pedro\AI-INFRASTRUCTURE\Auto-Failover'

# Scripts BAT
@'
@echo off
REM Iniciar Auto-Failover - diagnostico
python "%~dp0cli.py" doctor
python "%~dp0cli.py" status
pause
'@ | Out-File "$root\Iniciar-AutoFailover.bat" -Encoding ascii

@'
@echo off
python "%~dp0cli.py" status
pause
'@ | Out-File "$root\Status-AutoFailover.bat" -Encoding ascii

@'
@echo off
python "%~dp0cli.py" stop %1
pause
'@ | Out-File "$root\Parar-AutoFailover.bat" -Encoding ascii

@'
@echo off
python "%~dp0cli.py" test
pause
'@ | Out-File "$root\Testar-AutoFailover.bat" -Encoding ascii

# Documentacao
$docs = @{
'README.md' = @'
# AUTO FAILOVER V1.0.4

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
'@

'ARCHITECTURE.md' = @'
# Arquitetura

15 componentes: Orchestrator, Provider Registry, Model Selector, Failover Manager,
Health Monitor, Cost Controller, Checkpoint Manager, Task Recovery, Shared Memory Manager,
Security Controller, Audit Logger, Config Validator, Stop Controller, Skills Integration,
Project Manager.

Supervisor independente (supervisor/) monitora processos filhos via subprocess no Windows,
sobrevivendo ao encerramento da sessao de IA.

Adaptador real (adapters/opencode_adapter.py) usa `opencode run --model <id> --format json --auto`.

Fluxo: tarefa -> checkpoint -> selecao -> inferencia -> deteccao de falha -> failover -> recuperacao.
'@

'PROVIDERS.md' = @'
# Provedores

Conectados via `opencode auth list` (v2.3.2):
1. OpenCode Console
2. Google Gemini
3. OpenRouter
4. GitHub Copilot
5. OpenAI

Anthropic: NAO CONFIRMADO - fora da cadeia inicial.

Modelos gratuitos confirmados via `opencode models` e homologados com dados sinteticos:
- opencode/hy4-flash-free (homologado, resposta "OK")
- opencode/beam-free (homologado)
- opencode/deepseek-v4.1-flash-free
- google/gemini-3.5-flash-lite

Custo zero nao e garantia permanente: modelos podem mudar. Verificar antes de cada uso.
'@

'FAILOVER.md' = @'
# Failover

Categorias: HTTP 429, 5xx, timeout, conexao, autenticacao, credencial expirada,
contexto, modelo indisponivel/incompativel, seguranca, interrupcao manual.

Comportamento: backoff progressivo, Retry-After, circuit breaker (3 falhas),
cooldown, limite 6 tentativas, grupos de cota compartilhada, suspensao segura.

Nao trocar provedor em violacao de seguranca ou recusa legitima.
Falha injetada no demo e SIMULADA - nao esgota cota real.
'@

'CHECKPOINTS.md' = @'
# Checkpoints

Escrita atomica, SHA-256 (detecta alteracao, nao garante autenticade),
historico de versoes, recuperacao de corrupcao (usa checkpoint anterior),
idempotencia, locks e limite configuravel (padrao ilimitado - nao limitar a 3).
'@

'SECURITY.md' = @'
# Seguranca

Controles em Python: validacao de acoes, deteccao de prompt injection,
protecao de credenciais, validacao de caminhos, bloqueio de comandos perigosos,
sanitizacao de logs, isolamento por projeto.

LIMITACAO: modulo Python NAO e sandbox inviolavel. Isolamento efetivo depende
do sistema operacional/executor. Nao declarar seguranca absoluta.
'@

'TESTING.md' = @'
# Testes

70 cenarios em tests/test_scenarios_v104.py.
Tipos: LOCAL_REAL (codigo local real), SIMULADO (mocks), EXTERNO_LEVE (CLI), HOMOLOGACAO_EXTERNA_LIMITADA.

Resultado V1.0.4: 70/70 aprovados (reports/resultados_testes_v104.json).
Homologacao externa: 2 chamadas reais com dados sinteticos, custo observado $0,00.
'@

'RECOVERY.md' = @'
# Recuperacao

Stop Controller: pausar, retoma, cancelar, interrupcao_imediata, autorizar_retomada.
Tarefa cancelada NAO retoma sem autorizacao explicita.

Supervisor sobrevive ao encerramento do agente e recupera ultimo checkpoint valido.
'@

'MEMORY.md' = @'
# Memoria Compartilhada

4 camadas: universal (regras), projeto, tarefa, historico de execucao.
Nao envia credenciais nem dados privados. Contexto minimo autorizado ao proximo agente.
'@

'SKILLS-INTEGRATION.md' = @'
# Skills

Skills existentes preservadas e nao modificadas. Compatibilidade verificada via
SkillsIntegration. Diferentes agentes podem interpretar Skills de formas distintas.
Nao declarar compatibilidade universal sem testes.
'@

'USER-GUIDE.md' = @'
# Guia do Usuario

1. python cli.py doctor
2. python cli.py validate
3. python cli.py test
4. python cli.py demo
5. python cli.py status

Brave e o navegador preferencial se houver integracao futura.
'@

'CHANGELOG.md' = @'
# Changelog

V1.0.4: homologacao limitada, supervisor independente, adaptador real OpenCode,
70 cenarios, demo multiagente, correcao de 17 bugs reais.
V1.0.3: 15 componentes (contudo com erros de sintaxe nao detectados).
V1.0.2: prototipo inicial.
'@

'ROADMAP.md' = @'
# Roadmap

V1.0.5: homologacao com mais provedores gratuitos (Gemini, OpenRouter),
revisao cruzada entre agentes, interface web opcional (Brave).
'@

'AGENTS.md' = @'
# Agentes

Papeis: Planejador, Desenvolvedor, Revisor, Testador, Supervisor deterministico.
Nao exigir 5 modelos diferentes para tarefas simples.
Agente nao pode ampliar suas proprias permissoes.
'@

'REAL-PROVIDERS-VALIDATION-PLAN.md' = @'
# Plano de Homologacao Real

1. Verificar plano efetivo de cada conta.
2. Confirmar gratuidade e ausencia de faturamento.
3. Testes com dados sinteticos (max 3 chamadas/provedor).
4. Nao esgotar cotas artificialmente.
5. Nao ativar faturamento nem comprar creditos.
6. Registrar evidencias e custo observado.

Executado parcialmente em V1.0.4: 2 provedores homologados (hy4-flash-free, beam-free).
'@
}

foreach ($nome in $docs.Keys) {
    $docs[$nome] | Out-File "$root\$nome" -Encoding utf8
}
Write-Output ("Documentos criados: " + $docs.Count)
Write-Output "Scripts BAT criados: 4"
