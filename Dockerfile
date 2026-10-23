# Backend/worker image. Build context is the repository root.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH=/app/.venv/bin:$PATH

RUN pip install --no-cache-dir "uv>=0.5,<1"

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY packages ./packages
COPY apps/backend ./apps/backend
COPY alembic.ini ./

RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uvicorn", "logistics_backend.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
