"""
backend/main.py
---------------
FastAPI server for AI-Driven FMEA 5.0.

Headless REST API for professional integrations, Docker deployments,
and the React frontend.

Start the server:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Interactive API docs:
    http://127.0.0.1:8000/docs   (Swagger UI)
    http://127.0.0.1:8000/redoc  (ReDoc)
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.schemas import (
    AgentRequest,
    AgentResponse,
    ExtractionResponse,
    FMEADocumentSchema,
    HealthResponse,
    MissingFailuresRequest,
    MissingFailuresResponse,
    MissingFailureSuggestion,
)
from backend.services.extractor import extract_file
from backend.agents.specialist_agents import route_and_call

# ── Load environment variables ──────────────────────────────────────────────
_ENV_FILE = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=True)

# ============================================================================
# LIFESPAN — startup / shutdown hooks
# ============================================================================

# ============================================================================
# APP FACTORY
# ============================================================================

app = FastAPI(
    title       = "AI-Driven FMEA 5.0 API",
    description = (
        "REST backend for multi-agent FMEA analysis.\n\n"
        "**Endpoints**\n"
        "- `POST /extract` — Upload a PDF or Excel FMEA file and receive structured JSON\n"
        "- `POST /analyze` — Ask a specialist AI agent for a field suggestion\n"
        "- `GET  /health`  — Service health check\n\n"
        "**Authentication** — pass your UTC platform key in the `X-API-Key` header."
    ),
    version     = "5.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# ── CORS (allow any origin for development; restrict in production) ──────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ============================================================================
# DEPENDENCY HELPERS
# ============================================================================

def _resolve_api_key(x_api_key: str | None) -> str:
    """
    Resolve the UTC platform API key from:
      1. X-API-Key request header (preferred)
      2. UTCLLM_API_KEY environment variable (fallback)

    Raises HTTP 401 if no key is available.
    """
    key = x_api_key or os.getenv("UTCLLM_API_KEY", "")
    if not key:
        raise HTTPException(
            status_code=401,
            detail=(
                "UTC platform API key required. "
                "Pass it in the X-API-Key header or set UTCLLM_API_KEY in .env"
            ),
        )
    return key


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Returns service status. Use to verify the backend is running."""
    return HealthResponse()


@app.post(
    "/extract",
    response_model = ExtractionResponse,
    tags           = ["Extraction"],
    summary        = "Extract FMEA data from a PDF or Excel file",
    description    = (
        "Upload a supplier FMEA document. The service will:\n"
        "1. Detect the file format (PDF or Excel)\n"
        "2. Extract all FMEA rows (function, failure mode, effect, cause, S/O/D)\n"
        "3. Return the structured JSON document\n\n"
        "For PDF files the UTC LLM platform is used — an API key is required.\n"
        "For Excel files the extraction is rule-based and requires no API key."
    ),
)
async def extract_document(
    file      : UploadFile = File(..., description="PDF or Excel FMEA file"),
    x_api_key : str | None = Header(default=None, description="UTC platform API key"),
    model_name: str | None = Header(default=None, alias="X-Model-Name",
                                    description="Override the LLM model (optional)"),
):
    """
    Extract structured FMEA data from an uploaded file.

    - **PDF**: uses the UTC LLM platform for deep row-by-row extraction.
    - **Excel (.xlsx/.xls)**: uses the rule-based FMEAExtractorV2.

    Returns a fully-validated `FMEADocumentSchema` wrapped in `ExtractionResponse`.
    """
    api_key = _resolve_api_key(x_api_key)

    try:
        file_bytes = await file.read()
        document   = await extract_file(
            file_bytes  = file_bytes,
            filename    = file.filename or "upload",
            api_key     = api_key,
            model_name  = model_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {exc}",
        )

    return ExtractionResponse(
        success  = True,
        message  = f"Extracted {document.total_records} FMEA records from '{file.filename}'",
        document = document,
    )


