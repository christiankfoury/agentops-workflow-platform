---
name: phase2-monorepo-setup
description: Design spec for Phase 2 — monorepo structure, FastAPI backend scaffold, Next.js frontend scaffold, tooling, and environment setup. No agents implemented.
metadata:
  type: project
---

# Phase 2: Repository Setup and Monorepo Structure — Design Spec

## Goal

Establish the full-stack monorepo foundation for the Enterprise Multi-Agent Workflow Platform. No agents, no database migrations, no Docker. This phase creates the directory structure, installs tooling, and verifies that both apps can start locally.

## Directory Structure

```
agentops-workflow-platform/        ← existing repo root
  apps/
    api/                           ← FastAPI backend
      src/
        main.py                    ← FastAPI app, health endpoint
        config.py                  ← Pydantic BaseSettings (reads .env)
      pyproject.toml               ← Python deps + ruff config
      .python-version              ← pins Python 3.12
      .env.example                 ← documented env vars
    web/                           ← Next.js frontend
      src/
        app/
          layout.tsx
          page.tsx
      package.json
      tsconfig.json
      next.config.ts
      tailwind.config.ts
      postcss.config.mjs
      .env.local.example           ← documented env vars
  packages/
    shared/                        ← shared TypeScript types
      src/
        index.ts                   ← barrel export (stub)
      package.json
      tsconfig.json
  docs/                            ← project documentation
    PROJECT_SPEC.md                ← moved from root
    phases.md                      ← moved from root
    overview.md                    ← moved from root
    superpowers/
      specs/
        this-file.md
  scripts/                         ← placeholder for future scripts
  docker/                          ← placeholder for Phase 3
  .gitignore                       ← updated to cover all tooling
  pnpm-workspace.yaml              ← declares apps/* and packages/*
  package.json                     ← workspace root (no deps, scripts only)
  README.md                        ← expanded with setup instructions
```

## Backend (apps/api)

**Language & runtime:** Python 3.12, managed with `uv`.

**Key dependencies:**
- `fastapi` — web framework
- `uvicorn[standard]` — ASGI server
- `pydantic-settings` — environment config via `BaseSettings`
- `sqlalchemy` — ORM (imported, not configured yet)
- `alembic` — migrations (imported, not configured yet)
- `httpx` — async HTTP client (for LLM calls later)

**Dev dependencies:**
- `ruff` — linting and formatting (replaces black, isort, pylint)
- `pytest` — testing
- `pytest-asyncio` — async test support

**Ruff configuration** (in `pyproject.toml`):
- `line-length = 100`
- rules: `E`, `F`, `I` (isort), `UP` (pyupgrade)
- formatter: ruff format (black-compatible)

**Entry point:** `src/main.py` exports a FastAPI `app` with:
- `GET /health` → `{"status": "ok"}`
- `GET /` → redirect or brief API description

**Config:** `src/config.py` defines a `Settings` class with `model_config = SettingsConfigDict(env_file=".env")`. Fields added later as needed.

**Start command:** `uv run uvicorn src.main:app --reload`

## Frontend (apps/web)

**Framework:** Next.js 15 with App Router, TypeScript strict mode.

**Key dependencies:**
- `next` 15
- `react` 19
- `typescript`
- `tailwindcss` + `@tailwindcss/typography`
- `shadcn/ui` initialized via CLI (`npx shadcn@latest init`), no components added yet
- `lucide-react` — icons (peer dep of shadcn/ui)

**Dev dependencies:**
- `eslint` + `eslint-config-next`
- `prettier` + `prettier-plugin-tailwindcss`

**TypeScript config:** strict mode, path alias `@/*` → `./src/*`.

**Content:** `app/page.tsx` renders a minimal placeholder page ("AgentOps Workflow Platform — coming soon").

**Start command:** `pnpm dev` (runs on port 3000)

## Shared Package (packages/shared)

Stub TypeScript package. Exports nothing meaningful yet but establishes the import path (`@agentops/shared`) for future shared types (workflow states, API response shapes, etc.).

## Workspace Root

`pnpm-workspace.yaml`:
```yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

Root `package.json` has no runtime deps, only scripts:
```json
{
  "scripts": {
    "dev:web": "pnpm --filter web dev",
    "dev:api": "cd apps/api && uv run uvicorn src.main:app --reload",
    "lint": "pnpm --filter web lint",
    "typecheck": "pnpm --filter web typecheck"
  }
}
```

## Environment Files

**apps/api/.env.example:**
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agentops
OPENAI_API_KEY=
ENVIRONMENT=development
```

**apps/web/.env.local.example:**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## .gitignore Updates

Ensure the following are covered:
- Python: `__pycache__/`, `*.pyc`, `.venv/`, `.uv/`, `*.egg-info/`, `dist/`, `.ruff_cache/`
- Node: `node_modules/`, `.next/`, `.turbo/`
- Environment: `.env`, `.env.local` (keep `.env.example` and `.env.local.example`)

## README Update

Expand `README.md` with:
- Project name and one-line description
- Tech stack summary
- Prerequisites (Python 3.12, uv, Node 20+, pnpm)
- Setup instructions (clone, `pnpm install`, `uv sync`, copy env files)
- Start commands for each app
- Link to `PROJECT_SPEC.md` in `docs/`

## What This Phase Does NOT Include

- Docker / Docker Compose (Phase 3)
- Database setup or migrations (Phase 4)
- Any API endpoints beyond `/health` (Phase 5)
- Any real frontend pages (Phase 6)
- LLM or agent code (Phase 8+)
- Authentication (Phase 54)

## Success Criteria

- `cd apps/api && uv run uvicorn src.main:app --reload` starts without errors
- `cd apps/web && pnpm dev` starts without errors
- `GET http://localhost:8000/health` returns `{"status": "ok"}`
- `http://localhost:3000` renders the placeholder page
- `ruff check apps/api/src` passes with no errors
- `pnpm --filter web lint` passes with no errors
- `pnpm --filter web typecheck` passes with no errors
