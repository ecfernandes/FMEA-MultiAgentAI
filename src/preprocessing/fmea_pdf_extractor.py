"""
LLM-powered PDF FMEA extraction module.

Pipeline:
    1. PyMuPDF  → extract raw text from every page of the PDF
    2. UTC LLM  → structured-output call (JSON) to parse FMEA table rows
    3. Pydantic → validate and return a typed FMEAFullExtraction model

The result can then be converted to a skeleton FMEADocument for the UI (Step 2).
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF  (pip install pymupdf)
from openai import OpenAI
from pydantic import BaseModel, Field

from src.preprocessing.fmea_schema import FMEADocument, FMEARecord


# ============================================================================
# PYDANTIC CONTRACT — "the shape the LLM must return"
# ============================================================================

class FMEAHeaderExtraction(BaseModel):
    """Structured metadata extracted from a supplier FMEA PDF."""

    part_name: str = Field(
        description="Component/part name (e.g. 'DAB Alpine XR110')"
    )
    supplier: str = Field(
        description="Supplier company name (e.g. 'Autoliv')"
    )
    functions: List[str] = Field(
        description=(
            "All unique function descriptions from the 'Function' column "
            "of the FMEA table, in document order."
        )
    )


# ---------------------------------------------------------------------------
# DEEP EXTRACTION — full FMEA row with SOD ratings
# ---------------------------------------------------------------------------

class FMEAFullExtraction(BaseModel):
    """Complete FMEA document: metadata + every table row (fully dynamic)."""

    part_name: str = Field(description="Component / part name.")
    supplier: str = Field(description="Supplier company name.")
    columns: List[str] = Field(
        default_factory=list,
        description="All column keys discovered from the document header row, in order.",
    )
    records: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "ALL rows of the FMEA table in document order. "
            "Each row is a dict keyed by the discovered column names."
        ),
    )


# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

# Legacy header-only prompt (kept for backward compatibility)
_SYSTEM_PROMPT = """\
You are an expert FMEA document analyst for the automotive industry
( supply chain, AIAG & VDA standards).

Your task is to extract structured metadata from a supplier FMEA PDF.
The document may follow different templates (AIAG, VDA, AIAG&VDA, proprietary).

Extract exactly three fields:

1. **part_name**
   - The name of the component, system, or part being analysed.
   - Look for labels: "Part Name", "Project", "Part No", "System", "Item",
     "Component", "Description", "Référence", "Désignation".
   - If the label is absent, infer from the document title or header area.

2. **supplier**
   - The company that authored the FMEA.
   - Look for: "Supplier", "Prepared by", "Author", "Company", "Fournisseur".
   - If not explicit, infer from email addresses in the header:
     e.g. "victor.vaillier@autoliv.com"  →  supplier = "Autoliv".
   - Check letterhead, logos, footer references.

3. **functions**
   - A list of ALL unique function descriptions from the FMEA table.
   - The column may be labelled: "Function", "Item Function", "Funktion",
     "Fonction", "Function / Requirements".
   - Each entry describes what the component is designed to do
     (typically starts with "To allow …", "To ensure …", "To resist …",
     "To provide …", "To prevent …", "To support …").
   - Extract EVERY distinct function. Do NOT merge, paraphrase, or skip.
   - Remove exact duplicates; preserve document order.

Rules:
- Be tolerant of varying column layouts, merged cells, rotated headers.
- Never invent data. If a field truly cannot be found, use "Unknown".
- Return ONLY a valid JSON object — no markdown fence, no commentary.
""".strip()


# Deep extraction prompt — captures every row of the FMEA table
_DEEP_SYSTEM_PROMPT = """\
You are an expert FMEA document analyst for the automotive industry
(AIAG, VDA, AIAG&VDA, and proprietary supplier templates).

Extract the COMPLETE contents of the FMEA table from the document below.

## STEP 1 — COLUMN DETECTION
Inspect the FIRST row of the pipe-separated table (the header row).
Map each column position to a snake_case key.
Use these MANDATORY aliases for the standard FMEA columns — these exact key
names are REQUIRED regardless of how the column is labelled in the document:

  Column header contains…                                → REQUIRED key
  ──────────────────────────────────────────────────────────────────────
  "function" / "item function" / "fonction" / "item"    → function
  "failure mode" / "mode de défaillance" / "defaillance" → failure_mode
  "effect" / "effet" / "potential effect"               → effect
  "cause" / "potential cause" / "mechanism"             → cause
  Severity column (S, S/C, Severity, SC, Gravité)       → severity
  Occurrence column (O, Occurrence, Fréquence)          → occurrence
  Detection column (D, Detection, Détection)            → detection
  ──────────────────────────────────────────────────────────────────────
