# Failover

Categorias: HTTP 429, 5xx, timeout, conexao, autenticacao, credencial expirada,
contexto, modelo indisponivel/incompativel, seguranca, interrupcao manual.

Comportamento: backoff progressivo, Retry-After, circuit breaker (3 falhas),
cooldown, limite 6 tentativas, grupos de cota compartilhada, suspensao segura.

Nao trocar provedor em violacao de seguranca ou recusa legitima.
Falha injetada no demo e SIMULADA - nao esgota cota real.
