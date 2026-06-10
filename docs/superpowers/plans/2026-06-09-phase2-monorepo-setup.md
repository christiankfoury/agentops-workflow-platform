# Phase 2: Monorepo Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the full-stack monorepo foundation — FastAPI backend, Next.js frontend, shared TypeScript package, tooling, and environment files — with no agent or database logic yet.

**Architecture:** pnpm workspaces manage the JS side (`apps/web`, `packages/shared`); `apps/api` is an independent Python project managed by uv. Both apps are verifiable by starting their dev servers and hitting `/health`.

**Tech Stack:** Python 3.12, uv, FastAPI, Pydantic-Settings, Ruff, pytest — Node 20+, pnpm, Next.js 15 (App Router), TypeScript strict, Tailwind CSS, shadcn/ui, ESLint, Prettier

---

## File Map

**Created:**
- `apps/api/src/__init__.py`
- `apps/api/src/main.py` — FastAPI app, `/health` endpoint
- `apps/api/src/config.py` — Pydantic BaseSettings
- `apps/api/tests/__init__.py`
- `apps/api/tests/test_health.py` — health endpoint test
- `apps/api/pyproject.toml` — Python deps + ruff + pytest config
- `apps/api/.python-version` — pins 3.12
- `apps/api/.env.example`
- `apps/web/` — scaffolded by `pnpm create next-app`
- `apps/web/src/app/page.tsx` — replaced with minimal placeholder
- `apps/web/src/app/layout.tsx` — replaced with clean layout
- `apps/web/.env.local.example`
- `packages/shared/src/index.ts` — stub barrel export
- `packages/shared/package.json`
- `packages/shared/tsconfig.json`
- `pnpm-workspace.yaml`
- `package.json` — workspace root
- `scripts/.gitkeep`
- `docker/.gitkeep`
- `docs/.gitkeep` (docs/ already has content from Phase 1)

**Modified:**
- `.gitignore` — add Node/pnpm/Next.js entries
- `README.md` — expanded setup instructions

**Moved (git mv):**
- `PROJECT_SPEC.md` → `docs/PROJECT_SPEC.md`
- `phases.md` → `docs/phases.md`
- `overview.md` → `docs/overview.md`

---

## Task 1: Directory skeleton + move docs

**Files:**
- Create: `scripts/.gitkeep`, `docker/.gitkeep`
- Move: `PROJECT_SPEC.md` → `docs/PROJECT_SPEC.md`, `phases.md` → `docs/phases.md`, `overview.md` → `docs/overview.md`

- [ ] **Step 1: Create placeholder directories**

```bash
mkdir -p apps/api/src apps/api/tests apps/web packages/shared/src docs scripts docker
touch scripts/.gitkeep docker/.gitkeep
```

- [ ] **Step 2: Move docs to docs/ using git mv**

```bash
git mv PROJECT_SPEC.md docs/PROJECT_SPEC.md
git mv phases.md docs/phases.md
git mv overview.md docs/overview.md
```

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "chore: scaffold directory structure and move docs"
```

---

## Task 2: Root workspace config

**Files:**
- Create: `pnpm-workspace.yaml`, `package.json` (root)

- [ ] **Step 1: Create `pnpm-workspace.yaml`**

```yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

- [ ] **Step 2: Create root `package.json`**

```json
{
  "name": "agentops-workflow-platform",
  "private": true,
  "scripts": {
    "dev:web": "pnpm --filter @agentops/web dev",
    "dev:api": "cd apps/api && uv run uvicorn src.main:app --reload --port 8000",
    "lint": "pnpm --filter @agentops/web lint",
    "typecheck": "pnpm --filter @agentops/web typecheck && pnpm --filter @agentops/shared typecheck"
  },
  "engines": {
    "node": ">=20",
    "pnpm": ">=9"
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add pnpm-workspace.yaml package.json
git commit -m "chore: add pnpm workspace config"
```

---

## Task 3: Update .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Append Node/pnpm/Next.js entries to `.gitignore`**

Add the following block to the bottom of `.gitignore`:

```
# Node / pnpm
node_modules/
.next/
.turbo/
.pnpm-store/

# Frontend environment
.env.local

# uv virtual environment (if inside project dir)
.venv/
```

> Note: `.env` is already in `.gitignore`. The `.env.local` entry ensures Next.js local env files are ignored. `.env.example` and `.env.local.example` are NOT ignored — they're committed as documentation.

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add node and frontend entries to .gitignore"
```

---

## Task 4: FastAPI backend — project config

**Files:**
- Create: `apps/api/pyproject.toml`, `apps/api/.python-version`, `apps/api/.env.example`

- [ ] **Step 1: Create `apps/api/.python-version`**

```
3.12
```

- [ ] **Step 2: Create `apps/api/pyproject.toml`**

```toml
[project]
name = "agentops-api"
version = "0.1.0"
description = "AgentOps Workflow Platform — FastAPI backend"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic-settings>=2.6.0",
]

