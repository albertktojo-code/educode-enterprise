# Endurecimento de segurança — 0.16.11.5

Este lote corrige riscos encontrados na auditoria posterior à Sprint 16.11.5.

## Escopo

- corrigir o default temporal do snapshot de Analytics pós-HQ;
- impedir que o seed reative organização, usuário ou membership existentes;
- impedir que o seed restaure `is_superuser` ou o papel `OWNER` removidos;
- criar o administrador inicial apenas quando o usuário configurado não existe;
- bloquear segredos JWT de desenvolvimento fora do ambiente `development`.

## Compatibilidade

Não há migration, alteração de schema, nova tabela ou mudança de rota. O
comando explícito `python -m app.db.reset_admin` continua sendo o mecanismo de
recuperação administrativa quando a restauração de privilégios for realmente
intencional.

## Rollback

O rollback é exclusivamente de código. Nenhum dado existente é reescrito por
este lote.

## Riscos não incluídos

- ausência de metadata Git;
- drift histórico apontado por `alembic check`;
- escolha explícita de organização em contas com múltiplas memberships;
- reconciliação dos domínios avaliativos legados.
