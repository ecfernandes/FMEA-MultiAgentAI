"""
Lessons Learned feature test script.
Tests semantic search for similar risks in history.
"""

from src.vector_store.retriever import SemanticRetriever

def test_similar_risks():
    """Test search for similar risks."""
    
    print("=" * 80)
    print("🧪 TEST: Similar Risk Search in History")
    print("=" * 80)
    
    try:
        # Initialize retriever
        print("\n1️⃣ Initializing retriever...")
        retriever = SemanticRetriever()
        print("✅ Retriever initialized successfully!")
        
        # Check whether there is historical data
        print("\n2️⃣ Checking history...")
        all_docs = retriever.chroma_manager.get_all_documents()
        
        if not all_docs or not all_docs['ids']:
            print("⚠️  No data in history. Run a few analyses first!")
            print("   Use app.py to analyze documents and build history.")
            return
        
        num_analyses = len(all_docs['ids'])
        print(f"✅ Found {num_analyses} analyses in history")
        
        # Sample risk for testing
        test_risk = "Project budget has experienced significant overruns without clear justification"
        
        print(f"\n3️⃣ Searching for risks similar to:")
        print(f"   '{test_risk}'")
        print("\n   Similarity threshold: 70%")
        
        # Search similar risks
        similar_analyses = retriever.find_similar_risks(
            risk_description=test_risk,
            similarity_threshold=0.70,
            max_results=50
        )
        
        if not similar_analyses:
            print("\n❌ No similar risk found in history.")
            print("   This is normal if the history does not contain budget-related risks.")
            return
        
        # Show results
        print(f"\n✅ SIMILAR RISKS FOUND IN {len(similar_analyses)} ANALYSIS(ES):")
        print("=" * 80)
        
        for analysis in similar_analyses:
            print(f"\n📋 ANALYSIS #{analysis['analysis_number']}")
            print(f"   📅 Date: {analysis['analysis_date']}")
            print(f"   📁 File: {analysis['file_name']}")
            print(f"   🔍 Similar risks found: {len(analysis['similar_risks'])}")
            
            for i, risk in enumerate(analysis['similar_risks'][:2], 1):  # Show up to 2
                similarity_pct = risk['similarity'] * 100
                print(f"\n   Similar Risk #{i}:")
                print(f"   ├─ Similarity: {similarity_pct:.1f}%")
                print(f"   ├─ Description: {risk['risk_description'][:100]}...")
                print(f"   ├─ Category: {risk['category']}")
                print(f"   ├─ Probability: {risk['probability']} | Impact: {risk['impact']}")
                print(f"   ├─ Strategy: {risk['strategy']}")
                print(f"   └─ Action: {risk['action'][:80]}...")
                
                # Show feedback if available
                if risk.get('feedback'):
                    feedback = risk['feedback']
                    worked = feedback.get('worked') if isinstance(feedback, dict) else feedback
                    
                    if worked == 'Yes':
                        print(f"      ✅ Feedback: This action WORKED!")
                    elif worked == 'No':
                        print(f"      ❌ Feedback: This action DID NOT WORK!")
                        if isinstance(feedback, dict) and feedback.get('alternative_action'):
                            print(f"      💡 Suggested alternative: {feedback['alternative_action'][:60]}...")
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 SUMMARY:")
        analysis_numbers = [a['analysis_number'] for a in similar_analyses]
        print(f"   Similar risk found in analyses: #{', #'.join(map(str, analysis_numbers))}")
        print("=" * 80)
        
        print("\n✅ TEST COMPLETED SUCCESSFULLY!")
        print("\n💡 NEXT STEP:")
        print("   Run app.py and execute a risk analysis.")
        print("   The 'Lessons Learned' section will appear automatically after analysis,")
        print("   showing similar risks found in history!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_similar_risks()
