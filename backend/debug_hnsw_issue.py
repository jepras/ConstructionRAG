#!/usr/bin/env python
"""
Debug why HNSW function returns limited results.
"""

import sys
from pathlib import Path
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_supabase_admin_client

def debug_hnsw_issue(indexing_run_id: str):
    """Debug the HNSW function issue"""
    
    db = get_supabase_admin_client()
    
    print(f"\n{'='*60}")
    print(f"DEBUGGING HNSW ISSUE")
    print(f"{'='*60}\n")
    
    # 1. First, let's check what the function definition looks like
    print("1. Checking function signature...")
    
    try:
        # Get function info
        func_info_query = """
        SELECT 
            proname as function_name,
            pg_get_function_arguments(oid) as arguments,
            pg_get_function_result(oid) as return_type,
            prosrc as source_code
        FROM pg_proc 
        WHERE proname = 'match_chunks';
        """
        
        # Try to get function definition via a simpler query
        simple_test = db.table("document_chunks").select(
            "id"
        ).eq("indexing_run_id", indexing_run_id).limit(1).execute()
        
        if simple_test.data:
            print(f"   ✅ Can query chunks table directly")
            
    except Exception as e:
        print(f"   Cannot directly query function definition: {e}")
    
    # 2. Test with a real embedding from the database
    print("\n2. Testing with a real embedding from the database...")
    
    # Get a sample chunk with embedding
    sample_chunk = db.table("document_chunks").select(
        "id,embedding_1024"
    ).eq("indexing_run_id", indexing_run_id).not_.is_("embedding_1024", "null").limit(1).execute()
    
    if sample_chunk.data and sample_chunk.data[0]['embedding_1024']:
        real_embedding = sample_chunk.data[0]['embedding_1024']
        chunk_id = sample_chunk.data[0]['id']
        
        print(f"   Using embedding from chunk: {chunk_id}")
        
        # Parse the embedding
        if isinstance(real_embedding, str):
            real_embedding = json.loads(real_embedding)
        
        # Test with this real embedding
        try:
            response = db.rpc('match_chunks', {
                'query_embedding': real_embedding,
                'match_threshold': -999.0,  # Extremely low threshold
                'match_count': 100,
                'indexing_run_id_filter': indexing_run_id
            }).execute()
            
            results = len(response.data) if response.data else 0
            print(f"   Results with real embedding: {results}")
            
            if response.data:
                # Check if the source chunk is in results
                found_self = any(r['id'] == chunk_id for r in response.data)
                print(f"   Found self in results: {found_self}")
                
                # Check similarity scores
                similarities = [r.get('similarity', 0) for r in response.data[:5]]
                print(f"   Top 5 similarities: {similarities}")
                
        except Exception as e:
            print(f"   Error with real embedding: {e}")
    
    # 3. Test without indexing_run_id filter
    print("\n3. Testing WITHOUT indexing_run_id filter...")
    
    test_embedding = [0.1] * 1024
    
    try:
        response_no_filter = db.rpc('match_chunks', {
            'query_embedding': test_embedding,
            'match_threshold': -999.0,
            'match_count': 100,
            'indexing_run_id_filter': None  # No filter
        }).execute()
        
        results_no_filter = len(response_no_filter.data) if response_no_filter.data else 0
        print(f"   Results without filter: {results_no_filter}")
        
        if response_no_filter.data:
            # Count how many are from our indexing run
            from_our_run = sum(1 for r in response_no_filter.data 
                              if str(r.get('indexing_run_id')) == indexing_run_id)
            print(f"   From our indexing run: {from_our_run}")
            
            # Show unique indexing runs in results
            unique_runs = set(str(r.get('indexing_run_id')) for r in response_no_filter.data)
            print(f"   Unique indexing runs in results: {len(unique_runs)}")
            
    except Exception as e:
        print(f"   Error without filter: {e}")
    
    # 4. Direct SQL-like query to understand the issue
    print("\n4. Testing direct queries to understand filtering...")
    
    # Count chunks that match our indexing_run_id
    direct_count = db.table("document_chunks").select(
        "id", count="exact"
    ).eq("indexing_run_id", indexing_run_id).not_.is_("embedding_1024", "null").execute()
    
    print(f"   Direct count with indexing_run_id: {direct_count.count if hasattr(direct_count, 'count') else len(direct_count.data)}")
    
    # Get a few chunks to see their structure
    sample_chunks = db.table("document_chunks").select(
        "id,indexing_run_id,embedding_1024"
    ).eq("indexing_run_id", indexing_run_id).not_.is_("embedding_1024", "null").limit(5).execute()
    
    if sample_chunks.data:
        print(f"\n   Sample chunk indexing_run_ids:")
        for chunk in sample_chunks.data:
            run_id = chunk['indexing_run_id']
            print(f"     {chunk['id'][:8]}... -> {run_id}")
            
    # 5. Test the alternative function if it exists
    print("\n5. Testing alternative function (match_chunks_with_threshold)...")
    
    try:
        response_alt = db.rpc('match_chunks_with_threshold', {
            'query_embedding': test_embedding,
            'match_threshold': -999.0,
            'match_count': 100,
            'indexing_run_id_filter': indexing_run_id
        }).execute()
        
        results_alt = len(response_alt.data) if response_alt.data else 0
        print(f"   Results with alternative function: {results_alt}")
        
    except Exception as e:
        print(f"   Alternative function not available or error: {e}")
    
    print(f"\n{'='*60}")
    print("ANALYSIS")
    print(f"{'='*60}")
    
    print("""
The issue appears to be one of:
1. The function update didn't actually take effect
2. The indexing_run_id filter is not working correctly
3. The HNSW index itself has an issue
4. The vector similarity calculation is returning very low scores

Next steps:
- Check if the function source code was actually updated
- Test with raw SQL queries if possible
- Consider recreating the HNSW index
""")


if __name__ == "__main__":
    indexing_run_id = "a7f5598e-a679-4d5f-a41c-298d6403812e"
    debug_hnsw_issue(indexing_run_id)