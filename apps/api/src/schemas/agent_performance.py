from pydantic import BaseModel


class AgentPerformanceSummaryRead(BaseModel):
    agent_type: str
    agent_name: str
    step_count: int
    completed_count: int
    failed_count: int
    retry_count: int
    schema_validation_failure_count: int
    average_latency_ms: float
    average_cost: float
    failure_rate: float
    retry_rate: float
    average_reviewer_score: float | None
    schema_validation_failure_rate: float
