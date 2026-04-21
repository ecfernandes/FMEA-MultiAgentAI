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

# Install backend-only dependencies (layer cache)
# Uses backend/requirements.txt — much lighter than the root requirements.txt
# (no torch, transformers, spacy, streamlit, etc.)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Non-root user
RUN adduser --disabled-password --gecos "" fmea && chown -R fmea /app
USER fmea

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# --reload enables hot-reload when source files change via Docker volume
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
