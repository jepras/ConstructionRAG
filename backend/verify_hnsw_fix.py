#!/usr/bin/env python
"""
Verify the HNSW function fix works correctly.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_supabase_admin_client

def verify_hnsw_fix(indexing_run_id: str):
    """Verify the fixed HNSW function returns all results"""
    
    db = get_supabase_admin_client()
    
    print(f"\n{'='*60}")
    print(f"VERIFYING HNSW FIX FOR RUN: {indexing_run_id}")
    print(f"{'='*60}\n")
    
    # Create a simple test embedding
    test_embedding = [0.1] * 1024  # Simple test vector
    
    print("Testing different match_count values with threshold = 0.0:")
    
    for count in [15, 50, 100, 200]:
        try:
            response = db.rpc('match_chunks', {
                'query_embedding': test_embedding,
                'match_threshold': 0.0,
                'match_count': count,
                'indexing_run_id_filter': indexing_run_id
            }).execute()
            
            results = len(response.data) if response.data else 0
            print(f"  Request {count} results → Got {results} results")
            
            if results > 0 and response.data:
                # Show similarity range
                similarities = [r.get('similarity', 0) for r in response.data]
                print(f"    Similarity range: {min(similarities):.4f} to {max(similarities):.4f}")
                
        except Exception as e:
            print(f"  Error with count={count}: {e}")
    
    print(f"\n{'='*60}")
    print("CONCLUSION")
    print(f"{'='*60}")
    
    # Final test with high count
    try:
        final_response = db.rpc('match_chunks', {
            'query_embedding': test_embedding,
            'match_threshold': 0.0,
            'match_count': 200,
            'indexing_run_id_filter': indexing_run_id
        }).execute()
        
        final_count = len(final_response.data) if final_response.data else 0
        
        if final_count >= 15:
            print(f"✅ SUCCESS: HNSW now returns {final_count} results (was 4 before fix)")
            print(f"   The function can now properly retrieve chunks!")
        else:
            print(f"⚠️ Still limited: Only {final_count} results returned")
            print(f"   There may be another issue to investigate")
            
    except Exception as e:
        print(f"❌ Error in final test: {e}")


if __name__ == "__main__":
    indexing_run_id = "a7f5598e-a679-4d5f-a41c-298d6403812e"
    verify_hnsw_fix(indexing_run_id)