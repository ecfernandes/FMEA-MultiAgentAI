"""Quick script to check why Fatigue and Tolerance aren't indexing."""
import sys
sys.path.insert(0, '/app')

from backend.services.book_indexer import index_book, BOOKS_PATH
import traceback

for name in sorted(BOOKS_PATH.glob("*.pdf")):
    from backend.services.book_indexer import _collection
    col = _collection()
    existing = col.get(where={"book_file": name.name})
    if existing['ids']:
        print(f"  SKIP (already indexed: {len(existing['ids'])} chunks): {name.name}")
        continue
    print(f"  Indexing: {name.name} ...", end='', flush=True)
    try:
        n = index_book(name.name, col)
        print(f" {n} chunks")
    except Exception as e:
        print(f" ERROR: {e}")
        traceback.print_exc()
