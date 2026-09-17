"""Infrastructure operators: export aggregate Prometheus metrics using DB access.

Run `uv run python -m src.operations_metrics`. Tenant API roles cannot invoke this
global view remotely. No identifiers, payloads or worker hostnames are exported.
"""

from src.database import engine
from src.services.operations import prometheus, snapshot


def main():
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
        print(prometheus(snapshot(conn, None)), end="")


if __name__ == "__main__":
    main()
