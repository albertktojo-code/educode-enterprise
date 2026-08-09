[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$BaseRevision = '0061_enrollment_contracts'
$TargetRevision = '0062_enrollment_movements'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ChecksumPath = Join-Path $RepoRoot 'docs\SPRINT_27_2B_SHA256SUMS.txt'
$StartedAt = Get-Date
$Status = 'failed'
$Message = ''

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
    $Checksums = @{}
    foreach ($Line in Get-Content -LiteralPath $ChecksumPath -Encoding UTF8) {
        if ($Line -match '^([0-9a-f]{64})  (.+)$') { $Checksums[$Matches[2].Replace('\','/')] = $Matches[1] }
    }
    if (-not $Checksums.Count) { throw 'Manifesto de checksums vazio ou ausente.' }
    foreach ($Path in $Checksums.Keys) {
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Payload ausente: $Path" }
        if ((Get-FileHash $Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Checksums[$Path]) {
            throw "Checksum divergente: $Path"
        }
    }
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $Unexpected = @(); $Untracked = @()
        foreach ($Line in (& git status --porcelain=v1)) {
            if ($Line.Length -lt 4) { continue }
            $Path = $Line.Substring(3).Replace('\','/')
            if ($Line.StartsWith('??')) { $Untracked += $Path }
            elseif (-not $Checksums.ContainsKey($Path)) { $Unexpected += $Path }
        }
        if ($Unexpected.Count) { throw ('Mudanças rastreadas externas: ' + ($Unexpected -join ', ')) }
        if ($Untracked.Count) { Write-Warning "Arquivos não rastreados serão preservados: $($Untracked.Count)" }
    }
    Invoke-Checked 'Validando Compose' { docker compose config --quiet }
    Invoke-Checked 'Subindo dependências' { docker compose up -d db redis }
    $Current = (& docker compose run --rm backend alembic current 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0 -or ($Current -notmatch $BaseRevision -and $Current -notmatch $TargetRevision)) {
        throw "Revisão incompatível; esperado $BaseRevision ou $TargetRevision."
    }
    Invoke-Checked 'Criando backup' { docker compose run --rm backend python -m app.operations.backup }
    Invoke-Checked 'Lint Python' { docker compose run --rm backend ruff check app/school_admissions app/db/model_registry.py app/api/v1/router.py alembic/versions/0062_enrollment_movements.py tests/test_school_admissions_sprint_27_2b.py tests/test_school_admissions_movements_integration.py }
    Invoke-Checked 'Testes pré-migration' { docker compose run --rm --volume "${RepoRoot}/frontend:/frontend:ro" backend pytest -q tests/test_school_admissions_sprint_27_2a.py tests/test_school_admissions_sprint_27_2b.py }
    Invoke-Checked 'Lint frontend' { docker compose run --rm frontend npm run lint }
    Invoke-Checked 'Build frontend' { docker compose run --rm frontend npm run build }
    if ($Current -match $BaseRevision) { Invoke-Checked 'Aplicando migration' { docker compose run --rm backend alembic upgrade $TargetRevision } }
    Invoke-Checked 'Subindo serviços' { docker compose up -d }
    $Final = (& docker compose run --rm backend alembic current 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0 -or $Final -notmatch $TargetRevision) { throw 'Head final incorreto.' }
    $Status = 'success'
} catch {
    $Message = $_.Exception.Message
    throw
} finally {
    $ReportDir = Join-Path $RepoRoot 'storage\sprint-reports'
    New-Item -ItemType Directory -Path $ReportDir -ErrorAction SilentlyContinue | Out-Null
    [ordered]@{sprint='27.2B';status=$Status;message=$Message;base_revision=$BaseRevision;target_revision=$TargetRevision;started_at=$StartedAt.ToString('o');finished_at=(Get-Date).ToString('o');untracked_files_preserved=$true;migration_order='after-tests-and-builds'} | ConvertTo-Json | Set-Content (Join-Path $ReportDir ('sprint-27-2b-{0}.json' -f (Get-Date -Format 'yyyyMMddTHHmmss'))) -Encoding UTF8
    Pop-Location
}
