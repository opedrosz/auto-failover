# Seguranca

Controles em Python: validacao de acoes, deteccao de prompt injection,
protecao de credenciais, validacao de caminhos, bloqueio de comandos perigosos,
sanitizacao de logs, isolamento por projeto.

LIMITACAO: modulo Python NAO e sandbox inviolavel. Isolamento efetivo depende
do sistema operacional/executor. Nao declarar seguranca absoluta.

## V1.0.6

A CLI de demonstração usa apenas workers Python locais conhecidos. O supervisor não fornece isolamento de processos hostis. Use um workspace dedicado e capture somente metadados autorizados no checkpoint. A integração externa exige verificação dos limites, faturamento e dados sintéticos antes de ser habilitada.
