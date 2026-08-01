$ErrorActionPreference = "Stop"

Write-Host "EduCode Sprint 14 - Kubernetes preflight" -ForegroundColor Cyan

$required = @("kubectl", "helm")
foreach ($command in $required) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Comando obrigatório não encontrado: $command"
    }
}

kubectl version --client
helm version --short

$chart = "infra/kubernetes/helm/educode"
helm lint $chart
helm template educode-homolog $chart -f "$chart/values-homologation.yaml" | Out-Null
helm template educode-production $chart -f "$chart/values-production.yaml" | Out-Null

Write-Host "Chart Helm validado. Nenhuma alteração foi aplicada ao cluster." -ForegroundColor Green
