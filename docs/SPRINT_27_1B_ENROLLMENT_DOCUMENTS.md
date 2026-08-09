# Sprint 27.1B — Documentos de matrícula

## Objetivo

Incrementar a Secretaria Digital existente com documentos de matrícula, sem recriar
autenticação, organizações, inscrições, auditoria ou armazenamento. O módulo continua no
EduCode Admin e reutiliza o `ObjectStorage`, o RBAC institucional e a aplicação de matrícula
da Sprint 27.1A.

## Entrega

- requisitos documentais globais ou por unidade escolar;
- checklist por inscrição, incluindo itens ainda não enviados;
- upload de PDF, JPEG e PNG, limitado pelo requisito e validado por extensão, MIME e
  assinatura do arquivo;
- SHA-256, tamanho, autor e data registrados em versões imutáveis;
- estados enviado, em análise, aprovado, rejeitado, ilegível, expirado e nova entrega;
- histórico imutável das decisões e observações administrativas;
- download autenticado e privado, sem exposição da chave interna de armazenamento;
- interface `/secretaria/documentos`, separada de `/secretaria/matriculas` e
  `/secretaria/turmas-vagas`.

## Segurança e privacidade

O escopo da organização vem da sessão. A API também valida a unidade atribuída ao servidor.
Arquivos são armazenados pelo serviço canônico, sob chaves internas por tenant, inscrição,
documento e versão. Respostas de download usam `Cache-Control: private, no-store` e
`X-Content-Type-Options: nosniff`. Upload, revisão, download e criação de requisito geram os
eventos de auditoria já existentes.

Não foram adicionados campos de CPF ou RG. Nesta etapa somente equipe institucional e
administradores enviam e revisam arquivos. O autoenvio por responsável depende do Portal da
Família e de seu consentimento, a ser incrementado separadamente. O financeiro escolar
continua fora deste domínio.

## Banco de dados

A migration `0060_enrollment_documents` sucede `0059_school_admissions` e cria:

- `enrollment_document_requirements`;
- `enrollment_documents`;
- `enrollment_document_versions`;
- `enrollment_document_reviews`.

Ausência documental é representada pelo requisito sem documento; não existe linha artificial
com status ausente. Reenvios criam nova versão e preservam as anteriores.

## Instalação

Na raiz consolidada, execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-sprint-27-1b.ps1
```

O instalador preserva arquivos não rastreados, valida SHA-256 e estado-base, cria backup e
executa lint, testes e builds **antes** da migration. Depois aplica o upgrade, recria os
serviços, verifica o healthcheck e grava relatório em `storage/sprint-reports/`.

## Rollback

O downgrade remove metadados, histórico e vínculos documentais. Objetos já gravados no
storage não devem ser apagados automaticamente: devem seguir a política de retenção ou ser
restaurados com o backup.

1. coloque a aplicação em manutenção e crie um novo backup;
2. confirme e exporte documentos criados após a instalação;
3. prefira restaurar o backup integral anterior à migration;
4. apenas quando a perda for aceita, execute
   `docker compose run --rm backend alembic downgrade 0059_school_admissions`;
5. restaure o código anterior, reconstrua os serviços e valide `/api/v1/health/ready`.

## Validações executadas

- lint, formatação e compilação Python;
- testes focados e contratos estáticos antes da migration principal;
- integração de upload, revisão, download, reenvio e isolamento em PostgreSQL descartável;
- ciclo descartável `upgrade -> downgrade -> upgrade`;
- lint e build React/TypeScript;
- healthcheck, smoke test e inspeção visual das quatro áreas da Secretaria.

O `alembic check` conserva drift histórico anterior, avaliado sem ampliar a auditoria. Não há
drift relacionado às quatro tabelas desta sprint.

## Critérios de aceite

- [x] requisito e checklist respeitam organização e unidade;
- [x] arquivo inválido ou acima do limite é rejeitado;
- [x] cada reenvio cria versão imutável;
- [x] revisão aponta para a versão analisada e mantém histórico;
- [x] chave interna nunca é retornada ao frontend;
- [x] download exige autenticação e registra acesso sensível;
- [x] módulos da Secretaria estão visualmente separados;
- [x] testes e backup precederam a migration principal;
- [x] instalação, rollback, manifesto e SHA-256 estão documentados.
