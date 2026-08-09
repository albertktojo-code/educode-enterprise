# Relatório de instalação — Sprint 27.1A

- Data: 2026-08-09
- Base confirmada: `0058_student_certificates`
- Revisão instalada: `0059_school_admissions`
- Head final: único, `0059_school_admissions`
- Ordem de segurança: testes pré-migration, backup, migration e validação final
- Arquivos não rastreados anteriores: preservados

## Backup anterior à migration

- Artefato:
  `/app/storage/backups/4e31b582-bfa7-4aea-9f44-099bd8ffbfc0/educode-full-20260809T120701Z-a0514518-f385-4eae-805f-f2873818b4c7.tar.gz`
- SHA-256:
  `568083ef61631b7600eb4b18626c0830906a94ea1fed71214a8e78ccb569aa38`
- Tamanho: 986347 bytes

## Evidências

- suíte pré-migration: 75 testes aprovados;
- suíte final focada: 15 aprovados e 1 integração opt-in ignorada;
- integração PostgreSQL descartável: 1 teste aprovado;
- ciclo descartável `upgrade -> downgrade -> upgrade`: aprovado;
- lint e formatação Python: aprovados;
- compilação Python: aprovada;
- lint e build React/TypeScript: aprovados;
- Docker Compose: configuração válida;
- healthcheck final: `ready`;
- inspeção visual de `/secretaria`: aprovada.

## Observações

- O build do frontend mantém o aviso não bloqueante de chunk principal com
  aproximadamente 1,04 MB.
- `alembic check` mantém drift histórico anterior, sem correspondências para as
  tabelas e colunas introduzidas pela Sprint 27.1A.
- O banco temporário usado na integração foi removido após o teste.
