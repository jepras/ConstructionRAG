#!/usr/bin/env python3
"""Test bbox flow through actual PartitionStep execution."""

import sys
import json
import asyncio
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline.indexing.steps.partition import PartitionStep
from src.pipeline.shared.models import DocumentInput
from src.models import StepResult

test_pdf = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"

async def test_bbox_flow():
    print("="*60)
    print("FULL BBOX FLOW TEST")
    print("="*60)
    
    # Create document input
    doc_input = DocumentInput(
        document_id=str(uuid4()),
        file_path=test_pdf,
        filename="test-with-little-variety.pdf",
        upload_type="email",
        run_id=str(uuid4()),
        indexing_run_id=str(uuid4()),
    )
    
    # Initialize partition step
    config = {
        "ocr_strategy": "auto",
        "extract_tables": True,
        "extract_images": True,
        "include_coordinates": True,
        "ocr_languages": ["dan", "eng"],
        "table_validation": {
            "enabled": False  # Disable to avoid validation errors
        }
    }
    
    partition_step = PartitionStep(config=config)
    
    print("\n1. RUNNING PARTITION STEP...")
    print("-"*40)
    
    try:
        result: StepResult = await partition_step.execute(doc_input)
        
        if result.status == "completed":
            print("✅ Partition step completed")
            
            # Check text_elements in result
            partition_data = result.data
            text_elements = partition_data.get("text_elements", [])
            
            print(f"\nText elements in result: {len(text_elements)}")
            
            # Check bbox presence
            with_bbox = 0
            null_bbox = 0
            no_bbox = 0
            
            for elem in text_elements:
                meta = elem.get("metadata", {})
                if "bbox" not in meta:
                    no_bbox += 1
                elif meta["bbox"] is None:
                    null_bbox += 1
                else:
                    with_bbox += 1
            
            print(f"\nBbox Status in text_elements:")
            print(f"  ✅ With bbox: {with_bbox}")
            print(f"  ⚠️  Null bbox: {null_bbox}")
            print(f"  ❌ No bbox key: {no_bbox}")
            
            # Show samples
            print("\nSample elements:")
            for i, elem in enumerate(text_elements[:3]):
                meta = elem.get("metadata", {})
                bbox = meta.get("bbox", "NO KEY")
                text = elem.get("text", "")[:50]
                print(f"\n  Element {i+1}:")
                print(f"    Text: {text}...")
                print(f"    Bbox: {bbox}")
                if bbox and bbox != "NO KEY":
                    print(f"    Bbox type: {type(bbox)}")
            
            # Check table elements
            table_elements = partition_data.get("table_elements", [])
            if table_elements:
                print(f"\nTable elements: {len(table_elements)}")
                for i, elem in enumerate(table_elements[:2]):
                    meta = elem.get("metadata", {})
                    bbox = meta.get("bbox", "NO KEY")
                    print(f"  Table {i+1} bbox: {bbox}")
            
            # Save full output for inspection
            output = {
                "summary": {
                    "total_text_elements": len(text_elements),
                    "with_bbox": with_bbox,
                    "null_bbox": null_bbox,
                    "no_bbox_key": no_bbox
                },
                "sample_elements": [
                    {
                        "id": elem.get("id"),
                        "page": elem.get("page"),
                        "metadata": elem.get("metadata"),
                        "text_preview": elem.get("text", "")[:100]
                    }
                    for elem in text_elements[:5]
                ]
            }
            
            with open("bbox_flow_output.json", "w") as f:
                json.dump(output, f, indent=2, default=str)
            
            print("\n\nFull output saved to: bbox_flow_output.json")
            
            # Final verdict
            print("\n" + "="*60)
            print("VERDICT")
            print("="*60)
            
            if with_bbox > 0:
                percentage = (with_bbox / len(text_elements)) * 100
                print(f"✅ SUCCESS: {percentage:.1f}% of elements have bbox!")
                print(f"   Bbox is being extracted and preserved in PartitionStep")
            elif null_bbox > 0:
                print("⚠️  PARTIAL: Bbox key exists but values are null")
                print("   Check if bbox is being set to None somewhere")
            else:
                print("❌ FAILURE: No bbox data found")
                print("   Bbox extraction is not working")
                
        else:
            print(f"❌ Partition step failed: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bbox_flow())