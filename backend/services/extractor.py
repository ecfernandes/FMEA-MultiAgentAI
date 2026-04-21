"""
backend/services/extractor.py
------------------------------
Stateless extraction service — converts uploaded files (PDF or Excel) into
validated FMEADocumentSchema objects ready to be returned by the FastAPI layer.

This service is the async wrapper around the existing extraction modules
in src/preprocessing/ so they can be called from FastAPI without modification.

Pipeline:
    UploadFile bytes
        ├─ .xlsx / .xls  → FMEAExtractorV2.extract_from_excel()
        └─ .pdf          → extract_fmea_from_pdf_bytes()
                               └─ extract_fmea_full()  [LLM deep extraction]
                               └─ full_extraction_to_fmea_document()
    FMEADocument (dataclass)
        └─ _to_schema()  → FMEADocumentSchema (Pydantic)
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Optional

from backend.schemas import FMEADocumentSchema, FMEARecordSchema


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _compute_rpn(s, o, d) -> Optional[int]:
    """Calculate S × O × D, returning None if any value is missing."""
    try:
        return int(s) * int(o) * int(d) if s and o and d else None
    except (ValueError, TypeError):
        return None


def _dataclass_record_to_schema(rec) -> FMEARecordSchema:
    """Convert a src FMEARecord dataclass to a Pydantic FMEARecordSchema.

    Core fields are mapped explicitly; all document-specific columns stored
    in rec.extra_fields are unpacked directly into the schema (extra='allow').
    Core keys are removed from extra to avoid 'multiple values' errors.
    """
    _EXPLICIT_KEYS = frozenset({
        "component", "function", "failure_mode", "effect", "cause",
        "severity", "occurrence", "detection", "rpn",
        "source_file", "sheet_name", "row_number",
    })
    rpn   = rec.rpn or _compute_rpn(rec.severity, rec.occurrence, rec.detection)
    raw   = getattr(rec, "extra_fields", {}) or {}
    extra = {k: v for k, v in raw.items() if k not in _EXPLICIT_KEYS}
    return FMEARecordSchema(
        component    = rec.component or "Unknown",
        function     = rec.function,
        failure_mode = rec.failure_mode or "",
        effect       = rec.effect or "",
        cause        = rec.cause or "",
        severity     = rec.severity,
        occurrence   = rec.occurrence,
        detection    = rec.detection,
        rpn          = rpn,
        source_file  = rec._source_file,
        sheet_name   = rec._sheet_name,
        row_number   = rec._row_number,
        **extra,
    )


def _fmea_document_to_schema(doc) -> FMEADocumentSchema:
    """Convert src FMEADocument dataclass → validated FMEADocumentSchema."""
    return FMEADocumentSchema(
        part_name       = doc.part_name or "Unknown Part",
        supplier        = doc.supplier or "Unknown",
        source_file     = doc.source_file or "",
        extraction_date = doc.extraction_date or datetime.now().isoformat(),
        project_name    = getattr(doc, "project_name", None),
        team            = getattr(doc, "team", None),
        phase           = getattr(doc, "phase", None),
        records         = [_dataclass_record_to_schema(r) for r in doc.failures],
    )


# ============================================================================
# PUBLIC EXTRACTION FUNCTIONS (async-safe via run_in_executor)
# ============================================================================

def _excel_to_markdown(file_bytes: bytes, filename: str) -> str:
    """
    Convert an Excel file to a markdown-style text representation suitable for
    LLM ingestion. Scans all sheets and all skiprow offsets (0-15) to find where
    the actual table data begins.  Returns the raw text to be sent to the LLM.
    """
    import io
    import pandas as pd
    import warnings

    warnings.filterwarnings("ignore")
    buf = io.BytesIO(file_bytes)
    try:
        xl = pd.ExcelFile(buf)
    except Exception as exc:
        return f"[Excel could not be opened: {exc}]"

    lines: list[str] = [f"[EXCEL FILE: {filename}]", ""]
    found_any = False

    for sheet in xl.sheet_names:
        best_df = None
        best_skip = 0
        # Try to find the header row by scanning for the skiprows offset that
        # yields the most non-unnamed columns with ≥ 4 recognisable headers.
        for skip in range(16):
            try:
                df = pd.read_excel(buf, sheet_name=sheet, skiprows=skip, nrows=200)
                named = [c for c in df.columns if "Unnamed" not in str(c)]
                if len(named) >= 4:
                    best_df = df
                    best_skip = skip
                    break
            except Exception:
                continue

        if best_df is None:
            continue

        found_any = True
        lines.append(f"[SHEET: {sheet}  (header detected at row {best_skip})]")

        # Build pipe-separated table — header row first
        headers = [str(c).strip().replace("\n", " ") for c in best_df.columns]
        lines.append(" | ".join(headers))

        # Data rows — forward-fill blank cells in first column (merged-cell pattern)
        best_df = best_df.ffill(axis=0)
        for _, row in best_df.iterrows():
            cells = []
            for v in row:
                s = str(v).strip().replace("\n", " ")
                cells.append("" if s in ("nan", "None") else s)
            # Skip fully-empty rows
            if any(cells):
                lines.append(" | ".join(cells))
        lines.append("")

    if not found_any:
        lines.append("[No structured table found in this Excel file]")

    return "\n".join(lines)


async def extract_from_excel_bytes(
    file_bytes: bytes,
    filename: str,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    on_llm_fallback=None,
) -> FMEADocumentSchema:
    """
    Extract FMEA data from Excel bytes and return a validated schema object.

    Strategy:
      1. Try rule-based FMEAExtractorV2 (fast, 0 tokens).
      2. If that returns nothing, fall back to the UTC LLM (same path as PDF).

    Runs synchronous code in a thread-pool executor to avoid blocking the event loop.

    Args:
        file_bytes:       Raw Excel bytes.
        filename:         Original filename.
        api_key:          UTC platform API key (required for LLM fallback).
        model_name:       LLM model override.
        on_llm_fallback:  Optional async callable invoked when LLM path is taken
                          (used by the streaming endpoint to send a status event).
    """
    import io
    from src.preprocessing.fmea_extractor_v2 import FMEAExtractorV2

    # ── 1. Rule-based attempt ──────────────────────────────────────────────
    def _sync_rule_based():
        extractor = FMEAExtractorV2()
        file_obj  = io.BytesIO(file_bytes)
        file_obj.name = filename
        return extractor.extract_fmea_document(file_obj, filename)

    loop = asyncio.get_event_loop()
    doc  = await loop.run_in_executor(None, _sync_rule_based)

    if doc is not None and doc.failures:
        return _fmea_document_to_schema(doc)

    # ── 2. LLM fallback ───────────────────────────────────────────────────
    if on_llm_fallback:
        await on_llm_fallback()

    if not api_key:
        api_key = os.getenv("UTCLLM_API_KEY", "")

    _model = model_name or os.getenv("LLM_DEFAULT_MODEL", "qwen3527b-no-think")

    def _sync_llm():
        from src.preprocessing.fmea_pdf_extractor import (
            _call_llm_for_json,
            _DEEP_SYSTEM_PROMPT,
            _normalise_records,
            full_extraction_to_fmea_document,
            FMEAFullExtraction,
        )
        excel_text = _excel_to_markdown(file_bytes, filename)
        user_msg = (
            "Extract the complete FMEA table from the Excel document below.\n\n"
            "---BEGIN EXCEL CONTENT---\n"
            f"{excel_text}\n"
            "---END EXCEL CONTENT---"
        )
        data = _call_llm_for_json(_DEEP_SYSTEM_PROMPT, user_msg, api_key, _model, max_tokens=6144)

        # Normalise SOD fields
        for rec in data.get("records", []):
            for field in ("severity", "occurrence", "detection", "rpn"):
                val = rec.get(field)
                if val is not None:
                    try:
                        rec[field] = int(val)
                    except (ValueError, TypeError):
                        rec[field] = None

        records, _ = _normalise_records(data.get("records", []), None)
        extraction = FMEAFullExtraction(
            part_name = data.get("part_name") or "Unknown",
            supplier  = data.get("supplier") or "Unknown",
            columns   = data.get("columns", []),
            records   = records,
        )
        fmea_doc = full_extraction_to_fmea_document(extraction, filename)
        return fmea_doc, data.get("columns", [])

    try:
        fmea_doc, columns = await loop.run_in_executor(None, _sync_llm)
        schema = _fmea_document_to_schema(fmea_doc)
        # Attach discovered columns so the streaming layer can forward them
        schema.__dict__["_excel_columns"] = columns
        return schema
    except Exception as exc:
        # LLM also failed — return minimal placeholder
        from src.preprocessing.fmea_schema import FMEADocument, FMEARecord
        doc = FMEADocument(
            failures=[FMEARecord(
                component    = "Unknown",
                function     = "Function — to be analysed",
                failure_mode = "",
                effect       = "",
                cause        = "",
                _source_file = filename,
            )],
            source_file     = filename,
            extraction_date = datetime.now().isoformat(),
            part_name       = f"Excel — extraction failed: {exc}",
            supplier        = "Unknown",
        )
        return _fmea_document_to_schema(doc)


async def extract_from_pdf_bytes(
    file_bytes: bytes,
    filename: str,
    api_key: str,
    model_name: Optional[str] = None,
) -> FMEADocumentSchema:
    """
    Extract FMEA data from PDF bytes via LLM deep extraction.

    Calls the synchronous pdf extractor in a thread-pool executor.

    Args:
        file_bytes: Raw PDF bytes from the uploaded file.
        filename:   Original filename for traceability.
        api_key:    UTC platform API key.
        model_name: Override LLM model id.
    """
    from src.preprocessing.fmea_pdf_extractor import extract_fmea_from_pdf_bytes

    _model = model_name or os.getenv("LLM_DEFAULT_MODEL", "qwen3527b-no-think")

    def _sync_extract():
        return extract_fmea_from_pdf_bytes(
            file_bytes      = file_bytes,
            source_filename = filename,
            api_key         = api_key,
            model_name      = _model,
        )

    loop = asyncio.get_event_loop()
    doc  = await loop.run_in_executor(None, _sync_extract)

    return _fmea_document_to_schema(doc)


async def extract_file(
    file_bytes: bytes,
    filename: str,
    api_key: str,
    model_name: Optional[str] = None,
) -> FMEADocumentSchema:
    """
    Unified entry point — dispatches to Excel or PDF extractor based on filename.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename:   Original filename (used to determine file type).
        api_key:    UTC platform API key (required for PDF extraction).
        model_name: Optional LLM model override.

    Returns:
        FMEADocumentSchema ready to be serialised and returned by the API.
    """
    lower = filename.lower()

    if lower.endswith((".xlsx", ".xls")):
        return await extract_from_excel_bytes(file_bytes, filename, api_key, model_name)

    if lower.endswith(".pdf"):
        return await extract_from_pdf_bytes(file_bytes, filename, api_key, model_name)

    raise ValueError(
        f"Unsupported file type: '{filename}'. "
        "Accepted formats: .pdf, .xlsx, .xls"
    )
