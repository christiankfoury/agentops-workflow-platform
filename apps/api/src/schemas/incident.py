from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time: str = Field(min_length=1)
    event: str = Field(min_length=1)
    source_evidence: str = Field(min_length=1)


class IncidentTimelineOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timeline: list[TimelineEvent]
    ambiguous_events: list[str]


class IncidentImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    severity: Literal["low", "medium", "high", "unknown"]
    affected_systems: list[str]


class IncidentClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=1)
    support: str = Field(min_length=1)


class IncidentFollowUpAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1)
    owner: str | None = None
    priority: Literal["low", "medium", "high"]


class IncidentRootCauseOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    impact: list[IncidentImpact]
    suspected_root_cause: str = Field(min_length=1)
    confirmed_facts: list[IncidentClaim]
    inferred_claims: list[IncidentClaim]
    follow_up_actions: list[IncidentFollowUpAction]
