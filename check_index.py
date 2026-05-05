import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from pathlib import Path

# Works both locally (relative path) and inside container (/app prefix)
for store_path in ["/app/data/vector_store", "data/vector_store"]:
    if Path(store_path).exists():
        break

client = chromadb.PersistentClient(path=store_path)
try:
    col = client.get_or_create_collection(
        name="fmea_books",
        embedding_function=DefaultEmbeddingFunction(),
    )
    total = col.count()
    print(f"Total chunks in fmea_books: {total}")
    if total > 0:
        sample = col.get(limit=5000, include=["metadatas"])
        books = {}
        for m in sample["metadatas"]:
            b = m.get("book_file", "unknown")
            books[b] = books.get(b, 0) + 1
        for b, n in sorted(books.items()):
            print(f"  {n:>5} chunks  {b}")
    else:
        print("Collection exists but is empty — books have not been indexed yet.")
except Exception as e:
    print(f"Error: {e}")