@app.post(
    "/extract/stream",
    tags    = ["Extraction"],
    summary = "Stream FMEA extraction page-by-page (PDF only)",
    description = (
        "Streams Server-Sent Events (SSE) as each PDF page is processed.\n\n"
        "Events: `start` → `page` (×N) → `done` | `error`.\n\n"
        "For Excel files a single `start` + `done` pair is emitted immediately."
    ),
)
async def extract_document_stream(
    file        : UploadFile = File(...),
    x_api_key   : str | None = Header(default=None),
    model_name  : str | None = Header(default=None, alias="X-Model-Name"),
    x_page_range: str | None = Header(default=None, alias="X-Page-Range"),
):
    api_key    = _resolve_api_key(x_api_key)
    file_bytes = await file.read()
    filename   = file.filename or "upload"

    # Parse optional page range header, e.g. "2-32, 40-42"
    _allowed_pages: set[int] | None = None
    if x_page_range and x_page_range.strip():
        _allowed_pages = set()
        for _part in x_page_range.split(','):
            _part = _part.strip()
            if '-' in _part:
                _a, _b = _part.split('-', 1)
                _allowed_pages.update(range(int(_a), int(_b) + 1))
            elif _part.isdigit():
                _allowed_pages.add(int(_part))

    async def _sse(obj: dict) -> str:
        return f"data: {json.dumps(obj)}\n\n"

    async def excel_stream():
        try:
            from backend.services.extractor import extract_from_excel_bytes

            llm_triggered = False

            async def _on_llm_fallback():
                nonlocal llm_triggered
                llm_triggered = True
                yield await _sse({"type": "status", "message": "Rule-based extraction found no structure — switching to LLM…"})

            # We can't yield inside a nested async generator directly, so we
            # collect any status messages via a queue-like approach.
            status_msgs: list[str] = []

            async def _on_llm_cb():
                status_msgs.append("Rule-based extraction found no structure — switching to LLM…")

            yield await _sse({"type": "start", "total_pages": 1, "filename": filename})
            document = await extract_from_excel_bytes(
                file_bytes, filename, api_key, model_name,
                on_llm_fallback=_on_llm_cb,
            )
            # Forward any status messages emitted during extraction
            for msg in status_msgs:
                yield await _sse({"type": "status", "message": msg})

            columns = getattr(document, "__dict__", {}).get("_excel_columns", [])
            yield await _sse({"type": "done", "document": document.model_dump(), "columns": columns})
        except Exception as exc:
            yield await _sse({"type": "error", "message": str(exc)})

    async def pdf_stream():
        try:
            from src.preprocessing.fmea_pdf_extractor import (
                extract_pages_text,
                extract_fmea_page,
                _discover_columns_from_pages,
                _normalise_records,
                full_extraction_to_fmea_document,
                FMEAFullExtraction,
            )
            from backend.services.extractor import _fmea_document_to_schema
            loop = asyncio.get_event_loop()

            pages = await loop.run_in_executor(None, extract_pages_text, file_bytes)
            # Apply page range filter if provided
            if _allowed_pages:
                pages = [(n, t) for n, t in pages if n in _allowed_pages]
            total_pages = len(pages)
            yield await _sse({"type": "start", "total_pages": total_pages, "filename": filename})

            # ── Phase 1: discover the complete column schema from the first pages ──
            yield await _sse({"type": "status", "message": "Detecting columns…"})
            known_columns, part_name, supplier, _, _page_cache = await loop.run_in_executor(
                None,
                lambda: _discover_columns_from_pages(pages, api_key, model_name),
            )

            # ── Phase 2: extract all rows page by page ────────────────────────
            all_records: list = []
            last_fn: str | None = None
            _FN_SKIP = {
                'function', 'item_function', 'item function', 'fonction',
                'item', 'component_function', 'component',
            }

            for page_num, page_text in pages:
                try:
                    if page_num in _page_cache:
                        # Reuse data already fetched during column discovery — no extra LLM call
                        cached = _page_cache[page_num]
                        recs = cached.get("records", [])
                        for c in cached.get("columns", []):
                            if c not in known_columns and c.lower() not in _FN_SKIP:
                                known_columns.append(c)
                        if cached.get("part_name", "Unknown") not in ("Unknown", None, ""):
                            part_name = cached["part_name"]
                        if cached.get("supplier", "Unknown") not in ("Unknown", None, ""):
                            supplier = cached["supplier"]
                        recs, last_fn = _normalise_records(recs, last_fn)
                        cols = known_columns
                        pname = part_name
                        sup = supplier
                    else:
                        cols, recs, last_fn, pname, sup = await loop.run_in_executor(
                            None,
                            lambda pt=page_text, pn=page_num, lf=last_fn: extract_fmea_page(
                                pt, pn, known_columns, api_key, model_name, lf
                            ),
                        )
                        for c in cols:
                            if c not in known_columns and c.lower() not in _FN_SKIP:
                                known_columns.append(c)
                        if pname and pname != "Unknown":
                            part_name = pname
                        if sup and sup != "Unknown":
                            supplier = sup
                    all_records.extend(recs)
                    yield await _sse({
                        "type": "page",
                        "page": page_num,
                        "total_pages": total_pages,
                        "new_records": len(recs),
                        "total_records": len(all_records),
                    })
                except Exception as exc:
                    yield await _sse({"type": "page_error", "page": page_num, "message": str(exc)})

            extraction = FMEAFullExtraction(
                part_name = part_name,
                supplier  = supplier,
                columns   = known_columns,
                records   = all_records,
            )
            fmea_doc = await loop.run_in_executor(
                None, full_extraction_to_fmea_document, extraction, filename
            )
            document = _fmea_document_to_schema(fmea_doc)
            yield await _sse({"type": "done", "document": document.model_dump(), "columns": known_columns})

        except Exception as exc:
            yield await _sse({"type": "error", "message": str(exc)})

    is_pdf = filename.lower().endswith(".pdf")
    return StreamingResponse(
        pdf_stream() if is_pdf else excel_stream(),
        media_type = "text/event-stream",
        headers    = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post(
    "/analyze",
    response_model = AgentResponse,
    tags           = ["AI Agents"],
    summary        = "Ask a specialist agent for an FMEA field suggestion",
    description    = (
        "Sends a field-level question to the best-matching specialist agent.\n\n"
        "The router selects from 13 domain experts (Fatigue, Corrosion, NVH, "
        "Mechatronics, Materials, ...) based on keyword scoring against the "
        "combined function + failure_mode text.\n\n"
        "The selected agent returns a `suggested_value` and a dense "
        "`justification` grounded in its reference engineering book."
    ),
)
async def analyze_field(
    request   : AgentRequest,
    x_api_key : str | None = Header(default=None, description="UTC platform API key"),
):
    """
    Route an FMEA field to the most appropriate specialist agent and return
    a structured engineering assessment.

    **Supported fields**: any column key present in the FMEA record
    (e.g. `failure_mode`, `effect`, `cause`, `severity`, `current_controls_prevention`, etc.)
    """
    api_key = _resolve_api_key(x_api_key)

    if not request.field.strip():
        raise HTTPException(status_code=422, detail="'field' must not be empty.")

    try:
        result = await route_and_call(request, api_key)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Agent call failed: {exc}",
        )

    return result