IMPORTANT: Never use "item_function", "item", "fonction", or any variant
for the function column — always use exactly the key "function".

For any OTHER column not in the table above, create a short snake_case key:
  "Current Design Controls – Prevention"  → current_controls_prevention
  "Current Design Controls – Detection"   → current_controls_detection
  "Recommended Action(s)"                 → recommended_action
  "Responsibility & Target Date"          → responsibility_target_date
  "Completion Date"                       → completion_date
  "Action Taken"                          → action_taken
  "FMEA Number"                           → fmea_number
  "RPN"                                   → rpn

## STEP 2 — EXTRACT ALL ROWS
Using EXACTLY the keys determined in Step 1, extract EVERY data row.

## INPUT FORMAT
The document contains sections labelled [PAGE N - TABLE DATA (pipe-separated columns)].
Each line in those sections is ONE row of the original PDF table, with cells
separated by " | ". The first row of each table section is the header row.

## OUTPUT FORMAT
Return a single valid JSON object:

{
  "part_name": "<component / part name>",
  "supplier":  "<supplier company name>",
  "columns":   ["function", "failure_mode", "effect", "cause", "severity", "occurrence", "detection", ...],
  "records": [
    {"function": "To allow...", "failure_mode": "...", "effect": "...", "cause": "...", "severity": 7, ...},
    ...
  ]
}

## EXTRACTION RULES
1. part_name: look for "Part Name", "System", "Item", "Désignation", "Référence".
2. supplier: look for "Supplier", "Prepared by", "Company", "Fournisseur".
   If absent, infer from email domain (e.g. john@autoliv.com → "Autoliv").
3. columns: the COMPLETE ordered list of snake_case keys from the header row —
   "function" MUST always be first.
   CRITICAL: Include ALL columns present in the document header, even if every
   cell in that column is empty. Do NOT omit columns just because they have no data.
4. records: EVERY data row of the FMEA table — do NOT skip any.
   - severity, occurrence, detection: integer 1–10 or null.
   - All other fields: string or null.
   - Every record MUST contain ALL keys listed in "columns" — use null for empty cells.
   - CRITICAL: If a "function" cell is blank (merged-cell pattern in the PDF),
     copy the value from the most recent non-blank "function" cell above.
     Every single record MUST have a non-null "function" value.
5. ROW INTEGRITY: every field in a record must come from the SAME pipe-separated
   line. Never mix values from different lines.
6. Never invent data. Use null for absent optional values (not "Unknown").
7. TRANSLATION: All text fields in the output MUST be in English. If a cell
   contains text in any other language (Chinese, French, Portuguese, German,
   Japanese, Korean, etc.), translate it to English before inserting it in the
   record. Preserve the technical meaning exactly — do not summarise or omit.
   Part names, supplier names, codes, and numeric values are NOT translated.
8. Return ONLY the JSON object — no markdown fences, no commentary.
""".strip()


# ============================================================================
# STEP 1 — PDF TEXT EXTRACTION
# ============================================================================

# ─── Synthesis-sheet prompt — for numbered bullet-point AMDEC format ──────────
_SYNTHESIS_SYSTEM_PROMPT = """\
You are an FMEA data extraction specialist.

This document uses an AMDEC Synthesis Sheet format: each failure mode entry is a
numbered block with bullet points:

  N
  Failure Mode: <description>
  • Severity (S): <int>
  • Occurrence (O): <int>
  • Detection (D): <int>
  • RPN: <int>
  • Associated Actions:
    o Prevention: <text>
    o Detection: <text>

Extract EVERY numbered entry as one record.

Use the document header to populate the fields:
- part_name: use "Subsystem or Part" field ONLY. Do NOT use the Project name.
  Example: "Subsystem or Part : Wiper System Linkage" → part_name = "Wiper System Linkage".
  If absent, use the "Area of the study" field. Last resort: "Unknown".
- supplier: look for "Prepared by", "Company", "Supplier". If absent, use "Unknown".
- function: set to the SAME value as part_name for ALL records.

