$ErrorActionPreference = 'Stop'

docker compose up -d db redis
docker compose run --rm backend python -m app.operations.preflight
if ($LASTEXITCODE -ne 0) {
  throw 'O preflight encontrou bloqueios. Corrija-os antes da migration.'
}
Write-Host 'Preflight concluído com sucesso.' -ForegroundColor Green