# ============================================================================
# KNOWLEDGE BASE — Book Indexing
# ============================================================================

@app.get(
    "/index/books",
    tags    = ["Knowledge Base"],
    summary = "Get indexing status for each reference book",
)
async def books_status():
    """Returns how many chunks are stored per book in ChromaDB."""
    from backend.services.book_indexer import books_index_status
    return {"status": books_index_status()}


@app.post(
    "/index/books",
    tags    = ["Knowledge Base"],
    summary = "Index (or re-index) all books in the Books/ folder",
    description = (
        "Reads every PDF in `Books/`, extracts text page-by-page, splits into "
        "chunks and stores them in ChromaDB (`fmea_books` collection).\n\n"
        "Already-indexed chunks are skipped — safe to run repeatedly.\n\n"
        "**This only needs to be run once** (or when new books are added)."
    ),
)
async def index_books():
    """Index all reference books into ChromaDB for RAG retrieval."""
    from backend.services.book_indexer import index_all_books
    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(None, index_all_books)
        total   = sum(results.values())
        return {
            "success":      True,
            "total_chunks": total,
            "books":        results,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}")


# ============================================================================
# MISSING FAILURES ANALYSIS
# ============================================================================

@app.post(
    "/suggest-missing-failures",
    response_model = MissingFailuresResponse,
    tags           = ["AI Agents"],
    summary        = "Identify failure modes not yet covered in the FMEA",
    description    = (
        "Sends all documented functions and their existing failure modes to the LLM.\n\n"
        "The AI performs a completeness review and returns any significant failure modes "
        "that are typically expected in a rigorous FMEA but are not yet listed.\n\n"
        "If all important failure modes are already covered, `all_covered` will be `true`."
    ),
)
async def suggest_missing_failures(
    body      : MissingFailuresRequest,
    x_api_key : str | None = Header(default=None, description="UTC platform API key"),
):
    """
    Completeness review: identify missing failure modes across all FMEA functions.
    """
    api_key = _resolve_api_key(x_api_key)

    # Build the functions block for the prompt
    functions_text = ""
    for item in body.functions:
        failures_list = (
            "\n".join(f"    - {fm}" for fm in item.existing_failures)
            if item.existing_failures
            else "    (none documented)"
        )
        functions_text += f"Function: {item.function}\nExisting failure modes:\n{failures_list}\n---\n"

    system_prompt = (
        "You are a senior FMEA engineer performing a completeness review of an FMEA document.\n"
        "Your task: given the listed functions and their existing failure modes, identify any "
        "IMPORTANT failure modes that are MISSING — i.e., failure modes that a thorough FMEA "
        "would normally include for those functions but which are NOT yet listed.\n\n"
        "RULES:\n"
        "- Only suggest failure modes that represent genuine, significant engineering risks\n"
        "- Do NOT suggest trivial modifications, duplicates, or paraphrases of existing modes\n"
        "- If ALL important failure modes are already covered, set all_covered=true and return an empty suggestions list\n"
        "- Return ONLY a valid JSON object — no markdown fences, no preamble, no commentary\n\n"
        "Return format (strict):\n"
        "{\n"
        '  "all_covered": false,\n'
        '  "message": "brief summary sentence",\n'
        '  "suggestions": [\n'
        "    {\n"
        '      "function": "exact function name from the list above",\n'
        '      "failure_mode": "concise failure mode (max 120 chars)",\n'
        '      "effect": "effect on customer or system (max 120 chars)",\n'
        '      "cause": "root cause or failure mechanism (max 120 chars)",\n'
        '      "justification": "2-3 sentences explaining why this mode is a significant risk"\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    user_prompt = (
        f"Part / System: {body.part_name}\n\n"
        f"Current FMEA coverage:\n{functions_text}\n"
        "Identify any failure modes that are significant engineering risks but NOT yet listed above."
    )

    base_url   = os.getenv("LLM_BASE_URL", "https://ia.beta.utc.fr/api/v1")
    model_name = body.model_name or os.getenv("LLM_DEFAULT_MODEL", "RedHatAI/Qwen3.6-35B-A3B-NVFP4")

    def _repair_truncated_json(raw: str) -> str:
        """
        Attempt to recover a JSON object that was cut off by a token limit.
        Strategy: find all complete suggestion objects and reconstruct valid JSON.
        """
        import re as _re2
        # Find the outermost `{` to start building
        start = raw.find('{')
        if start == -1:
            raise ValueError("No JSON object found in response")
        raw = raw[start:]

        # Extract all_covered and message from the beginning
        all_covered = False
        message = ""
        m_ac = _re2.search(r'"all_covered"\s*:\s*(true|false)', raw, _re2.IGNORECASE)
        if m_ac:
            all_covered = m_ac.group(1).lower() == 'true'
        m_msg = _re2.search(r'"message"\s*:\s*"([^"]*?)"', raw)
        if m_msg:
            message = m_msg.group(1)

        # Extract all complete suggestion objects  { ... }
        # A complete suggestion has all 5 required string fields
        suggestions = []
        for obj_match in _re2.finditer(r'\{[^{}]*?"failure_mode"[^{}]*?\}', raw, _re2.DOTALL):
            try:
                obj = json.loads(obj_match.group(0))
                if obj.get('failure_mode'):  # must have at least this field
                    suggestions.append(obj)
            except Exception:
                pass

        return json.dumps({
            'all_covered': all_covered,
            'message': message,
            'suggestions': suggestions,
        })

    try:
        from openai import AsyncOpenAI
        import re as _re

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=3000,
        )
        raw = response.choices[0].message.content.strip()

        # Strip <think>...</think> blocks (reasoning models)
        raw = _re.sub(r"<think>.*?</think>", "", raw, flags=_re.DOTALL).strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")].strip()

        # Find the first { to discard any leading preamble text
        brace_pos = raw.find("{")
        if brace_pos > 0:
            raw = raw[brace_pos:]

        # Try standard parse; fall back to truncation recovery
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raw   = _repair_truncated_json(raw)
            data  = json.loads(raw)

        suggestions = [
            MissingFailureSuggestion(
                function     = s.get("function", ""),
                failure_mode = s.get("failure_mode", ""),
                effect       = s.get("effect", ""),
                cause        = s.get("cause", ""),
                justification= s.get("justification", ""),
            )
            for s in data.get("suggestions", [])
        ]

        return MissingFailuresResponse(
            all_covered = bool(data.get("all_covered", False)),
            message     = data.get("message", ""),
            suggestions = suggestions,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Missing-failures analysis failed: {exc}",
        )

