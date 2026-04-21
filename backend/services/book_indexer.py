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

import fitz  # PyMuPDF

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

# ── Paths ────────────────────────────────────────────────────────────────────
_ROOT          = Path(__file__).parent.parent.parent          # project root
BOOKS_PATH     = _ROOT / "Books"
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
    path = BOOKS_PATH / book_filename
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
            metadatas.append({"book_file": book_filename, "page_num": page_num})
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
    root = Path(books_path) if books_path else BOOKS_PATH
    col  = _collection()
    results: dict[str, int] = {}
    for pdf in sorted(root.glob("*.pdf")):
        try:
            results[pdf.name] = index_book(pdf.name, col)
        except Exception as exc:
            print(f"[RAG] Skipping {pdf.name}: {exc}")
            results[pdf.name] = 0
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
