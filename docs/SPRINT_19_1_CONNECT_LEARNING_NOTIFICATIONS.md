# Sprint 19.1 — Notificações de aprendizagem no EduCode Connect

## Incremento entregue

- Emissão de certificado gera uma notificação para o estudante.
- Revogação gera uma notificação distinta, com motivo e acesso ao portfólio.
- Nova central do estudante em `/aluno/notificacoes`.
- Filtros para não lidas, aprendizagem e certificados.
- Ações individuais e em lote para marcar como lida.
- Navegação e catálogo do EduCode Connect apontam para a nova central.

## Arquitetura

Eventos pedagógicos continuam usando `user_notifications`, já utilizado por atividades, correções e tentativas. Processamentos internos continuam usando `job_notifications`. A sprint não cria um terceiro domínio nem mistura mensagens operacionais com a jornada do estudante.

## Segurança e compatibilidade

Listagem e atualização continuam filtradas pelo usuário autenticado e pela organização atual. A atualização em lote afeta somente notificações não lidas desse escopo. Os endpoints e payloads anteriores permanecem compatíveis.

## Persistência e rollback

Não há migration. O head permanece `0058_student_certificates`. O rollback consiste em reverter o commit da sprint; notificações já criadas permanecem registros válidos no domínio canônico.
