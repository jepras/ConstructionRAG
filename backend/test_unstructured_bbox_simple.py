#!/usr/bin/env python3
"""Test Unstructured bbox extraction with coordinate conversion fix."""

import sys
import json
import asyncio
import uuid
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline.indexing.steps.partition import PartitionStep
from src.pipeline.shared.models import DocumentInput

async def test_unstructured_bbox():
    """Test Unstructured bbox extraction with the mole-scannable.pdf."""
    
    test_file = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/small-complicated/mole-scannable.pdf"
    
    print("\n" + "=" * 60)
    print("TESTING UNSTRUCTURED BBOX EXTRACTION")
    print("=" * 60)
    print(f"\nFile: {Path(test_file).name}")
    
    # Test Unstructured only
    processor_config = {"processor": "unstructured", "ocr_languages": ["dan"], "enable_ocr": True}
    
    print(f"\n--- Testing unstructured processor ---")  
    partition_step = PartitionStep(config=processor_config)
    doc_input = DocumentInput(
        document_id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4()),
        file_path=test_file,
        filename=Path(test_file).name,
        user_id=None,
        upload_type="email",
        project_id=None,
        index_run_id=None
    )
    
    print("Processing document... this may take a minute for OCR...")
    
    partition_result = await partition_step.process({
        "documents": [doc_input],
        "file_paths": {doc_input.document_id: test_file}
    })
    
    partition_output = partition_result['partition_results'][doc_input.document_id]
    text_count = len(partition_output.get('text_elements', []))
    table_count = len(partition_output.get('table_elements', []))
    
    # Check bbox in partition output with detailed logging
    print(f"\n  Extracted: {text_count} text elements, {table_count} tables")
    print(f"\n  Checking first 10 text elements for bbox:")
    print("  " + "=" * 50)
    
    bbox_count = 0
    for i, elem in enumerate(partition_output.get('text_elements', [])[:10]):
        metadata = elem.get('metadata', {})
        bbox = metadata.get('bbox')
        
        if bbox:
            bbox_count += 1
            print(f"  ✅ Element {i}: HAS BBOX")
            print(f"     Text: {elem.get('text', '')[:50]}...")
            print(f"     Page: {metadata.get('page_number')}")
            print(f"     Bbox: {bbox}")
            
            # Check if values are reasonable
            if all(isinstance(x, (int, float)) for x in bbox):
                x0, y0, x1, y1 = bbox
                width = x1 - x0
                height = y1 - y0
                print(f"     Dimensions: {width:.1f} x {height:.1f} points")
                
                # PDF pages are typically ~600x850 points
                if x0 < 0 or y0 < 0 or x1 > 1000 or y1 > 1200:
                    print(f"     ⚠️  WARNING: Bbox might be out of typical page bounds")
        else:
            print(f"  ❌ Element {i}: NO BBOX")
            print(f"     Text: {elem.get('text', '')[:50]}...")
    
    print(f"\n  Summary: {bbox_count}/10 elements have bbox coordinates")
    
    if bbox_count == 0:
        print(f"\n  ❌ ERROR: No bbox found in unstructured output!")
        print(f"     This means coordinates=True may not be working")
        return False
    elif bbox_count < 5:
        print(f"\n  ⚠️  WARNING: Only {bbox_count}/10 elements have bbox")
        print(f"     Some elements may be missing coordinates")
    else:
        print(f"\n  ✅ SUCCESS: Bbox extraction is working!")
    
    return bbox_count > 0

if __name__ == "__main__":
    success = asyncio.run(test_unstructured_bbox())
    sys.exit(0 if success else 1)