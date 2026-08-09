# Sprint 18.14 — Consolidação do EduCode Credentials

## Objetivo

Encerrar o ciclo incremental de portfólio e certificações com um contrato único no frontend, acesso público descobrível e testes de regressão que preservam os fluxos das Sprints 18.9 a 18.13.

## Incremento entregue

- Tipos canônicos em `features/credentials/types.ts`.
- Cliente HTTP centralizado em `features/credentials/api.ts`.
- Professor, estudante e verificação pública reutilizam o mesmo contrato.
- Link “Verificar um certificado EduCode” disponível antes do login.
- Testes históricos adaptados ao cliente canônico.
- Testes de consolidação para rotas públicas, reutilização e ausência de migration.

## Compatibilidade e rollback

As URLs e os payloads existentes foram preservados. O rollback consiste em reverter o commit da sprint, pois não há alteração de banco. Nenhuma migration é criada ou aplicada; o head continua `0058_student_certificates`.

## Próximo ciclo

Com o EduCode Credentials consolidado, a evolução recomendada passa para o EduCode Connect, iniciando por notificações orientadas a eventos de aprendizagem e certificação.
