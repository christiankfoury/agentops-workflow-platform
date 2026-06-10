FROM python:3.12-slim

RUN pip install uv

WORKDIR /app

COPY pyproject.toml .
RUN uv sync

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
