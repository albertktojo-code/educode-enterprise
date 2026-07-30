# Hotfix Sprint 08 — enums PostgreSQL da migration 0013

## Problema corrigido

A migration `0013_teacher_studio_canvas` criava os tipos ENUM explicitamente e reutilizava instâncias `sa.Enum` configuradas para também criar os tipos durante `op.create_table`. Isso causava:

```text
asyncpg.exceptions.DuplicateObjectError: type "studio_creation_mode" already exists
```

## Correção

Os seis tipos passaram a usar `postgresql.ENUM(..., create_type=False)`. A migration continua criando os tipos uma única vez com `checkfirst=True`, e o `downgrade` agora remove os tipos depois das tabelas.

A correção é segura quando o enum já existe por uma tentativa anterior: `checkfirst=True` reutiliza o tipo existente, enquanto `create_type=False` impede a segunda criação durante as tabelas.
