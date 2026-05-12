# An Integrated Multi-Agent System for AI-Driven FMEA Auditing

## Postdoctoral Research Project

**UTC (France) | CIT (Japan)**  
**Researcher:** Ederson Carvalhar Fernandes

---

## Overview

This repository contains an AI-assisted FMEA platform with:

- a FastAPI backend for extraction, persistence, and specialist-agent workflows
- a React frontend for document upload, review, AI suggestions, and session recovery
- PostgreSQL for relational persistence
- MinIO for uploaded files and generated artifacts
- local vector indexes for Books and Standards retrieval
- RAGAS and LLM-as-Judge evaluation for AI suggestions

The current persistence model is Alembic-first: database schema changes are applied through migrations, and the application no longer relies on SQLAlchemy `create_all()` during startup.

---

## Quick Start With Docker

1. Create a `.env` file from `.env.example` and fill in the required values, especially `UTCLLM_API_KEY`.
2. Never commit `.env` to version control.
3. Start the full stack:

```bash
docker compose up --build
```

Subsequent runs usually do not need a rebuild:

```bash
docker compose up
```

Available services:

- UI: http://localhost:5174
- API base: http://localhost:8001
- Docker-internal API port: `api:8000`
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
- MinIO API: http://localhost:9000
- MinIO Console: http://localhost:9001
- PostgreSQL: `localhost:5433`

### Docker Startup Notes

The `api` container runs this boot sequence:

1. `alembic upgrade head`
2. `uvicorn backend.main:app --host 0.0.0.0 --port 8000`

If you keep following container logs after startup, repeated `GET /health` entries are expected. They are health checks, not a migration still running.

---

## Local Development

### Backend

Requirements:

- Python 3.11+
- Poetry
- PostgreSQL and MinIO available locally or through Docker

Install dependencies and apply migrations:

```bash
poetry install
poetry run alembic upgrade head
poetry run uvicorn backend.main:app --reload --port 8001
```

### Frontend

Requirements:

- Node.js 18+

```bash
cd frontend
npm ci
npm run dev
```

Frontend URLs by mode:

| Mode | URL | Use case |
|------|-----|----------|
| Local Vite dev server | http://localhost:5173 | Fast frontend iteration |
| Docker web container | http://localhost:5174 | Production-like frontend build |

When developing the frontend locally, it is usually better to stop the Docker `web` container and keep the Docker `api` container running.

The local Vite frontend proxies `/api` requests to `http://127.0.0.1:8001`. The Docker web container serves the production build on port `5174` and proxies `/api` internally to `http://api:8000`.

---

## Updating Dependencies

Use Poetry as the source of truth for Python dependencies.

`pyproject.toml` declares the dependency ranges required by the project, while
`poetry.lock` records the exact versions selected by Poetry after dependency
resolution. This keeps local development, Docker builds, and future clones of
the repository reproducible. When dependencies change, commit `poetry.lock`
together with `pyproject.toml`.

```bash
poetry add <package>
poetry update <package>
poetry update
```

After dependency changes, rebuild the backend image:

```bash
docker compose build api
docker compose up
```

Always commit `poetry.lock` together with dependency changes.

---

## API Summary

### System

- `GET /health` — service health check

### Extraction and Analysis

- `POST /extract` — extract FMEA data from PDF or Excel
- `POST /extract/stream` — stream PDF extraction page by page
- `POST /analyze` — request an AI suggestion for a specific FMEA field
- `POST /missing-failures` — identify candidate failure modes not yet covered

### Book Indexing

- `GET /index/books` — inspect indexed Books and Standards status
- `POST /index/books` — index or re-index all PDFs under `Books/` and `Standards/`
- `GET /index/books/diagnostics` — inspect extraction diagnostics for a specific reference PDF

### Sessions and Persistence

- `POST /sessions` — create a new FMEA session
- `GET /sessions` — list all sessions
- `GET /sessions/{session_id}` — get one session
- `PUT /sessions/{session_id}` — update one session
- `DELETE /sessions/{session_id}` — delete one session
- `POST /sessions/from-extraction` — create a session and persist extracted records
- `PUT /sessions/{session_id}/document` — persist the current edited document for an existing session
- `POST /sessions/{session_id}/files` — persist the original uploaded file for a session
- `GET /sessions/{session_id}/files` — list original uploaded files for a session
- `GET /sessions/{session_id}/document` — get the active persisted document snapshot
- `GET /sessions/{session_id}/records` — get all saved FMEA records for a session
- `POST /sessions/{session_id}/suggestions` — persist an AI suggestion and engineer verdict

Interactive API documentation is available in Swagger UI at http://localhost:8001/docs.

---

## Backend Details

- FastAPI with async endpoints
- SQLAlchemy async ORM
- Alembic for schema migrations
- Pydantic v2 schemas
- MinIO-backed file persistence
- Local vector indexes for Books and Standards retrieval
- UTC LLM integration through `https://ia.beta.utc.fr`
- RAGAS faithfulness and response-groundedness evaluation
- LLM-as-Judge validation after specialist-agent generation
- Docker backend image optimized for CPU-only Torch usage

