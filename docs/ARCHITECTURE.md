# Arquitetura

15 componentes: Orchestrator, Provider Registry, Model Selector, Failover Manager,
Health Monitor, Cost Controller, Checkpoint Manager, Task Recovery, Shared Memory Manager,
Security Controller, Audit Logger, Config Validator, Stop Controller, Skills Integration,
Project Manager.

Supervisor independente (supervisor/) monitora processos filhos via subprocess no Windows,
sobrevivendo ao encerramento da sessao de IA.

Adaptador real (adapters/opencode_adapter.py) usa `opencode run --model <id> --format json --auto`.

Fluxo: tarefa -> checkpoint -> selecao -> inferencia -> deteccao de falha -> failover -> recuperacao.

## Supervisor local V1.0.6

O seletor avalia modelos concretos. O supervisor inicia um processo por vez, mantém um lock no workspace e só tenta outro provedor após uma falha declarada com código 75 e registro do checkpoint. Pode consultar um controle de interrupção antes de cada novo processo.
