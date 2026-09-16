"""Server-owned output validators reused by published business templates."""

from src.schemas.customer_feedback import (
    CustomerFeedbackClassificationOutput,
    CustomerFeedbackReviewOutput,
    ProductInsightOutput,
)


def final_report(value):
    text = value["final_output"].strip()
    if not text:
        raise ValueError("Final report must contain non-whitespace text")
    return {"final_output": text}


FEEDBACK_MODELS = {
    "feedback.classification.v1": CustomerFeedbackClassificationOutput,
    "feedback.insight.v1": ProductInsightOutput,
    "feedback.review.v1": CustomerFeedbackReviewOutput,
}


def model_validator(model):
    def validate(value):
        return model.model_validate(value, strict=True).model_dump(mode="json")

    return validate
