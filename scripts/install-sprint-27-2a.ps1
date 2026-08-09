[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$BaseRevision = '0060_enrollment_documents'
$TargetRevision = '0061_enrollment_contracts'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ChecksumPath = Join-Path $RepoRoot 'docs\SPRINT_27_2A_SHA256SUMS.txt'
$StartedAt = Get-Date

function Invoke-Checked([string]$Description, [scriptblock]$Command) {
    Write-Host "`n==> $Description" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$Description falhou com código $LASTEXITCODE." }
}

Push-Location $RepoRoot
try {
    if (-not (Test-Path 'docker-compose.yml') -or -not (Test-Path 'backend') -or -not (Test-Path 'frontend')) {
        throw 'Raiz consolidada do EduCode não encontrada.'
    }
    $checksums = @{}
    foreach ($line in Get-Content -LiteralPath $ChecksumPath -Encoding UTF8) {
        if ($line -match '^([0-9a-f]{64})  (.+)$') { $checksums[$Matches[2].Replace('\','/')] = $Matches[1] }
    }
    if (-not $checksums.Count) { throw 'Manifesto de checksums vazio ou ausente.' }
    foreach ($path in $checksums.Keys) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Payload ausente: $path" }
        if ((Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $checksums[$path]) {
            throw "Checksum divergente: $path"
        }
    }
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $unexpected = @(); $untracked = @()
        foreach ($line in (& git status --porcelain=v1)) {
            if ($line.Length -lt 4) { continue }
            $path = $line.Substring(3).Replace('\','/')
            if ($line.StartsWith('??')) { $untracked += $path }
            elseif (-not $checksums.ContainsKey($path)) { $unexpected += $path }
        }
        if ($unexpected.Count) { throw ('Mudanças rastreadas externas: ' + ($unexpected -join ', ')) }
        if ($untracked.Count) { Write-Warning "Arquivos não rastreados serão preservados: $($untracked.Count)" }
    }
    Invoke-Checked 'Validando Compose' { docker compose config --quiet }
    Invoke-Checked 'Subindo dependências' { docker compose up -d db redis }
    $current = (& docker compose run --rm backend alembic current 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0 -or ($current -notmatch $BaseRevision -and $current -notmatch $TargetRevision)) {
        throw "Revisão incompatível; esperado $BaseRevision ou $TargetRevision."
    }
    Invoke-Checked 'Criando backup' { docker compose run --rm backend python -m app.operations.backup }
    # Nenhum upgrade ocorre antes destas validações.
    Invoke-Checked 'Lint Python' { docker compose run --rm backend ruff check app/school_admissions app/db/model_registry.py tests/test_school_admissions_sprint_27_2a.py tests/test_school_admissions_contracts_integration.py }
    Invoke-Checked 'Testes pré-migration' { docker compose run --rm --volume "${RepoRoot}/frontend:/frontend:ro" --volume "${RepoRoot}/scripts:/scripts:ro" backend pytest -q tests/test_school_admissions_sprint_27_1a.py tests/test_school_admissions_sprint_27_1b.py tests/test_school_admissions_sprint_27_2a.py tests/test_school_admissions_contracts_integration.py }
    Invoke-Checked 'Lint frontend' { docker compose run --rm frontend npm run lint }
    Invoke-Checked 'Build frontend' { docker compose run --rm frontend npm run build }
    if ($current -match $BaseRevision) { Invoke-Checked 'Aplicando migration' { docker compose run --rm backend alembic upgrade head } }
    Invoke-Checked 'Construindo serviços' { docker compose build backend frontend }
    Invoke-Checked 'Subindo serviços' { docker compose up -d }
    $final = (& docker compose run --rm backend alembic current 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0 -or $final -notmatch $TargetRevision) { throw 'Head final incorreto.' }
    $port = if ($env:BACKEND_EXTERNAL_PORT) { $env:BACKEND_EXTERNAL_PORT } else { '8000' }
    $ready = $false
    for ($i=0; $i -lt 20; $i++) { try { if ((Invoke-RestMethod "http://localhost:$port/api/v1/health/ready" -TimeoutSec 5).status -eq 'ready') { $ready=$true; break } } catch {}; Start-Sleep 2 }
    if (-not $ready) { throw 'Healthcheck não ficou pronto.' }
    $status = 'success'
} catch { $status = 'failed'; $message = $_.Exception.Message; throw }
finally {
    $reportDir = Join-Path $RepoRoot 'storage\sprint-reports'; New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
    [ordered]@{sprint='27.2A';status=$status;message=$message;base_revision=$BaseRevision;target_revision=$TargetRevision;started_at=$StartedAt.ToString('o');finished_at=(Get-Date).ToString('o');untracked_files_preserved=$true;migration_order='after-tests-and-builds'} | ConvertTo-Json | Set-Content (Join-Path $reportDir ('sprint-27-2a-{0}.json' -f (Get-Date -Format 'yyyyMMddTHHmmss'))) -Encoding UTF8
    Pop-Location
}
