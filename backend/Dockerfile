# ============================================================================
# backend/Dockerfile
# AI-Driven FMEA 5.0 — FastAPI Backend
# Build context: project root (needs src/, requirements.txt, translations/)
# ============================================================================
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry (pinned to same version used locally)
RUN pip install --no-cache-dir poetry==2.1.3

# Copy only dependency files first — maximises Docker layer cache.
# If pyproject.toml/poetry.lock don't change, this layer is reused.
COPY pyproject.toml poetry.lock ./

# Install production deps from the lock file directly into the system Python.
# --only main   → skip [dev] group (pytest etc.)
# --no-root     → don't try to install the project itself as a package
# virtualenvs.create false → no venv inside container (cleaner for Docker)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root

# Copy source
COPY . .

# Non-root user
RUN adduser --disabled-password --gecos "" fmea && chown -R fmea /app
USER fmea

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
