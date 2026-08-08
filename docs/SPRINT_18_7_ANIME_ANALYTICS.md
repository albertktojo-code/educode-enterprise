# Sprint 18.7 — Analytics audiovisual e checkpoints

## Incremento entregue

- Registro de início, marcos de retenção, checkpoints e conclusão no domínio canônico `learning_events`.
- Painel docente agregado por publicação em `/analytics/anime/:projectId`.
- Funil de retenção em 25%, 50%, 75% e 100%.
- Alcance, conclusão e média de desempenho por checkpoint, usando tentativas submetidas ou corrigidas do Assessment Delivery.
- Acesso ao painel pelo cabeçalho do EduCode Studio.

## Decisões de domínio

Não foi criada tabela paralela. Os eventos audiovisuais reutilizam `LearningEvent`, mantendo organização, estudante e atividade canônicos. A leitura docente aplica isolamento por organização e devolve apenas totais agregados, sem nomes de estudantes.

Como `LearningEvent` exige uma atividade, a publicação usa o primeiro checkpoint acessível ao estudante como âncora dos eventos gerais do vídeo. Publicações sem checkpoint não possuem âncora canônica e, nesta entrega, não geram telemetria audiovisual; o painel informa a ausência nos avisos de qualidade.

O filtro de `anime_project_id` ocorre nos metadados JSON após a seleção dos eventos audiovisuais da organização. Se o volume justificar, uma evolução futura poderá criar índice JSON específico, acompanhada de migration própria e plano de rollback.

## Eventos

- `anime_video_started`
- `anime_video_progress`
- `anime_checkpoint_opened`
- `anime_checkpoint_completed`
- `anime_video_completed`

Os metadados incluem somente identificadores técnicos, revisão, posição e marco percentual. A falha de telemetria não bloqueia a reprodução e é sinalizada ao estudante.

## Banco de dados e rollback

Esta sprint não cria nem aplica migration. O rollback consiste em remover a rota/página de Analytics e o envio dos cinco eventos; os registros já armazenados continuam válidos no histórico geral de aprendizagem.

## Critérios de aceite

- Eventos usam o endpoint e a tabela canônicos de aprendizagem.
- Professor acessa métricas apenas da própria organização.
- Painel apresenta estados de carregamento, erro, vazio e observações de qualidade.
- Nenhum dado individual do estudante aparece no painel audiovisual.
- Testes são executados antes de qualquer operação de migration.
