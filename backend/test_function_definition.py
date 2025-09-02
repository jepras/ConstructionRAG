#!/usr/bin/env python
"""
Test what the actual function definition looks like and if it's the issue.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_supabase_admin_client

def test_function_definition():
    """Test the actual behavior of the function"""
    
    db = get_supabase_admin_client()
    
    print("\n" + "="*60)
    print("TESTING FUNCTION BEHAVIOR")
    print("="*60)
    
    indexing_run_id = "a7f5598e-a679-4d5f-a41c-298d6403812e"
    
    # Create a simple test embedding
    test_embedding = [0.1] * 1024
    
    # Test 1: Call with extremely negative threshold
    print("\n1. Testing with extremely negative threshold (-999):")
    print("-" * 40)
    
    try:
        response = db.rpc('match_chunks', {
            'query_embedding': test_embedding,
            'match_threshold': -999.0,  # Should return everything if threshold is in WHERE
            'match_count': 15,
            'indexing_run_id_filter': indexing_run_id
        }).execute()
        
        count = len(response.data) if response.data else 0
        print(f"Results: {count}")
        
        if response.data and count > 0:
            # Check the structure of returned data
            first_result = response.data[0]
            print(f"First result keys: {list(first_result.keys())}")
            print(f"Has 'similarity' field: {'similarity' in first_result}")
            
            # Check similarity values
            if 'similarity' in first_result:
                sims = [r['similarity'] for r in response.data[:5]]
                print(f"Top 5 similarities: {sims}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Get one chunk directly and use its embedding
    print("\n2. Testing with a real chunk's own embedding:")
    print("-" * 40)
    
    # Get a chunk with its embedding
    chunk_response = db.table("document_chunks").select(
        "id,embedding_1024"
    ).eq("indexing_run_id", indexing_run_id).not_.is_("embedding_1024", "null").limit(1).execute()
    
    if chunk_response.data:
        chunk_id = chunk_response.data[0]['id']
        chunk_embedding = chunk_response.data[0]['embedding_1024']
        
        print(f"Using embedding from chunk: {chunk_id}")
        
        # Test with this chunk's own embedding (should return itself as top result)
        try:
            response = db.rpc('match_chunks', {
                'query_embedding': chunk_embedding,
                'match_threshold': -999.0,
                'match_count': 15,
                'indexing_run_id_filter': indexing_run_id
            }).execute()
            
            count = len(response.data) if response.data else 0
            print(f"Results: {count}")
            
            if response.data:
                # Check if the source chunk is first
                first_id = response.data[0]['id']
                print(f"First result is source chunk: {first_id == chunk_id}")
                
                # Show similarities
                if 'similarity' in response.data[0]:
                    sims = [r['similarity'] for r in response.data[:5]]
                    print(f"Top 5 similarities: {sims}")
                
        except Exception as e:
            print(f"Error: {e}")
    
    # Test 3: Raw SQL equivalent (what the function SHOULD do)
    print("\n3. What we expect (direct count of chunks with embeddings):")
    print("-" * 40)
    
    count_response = db.table("document_chunks").select(
        "id", count="exact"
    ).eq("indexing_run_id", indexing_run_id).not_.is_("embedding_1024", "null").execute()
    
    total_with_embeddings = count_response.count if hasattr(count_response, 'count') else len(count_response.data)
    print(f"Total chunks with embeddings in this run: {total_with_embeddings}")
    print(f"Expected HNSW results with no threshold: 15 (or {min(15, total_with_embeddings)} if less than 15)")
    
    print("\n" + "="*60)
    print("DIAGNOSIS")
    print("="*60)
    
    print("""
If HNSW returns fewer results than expected, the function still has:
1. The threshold filter in the WHERE clause (blocking results)
2. Some other filtering condition we're not aware of
3. A caching issue where the old function definition persists

The Python fallback works because it:
- Fetches ALL chunks with embeddings
- Calculates similarity for each in Python
- Sorts and returns top K

While HNSW should:
- Use the index to find K nearest neighbors efficiently
- Return them regardless of similarity score
""")

if __name__ == "__main__":
    test_function_definition()