# Backend/worker image. Build context is the repository root.
FROM python:3.12-slim AS runtime

ARG UV_DEFAULT_INDEX=https://pypi.org/simple
ARG PIP_INDEX_URL=https://pypi.org/simple
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_DEFAULT_INDEX=${UV_DEFAULT_INDEX} \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    PATH=/app/.venv/bin:$PATH

RUN pip install --no-cache-dir --index-url "$PIP_INDEX_URL" "uv>=0.5,<1"

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY packages ./packages
COPY apps/backend ./apps/backend
COPY partner_engine/backend ./partner_engine/backend
COPY partner_engine/frontend/public ./partner_engine/frontend/public
COPY data ./data
COPY alembic.ini ./

RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uvicorn", "logistics_backend.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
