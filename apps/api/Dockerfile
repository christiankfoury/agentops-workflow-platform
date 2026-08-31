FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.12.7

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"]
