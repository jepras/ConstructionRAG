#!/usr/bin/env python
"""
Test HNSW function directly to debug the empty results issue.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_supabase_admin_client
from src.pipeline.shared.embedding_service import VoyageEmbeddingService

async def test_hnsw_directly():
    """Test HNSW function with various parameters"""
    
    db = get_supabase_admin_client()
    embedding_service = VoyageEmbeddingService()
    
    query = "Hvor mange offline ADK kontroller skal der være?"
    indexing_run_id = "a7f5598e-a679-4d5f-a41c-298d6403812e"
    
    print(f"\nQuery: {query}")
    print(f"Indexing Run ID: {indexing_run_id}\n")
    
    # Generate real embedding
    print("Generating embedding...")
    query_embedding = await embedding_service.get_embedding(query)
    print(f"Embedding generated: {len(query_embedding)} dimensions\n")
    
    print("="*60)
    print("TEST 1: With indexing_run_id filter (as in production)")
    print("="*60)
    
    try:
        response = db.rpc('match_chunks', {
            'query_embedding': query_embedding,
            'match_threshold': -999.0,
            'match_count': 10,
            'indexing_run_id_filter': indexing_run_id
        }).execute()
        
        print(f"Response type: {type(response)}")
        print(f"Has data attribute: {hasattr(response, 'data')}")
        print(f"Response.data type: {type(response.data)}")
        print(f"Response.data is None: {response.data is None}")
        
        if response.data is not None:
            print(f"Number of results: {len(response.data)}")
            if len(response.data) > 0:
                print(f"First result keys: {list(response.data[0].keys())}")
                if 'similarity' in response.data[0]:
                    print(f"First result similarity: {response.data[0]['similarity']}")
        else:
            print("Response.data is None!")
            
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e)}")
        if hasattr(e, '__dict__'):
            print(f"Error details: {e.__dict__}")
    
    print("\n" + "="*60)
    print("TEST 2: Without indexing_run_id filter")
    print("="*60)
    
    try:
        response = db.rpc('match_chunks', {
            'query_embedding': query_embedding,
            'match_threshold': -999.0,
            'match_count': 10,
            'indexing_run_id_filter': None
        }).execute()
        
        if response.data:
            print(f"Number of results: {len(response.data)}")
            
            # Check how many are from our indexing run
            from_our_run = [r for r in response.data if str(r.get('indexing_run_id')) == indexing_run_id]
            print(f"Results from our indexing run: {len(from_our_run)}")
            
            if len(response.data) > 0:
                print(f"\nFirst 3 results:")
                for i, r in enumerate(response.data[:3], 1):
                    print(f"  {i}. Run: {r.get('indexing_run_id')}, Similarity: {r.get('similarity', 0):.4f}")
        else:
            print("No results!")
            
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*60)
    print("TEST 3: Direct table query (bypass function)")
    print("="*60)
    
    # Check if chunks exist for this indexing run
    chunks = db.table("document_chunks").select(
        "id,indexing_run_id"
    ).eq("indexing_run_id", indexing_run_id).not_.is_("embedding_1024", "null").limit(5).execute()
    
    print(f"Chunks with embeddings in this run: {len(chunks.data) if chunks.data else 0}")
    if chunks.data:
        print(f"Sample chunk IDs:")
        for chunk in chunks.data:
            print(f"  - {chunk['id']}")
    
    print("\n" + "="*60)
    print("TEST 4: Test with string vs UUID format")
    print("="*60)
    
    # Try passing the indexing_run_id as a string directly
    try:
        response = db.rpc('match_chunks', {
            'query_embedding': query_embedding,
            'match_threshold': -999.0,
            'match_count': 10,
            'indexing_run_id_filter': str(indexing_run_id)  # Ensure it's a string
        }).execute()
        
        print(f"Results with string format: {len(response.data) if response.data else 0}")
        
    except Exception as e:
        print(f"Error with string format: {e}")
    
    print("\n" + "="*60)
    print("DIAGNOSIS")
    print("="*60)
    print("""
If Test 1 returns 0 results but Test 2 returns results:
- The indexing_run_id filter in the function is not working correctly
- Could be a type mismatch (UUID vs string comparison)

If both Test 1 and 2 return 0 results:
- The function itself is broken
- The embeddings might not be properly indexed

If Test 3 shows chunks exist:
- Confirms data is there, issue is with the function
""")

if __name__ == "__main__":
    asyncio.run(test_hnsw_directly())