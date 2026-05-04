# An Integrated Multi-Agent System for AI-Driven FMEA Auditing

## Postdoctoral Research Project
**UTC (France) | CIT (Japan)**
**Researcher:** Ederson Carvalhar Fernandes

---

## Quick Start (Docker — recommended)

```bash
cp .env.example .env        # fill in UTCLLM_API_KEY and other vars
docker compose up --build   # first run: builds and starts everything
docker compose up           # subsequent runs (no rebuild needed)
```

The app is available at:
- **UI:** http://localhost:5174 (React + Vite, served by nginx)
- **API:** http://localhost:8001/docs

---

## Local Development (without Docker)

**Requirements:** Python 3.11+ and [Poetry](https://python-poetry.org/docs/#installation)

```bash
poetry install              # installs all dependencies from poetry.lock
poetry run uvicorn backend.main:app --reload --port 8001
```

Frontend (optional React UI):
```bash
cd frontend
npm install
npm run dev
```

---

## Updating Dependencies

When you need to add or update a package:

```bash
# 1. Edit pyproject.toml (add/change the package version)
# or run:
poetry add <package>          # add new package
poetry update <package>       # update one package
poetry update                 # update all within version constraints

# 2. Rebuild the Docker image to apply changes
docker compose build api
docker compose up
```

The `poetry.lock` file must always be committed to git — it guarantees that
every developer and every Docker build uses the exact same dependency versions.

---




### Project Structure
```
FMEA_AI/
├── pyproject.toml                 # Dependency management (Poetry)
├── poetry.lock                    # Pinned dependency versions — always commit this
├── requirements.txt               # pip fallback (mirrors pyproject.toml)
├── docker-compose.yml             # Orchestrates API + DB + frontend
│
├── backend/                       # FastAPI backend application
│   ├── Dockerfile                 # Single Dockerfile for the API container
│   ├── main.py                    # FastAPI entry point
│   ├── schemas.py                 # Pydantic models
│   ├── database.py                # SQLAlchemy async engine + session factory
│   ├── models.py                  # ORM models (10 tables — PostgreSQL)
│   ├── storage.py                 # MinIO client wrapper
│   ├── agents/                    # Specialist AI agent modules
│   └── services/                  # Extraction and indexing services
│
├── frontend/                      # React frontend (Vite + Tailwind CSS)
│   ├── src/
│   │   ├── App.jsx                # All UI components (migrated from legacy HTML)
│   │   ├── main.jsx               # React 18 entry point
│   │   └── index.css              # Tailwind directives + animations
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js         # darkMode: 'class', industrial palette
│   ├── postcss.config.js
│   └── Dockerfile                 # Multi-stage: node:18-alpine → nginx:alpine
│
├── legacy/
│   └── fmea_app.html              # Original standalone HTML+CDN demo (reference only)
│
├── migrations/                    # Alembic database migrations
│   ├── env.py
│   └── versions/                  # ac938dff9acc_create_initial_tables.py (APPLIED)
│
├── src/                           # Core analytics and utilities
│   ├── analytics/                 # Monte Carlo, EMV, probability calibration
│   ├── nlp/                       # NLP, risk analysis, deduplication
│   ├── preprocessing/             # PDF/Excel FMEA extractors
│   ├── vector_store/              # ChromaDB manager, embeddings, retriever
│   └── visualization/             # Ontology builder (Plotly/NetworkX)
│
├── data/
│   ├── sample_documents/          # Example FMEA documents
│   └── vector_store/              # ChromaDB persistent storage
│
├── migrations/                    # Alembic database migrations
│   ├── env.py                     # Async migration environment
│   └── versions/                  # Auto-generated migration scripts
│
├── Books/                         # Reference books for RAG indexing
├── Standards/                     # FMEA standards documents
├── tests/                         # pytest test suite
└── translations/                  # i18n files (en, fr, pt-br)
```

### Key Features (MVP v2.0)

Multilingual Support: Interface and prompts available in English, French, and Brazilian Portuguese.
RAG (Retrieval-Augmented Generation): Semantic search, historical memory, and context-aware recommendations using ChromaDB.
Document Analysis: AI-powered risk detection and categorization from PDF, TXT, and DOCX files, with UTCLLM integration.
Interactive Dashboard: Visual risk matrix, metrics, historical tracking, and CSV export.
Multiple File Support: Analyze and compare several documents simultaneously.
---

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                            │
│      ┌───────────────────────────────────────────────┐      │
│      │  React 18 + Vite + Tailwind CSS (frontend/)  │      │
│      │  served by nginx (Docker port 5174)           │      │
└──────┴───────────────────────────────────────────────┘      │
                     │  (REST API calls)                      │
         ┌───────────▼────────────┐
         │      Backend           │
         │   FastAPI (backend/)   │
         └───────────┬────────────┘
                     │
         ┌───────────▼────────────┐
         │   Analytics & NLP      │
         │   (src/analytics, nlp) │
         └───────────┬────────────┘
                     │
         ┌───────────▼────────────┐
         │   Data Storage         │
         │   PostgreSQL 16 (DB)   │
         │   MinIO (file storage) │
         │   ChromaDB (vectors)   │
         └────────────────────────┘
Frontend: User interacts via a web interface (HTML demo or React app).
Backend: FastAPI serves REST endpoints for document upload, analysis, and retrieval.
Analytics/NLP: Core logic for risk analysis, RAG, and document processing.
Data Storage: PostgreSQL (relational persistence), MinIO (file/object storage), ChromaDB (vector store for RAG).
---

### Future Roadmap

AI-Meeting

---

### Database Infrastructure

The system uses **PostgreSQL 16** for relational persistence and **MinIO** for object/file storage.

**Services (docker-compose):**
| Service | Port (host) | Purpose |
|---------|-------------|---------|
| `db` | 5433 | PostgreSQL 16 |
| `minio` | 9000 / 9001 | MinIO API / Console |
| `api` | 8001 | FastAPI backend |
| `web` | 5174 | React frontend (nginx) |

**Database tables (10):**
| Table | Description |
|-------|-------------|
| `fmea_sessions` | Anchor for every analysis session |
| `uploaded_files` | Metadata for uploaded files (path in MinIO) |
| `fmea_records` | Individual failure mode rows (component, severity, RPN…) |
| `ai_suggestions` | LLM-generated suggestions per field |
| `suggestion_feedback` | Engineer decision on each suggestion (ML training data) |
| `fmea_reports` | JSON/PDF snapshots of completed analyses |
| `meetings` | Meeting sessions linked to a FMEA session |
| `meeting_transcripts` | STT output for meetings |
| `meeting_fmea_links` | Maps transcript segments to FMEA records |
| `agent_telemetry` | Latency, token usage, errors per LLM call |

**Running migrations (first time):**
```powershell
$env:DATABASE_URL="postgresql+asyncpg://fmea:fmea_secret@localhost:5433/fmea_db"
.\venv\Scripts\python.exe -m alembic revision --autogenerate -m "initial schema"
.\venv\Scripts\python.exe -m alembic upgrade head
```

> **Status:** Migration applied — all 10 tables created in PostgreSQL.
> Persistence endpoints (`POST /sessions`, `GET /sessions`, etc.) are the next development phase.

---



### Tech Stack

**Core:**
- Python 3.11+
- FastAPI (backend REST API + SSE streaming)
- React 18 + Vite 5 + Tailwind CSS 3 (frontend — compiled, served by nginx)
- Docker + Docker Compose (containerization)
- UTCLLM / OpenAI-compatible API (LLM integration)

**NLP / ML:**
- Sentence Transformers (embeddings)
- PyMuPDF (PDF extraction)
- OpenAI client (LLM calls)

**Data:**
- PostgreSQL 16 (relational persistence — sessions, records, AI suggestions, feedback)
- MinIO (object storage — uploaded files, generated reports, audio/video)
- ChromaDB (vector store for RAG)
- SQLAlchemy ≥2.0 + asyncpg (async ORM)
- Alembic (database migrations)
- Pandas + openpyxl (Excel processing)

**Dev:**
- Poetry (dependency management)
- pytest (tests)

---

**Last Updated:** May 2026
