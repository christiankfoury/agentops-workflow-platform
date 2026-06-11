import argparse
from collections.abc import Sequence

from src.config import settings
from src.database import SessionLocal
from src.models.evaluation_case import EvaluationCase
from src.models.workflow_run import RunMode
from src.services.evaluation_cases import seed_default_evaluation_cases
from src.services.evaluation_runner import run_sales_evaluation_suite
from src.services.llm_client import LLMClient
from src.services.prompt_versions import seed_default_prompt_versions


def parse_run_modes(argv: Sequence[str] | None = None) -> tuple[RunMode, ...]:
    parser = argparse.ArgumentParser(description="Run workflow evaluation cases.")
    parser.add_argument(
        "--mode",
        choices=("baseline", "multi_agent", "all"),
        default="all",
        help="Evaluation mode to run. Defaults to all.",
    )
    args = parser.parse_args(argv)
    if args.mode == "baseline":
        return (RunMode.baseline,)
    if args.mode == "multi_agent":
        return (RunMode.multi_agent,)
    return (RunMode.baseline, RunMode.multi_agent)


def main(argv: Sequence[str] | None = None) -> None:
    run_modes = parse_run_modes(argv)
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to run evaluations.")

    llm_client = LLMClient(
        api_key=settings.openai_api_key,
        default_model=settings.openai_model,
    )
    with SessionLocal() as db:
        seed_default_prompt_versions(db)
        seed_default_evaluation_cases(db)
        cases = db.query(EvaluationCase).all()
        results = run_sales_evaluation_suite(
            db,
            cases,
            llm_client,
            run_modes=run_modes,
        )
    print(f"Stored {len(results)} evaluation results.")


if __name__ == "__main__":
    main()
