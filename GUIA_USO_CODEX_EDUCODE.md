# Como migrar o desenvolvimento do EduCode para o Codex

## Estrutura recomendada

Coloque na raiz consolidada:

```text
AGENTS.md
CODEX_CONTINUATION_PROMPT.md
```

A raiz consolidada é a pasta que contém `docker-compose.yml`, `backend` e
`frontend`.

## Não faça

Não abra no Codex apenas a pasta extraída de uma sprint. Ela contém somente o
delta da entrega e não representa o sistema completo.

## Faça

1. Use a raiz consolidada do EduCode.
2. Inicialize Git, caso ainda não exista.
3. Crie um commit de segurança.
4. Adicione `AGENTS.md`.
5. Abra essa raiz no VS Code.
6. Execute o Codex dentro dessa pasta.
7. Use primeiro o prompt de auditoria.
8. Somente depois peça uma nova sprint.

## Commit de segurança

```powershell
cd "C:\Users\lady_\Downloads\educode-enterprise-2.0-sprint-14\educode-enterprise-2.0-sprint-14"

git init
git add .
git commit -m "baseline EduCode antes da continuidade com Codex"
```

Não envie `.env`, chaves, backups, banco ou arquivos secretos ao repositório.

## Primeiro comando no Codex CLI

```powershell
cd "C:\Users\lady_\Downloads\educode-enterprise-2.0-sprint-14\educode-enterprise-2.0-sprint-14"

codex
```

Cole o conteúdo de `CODEX_CONTINUATION_PROMPT.md`.

## Prompt para cada nova sprint

```text
Leia AGENTS.md e audite o estado real antes de alterar arquivos.

Implemente a Sprint <NÚMERO> — <TÍTULO>.

Objetivo:
<OBJETIVO>

Escopo obrigatório:
<ESCOPO>

Restrições:
- reutilizar domínios canônicos;
- não criar sistemas paralelos;
- respeitar organization_id, RBAC e auditoria;
- verificar Alembic antes de criar migration;
- implementar testes;
- executar build;
- documentar o que foi e não foi executado;
- preservar instalação idempotente e rollback.

Primeiro apresente o plano e os arquivos que pretende alterar.
Depois implemente, execute os testes e entregue um resumo verificável.
```
