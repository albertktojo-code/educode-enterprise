# Sprint 16.11.5 — Adaptação e intervenções pós-HQ

## Objetivo

Transformar evidências reais de leitura e avaliação pós-HQ em alertas,
recomendações e intervenções pedagógicas revisadas por docentes.

## Arquitetura

A sprint não cria tabelas nem sistemas paralelos. O head do Alembic permanece
`0054_delivery_model_sync`.

O fluxo reutiliza:

1. `assessment_delivery_sessions` para aplicação e vínculo com tentativas;
2. `assessment_hub_responses` e `assessment_hub_question_skills` para
   desempenho e rastreabilidade BNCC/Pensamento Computacional;
3. `comic_reader_events` para visualizações, releituras e tempo ativo;
4. `hq_learning_analytics_snapshots` como consolidação idempotente;
5. `learning_alerts` como alerta pedagógico canônico;
6. `adaptive_recommendations` e `adaptive_recommendation_evidence` para
   propostas explicáveis;
7. `learning_interventions` e eventos para aprovação, execução e histórico;
8. os checkpoints de `intervention_effectiveness` para acompanhamento.

## Regras funcionais

- respostas pendentes de revisão humana não são contabilizadas como erro;
- alertas agregados são suprimidos abaixo do tamanho mínimo de grupo;
- cada alerta referencia snapshot, publicação, release, período e escopo;
- regenerar o mesmo recorte atualiza o snapshot e seus sinais sem duplicá-los;
- sinais removidos resolvem somente alertas ainda abertos;
- sugestões cobrem releitura, simplificação, equivalência, reforço,
  consolidação, aprofundamento e desafio;
- variantes de atividade exigem seleção docente;
- nenhuma recomendação cria ou publica intervenção automaticamente;
- aprovação e rejeição continuam no domínio de orquestração, com auditoria;
- toda consulta nova restringe `organization_id`.

## APIs reutilizadas

- `POST /api/v1/comic-page-editor/activity-deliveries/{id}/analytics/generate`
- `GET /api/v1/comic-page-editor/activity-deliveries/{id}/analytics/latest`
- `POST /api/v1/comic-reader-analytics/events/batch`
- `GET /api/v1/intervention-orchestration/alerts`
- `POST /api/v1/intervention-orchestration/proposals/from-alert/{alert_id}`
- `PATCH /api/v1/intervention-orchestration/proposals/{recommendation_id}`
- endpoints existentes de execução e effectiveness.

## Rollback

Não há downgrade de banco. O rollback consiste em restaurar os arquivos da
versão anterior e reconstruir backend/frontend. Snapshots, alertas,
recomendações e intervenções já registrados devem ser preservados como
histórico; não devem ser removidos automaticamente.

## Limitações conhecidas

- o banco de desenvolvimento auditado não contém amostra pedagógica real;
- ambientes históricos devem verificar atividades sem
  `question_version_id`, vínculos de habilidade ou release publicado;
- o drift preexistente apontado por `alembic check` precisa de tratamento
  separado e não deve virar uma migration autogerada em massa;
- a seleção explícita de organização continua sendo uma frente de
  consolidação independente.
