# Sprint 13.1 — Operação e Observabilidade

A Sprint 13.1 amplia o endurecimento da plataforma com telemetria, objetivos de confiabilidade, quotas institucionais e reconciliação de dados.

## Entregas principais

- migration `0025_ops_observability`;
- métricas HTTP em formato Prometheus;
- `request_id` e `trace_id` em todas as respostas;
- OpenTelemetry opcional com exportação OTLP;
- worker periódico de observabilidade;
- snapshots persistidos das métricas operacionais;
- SLOs versionados por organização;
- avaliação de cumprimento e orçamento de erro;
- regras de alerta explicáveis e cooldown;
- reconhecimento e resolução de alertas;
- quotas por organização com modos observar, avisar ou bloquear;
- bloqueio efetivo de tarefas simultâneas e orçamento de IA quando configurado;
- diagnóstico integrado de PostgreSQL, Redis, armazenamento, workers e migration;
- reconciliação de vínculos e recuperação segura de tarefas abandonadas;
- painel administrativo `/admin/observabilidade`;
- Prometheus e Grafana opcionais pelo profile Docker `observability`.

## Fonte definitiva

O PostgreSQL permanece como fonte definitiva dos SLOs, alertas, quotas, diagnósticos e reconciliações. Prometheus e Grafana são recursos complementares de visualização e não substituem os registros auditáveis do EduCode.

## Serviços

A instalação padrão acrescenta o `worker-observability`. Prometheus e Grafana são iniciados somente quando solicitado:

```powershell
docker compose --profile observability up -d
```

Acessos locais:

- painel EduCode: `http://localhost:5173/admin/observabilidade`;
- métricas: `http://localhost:8000/api/v1/observability/metrics`;
- Prometheus: `http://localhost:9090`;
- Grafana: `http://localhost:3000`.

## Migration

```text
0024_platform_hardening
        ↓
0025_ops_observability
```

O identificador possui menos de 32 caracteres.
