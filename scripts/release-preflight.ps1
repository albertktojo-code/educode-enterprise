$ErrorActionPreference = "Stop"
Write-Host "1/5 Validando Docker Compose"
docker compose config | Out-Null
Write-Host "2/5 Verificando configuração da aplicação"
docker compose run --rm backend python -m app.operations.preflight
Write-Host "3/5 Validando cadeia e SQL de migrations"
docker compose run --rm backend python -m app.operations.migration_check --json
Write-Host "4/5 Consultando migration atual"
docker compose run --rm backend alembic current
Write-Host "5/5 Verificando serviços"
docker compose ps
Write-Host "Preflight de release concluído." -ForegroundColor Green
