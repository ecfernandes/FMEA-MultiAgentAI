"""
backend/services/book_indexer.py
---------------------------------
Indexes reference PDFs into a local persistent embedding index so that
specialist agents can retrieve relevant excerpts at query time (RAG).

Design:
  - PyMuPDF extracts text page-by-page.
  - SentenceTransformer generates embeddings.
  - Books and standards are stored in separate local indexes.
  - OCR is attempted only when a page has no text layer and RapidOCR is available.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import numpy as np
from sentence_transformers import SentenceTransformer

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    RapidOCR = None


# ── Paths ────────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent.parent
BOOKS_PATH = _ROOT / "Books"
STANDARDS_PATH = _ROOT / "Standards"
VECTOR_STORE = _ROOT / "data" / "vector_store"
BOOKS_INDEX_DIR = VECTOR_STORE / "books"
STANDARDS_INDEX_DIR = VECTOR_STORE / "standards"
CHUNK_MAX_CHARS = 1500
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _chunk_page(text: str, max_chars: int = CHUNK_MAX_CHARS) -> list[str]:
    """Split page text into chunks of at most max_chars, breaking on paragraphs."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current = ""
    for para in re.split(r"\n{2,}", text):
        para = para.strip()
        if not para:
            continue
        if current and len(current) + len(para) + 2 > max_chars:
            chunks.append(current.strip())
            current = para
        else:
            current = (current + "\n\n" + para).strip() if current else para
    if current:
        chunks.append(current.strip())
    return chunks or [text[:max_chars]]


_model_singleton: SentenceTransformer | None = None
_ocr_singleton: Any | None = None


def _embedding_model() -> SentenceTransformer:
    global _model_singleton
    if _model_singleton is None:
        _model_singleton = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model_singleton


def _ocr_engine() -> Any | None:
    global _ocr_singleton
    if RapidOCR is None:
        return None
    if _ocr_singleton is None:
        _ocr_singleton = RapidOCR()
    return _ocr_singleton


def _index_dir_for(source_type: str) -> Path:
    return STANDARDS_INDEX_DIR if source_type == "standard" else BOOKS_INDEX_DIR


def _rows_path(source_type: str) -> Path:
    return _index_dir_for(source_type) / "rows.json"


def _embeddings_path(source_type: str) -> Path:
    return _index_dir_for(source_type) / "embeddings.npy"


def _ensure_index_dir(source_type: str) -> None:
    _index_dir_for(source_type).mkdir(parents=True, exist_ok=True)


def _empty_embeddings() -> np.ndarray:
    return np.empty((0, 384), dtype=np.float32)


def _load_index(source_type: str) -> tuple[list[dict[str, Any]], np.ndarray]:
    _ensure_index_dir(source_type)
    rows_file = _rows_path(source_type)
    emb_file = _embeddings_path(source_type)
    rows: list[dict[str, Any]] = []
    embeddings = _empty_embeddings()

    if rows_file.exists():
        rows = json.loads(rows_file.read_text(encoding="utf-8"))
    if emb_file.exists():
        embeddings = np.load(emb_file)
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
    if rows and len(rows) != len(embeddings):
        raise ValueError(f"Index row/embedding mismatch for {source_type}")
    return rows, embeddings.astype(np.float32, copy=False)


def _save_index(source_type: str, rows: list[dict[str, Any]], embeddings: np.ndarray) -> None:
    _ensure_index_dir(source_type)
    _rows_path(source_type).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    np.save(_embeddings_path(source_type), embeddings.astype(np.float32, copy=False))


def _resolve_pdf_path(filename: str, source_type: str | None = None) -> Path | None:
    roots = {
        "book": (BOOKS_PATH,),
        "standard": (STANDARDS_PATH,),
    }.get(source_type, (BOOKS_PATH, STANDARDS_PATH))
    for root in roots:
        candidate = root / filename
        if candidate.exists():
            return candidate
    return None


def _source_type_for(filename: str) -> str:
    path = _resolve_pdf_path(filename)
    if path is None:
        return "unknown"
    return "standard" if path.parent == STANDARDS_PATH else "book"