Return a single valid JSON object:
{{
  "part_name": "<project or part name>",
  "supplier": "<supplier or Unknown>",
  "columns": ["function", "failure_mode", "severity", "occurrence", "detection", "rpn", "prevention", "detection_action"],
  "records": [
    {{
      "function": "<subsystem name>",
      "failure_mode": "<full failure mode text>",
      "severity": <int or null>,
      "occurrence": <int or null>,
      "detection": <int or null>,
      "rpn": <int or null>,
      "prevention": "<prevention action text or null>",
      "detection_action": "<detection action text or null>"
    }},
    ...
  ]
}}

Rules:
- Extract EVERY numbered entry — do not skip any.
- rpn: use the value listed in the document (do NOT recalculate).
- prevention: full text after "o Prevention:".
- detection_action: full text after "o Detection:".
- If a field is absent, use null.
- TRANSLATION: All text fields MUST be in English. Translate any non-English
  text (Chinese, French, Portuguese, etc.) to English preserving technical
  meaning. Do not translate codes, part names, or numeric values.
- Return ONLY the JSON object — no markdown, no commentary.
""".strip()


def _is_synthesis_format(text: str) -> bool:
    """Detect AMDEC synthesis sheet / numbered bullet-point format."""
    return (
        "Failure Mode:" in text
        and "Severity (S):" in text
        and "•" in text
    )


# ─── Per-page prompt — synthesis format, pages 2+ (function name already known) ───
_SYNTHESIS_PAGE_PROMPT = """\
You are an FMEA data extraction specialist.

This page is a continuation of an AMDEC Synthesis Sheet.
Each entry is a numbered block:

  N
  Failure Mode: <description>
  • Severity (S): <int>
  • Occurrence (O): <int>
  • Detection (D): <int>
  • RPN: <int>
  • Associated Actions:
    o Prevention: <text>
    o Detection: <text>

The "function" value for ALL records on this page is: "{function_name}"

Extract EVERY numbered entry. Return ONLY a valid JSON object:
{{"records": [
  {{"function": "{function_name}", "failure_mode": "...", "severity": <int|null>, "occurrence": <int|null>, "detection": <int|null>, "rpn": <int|null>, "prevention": "...", "detection_action": "..."}},
  ...
]}}

Rules:
- Do NOT skip any numbered entry.
- rpn: use the value listed, do not recalculate.
- prevention / detection_action: full text after the label, or null if absent.
- Return ONLY the JSON — no markdown, no commentary.
""".strip()


# ─── Per-page prompt — used by extract_fmea_page for pages 2+ (table format) ───
_PAGE_SYSTEM_PROMPT = """\
You are an FMEA data extraction specialist.

You are given ONE PAGE of an FMEA table (pipe-separated columns).
The column keys have already been identified: {columns_json}

Extract ONLY the data rows visible on this page.
Rules:
- Use EXACTLY the column keys listed above — include ALL of them in every record, even if the value is null.
- Do NOT omit a key just because the cell is empty — use null instead.
- If the "function" cell is blank, fill it with the most recent non-blank function value (merged-cell logic).
- For severity / occurrence / detection: return an integer 1-10 or null.
- Skip header rows (rows whose cells repeat the column names themselves).
- If there are no data rows on this page, return an empty list.
- TRANSLATION: All text fields MUST be in English. Translate any non-English
  text (Chinese, French, Portuguese, etc.) to English preserving technical
  meaning. Do not translate codes, part names, or numeric values.

