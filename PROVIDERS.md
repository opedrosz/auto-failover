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

## Capacidades V1.0.6

Cada modelo pode declarar `contexto` com `janela_total`, `entrada`, `saida`, `fonte` e `verificado_em`. A configuração local pode declarar `configuravel` ou `estado: variavel`. As unidades K e M significam 1.000 e 1.000.000 tokens. Uma capacidade desconhecida não satisfaz um mínimo positivo. O catálogo embutido é histórico. Identificadores, custo e disponibilidade atuais exigem verificação independente.
