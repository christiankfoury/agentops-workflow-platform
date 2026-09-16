from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.config import settings
from src.database import check_db
from src.routers import (
    access,
    agent_performance,
    agent_settings,
    demo,
    evaluation_results,
    execution_approvals,
    human_approvals,
    identity,
    prompt_versions,
    tools,
    uploaded_inputs,
    workflow_definitions,
    workflow_executions,
    workflow_runs,
)
from src.security import enforce_rate_limit, require_access
from src.services.tenancy import TenantAccessError
from src.services.workflow_transactions import StaleWorkflowError


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.environment not in {"development", "test"}:
        if not settings.identity_enabled or not settings.oidc_audience or any(
            not value or urlparse(value).scheme != "https" or not urlparse(value).hostname
            for value in [settings.oidc_issuer, settings.oidc_jwks_url]
        ):
            raise RuntimeError(
                "Public deployment requires configured verified identity and HTTPS OIDC endpoints"
            )
    yield


app = FastAPI(
    title="AgentOps Workflow Platform API",
    version="0.1.0",
    lifespan=lifespan,
)

authenticated_router_dependencies = [Depends(require_access)]
app.include_router(tools.router, prefix="/tools", tags=["tools"],
                   dependencies=authenticated_router_dependencies)
app.include_router(execution_approvals.router, prefix="/execution-approvals",
                   tags=["execution-approvals"], dependencies=authenticated_router_dependencies)
app.include_router(workflow_executions.router, prefix="/workflow-executions",
                   tags=["workflow-executions"], dependencies=authenticated_router_dependencies)
app.include_router(workflow_definitions.router, prefix="/workflow-definitions",
                   tags=["workflow-definitions"], dependencies=authenticated_router_dependencies)
app.include_router(identity.router, prefix="/identity", tags=["identity"])
app.include_router(access.router, prefix="/access", tags=["access"],
                   dependencies=authenticated_router_dependencies)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/tools"):
        return JSONResponse({"detail": [
            {key: error[key] for key in ("type", "loc", "msg")}
            for error in exc.errors()
        ]}, status_code=422)
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(StaleWorkflowError)
async def stale_workflow(_request: Request, exc: StaleWorkflowError):
    return JSONResponse({"detail": str(exc)}, status_code=409)


@app.exception_handler(TenantAccessError)
async def tenant_access_error(_request: Request, exc: TenantAccessError):
    return JSONResponse({"detail": str(exc)}, status_code=403)


@app.middleware("http")
async def rate_limit_requests(request: Request, call_next):
    try:
        enforce_rate_limit(request)
    except HTTPException as e:
        return JSONResponse({"detail": e.detail}, status_code=e.status_code)
    return await call_next(request)


app.include_router(
    workflow_runs.router,
    prefix="/workflow-runs",
    tags=["workflow-runs"],
    dependencies=authenticated_router_dependencies,
)
app.include_router(
    human_approvals.router,
    prefix="/human-approvals",
    tags=["human-approvals"],
    dependencies=authenticated_router_dependencies,
)
app.include_router(
    prompt_versions.router,
    prefix="/prompt-versions",
    tags=["prompt-versions"],
    dependencies=authenticated_router_dependencies,
)
app.include_router(
    uploaded_inputs.router,
    prefix="/uploaded-inputs",
    tags=["uploaded-inputs"],
    dependencies=authenticated_router_dependencies,
)
app.include_router(
    agent_settings.router,
    prefix="/agent-settings",
    tags=["agent-settings"],
    dependencies=authenticated_router_dependencies,
)
app.include_router(
    demo.router,
    prefix="/demo",
    tags=["demo"],
    dependencies=authenticated_router_dependencies,
)
app.include_router(
    agent_performance.router,
    prefix="/agent-performance",
    tags=["agent-performance"],
    dependencies=authenticated_router_dependencies,
)
app.include_router(
    evaluation_results.router,
    prefix="/evaluation-results",
    tags=["evaluation-results"],
    dependencies=authenticated_router_dependencies,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> JSONResponse:
    if check_db():
        return JSONResponse({"status": "ready"})
    return JSONResponse({"status": "unavailable"}, status_code=503)
