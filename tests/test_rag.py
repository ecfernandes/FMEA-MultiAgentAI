"""
RAG system test script.
Checks if all dependencies are installed.
"""

import sys

print("=" * 60)
print("DEPENDENCY TEST - RAG PHASE 2")
print("=" * 60)

# Test imports
dependencies = {
    'chromadb': 'ChromaDB',
    'sentence_transformers': 'Sentence Transformers',
    'streamlit': 'Streamlit',
    'google.generativeai': 'Google Gemini AI',
    'pandas': 'Pandas',
    'numpy': 'NumPy'
}

missing = []
installed = []

for module, name in dependencies.items():
    try:
        __import__(module)
        installed.append(f"✅ {name}")
    except ImportError:
        missing.append(f"❌ {name} ({module})")

print("\n📦 Installed Dependencies:")
for item in installed:
    print(f"  {item}")

if missing:
    print("\n⚠️  Missing Dependencies:")
    for item in missing:
        print(f"  {item}")
    print("\n💡 Execute: pip install -r requirements.txt")
    sys.exit(1)
else:
    print("\n✅ All dependencies are installed!")

print("\n" + "=" * 60)
print("RAG MODULE TEST")
print("=" * 60)

try:
    from src.vector_store.chroma_manager import ChromaManager
    print("✅ ChromaManager imported")
    
    from src.vector_store.embeddings import EmbeddingGenerator
    print("✅ EmbeddingGenerator imported")
    
    from src.vector_store.retriever import SemanticRetriever
    print("✅ SemanticRetriever imported")
    
    print("\n🧪 Testing ChromaManager...")
    cm = ChromaManager(persist_directory="./data/vector_store_test")
    print(f"  Documents in DB: {cm.count_documents()}")
    
    print("\n🧪 Testing EmbeddingGenerator...")
    print("  Loading model (first run may take longer)...")
    eg = EmbeddingGenerator()
    test_embedding = eg.encode_text("Embedding test")
    print(f"  ✅ Embedding generated: {len(test_embedding)} dimensions")
    
    print("\n🧪 Testing SemanticRetriever...")
    sr = SemanticRetriever(persist_directory="./data/vector_store_test")
    stats = sr.get_statistics()
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Model: {stats['embedding_model']}")
    print(f"  Dimensions: {stats['embedding_dimension']}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\n🚀 RAG system is ready to use!")
    print("   Execute: streamlit run app.py")
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
