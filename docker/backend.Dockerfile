# Backend image - FastAPI served by uvicorn.
# Build context: repository root (see docker-compose.yml).

# Base image pinned by digest (review S7, read on 30/10); Dependabot proposes the updates.
FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

# uv is the dependency manager of the backend (pinned for reproducible builds).
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Dependencies first: this layer is rebuilt only when the lock file changes.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/ ./

# Never run the API as root.
RUN useradd --create-home --uid 1000 roi \
    # Mount point of the GLEIF copy (branch feature/gleif-local): a named volume created on this
    # folder inherits its owner, so the updater (same image, same user) can write into it.
    && mkdir -p /data/gleif && chown roi:roi /data/gleif
USER roi

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
