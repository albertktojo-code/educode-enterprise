# Hotfix Alembic 0022

A revisão original `0022_ai_fabric_advanced_workflows` tinha 33 caracteres, acima do limite padrão de 32 caracteres da coluna `alembic_version.version_num`.

A revisão corrigida é:

`0022_ai_fabric_advanced_flow`

O `down_revision` permanece:

`0021_ai_orchestration_runtime`

Para bancos em que a execução anterior falhou, basta usar este pacote corrigido e executar novamente:

```powershell
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend alembic current
```

Resultado esperado:

`0022_ai_fabric_advanced_flow (head)`

Não use `docker compose down -v`.
