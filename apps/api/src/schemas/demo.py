from pydantic import BaseModel


class DemoDatasetSummaryRead(BaseModel):
    evaluation_cases: int
    uploaded_inputs: int
    workflow_runs: int
    evaluation_results: int
    agent_steps: int
