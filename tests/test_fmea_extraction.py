"""
Quick CLI test for the FMEA PDF extraction pipeline.

Usage:
    python test_fmea_extraction.py

Tests the full stack:
    PDF bytes → PyMuPDF text → Gemini structured output → FMEAHeaderExtraction + FMEADocument
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PDF_PATH = Path(
    "data/sample_documents/Example04231-RGPQP_V4_1_design fmea_DAB XR110.pdf"
)


def main():
    api_key = os.getenv("UTCLLM_API_KEY", "")
    if not api_key:
        print("ERROR: UTCLLM_API_KEY not set in .env file")
        return

    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found at {PDF_PATH}")
        return

    # ── Lazy imports (so missing packages fail here, not at module load) ──
    from src.preprocessing.fmea_pdf_extractor import (
        extract_fmea_from_pdf_bytes,
        extract_text_from_pdf,
        extract_fmea_header,
        header_to_fmea_document,
    )

    print(f"\n📄 PDF: {PDF_PATH.name}")
    print("=" * 60)

    # ── Step 1: read bytes ─────────────────────────────────────────────────
    with open(PDF_PATH, "rb") as f:
        file_bytes = f.read()
    print(f"File size : {len(file_bytes):,} bytes")

    # ── Step 2: extract text ────────────────────────────────────────────────
    print("\n[1/3] Extracting text with PyMuPDF...")
    raw_text = extract_text_from_pdf(file_bytes)
    print(f"       Extracted {len(raw_text):,} characters")
    print("       --- TEXT PREVIEW (first 400 chars) ---")
    print(raw_text[:400])
    print("       ...")

    # ── Step 3: LLM structured extraction ──────────────────────────────────
    print("\n[2/3] Sending to Gemini (structured output)...")
    header = extract_fmea_header(raw_text, api_key)

    print("\n✅ EXTRACTION RESULT")
    print("-" * 60)
    print(json.dumps(header.model_dump(), indent=2, ensure_ascii=False))

    # ── Step 4: convert to FMEADocument ────────────────────────────────────
    print("\n[3/3] Converting to FMEADocument skeleton...")
    doc = header_to_fmea_document(header, PDF_PATH.name)

    print(f"\n✅ FMEA DOCUMENT")
    print("-" * 60)
    print(f"Part Name : {doc.part_name}")
    print(f"Supplier  : {doc.supplier}")
    print(f"Functions : {len(doc.failures)} extracted")
    for i, record in enumerate(doc.failures, 1):
        print(f"  {i:02d}. {record.function}")

    print("\n[OK] Extraction complete — ready for Step 2 UI.")


if __name__ == "__main__":
    main()
