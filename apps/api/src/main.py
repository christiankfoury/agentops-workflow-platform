from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.database import check_db
from src.routers import workflow_runs

app = FastAPI(
    title="AgentOps Workflow Platform API",
    version="0.1.0",
)

app.include_router(workflow_runs.router, prefix="/workflow-runs", tags=["workflow-runs"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> JSONResponse:
    if check_db():
        return JSONResponse({"status": "ready"})
    return JSONResponse({"status": "unavailable"}, status_code=503)
