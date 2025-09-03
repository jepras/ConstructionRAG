#!/usr/bin/env python3
"""Test bbox extraction from scanned documents through the full indexing pipeline."""

import sys
import json
import asyncio
import uuid
from pathlib import Path
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.services.beam_service import BeamService
from src.services.pipeline_service import PipelineService
from src.services.document_service import DocumentService
from src.config.database import get_supabase_admin_client
from src.config.settings import Settings

settings = Settings()

async def test_scanned_document_indexing():
    """Test indexing a scanned document with bbox extraction."""
    
    # Initialize services
    db = get_supabase_admin_client()
    beam_service = BeamService()
    pipeline_service = PipelineService()
    document_service = DocumentService(db=db)
    
    print("="*60)
    print("TESTING SCANNED DOCUMENT INDEXING WITH BBOX")
    print("="*60)
    
    # Test file (scanned document)
    test_file = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/small-complicated/mole-scannable.pdf"
    
    # Create a unique indexing run
    run_id = str(uuid.uuid4())
    print(f"\nIndexing Run ID: {run_id}")
    
    # Step 1: Upload document to storage
    print("\n1. UPLOADING DOCUMENT:")
    print("-"*40)
    
    try:
        # Create document record
        doc_result = db.table("documents").insert({
            "filename": "mole-scannable-test.pdf",
            "file_path": test_file,
            "file_size": Path(test_file).stat().st_size,
            "page_count": 4,
            "upload_type": "email"
        }).execute()
        
        document_id = doc_result.data[0]["id"]
        print(f"Document ID: {document_id}")
        
        # Create indexing run
        run_result = db.table("indexing_runs").insert({
            "id": run_id,
            "status": "processing",
            "upload_type": "email",
            "user_email": "test@example.com",
            "documents": [document_id],
            "started_at": datetime.utcnow().isoformat()
        }).execute()
        
        print(f"Indexing run created")
        
    except Exception as e:
        print(f"Error creating records: {e}")
        return
    
    # Step 2: Trigger indexing with Beam (with OCR strategy)
    print("\n2. TRIGGERING BEAM INDEXING:")
    print("-"*40)
    
    try:
        # Prepare document input
        document_input = {
            "document_id": document_id,
            "filename": "mole-scannable-test.pdf",
            "file_path": test_file,
            "upload_type": "email",
            "run_id": run_id
        }
        
        # Send to Beam with explicit OCR strategy
        config_overrides = {
            "indexing": {
                "partition": {
                    "ocr_strategy": "auto",  # Will detect scanned and use Unstructured
                    "extract_tables": True,
                    "extract_images": True,
                    "include_coordinates": True
                }
            }
        }
        
        print("Sending to Beam for processing...")
        beam_result = await beam_service.process_document(
            document_input,
            config_overrides=config_overrides
        )
        
        if beam_result and beam_result.get("task_id"):
            print(f"Beam task ID: {beam_result['task_id']}")
        else:
            print("Warning: No task ID returned from Beam")
        
    except Exception as e:
        print(f"Error triggering Beam: {e}")
        return
    
    # Step 3: Wait for processing to complete
    print("\n3. WAITING FOR PROCESSING:")
    print("-"*40)
    
    max_wait_time = 120  # seconds
    check_interval = 5  # seconds
    elapsed = 0
    
    while elapsed < max_wait_time:
        # Check run status
        run_check = db.table("indexing_runs").select("*").eq("id", run_id).execute()
        
        if run_check.data:
            status = run_check.data[0]["status"]
            print(f"  [{elapsed}s] Status: {status}")
            
            if status == "completed":
                print("\n✅ Indexing completed!")
                break
            elif status == "failed":
                print("\n❌ Indexing failed!")
                error = run_check.data[0].get("error_message", "Unknown error")
                print(f"Error: {error}")
                return
        
        time.sleep(check_interval)
        elapsed += check_interval
    
    if elapsed >= max_wait_time:
        print("\n⚠️ Timeout waiting for indexing to complete")
        return
    
    # Step 4: Check bbox in stored chunks
    print("\n4. CHECKING BBOX IN STORED CHUNKS:")
    print("-"*40)
    
    # Query chunks from database
    chunks_result = db.table("document_chunks").select("*").eq("indexing_run_id", run_id).limit(20).execute()
    
    if chunks_result.data:
        chunks = chunks_result.data
        print(f"Total chunks found: {len(chunks)}")
        
        # Check bbox presence
        chunks_with_bbox = 0
        bbox_samples = []
        
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            if metadata.get("bbox"):
                chunks_with_bbox += 1
                if len(bbox_samples) < 3:
                    bbox_samples.append({
                        "chunk_id": chunk["chunk_id"],
                        "bbox": metadata["bbox"],
                        "content": chunk["content"][:100] + "...",
                        "page": metadata.get("page_number")
                    })
        
        print(f"\nChunks with bbox: {chunks_with_bbox}/{len(chunks)}")
        
        if bbox_samples:
            print("\nSample chunks with bbox:")
            for i, sample in enumerate(bbox_samples, 1):
                print(f"\n  Sample {i}:")
                print(f"    Page: {sample.get('page', 'N/A')}")
                print(f"    Bbox: {sample['bbox']}")
                print(f"    Content: {sample['content']}")
        
        # Check if OCR was used
        step_results = db.table("indexing_step_results").select("*").eq("indexing_run_id", run_id).eq("step", "partition").execute()
        
        if step_results.data:
            partition_stats = step_results.data[0].get("summary_stats", {})
            processing_strategy = partition_stats.get("processing_strategy", "unknown")
            print(f"\nProcessing strategy used: {processing_strategy}")
            
            if "hybrid" in processing_strategy.lower() or "ocr" in processing_strategy.lower():
                print("✅ OCR extraction was used!")
            else:
                print("⚠️ OCR extraction was NOT used - document may not have been detected as scanned")
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        if chunks_with_bbox > 0:
            success_rate = (chunks_with_bbox / len(chunks)) * 100
            print(f"✅ SUCCESS: {success_rate:.1f}% of chunks have bbox coordinates!")
            print(f"   - Total chunks: {len(chunks)}")
            print(f"   - Chunks with bbox: {chunks_with_bbox}")
            print(f"   - Processing strategy: {processing_strategy}")
        else:
            print("❌ FAILURE: No chunks have bbox coordinates")
            print("   This might indicate:")
            print("   - OCR extraction failed")
            print("   - Bbox coordinates were not preserved through pipeline")
            print("   - Document was not detected as scanned")
    else:
        print("❌ No chunks found in database")
    
    # Clean up
    print("\n5. CLEANUP:")
    print("-"*40)
    
    try:
        # Delete test data
        db.table("document_chunks").delete().eq("indexing_run_id", run_id).execute()
        db.table("indexing_step_results").delete().eq("indexing_run_id", run_id).execute()
        db.table("indexing_runs").delete().eq("id", run_id).execute()
        db.table("documents").delete().eq("id", document_id).execute()
        print("✅ Test data cleaned up")
    except Exception as e:
        print(f"⚠️ Cleanup error: {e}")

if __name__ == "__main__":
    asyncio.run(test_scanned_document_indexing())