[tool.uv]
dev-dependencies = [
    "ruff>=0.8.0",
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.28.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Create `apps/api/.env.example`**

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agentops
OPENAI_API_KEY=
ENVIRONMENT=development
```

- [ ] **Step 4: Install dependencies**

```bash
cd apps/api
uv sync
```

Expected output: uv creates `.venv/` and installs all deps including dev deps. No errors.

- [ ] **Step 5: Commit**

```bash
cd ../..
git add apps/api/pyproject.toml apps/api/.python-version apps/api/.env.example
git commit -m "feat(api): add pyproject.toml, python version pin, and env example"
```

---

## Task 5: FastAPI app — health endpoint (TDD)

**Files:**
- Create: `apps/api/src/__init__.py`, `apps/api/src/main.py`, `apps/api/src/config.py`, `apps/api/tests/__init__.py`, `apps/api/tests/test_health.py`

- [ ] **Step 1: Create empty `__init__.py` files**

```bash
touch apps/api/src/__init__.py apps/api/tests/__init__.py
```

- [ ] **Step 2: Write the failing test**

Create `apps/api/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: Run the test — verify it fails**

```bash
cd apps/api
uv run pytest tests/test_health.py -v
```

Expected: `FAILED` / `ModuleNotFoundError: No module named 'src'` or similar. The test cannot pass yet because `src/main.py` doesn't exist.

- [ ] **Step 4: Create `apps/api/src/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    environment: str = "development"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/agentops"
    openai_api_key: str = ""


settings = Settings()
```

- [ ] **Step 5: Create `apps/api/src/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(
    title="AgentOps Workflow Platform API",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Run the test — verify it passes**

```bash
cd apps/api
uv run pytest tests/test_health.py -v
```

Expected output:
```
tests/test_health.py::test_health_returns_ok PASSED
1 passed in 0.XXs
```

- [ ] **Step 7: Run the linter**

```bash
cd apps/api
uv run ruff check src/ tests/
```

Expected: no output (no issues). If there are issues, fix them before committing.

- [ ] **Step 8: Verify the dev server starts**

```bash
cd apps/api
uv run uvicorn src.main:app --reload --port 8000
```

In a second terminal:
```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

Stop the server with Ctrl+C.

- [ ] **Step 9: Commit**

```bash
cd ../..
git add apps/api/src/ apps/api/tests/
git commit -m "feat(api): add FastAPI app with health endpoint and passing test"
```

---

## Task 6: Next.js frontend scaffold

**Files:**
- Create: `apps/web/` (entire directory via create-next-app)
- Modify: `apps/web/src/app/page.tsx`, `apps/web/src/app/layout.tsx`, `apps/web/package.json`

- [ ] **Step 1: Scaffold Next.js app**

Run from the repo root:

```bash
cd apps
pnpm create next-app@latest web \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --no-git
```

Expected: creates `apps/web/` with Next.js 15, TypeScript, Tailwind, ESLint, App Router, and `src/` directory. Accept all defaults if prompted.

- [ ] **Step 2: Set the package name to `@agentops/web`**

In `apps/web/package.json`, change the `"name"` field:

```json
{
  "name": "@agentops/web",
  ...
}
```

- [ ] **Step 3: Add `typecheck` script to `apps/web/package.json`**

In `apps/web/package.json`, add to `"scripts"`:

```json
"typecheck": "tsc --noEmit"
```

So the scripts section looks like:

```json
"scripts": {
  "dev": "next dev --turbopack",
  "build": "next build",
  "start": "next start",
  "lint": "next lint",
  "typecheck": "tsc --noEmit"
}
```

- [ ] **Step 4: Create `apps/web/.env.local.example`**

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 5: Replace `apps/web/src/app/page.tsx`**

```tsx
export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold tracking-tight">
        AgentOps Workflow Platform
      </h1>
      <p className="mt-4 text-lg text-gray-500">
        Enterprise multi-agent workflow platform — coming soon.
      </p>
    </main>
  );
}
```

- [ ] **Step 6: Install workspace deps from root**

```bash
cd ..
pnpm install
```

Expected: pnpm links all workspace packages and installs node_modules.

- [ ] **Step 7: Verify the dev server starts**

```bash
pnpm --filter @agentops/web dev
```

Expected: Next.js starts on `http://localhost:3000`. Open in browser, see the placeholder page. Stop with Ctrl+C.

- [ ] **Step 8: Run lint and typecheck**

```bash
pnpm --filter @agentops/web lint
pnpm --filter @agentops/web typecheck
```

Expected: both pass with no errors.

- [ ] **Step 9: Commit**

```bash
git add apps/web/
git commit -m "feat(web): scaffold Next.js 15 app with TypeScript, Tailwind, and placeholder page"
```

---

## Task 7: shadcn/ui init

**Files:**
- Modify: `apps/web/` (shadcn adds `components.json`, `src/lib/utils.ts`, updates `tailwind.config.ts` and `globals.css`)

- [ ] **Step 1: Initialize shadcn/ui**

Run from `apps/web/`:

```bash
cd apps/web
pnpm dlx shadcn@latest init -d
```

The `-d` flag uses defaults: New York style, Zinc color, CSS variables enabled. This creates:
- `components.json`
- `src/lib/utils.ts`
- Updates `tailwind.config.ts` and `src/app/globals.css`

If `-d` doesn't work with your shadcn version, run without it and answer the prompts:
- Style: **New York**
- Base color: **Zinc**
- CSS variables: **yes**

- [ ] **Step 2: Verify no build errors**

```bash
pnpm --filter @agentops/web typecheck
```

Expected: passes with no errors.

- [ ] **Step 3: Commit**

```bash
cd ../..
git add apps/web/components.json apps/web/src/lib/ apps/web/tailwind.config.ts apps/web/src/app/globals.css
git commit -m "feat(web): initialize shadcn/ui with New York style"
```

---

## Task 8: Shared TypeScript package stub

**Files:**
- Create: `packages/shared/package.json`, `packages/shared/tsconfig.json`, `packages/shared/src/index.ts`

- [ ] **Step 1: Create `packages/shared/package.json`**

```json
{
  "name": "@agentops/shared",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "scripts": {
    "typecheck": "tsc --noEmit"
  }
}
```

- [ ] **Step 2: Create `packages/shared/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create `packages/shared/src/index.ts`**

```typescript
// Shared types for AgentOps Workflow Platform.
// Workflow state types and API shapes will be added in later phases.

export type WorkflowStatus =
  | "created"
  | "running"
  | "analyst_running"
  | "reviewer_running"
  | "retrying"
  | "waiting_for_human"
  | "writer_running"
  | "completed"
  | "failed"
  | "cancelled";
```

- [ ] **Step 4: Install from root (picks up new package)**

```bash
pnpm install
```

- [ ] **Step 5: Typecheck the shared package**

```bash
pnpm --filter @agentops/shared typecheck
```

Expected: passes with no errors.

- [ ] **Step 6: Commit**

```bash
git add packages/
git commit -m "feat(shared): add shared TypeScript package stub with WorkflowStatus type"
```

---

## Task 9: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace `README.md` with the full content below**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: expand README with setup instructions and project structure"
```

---

## Task 10: Final verification

No new files. This task proves the entire scaffold is working.

- [ ] **Step 1: Run all Python checks**

```bash
cd apps/api
uv run ruff check src/ tests/
uv run pytest -v
```

Expected:
```
tests/test_health.py::test_health_returns_ok PASSED
1 passed in 0.XXs
```

- [ ] **Step 2: Run all JS checks**

```bash
cd ../..
pnpm --filter @agentops/web lint
pnpm --filter @agentops/web typecheck
pnpm --filter @agentops/shared typecheck
```

Expected: all three commands exit with code 0, no errors.

- [ ] **Step 3: Start API and verify health endpoint**

```bash
cd apps/api
uv run uvicorn src.main:app --port 8000
```

In a second terminal:
```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

Stop the server.

- [ ] **Step 4: Start frontend and verify page renders**

```bash
pnpm --filter @agentops/web dev
```

Open `http://localhost:3000`. Expected: page renders with "AgentOps Workflow Platform" heading.

Stop the server.

- [ ] **Step 5: Final commit (if any uncommitted changes)**

```bash
git status
```

If clean: Phase 2 is complete. If there are uncommitted changes, investigate and commit or discard appropriately.

---

## Success Criteria

- [ ] `GET http://localhost:8000/health` → `{"status": "ok"}`
- [ ] `http://localhost:3000` renders placeholder page
- [ ] `uv run pytest` → 1 passed
- [ ] `uv run ruff check src/ tests/` → clean
- [ ] `pnpm --filter @agentops/web lint` → clean
- [ ] `pnpm --filter @agentops/web typecheck` → clean
- [ ] `pnpm --filter @agentops/shared typecheck` → clean
- [ ] All files committed, working tree clean