Return ONLY a valid JSON object — no markdown, no explanation:
{{"records": [{{"function": "...", "failure_mode": "...", ...}}, ...]}}
""".strip()


def _table_is_fmea_like(rows: list) -> bool:
    """Return True only if a table looks like FMEA tabular data (≥5 non-empty cols)."""
    if not rows:
        return False
    max_non_empty = max(
        sum(1 for c in row if c and str(c).strip()) for row in rows
    )
    return max_non_empty >= 5


def _extract_single_page_text(page, page_num: int) -> str:
    """Extract structured text from one PyMuPDF page object."""
    plain = page.get_text("text").strip()
    table_text = ""
    has_fmea_table = False
    try:
        tabs = page.find_tables()
        if tabs and tabs.tables:
            lines = []
            for ti, tab in enumerate(tabs.tables, start=1):
                rows = tab.extract()
                if not rows:
                    continue
                if _table_is_fmea_like(rows):
                    has_fmea_table = True
                lines.append(f"[TABLE {ti}]")
                for row in rows:
                    cells = [str(c).strip().replace("\n", " ") if c is not None else "" for c in row]
                    lines.append(" | ".join(cells))
            table_text = "\n".join(lines)
    except Exception:
        pass
    if table_text and has_fmea_table:
        # Proper FMEA table — include short metadata excerpt + table
        return (
            f"[PAGE {page_num} - METADATA]\n{plain[:500]}\n\n"
            f"[PAGE {page_num} - TABLE DATA (pipe-separated columns)]\n{table_text}"
        )
    # No proper FMEA table (only header forms, or no table at all)
    # Return full plain text so bullet-point / synthesis formats are not truncated
    return f"[PAGE {page_num}]\n{plain}"


def extract_pages_text(file_bytes: bytes) -> List[tuple]:
    """
    Extract text page-by-page from a PDF.
    Returns a list of (page_num: int, page_text: str) tuples (non-empty pages only).
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = _extract_single_page_text(page, page_num)
        if text.strip():
            pages.append((page_num, text))
    doc.close()
    return pages


_CANON_ALIASES_MAP: dict[str, list[str]] = {
    "function":     ["item_function", "item function", "fonction", "item", "component_function"],
    "failure_mode": ["failure mode", "potential_failure_mode", "mode_de_defaillance",
                     "defaillance", "falha", "modo_de_falha"],
    "effect":       ["potential_effect", "effet", "efeito"],
    "cause":        ["potential_cause", "root_cause", "causa"],
    # S / O / D numeric columns — many alias names across languages / templates
    "severity":     ["s", "g", "gravite", "gravité", "sc", "s/c", "sev",
                     "severity_s", "severity_rating", "note_g"],
    "occurrence":   ["o", "f", "freq", "frequence", "fréquence", "occ",
                     "occurrence_o", "note_f"],
    "detection":    ["d", "det", "nd", "non_detection", "non-detection",
                     "detectabilite", "détectabilité", "detection_d", "note_d"],
    "rpn":          ["c", "ipr", "ipn", "criticite", "criticité",
                     "risk_priority_number", "risk_priority"],
}


def _normalise_records(records: list, last_fn: Optional[str] = None) -> tuple:
    """
    Normalise alias keys → canonical names; propagate function down blank cells.
    Returns (normalised_records, last_fn).
    """
    for rec in records:
        # Alias → canonical (must run BEFORE SOD coercion so aliases become canonical names)
        for canonical, aliases in _CANON_ALIASES_MAP.items():
            if canonical not in rec or rec[canonical] is None:
                for alias in aliases:
                    if alias in rec and rec[alias] is not None:
                        rec[canonical] = rec.pop(alias)
                        break
        # SOD coercion — after alias normalisation
        for field in ("severity", "occurrence", "detection", "rpn"):
            val = rec.get(field)
            if val is not None:
                try:
                    rec[field] = int(val)
                except (ValueError, TypeError):
                    rec[field] = None
        # Function propagation
        fn = rec.get("function")
        if fn and str(fn).strip():
            last_fn = str(fn).strip()
        elif last_fn:
            rec["function"] = last_fn
    return records, last_fn