def _extract_text_with_optional_ocr(page: fitz.Page) -> tuple[str, bool]:
    text = page.get_text("text").strip()
    if text:
        return text, False

    ocr = _ocr_engine()
    if ocr is None:
        return "", False

    pix = page.get_pixmap(dpi=200, alpha=False)
    image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    result, _ = ocr(image)
    if not result:
        return "", True

    ocr_text = "\n".join(item[1] for item in result if len(item) > 1 and item[1]).strip()
    return ocr_text, True


def _embed_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return _empty_embeddings()
    model = _embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return embeddings.astype(np.float32, copy=False)


def _cosine_rank(query_embedding: np.ndarray, embeddings: np.ndarray, n_results: int) -> np.ndarray:
    if embeddings.size == 0:
        return np.array([], dtype=np.int64)
    scores = embeddings @ query_embedding
    order = np.argsort(scores)[::-1]
    return order[:n_results]


def _document_rows(rows: list[dict[str, Any]], book_filename: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("book_file") == book_filename]


def diagnose_document_extraction(book_filename: str, source_type: str | None = None) -> dict[str, Any]:
    path = _resolve_pdf_path(book_filename, source_type)
    if path is None or not path.exists():
        return {"book_file": book_filename, "exists": False}

    doc = fitz.open(str(path))
    page_count = doc.page_count
    nonempty_pages = 0
    total_chars = 0
    ocr_pages = 0
    samples: list[dict[str, Any]] = []

    for page_num, page in enumerate(doc, start=1):
        text, used_ocr = _extract_text_with_optional_ocr(page)
        if text:
            nonempty_pages += 1
            total_chars += len(text)
            if used_ocr:
                ocr_pages += 1
            if len(samples) < 3:
                samples.append(
                    {
                        "page": page_num,
                        "chars": len(text),
                        "used_ocr": used_ocr,
                        "snippet": text[:180].replace("\n", " "),
                    }
                )

    doc.close()
    return {
        "book_file": book_filename,
        "exists": True,
        "source_type": source_type or _source_type_for(book_filename),
        "pages": page_count,
        "nonempty_pages": nonempty_pages,
        "total_chars": total_chars,
        "ocr_pages": ocr_pages,
        "ocr_available": _ocr_engine() is not None,
        "samples": samples,
    }


# ============================================================================
# PUBLIC API
# ============================================================================

def index_book(book_filename: str, index_data=None, source_type: str | None = None) -> int:
    """Index one PDF into the local vector index."""
    resolved_source_type = source_type or _source_type_for(book_filename)
    path = _resolve_pdf_path(book_filename, resolved_source_type)
    if path is None or not path.exists():
        return 0

    if index_data is None:
        rows, embeddings = _load_index(resolved_source_type)
        index_data = [rows, embeddings]

    rows = index_data[0]
    embeddings = index_data[1]
    known_ids = {row["chunk_id"] for row in rows}

    doc = fitz.open(str(path))
    new_rows: list[dict[str, Any]] = []
    new_texts: list[str] = []

    for page_num, page in enumerate(doc, start=1):
        text, used_ocr = _extract_text_with_optional_ocr(page)
        if not text:
            continue
        for chunk_index, chunk in enumerate(_chunk_page(text)):
            chunk_id = f"{book_filename}::p{page_num}::c{chunk_index}"
            if chunk_id in known_ids:
                continue
            new_rows.append(
                {
                    "book_file": book_filename,
                    "page_num": page_num,
                    "chunk_index": chunk_index,
                    "chunk_id": chunk_id,
                    "source_type": resolved_source_type,
                    "used_ocr": used_ocr,
                    "text": chunk,
                }
            )
            new_texts.append(chunk)

    doc.close()

    if not new_rows:
        return 0

    new_embeddings = _embed_texts(new_texts)
    rows.extend(new_rows)
    if embeddings.size == 0:
        embeddings = new_embeddings
    else:
        embeddings = np.vstack([embeddings, new_embeddings]).astype(np.float32, copy=False)

    index_data[1] = embeddings
    if len(index_data) > 2:
        index_data[2] = True
    return len(new_rows)


