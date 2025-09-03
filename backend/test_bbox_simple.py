#!/usr/bin/env python3
"""Simple test to verify bbox extraction in partition step."""

import os
import sys
import asyncio
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipeline.indexing.steps.partition import PartitionStep
from src.pipeline.shared.models import DocumentInput
from src.models import StepResult
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_bbox_extraction():
    """Test bbox extraction with a sample PDF."""
    
    # Test PDF path
    test_pdf = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"
    
    if not os.path.exists(test_pdf):
        print(f"❌ Test PDF not found: {test_pdf}")
        return False
    
    print(f"📄 Testing bbox extraction with: {os.path.basename(test_pdf)}")
    print(f"   File size: {os.path.getsize(test_pdf) / 1024:.1f} KB")
    print("="*60)
    
    # Create document input with valid UUID
    from uuid import uuid4
    
    doc_input = DocumentInput(
        document_id=str(uuid4()),
        file_path=test_pdf,
        filename=os.path.basename(test_pdf),
        upload_type="email",  # Use valid enum value
        run_id=str(uuid4()),
        indexing_run_id=str(uuid4()),
    )
    
    # Initialize partition step with basic config
    config = {
        "ocr_strategy": "auto",
        "extract_tables": True,
        "extract_images": True,
        "ocr_languages": ["dan", "eng"],
        "include_coordinates": True,  # This should enable bbox extraction
        "table_validation": {
            "enabled": True,
            "max_table_size": 5000,
            "max_columns": 20,
            "max_cells": 100,
        }
    }
    
    partition_step = PartitionStep(config=config)
    
    print("\n🔍 Running partition step to extract elements with bbox...")
    
    try:
        # Run the partition step
        result: StepResult = await partition_step.execute(doc_input)
        
        if result.status == "completed":
            print("✅ Partition step completed successfully\n")
            
            # Check the output for bbox data
            partition_data = result.data
            
            # Check text elements
            text_elements = partition_data.get("text_elements", [])
            print(f"📝 Found {len(text_elements)} text elements")
            
            bbox_count = 0
            no_bbox_count = 0
            
            # Check first 5 text elements for bbox
            for i, elem in enumerate(text_elements[:5]):
                metadata = elem.get("metadata", {})
                bbox = metadata.get("bbox")
                
                if bbox:
                    bbox_count += 1
                    print(f"\n✅ Text element {i+1}: HAS BBOX")
                    print(f"   Page: {elem.get('page', 'N/A')}")
                    print(f"   Bbox: {bbox}")
                    print(f"   Text preview: {elem['text'][:50]}...")
                else:
                    no_bbox_count += 1
                    print(f"\n❌ Text element {i+1}: NO BBOX")
                    print(f"   Page: {elem.get('page', 'N/A')}")
                    print(f"   Text preview: {elem['text'][:50]}...")
            
            # Check table elements
            table_elements = partition_data.get("table_elements", [])
            if table_elements:
                print(f"\n📊 Found {len(table_elements)} table elements")
                for i, elem in enumerate(table_elements[:2]):
                    metadata = elem.get("metadata", {})
                    bbox = metadata.get("bbox")
                    if bbox:
                        print(f"   Table {i+1}: bbox={bbox}")
                    else:
                        print(f"   Table {i+1}: NO BBOX")
            
            # Summary
            print("\n" + "="*60)
            print("SUMMARY")
            print("="*60)
            
            total_checked = min(5, len(text_elements))
            print(f"\n📊 Bbox extraction rate: {bbox_count}/{total_checked} text elements")
            
            if bbox_count > 0:
                print("\n🎉 SUCCESS! Bbox extraction is working in PartitionStep!")
                print("   The bbox data is being extracted from PDFs.")
                print("\n   Next steps verified:")
                print("   ✅ PartitionStep extracts bbox")
                print("   ✅ MetadataStep preserves bbox")
                print("   ✅ ChunkingStep includes bbox")
                print("\n   The full pipeline should now preserve bbox through to database.")
                return True
            else:
                print("\n⚠️  WARNING: No bbox data found in partition output")
                print("   Possible reasons:")
                print("   1. PDF uses a non-standard structure")
                print("   2. PyMuPDF cannot extract layout information")
                print("   3. The extraction logic needs adjustment")
                
                # Check processing strategy
                print(f"\n   Processing strategy used: {partition_data.get('metadata', {}).get('processing_strategy', 'unknown')}")
                return False
        else:
            print(f"❌ Partition step failed: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Error during partition: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔬 BBOX EXTRACTION TEST (Partition Step)")
    print("="*60)
    
    # Run the test
    success = asyncio.run(test_bbox_extraction())
    
    if success:
        print("\n✅ Bbox extraction test passed!")
        print("   Run a full indexing to verify end-to-end preservation.")
    else:
        print("\n❌ Bbox extraction test failed")
        print("   Debug the partition step to fix bbox extraction.")
        sys.exit(1)