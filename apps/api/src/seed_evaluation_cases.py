from src.database import SessionLocal
from src.services.evaluation_cases import seed_default_evaluation_cases


def main() -> None:
    with SessionLocal() as db:
        cases = seed_default_evaluation_cases(db)
    print(f"Seeded {len(cases)} evaluation cases.")


if __name__ == "__main__":
    main()
