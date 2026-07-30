# Sprint 12.2 — Processamento assíncrono e operação da IA

A Sprint 12.2 conecta o AI Fabric e os demais módulos do EduCode a uma infraestrutura persistente de filas e workers.

## Arquitetura

```text
FastAPI → PostgreSQL (estado definitivo) → Redis (fila/eventos) → workers
                                              ↓
                              notificações, checkpoints e resultados
```

O Redis nunca é a fonte única do estado. Reiniciar ou perder o Redis não elimina as tarefas, pois os workers recuperam registros pendentes no PostgreSQL.

## Serviços Docker

- `db`: PostgreSQL com pgvector;
- `redis`: fila com persistência AOF;
- `backend`: API FastAPI;
- `worker-ai`: gerações do AI Fabric e acessibilidade;
- `worker-documents`: PDF, indexação, importações, exportações e relatórios;
- `worker-analytics`: recálculos, evidências, métricas e intervenções;
- `worker-default`: tarefas gerais;
- `frontend`: React/Vite.

## Funcionalidades

- tarefas persistentes e isoladas por organização;
- idempotência por chave única;
- filas por prioridade `urgent`, `high`, `normal` e `low`;
- retries com backoff;
- cancelamento cooperativo;
- checkpoints e recuperação de tarefas abandonadas;
- dependências entre tarefas;
- limite de concorrência por usuário;
- reservas de orçamento;
- circuit breaker por provedor;
- cache semântico somente para resultados aprovados;
- notificações internas;
- heartbeats dos workers;
- dead-letter operacional por tarefas com status `failed`;
- eventos persistentes e endpoint SSE;
- painel de tarefas em `/tarefas`;
- painel administrativo em `/admin/operacao`.

## Estados

```text
pending → queued → processing → validating → completed
                    ↓
                 retrying → queued
                    ↓
                  failed
```

Também podem ocorrer `waiting_provider`, `cancel_requested`, `cancelled` e `expired`.

## Idempotência

A combinação `organization_id + idempotency_key` é única. Reenvios com a mesma chave retornam a tarefa existente e não duplicam publicação, importação, relatório ou geração.

## Recuperação

A cada período o worker verifica o PostgreSQL e recoloca na fila:

- tarefas `pending`, `queued` ou `retrying` sem mensagem válida no Redis;
- tarefas em processamento sem atualização por mais de dez minutos.

Mensagens duplicadas são descartadas quando a tarefa já está processando ou concluída.

## Cache semântico

Resultados de IA aprovados são registrados por organização, modelo, template, contexto RAG, entrada e parâmetros. Uma geração compatível pode reutilizar o resultado quando `reuse_cache` não for desativado.

O cache:

- nunca atravessa organizações;
- exige resultado aprovado;
- tem validade padrão de 30 dias;
- registra quantidade de reutilizações;
- não inclui prioridade e parâmetros operacionais no fingerprint.

## Migration

```text
0022_ai_fabric_advanced_flow
        ↓
0023_ai_async_operations
```

Novas tabelas:

- `background_jobs`;
- `background_job_attempts`;
- `background_job_events`;
- `job_dependencies`;
- `job_notifications`;
- `provider_circuit_states`;
- `semantic_cache_entries`;
- `resource_reservations`;
- `worker_heartbeats`.

## Configuração

```env
REDIS_URL=redis://redis:6379/0
REDIS_EXTERNAL_PORT=6379
REDIS_VOLUME_NAME=educode-redis-data
JOB_QUEUE_PREFIX=educode
WORKER_HEARTBEAT_SECONDS=10
WORKER_STEP_DELAY_MS=150
JOB_EVENT_RETENTION_DAYS=30
MAX_CONCURRENT_JOBS_PER_USER=5
```

## Atualização

```powershell
docker compose down --remove-orphans
docker compose up -d db redis
docker compose run --rm backend alembic upgrade head
docker compose up -d --build
docker compose run --rm backend alembic current
docker compose ps
```

Resultado esperado:

```text
0023_ai_async_operations (head)
```

Nunca use `docker compose down -v` durante uma atualização.