def extract_fmea_page(
    page_text: str,
    page_num: int,
    known_columns: List[str],
    api_key: str,
    model_name: Optional[str] = None,
    last_fn: Optional[str] = None,
) -> tuple:
    """
    Extract FMEA records from a single page.

    - First call (known_columns=[]): runs full column discovery via _DEEP_SYSTEM_PROMPT.
    - Subsequent calls: uses known_columns with the lighter _PAGE_SYSTEM_PROMPT.

    Returns:
        (columns, records, last_fn, part_name, supplier)
        part_name / supplier are None for pages 2+.
    """
    model = model_name or os.getenv("LLM_DEFAULT_MODEL", "qwen3527b-no-think")

    if not known_columns:
        # First page — full discovery; choose prompt based on format
        prompt = _SYNTHESIS_SYSTEM_PROMPT if _is_synthesis_format(page_text) else _DEEP_SYSTEM_PROMPT
        user_msg = (
            "Extract the complete FMEA table from the document below.\n\n"
            "---BEGIN PAGE TEXT---\n"
            f"{page_text}\n"
            "---END PAGE TEXT---"
        )
        data = _call_llm_for_json(prompt, user_msg, api_key, model, max_tokens=4096)
        columns   = data.get("columns", [])
        records   = data.get("records", [])
        part_name = data.get("part_name", "Unknown")
        supplier  = data.get("supplier", "Unknown")
    else:
        # Subsequent pages — choose prompt based on format
        import json as _json
        if _is_synthesis_format(page_text):
            # Synthesis format: pass the fixed function name so LLM doesn't invent one
            fn_name = last_fn or "Unknown function"
            system_msg = _SYNTHESIS_PAGE_PROMPT.replace("{function_name}", fn_name)
        else:
            # Always include "function" first so the LLM extracts it per-row.
            # "function" is stripped from colOrder for display only — it must still
            # appear in the extraction schema so each record carries its own function.
            cols_for_prompt = ["function"] + [c for c in known_columns if c != "function"]
            system_msg = _PAGE_SYSTEM_PROMPT.format(columns_json=_json.dumps(cols_for_prompt))
        user_msg = (
            "Extract data rows from this FMEA page.\n\n"
            "---BEGIN PAGE TEXT---\n"
            f"{page_text}\n"
            "---END PAGE TEXT---"
        )
        data      = _call_llm_for_json(system_msg, user_msg, api_key, model, max_tokens=2048)
        # Merge any NEW columns the LLM detected on this page that weren't in known_columns
        extra_cols = [c for c in data.get("columns", []) if c not in known_columns]
        columns    = known_columns + extra_cols
        records    = data.get("records", [])
        part_name  = None
        supplier   = None

    records, last_fn = _normalise_records(records, last_fn)
    return columns, records, last_fn, part_name, supplier


def _discover_columns_from_pages(
    pages: List[tuple],
    api_key: str,
    model_name: Optional[str] = None,
) -> tuple:
    """
    Scan up to 3 pages to find the most complete column list.
    Returns (best_columns, part_name, supplier, best_page_idx).
    """
    import json as _json
    model = model_name or os.getenv("LLM_DEFAULT_MODEL", "qwen3527b-no-think")
    best_columns: List[str] = []
    part_name = "Unknown"
    supplier  = "Unknown"
    best_page_idx = 0
    # Cache raw LLM response per page_num so the caller can reuse records
    # and avoid a second LLM call for these pages.
    cached_page_data: dict = {}

    # Only scan first 3 pages for speed — the header is always near the start
    # Auto-detect format from the combined text of the first few pages
    combined_sample = " ".join(t for _, t in pages[:3])
    discovery_prompt = _SYNTHESIS_SYSTEM_PROMPT if _is_synthesis_format(combined_sample) else _DEEP_SYSTEM_PROMPT

    for idx, (page_num, page_text) in enumerate(pages[:3]):
        user_msg = (
            "Extract the complete FMEA table from the document below.\n\n"
            "---BEGIN PAGE TEXT---\n"
            f"{page_text}\n"
            "---END PAGE TEXT---"
        )
        try:
            data = _call_llm_for_json(discovery_prompt, user_msg, api_key, model, max_tokens=4096)
            # Cache full response so the caller can skip re-extraction for this page
            cached_page_data[page_num] = data
            cols = data.get("columns", [])
            if len(cols) > len(best_columns):
                best_columns = cols
                best_page_idx = idx
                if data.get("part_name", "Unknown") != "Unknown":
                    part_name = data["part_name"]
                if data.get("supplier", "Unknown") != "Unknown":
                    supplier = data["supplier"]
            # If we already have a rich column set (≥8 cols), stop early
            if len(best_columns) >= 8:
                break
        except Exception:
            continue

    # "function" / its aliases are used for grouping — never expose as table columns
    _FN_ALIASES = {
        'function', 'item_function', 'item function', 'fonction',
        'item', 'component_function', 'component',
    }
    best_columns = [c for c in best_columns if c.lower() not in _FN_ALIASES]

    # Normalise S/O/D/RPN alias column names → canonical names so page prompts
    # always use the standard keys regardless of what the LLM returned.
    _normalised_cols: list[str] = []
    _seen: set[str] = set()
    for col in best_columns:
        canonical = col
        for canon, aliases in _CANON_ALIASES_MAP.items():
            if col.lower() in [a.lower() for a in aliases]:
                canonical = canon
                break
        if canonical not in _seen:
            _normalised_cols.append(canonical)
            _seen.add(canonical)
    best_columns = _normalised_cols

    return best_columns, part_name, supplier, best_page_idx, cached_page_data


