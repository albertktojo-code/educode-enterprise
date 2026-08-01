$ErrorActionPreference = 'Stop'

$live = Invoke-RestMethod http://localhost:8000/api/v1/health/live
$ready = Invoke-RestMethod http://localhost:8000/api/v1/health/ready
Write-Host "Liveness: $($live.status) — versão $($live.version)"
Write-Host "Readiness: $($ready.status)"
if ($ready.status -ne 'ready') {
  throw 'O backend ainda não está pronto.'
}
Write-Host 'Smoke test aprovado.' -ForegroundColor Green
