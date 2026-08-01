$ErrorActionPreference = 'Stop'

docker compose up -d db redis
docker compose run --rm backend python -m app.operations.backup
if ($LASTEXITCODE -ne 0) {
  throw 'O backup falhou. Consulte os logs do backend.'
}
Write-Host 'Backup concluído e registrado.' -ForegroundColor Green
