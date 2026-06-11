from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.database import check_db
from src.routers import (
    evaluation_results,
    human_approvals,
    prompt_versions,
    uploaded_inputs,
    workflow_runs,
)

app = FastAPI(
    title="AgentOps Workflow Platform API",
    version="0.1.0",
)

app.include_router(workflow_runs.router, prefix="/workflow-runs", tags=["workflow-runs"])
app.include_router(human_approvals.router, prefix="/human-approvals", tags=["human-approvals"])
app.include_router(prompt_versions.router, prefix="/prompt-versions", tags=["prompt-versions"])
app.include_router(uploaded_inputs.router, prefix="/uploaded-inputs", tags=["uploaded-inputs"])
app.include_router(
    evaluation_results.router,
    prefix="/evaluation-results",
    tags=["evaluation-results"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> JSONResponse:
    if check_db():
        return JSONResponse({"status": "ready"})
    return JSONResponse({"status": "unavailable"}, status_code=503)
