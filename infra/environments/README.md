# Ambientes EduCode

Use bancos, Redis, volumes, URLs e segredos diferentes para desenvolvimento, homologação e produção.

- Desenvolvimento: `docker compose up -d`.
- Homologação: `docker compose -f docker-compose.yml -f compose.homolog.yaml up -d`.
- Produção: `docker compose -f docker-compose.yml -f compose.production.yaml up -d`.

Nunca reutilize o `.env` de desenvolvimento em produção.
