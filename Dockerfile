# Use Python 3.12 slim
FROM python:3.12-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast pip sync
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy requirements
COPY requirements/ /app/requirements/

# Create venv and install deps
RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install -r /app/requirements/base.txt

FROM base AS dev
RUN . /app/.venv/bin/activate && \
    uv pip install -r /app/requirements/local.txt
COPY . /app/

FROM base AS production
RUN . /app/.venv/bin/activate && \
    uv pip install -r /app/requirements/production.txt
COPY . /app/
RUN . /app/.venv/bin/activate && \
    python manage.py collectstatic --noinput --settings=config.settings.production

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

CMD ["/app/.venv/bin/gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]