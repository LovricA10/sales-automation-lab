# ---------- Stage 1: install dependencies ----------
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Dependencies first, so the Docker layer cache survives code-only changes.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

# ---------- Stage 2: slim runtime image ----------
FROM python:3.12-slim
RUN useradd --create-home app
WORKDIR /app
COPY --from=builder /app /app
COPY alembic.ini ./
COPY migrations ./migrations
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn sales_api.api.main:create_app --factory --host 0.0.0.0 --port 8000"]
