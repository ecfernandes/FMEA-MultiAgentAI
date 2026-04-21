"""Script to inspect RAG history contents."""

from src.vector_store.retriever import SemanticRetriever

def main():
    print("=" * 60)
    print("RAG HISTORY CHECK")
    print("=" * 60)
    
    try:
        retriever = SemanticRetriever()
        stats = retriever.get_statistics()
        
        print(f"\nSTATISTICS:")
        print(f"  Total documents: {stats['total_documents']}")
        print(f"  Embedding model: {stats['embedding_model']}")
        print(f"  Dimensions: {stats['embedding_dimension']}")
        
        if stats['total_documents'] == 0:
            print("\nEmpty history - no analysis saved yet.")
            return
        
        # Retrieve all cases
        print(f"\nSTORED ANALYSES:\n")
        results = retriever.find_similar_cases("project", n_results=20, similarity_threshold=0.0)
        
        for i, case in enumerate(results, 1):
            print(f"\n{'-' * 60}")
            print(f"ANALYSIS #{i}")
            print(f"{'-' * 60}")
            print(f"  ID: {case['doc_id']}")
            print(f"  Date: {case['metadata'].get('analysis_date', 'N/A')[:19]}")
            print(f"  Files: {case['metadata'].get('files_analyzed', 'N/A')}")
            print(f"  Num risks: {case['metadata'].get('num_risks', 0)}")
            print(f"  Preview: {case['document_text'][:150].replace(chr(10), ' ')}...")
            
            if 'historical_risks' in case and case['historical_risks']:
                print(f"\n  Identified risks:")
                for risk in case['historical_risks'][:3]:
                    category = risk.get('Category', risk.get('Categoria', 'N/A'))
                    description = risk.get('Risk Description', risk.get('Descrição do Risco', 'N/A'))
                    print(f"    - [{category}] {description[:80]}...")
        
        print(f"\n{'=' * 60}\n")
        
    except Exception as e:
        print(f"\nError: {str(e)}")


if __name__ == "__main__":
    main()
