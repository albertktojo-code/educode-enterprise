SHELL := /bin/bash

.PHONY: help up down logs ps build migrate test test-backend lint format clean preflight smoke backup migration-check release-preflight drain-workers resume-workers cloud-up helm-template k8s-preflight

help:
	@echo "Comandos disponíveis:"
	@echo "  make up            Sobe todos os serviços"
	@echo "  make down          Para e remove os containers"
	@echo "  make logs          Exibe logs"
	@echo "  make migrate       Executa migrations"
	@echo "  make test          Executa os testes do backend"
	@echo "  make lint          Executa verificações de qualidade"
	@echo "  make format        Formata o backend"
	@echo "  make preflight     Valida dependências e segurança"
	@echo "  make smoke         Executa teste rápido pós-implantação"
	@echo "  make backup        Cria backup manual auditável"
	@echo "  make migration-check Valida migrations sem alterar o banco"
	@echo "  make release-preflight Executa gates de implantação"
	@echo "  make drain-workers Drena workers com checkpoint"
	@echo "  make cloud-up       Sobe MinIO opcional"
	@echo "  make helm-template  Renderiza o chart Kubernetes"

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

build:
	docker compose build

migrate:
	docker compose exec backend alembic upgrade head

test: test-backend

test-backend:
	docker compose exec backend pytest -q

lint:
	docker compose exec backend ruff check app tests
	docker compose exec backend mypy app
	docker compose exec frontend npm run lint

format:
	docker compose exec backend ruff format app tests
	docker compose exec backend ruff check --fix app tests

clean:
	docker compose down --remove-orphans
	find backend -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.pytest_cache frontend/dist

preflight:
	docker compose run --rm backend python -m app.operations.preflight

smoke:
	python scripts/smoke_test.py

backup:
	docker compose run --rm backend python -m app.operations.backup

# Sprint 12.2
workers:
	docker compose up -d redis worker-ai worker-documents worker-analytics worker-default

logs-workers:
	docker compose logs -f worker-ai worker-documents worker-analytics worker-default

operations-status:
	docker compose ps redis worker-ai worker-documents worker-analytics worker-default


migration-check:
	docker compose run --rm backend python -m app.operations.migration_check --json

release-preflight:
	powershell -ExecutionPolicy Bypass -File scripts/release-preflight.ps1

drain-workers:
	docker compose run --rm backend python -m app.operations.workers drain --queue all

resume-workers:
	docker compose run --rm backend python -m app.operations.workers resume --queue all


cloud-up:
	docker compose --profile cloud up -d minio minio-init

helm-template:
	helm template educode infra/kubernetes/helm/educode -f infra/kubernetes/helm/educode/values-homologation.yaml

k8s-preflight:
	powershell -ExecutionPolicy Bypass -File scripts/k8s-preflight.ps1
