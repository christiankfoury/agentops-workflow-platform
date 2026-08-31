# Deployment

This project is designed to run locally with Docker Compose and can be deployed
as separate web, API, and PostgreSQL services. The included Compose file and
Dockerfiles are development tooling, not a production deployment template.

## Local Docker

```bash
cp .env.example .env
make up
```

Services:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- Database: PostgreSQL on `localhost:5432`

Useful commands:

```bash
make logs
make ps
make down
```

## Local Non-Docker

API:

```bash
cd apps/api
uv sync
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

Web:

```bash
pnpm install
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 pnpm --dir apps/web dev
```

## Required Environment

Backend:

- Database URL for PostgreSQL.
- OpenAI API key for live LLM-backed runs.

Frontend:

- `NEXT_PUBLIC_API_URL` for browser-visible API calls.
- `API_INTERNAL_URL` when the web server should call an internal Docker/service
  hostname instead of the public API URL.

## Database Setup

The app uses SQLAlchemy models and Alembic migrations. A deployment should:

1. Provision PostgreSQL.
2. Apply migrations.
3. Seed prompt versions.
4. Optionally seed evaluation/demo data.

Seed commands:

```bash
cd apps/api
uv run python -m src.seed_prompts
uv run python -m src.seed_evaluation_cases
uv run python -m src.seed_demo_dataset
```

## Deployment Shape

Recommended service split:

```mermaid
flowchart LR
    CDN["Web hosting"]
    API["API service"]
    DB["Managed PostgreSQL"]
    LLM["OpenAI API"]

    CDN --> API
    API --> DB
    API --> LLM
```

Suitable portfolio deployment targets:

- Render
- Railway
- Fly.io
- Azure App Service / Container Apps

## Public Deployment Requirements

Before exposing the application to the internet:

1. Keep PostgreSQL on a private network and use a managed secret for its password.
2. Set `ENVIRONMENT=production`.
3. Set `API_AUTH_ENABLED=true` and provide a strong `API_KEY` through the hosting
   platform's secret manager.
4. Set `API_RATE_LIMIT_PER_MINUTE` to a positive value appropriate for the service.
5. Terminate TLS at the hosting platform or reverse proxy.
6. Restrict allowed network origins and do not expose development or database ports.
7. Run migrations as a release step rather than using a reload-enabled development
   process.
8. Decide whether demo seeding endpoints should remain enabled for the deployment.

The current shared API-key roles are sufficient for a controlled portfolio demo;
they are not a replacement for user identity, sessions, or tenant-aware authorization.

## Release Checklist

- API health endpoint returns `200`.
- Web app can reach API through configured URL.
- Migrations are applied.
- Prompt versions are seeded.
- Demo mode can seed the demo dataset.
- `/evaluation` and `/workflow-comparison` show baseline and multi-agent data.
- Secrets are configured outside source control.
- API authentication and rate limiting are enabled.
- PostgreSQL is not exposed to the public internet.
- TLS and hosting-level network controls are configured.
- Full validation passes before deployment.

## Known Limits

- Full user authentication and tenant-aware authorization are not implemented; the
  API currently supports shared-key viewer, operator, and admin roles.
- Background jobs are not yet required for demo mode.
- Live LLM runs require valid provider credentials and quota.
- The deterministic demo path is intended for portfolio walkthroughs and does not
  replace live evaluation runs.
