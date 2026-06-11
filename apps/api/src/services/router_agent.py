from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion
from src.models.workflow_run import WorkflowType
from src.services.llm_client import StructuredResponse

HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.60

ROUTER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "workflow_type": {
            "type": "string",
            "enum": [
                WorkflowType.sales_report.value,
                WorkflowType.customer_feedback.value,
                WorkflowType.incident_log.value,
            ],
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning_summary": {"type": "string"},
    },
    "required": ["workflow_type", "confidence", "reasoning_summary"],
    "additionalProperties": False,
}


class RouterRunError(Exception):
    pass


class RawRouterOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_type: Literal["sales_report", "customer_feedback", "incident_log"]
    confidence: float = Field(ge=0, le=1)
    reasoning_summary: str = Field(min_length=1)


class RouterOutput(RawRouterOutput):
    recommended_action: Literal["auto_select", "confirm", "manual_required"]


class LLMClientLike(Protocol):
    def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: dict[str, Any],
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> StructuredResponse:
        pass


def detect_workflow_type(
    db: Session,
    *,
    title: str,
    raw_text: str,
    notes: str | None,
    llm_client: LLMClientLike,
) -> RouterOutput:
    prompt = _get_active_router_prompt(db)
    try:
        response = llm_client.generate_structured(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Inspect this business input and choose the best workflow type. "
                        "Use sales_report for revenue, pipeline, churn, sales, or "
                        "commercial performance updates. Use customer_feedback for "
                        "reviews, surveys, tickets, feature requests, bugs, sentiment, "
                        "or product feedback. Use incident_log for timestamped "
                        "operational events, outages, alerts, mitigations, impact, "
                        "recovery, or root-cause notes.\n\n"
                        f"Title: {title}\n\n"
                        f"Notes: {notes or 'None'}\n\n"
                        f"Input:\n{raw_text}"
                    ),
                }
            ],
            system=prompt.template,
            schema=ROUTER_SCHEMA,
            max_tokens=600,
        )
        raw_output = RawRouterOutput.model_validate(response.data)
        return RouterOutput(
            **raw_output.model_dump(),
            recommended_action=_recommended_action(raw_output.confidence),
        )
    except ValidationError as e:
        raise RouterRunError("Router returned invalid workflow detection output") from e
    except Exception as e:
        raise RouterRunError(str(e)) from e


def _get_active_router_prompt(db: Session) -> PromptVersion:
    prompt = (
        db.query(PromptVersion)
        .filter(
            PromptVersion.agent_type == AgentType.router,
            PromptVersion.is_active == True,  # noqa: E712
        )
        .order_by(PromptVersion.version.desc(), PromptVersion.created_at.desc())
        .first()
    )
    if prompt is None:
        raise RouterRunError("Active Router prompt not found")
    return prompt


def _recommended_action(confidence: float) -> Literal["auto_select", "confirm", "manual_required"]:
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        return "auto_select"
    if confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "confirm"
    return "manual_required"
