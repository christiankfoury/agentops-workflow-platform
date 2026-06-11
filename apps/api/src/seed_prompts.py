from src.database import SessionLocal
from src.services.prompt_versions import seed_default_prompt_versions


def main() -> None:
    with SessionLocal() as db:
        prompts = seed_default_prompt_versions(db)
    print(f"Seeded {len(prompts)} prompt versions.")


if __name__ == "__main__":
    main()
