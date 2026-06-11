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

DEFAULT_CUSTOMER_FEEDBACK_EVALUATION_CASES = [
    {
        "title": "Mobile performance and export requests",
        "input_text": (
            "Review 1: The mobile app is slow during checkout. Review 2: Checkout "
            "freezes on older Android phones. Ticket 9: Please add bulk export for "
            "reports. NPS: Support was helpful but performance is frustrating."
        ),
        "expected_facts_json": [
            "Mobile app is slow during checkout",
            "Checkout freezes on older Android phones",
            "Customers requested bulk export for reports",
            "Support was helpful",
        ],
        "expected_risks_json": ["Mobile checkout performance may hurt conversion"],
        "expected_recommendations_json": [
            "Prioritize mobile checkout performance",
            "Add bulk export for reports",
        ],
        "expected_themes_json": ["performance", "feature_requests", "support_experience"],
        "expected_output_notes": "Report should not claim support sentiment is negative.",
    },
    {
        "title": "Pricing concerns from small businesses",
        "input_text": (
            "Survey: Small business users said the new plan is too expensive. Review: "
            "Great product, but pricing jumped before we saw value. Ticket: Annual "
            "discount options are confusing. Review: Enterprise features are not needed "
            "for our five-person team."
        ),
        "expected_facts_json": [
            "Small business users said the new plan is too expensive",
            "Pricing jumped before value was clear",
            "Annual discount options are confusing",
            "Enterprise features are not needed for small teams",
        ],
        "expected_risks_json": ["Pricing friction among small business customers"],
        "expected_recommendations_json": [
            "Test clearer SMB pricing",
            "Simplify annual discount messaging",
        ],
        "expected_themes_json": ["pricing", "usability"],
        "expected_output_notes": "Report should not generalize pricing complaints to enterprise.",
    },
    {
        "title": "Bug reports after dashboard release",
        "input_text": (
            "Ticket 101: Dashboard filters reset after refresh. Ticket 102: Saved views "
            "sometimes disappear. Review: The new dashboard is useful when it loads. "
            "Ticket 103: Exported CSV files have duplicated rows."
        ),
        "expected_facts_json": [
            "Dashboard filters reset after refresh",
            "Saved views sometimes disappear",
            "New dashboard is useful when it loads",
            "Exported CSV files have duplicated rows",
        ],
        "expected_risks_json": ["Dashboard reliability issues may reduce trust"],
        "expected_recommendations_json": [
            "Fix dashboard filter persistence",
            "Investigate CSV duplicate rows",
        ],
        "expected_themes_json": ["bugs", "usability"],
        "expected_output_notes": "Report should separate usefulness from reliability bugs.",
    },
    {
        "title": "Support delays and onboarding confusion",
        "input_text": (
            "NPS comment: It took three days to get a support response. Review: Setup "
            "docs skipped the SSO configuration step. Ticket: Onboarding checklist is "
            "unclear for admins. Review: Once configured, the product works well."
        ),
        "expected_facts_json": [
            "Support response took three days",
            "Setup docs skipped SSO configuration",
            "Onboarding checklist is unclear for admins",
            "Product works well once configured",
        ],
        "expected_risks_json": ["Slow support and unclear onboarding may delay activation"],
        "expected_recommendations_json": [
            "Improve support response times",
            "Update SSO setup documentation",
            "Clarify admin onboarding checklist",
        ],
        "expected_themes_json": ["support_experience", "usability"],
        "expected_output_notes": "Report should not say the product fails after setup.",
    },
    {
        "title": "Feature requests for integrations",
        "input_text": (
            "Ticket: We need Salesforce sync for account owners. Review: Slack alerts "
            "would help our team act faster. Survey: HubSpot integration is required "
            "before rollout. Review: Current CSV import works but takes too long."
        ),
        "expected_facts_json": [
            "Customers need Salesforce sync for account owners",
            "Slack alerts would help teams act faster",
            "HubSpot integration is required before rollout",
            "CSV import works but takes too long",
        ],
        "expected_risks_json": ["Missing integrations may block rollout"],
        "expected_recommendations_json": [
            "Prioritize CRM integrations",
            "Evaluate Slack alerts",
            "Reduce CSV import friction",
        ],
        "expected_themes_json": ["feature_requests", "usability"],
        "expected_output_notes": "Report should not claim integrations already exist.",
    },
    {
        "title": "Positive sentiment with reporting gaps",
        "input_text": (
            "Review: The automation saves our team hours every week. NPS: Reporting is "
            "too limited for executives. Ticket: Need scheduled PDF reports. Review: "
            "Support answered our question quickly."
        ),
        "expected_facts_json": [
            "Automation saves hours every week",
            "Reporting is too limited for executives",
            "Customers need scheduled PDF reports",
            "Support answered quickly",
        ],
        "expected_risks_json": ["Reporting gaps may limit executive adoption"],
        "expected_recommendations_json": [
            "Add scheduled PDF reports",
            "Improve executive reporting",
        ],
        "expected_themes_json": ["feature_requests", "support_experience"],
        "expected_output_notes": "Report should preserve positive automation sentiment.",
    },
    {
        "title": "Usability friction in permissions",
        "input_text": (
            "Ticket: Role permissions are hard to understand. Review: We accidentally "
            "gave contractors admin access. Survey: Permission templates would help. "
            "Ticket: Audit log labels are confusing."
        ),
        "expected_facts_json": [
            "Role permissions are hard to understand",
            "Contractors were accidentally given admin access",
            "Permission templates were requested",
            "Audit log labels are confusing",
        ],
        "expected_risks_json": ["Permission confusion may create access control risk"],
        "expected_recommendations_json": [
            "Improve permission UX",
            "Add permission templates",
            "Clarify audit log labels",
        ],
        "expected_themes_json": ["usability", "feature_requests"],
        "expected_output_notes": "Report should treat contractor admin access as a risk.",
    },
    {
        "title": "Performance complaints in search",
        "input_text": (
            "Review: Search takes more than ten seconds for large accounts. Ticket: "
            "Results are stale after imports. NPS: Search relevance is good when it "
            "finishes. Survey: Faster filtering is our top request."
        ),
        "expected_facts_json": [
            "Search takes more than ten seconds for large accounts",
            "Search results are stale after imports",
            "Search relevance is good when it finishes",
            "Faster filtering is the top request",
        ],
        "expected_risks_json": ["Slow search may reduce usage in large accounts"],
        "expected_recommendations_json": [
            "Improve search latency",
            "Refresh search results after imports",
            "Speed up filtering",
        ],
        "expected_themes_json": ["performance", "feature_requests"],
        "expected_output_notes": "Report should not ignore the positive relevance note.",
    },
    {
        "title": "Mixed support and billing feedback",
        "input_text": (
            "Review: Billing invoices are hard to reconcile. Ticket: Support resolved "
            "our billing issue in one call. Survey: Need separate invoices by workspace. "
            "Review: Renewal reminders arrived too late."
        ),
        "expected_facts_json": [
            "Billing invoices are hard to reconcile",
            "Support resolved a billing issue in one call",
            "Customers need separate invoices by workspace",
            "Renewal reminders arrived too late",
        ],
        "expected_risks_json": ["Billing confusion may create renewal friction"],
        "expected_recommendations_json": [
            "Improve invoice clarity",
            "Add workspace-level invoices",
            "Send earlier renewal reminders",
        ],
        "expected_themes_json": ["pricing", "support_experience", "feature_requests"],
        "expected_output_notes": "Report should distinguish billing UX from support quality.",
    },
    {
        "title": "Accessibility and usability requests",
        "input_text": (
            "Review: Keyboard navigation skips the settings menu. Ticket: Low contrast "
            "text is hard to read. Survey: Screen reader labels are missing on charts. "
            "Review: The new layout is cleaner overall."
        ),
        "expected_facts_json": [
            "Keyboard navigation skips the settings menu",
            "Low contrast text is hard to read",
            "Screen reader labels are missing on charts",
            "The new layout is cleaner overall",
        ],
        "expected_risks_json": ["Accessibility gaps may block users from key workflows"],
        "expected_recommendations_json": [
            "Fix keyboard navigation",
            "Improve text contrast",
            "Add screen reader labels to charts",
        ],
        "expected_themes_json": ["usability"],
        "expected_output_notes": "Report should include accessibility-specific recommendations.",
    },
]


