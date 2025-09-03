#!/usr/bin/env python3
"""Test bbox preservation through the pipeline steps without database."""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Test imports
from src.pipeline.indexing.steps.partition import PartitionStep

test_pdf = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"

print("="*60)
print("PIPELINE BBOX TEST")
print("="*60)

# Step 1: Test PartitionStep directly
print("\n1. TESTING PARTITIONSTEP:")
print("-"*40)

# Initialize with config
config = {
    "ocr_strategy": "auto",
    "extract_tables": True,
    "extract_images": True,
    "include_coordinates": True,
    "table_validation": {"enabled": False}  # Disable to avoid errors
}

partition_step = PartitionStep(config=config)

# Create a minimal test by directly calling the text extraction method
import fitz
doc = fitz.open(test_pdf)

# Call the internal method that extracts text
partitioner = partition_step
text_elements, raw_elements = partitioner.stage2_fast_text_extraction(test_pdf)

print(f"Text elements extracted: {len(text_elements)}")

# Check bbox in text_elements
bbox_count = 0
null_bbox_count = 0
no_bbox_count = 0

for i, elem in enumerate(text_elements[:5]):
    meta = elem.get("metadata", {})
    
    if "bbox" not in meta:
        no_bbox_count += 1
        print(f"\nElement {i+1}: NO BBOX KEY")
    elif meta["bbox"] is None:
        null_bbox_count += 1
        print(f"\nElement {i+1}: NULL BBOX")
    else:
        bbox_count += 1
        bbox = meta["bbox"]
        print(f"\nElement {i+1}: HAS BBOX")
        print(f"  Value: {bbox}")
        print(f"  Type: {type(bbox)}")

print(f"\n\nSummary after stage2_fast_text_extraction:")
print(f"  With bbox: {bbox_count}")
print(f"  Null bbox: {null_bbox_count}")
print(f"  No bbox key: {no_bbox_count}")

# Step 2: Test the filtering function
print("\n\n2. TESTING FILTER FUNCTION:")
print("-"*40)

filtered_elements = partitioner._filter_text_elements(text_elements)
print(f"Elements after filtering: {len(filtered_elements)}")

# Check bbox after filtering
bbox_after_filter = 0
for elem in filtered_elements[:5]:
    meta = elem.get("metadata", {})
    if meta.get("bbox"):
        bbox_after_filter += 1

print(f"Elements with bbox after filtering: {bbox_after_filter}/{min(5, len(filtered_elements))}")

# Step 3: Check metadata cleaning
print("\n\n3. TESTING METADATA CLEANING:")
print("-"*40)

if text_elements:
    original_meta = text_elements[0].get("metadata", {})
    cleaned_meta = partitioner._clean_metadata(original_meta)
    
    print(f"Original has bbox: {'bbox' in original_meta}")
    if "bbox" in original_meta:
        print(f"  Original bbox: {original_meta['bbox']}")
    
    print(f"Cleaned has bbox: {'bbox' in cleaned_meta}")
    if "bbox" in cleaned_meta:
        print(f"  Cleaned bbox: {cleaned_meta['bbox']}")

# Write detailed output
output = {
    "stage2_text_elements": [
        {
            "id": elem.get("id"),
            "metadata": elem.get("metadata"),
            "text_preview": elem.get("text", "")[:50]
        }
        for elem in text_elements[:3]
    ],
    "filtered_elements": [
        {
            "id": elem.get("id"),
            "metadata": elem.get("metadata"),
            "text_preview": elem.get("text", "")[:50]
        }
        for elem in filtered_elements[:3]
    ]
}

with open("pipeline_bbox_test.json", "w") as f:
    json.dump(output, f, indent=2, default=str)

print("\n\nDetailed output written to: pipeline_bbox_test.json")

doc.close()

print("\n" + "="*60)
print("CONCLUSION")
print("="*60)

if bbox_count > 0 and bbox_after_filter > 0:
    print("✅ Bbox is preserved through partition and filtering!")
elif bbox_count > 0 and bbox_after_filter == 0:
    print("❌ Bbox is extracted but lost during filtering!")
elif bbox_count == 0:
    print("❌ Bbox is not being extracted at all!")
    print("   Check if PyMuPDF extraction is working correctly")