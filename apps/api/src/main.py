from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from src.database import check_db
from src.routers import (
    agent_performance,
    agent_settings,
    demo,
    evaluation_results,
    human_approvals,
    prompt_versions,
    uploaded_inputs,
    workflow_runs,
)
from src.security import enforce_rate_limit, require_api_key

app = FastAPI(
    title="AgentOps Workflow Platform API",
    version="0.1.0",
)

authenticated_router_dependencies = [Depends(require_api_key)]


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
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> JSONResponse:
    if check_db():
        return JSONResponse({"status": "ready"})
    return JSONResponse({"status": "unavailable"}, status_code=503)
