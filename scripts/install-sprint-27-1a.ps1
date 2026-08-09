[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$SprintName = '27.1A'
$BaseRevision = '0058_student_certificates'
$TargetRevision = '0059_school_admissions'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ChecksumPath = Join-Path $RepoRoot 'docs\SPRINT_27_1A_SHA256SUMS.txt'
$ReportDirectory = Join-Path $RepoRoot 'storage\sprint-reports'
$StartedAt = Get-Date

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)][scriptblock]$Command
    )

    Write-Host "`n==> $Description" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description falhou com código $LASTEXITCODE."
    }
}

function Read-Checksums {
    if (-not (Test-Path -LiteralPath $ChecksumPath -PathType Leaf)) {
        throw "Arquivo de checksums ausente: $ChecksumPath"
    }
    $entries = @{}
    foreach ($line in Get-Content -LiteralPath $ChecksumPath -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) { continue }
        if ($line -notmatch '^([0-9a-f]{64})  (.+)$') {
            throw "Linha inválida no arquivo de checksums: $line"
        }
        $entries[$Matches[2].Replace('\', '/')] = $Matches[1]
    }
    if ($entries.Count -eq 0) { throw 'O manifesto de checksums está vazio.' }
    return $entries
}

function Write-InstallReport {
    param(
        [Parameter(Mandatory = $true)][string]$Status,
        [string]$Message = ''
    )

    New-Item -ItemType Directory -Path $ReportDirectory -Force | Out-Null
    $reportPath = Join-Path $ReportDirectory (
        'sprint-27-1a-{0}.json' -f (Get-Date -Format 'yyyyMMddTHHmmss')
    )
    [ordered]@{
        sprint = $SprintName
        status = $Status
        message = $Message
        base_revision = $BaseRevision
        target_revision = $TargetRevision
        started_at = $StartedAt.ToString('o')
        finished_at = (Get-Date).ToString('o')
        repository = $RepoRoot
        untracked_files_preserved = $true
        migration_order = 'after-tests-and-builds'
    } | ConvertTo-Json | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Write-Host "Relatório: $reportPath" -ForegroundColor DarkGray
}

Push-Location $RepoRoot
try {
    if (-not (Test-Path -LiteralPath 'docker-compose.yml' -PathType Leaf) -or
        -not (Test-Path -LiteralPath 'backend' -PathType Container) -or
        -not (Test-Path -LiteralPath 'frontend' -PathType Container)) {
        throw 'A pasta informada não é a raiz consolidada do EduCode.'
    }

    $checksums = Read-Checksums
    Write-Host 'Validando payload e SHA-256...' -ForegroundColor Cyan
    foreach ($relativePath in $checksums.Keys) {
        $absolutePath = Join-Path $RepoRoot $relativePath
        if (-not (Test-Path -LiteralPath $absolutePath -PathType Leaf)) {
            throw "Arquivo do payload ausente: $relativePath"
        }
        $actual = (Get-FileHash -LiteralPath $absolutePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $checksums[$relativePath]) {
            throw "Checksum divergente: $relativePath"
        }
    }

    if (Get-Command git -ErrorAction SilentlyContinue) {
        $unexpectedTracked = @()
        $untracked = @()
        foreach ($line in (& git status --porcelain=v1)) {
            if ($line.Length -lt 4) { continue }
            $path = $line.Substring(3).Replace('\', '/')
            if ($line.StartsWith('??')) {
                $untracked += $path
            } elseif (-not $checksums.ContainsKey($path)) {
                $unexpectedTracked += $path
            }
        }
        if ($unexpectedTracked.Count -gt 0) {
            throw ('Há mudanças rastreadas externas ao payload: ' + ($unexpectedTracked -join ', '))
        }
        if ($untracked.Count -gt 0) {
            Write-Warning ("Arquivos não rastreados serão preservados: {0}" -f $untracked.Count)
        }
    }

    Invoke-Checked 'Validando Docker Compose' { docker compose config --quiet }
    Invoke-Checked 'Subindo dependências para inspeção e backup' { docker compose up -d db redis }

    $revisionOutput = (& docker compose run --rm backend alembic current 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível consultar a revisão atual.' }
    if ($revisionOutput -notmatch [regex]::Escape($BaseRevision) -and
        $revisionOutput -notmatch [regex]::Escape($TargetRevision)) {
        throw "Revisão incompatível. Esperado $BaseRevision ou $TargetRevision."
    }
    Invoke-Checked 'Confirmando head único do Alembic' { docker compose run --rm backend alembic heads }

    Invoke-Checked 'Criando backup anterior à instalação' {
        docker compose run --rm backend python -m app.operations.backup
    }

    # Regra da sprint: nenhum upgrade é executado antes destes testes e builds.
    Invoke-Checked 'Executando lint Python' {
        docker compose run --rm backend ruff check app/school_admissions app/api/v1/router.py app/api/v1/routes_education.py app/db/model_registry.py app/db/seed.py app/models/education.py app/schemas/education.py tests/test_school_admissions_sprint_27_1a.py tests/test_school_admissions_integration.py
    }
    Invoke-Checked 'Executando testes focados pré-migration' {
        docker compose run --rm --volume "${RepoRoot}/frontend:/frontend:ro" backend pytest -q tests/test_school_admissions_sprint_27_1a.py tests/test_connect_sprint_19_1.py tests/test_connect_sprint_19_2.py
    }
    Invoke-Checked 'Executando lint do frontend' { docker compose run --rm frontend npm run lint }
    Invoke-Checked 'Executando build do frontend' { docker compose run --rm frontend npm run build }

    if ($revisionOutput -match [regex]::Escape($BaseRevision)) {
        Invoke-Checked "Aplicando migration $TargetRevision" {
            docker compose run --rm backend alembic upgrade head
        }
    } else {
        Write-Host "Migration $TargetRevision já aplicada; etapa idempotente ignorada." -ForegroundColor Yellow
    }

    Invoke-Checked 'Construindo backend e frontend' { docker compose build backend frontend }
    Invoke-Checked 'Subindo serviços consolidados' { docker compose up -d }

    $backendPort = if ($env:BACKEND_EXTERNAL_PORT) { $env:BACKEND_EXTERNAL_PORT } else { '8000' }
    $readyUrl = "http://localhost:$backendPort/api/v1/health/ready"
    $ready = $false
    for ($attempt = 1; $attempt -le 20; $attempt++) {
        try {
            $response = Invoke-RestMethod -Uri $readyUrl -TimeoutSec 5
            if ($response.status -eq 'ready') { $ready = $true; break }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    if (-not $ready) { throw "Healthcheck não ficou pronto: $readyUrl" }

    $finalRevision = (& docker compose run --rm backend alembic current 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0 -or $finalRevision -notmatch [regex]::Escape($TargetRevision)) {
        throw "A revisão final não é $TargetRevision."
    }
    Invoke-Checked 'Verificando estado dos serviços' { docker compose ps }
    Write-InstallReport -Status 'success' -Message 'Instalação e validações concluídas.'
    Write-Host "Sprint $SprintName instalada com sucesso." -ForegroundColor Green
} catch {
    Write-InstallReport -Status 'failed' -Message $_.Exception.Message
    throw
} finally {
    Pop-Location
}
