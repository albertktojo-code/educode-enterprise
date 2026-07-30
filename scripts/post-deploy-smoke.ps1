param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$FrontendUrl = "http://localhost:5173"
)
$ErrorActionPreference = "Stop"

function Check-Url([string]$Url, [string]$Name) {
  Write-Host "Verificando $Name: $Url"
  $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 20
  if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
    throw "$Name retornou HTTP $($response.StatusCode)"
  }
}

Check-Url "$BaseUrl/api/v1/health/live" "Liveness"
Check-Url "$BaseUrl/api/v1/health/ready" "Readiness"
Check-Url "$BaseUrl/openapi.json" "Contrato OpenAPI"
Check-Url "$FrontendUrl" "Frontend"
Write-Host "Smoke tests pós-implantação concluídos." -ForegroundColor Green
