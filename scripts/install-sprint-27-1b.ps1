[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$SprintName = '27.1B'
$BaseRevision = '0059_school_admissions'
$TargetRevision = '0060_enrollment_documents'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ChecksumPath = Join-Path $RepoRoot 'docs\SPRINT_27_1B_SHA256SUMS.txt'
$ReportDirectory = Join-Path $RepoRoot 'storage\sprint-reports'
$StartedAt = Get-Date

function Invoke-Checked {
    param([Parameter(Mandatory)][string]$Description, [Parameter(Mandatory)][scriptblock]$Command)
    Write-Host "`n==> $Description" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$Description falhou com código $LASTEXITCODE." }
}

function Read-Checksums {
    if (-not (Test-Path -LiteralPath $ChecksumPath -PathType Leaf)) {
        throw "Arquivo de checksums ausente: $ChecksumPath"
    }
    $entries = @{}
    foreach ($line in Get-Content -LiteralPath $ChecksumPath -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) { continue }
        if ($line -notmatch '^([0-9a-f]{64})  (.+)$') { throw "Linha inválida: $line" }
        $entries[$Matches[2].Replace('\', '/')] = $Matches[1]
    }
    if ($entries.Count -eq 0) { throw 'O manifesto de checksums está vazio.' }
    return $entries
}

function Write-InstallReport {
    param([Parameter(Mandatory)][string]$Status, [string]$Message = '')
    New-Item -ItemType Directory -Path $ReportDirectory -Force | Out-Null
    $reportPath = Join-Path $ReportDirectory ('sprint-27-1b-{0}.json' -f (Get-Date -Format 'yyyyMMddTHHmmss'))
    [ordered]@{
        sprint = $SprintName; status = $Status; message = $Message
        base_revision = $BaseRevision; target_revision = $TargetRevision
        started_at = $StartedAt.ToString('o'); finished_at = (Get-Date).ToString('o')
        repository = $RepoRoot; untracked_files_preserved = $true
        migration_order = 'after-tests-and-builds'
    } | ConvertTo-Json | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Write-Host "Relatório: $reportPath" -ForegroundColor DarkGray
}

Push-Location $RepoRoot
try {
    if (-not (Test-Path 'docker-compose.yml') -or -not (Test-Path 'backend') -or -not (Test-Path 'frontend')) {
        throw 'A pasta informada não é a raiz consolidada do EduCode.'
    }
    $checksums = Read-Checksums
    foreach ($relativePath in $checksums.Keys) {
        $absolutePath = Join-Path $RepoRoot $relativePath
        if (-not (Test-Path -LiteralPath $absolutePath -PathType Leaf)) { throw "Payload ausente: $relativePath" }
        $actual = (Get-FileHash -LiteralPath $absolutePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $checksums[$relativePath]) { throw "Checksum divergente: $relativePath" }
    }

    if (Get-Command git -ErrorAction SilentlyContinue) {
        $unexpectedTracked = @(); $untracked = @()
        foreach ($line in (& git status --porcelain=v1)) {
            if ($line.Length -lt 4) { continue }
            $path = $line.Substring(3).Replace('\', '/')
            if ($line.StartsWith('??')) { $untracked += $path }
            elseif (-not $checksums.ContainsKey($path)) { $unexpectedTracked += $path }
        }
        if ($unexpectedTracked.Count) { throw ('Mudanças rastreadas externas ao payload: ' + ($unexpectedTracked -join ', ')) }
        if ($untracked.Count) { Write-Warning ("Arquivos não rastreados preservados: {0}" -f $untracked.Count) }
    }

    Invoke-Checked 'Validando Docker Compose' { docker compose config --quiet }
    Invoke-Checked 'Subindo dependências para inspeção e backup' { docker compose up -d db redis }
    $revisionOutput = (& docker compose run --rm backend alembic current 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0 -or ($revisionOutput -notmatch $BaseRevision -and $revisionOutput -notmatch $TargetRevision)) {
        throw "Revisão incompatível. Esperado $BaseRevision ou $TargetRevision."
    }
    Invoke-Checked 'Confirmando head único do Alembic' { docker compose run --rm backend alembic heads }
    Invoke-Checked 'Criando backup anterior à instalação' { docker compose run --rm backend python -m app.operations.backup }

    # Regra obrigatória: nenhum upgrade antes dos testes e builds abaixo.
    Invoke-Checked 'Executando lint Python' {
        docker compose run --rm backend ruff check app/school_admissions app/db/model_registry.py tests/test_school_admissions_sprint_27_1a.py tests/test_school_admissions_sprint_27_1b.py tests/test_school_admissions_documents_integration.py
    }
    Invoke-Checked 'Executando testes focados pré-migration' {
        docker compose run --rm --volume "${RepoRoot}/frontend:/frontend:ro" --volume "${RepoRoot}/scripts:/scripts:ro" backend pytest -q tests/test_school_admissions_sprint_27_1a.py tests/test_school_admissions_sprint_27_1b.py tests/test_school_admissions_documents_integration.py tests/test_student_portfolio_sprint_18_9.py tests/test_student_portfolio_sprint_18_11.py
    }
    Invoke-Checked 'Executando lint do frontend' { docker compose run --rm frontend npm run lint }
    Invoke-Checked 'Executando build do frontend' { docker compose run --rm frontend npm run build }

    if ($revisionOutput -match $BaseRevision) {
        Invoke-Checked "Aplicando migration $TargetRevision" { docker compose run --rm backend alembic upgrade head }
    } else { Write-Host "Migration já aplicada; etapa idempotente ignorada." -ForegroundColor Yellow }

    Invoke-Checked 'Construindo backend e frontend' { docker compose build backend frontend }
    Invoke-Checked 'Subindo serviços consolidados' { docker compose up -d }
    $backendPort = if ($env:BACKEND_EXTERNAL_PORT) { $env:BACKEND_EXTERNAL_PORT } else { '8000' }
    $readyUrl = "http://localhost:$backendPort/api/v1/health/ready"; $ready = $false
    for ($attempt = 1; $attempt -le 20; $attempt++) {
        try { if ((Invoke-RestMethod -Uri $readyUrl -TimeoutSec 5).status -eq 'ready') { $ready = $true; break } }
        catch { Start-Sleep -Seconds 2 }
    }
    if (-not $ready) { throw "Healthcheck não ficou pronto: $readyUrl" }
    $finalRevision = (& docker compose run --rm backend alembic current 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0 -or $finalRevision -notmatch $TargetRevision) { throw "A revisão final não é $TargetRevision." }
    Invoke-Checked 'Verificando serviços' { docker compose ps }
    Write-InstallReport -Status 'success' -Message 'Instalação e validações concluídas.'
} catch {
    Write-InstallReport -Status 'failed' -Message $_.Exception.Message
    throw
} finally { Pop-Location }
