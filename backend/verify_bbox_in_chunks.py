#!/usr/bin/env python3
"""Verify that bbox coordinates are stored in document chunks."""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_supabase_admin_client

def verify_bbox_in_chunks():
    """Check existing chunks for bbox coordinates."""
    
    db = get_supabase_admin_client()
    
    print("="*60)
    print("VERIFYING BBOX IN DOCUMENT CHUNKS")
    print("="*60)
    
    # Get recent indexing runs
    print("\n1. RECENT INDEXING RUNS:")
    print("-"*40)
    
    runs = db.table("indexing_runs").select("*").order("created_at", desc=True).limit(5).execute()
    
    if not runs.data:
        print("No indexing runs found")
        return
    
    for run in runs.data:
        print(f"\nRun ID: {run['id']}")
        print(f"  Status: {run['status']}")
        print(f"  Created: {run['created_at']}")
        print(f"  Upload type: {run.get('upload_type', 'N/A')}")
        
        # Check chunks for this run
        chunks = db.table("document_chunks").select("chunk_id, content, metadata").eq("indexing_run_id", run['id']).limit(10).execute()
        
        if chunks.data:
            print(f"  Chunks found: {len(chunks.data)}")
            
            # Check for bbox
            chunks_with_bbox = 0
            bbox_samples = []
            
            for chunk in chunks.data:
                metadata = chunk.get("metadata", {})
                if metadata.get("bbox"):
                    chunks_with_bbox += 1
                    if len(bbox_samples) < 2:
                        bbox_samples.append({
                            "chunk_id": chunk["chunk_id"],
                            "bbox": metadata["bbox"],
                            "content": chunk["content"][:50] + "...",
                            "page": metadata.get("page_number")
                        })
            
            if chunks_with_bbox > 0:
                print(f"  ✅ Chunks with bbox: {chunks_with_bbox}/{len(chunks.data)}")
                if bbox_samples:
                    for sample in bbox_samples:
                        print(f"     Sample bbox: {sample['bbox']} (page {sample.get('page', 'N/A')})")
            else:
                print(f"  ❌ No chunks with bbox coordinates")
        else:
            print(f"  No chunks found for this run")
    
    # Check overall statistics
    print("\n2. OVERALL BBOX STATISTICS:")
    print("-"*40)
    
    # Get total chunks with bbox
    all_chunks = db.table("document_chunks").select("metadata").limit(1000).execute()
    
    if all_chunks.data:
        total_chunks = len(all_chunks.data)
        chunks_with_bbox = sum(1 for c in all_chunks.data if c.get("metadata", {}).get("bbox"))
        
        print(f"Total chunks checked: {total_chunks}")
        print(f"Chunks with bbox: {chunks_with_bbox}")
        print(f"Percentage with bbox: {(chunks_with_bbox/total_chunks)*100:.1f}%")
        
        if chunks_with_bbox > 0:
            print("\n✅ BBOX COORDINATES ARE BEING STORED!")
        else:
            print("\n❌ NO BBOX COORDINATES FOUND IN ANY CHUNKS")
    else:
        print("No chunks found in database")

if __name__ == "__main__":
    verify_bbox_in_chunks()