---

## Persistence and Storage

The platform currently uses:

- PostgreSQL 16 for relational persistence
- MinIO for original uploads and future generated artifacts
- Local vector indexes under `data/vector_store/books/` and `data/vector_store/standards/` for active specialist-agent retrieval
- ChromaDB files may still exist under `data/vector_store/`, but the current specialist RAG path uses the local `rows.json` and `embeddings.npy` indexes

### Main persisted entities

| Table | Purpose |
|------|---------|
| `fmea_sessions` | Root entity for each analysis session |
| `uploaded_files` | Original uploaded file metadata |
| `session_artifacts` | Versioned derived outputs such as extraction snapshots |
| `fmea_records` | Persisted FMEA rows |
| `ai_suggestions` | AI-generated suggestions and review state |
| `suggestion_feedback` | Engineer decision snapshots for future ML use |
| `fmea_reports` | JSON or PDF report snapshots |
| `meetings` | Meeting sessions optionally linked to FMEA work |
| `meeting_transcripts` | STT outputs and media linkage |
| `meeting_fmea_links` | Links between transcript segments and FMEA rows |
| `agent_telemetry` | LLM latency, token usage, and error tracking |

### Migrations

Apply migrations locally with:

```bash
poetry run alembic upgrade head
```

If you are using a local virtual environment instead of Poetry-managed execution:

```powershell
$env:DATABASE_URL="postgresql+asyncpg://fmea:fmea_secret@localhost:5433/fmea_db"
.\venv\Scripts\python.exe -m alembic upgrade head
```

---

## Project Structure

```text
FMEA_AI/
├── backend/                       # FastAPI backend application
│   ├── agents/                    # Specialist agent orchestration
│   ├── services/                  # Extraction, indexing, and related services
│   ├── Dockerfile                 # Backend container image
│   ├── database.py                # Async engine and session factory
│   ├── main.py                    # API entry point
│   ├── models.py                  # SQLAlchemy ORM models
│   ├── schemas.py                 # Pydantic request/response models
│   └── storage.py                 # MinIO storage helpers
├── frontend/                      # React frontend
├── migrations/                    # Alembic migrations
├── src/                           # Analytics, NLP, preprocessing, vector store, visualization
├── Books/                         # Reference books used for retrieval
├── Standards/                     # Standards documents used as normative references
├── data/                          # Sample data and local vector indexes
├── tests/                         # Test suite
├── translations/                  # i18n resources (en, fr, pt-br)
├── docker-compose.yml             # Full local stack
├── pyproject.toml                 # Python project configuration
├── poetry.lock                    # Locked Python dependencies
└── requirements.txt               # pip fallback dependency file
```

---

## Key Capabilities

- FMEA extraction from PDF and Excel documents
- Session persistence with reopening through the frontend
- Original file persistence in MinIO
- Editable document snapshots with explicit save flow
- Specialist-agent suggestions for FMEA fields
- Books and Standards retrieval for specialist-agent context
- RAGAS evaluation for faithfulness and response groundedness
- LLM-as-Judge and human-review persistence in `ai_suggestions`
- Multilingual support in English, French, and Brazilian Portuguese

---

## Architecture Overview

```text
Frontend (React/Vite or nginx-served build)
    |
    v
FastAPI backend
    |
    +-- PostgreSQL 16   (sessions, records, suggestions, feedback, telemetry)
    +-- MinIO           (uploaded files and future generated artifacts)
    +-- Local indexes   (Books and Standards retrieval store)
    +-- NLP/analytics   (extraction, risk analysis, supporting utilities)
```

---

## Tech Stack

### Core

- Python 3.11+
- FastAPI
- React 18
- Vite 5
- Tailwind CSS 3
- Docker and Docker Compose
- OpenAI-compatible UTC LLM integration

### Data and AI

- SQLAlchemy 2.x
- Alembic
- asyncpg
- PostgreSQL 16
- MinIO
- ChromaDB
- RAGAS
- PyMuPDF
- Pandas
- openpyxl
- Torch CPU-only

### Development

- Poetry
- pytest

---

## Current Direction

The repository currently supports persistence for sessions, uploaded files, extracted records, edited document snapshots, and reviewed AI suggestions. Specialist-agent suggestions use RAG over local Books and Standards indexes, then evaluate generated suggestions with RAGAS and LLM-as-Judge before returning them to the frontend.

The AI Suggestion flow is:

```text
Frontend AI Suggestion or Swagger POST /analyze
    -> router LLM selects a specialist agent
    -> RAG retrieves Books and Standards context
    -> specialist LLM generates the suggestion
    -> RAGAS evaluates faithfulness and response groundedness
    -> LLM-as-Judge evaluates correctness
    -> response is returned to the UI
```

`POST /analyze` computes the suggestion and evaluation values but does not persist them by itself. Suggestions and RAGAS metadata are persisted when the engineer accepts or rejects the suggestion through `POST /sessions/{session_id}/suggestions`. The edited FMEA table is persisted separately through `PUT /sessions/{session_id}/document`, which is the Save Session flow in the frontend.

---

**Last Updated:** May 2026
