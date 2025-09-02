#!/usr/bin/env python
"""
Test if embeddings are valid and searchable for the failing indexing run.
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_supabase_admin_client

def test_embeddings(indexing_run_id: str):
    """Test embeddings directly"""
    
    db = get_supabase_admin_client()
    
    print(f"\nTesting embeddings for: {indexing_run_id}")
    print("="*60)
    
    # Get one chunk with embedding
    chunk_response = (
        db.table("document_chunks")
        .select("id, content, embedding_1024")
        .eq("indexing_run_id", indexing_run_id)
        .not_.is_("embedding_1024", "null")
        .limit(1)
        .execute()
    )
    
    if not chunk_response.data:
        print("No chunks found!")
        return
    
    chunk = chunk_response.data[0]
    print(f"Chunk ID: {chunk['id']}")
    print(f"Content preview: {chunk['content'][:100]}...")
    
    # Check embedding
    embedding = chunk['embedding_1024']
    if isinstance(embedding, str):
        try:
            embedding = json.loads(embedding)
        except:
            embedding = eval(embedding)
    
    print(f"Embedding type: {type(embedding)}")
    print(f"Embedding dimensions: {len(embedding) if isinstance(embedding, list) else 'N/A'}")
    
    if isinstance(embedding, list) and len(embedding) > 0:
        print(f"First 5 values: {embedding[:5]}")
        print(f"All zeros? {all(v == 0 for v in embedding)}")
        print(f"Valid floats? {all(isinstance(v, (int, float)) for v in embedding)}")
        
        # Test direct SQL query with this embedding
        print("\nTesting direct SQL similarity search:")
        
        # Use the same embedding to search (should find itself with similarity = 1)
        rpc_params = {
            'query_embedding': embedding,
            'match_threshold': 0.0,
            'match_count': 5,
            'indexing_run_id_filter': indexing_run_id
        }
        
        response = db.rpc('match_chunks', rpc_params).execute()
        
        if response.data:
            print(f"✓ Found {len(response.data)} results")
            for i, result in enumerate(response.data[:3]):
                print(f"  Result {i+1}: ID={result['id']}, Similarity={result.get('similarity', 'N/A')}")
        else:
            print("✗ No results found - HNSW index might be broken!")


if __name__ == "__main__":
    # Test both runs
    test_embeddings("1ed7dc55-25ea-4b37-8f03-33d9f7aeeff8")  # Working
    test_embeddings("a7f5598e-a679-4d5f-a41c-298d6403812e")  # Failing