def index_all_books(books_path: str | None = None) -> dict[str, int]:
    """Index every PDF in the Books/ folder."""
    root = Path(books_path) if books_path else BOOKS_PATH
    rows, embeddings = _load_index("book")
    index_data = [rows, embeddings, False]
    pdfs = sorted(root.glob("*.pdf"))
    total = len(pdfs)
    results: dict[str, int] = {}
    for idx, pdf in enumerate(pdfs, start=1):
        print(f"[RAG] ({idx}/{total}) Indexing {pdf.name} ...", flush=True)
        try:
            n = index_book(pdf.name, index_data=index_data, source_type="book")
            results[pdf.name] = n
            print(f"[RAG]   -> {n} chunks added", flush=True)
        except Exception as exc:
            print(f"[RAG]   -> ERROR: {exc}", flush=True)
            results[pdf.name] = 0
    if index_data[2]:
        _save_index("book", index_data[0], index_data[1])
    print(f"[RAG] Done. Total books: {total}", flush=True)
    return results


def index_all_standards(standards_path: str | None = None) -> dict[str, int]:
    """Index every PDF in the Standards/ folder."""
    root = Path(standards_path) if standards_path else STANDARDS_PATH
    rows, embeddings = _load_index("standard")
    index_data = [rows, embeddings, False]
    pdfs = sorted(root.glob("*.pdf"))
    total = len(pdfs)
    results: dict[str, int] = {}
    for idx, pdf in enumerate(pdfs, start=1):
        print(f"[RAG] ({idx}/{total}) Indexing standard {pdf.name} ...", flush=True)
        try:
            n = index_book(pdf.name, index_data=index_data, source_type="standard")
            results[pdf.name] = n
            print(f"[RAG]   -> {n} chunks added", flush=True)
        except Exception as exc:
            print(f"[RAG]   -> ERROR: {exc}", flush=True)
            results[pdf.name] = 0
    if index_data[2]:
        _save_index("standard", index_data[0], index_data[1])
    print(f"[RAG] Done. Total standards: {total}", flush=True)
    return results


def retrieve_book_context(query: str, book_filename: str, n_results: int = 3) -> list[str]:
    """Retrieve the top-n most relevant chunks from a specific document."""
    rows = retrieve_book_context_with_metadata(query, book_filename, n_results=n_results)
    return [row["text"] for row in rows]


def retrieve_book_context_with_metadata(
    query: str,
    book_filename: str,
    n_results: int = 3,
) -> list[dict[str, Any]]:
    """Retrieve the top-n relevant chunks from a specific document with metadata."""
    source_type = _source_type_for(book_filename)
    rows, embeddings = _load_index(source_type)
    if not rows:
        return []

    row_indices = [idx for idx, row in enumerate(rows) if row.get("book_file") == book_filename]
    if not row_indices:
        return []

    doc_rows = [rows[idx] for idx in row_indices]
    doc_embeddings = embeddings[row_indices]
    if doc_embeddings.size == 0:
        return []

    query_embedding = _embed_texts([query])[0]
    top_indices = _cosine_rank(query_embedding, doc_embeddings, n_results)
    results: list[dict[str, Any]] = []
    for idx in top_indices:
        row = doc_rows[int(idx)]
        score = float(doc_embeddings[int(idx)] @ query_embedding)
        results.append(
            {
                "text": row["text"],
                "book_file": row["book_file"],
                "page_num": row["page_num"],
                "chunk_index": row["chunk_index"],
                "chunk_id": row["chunk_id"],
                "source_type": row["source_type"],
                "used_ocr": row.get("used_ocr", False),
                "distance": 1.0 - score,
            }
        )
    return results


def list_standard_documents() -> list[str]:
    """Return all PDF filenames currently available in Standards/."""
    if not STANDARDS_PATH.exists():
        return []
    return sorted(pdf.name for pdf in STANDARDS_PATH.glob("*.pdf"))


def books_index_status() -> dict[str, int]:
    """Return how many chunks are stored per book."""
    rows, _ = _load_index("book")
    counts: dict[str, int] = {}
    for row in rows:
        bf = row.get("book_file", "unknown")
        counts[bf] = counts.get(bf, 0) + 1
    return counts


def standards_index_status() -> dict[str, int]:
    """Return how many chunks are stored per standard document."""
    rows, _ = _load_index("standard")
    counts: dict[str, int] = {}
    for row in rows:
        bf = row.get("book_file", "unknown")
        counts[bf] = counts.get(bf, 0) + 1
    return counts
