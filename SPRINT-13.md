# Sprint 13 — Homologação, Segurança e Operação

A Sprint 13 prepara o EduCode para homologação institucional, sem criar um novo domínio pedagógico.

## Entregas

- migration `0024_platform_hardening`;
- health checks de liveness, readiness e dependências;
- preflight antes de migrations e implantação;
- request ID, mensagens de erro seguras e logs estruturados;
- CSP, HSTS em produção e headers de segurança;
- rate limiting com Redis;
- backups completos em worker, checksum e restauração real em banco temporário;
- versionamento de implantação;
- incidentes operacionais;
- feature flags;
- políticas LGPD de retenção;
- auditoria encadeada por hash;
- verificação de integridade dos dados;
- backend em contêiner não root;
- pipeline CI para backend, frontend e imagens;
- painéis administrativos de homologação, privacidade e auditoria.

## Regra operacional

O EduCode deve falhar de forma segura, preservar dados, indicar o `request_id` do erro e permitir diagnóstico sem revelar segredos ou respostas pessoais dos estudantes.


## Segurança operacional de backups

Backups completos contêm dados de toda a instalação e, por isso, só podem ser solicitados ou verificados por um usuário `is_superuser`. Administradores de organização continuam com acesso aos diagnósticos da própria instituição, mas não recebem acesso ao dump global.

O teste de restauração cria um banco PostgreSQL temporário, restaura o dump com `pg_restore`, consulta a quantidade de tabelas e a migration recuperada e remove o banco temporário ao final.
