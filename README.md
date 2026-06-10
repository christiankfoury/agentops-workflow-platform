# AgentOps Workflow Platform

An enterprise-style multi-agent workflow platform that improves factual accuracy and reduces unsupported claims compared to a single-agent baseline.

See [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) for the full product specification.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.12, Pydantic, SQLAlchemy, Alembic |
| Agents | LangGraph (Phase 8+) |
| Database | PostgreSQL (Phase 3+) |
| Package manager (JS) | pnpm workspaces |
| Package manager (Python) | uv |

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 20+
- [pnpm](https://pnpm.io/installation) (`npm install -g pnpm`)

## Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd agentops-workflow-platform

# 2. Install JS dependencies
pnpm install

# 3. Install Python dependencies
cd apps/api
uv sync
cd ../..

# 4. Copy environment files
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.local.example apps/web/.env.local
```

## Start Development Servers

**Backend (port 8000):**
```bash
cd apps/api
uv run uvicorn src.main:app --reload --port 8000
```

**Frontend (port 3000):**
```bash
pnpm --filter @agentops/web dev
```

## Verify

- API health check: `curl http://localhost:8000/health` → `{"status":"ok"}`
- Frontend: open `http://localhost:3000`

## Run Backend Tests

```bash
cd apps/api
uv run pytest
```

## Lint and Typecheck

```bash
# Python
cd apps/api && uv run ruff check src/ tests/

# TypeScript
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
scripts/        Utility scripts (Phase 3+)
docker/         Docker configs (Phase 3+)
```
