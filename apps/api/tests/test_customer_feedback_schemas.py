import pytest
from pydantic import ValidationError

from src.schemas.customer_feedback import (
    CustomerFeedbackClassificationOutput,
    ProductInsightOutput,
)


def test_customer_feedback_classification_output_accepts_expected_shape():
    output = CustomerFeedbackClassificationOutput.model_validate(
        {
            "themes": [
                {
                    "name": "performance",
                    "count": 14,
                    "sentiment": "negative",
                    "examples": [{"text": "Mobile app is slow.", "source": "review"}],
                }
            ],
            "sentiment_patterns": [
                {
                    "sentiment": "negative",
                    "count": 18,
                    "summary": "Mobile performance complaints dominate.",
                }
            ],
            "feature_requests": [
                {
                    "request": "Bulk export",
                    "count": 6,
                    "supporting_examples": [{"text": "Need CSV export."}],
                }
            ],
            "bug_reports": [
                {
                    "issue": "Dashboard fails to load",
                    "count": 4,
                    "severity": "high",
                    "supporting_examples": [{"text": "Dashboard times out."}],
                }
            ],
        }
    )

    assert output.themes[0].name == "performance"
    assert output.feature_requests[0].request == "Bulk export"
    assert output.bug_reports[0].severity == "high"


def test_customer_feedback_classification_output_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        CustomerFeedbackClassificationOutput.model_validate(
            {
                "themes": [],
                "sentiment_patterns": [],
                "feature_requests": [],
                "bug_reports": [],
                "unsupported": True,
            }
        )


def test_product_insight_output_accepts_recommendations_with_supporting_examples():
    output = ProductInsightOutput.model_validate(
        {
            "top_insights": ["Mobile performance is the largest complaint."],
            "customer_pain_points": ["Slow mobile load times"],
            "feature_requests": [
                {
                    "request": "Bulk export",
                    "count": 6,
                    "supporting_examples": [{"text": "Need CSV export."}],
                }
            ],
            "risks": ["Mobile churn risk"],
            "recommendations": [
                {
                    "recommendation": "Prioritize mobile performance work",
                    "rationale": "Performance complaints are frequent and negative.",
                    "supporting_examples": [{"text": "Mobile app is slow."}],
                }
            ],
            "supporting_examples": [{"text": "Mobile app is slow."}],
        }
    )

    assert output.top_insights == ["Mobile performance is the largest complaint."]
    assert output.recommendations[0].recommendation == "Prioritize mobile performance work"
