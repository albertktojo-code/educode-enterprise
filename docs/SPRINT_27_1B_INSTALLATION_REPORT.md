# Relatório de instalação — Sprint 27.1B

- Data: 2026-08-09
- Base confirmada: `0059_school_admissions`
- Revisão instalada: `0060_enrollment_documents`
- Head final: único, `0060_enrollment_documents`
- Ordem de segurança: testes, integração descartável, backup, migration e validação final
- Arquivos não rastreados anteriores: preservados

## Backup anterior à migration

- Artefato: `/app/storage/backups/4e31b582-bfa7-4aea-9f44-099bd8ffbfc0/educode-full-20260809T143133Z-6c3035ec-b4e2-44de-bd5c-e21d9ef0f70a.tar.gz`
- SHA-256: `d81a87422c814facaeab8c68fd15cb7fc764939034ec790e0917d92d74ad0677`
- Tamanho: 1008698 bytes
- SHA-256 do dump PostgreSQL: `a4da68a443dc0dad1eb55f01266eac99fede7db59fc624533c9facbf7ddf4acc`

## Evidências

- testes focados pré-migration: 22 aprovados;
- integração PostgreSQL descartável: 1 aprovada;
- ciclo descartável `upgrade -> downgrade -> upgrade`: aprovado;
- lint, formatação e compilação Python: aprovados;
- lint e build React/TypeScript: aprovados;
- healthcheck final: `ready`;
- inspeção visual de painel, matrículas, documentos e turmas/vagas: aprovada.

## Observações

- O frontend mantém aviso não bloqueante do bundle principal, aproximadamente 1,05 MB.
- O drift histórico do Alembic foi conferido apenas no escopo desta entrega.
- O banco temporário de integração foi removido depois do teste.
