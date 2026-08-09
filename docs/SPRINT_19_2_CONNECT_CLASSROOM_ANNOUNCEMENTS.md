# Sprint 19.2 — Comunicados por turma no EduCode Connect

## Incremento entregue

- Professor envia um comunicado para uma ou mais turmas ativas pela central de notificações.
- Cada estudante recebe uma notificação canônica do tipo `classroom_announcement`.
- O estudante encontra os avisos no novo filtro **Comunicados** da sua central.
- As notificações operacionais de tarefas continuam separadas no painel do professor.

## Regras e segurança

- O endpoint exige um papel docente autorizado.
- As turmas precisam estar ativas e pertencer à organização atual.
- Apenas usuários ativos, matriculados como estudantes e membros ativos da mesma organização recebem o aviso.
- Um estudante presente em mais de uma turma selecionada recebe somente uma notificação.
- O destino da notificação aceita apenas rotas internas da aplicação.
- Cada envio registra o evento de auditoria `announcement.sent`, com turmas e total de destinatários.

## Banco de dados

Esta sprint reutiliza `user_notifications`, `classrooms` e `classroom_enrollments`. Não há migration nova e o head permanece `0058_student_certificates`.

## Validação e reversão

Os testes verificam validação do payload, isolamento por organização, deduplicação, auditoria e integração das telas. A reversão consiste em remover o endpoint e a interface do compositor; nenhuma alteração de esquema precisa ser revertida.