def seed_default_evaluation_cases(db: Session) -> list[EvaluationCase]:
    seeded: list[EvaluationCase] = []
    defaults_by_workflow = {
        WorkflowType.sales_report: DEFAULT_SALES_EVALUATION_CASES,
        WorkflowType.customer_feedback: DEFAULT_CUSTOMER_FEEDBACK_EVALUATION_CASES,
    }
    for workflow_type, defaults in defaults_by_workflow.items():
        seeded.extend(_seed_cases_for_workflow(db, workflow_type, defaults))

    db.commit()
    for case in seeded:
        db.refresh(case)
    return seeded


def _seed_cases_for_workflow(
    db: Session,
    workflow_type: WorkflowType,
    defaults: list[dict[str, object]],
) -> list[EvaluationCase]:
    seeded: list[EvaluationCase] = []
    for default in defaults:
        case = (
            db.query(EvaluationCase)
            .filter(
                EvaluationCase.workflow_type == workflow_type,
                EvaluationCase.title == default["title"],
            )
            .first()
        )
        if case is None:
            case = EvaluationCase(
                workflow_type=workflow_type,
                title=default["title"],
                input_text=default["input_text"],
                expected_facts_json=default["expected_facts_json"],
                expected_risks_json=default["expected_risks_json"],
                expected_recommendations_json=default["expected_recommendations_json"],
                expected_themes_json=default.get("expected_themes_json"),
                expected_output_notes=default["expected_output_notes"],
            )
            db.add(case)
        else:
            case.input_text = default["input_text"]
            case.expected_facts_json = default["expected_facts_json"]
            case.expected_risks_json = default["expected_risks_json"]
            case.expected_recommendations_json = default["expected_recommendations_json"]
            case.expected_themes_json = default.get("expected_themes_json")
            case.expected_output_notes = default["expected_output_notes"]
        seeded.append(case)
    return seeded