def extract_text_from_pdf(file_bytes: bytes, max_chars: int = 60_000) -> str:
    """
    Extract text from a PDF using PyMuPDF with structured table detection.

    Strategy per page:
      1. Extract surrounding plain text (headers, metadata, footers).
      2. Detect tables with find_tables() and output each row as pipe-separated
         cells — this preserves column alignment so the LLM can reliably map
         each value to the correct FMEA field.
      3. Fall back to plain text if no tables are detected.

    The pipe-separated format ensures each FMEA row (function | failure_mode |
    effect | cause | S | O | D | …) remains on ONE logical line, preventing
    cross-row value mixing by the LLM.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    parts: list[str] = []
    total = 0

    for page_num, page in enumerate(doc, start=1):
        page_parts: list[str] = []

        # ── Plain text section (metadata, headers, footers) ──────────────────
        plain = page.get_text("text").strip()

        # ── Structured table extraction ───────────────────────────────────────
        table_text = ""
        try:
            tabs = page.find_tables()
            if tabs and tabs.tables:
                table_lines: list[str] = []
                for tab_idx, tab in enumerate(tabs.tables, start=1):
                    rows = tab.extract()
                    if not rows:
                        continue
                    table_lines.append(f"[TABLE {tab_idx}]")
                    for row in rows:
                        cells = [
                            str(c).strip().replace("\n", " ") if c is not None else ""
                            for c in row
                        ]
                        table_lines.append(" | ".join(cells))
                table_text = "\n".join(table_lines)
        except Exception:
            pass  # find_tables unavailable — fall back to plain text

        if table_text:
            # Include a small header excerpt for metadata context, then the table
            header_excerpt = plain[:500] if plain else ""
            page_parts.append(
                f"[PAGE {page_num} - METADATA]\n{header_excerpt}\n\n"
                f"[PAGE {page_num} - TABLE DATA (pipe-separated columns)]\n{table_text}"
            )
        else:
            page_parts.append(f"[PAGE {page_num}]\n{plain}")

        chunk = "\n\n".join(page_parts)
        parts.append(chunk)
        total += len(chunk)
        if total >= max_chars:
            break

    doc.close()

    raw = "\n\n".join(parts)[:max_chars]

    if not raw.strip():
        raise ValueError(
            "No readable text found in the PDF. "
            "The file may consist of scanned images — OCR is required."
        )

    return raw


# ============================================================================
# STEP 2 — LLM STRUCTURED EXTRACTION
# ============================================================================

def _call_llm_for_json(
    system_msg: str,
    user_msg: str,
    api_key: str,
    model: str,
    max_tokens: int = 8192,
    timeout: float = 180.0,
) -> dict:
    """Shared helper: call the UTC LLM platform and return parsed JSON."""
    base_url = os.getenv("LLM_BASE_URL", "https://ia.beta.utc.fr/api/v1")
    _timeout = float(os.getenv("LLM_REQUEST_TIMEOUT", str(timeout)))
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=_timeout, max_retries=1)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.0,
        max_tokens=max_tokens,
    )

    raw = response.choices[0].message.content.strip()

    # Strip <think>...</think> blocks emitted by reasoning models (Magistral, Olmo Think, etc.)
    import re as _re
    raw = _re.sub(r"<think>.*?</think>", "", raw, flags=_re.DOTALL).strip()

    # Strip markdown code fences if the model wraps the JSON
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    # Remove trailing fence if present
    if raw.endswith("```"):
        raw = raw[: raw.rfind("```")].strip()

    return json.loads(raw)


def extract_fmea_header(raw_text: str, api_key: str, model_name: str | None = None) -> FMEAHeaderExtraction:
    """
    Legacy header-only extraction (part_name, supplier, functions list).
    Kept for backward compatibility with api.py and test suites.
    """
    model = model_name or os.getenv("LLM_DEFAULT_MODEL", "qwen3527b-no-think")

    system_msg = _SYSTEM_PROMPT + (
        "\n\nIMPORTANT: Return ONLY a valid JSON object with exactly these keys: "
        '"part_name" (string), "supplier" (string), "functions" (array of strings). '
        "No markdown, no extra text."
    )
    user_msg = (
        "Extract the FMEA header data from the following PDF text.\n\n"
        "---BEGIN PDF TEXT---\n"
        f"{raw_text}\n"
        "---END PDF TEXT---"
    )

    data = _call_llm_for_json(system_msg, user_msg, api_key, model, max_tokens=1024)
    return FMEAHeaderExtraction(**data)


def extract_fmea_full(
    raw_text: str,
    api_key: str,
    model_name: str | None = None,
) -> FMEAFullExtraction:
    """
    Deep extraction: parses EVERY row of the FMEA table including all
    SOD ratings, failure modes, effects, and causes.

    Args:
        raw_text:   Output of extract_text_from_pdf().
        api_key:    UTC platform API key.
        model_name: Override the LLM model id.

    Returns:
        FMEAFullExtraction with validated records.

    Raises:
        json.JSONDecodeError: Malformed JSON from the model.
        pydantic.ValidationError: Schema mismatch.
    """
    model = model_name or os.getenv("LLM_DEFAULT_MODEL", "qwen3527b-no-think")

    user_msg = (
        "Extract the complete FMEA table from the document below.\n\n"
        "---BEGIN PDF TEXT---\n"
        f"{raw_text}\n"
        "---END PDF TEXT---"
    )

    # Allow enough output for large FMEAs (50+ rows) while staying within model limits
    data = _call_llm_for_json(
        _DEEP_SYSTEM_PROMPT, user_msg, api_key, model, max_tokens=4096
    )

    # Normalise SOD fields to int / None before Pydantic validation
    for rec in data.get("records", []):
        for field in ("severity", "occurrence", "detection"):
            val = rec.get(field)
            if val is not None:
                try:
                    rec[field] = int(val)
                except (ValueError, TypeError):
                    rec[field] = None

    # Pre-processing: normalise alias keys to canonical names in every record
    # (e.g. "item_function" → "function") so propagation and lookup work correctly
    _CANON_ALIASES: dict[str, list[str]] = {
        "function":     ["item_function", "item function", "fonction", "item",
                         "component_function"],
        "failure_mode": ["failure mode", "potential_failure_mode",
                         "mode_de_defaillance", "defaillance", "falha", "modo_de_falha"],
        "effect":       ["potential_effect", "effet", "efeito"],
        "cause":        ["potential_cause", "root_cause", "causa"],
    }
    for rec in data.get("records", []):
        for canonical, aliases in _CANON_ALIASES.items():
            if canonical not in rec or rec[canonical] is None:
                for alias in aliases:
                    if alias in rec and rec[alias] is not None:
                        rec[canonical] = rec.pop(alias)
                        break

    # Post-processing: propagate "function" down to rows where it is blank
    # (handles merged-cell PDFs where only the first row of a group has the value)
    last_fn: Optional[str] = None
    for rec in data.get("records", []):
        fn = rec.get("function")
        if fn and str(fn).strip():
            last_fn = str(fn).strip()
        elif last_fn:
            rec["function"] = last_fn

    return FMEAFullExtraction(**data)


# ============================================================================
# STEP 3 — CONVERT TO FMEA DOCUMENT
# ============================================================================

def _safe_int(value) -> Optional[int]:
    """Coerce a value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def full_extraction_to_fmea_document(
    extraction: FMEAFullExtraction,
    source_file: str,
) -> FMEADocument:
    """
    Convert a FMEAFullExtraction into a fully populated FMEADocument.

    Each record's RPN is computed automatically via models.calculate_rpn so
    that the coloured badges in the UI render correctly from the first load.

    Args:
        extraction:  Deep extraction result from extract_fmea_full().
        source_file: Original filename (for traceability).

    Returns:
        FMEADocument with one FMEARecord per row, RPN pre-calculated.
    """
    # Import here to avoid a hard dependency at module load time
    try:
        from models import calculate_rpn  # type: ignore[import]
    except ImportError:
        def calculate_rpn(s, o, d):  # type: ignore[misc]
            try:
                return int(s) * int(o) * int(d) if s and o and d else None
            except Exception:
                return None

    records: List[FMEARecord] = []

    # Keys handled as explicit FMEARecord constructor parameters — must not appear in extra_fields
    _CORE_KEYS = frozenset({"function", "failure_mode", "effect", "cause",
                            "severity", "occurrence", "detection", "rpn"})

    # Alternative key names the LLM might use for each core field
    _ALIASES: dict = {
        "function":     ["function", "item_function", "item function", "fonction",
                         "item", "component_function", "funkcja"],
        "failure_mode": ["failure_mode", "failure mode", "potential_failure_mode",
                         "mode_de_defaillance", "defaillance", "falha", "modo_de_falha"],
        "effect":       ["effect", "potential_effect", "effet", "efeito"],
        "cause":        ["cause", "potential_cause", "root_cause", "causa"],
    }

    def _get(row: dict, field: str) -> Optional[str]:
        """Look up a field trying the canonical name then known aliases."""
        for alias in _ALIASES.get(field, [field]):
            val = row.get(alias)
            if val is not None and str(val).strip():
                return str(val).strip()
        return None

    # Safety propagation: fill blank "function" cells from the row above
    # (applies whether extraction came from extract_fmea_full or was built directly)
    last_fn: Optional[str] = None
    for row in extraction.records:
        fn = _get(row, "function")
        if fn:
            last_fn = fn
        elif last_fn:
            row["function"] = last_fn  # type: ignore[index]

    for row in extraction.records:
        s   = _safe_int(row.get("severity"))
        o   = _safe_int(row.get("occurrence"))
        d   = _safe_int(row.get("detection"))
        rpn = calculate_rpn(s, o, d)

        # Build a normalised row dict: remap alias keys to canonical names
        # so extra_fields doesn't contain e.g. "item_function" alongside function=None
        normalised_row: dict = {}
        used_keys: set = set()
        for field, aliases in _ALIASES.items():
            for alias in aliases:
                if alias in row and row[alias] is not None:
                    normalised_row[field] = row[alias]
                    used_keys.add(alias)
                    break
        # Keep remaining (non-aliased) keys
        for k, v in row.items():
            if k not in used_keys and k not in normalised_row:
                normalised_row[k] = v

        # Everything outside the core set goes to extra_fields
        extra = {k: v for k, v in normalised_row.items() if k not in _CORE_KEYS}

        records.append(
            FMEARecord(
                component    = extraction.part_name,
                function     = _get(row, "function") or "Unknown function",
                failure_mode = _get(row, "failure_mode") or "",
                effect       = _get(row, "effect") or "",
                cause        = _get(row, "cause") or "",
                severity     = s,
                occurrence   = o,
                detection    = d,
                rpn          = rpn,
                extra_fields = extra,
                _source_file = source_file,
            )
        )

    return FMEADocument(
        failures=records,
        source_file=source_file,
        extraction_date=datetime.now().isoformat(),
        part_name=extraction.part_name,
        supplier=extraction.supplier,
    )


