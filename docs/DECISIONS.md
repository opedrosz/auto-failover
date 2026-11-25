# DECISÕES — AUTO FAILOVER V1.0.4

Registro de decisões técnicas, funcionais e de segurança tomadas nesta sessão.

## Decisões Técnicas

| # | Decisão | Justificativa |
|---|---------|---------------|
| 1 | Manter infraestrutura em diretório isolado `AI-INFRASTRUCTURE/Auto-Failover` | Independência dos projetos consumidores (Orion, Editor-Vídeo, ADS-Intelligence, Codex Skills) |
| 2 | Usar `opencode run --model <id> --format json --auto` como adaptador real | Interface oficial não interativa do OpenCode v2.3.2; não extrair tokens internos |
| 3 | Supervisor determinístico separado da sessão de IA | Orquestrador não pode depender do modelo ativo para decidir troca |
| 4 | Circuit breaker após 3 falhas consecutivas, cooldown 30s, backoff progressivo | Evitar loops e consumo inútil de cotas |
| 5 | Checkpoints com limite configurável, padrão ilimitado | V1.0.3 limitava a 3; corrigido conforme requisito V1.0.4 |
| 6 | SHA-256 para integridade, mas não como garantia de autenticidade | Detecta corrupção; não protege contra adulteração intencional isoladamente |
| 7 | Reescrita atômica com `os.replace()` | Evitar checkpoints corrompidos por escrita parcial |
| 8 | Aliases `opencode`/`google` no Provider Registry | Compatibilidade com identificadores usados pela CLI |

## Decisões de Segurança

| # | Decisão | Justificativa |
|---|---------|---------------|
| 9 | Orçamento padrão R$ 0,00 e fail-closed para custos desconhecidos | Nenhuma cobrança não autorizada |
| 10 | 9 verificações financeiras antes de cada chamada externa | Bloquear modelo não gratuito, dado não sintético, limites excedidos |
| 11 | Logs sanitizados (máscara `****SANITIZADO****`) | Nunca registrar chaves, tokens, cookies |
| 12 | Security Controller valida ações antes de executar | Privilégio mínimo; bloquear prompt injection e comandos perigosos |
| 13 | Declarar limitação: módulo Python não é sandbox inviolável | Isolamento real depende do SO/executor |
| 14 | Dados sintéticos apenas em chamadas reais | Nenhum código privado enviado aos provedores |

## Decisões de Continuidade

| # | Decisão | Justificativa |
|---|---------|---------------|
| 15 | Memória compartilhada em 4 camadas | Universal, projeto, tarefa, histórico — sem misturar contextos |
| 16 | Tarefa cancelada não retoma sem autorização explícita | Respeitar interrupção do usuário |
| 17 | Backup da V1.0.3 antes de qualquer alteração | Preservar estado anterior sem duplicar credenciais |
| 18 | Falha no demo injetada/simulada, não real | Não esgotar cotas reais artificialmente |

## Decisões de Publicação (pendentes)

| # | Decisão | Status |
|---|---------|--------|
| 19 | Não inicializar Git sem aprovação | ⏳ Aguardando autorização |
| 20 | Não executar commit/push/merge sem aprovação | ⏳ Aguardando autorização |
| 21 | `.gitignore` criado para excluir credenciais, logs, dados, backups | ✅ Implementado |
| 22 | Verificar credenciais antes de publicar | ✅ Nenhuma credencial real encontrada (2 chaves falsas em testes) |

## Aprendizados Relevantes

- A V1.0.3 relatou "48 testes aprovados" sem evidência; a execução real revelou 60/70, com 10 defeitos. **Só considerar aprovado o que foi executado e registrado.**
- Erros de sintaxe em 6 módulos passaram despercebidos porque nunca se executou `py_compile`. **Sempre compilar antes de declarar conclusão.**
- Modelos externos podem envolver código em cercas markdown (```python). **Tratar saída como não confiável e sanitizar antes de validar.**
- `opencode auth list` mostra credenciais armazenadas, mas não prova autenticação funcional nem gratuidade.
- Custo zero observado em teste não garante gratuidade permanente.
-有限 limitações de API do OpenCode: transferência de sessão entre provedores é parcial.

## Correções Realizadas nesta Sessão

17 bugs reais corrigidos (sintaxe, imports, métodos, lógica de custo, recuperação de checkpoint, aliases). Ver `CHANGELOG.md` e o relatório final V1.0.4.
