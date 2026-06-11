from sqlalchemy.orm import Session

from src.models.agent_type import AgentType
from src.models.prompt_version import PromptVersion

DEFAULT_PROMPTS = [
    {
        "agent_type": AgentType.analyst,
        "name": "Sales Analyst Agent",
        "template": (
            "Analyze the supplied sales report. Extract key findings, risks, "
            "opportunities, recommendations, and supporting evidence as structured JSON. "
            "Use only facts supported by the source input."
        ),
        "notes": "Initial sales report analyst prompt.",
    },
    {
        "agent_type": AgentType.reviewer,
        "name": "Reviewer Agent",
        "template": (
            "Review the agent output against the original source input. Identify unsupported "
            "claims, verify numbers, assign a quality score from 0 to 1, and recommend "
            "approval, retry, or human review."
        ),
        "notes": "Initial factual review prompt.",
    },
    {
        "agent_type": AgentType.writer,
        "name": "Writer Agent",
        "template": (
            "Turn approved structured analysis into a concise business report for leadership. "
            "Do not introduce unsupported claims, preserve important numbers, and include "
            "risks and recommended actions."
        ),
        "notes": "Initial final report writer prompt.",
    },
    {
        "agent_type": AgentType.router,
        "name": "Router Agent",
        "template": (
            "Classify the input as a sales report, customer feedback, or incident log. Return "
            "the workflow type, confidence, and a short reasoning summary."
        ),
        "notes": "Initial workflow routing prompt.",
    },
    {
        "agent_type": AgentType.timeline,
        "name": "Timeline Agent",
        "template": (
            "Extract a chronological timeline from the incident log. Preserve timestamps, "
            "event descriptions, and source evidence for every event."
        ),
        "notes": "Initial incident timeline prompt.",
    },
    {
        "agent_type": AgentType.root_cause,
        "name": "Root Cause Agent",
        "template": (
            "Analyze the incident timeline. Separate confirmed facts from inferred causes, "
            "identify unknowns, estimate impact, and recommend follow-up actions."
        ),
        "notes": "Initial root cause analysis prompt.",
    },
    {
        "agent_type": AgentType.classifier,
        "name": "Classifier Agent",
        "template": (
            "Classify customer feedback into themes such as pricing, bugs, feature requests, "
            "performance, usability, and support experience. Include counts, sentiment, and "
            "representative examples."
        ),
        "notes": "Initial customer feedback classification prompt.",
    },
    {
        "agent_type": AgentType.insight,
        "name": "Insight Agent",
        "template": (
            "Convert classified customer feedback into product insights. Identify top pain "
            "points, feature requests, risks, recommendations, and supporting examples."
        ),
        "notes": "Initial customer feedback insight prompt.",
    },
]


def deactivate_matching_prompts(
    db: Session, agent_type: AgentType, name: str, exclude_id: object | None = None
) -> None:
    query = db.query(PromptVersion).filter(
        PromptVersion.agent_type == agent_type,
        PromptVersion.name == name,
    )
    if exclude_id is not None:
        query = query.filter(PromptVersion.id != exclude_id)

    for prompt in query.all():
        prompt.is_active = False


def activate_prompt_version(db: Session, prompt: PromptVersion) -> PromptVersion:
    deactivate_matching_prompts(db, prompt.agent_type, prompt.name, exclude_id=prompt.id)
    prompt.is_active = True
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt


def seed_default_prompt_versions(db: Session) -> list[PromptVersion]:
    seeded: list[PromptVersion] = []

    for default in DEFAULT_PROMPTS:
        prompt = (
            db.query(PromptVersion)
            .filter(
                PromptVersion.agent_type == default["agent_type"],
                PromptVersion.name == default["name"],
                PromptVersion.version == 1,
            )
            .first()
        )

        if prompt is None:
            deactivate_matching_prompts(db, default["agent_type"], default["name"])
            prompt = PromptVersion(
                agent_type=default["agent_type"],
                name=default["name"],
                version=1,
                template=default["template"],
                notes=default["notes"],
                is_active=True,
            )
            db.add(prompt)
        else:
            deactivate_matching_prompts(db, prompt.agent_type, prompt.name, exclude_id=prompt.id)
            prompt.template = default["template"]
            prompt.notes = default["notes"]
            prompt.is_active = True

        seeded.append(prompt)

    db.commit()
    for prompt in seeded:
        db.refresh(prompt)

    return seeded
