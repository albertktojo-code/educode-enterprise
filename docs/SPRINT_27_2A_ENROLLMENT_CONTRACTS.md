# Sprint 27.2A — Contratos de matrícula

## Objetivo e entrega

Este incremento adiciona contratos eletrônicos ao domínio canônico `school_admissions`,
reutilizando matrículas, estudantes, responsáveis, unidades, RBAC e auditoria existentes.
Inclui templates globais ou por unidade, variáveis controladas, geração de versões imutáveis,
SHA-256 do conteúdo, aceite do responsável e cancelamento administrativo antes do aceite.

A Secretaria possui uma área separada em `/secretaria/contratos`. O aceite já está preparado
na API para o responsável autenticado e vinculado; sua tela familiar será conectada na Sprint
27.6. Não há gateway de assinatura externa, CPF/RG nem fluxo financeiro nesta entrega.

## Variáveis permitidas

`nome_aluno`, `nome_responsavel`, `ano_letivo`, `serie`, `turma`, `turno`,
`unidade_escolar` e `data_geracao`. Variáveis desconhecidas são rejeitadas.

## Banco e segurança

A migration reversível `0061_enrollment_contracts`, baseada em
`0060_enrollment_documents`, cria templates, contratos, versões e aceites. Todas as tabelas
são isoladas por organização. Cada aceite aponta para uma versão exata e registra responsável,
usuário, timestamp, IP e hash. Contrato aceito exige processo formal futuro para cancelamento.

## Instalação

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-sprint-27-2a.ps1
```

O instalador preserva arquivos não rastreados, valida SHA-256 e o head, cria backup e executa
testes e builds antes da migration.

## Rollback

O downgrade apaga templates, versões e aceites. Antes de executá-lo, coloque o sistema em
manutenção, crie outro backup e exporte contratos emitidos. Prefira restaurar o backup integral.
Somente com a perda aceita execute:

```powershell
docker compose run --rm backend alembic downgrade 0060_enrollment_documents
```

Depois restaure o código anterior, reconstrua os serviços e valide o healthcheck.

## Validação

- testes focados pré-migration: 29 aprovados;
- testes específicos: 7 aprovados e integração opt-in ignorada no banco principal;
- integração PostgreSQL descartável: aprovada;
- ciclo descartável `upgrade -> downgrade -> upgrade`: aprovado;
- lint, compilação, frontend lint/build, smoke e inspeção visual: aprovados;
- drift histórico do Alembic permanece fora do escopo; nenhuma ocorrência envolve as tabelas
  desta sprint.

## Critérios de aceite

- [x] template restringe variáveis;
- [x] geração cria versão e hash imutáveis;
- [x] regeneração preserva versões anteriores;
- [x] aceite só pertence ao responsável autenticado e vinculado;
- [x] aceite repetido é idempotente;
- [x] contrato aceito não é alterado diretamente;
- [x] isolamento, auditoria, backup e rollback foram validados;
- [x] módulo Contratos está separado no frontend.
