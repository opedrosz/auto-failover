# AUTO FAILOVER V1.0.6

## Parecer

Validação local aprovada para o seletor e a demonstração de failover. Homologação externa pendente. A versão usa uma calculadora sintética e processos Python sob controle local. A continuidade entre serviços reais requer verificação adicional.

## Baseline e reprodução

O checkout original e o `main` remoto apontavam para `3866bfee2b85c4e3695dad540281614eff7eae99`. A cadeia de quatro commits foi conferida com o Git. O clone isolado preservou os arquivos locais não rastreados e serviu como cópia do baseline versionado. `python -m unittest discover -s tests -q` passou os 70 cenários originais.

O teste novo dos requisitos padrão falhou no baseline com `nenhum_provedor_compativel`. O parser removia a letra K e convertia todo o restante para inteiro. Por isso, `128K tokens (sintetico)` zerava o limite e um inteiro em string podia ser multiplicado indevidamente. A regressão passa com o parser novo. A representação estruturada distingue janela total, entrada, saída, estado, configurabilidade, fonte e data de verificação. K e M usam unidades decimais. Uma declaração variável ou desconhecida continua bloqueada diante de um mínimo positivo.

## Seleção e continuidade

O seletor avalia modelos concretos, requisitos de contexto e capacidades, estado do provedor, exclusões, grupos de cota e custo. A ordem desempata por identificador. Um catálogo legado com nomes de modelos e etiquetas de gratuidade não comprova disponibilidade e faturamento. Os únicos modelos demonstrados nesta fase foram `sintetico-a` e `sintetico-b`, carregados dos templates.

`python cli.py demo-local` concluiu a tarefa `calculadora` no Windows. O processo inicial, PID 25908, escreveu a soma e terminou com código 75 às 23:42:11 no horário de Brasília de 24/11/2026. O supervisor registrou o checkpoint de `calc.py`, SHA-256 `8c3661edcc7e111bb9c4250062f6908b82920676e6591ae130d226f38335697d`, e selecionou o segundo provedor simulado. O PID 21352 leu o mesmo artefato, adicionou a subtração e saiu com código 0. As duas operações passaram na validação final. Foram realizadas zero chamadas reais, com custo adicional de R$ 0,00.

O código 75 pertence ao protocolo local e representa indisponibilidade simulada. Outras falhas exigem reconciliação. Locks impedem sobreposição no mesmo workspace. O controle de interrupção pode impedir a próxima tentativa. A proteção de processos descendentes, a retomada automática após queda do próprio supervisor e a coordenação entre workspaces com a mesma base ainda requerem validação ou implementação.

## Testes e componentes

`python cli.py test` executa a suíte inteira e retorna seu código de saída. Resultado antes da publicação: 82 testes, zero falhas. Os 11 cenários com verificações de tipo ou presença identificados na V1.0.5 ganharam verificações de comportamento. Os cenários novos cobrem formatos de contexto, limites combinados, custo remoto não verificado, exclusão de modelo e provedor, cota compartilhada, bloqueio de circuito, troca de processo, falha incerta, cancelamento, lock, caminho fora do projeto e execução da demo com templates em outro processo. Alguns cenários legados são simulados e preservam seus rótulos históricos.

| Componentes | Evidência nesta entrega |
| --- | --- |
| Provider Registry e Model Selector | Formatos legados, requisitos, seleção e rejeição por modelo |
| Orchestrator e Failover Manager | Suíte legada e classificação simulada. O fluxo de execução V1.0.6 usa o Supervisor |
| Supervisor e Stop Controller | Dois processos sequenciais, bloqueio entre tentativas e persistência do resultado |
| Checkpoint Manager, Shared Memory e Task Recovery | Cenários legados de integridade, restauração, idempotência, isolamento e reconciliação. A demo persiste seu próprio checkpoint de artefato |
| Health Monitor, Cost Controller e Config Validator | Cenários legados. Sem autenticação, descoberta de preço ou cota externa homologada |
| Project Manager, Security Controller, Skills Integration e Audit Logger | Cobertura legada e verificação de fronteira, proteção de rede e sanitização. Sem certificação de isolamento integral |

## Segurança e publicação

Foram examinados por padrões os blobs dos quatro commits de referência e sete blobs órfãos locais. Os candidatos observados eram exemplos, padrões de auditoria ou fixtures sintéticas. A revisão testa padrões conhecidos e não certifica a ausência absoluta de segredos. A árvore proposta inclui `.env.example` e dois JSONs em `examples/`. Configurações efetivas, dados, logs e checkpoints permanecem ignorados.

O caminho de inferência pelo adaptador histórico foi bloqueado. Seu parâmetro de limite de saída não chegava ao processo e a interface usada não comprovava o faturamento da conta ou a contagem de chamadas internas. A tabela pública de preços apenas descreve modalidades disponíveis. A etapa com OpenCode e Gemini permanece pendente. [Preços da Gemini Developer API](https://ai.google.dev/gemini-api/docs/pricing/)

O GitHub público expõe arquitetura, procedimentos e metadados já existentes. Antes de conectar projetos privados, convém reavaliar essa exposição e decidir a visibilidade com o proprietário. O trabalho não usa a instalação dos outros projetos. A relação completa de arquivos criados e alterados está no commit da V1.0.6. A branch de publicação proposta é `codex/auto-failover-v1.0.6`.
