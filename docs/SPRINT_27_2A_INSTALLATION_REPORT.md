# Relatório de instalação — Sprint 27.2A

- Data: 2026-08-09
- Base: `0060_enrollment_documents`
- Revisão instalada: `0061_enrollment_contracts` (head único)
- Testes executados antes da migration: sim
- Arquivos não rastreados: preservados

## Backup anterior à migration

- Caminho: `/app/storage/backups/4e31b582-bfa7-4aea-9f44-099bd8ffbfc0/educode-full-20260809T150231Z-c02c5b0a-2eed-499c-adeb-513ae82c5119.tar.gz`
- SHA-256: `8a557f9e7a52a29c7a60c1709438051e414c542e5a72ba2944e0af1c32895795`
- Tamanho: 1020180 bytes
- Dump PostgreSQL: `4fb4641fbf8b5ef62c905e676ba324e813066bd383eaf9672c3ba9b94869646a`

## Evidências

- 29 testes focados e 7 específicos aprovados;
- integração descartável e ciclo de rollback aprovados;
- lint/compilação Python e lint/build frontend aprovados;
- smoke autenticado e healthcheck aprovados;
- interface `/secretaria/contratos` renderizada sem erros no console.
