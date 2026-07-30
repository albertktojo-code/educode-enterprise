param(
    [Parameter(Mandatory=$true)][string]$PlanId,
    [string]$ApiUrl = "http://localhost:8000/api/v1",
    [Parameter(Mandatory=$true)][string]$Token
)

$headers = @{ Authorization = "Bearer $Token"; "Content-Type" = "application/json" }
$readiness = Invoke-RestMethod -Uri "$ApiUrl/infrastructure/dr-plans/$PlanId/readiness" -Headers $headers
$readiness | ConvertTo-Json -Depth 8
if (-not $readiness.ready) {
    throw "Plano não está pronto para drill. Corrija os bloqueios antes de continuar."
}
$body = @{ run_type = "drill"; reason = "Drill iniciado por script operacional" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$ApiUrl/infrastructure/dr-plans/$PlanId/runs" -Headers $headers -Body $body
