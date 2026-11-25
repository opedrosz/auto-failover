# Recuperacao

Stop Controller: pausar, retoma, cancelar, interrupcao_imediata, autorizar_retomada.
Tarefa cancelada NAO retoma sem autorizacao explicita.

Supervisor sobrevive ao encerramento do agente e recupera ultimo checkpoint valido.

## Recuperação V1.0.6

O código de saída 75 sinaliza que o worker confiável preservou o progresso. O supervisor persiste o checkpoint antes de iniciar outro provedor, que lê o artefato local. Um código desconhecido, timeout ou checkpoint ausente suspende a tarefa. Após queda do supervisor, revise o estado persistido e confirme que o processo anterior terminou antes de remover o lock ou iniciar outra tarefa no workspace.
