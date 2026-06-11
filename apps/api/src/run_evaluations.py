from src.database import SessionLocal
from src.models.evaluation_case import EvaluationCase
from src.models.workflow_run import RunMode, WorkflowType
from src.services.evaluation_cases import seed_default_evaluation_cases
from src.services.evaluation_runner import run_sales_evaluation_suite
from src.services.llm_client import LLMClient
from src.services.prompt_versions import seed_default_prompt_versions


def main() -> None:
    llm_client = LLMClient()
    with SessionLocal() as db:
        seed_default_prompt_versions(db)
        seed_default_evaluation_cases(db)
        cases = (
            db.query(EvaluationCase)
            .filter(EvaluationCase.workflow_type == WorkflowType.sales_report)
            .all()
        )
        results = run_sales_evaluation_suite(
            db,
            cases,
            llm_client,
            run_modes=(RunMode.baseline, RunMode.multi_agent),
        )
    print(f"Stored {len(results)} evaluation results.")


if __name__ == "__main__":
    main()
