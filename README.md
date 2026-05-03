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
- **UI:** http://localhost:5174 (or open `fmea_app.html` directly in the browser)
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
│   ├── agents/                    # Specialist AI agent modules
│   └── services/                  # Extraction and indexing services
│
├── frontend/                      # React frontend (Vite)
│   ├── src/                       # React source code
│   ├── index.html
│   ├── package.json
│   └── Dockerfile
│
├── fmea_app.html                  # Standalone HTML+CDN demo UI (no build needed)
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
│      │  fmea_app.html (HTML+CDN demo)                │      │
│      │  or React App (frontend/)                     │      │
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
         │   (ChromaDB, files)    │
         └────────────────────────┘
Frontend: User interacts via a web interface (HTML demo or React app).
Backend: FastAPI serves REST endpoints for document upload, analysis, and retrieval.
Analytics/NLP: Core logic for risk analysis, RAG, and document processing.
Data Storage: Vector store (ChromaDB) and file storage for documents and embeddings.
---

### Future Roadmap

AI-Meeting

---



### Tech Stack

**Core:**
- Python 3.11+
- FastAPI (backend REST API + SSE streaming)
- React 18 (frontend)
- Docker + Docker Compose (containerization)
- UTCLLM / OpenAI-compatible API (LLM integration)

**NLP / ML:**
- Sentence Transformers (embeddings)
- PyMuPDF (PDF extraction)
- OpenAI client (LLM calls)

**Data:**
- ChromaDB (vector store for RAG)
- Pandas + openpyxl (Excel processing)

**Dev:**
- Poetry (dependency management)
- pytest (tests)

---

**Last Updated:** May 2026
