param(
    [string]$FrontendUrl = "http://localhost:5173",
    [string]$BackendUrl = "http://localhost:8000/api/v1",
    [string]$TeacherEmail = $env:EDUCODE_E2E_TEACHER_EMAIL,
    [string]$TeacherPassword = $env:EDUCODE_E2E_TEACHER_PASSWORD,
    [string]$DeliveryId = $env:EDUCODE_E2E_DELIVERY_ID
)

$ErrorActionPreference = "Stop"

function Assert-EduCode {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Assert-ProtectedEndpoint {
    param([string]$Uri)

    try {
        Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 15 | Out-Null
        throw "O endpoint protegido aceitou uma chamada sem autenticação: $Uri"
    }
    catch {
        $response = $_.Exception.Response
        if ($null -eq $response) {
            throw
        }

        $statusCode = [int]$response.StatusCode
        if ($statusCode -notin @(401, 403)) {
            throw "O endpoint protegido retornou HTTP $statusCode em vez de 401/403: $Uri"
        }
    }
}

$frontend = Invoke-WebRequest -Uri $FrontendUrl -UseBasicParsing -TimeoutSec 15
Assert-EduCode ($frontend.StatusCode -eq 200) "O frontend não respondeu HTTP 200."
Assert-EduCode (
    $frontend.Content -match "<title>EduCode Enterprise 2.0</title>"
) "O HTML do frontend não contém o título esperado do EduCode."

$live = Invoke-RestMethod -Uri "$BackendUrl/health/live" -TimeoutSec 15
$ready = Invoke-RestMethod -Uri "$BackendUrl/health/ready" -TimeoutSec 15
Assert-EduCode ($live.status -eq "alive") "O healthcheck live não está saudável."
Assert-EduCode ($ready.status -eq "ready") "O healthcheck ready não está saudável."
Assert-EduCode (
    [string]$live.version -eq "0.16.11.6"
) "A versão em execução não corresponde à Sprint 16.11.6."

$backendOrigin = $BackendUrl -replace "/api/v1/?$", ""
$openApi = Invoke-RestMethod -Uri "$backendOrigin/openapi.json" -TimeoutSec 30
$routeNames = @($openApi.paths.PSObject.Properties.Name)
$monitorRoute = "/api/v1/comic-page-editor/activity-deliveries/{delivery_id}/monitoring"
$actionsRoute = "/api/v1/assessment-delivery/sessions/{session_id}/actions"
Assert-EduCode ($monitorRoute -in $routeNames) "A rota do monitor não está no OpenAPI."
Assert-EduCode ($actionsRoute -in $routeNames) "A rota de ações docentes não está no OpenAPI."

$protectedProbe = "$BackendUrl/comic-page-editor/activity-deliveries/00000000-0000-0000-0000-000000000000/monitoring"
Assert-ProtectedEndpoint $protectedProbe

$authenticated = $false
$monitorValidated = $false

if ($TeacherEmail -and $TeacherPassword) {
    $loginBody = @{
        email = $TeacherEmail.Trim().ToLowerInvariant()
        password = $TeacherPassword
        remember_me = $false
    } | ConvertTo-Json

    $tokens = Invoke-RestMethod `
        -Uri "$BackendUrl/auth/login" `
        -Method Post `
        -ContentType "application/json" `
        -Body $loginBody `
        -TimeoutSec 15

    Assert-EduCode ([bool]$tokens.access_token) "O login não retornou access token."
    $headers = @{ Authorization = "Bearer $($tokens.access_token)" }
    $actor = Invoke-RestMethod -Uri "$BackendUrl/auth/me" -Headers $headers -TimeoutSec 15
    Assert-EduCode ([bool]$actor.id) "O usuário autenticado não foi carregado."
    $authenticated = $true

    if ($DeliveryId) {
        $snapshot = Invoke-RestMethod `
            -Uri "$BackendUrl/comic-page-editor/activity-deliveries/$DeliveryId/monitoring" `
            -Headers $headers `
            -TimeoutSec 30

        Assert-EduCode (
            $snapshot.monitoring.transport -eq "AUTHENTICATED_POLLING"
        ) "O monitor não informou o transporte autenticado esperado."
        Assert-EduCode (
            $snapshot.privacy.answers_exposed -eq $false
        ) "O monitor expôs respostas de estudantes."
        Assert-EduCode (
            $snapshot.privacy.answer_keys_exposed -eq $false
        ) "O monitor expôs gabaritos no snapshot docente."
        Assert-EduCode (
            $snapshot.privacy.device_details_exposed -eq $false
        ) "O monitor expôs detalhes de dispositivo."
        $monitorValidated = $true
    }
}

[PSCustomObject]@{
    success = $true
    version = [string]$live.version
    frontend_status = [int]$frontend.StatusCode
    live = [string]$live.status
    ready = [string]$ready.status
    openapi_routes = $true
    unauthenticated_access_blocked = $true
    authenticated_flow = $authenticated
    monitoring_snapshot = $monitorValidated
}

if (-not $authenticated) {
    Write-Warning (
        "Fluxo autenticado não executado. Defina EDUCODE_E2E_TEACHER_EMAIL e " +
        "EDUCODE_E2E_TEACHER_PASSWORD; para validar o snapshot, defina também " +
        "EDUCODE_E2E_DELIVERY_ID."
    )
}