def header_to_fmea_document(
    header: FMEAHeaderExtraction,
    source_file: str,
) -> FMEADocument:
    """
    Legacy conversion: skeleton FMEADocument from header-only extraction.
    Each extracted function becomes one empty FMEARecord.
    Kept for backward compatibility.
    """
    records = [
        FMEARecord(
            component=header.part_name,
            function=func,
            failure_mode="",
            effect="",
            cause="",
            severity=None,
            occurrence=None,
            detection=None,
            _source_file=source_file,
        )
        for func in header.functions
    ]

    return FMEADocument(
        failures=records,
        source_file=source_file,
        extraction_date=datetime.now().isoformat(),
        part_name=header.part_name,
        supplier=header.supplier,
    )


# ============================================================================
# PUBLIC CONVENIENCE — used by both FastAPI and Streamlit
# ============================================================================

def extract_fmea_from_pdf_bytes(
    file_bytes: bytes,
    source_filename: str,
    api_key: str | None = None,
    model_name: str | None = None,
) -> FMEADocument:
    """
    Full pipeline: PDF bytes → fully populated FMEADocument.

    Performs deep extraction (all table rows with SOD values) and pre-calculates
    RPN for every record so the UI renders coloured badges immediately.

    Args:
        file_bytes:      Raw PDF bytes.
        source_filename: Original filename (displayed in the UI banner).
        api_key:         UTC platform API key (or None to read from env).
        model_name:      LLM model id (or None to use LLM_DEFAULT_MODEL env var).

    Returns:
        FMEADocument with every row populated and RPN calculated.
    """
    key = api_key or os.getenv("UTCLLM_API_KEY", "")
    if not key:
        raise ValueError("No API key provided and UTCLLM_API_KEY is not set.")

    raw_text = extract_text_from_pdf(file_bytes)

    extraction = extract_fmea_full(raw_text, key, model_name=model_name)
    return full_extraction_to_fmea_document(extraction, source_filename)

