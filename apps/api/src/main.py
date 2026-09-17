from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.config import settings
from src.database import check_db
from src.production import validate_configuration
from src.routers import (
    access,
    agent_performance,
    agent_settings,
    demo,
    evaluation_results,
    execution_approvals,
    execution_traces,
    human_approvals,
    identity,
    operations,
    prompt_versions,
    schedules,
    tools,
    uploaded_inputs,
    webhooks,
    workflow_definitions,
    workflow_executions,
    workflow_runs,
)
from src.security import enforce_rate_limit, require_access
from src.services.tenancy import TenantAccessError
from src.services.workflow_transactions import StaleWorkflowError


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_configuration()
    yield


app = FastAPI(
    title="AgentOps Workflow Platform API",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

authenticated_router_dependencies = [Depends(require_access)]
app.include_router(operations.router, prefix="/operations", tags=["operations"],
                   dependencies=authenticated_router_dependencies)
app.include_router(execution_traces.router, prefix="/execution-traces", tags=["execution-traces"],
                   dependencies=authenticated_router_dependencies)
app.include_router(schedules.router, prefix="/workflow-schedules", tags=["workflow-schedules"],
                   dependencies=authenticated_router_dependencies)
app.include_router(
    webhooks.router,
    prefix="/webhook-triggers",
    tags=["webhook-triggers"],
    dependencies=authenticated_router_dependencies,
)
app.include_router(webhooks.delivery_router, prefix="/webhooks", tags=["webhooks"])
app.include_router(
    tools.router, prefix="/tools", tags=["tools"], dependencies=authenticated_router_dependencies
)
app.include_router(
    execution_approvals.router,
    prefix="/execution-approvals",
    tags=["execution-approvals"],
    dependencies=authenticated_router_dependencies,
)
app.include_router(
    workflow_executions.router,
    prefix="/workflow-executions",
    tags=["workflow-executions"],
    dependencies=authenticated_router_dependencies,
)
app.include_router(
    workflow_definitions.router,
    prefix="/workflow-definitions",
    tags=["workflow-definitions"],
    dependencies=authenticated_router_dependencies,
)
app.include_router(identity.router, prefix="/identity", tags=["identity"])
app.include_router(
    access.router, prefix="/access", tags=["access"], dependencies=authenticated_router_dependencies
)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    if request.url.path.startswith(("/tools", "/webhook-triggers", "/workflow-schedules")):
        return JSONResponse(
            {
                "detail": [
                    {key: error[key] for key in ("type", "loc", "msg")} for error in exc.errors()
                ]
            },
            status_code=422,
        )
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
