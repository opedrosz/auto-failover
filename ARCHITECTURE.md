# Arquitetura

15 componentes: Orchestrator, Provider Registry, Model Selector, Failover Manager,
Health Monitor, Cost Controller, Checkpoint Manager, Task Recovery, Shared Memory Manager,
Security Controller, Audit Logger, Config Validator, Stop Controller, Skills Integration,
Project Manager.

Supervisor independente (supervisor/) monitora processos filhos via subprocess no Windows,
sobrevivendo ao encerramento da sessao de IA.

Adaptador real (adapters/opencode_adapter.py) usa `opencode run --model <id> --format json --auto`.

Fluxo: tarefa -> checkpoint -> selecao -> inferencia -> deteccao de falha -> failover -> recuperacao.
