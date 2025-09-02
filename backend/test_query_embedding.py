#!/usr/bin/env python
"""
Test query embedding generation and similarity.
"""

import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_supabase_admin_client
from src.pipeline.shared.embedding_service import VoyageEmbeddingService

async def test_query_similarity():
    """Test if query embeddings match chunk embeddings"""
    
    db = get_supabase_admin_client()
    embedding_service = VoyageEmbeddingService()
    
    query = "Hvor mange offline ADK kontroller skal der være?"
    
    print(f"Query: {query}")
    print("="*60)
    
    # Generate query embedding
    query_embedding = await embedding_service.get_embedding(query)
    print(f"Query embedding dimensions: {len(query_embedding)}")
    print(f"First 5 values: {query_embedding[:5]}")
    print(f"All zeros? {all(v == 0 for v in query_embedding)}")
    
    # Test on both indexing runs
    for run_id in ["1ed7dc55-25ea-4b37-8f03-33d9f7aeeff8", "a7f5598e-a679-4d5f-a41c-298d6403812e"]:
        print(f"\nTesting indexing run: {run_id}")
        
        rpc_params = {
            'query_embedding': query_embedding,
            'match_threshold': 0.0,
            'match_count': 5,
            'indexing_run_id_filter': run_id
        }
        
        response = db.rpc('match_chunks', rpc_params).execute()
        
        if response.data:
            print(f"  ✓ Found {len(response.data)} results")
            if response.data:
                print(f"  Top similarity: {response.data[0].get('similarity', 'N/A')}")
        else:
            print(f"  ✗ No results found")

if __name__ == "__main__":
    asyncio.run(test_query_similarity())
