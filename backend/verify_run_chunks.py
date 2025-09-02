#!/usr/bin/env python
"""
Verify what's in the specific indexing run and why similarities are so low.
"""

import asyncio
import sys
from pathlib import Path
import random

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_supabase_admin_client
from src.pipeline.shared.embedding_service import VoyageEmbeddingService

async def verify_run_chunks():
    """Check chunks in the specific run"""
    
    db = get_supabase_admin_client()
    embedding_service = VoyageEmbeddingService()
    
    indexing_run_id = "a7f5598e-a679-4d5f-a41c-298d6403812e"
    query = "Hvor mange TVO anlæg skal der installeres"
    
    print(f"\n{'='*60}")
    print(f"ANALYZING INDEXING RUN: {indexing_run_id}")
    print(f"{'='*60}\n")
    
    # Get query embedding
    print(f"Query: {query}")
    query_embedding = await embedding_service.get_embedding(query)
    
    # 1. Sample some chunks from this run to check their content
    print("\n1. Sample chunks from this run:")
    print("-" * 40)
    
    sample_chunks = db.table("document_chunks").select(
        "id,content,metadata"
    ).eq("indexing_run_id", indexing_run_id).limit(10).execute()
    
    if sample_chunks.data:
        for i, chunk in enumerate(sample_chunks.data[:5], 1):
            content_preview = chunk['content'][:100].replace('\n', ' ')
            print(f"{i}. {content_preview}...")
            if chunk.get('metadata', {}).get('source_filename'):
                print(f"   Source: {chunk['metadata']['source_filename']}")
    
    # 2. Search for chunks with "TVO" in content
    print("\n2. Chunks containing 'TVO' keyword:")
    print("-" * 40)
    
    # Get ALL chunks from this run to search locally
    all_chunks = db.table("document_chunks").select(
        "id,content,embedding_1024"
    ).eq("indexing_run_id", indexing_run_id).execute()
    
    tvo_chunks = []
    for chunk in all_chunks.data:
        if 'TVO' in chunk['content'] or 'tvo' in chunk['content'].lower():
            tvo_chunks.append(chunk)
    
    print(f"Found {len(tvo_chunks)} chunks containing 'TVO'")
    
    if tvo_chunks:
        # Calculate similarities for TVO chunks
        import ast
        import math
        
        def cosine_similarity(vec1, vec2):
            if len(vec1) != len(vec2):
                return 0.0
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(b * b for b in vec2))
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            return dot_product / (magnitude1 * magnitude2)
        
        for chunk in tvo_chunks[:3]:
            content_preview = chunk['content'][:200].replace('\n', ' ')
            print(f"\nChunk ID: {chunk['id']}")
            print(f"Content: {content_preview}...")
            
            # Calculate similarity
            if chunk.get('embedding_1024'):
                chunk_embedding = chunk['embedding_1024']
                if isinstance(chunk_embedding, str):
                    chunk_embedding = ast.literal_eval(chunk_embedding)
                
                similarity = cosine_similarity(query_embedding, chunk_embedding)
                print(f"Similarity to query: {similarity:.4f}")
    
    # 3. Check document diversity in this run
    print("\n3. Document diversity in this run:")
    print("-" * 40)
    
    doc_info = db.table("document_chunks").select(
        "document_id,metadata"
    ).eq("indexing_run_id", indexing_run_id).execute()
    
    unique_docs = set()
    unique_sources = set()
    
    for chunk in doc_info.data:
        unique_docs.add(chunk['document_id'])
        if chunk.get('metadata', {}).get('source_filename'):
            unique_sources.add(chunk['metadata']['source_filename'])
    
    print(f"Unique documents: {len(unique_docs)}")
    print(f"Unique source files: {len(unique_sources)}")
    
    if unique_sources:
        print("\nSource files:")
        for source in list(unique_sources)[:10]:
            print(f"  - {source}")
    
    # 4. Check if this is the right indexing run
    print("\n4. Indexing run metadata:")
    print("-" * 40)
    
    run_info = db.table("indexing_runs").select(
        "id,created_at,status,metadata"
    ).eq("id", indexing_run_id).execute()
    
    if run_info.data:
        run = run_info.data[0]
        print(f"Created: {run['created_at']}")
        print(f"Status: {run['status']}")
        if run.get('metadata'):
            print(f"Metadata: {run['metadata']}")
    
    print(f"\n{'='*60}")
    print("CONCLUSION")
    print(f"{'='*60}")
    print("""
Based on the analysis, we can determine:
1. Whether the chunks contain relevant content for the query
2. Why similarities are so low for this specific run
3. Whether this is the correct indexing run to search
""")

if __name__ == "__main__":
    asyncio.run(verify_run_chunks())