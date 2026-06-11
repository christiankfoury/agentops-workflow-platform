from enum import StrEnum


class AgentType(StrEnum):
    analyst = "analyst"
    reviewer = "reviewer"
    writer = "writer"
    router = "router"
    timeline = "timeline"
    root_cause = "root_cause"
    classifier = "classifier"
    insight = "insight"
