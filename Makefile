.PHONY: up down build logs ps test lint api-shell db-shell

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

test:
	cd apps/api && uv run pytest

lint:
	cd apps/api && uv run ruff check src/ tests/
	pnpm --filter @agentops/web lint

api-shell:
	docker compose exec api bash

db-shell:
	docker compose exec db psql -U postgres agentops
