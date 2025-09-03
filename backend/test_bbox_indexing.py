#!/usr/bin/env python3
"""Test script to index a PDF and verify bbox preservation."""

import os
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipeline.indexing.orchestrator import IndexingOrchestrator
from src.pipeline.shared.models import DocumentInput
from src.config.database import get_supabase_client
from src.services.config_service import ConfigService
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_bbox_indexing():
    """Test bbox preservation with a sample PDF."""
    
    # Test PDF path
    test_pdf = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"
    
    if not os.path.exists(test_pdf):
        print(f"❌ Test PDF not found: {test_pdf}")
        return None
    
    print(f"📄 Testing with PDF: {test_pdf}")
    print(f"   File size: {os.path.getsize(test_pdf) / 1024:.1f} KB")
    
    # Initialize database client
    db = get_supabase_client()
    
    # Create a test indexing run
    run_id = str(uuid4())
    print(f"\n🚀 Starting test indexing run: {run_id}")
    
    # Create indexing run record
    indexing_run = {
        "id": run_id,
        "status": "processing",
        "upload_type": "test",
        "started_at": datetime.utcnow().isoformat(),
        "access_level": "private",
    }
    
    result = db.table("indexing_runs").insert(indexing_run).execute()
    print("✅ Created indexing run record")
    
    # Create document record
    doc_id = str(uuid4())
    document = {
        "id": doc_id,
        "filename": os.path.basename(test_pdf),
        "file_path": test_pdf,
        "file_size": os.path.getsize(test_pdf),
        "status": "pending",
        "upload_type": "test",
        "index_run_id": run_id,
        "access_level": "private",
    }
    
    result = db.table("documents").insert(document).execute()
    print("✅ Created document record")
    
    # Link document to indexing run
    link = {
        "indexing_run_id": run_id,
        "document_id": doc_id,
    }
    result = db.table("indexing_run_documents").insert(link).execute()
    print("✅ Linked document to indexing run")
    
    # Create document input
    doc_input = DocumentInput(
        document_id=doc_id,
        file_path=test_pdf,
        filename=os.path.basename(test_pdf),
        upload_type="test",
        indexing_run_id=run_id,
    )
    
    # Initialize orchestrator
    config_service = ConfigService()
    pipeline_config = config_service.get_pipeline_config()
    
    orchestrator = IndexingOrchestrator(
        config=pipeline_config,
        indexing_run_id=run_id,
        db_client=db,
    )
    
    print("\n📊 Running indexing pipeline...")
    print("   This will test bbox preservation through all steps:")
    print("   1. Partition (extract bbox)")
    print("   2. Metadata (preserve bbox)")
    print("   3. Enrichment (keep bbox)")
    print("   4. Chunking (include bbox)")
    print("   5. Embedding (store with bbox)")
    
    try:
        # Process the document
        await orchestrator.process_document(doc_input)
        
        # Update indexing run status
        db.table("indexing_runs").update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", run_id).execute()
        
        print("\n✅ Indexing completed successfully!")
        
        # Now verify bbox preservation
        print("\n" + "="*60)
        print("VERIFYING BBOX PRESERVATION")
        print("="*60)
        
        # Check chunks for bbox
        result = db.table("document_chunks").select("chunk_id, metadata, content").eq("indexing_run_id", run_id).limit(10).execute()
        
        if result.data:
            bbox_count = 0
            print(f"\nFound {len(result.data)} chunks (showing up to 10)")
            
            for i, chunk in enumerate(result.data[:5]):  # Show first 5
                meta = chunk['metadata']
                if isinstance(meta, str):
                    meta = json.loads(meta)
                
                if meta and 'bbox' in meta and meta['bbox']:
                    bbox_count += 1
                    print(f"\n✅ Chunk {i+1}: HAS BBOX")
                    print(f"   Page: {meta.get('page_number', 'N/A')}")
                    print(f"   Bbox: {meta['bbox']}")
                    print(f"   Content preview: {chunk['content'][:50]}...")
                else:
                    print(f"\n❌ Chunk {i+1}: NO BBOX")
                    print(f"   Content preview: {chunk['content'][:50]}...")
            
            print(f"\n📊 Result: {bbox_count}/{len(result.data)} chunks have bbox ({bbox_count/len(result.data)*100:.1f}%)")
            
            if bbox_count > 0:
                print("\n🎉 SUCCESS! Bbox preservation is working!")
            else:
                print("\n⚠️  WARNING: No bbox data found. Pipeline may need debugging.")
        else:
            print("❌ No chunks created")
        
        return run_id
        
    except Exception as e:
        print(f"\n❌ Error during indexing: {e}")
        import traceback
        traceback.print_exc()
        
        # Update status to failed
        db.table("indexing_runs").update({
            "status": "failed",
            "error_message": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", run_id).execute()
        
        return None

if __name__ == "__main__":
    print("🔬 BBOX PRESERVATION TEST")
    print("="*60)
    
    # Run the test
    run_id = asyncio.run(test_bbox_indexing())
    
    if run_id:
        print(f"\n✅ Test completed. Run ID: {run_id}")
        print(f"   Run full verification: python verify_bbox.py {run_id}")
    else:
        print("\n❌ Test failed")
        sys.exit(1)