from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.customer_feedback import ProductInsightOutput
from src.schemas.incident import IncidentRootCauseOutput, IncidentTimelineOutput
from src.services.sales_analyst import SalesAnalysisOutput


class WriterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_run_id: str = Field(min_length=1)
    input_id: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
    reviewer_step_id: str | None = None
    human_approval_id: str | None = None
    human_feedback: str | None = None


class SalesWriterInput(WriterInput):
    analyst_step_id: str = Field(min_length=1)
    analysis: SalesAnalysisOutput
    analysis_source: Literal["analyst", "human_edited"]


class CustomerFeedbackWriterInput(WriterInput):
    insight_step_id: str = Field(min_length=1)
    insights: ProductInsightOutput
    insights_source: Literal["insight", "human_edited"]


class IncidentWriterInput(WriterInput):
    timeline_step_id: str = Field(min_length=1)
    root_cause_step_id: str = Field(min_length=1)
    timeline: IncidentTimelineOutput
    root_cause: IncidentRootCauseOutput
    root_cause_source: Literal["root_cause", "human_edited"]
