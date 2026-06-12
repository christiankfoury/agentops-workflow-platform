from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.workflow_run import WorkflowType
from src.schemas.demo import DemoDatasetSummaryRead
from src.security import ROLE_ADMIN, require_role
from src.services.demo_dataset import DemoDatasetSummary, seed_demo_dataset

router = APIRouter(dependencies=[Depends(require_role(ROLE_ADMIN))])


@router.post("/sales-report", response_model=DemoDatasetSummaryRead)
def seed_sales_demo(db: Session = Depends(get_db)) -> DemoDatasetSummary:
    return seed_demo_dataset(db, {WorkflowType.sales_report})


@router.post("/customer-feedback", response_model=DemoDatasetSummaryRead)
def seed_customer_feedback_demo(db: Session = Depends(get_db)) -> DemoDatasetSummary:
    return seed_demo_dataset(db, {WorkflowType.customer_feedback})


@router.post("/incident-log", response_model=DemoDatasetSummaryRead)
def seed_incident_demo(db: Session = Depends(get_db)) -> DemoDatasetSummary:
    return seed_demo_dataset(db, {WorkflowType.incident_log})


@router.post("/full-evaluation", response_model=DemoDatasetSummaryRead)
def seed_full_evaluation_demo(db: Session = Depends(get_db)) -> DemoDatasetSummary:
    return seed_demo_dataset(db)
