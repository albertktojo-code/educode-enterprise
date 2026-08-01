$ErrorActionPreference = 'Stop'

docker compose up -d db redis backend worker-observability
docker compose --profile observability up -d prometheus grafana

docker compose ps
Write-Host 'EduCode:     http://localhost:5173/admin/observabilidade'
Write-Host 'Métricas:    http://localhost:8000/api/v1/observability/metrics'
Write-Host 'Prometheus:  http://localhost:9090'
Write-Host 'Grafana:     http://localhost:3000'
