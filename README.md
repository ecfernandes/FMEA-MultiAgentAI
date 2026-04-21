# An Integrated Multi-Agent System for AI-Driven FMEA Auditing


## Postdoctoral Research Project
**UTC (France) | CIT (Japan)** 
**Researcher:** Ederson Carvalhar Fernandes


### Quick Start


1. Install backend dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Start the backend (FastAPI):
```bash
uvicorn main:app --reload
```
Or, using Docker:
```bash
docker build -t fmea-backend -f Dockerfile.backend .
docker run -p 8000:8000 fmea-backend
```

3. Start the frontend:
- For a quick test, open the file `fmea_app.html` in your browser.
- Or, to run the React frontend:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

4. (Optional) Configure environment variables:
Copy `.env.example` to `.env` and set the required keys.




### Project Structure
```
PM_AI/

├── backend/                       # FastAPI backend application
│   ├── main.py                    # FastAPI entry point
│   ├── requirements.txt           # Backend dependencies
│   ├── Dockerfile.backend         # Dockerfile for backend
│   ├── agents/                    # Specialist agent modules
│   └── services/                  # Extraction and indexing services
│
├── frontend/                      # (Optional) React frontend (Vite)
│   ├── src/                       # React source code
│   ├── index.html                 # Main HTML entry
│   ├── package.json               # Frontend dependencies
│   └── Dockerfile                 # Dockerfile for frontend
│
├── fmea_app.html                  # Standalone HTML+CDN demo UI
│
├── data/                          # Data and vector stores
│   ├── sample_documents/          # Example documents
│   └── vector_store/              # ChromaDB storage
│
├── src/                           # Core analytics and utilities
│   ├── analytics/                 # Quantitative analysis modules
│   ├── nlp/                       # NLP and risk analysis
│   ├── preprocessing/             # Data preprocessing

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

Core:

Python 3.10+
FastAPI (backend REST API)
React (frontend, optional)
HTML+CDN (standalone demo UI)
Docker (containerization)
UTCLLM (UTC Large Language Model integration)
NLP/ML:

LangChain (LLM orchestration)
Sentence Transformers (embeddings)
Scikit-learn (future ML models)

Data:

ChromaDB (vector store for RAG)
Pandas (data manipulation)


---

**Last Updated:** April 2026  
