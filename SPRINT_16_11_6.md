# Sprint 16.11.6 — Monitoramento docente em tempo real

## Objetivo

Permitir que docentes acompanhem aplicações pós-HQ enquanto elas acontecem e
realizem intervenções pontuais, sem expor respostas, criar sessões paralelas ou
automatizar decisões pedagógicas.

## Arquitetura adotada

A sprint não cria tabelas nem migration. O head permanece
`0055_delivery_source_invariant`.

O fluxo reutiliza:

1. `assessment_delivery_publications` e `assessment_delivery_targets` para
   publicação, audiência e tentativas adicionais;
2. `assessment_delivery_sessions`, itens e eventos para estado, posição,
   autosave, pausa, retomada, tempo e comandos docentes;
3. `hq_student_experience_states` para página, quadro, atividade e progresso;
4. `hq_activity_bindings` e perfis de feedback aprovados para dificuldade e
   dicas graduadas;
5. `user_notifications` para avisos persistentes ao estudante;
6. a auditoria institucional para toda ação docente sensível.

O painel usa polling autenticado a cada cinco segundos. Essa escolha segue o
padrão já usado pelo frontend para acompanhamento operacional e evita um canal
SSE que não poderia reutilizar diretamente o cabeçalho Bearer do cliente HTTP
central. O endpoint informa o intervalo e pode evoluir para SSE ou WebSocket
sem alterar o modelo de dados.

## Funcionalidades entregues

- audiência inclui estudantes ainda não iniciados;
- estados: não iniciou, iniciou, lendo, respondendo, pausado e concluído;
- página, quadro e atividade atuais;
- progresso de leitura, atividades e progresso combinado;
- tempo desde a última interação e limite configurável;
- alertas de ociosidade, pedido de ajuda e sinais que exigem revisão humana;
- filtros por turma, situação e estudante;
- pausa, retomada e concessão de tempo adicional;
- nova tentativa por target individual canônico;
- mensagem do professor;
- liberação gradual de dica previamente aprovada;
- liberação explícita de gabarito com confirmação;
- atualização da experiência do estudante para receber mensagens, dicas,
  pausa/retomada e gabarito;
- pedido de ajuda pelo estudante;
- estados de loading, erro, vazio e atualização manual;
- navegação por teclado, foco visível, `aria-live`, responsividade e redução de
  movimento.

## Privacidade e segurança

- todos os acessos restringem `organization_id`;
- o contexto organizacional vem da sessão autenticada;
- o monitor exige papel docente/editor;
- respostas, gabaritos não liberados e detalhes de dispositivo não aparecem no
  snapshot;
- não há ranking, webcam, reconhecimento facial ou decisão automática;
- eventos enviados por estudantes não podem declarar origem docente;
- toda mensagem, dica, gabarito, tempo extra, pausa, retomada ou tentativa
  adicional gera evento e auditoria;
- o professor mantém a decisão final.

## APIs

- `GET /api/v1/comic-page-editor/activity-deliveries/{id}/monitoring`
  - filtros opcionais: `classroom_id`, `student_id`, `status` e
    `idle_threshold_seconds`;
- `POST /api/v1/assessment-delivery/sessions/{id}/actions`
  - ações novas: `GRANT_ATTEMPT`, `SEND_MESSAGE`, `RELEASE_HINT` e
    `RELEASE_ANSWER_KEY`;
  - ações reutilizadas: `PAUSE`, `RESUME`, `EXTEND`;
- `POST /api/v1/assessment-delivery/sessions/{id}/events`
  - evento do estudante: `STUDENT_HELP_REQUESTED`;
- `GET /api/v1/comic-page-editor/student-experience/publications/{id}`
  - passa a retornar `teacher_support` e gabaritos explicitamente liberados.

## Changelog

- versão da aplicação elevada para `0.16.11.6`;
- painel registrado em
  `/teacher/comic-studio/monitoring/:deliveryId`;
- o atalho da experiência do estudante agora usa o `publication_id` correto;
- nenhum modelo, tabela ou índice novo;
- nenhum dado de demonstração incluído.

## Critérios de aceitação

- um docente vê estudantes previstos e sessões iniciadas da própria
  organização;
- filtros não atravessam organizações;
- respostas não são retornadas pelo monitor;
- ações docentes são auditadas e refletidas na experiência do estudante;
- solicitações de ajuda permanecem abertas até mensagem ou dica posterior;
- build TypeScript e testes backend passam;
- Alembic continua com um único head;
- healthcheck confirma banco, Redis e armazenamento.

## Smoke E2E reproduzível

O script `scripts/e2e-sprint-16-11-6.ps1` valida sem dependências adicionais:

- resposta do frontend e identidade visual do EduCode;
- liveness, readiness e versão instalada;
- registro das rotas da sprint no OpenAPI;
- bloqueio do monitoramento sem autenticação;
- login docente e privacidade do snapshot quando as variáveis
  `EDUCODE_E2E_TEACHER_EMAIL`, `EDUCODE_E2E_TEACHER_PASSWORD` e
  `EDUCODE_E2E_DELIVERY_ID` forem fornecidas.

Execução pública:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\scripts\e2e-sprint-16-11-6.ps1
```

## Rollback

Não há downgrade de banco. O rollback consiste em restaurar os arquivos da
versão anterior e reconstruir backend/frontend. Eventos, notificações e
auditorias já gravados devem ser preservados como histórico.

## Limitações conhecidas

- polling produz atualização próxima do tempo real, não entrega instantânea;
- o smoke autenticado depende de uma credencial docente e de uma aplicação de
  teste válidas; o script não cria nem altera usuários automaticamente;
- uma aplicação histórica sem targets ou memberships ativos mostra apenas
  estudantes que já possuem sessão;
- turmas associadas apenas por grupos legados podem aparecer pelo identificador
  quando o nome da turma não estiver disponível;
- o bundle principal do frontend ainda supera 500 kB e requer code splitting em
  uma frente de performance separada;
- o drift residual do Alembic continua limitado aos índices já documentados e
  não foi transformado em migration nesta sprint.
