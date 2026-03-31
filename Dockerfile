FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . /app

RUN uv sync --locked --no-editable --no-dev


FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY src/ /app/src/

CMD ["/app/.venv/bin/kopf", "run", "/app/src/postgres_db_admin_operator/main.py", "--all-namespaces"]
