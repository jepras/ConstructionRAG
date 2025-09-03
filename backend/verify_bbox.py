#!/usr/bin/env python3
"""Script to verify bbox preservation in document chunks after indexing."""

import os
import sys
import json
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def verify_bbox_preservation(run_id=None):
    """Verify that bbox data is preserved through the pipeline."""
    
    # Initialize Supabase client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        print("❌ Error: SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
        return
    
    db = create_client(url, key)
    
    # If no run_id provided, get the latest one
    if not run_id:
        print("Fetching latest indexing run...")
        result = db.table('indexing_runs').select('id, created_at').order('created_at', desc=True).limit(1).execute()
        if result.data:
            run_id = result.data[0]['id']
            created_at = result.data[0]['created_at']
            print(f"Using latest run: {run_id} (created: {created_at})")
        else:
            print("❌ No indexing runs found")
            return
    else:
        print(f"Checking indexing run: {run_id}")
    
    # Check chunks for bbox data
    print("\n" + "="*60)
    print("CHECKING DOCUMENT CHUNKS FOR BBOX DATA")
    print("="*60)
    
    result = db.table('document_chunks').select('chunk_id, metadata, content').eq('indexing_run_id', run_id).limit(20).execute()
    
    if not result.data:
        print("❌ No chunks found for this indexing run")
        return
    
    print(f"\nFound {len(result.data)} chunks (showing up to 20)")
    print("-"*60)
    
    bbox_count = 0
    bbox_samples = []
    no_bbox_samples = []
    
    for i, chunk in enumerate(result.data):
        meta = chunk['metadata']
        if isinstance(meta, str):
            meta = json.loads(meta)
        
        content_preview = chunk['content'][:50] + "..." if len(chunk['content']) > 50 else chunk['content']
        
        if meta and 'bbox' in meta and meta['bbox']:
            bbox_count += 1
            bbox_data = meta['bbox']
            page_num = meta.get('page_number', 'N/A')
            
            print(f"\n✅ Chunk {i+1}: HAS BBOX")
            print(f"   Page: {page_num}")
            print(f"   Bbox: {bbox_data}")
            print(f"   Content: {content_preview}")
            
            if len(bbox_samples) < 3:
                bbox_samples.append({
                    'chunk_id': chunk['chunk_id'],
                    'page': page_num,
                    'bbox': bbox_data,
                    'content_preview': content_preview
                })
        else:
            print(f"\n❌ Chunk {i+1}: NO BBOX")
            print(f"   Page: {meta.get('page_number', 'N/A') if meta else 'N/A'}")
            print(f"   Content: {content_preview}")
            
            if len(no_bbox_samples) < 3:
                no_bbox_samples.append({
                    'chunk_id': chunk['chunk_id'],
                    'page': meta.get('page_number', 'N/A') if meta else 'N/A',
                    'content_preview': content_preview
                })
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    percentage = (bbox_count / len(result.data)) * 100 if result.data else 0
    print(f"\n📊 Bbox preservation rate: {bbox_count}/{len(result.data)} chunks ({percentage:.1f}%)")
    
    if bbox_count > 0:
        print(f"\n✅ SUCCESS: Bbox data is being preserved!")
        print(f"   {bbox_count} chunks have bounding box coordinates")
        
        if bbox_samples:
            print("\n📍 Sample chunks with bbox:")
            for sample in bbox_samples[:2]:
                print(f"   - Page {sample['page']}: bbox={sample['bbox']}")
    else:
        print(f"\n❌ FAILURE: No bbox data found in any chunks")
        print("   This might indicate:")
        print("   1. The PDF was processed before bbox preservation was implemented")
        print("   2. The pipeline modifications are not working correctly")
        print("   3. The PDF doesn't contain extractable text (scanned/image-only)")
    
    # Check if we need to re-index
    if bbox_count == 0:
        print("\n💡 Recommendation: Re-index a test PDF to verify bbox preservation")
        print("   Use: /Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf")
    
    return bbox_count > 0

if __name__ == "__main__":
    # Check if run_id provided as argument
    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if run_id == "--help":
        print("Usage: python verify_bbox.py [indexing_run_id]")
        print("  If no run_id provided, uses the latest indexing run")
        sys.exit(0)
    
    success = verify_bbox_preservation(run_id)
    sys.exit(0 if success else 1)