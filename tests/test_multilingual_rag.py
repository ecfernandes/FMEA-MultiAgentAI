"""
Test Script - Multilingual RAG.
Checks system behavior across multiple languages.
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from vector_store.embeddings import EmbeddingGenerator
from vector_store.retriever import SemanticRetriever


def test_language_detection():
    """Test automatic language detection."""
    print("=" * 60)
    print("TEST 1: Language Detection")
    print("=" * 60)
    
    retriever = SemanticRetriever()
    
    test_texts = {
        'pt': "This is a software development project with risk of delivery delay",
        'fr': "Ceci est un projet de développement de logiciel avec risque de retard de livraison",
        'en': "This is a software development project with risk of delivery delay",
        'es': "Este es un proyecto de desarrollo de software con riesgo de retraso en la entrega"
    }
    
    for expected, text in test_texts.items():
        detected = retriever._detect_language(text)
        status = "✅" if detected == expected else "⚠️"
        print(f"{status} Expected: {expected} | Detected: {detected}")
        print(f"   Text: {text[:50]}...")
        print()


def test_multilingual_embeddings():
    """Test similarity among embeddings in different languages."""
    print("\n" + "=" * 60)
    print("TEST 2: Cross-Language Similarity")
    print("=" * 60)
    
    generator = EmbeddingGenerator()
    
    # Similar texts in 3 languages
    texts = {
        'pt': "risk of delivery delay due to lack of human resources",
        'fr': "risque de retard de livraison par manque de ressources humaines",
        'en': "risk of delivery delay due to lack of human resources"
    }
    
    # Generate embeddings
    embeddings = {}
    print("\n📊 Generating embeddings...\n")
    for lang, text in texts.items():
        embeddings[lang] = generator.encode_text(text)
        print(f"  {lang.upper()}: {text}")
    
    # Compute similarities
    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    print("\n🔍 Similarities between languages:\n")
    
    comparisons = [
        ('pt', 'fr'),
        ('pt', 'en'),
        ('fr', 'en')
    ]
    
    for lang1, lang2 in comparisons:
        sim = cosine_similarity(embeddings[lang1], embeddings[lang2])
        status = "✅" if sim > 0.75 else "⚠️"
        print(f"{status} {lang1.upper()} ↔ {lang2.upper()}: {sim:.3f} ({sim*100:.1f}%)")
    
    print("\n💡 Interpretation:")
    print("  > 0.90: Extremely similar")
    print("  0.80-0.90: Very similar")
    print("  0.70-0.80: Similar")
    print("  < 0.70: Weakly similar")


def test_different_concepts():
    """Test that different concepts have low similarity."""
    print("\n" + "=" * 60)
    print("TEST 3: Concept Differentiation")
    print("=" * 60)
    
    generator = EmbeddingGenerator()
    
    # Texts with different concepts
    concept1 = "project delivery delay due to resource shortages"
    concept2 = "source code quality issues"
    concept3 = "conflict among team members"
    
    print("\n📝 Tested concepts:\n")
    print(f"  1. {concept1}")
    print(f"  2. {concept2}")
    print(f"  3. {concept3}")
    
    # Generate embeddings
    emb1 = generator.encode_text(concept1)
    emb2 = generator.encode_text(concept2)
    emb3 = generator.encode_text(concept3)
    
    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    print("\n🔍 Similarities:\n")
    
    sim_1_2 = cosine_similarity(emb1, emb2)
    sim_1_3 = cosine_similarity(emb1, emb3)
    sim_2_3 = cosine_similarity(emb2, emb3)
    
    print(f"  Delay ↔ Quality: {sim_1_2:.3f} ({'low' if sim_1_2 < 0.6 else 'medium' if sim_1_2 < 0.75 else 'high'})")
    print(f"  Delay ↔ Conflict:  {sim_1_3:.3f} ({'low' if sim_1_3 < 0.6 else 'medium' if sim_1_3 < 0.75 else 'high'})")
    print(f"  Quality ↔ Conflict: {sim_2_3:.3f} ({'low' if sim_2_3 < 0.6 else 'medium' if sim_2_3 < 0.75 else 'high'})")
    
    print("\n✅ System correctly differentiates distinct concepts" if all(s < 0.75 for s in [sim_1_2, sim_1_3, sim_2_3]) else "\n⚠️ Concepts may be too close")


def test_same_concept_different_languages():
    """Test cross-language search for the same concept."""
    print("\n" + "=" * 60)
    print("TEST 4: Cross-Language Search (Simulation)")
    print("=" * 60)
    
    generator = EmbeddingGenerator()
    
    # Query in French
    query_fr = "retard dans la livraison du projet à cause d'un manque de ressources"
    
    # Historical cases in different languages
    historical_cases = {
        'pt': "project delivery delay due to lack of team resources",
        'en': "project delivery delay due to insufficient team resources",
        'fr': "retard de livraison du projet par manque de ressources",
        'pt_2': "client communication issues causing rework",
        'en_2': "quality issues in the software requiring extensive testing"
    }
    
    print(f"\n🔍 Query (FR): {query_fr}\n")
    print("📚 Historical cases:\n")
    
    # Generate embeddings
    query_emb = generator.encode_text(query_fr)
    historical_embs = {lang: generator.encode_text(text) for lang, text in historical_cases.items()}
    
    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    # Compute similarities
    results = []
    for lang, emb in historical_embs.items():
        sim = cosine_similarity(query_emb, emb)
        results.append({
            'lang': lang.split('_')[0],
            'text': historical_cases[lang],
            'similarity': sim
        })
    
    # Sort by similarity
    results.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Show top 3
    print("🎯 Top 3 most similar cases:\n")
    for i, result in enumerate(results[:3], 1):
        status = "✅" if result['similarity'] > 0.75 else "⚠️"
        print(f"{i}. {status} Similarity: {result['similarity']:.3f} ({result['similarity']*100:.1f}%)")
        print(f"   Language: {result['lang'].upper()}")
        print(f"   Text: {result['text'][:60]}...")
        print()
    
    print("💡 Note: Cases about 'delay/retard' have high similarity")
    print("   even in different languages!")


def main():
    """Run all tests."""
    print("\n" + "🧪" * 30)
    print("       MULTILINGUAL RAG SYSTEM TESTS")
    print("🧪" * 30 + "\n")
    
    try:
        # Test 1: Language detection
        test_language_detection()
        
        # Test 2: Multilingual embeddings
        test_multilingual_embeddings()
        
        # Test 3: Concept differentiation
        test_different_concepts()
        
        # Test 4: Cross-language search
        test_same_concept_different_languages()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED!")
        print("=" * 60)
        print("\n💡 Next steps:")
        print("  1. Install dependency: pip install langdetect")
        print("  2. Run app: streamlit run app.py")
        print("  3. Test with real documents in PT/FR/EN")
        print("  4. Validate RAG finding similar cases across languages\n")
        
    except Exception as e:
        print(f"\n❌ ERROR during tests: {str(e)}")
        print("\n💡 Possible causes:")
        print("  - langdetect not installed: pip install langdetect")
        print("  - Embedding model not downloaded yet (it will auto-download)")
        print(f"\n🔍 Error details:\n{type(e).__name__}: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
