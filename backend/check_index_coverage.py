#!/usr/bin/env python
"""
Check HNSW index coverage for a specific indexing run.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_supabase_admin_client

def check_index_coverage(indexing_run_id: str):
    """Check index coverage for chunks with embeddings"""
    
    db = get_supabase_admin_client()
    
    print(f"\n{'='*60}")
    print(f"CHECKING INDEX COVERAGE FOR RUN: {indexing_run_id}")
    print(f"{'='*60}\n")
    
    # 1. Count total chunks for this indexing run
    total_response = db.table("document_chunks").select(
        "id", count="exact"
    ).eq("indexing_run_id", indexing_run_id).execute()
    
    total_chunks = total_response.count if hasattr(total_response, 'count') else len(total_response.data)
    print(f"1. Total chunks in indexing run: {total_chunks}")
    
    # 2. Count chunks with embeddings
    with_embeddings_response = db.table("document_chunks").select(
        "id", count="exact"
    ).eq("indexing_run_id", indexing_run_id).not_.is_("embedding_1024", "null").execute()
    
    chunks_with_embeddings = with_embeddings_response.count if hasattr(with_embeddings_response.count, '__call__') else len(with_embeddings_response.data)
    print(f"2. Chunks with embeddings: {chunks_with_embeddings}")
    
    # 3. Count chunks without embeddings
    without_embeddings = total_chunks - chunks_with_embeddings
    print(f"3. Chunks WITHOUT embeddings: {without_embeddings}")
    
    if without_embeddings > 0:
        print("   ⚠️ WARNING: Some chunks are missing embeddings!")
    else:
        print("   ✅ All chunks have embeddings")
    
    # 4. Check if HNSW index exists
    print(f"\n4. Checking HNSW index status...")
    
    # Query to check index existence
    index_check_query = """
    SELECT 
        indexname,
        indexdef,
        tablename
    FROM pg_indexes 
    WHERE tablename = 'document_chunks' 
    AND indexname LIKE '%hnsw%';
    """
    
    try:
        # Execute raw SQL to check indexes
        response = db.rpc('exec_sql', {'query': index_check_query}).execute()
        if response.data:
            print("   HNSW indexes found:")
            for idx in response.data:
                print(f"   - {idx['indexname']}")
        else:
            print("   ⚠️ No HNSW index found!")
    except:
        # Alternative approach using table info
        print("   Note: Cannot directly query indexes via RPC")
        print("   Expected index: idx_document_chunks_embedding_1024_hnsw")
    
    # 5. Test the match_chunks function with this run
    print(f"\n5. Testing match_chunks function...")
    
    # Create a simple test embedding
    test_embedding = [0.1] * 1024  # Simple test vector
    
    try:
        # Test with very low threshold to get all results
        test_response = db.rpc('match_chunks', {
            'query_embedding': test_embedding,
            'match_threshold': -1.0,  # Very low threshold
            'match_count': 200,
            'indexing_run_id_filter': indexing_run_id
        }).execute()
        
        results_from_function = len(test_response.data) if test_response.data else 0
        print(f"   match_chunks returned: {results_from_function} results")
        
        if results_from_function < chunks_with_embeddings:
            print(f"   ⚠️ Function returns fewer results ({results_from_function}) than chunks with embeddings ({chunks_with_embeddings})")
            print(f"   Missing: {chunks_with_embeddings - results_from_function} chunks")
        else:
            print(f"   ✅ Function can access all chunks")
            
    except Exception as e:
        print(f"   ❌ Error testing match_chunks: {e}")
    
    # 6. Sample some chunks to verify embedding format
    print(f"\n6. Sampling chunk embeddings...")
    
    sample_response = db.table("document_chunks").select(
        "id,embedding_1024"
    ).eq("indexing_run_id", indexing_run_id).not_.is_("embedding_1024", "null").limit(3).execute()
    
    if sample_response.data:
        for i, chunk in enumerate(sample_response.data, 1):
            embedding_str = str(chunk['embedding_1024'])[:100]  # First 100 chars
            print(f"   Sample {i} (ID: {chunk['id'][:8]}...): {embedding_str}...")
            
            # Check if it's a proper array format
            if embedding_str.startswith('[') and ',' in embedding_str:
                print(f"      ✅ Proper array format")
            else:
                print(f"      ⚠️ Unusual embedding format")
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total chunks: {total_chunks}")
    print(f"With embeddings: {chunks_with_embeddings}")
    print(f"Coverage: {(chunks_with_embeddings/total_chunks*100):.1f}%" if total_chunks > 0 else "N/A")
    
    return {
        'total_chunks': total_chunks,
        'chunks_with_embeddings': chunks_with_embeddings,
        'missing_embeddings': without_embeddings
    }


if __name__ == "__main__":
    indexing_run_id = "a7f5598e-a679-4d5f-a41c-298d6403812e"
    check_index_coverage(indexing_run_id)