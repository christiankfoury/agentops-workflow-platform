# AgentOps Workflow Platform

An enterprise-style multi-agent workflow platform that improves factual accuracy and reduces unsupported claims compared to a single-agent baseline.

See [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) for the full product specification.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.12, Pydantic, SQLAlchemy, Alembic |
| Agents | LangGraph (Phase 8+) |
| Database | PostgreSQL 16 |
| Package manager (JS) | pnpm workspaces |
| Package manager (Python) | uv |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

For local development without Docker:
- Python 3.12 + [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 20+ + [pnpm](https://pnpm.io/installation)

## Quick Start (Docker)

```bash
# 1. Clone the repo
git clone <repo-url>
cd agentops-workflow-platform

# 2. Copy and configure environment
cp .env.example .env
# Add your OPENAI_API_KEY to .env (optional for now)

# 3. Start all services
make up
```

- API: http://localhost:8000
- Frontend: http://localhost:3000
- Postgres: localhost:5432

## Common Commands

```bash
make up         # Start all services (detached)
make down       # Stop all services
make build      # Rebuild images
make logs       # Tail logs for all services
make ps         # Show running containers
make test       # Run backend tests
make lint       # Run Python + JS linters
make api-shell  # Shell into the API container
make db-shell   # psql into the database
```

## Local Development (without Docker)

```bash
# Install JS dependencies
pnpm install

# Install Python dependencies
cd apps/api && uv sync && cd ../..

# Copy env files
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.local.example apps/web/.env.local

# Start backend (port 8000)
cd apps/api && uv run uvicorn src.main:app --reload --port 8000

# Start frontend (port 3000)
pnpm --filter @agentops/web dev
```

## Verify

```bash
curl http://localhost:8000/health  # {"status":"ok"}
curl http://localhost:8000/ready   # {"status":"ready"}
```

## Run Tests

```bash
make test
# or
cd apps/api && uv run pytest
```

## Lint and Typecheck

```bash
make lint
# or individually:
cd apps/api && uv run ruff check src/ tests/
pnpm --filter @agentops/web lint
pnpm --filter @agentops/web typecheck
```

## Project Structure

```
apps/
  api/          FastAPI backend
  web/          Next.js frontend
packages/
  shared/       Shared TypeScript types
docs/           Project documentation
scripts/        Utility scripts
docker/         Docker configs
```
