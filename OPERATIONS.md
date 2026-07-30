# Operação do EduCode Enterprise 2.0

## Preflight antes da atualização

```powershell
docker compose up -d db redis
docker compose run --rm backend python -m app.operations.preflight
```

O comando retorna código 0 somente quando PostgreSQL, Redis, armazenamento e configurações críticas estão prontos.

## Atualização segura

```powershell
docker compose down --remove-orphans
docker compose up -d db redis
docker compose run --rm backend python -m app.operations.preflight
docker compose run --rm backend alembic upgrade head
docker compose up -d --build
docker compose ps
```

Nunca utilize `docker compose down -v` em ambientes com dados.

## Backup manual

```powershell
docker compose run --rm backend python -m app.operations.backup
```

O arquivo é salvo no volume `educode-backup-storage`, com checksum SHA-256. O painel `/admin/plataforma` também cria backups pela fila, exclusivamente para o operador global (`is_superuser`).

## Health checks

- `/api/v1/health/live`: processo ativo;
- `/api/v1/health/ready`: PostgreSQL, Redis e volumes prontos;
- `/api/v1/health/dependencies`: diagnóstico resumido;
- `/api/v1/platform/preflight`: verificação administrativa completa.

## Falha de migration

1. execute `docker compose run --rm backend alembic current`;
2. execute `docker compose run --rm backend alembic heads`;
3. confirme que existe apenas um head;
4. não altere manualmente `alembic_version` sem analisar o erro;
5. restaure o backup quando uma alteração de dados tiver sido parcialmente aplicada.

## Worker travado

Consulte `/admin/operacao`, preserve o checkpoint, cancele ou repita a tarefa. Workers usam `init: true` e encerramento gracioso do Docker Compose.


## Teste real de restauração

No painel `/admin/plataforma`, selecione **Testar restauração** em um backup concluído. O EduCode agenda uma tarefa que:

1. confere o checksum do arquivo;
2. verifica a estrutura do `database.dump`;
3. cria um banco temporário isolado;
4. executa `pg_restore`;
5. consulta as tabelas e a migration restaurada;
6. remove o banco temporário.

Acompanhe o resultado em `/tarefas`. O usuário do PostgreSQL precisa possuir permissão para criar e remover o banco temporário. Na imagem padrão, o usuário definido por `POSTGRES_USER` possui essa permissão.

## Smoke test pós-implantação

Com os serviços ativos, execute:

```powershell
$env:EDUCODE_BASE_URL="http://localhost:8000"
$env:INITIAL_ADMIN_EMAIL="albertktojo@gmail.com"
$env:INITIAL_ADMIN_PASSWORD="SUA_SENHA"
python .\scripts\smoke_test.py
```

O teste verifica liveness, readiness, autenticação, perfil e versão/migration da plataforma sem criar ou excluir dados.

## Observabilidade — Sprint 13.1

O worker `worker-observability` coleta snapshots operacionais e avalia regras de alerta no intervalo definido por `METRIC_SNAPSHOT_INTERVAL_SECONDS`.

```powershell
docker compose logs worker-observability --tail 100
```

Para iniciar Prometheus e Grafana:

```powershell
docker compose --profile observability up -d prometheus grafana
```

Acesse o painel interno em `/admin/observabilidade`. Ele continua disponível mesmo quando Prometheus ou Grafana não estiverem ativos.

### Diagnóstico integrado

O botão **Executar diagnóstico** verifica PostgreSQL, Redis, volumes, workers e migration. Cada execução é persistida em `diagnostic_runs` e recebe o mesmo `request_id` da chamada administrativa.

### Reconciliação

A reconciliação pode somente verificar ou reparar estados operacionais seguros. Use primeiro **Somente verificar**. A opção de reparo pode recolocar tarefas abandonadas na situação pendente, mas não altera notas ou respostas dos estudantes.


## Releases e continuidade — Sprint 13.2

O painel `/admin/releases` centraliza etapas, artefatos, aprovações, RPO/RTO e janelas de manutenção.

Antes de atualizar:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/release-preflight.ps1
docker compose run --rm backend python -m app.operations.workers drain --queue all
```

Após subir a nova versão:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/post-deploy-smoke.ps1
docker compose run --rm backend python -m app.operations.workers resume --queue all
```

O modo `read_only` bloqueia escritas e preserva consultas. O modo `maintenance` bloqueia o acesso comum e mantém apenas health checks e autenticação.


## Infraestrutura distribuída — Sprint 13.3

### MinIO local opcional

```powershell
docker compose --profile cloud up -d minio minio-init
```

Acesse o console em `http://localhost:9001`. Altere a senha do exemplo antes de qualquer ambiente compartilhado.

### Kubernetes

```powershell
powershell -ExecutionPolicy Bypass -File scripts/k8s-preflight.ps1
```

O preflight renderiza homologação e produção sem aplicar recursos.

### Disaster recovery

Use `/admin/infraestrutura` para registrar clusters, storage e plano. Execute primeiro um `drill`. Failover/failback exigem operador global; a execução automática permanece desativada.
