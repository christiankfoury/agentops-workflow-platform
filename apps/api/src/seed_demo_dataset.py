from src.database import SessionLocal
from src.services.demo_dataset import seed_demo_dataset


def main() -> None:
    with SessionLocal() as db:
        summary = seed_demo_dataset(db)
    print(
        "Seeded demo dataset: "
        f"{summary.evaluation_cases} evaluation cases, "
        f"{summary.uploaded_inputs} uploaded inputs, "
        f"{summary.workflow_runs} workflow runs, "
        f"{summary.evaluation_results} evaluation results, "
        f"{summary.agent_steps} agent steps."
    )


if __name__ == "__main__":
    main()
