# Testes

70 cenarios em tests/test_scenarios_v104.py.
Tipos: LOCAL_REAL (codigo local real), SIMULADO (mocks), EXTERNO_LEVE (CLI), HOMOLOGACAO_EXTERNA_LIMITADA.

Resultado V1.0.4: 70/70 aprovados (reports/resultados_testes_v104.json).
Homologacao externa: 2 chamadas reais com dados sinteticos, custo observado $0,00.

## V1.0.6

`python cli.py test` roda a suíte histórica e os cenários de regressão em uma base temporária. `python cli.py demo-local` roda a calculadora em dois processos. O código de saída 75 é injetado localmente e representa indisponibilidade recuperável. Nenhuma função do provedor remoto é invocada.
