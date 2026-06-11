from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Sentiment = Literal["positive", "neutral", "negative", "mixed"]
FeedbackCategory = Literal[
    "pricing",
    "bugs",
    "feature_requests",
    "performance",
    "usability",
    "support_experience",
    "other",
]


class FeedbackExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    source: str | None = None


class FeedbackTheme(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: FeedbackCategory
    count: int = Field(ge=0)
    sentiment: Sentiment
    examples: list[FeedbackExample]


class SentimentPattern(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentiment: Sentiment
    count: int = Field(ge=0)
    summary: str = Field(min_length=1)


class FeatureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: str = Field(min_length=1)
    count: int = Field(ge=0)
    supporting_examples: list[FeedbackExample]


class BugReportPattern(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue: str = Field(min_length=1)
    count: int = Field(ge=0)
    severity: Literal["low", "medium", "high"]
    supporting_examples: list[FeedbackExample]


class CustomerFeedbackClassificationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    themes: list[FeedbackTheme]
    sentiment_patterns: list[SentimentPattern]
    feature_requests: list[FeatureRequest]
    bug_reports: list[BugReportPattern]


class ProductRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    supporting_examples: list[FeedbackExample]


class ProductInsightOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_insights: list[str]
    customer_pain_points: list[str]
    feature_requests: list[FeatureRequest]
    risks: list[str]
    recommendations: list[ProductRecommendation]
    supporting_examples: list[FeedbackExample]
