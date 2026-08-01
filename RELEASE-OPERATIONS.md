# Operação de releases do EduCode

## Homologação

```powershell
Copy-Item .env.example .env
# Ajuste segredos e URLs.
docker compose -f docker-compose.yml -f compose.homolog.yaml up -d db redis
powershell -ExecutionPolicy Bypass -File scripts/release-preflight.ps1
docker compose -f docker-compose.yml -f compose.homolog.yaml run --rm backend alembic upgrade head
docker compose -f docker-compose.yml -f compose.homolog.yaml up -d --build
powershell -ExecutionPolicy Bypass -File scripts/post-deploy-smoke.ps1
```

## Drenagem de workers

```powershell
docker compose run --rm backend python -m app.operations.workers drain --queue all
docker compose run --rm backend python -m app.operations.workers status --queue all
# Após a implantação
docker compose run --rm backend python -m app.operations.workers resume --queue all
```

## Migration check

```powershell
docker compose run --rm backend python -m app.operations.migration_check --json
```

Operações destrutivas exigem revisão e aprovação manual. Downgrade automático do banco não é realizado.

## Rollback

1. Ative modo somente leitura ou manutenção.
2. Drene os workers.
3. Preserve logs, métricas e identificadores de release.
4. Retorne backend e frontend ao digest anterior.
5. Não execute downgrade de migration sem validação.
6. Quando houver alteração destrutiva, restaure o backup associado.
7. Execute smoke tests antes de reabrir o sistema.

Nunca execute `docker compose down -v` em atualização ou rollback.
