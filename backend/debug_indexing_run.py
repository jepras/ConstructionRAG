#!/usr/bin/env python
"""
Debug script to check why HNSW works for some indexing runs but not others.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_supabase_admin_client, get_supabase_client

def check_indexing_run(indexing_run_id: str, use_admin: bool = True):
    """Check what's in the database for a specific indexing run"""
    
    db = get_supabase_admin_client() if use_admin else get_supabase_client()
    
    print(f"\n{'='*60}")
    print(f"Checking indexing run: {indexing_run_id}")
    print(f"Using {'admin' if use_admin else 'anon'} client")
    print(f"{'='*60}")
    
    # 1. Check if the indexing run exists
    print("\n1. Checking indexing_runs table:")
    run_response = db.table("indexing_runs").select("*").eq("id", indexing_run_id).execute()
    if run_response.data:
        run = run_response.data[0]
        print(f"   ✓ Found indexing run")
        print(f"   - access_level: {run.get('access_level')}")
        print(f"   - upload_type: {run.get('upload_type')}")
        print(f"   - user_id: {run.get('user_id')}")
        print(f"   - project_id: {run.get('project_id')}")
    else:
        print(f"   ✗ Indexing run NOT found")
        return
    
    # 2. Check chunks with embeddings
    print("\n2. Checking document_chunks with embeddings:")
    chunks_response = (
        db.table("document_chunks")
        .select("id, indexing_run_id")
        .eq("indexing_run_id", indexing_run_id)
        .not_.is_("embedding_1024", "null")
        .limit(5)
        .execute()
    )
    
    if chunks_response.data:
        print(f"   ✓ Found {len(chunks_response.data)} chunks with embeddings")
        for chunk in chunks_response.data[:3]:
            print(f"   - Chunk ID: {chunk['id']}")
            print(f"   - Indexing Run ID in chunk: {chunk['indexing_run_id']}")
    else:
        print(f"   ✗ No chunks with embeddings found")
    
    # 3. Count total chunks
    print("\n3. Counting all chunks for this run:")
    all_chunks = (
        db.table("document_chunks")
        .select("id", count="exact")
        .eq("indexing_run_id", indexing_run_id)
        .execute()
    )
    print(f"   Total chunks: {all_chunks.count if hasattr(all_chunks, 'count') else len(all_chunks.data)}")
    
    # 4. Count chunks without embeddings
    no_embed_chunks = (
        db.table("document_chunks")
        .select("id", count="exact")
        .eq("indexing_run_id", indexing_run_id)
        .is_("embedding_1024", "null")
        .execute()
    )
    print(f"   Chunks without embeddings: {no_embed_chunks.count if hasattr(no_embed_chunks, 'count') else len(no_embed_chunks.data)}")
    
    # 5. Test the match_chunks function directly
    print("\n4. Testing match_chunks RPC function:")
    try:
        # Create a dummy embedding (all zeros)
        dummy_embedding = [0.0] * 1024
        
        rpc_params = {
            'query_embedding': dummy_embedding,
            'match_threshold': 0.0,
            'match_count': 5,
            'indexing_run_id_filter': indexing_run_id
        }
        
        response = db.rpc('match_chunks', rpc_params).execute()
        
        if response.data:
            print(f"   ✓ RPC returned {len(response.data)} results")
        else:
            print(f"   ✗ RPC returned no results")
            
    except Exception as e:
        print(f"   ✗ RPC failed: {e}")
    
    # 6. Check UUID format
    print("\n5. UUID format check:")
    print(f"   Input ID: {indexing_run_id}")
    print(f"   Type: {type(indexing_run_id)}")
    print(f"   Length: {len(indexing_run_id)}")
    
    # Try to get one chunk and see its exact indexing_run_id format
    sample_chunk = (
        db.table("document_chunks")
        .select("indexing_run_id")
        .eq("indexing_run_id", indexing_run_id)
        .limit(1)
        .execute()
    )
    
    if sample_chunk.data:
        stored_id = sample_chunk.data[0]['indexing_run_id']
        print(f"   Stored ID: {stored_id}")
        print(f"   Type: {type(stored_id)}")
        print(f"   Match: {stored_id == indexing_run_id}")
        print(f"   String match: {str(stored_id) == str(indexing_run_id)}")


if __name__ == "__main__":
    # Test the working run
    print("\n" + "="*80)
    print("TESTING WORKING RUN (returns HNSW results)")
    print("="*80)
    check_indexing_run("1ed7dc55-25ea-4b37-8f03-33d9f7aeeff8", use_admin=True)
    
    # Test the failing run
    print("\n" + "="*80)
    print("TESTING FAILING RUN (returns no HNSW results)")
    print("="*80)
    check_indexing_run("a7f5598e-a679-4d5f-a41c-298d6403812e", use_admin=True)
    
    # Also test with anon client
    print("\n" + "="*80)
    print("TESTING FAILING RUN WITH ANON CLIENT")
    print("="*80)
    check_indexing_run("a7f5598e-a679-4d5f-a41c-298d6403812e", use_admin=False)
