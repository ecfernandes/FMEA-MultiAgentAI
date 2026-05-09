"""
backend/services/book_indexer.py
---------------------------------
Indexes all PDF books in the Books/ folder into ChromaDB so that
specialist agents can retrieve relevant excerpts at query time (RAG).

Usage (one-time, or when books change):
    POST /index/books   ← triggers index_all_books()

Design:
  - PyMuPDF extracts text page-by-page (already a backend dependency).
  - ChromaDB DefaultEmbeddingFunction (all-MiniLM-L6-v2 via ONNX) generates
    embeddings — no heavy torch/sentence-transformers dependency needed.
  - Pages longer than CHUNK_MAX_CHARS are split at paragraph boundaries.
  - Each chunk is stored with metadata: {book_file, page_num}.
  - Collection name: "fmea_books"
  - Chunks are identified by  "<book_file>::p<page>::c<chunk>" so re-indexing
    the same book is idempotent (duplicate IDs are silently skipped).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

# ── Paths ────────────────────────────────────────────────────────────────────
_ROOT          = Path(__file__).parent.parent.parent          # project root
BOOKS_PATH     = _ROOT / "Books"
STANDARDS_PATH = _ROOT / "Standards"
VECTOR_STORE   = _ROOT / "data" / "vector_store"
COLLECTION_NAME = "fmea_books"
CHUNK_MAX_CHARS = 1500   # ~300 tokens — good balance for retrieval precision


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


_ef_singleton  = None
_col_singleton = None

def _collection():
    """Return (or create) the fmea_books ChromaDB collection — singleton."""
    global _ef_singleton, _col_singleton
    if _col_singleton is not None:
        return _col_singleton
    VECTOR_STORE.mkdir(parents=True, exist_ok=True)
    if _ef_singleton is None:
        _ef_singleton = DefaultEmbeddingFunction()
    client = chromadb.PersistentClient(path=str(VECTOR_STORE))
    _col_singleton = client.get_or_create_collection(
        name               = COLLECTION_NAME,
        embedding_function = _ef_singleton,
        metadata           = {"description": "FMEA reference book excerpts"},
    )
    return _col_singleton


def _resolve_pdf_path(filename: str) -> Path | None:
    for root in (BOOKS_PATH, STANDARDS_PATH):
        candidate = root / filename
        if candidate.exists():
            return candidate
    return None


def _source_type_for(filename: str) -> str:
    path = _resolve_pdf_path(filename)
    if path is None:
        return "unknown"
    return "standard" if path.parent == STANDARDS_PATH else "book"


# ============================================================================
# PUBLIC API
# ============================================================================

def index_book(book_filename: str, col=None) -> int:
    """
    Index one book PDF into ChromaDB.

    Args:
        book_filename: Exact filename inside Books/ (e.g. "Fatigue-Metal…pdf").
        col:           Pre-opened collection (opened once when indexing many books).

    Returns:
        Number of new chunks added (0 if book not found or already fully indexed).
    """
    path = _resolve_pdf_path(book_filename)
    if not path.exists():
        return 0

    if col is None:
        col = _collection()

    doc = fitz.open(str(path))
    documents: list[str]  = []
    metadatas: list[dict] = []
    ids:       list[str]  = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if not text:
            continue
        for ci, chunk in enumerate(_chunk_page(text)):
            chunk_id = f"{book_filename}::p{page_num}::c{ci}"
            documents.append(chunk)
            metadatas.append(
                {
                    "book_file": book_filename,
                    "page_num": page_num,
                    "chunk_index": ci,
                    "source_type": _source_type_for(book_filename),
                }
            )
            ids.append(chunk_id)

    doc.close()

    if not documents:
        return 0

    # Filter out already-indexed IDs so re-indexing is safe
    existing = set(col.get(ids=ids, include=[])["ids"])
    new_docs  = [(d, m, i) for d, m, i in zip(documents, metadatas, ids) if i not in existing]

    if not new_docs:
        return 0

    BATCH = 100
    for i in range(0, len(new_docs), BATCH):
        batch   = new_docs[i : i + BATCH]
        col.add(
            documents = [b[0] for b in batch],
            metadatas = [b[1] for b in batch],
            ids       = [b[2] for b in batch],
        )

    return len(new_docs)


def index_all_books(books_path: str | None = None) -> dict[str, int]:
    """
    Index every PDF in the Books/ folder.

    Returns:
        {filename: chunks_added} for each book found.
    """
    root  = Path(books_path) if books_path else BOOKS_PATH
    col   = _collection()
    pdfs  = sorted(root.glob("*.pdf"))
    total = len(pdfs)
    results: dict[str, int] = {}
    for idx, pdf in enumerate(pdfs, start=1):
        print(f"[RAG] ({idx}/{total}) Indexing {pdf.name} ...", flush=True)
        try:
            n = index_book(pdf.name, col)
            results[pdf.name] = n
            print(f"[RAG]   -> {n} chunks added", flush=True)
        except Exception as exc:
            print(f"[RAG]   -> ERROR: {exc}", flush=True)
            results[pdf.name] = 0
    print(f"[RAG] Done. Total books: {total}", flush=True)
    return results


def index_all_standards(standards_path: str | None = None) -> dict[str, int]:
    """
    Index every PDF in the Standards/ folder.

    Returns:
        {filename: chunks_added} for each standard found.
    """
    root = Path(standards_path) if standards_path else STANDARDS_PATH
    col = _collection()
    pdfs = sorted(root.glob("*.pdf"))
    total = len(pdfs)
    results: dict[str, int] = {}
    for idx, pdf in enumerate(pdfs, start=1):
        print(f"[RAG] ({idx}/{total}) Indexing standard {pdf.name} ...", flush=True)
        try:
            n = index_book(pdf.name, col)
            results[pdf.name] = n
            print(f"[RAG]   -> {n} chunks added", flush=True)
        except Exception as exc:
            print(f"[RAG]   -> ERROR: {exc}", flush=True)
            results[pdf.name] = 0
    print(f"[RAG] Done. Total standards: {total}", flush=True)
    return results


def retrieve_book_context(
    query:         str,
    book_filename: str,
    n_results:     int = 3,
) -> list[str]:
    """
    Retrieve the top-n most relevant chunks from a specific book.

    Args:
        query:         The semantic query (e.g. "window lift motor shaft fatigue crack").
        book_filename: Exact book filename used as metadata filter.
        n_results:     Number of chunks to retrieve.

    Returns:
        List of text chunks (empty if book not yet indexed).
    """
    try:
        col = _collection()
        # Guard: if the book has no entries yet, return empty gracefully
        count = col.count()
        if count == 0:
            return []
        res = col.query(
            query_texts = [query],
            n_results   = min(n_results, count),
            where       = {"book_file": book_filename},
        )
        return res["documents"][0] if res.get("documents") else []
    except Exception:
        return []


def retrieve_book_context_with_metadata(
    query: str,
    book_filename: str,
    n_results: int = 3,
) -> list[dict[str, Any]]:
    """
    Retrieve the top-n relevant chunks from a specific document with metadata.

    Returns a list of dictionaries containing the chunk text and reference info.
    """
    try:
        col = _collection()
        count = col.count()
        if count == 0:
            return []
        res = col.query(
            query_texts=[query],
            n_results=min(n_results, count),
            where={"book_file": book_filename},
        )
        docs = res.get("documents", [[]])
        metas = res.get("metadatas", [[]])
        ids = res.get("ids", [[]])
        distances = res.get("distances", [[]])
        rows: list[dict[str, Any]] = []
        for idx, text in enumerate(docs[0] if docs else []):
            meta = metas[0][idx] if metas and metas[0] and idx < len(metas[0]) else {}
            rows.append(
                {
                    "text": text,
                    "book_file": meta.get("book_file", book_filename),
                    "page_num": meta.get("page_num"),
                    "chunk_index": meta.get("chunk_index"),
                    "chunk_id": ids[0][idx] if ids and ids[0] and idx < len(ids[0]) else None,
                    "source_type": meta.get("source_type", _source_type_for(book_filename)),
                    "distance": distances[0][idx] if distances and distances[0] and idx < len(distances[0]) else None,
                }
            )
        return rows
    except Exception:
        return []


def list_standard_documents() -> list[str]:
    """Return all PDF filenames currently available in Standards/."""
    if not STANDARDS_PATH.exists():
        return []
    return sorted(pdf.name for pdf in STANDARDS_PATH.glob("*.pdf"))


def books_index_status() -> dict[str, int]:
    """
    Return how many chunks are stored per book (for the /index/books GET endpoint).
    """
    try:
        col    = _collection()
        result = col.get(include=["metadatas"])
        counts: dict[str, int] = {}
        for meta in result.get("metadatas", []):
            bf = meta.get("book_file", "unknown")
            counts[bf] = counts.get(bf, 0) + 1
        return counts
    except Exception:
        return {}
