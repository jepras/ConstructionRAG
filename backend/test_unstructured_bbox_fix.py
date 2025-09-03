#!/usr/bin/env python3
"""Test that Unstructured bbox extraction now works correctly with coordinate conversion."""

import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline.indexing.steps.partition import PartitionStep
from src.pipeline.shared.models import DocumentInput, UploadType
import asyncio
import uuid

# Test file
test_file = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"

async def test_unstructured_bbox():
    """Test Unstructured bbox extraction with new coordinate conversion."""
    print("=" * 60)
    print("TESTING UNSTRUCTURED BBOX WITH COORDINATE CONVERSION")
    print("=" * 60)
    
    # Create partition step
    step = PartitionStep(config={
        "processor": "unstructured",
        "ocr_languages": ["dan"],
        "enable_ocr": True
    })
    
    # Create document input
    doc_id = uuid.uuid4()
    run_id = uuid.uuid4()
    doc_input = DocumentInput(
        document_id=doc_id,
        run_id=run_id,
        file_path=test_file,
        filename=Path(test_file).name,
        upload_type=UploadType.EMAIL,
        user_id=None,
        project_id=None,
        index_run_id=None
    )
    
    print(f"\nProcessing: {test_file}")
    print("Using processor: unstructured")
    
    # Process document
    result = await step.process({
        "documents": [doc_input],
        "file_paths": {doc_input.id: test_file}
    })
    
    # Check bbox in results
    partition_results = result["partition_results"][doc_input.id]
    
    print(f"\nExtracted {len(partition_results['text_elements'])} text elements")
    
    # Check first few elements for bbox
    elements_with_bbox = 0
    for i, elem in enumerate(partition_results['text_elements'][:5]):
        metadata = elem.get('metadata', {})
        bbox = metadata.get('bbox')
        
        if bbox:
            elements_with_bbox += 1
            print(f"\n✅ Element {i}: HAS BBOX")
            print(f"   Text: {elem['text'][:50]}...")
            print(f"   Page: {metadata.get('page_number')}")
            print(f"   Bbox: {bbox}")
            
            # Check if bbox values are reasonable (in PDF points)
            if all(isinstance(x, (int, float)) for x in bbox):
                x0, y0, x1, y1 = bbox
                width = x1 - x0
                height = y1 - y0
                print(f"   Dimensions: {width:.1f} x {height:.1f} points")
                
                # PDF pages are typically ~600x850 points
                if x0 < 0 or y0 < 0 or x1 > 1000 or y1 > 1200:
                    print(f"   ⚠️  WARNING: Bbox might be out of typical page bounds")
                else:
                    print(f"   ✓  Bbox appears to be in correct coordinate space")
        else:
            print(f"\n❌ Element {i}: NO BBOX")
            print(f"   Text: {elem['text'][:50]}...")
    
    print(f"\n{'=' * 40}")
    print(f"Summary: {elements_with_bbox}/5 elements have bbox")
    
    if elements_with_bbox == 0:
        print("❌ No bbox data found - coordinate extraction may have failed")
        print("\nPossible issues:")
        print("1. Unstructured didn't return coordinates (check coordinates=True)")
        print("2. Coordinate system conversion failed")
        print("3. Elements don't have metadata.coordinates attribute")
    else:
        print("✅ Bbox extraction is working!")
    
    return elements_with_bbox > 0

if __name__ == "__main__":
    success = asyncio.run(test_unstructured_bbox())
    sys.exit(0 if success else 1)