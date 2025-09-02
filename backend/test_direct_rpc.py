#!/usr/bin/env python
"""
Test the RPC function directly to understand what's happening.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_supabase_admin_client
from src.pipeline.shared.embedding_service import VoyageEmbeddingService

async def test_direct_rpc():
    """Test the RPC function directly with a real query"""
    
    db = get_supabase_admin_client()
    embedding_service = VoyageEmbeddingService()
    
    query = "Hvor mange TVO anlæg skal der installeres"
    indexing_run_id = "a7f5598e-a679-4d5f-a41c-298d6403812e"
    
    print(f"\nQuery: {query}")
    print(f"Indexing Run ID: {indexing_run_id}\n")
    
    # Generate real embedding
    print("Generating embedding...")
    query_embedding = await embedding_service.get_embedding(query)
    print(f"Embedding generated: {len(query_embedding)} dimensions\n")
    
    # Test 1: Original function behavior (with threshold in WHERE)
    print("Test 1: Current match_chunks behavior")
    print("-" * 40)
    
    for threshold in [0.4, 0.3, 0.2, 0.1, 0.0, -1.0]:
        try:
            response = db.rpc('match_chunks', {
                'query_embedding': query_embedding,
                'match_threshold': threshold,
                'match_count': 15,
                'indexing_run_id_filter': indexing_run_id
            }).execute()
            
            count = len(response.data) if response.data else 0
            if response.data and count > 0:
                scores = [r.get('similarity', 0) for r in response.data[:3]]
                print(f"Threshold {threshold:5.1f}: {count:2} results | Top scores: {scores}")
            else:
                print(f"Threshold {threshold:5.1f}: {count:2} results")
                
        except Exception as e:
            print(f"Threshold {threshold:5.1f}: ERROR - {e}")
    
    # Test 2: Without indexing_run_id filter
    print("\nTest 2: Without indexing_run_id filter")
    print("-" * 40)
    
    try:
        response_no_filter = db.rpc('match_chunks', {
            'query_embedding': query_embedding,
            'match_threshold': 0.0,
            'match_count': 15,
            'indexing_run_id_filter': None
        }).execute()
        
        count = len(response_no_filter.data) if response_no_filter.data else 0
        print(f"Results without filter: {count}")
        
        if response_no_filter.data:
            # Check how many are from our run
            from_our_run = sum(1 for r in response_no_filter.data 
                              if str(r.get('indexing_run_id')) == indexing_run_id)
            print(f"From our indexing run: {from_our_run}")
            
            # Show scores
            scores = [r.get('similarity', 0) for r in response_no_filter.data[:5]]
            print(f"Top 5 scores: {scores}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Alternative function if it exists
    print("\nTest 3: Alternative function (match_chunks_with_threshold)")
    print("-" * 40)
    
    try:
        response_alt = db.rpc('match_chunks_with_threshold', {
            'query_embedding': query_embedding,
            'match_threshold': 0.0,
            'match_count': 15,
            'indexing_run_id_filter': indexing_run_id
        }).execute()
        
        count = len(response_alt.data) if response_alt.data else 0
        print(f"Results with alternative: {count}")
        
        if response_alt.data:
            scores = [r.get('similarity', 0) for r in response_alt.data[:5]]
            print(f"Top 5 scores: {scores}")
            
    except Exception as e:
        print(f"Alternative function error: {e}")
    
    print("\n" + "="*60)
    print("ANALYSIS")
    print("="*60)
    print("""
The results show how the threshold in the WHERE clause affects results.
If we're only getting 1 result at threshold 0.0, it means only 1 chunk
has similarity > 0.0 for this query in this indexing run.

The function needs to be fixed to remove the threshold from WHERE clause
and return top K results regardless of their similarity scores.
""")

if __name__ == "__main__":
    asyncio.run(test_direct_rpc())