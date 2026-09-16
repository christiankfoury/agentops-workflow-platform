from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RawRouterOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_type: Literal["sales_report", "customer_feedback", "incident_log"]
    confidence: float = Field(ge=0, le=1)
    reasoning_summary: str = Field(min_length=1)


class RouterOutput(RawRouterOutput):
    recommended_action: Literal["auto_select", "confirm", "manual_required"]


