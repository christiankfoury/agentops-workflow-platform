from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReviewIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    problem: str
    severity: Literal["low", "medium", "high"]


class SalesReviewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    quality_score: float = Field(ge=0, le=1)
    issues: list[ReviewIssue]
    retry_recommended: bool
