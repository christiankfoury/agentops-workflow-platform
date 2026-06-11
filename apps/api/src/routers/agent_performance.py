from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.agent_step import AgentStep
from src.models.workflow_event import WorkflowEvent
from src.schemas.agent_performance import AgentPerformanceSummaryRead
from src.services.agent_performance import summarize_agent_performance

router = APIRouter()


@router.get("", response_model=list[AgentPerformanceSummaryRead])
def get_agent_performance_summary(
    db: Session = Depends(get_db),
) -> list[AgentPerformanceSummaryRead]:
    steps = db.query(AgentStep).all()
    events = db.query(WorkflowEvent).all()
    return summarize_agent_performance(steps, events)
