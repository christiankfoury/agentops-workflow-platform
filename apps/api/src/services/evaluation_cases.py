from sqlalchemy.orm import Session

from src.models.evaluation_case import EvaluationCase
from src.models.workflow_run import WorkflowType

DEFAULT_SALES_EVALUATION_CASES = [
    {
        "title": "Q1 regional growth and churn",
        "input_text": (
            "Q1 Sales Report\n"
            "Revenue increased 12% from $4.2M to $4.7M. North America grew 18% "
            "and was the strongest region. EMEA declined 4%. Enterprise churn "
            "increased from 5% to 7%. Analytics Suite was the top product."
        ),
        "expected_facts_json": [
            "Revenue increased 12% from $4.2M to $4.7M",
            "North America grew 18% and was the strongest region",
            "EMEA declined 4%",
            "Enterprise churn increased from 5% to 7%",
            "Analytics Suite was the top product",
        ],
        "expected_risks_json": ["Enterprise churn increased", "EMEA declined"],
        "expected_recommendations_json": [
            "Prioritize enterprise retention",
            "Investigate EMEA performance decline",
        ],
        "expected_output_notes": "Executive summary should not say churn doubled.",
    },
    {
        "title": "Pipeline softness with SMB expansion",
        "input_text": (
            "Q2 Sales Report\n"
            "Total revenue was flat at $5.1M. SMB revenue increased 9%. Enterprise "
            "pipeline coverage fell from 3.2x to 2.4x. The West region missed target "
            "by $300K. Expansion revenue from existing customers increased 14%."
        ),
        "expected_facts_json": [
            "Total revenue was flat at $5.1M",
            "SMB revenue increased 9%",
            "Enterprise pipeline coverage fell from 3.2x to 2.4x",
            "West region missed target by $300K",
            "Expansion revenue increased 14%",
        ],
        "expected_risks_json": [
            "Enterprise pipeline coverage fell",
            "West region missed target",
        ],
        "expected_recommendations_json": [
            "Rebuild enterprise pipeline",
            "Review West region execution",
        ],
        "expected_output_notes": "Summary should separate flat revenue from segment growth.",
    },
    {
        "title": "New product momentum and support load",
        "input_text": (
            "Monthly Sales Report\n"
            "Revenue grew 7% month over month. The new Automation add-on generated "
            "$420K in first-month bookings. Support-related churn risk was noted in "
            "mid-market accounts. APAC grew 11%, while Latin America was unchanged."
        ),
        "expected_facts_json": [
            "Revenue grew 7% month over month",
            "Automation add-on generated $420K in first-month bookings",
            "Support-related churn risk was noted in mid-market accounts",
            "APAC grew 11%",
            "Latin America was unchanged",
        ],
        "expected_risks_json": ["Support-related churn risk in mid-market accounts"],
        "expected_recommendations_json": [
            "Invest in Automation add-on momentum",
            "Address mid-market support issues",
        ],
        "expected_output_notes": "Summary should not invent Latin America decline.",
    },
    {
        "title": "Discounting pressure in enterprise deals",
        "input_text": (
            "Enterprise Sales Update\n"
            "Bookings increased 10%, but average discounting rose from 12% to 19%. "
            "Three large healthcare deals slipped into next quarter. North America "
            "closed 104% of target. Gross retention remained stable at 91%."
        ),
        "expected_facts_json": [
            "Bookings increased 10%",
            "Average discounting rose from 12% to 19%",
            "Three large healthcare deals slipped into next quarter",
            "North America closed 104% of target",
            "Gross retention remained stable at 91%",
        ],
        "expected_risks_json": [
            "Average discounting increased",
            "Healthcare deals slipped into next quarter",
        ],
        "expected_recommendations_json": [
            "Review discount approval discipline",
            "Recover slipped healthcare deals",
        ],
        "expected_output_notes": "Summary should mention margin pressure as a risk.",
    },
    {
        "title": "Renewal strength with product gap",
        "input_text": (
            "Renewals Sales Report\n"
            "Renewal bookings reached $2.3M, 15% above plan. Churn decreased from "
            "6% to 4%. Customers in manufacturing cited missing reporting exports as "
            "a blocker for expansion. The Central region delivered 98% of target."
        ),
        "expected_facts_json": [
            "Renewal bookings reached $2.3M, 15% above plan",
            "Churn decreased from 6% to 4%",
            "Manufacturing customers cited missing reporting exports as expansion blocker",
            "Central region delivered 98% of target",
        ],
        "expected_risks_json": [
            "Missing reporting exports blocked manufacturing expansion",
        ],
        "expected_recommendations_json": [
            "Prioritize reporting export improvements",
            "Use renewal motion as expansion lever",
        ],
        "expected_output_notes": "Summary should not describe churn as increasing.",
    },
]


def seed_default_evaluation_cases(db: Session) -> list[EvaluationCase]:
    seeded: list[EvaluationCase] = []
    for default in DEFAULT_SALES_EVALUATION_CASES:
        case = (
            db.query(EvaluationCase)
            .filter(
                EvaluationCase.workflow_type == WorkflowType.sales_report,
                EvaluationCase.title == default["title"],
            )
            .first()
        )
        if case is None:
            case = EvaluationCase(
                workflow_type=WorkflowType.sales_report,
                title=default["title"],
                input_text=default["input_text"],
                expected_facts_json=default["expected_facts_json"],
                expected_risks_json=default["expected_risks_json"],
                expected_recommendations_json=default["expected_recommendations_json"],
                expected_output_notes=default["expected_output_notes"],
            )
            db.add(case)
        else:
            case.input_text = default["input_text"]
            case.expected_facts_json = default["expected_facts_json"]
            case.expected_risks_json = default["expected_risks_json"]
            case.expected_recommendations_json = default["expected_recommendations_json"]
            case.expected_output_notes = default["expected_output_notes"]
        seeded.append(case)

    db.commit()
    for case in seeded:
        db.refresh(case)
    return seeded
