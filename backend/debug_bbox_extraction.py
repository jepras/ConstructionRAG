#!/usr/bin/env python3
"""Debug script to trace bbox extraction through the pipeline."""

import json
import fitz  # PyMuPDF
from pathlib import Path

test_pdf = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"

print("="*60)
print("BBOX EXTRACTION DEBUG")
print("="*60)

# Step 1: Verify PyMuPDF can extract bbox
print("\n1. RAW PYMUPDF EXTRACTION:")
print("-"*40)
doc = fitz.open(test_pdf)
page = doc[0]

# Get text dict - this is what partition.py uses
text_dict = page.get_text("dict")
blocks = text_dict.get("blocks", [])

print(f"Total blocks on page 1: {len(blocks)}")

# Check first 3 text blocks
text_blocks_found = 0
for i, block in enumerate(blocks[:5]):
    if "lines" in block:  # Text block
        text_blocks_found += 1
        bbox = block.get("bbox")
        
        # Get text
        text = ""
        for line in block["lines"]:
            for span in line.get("spans", []):
                text += span.get("text", "")
        
        print(f"\nBlock {i+1}:")
        print(f"  Has bbox: {'YES' if bbox else 'NO'}")
        if bbox:
            print(f"  Bbox value: {bbox}")
            print(f"  Bbox type: {type(bbox)}")
        print(f"  Text: {text[:50]}...")

doc.close()

# Step 2: Test the exact code from partition.py
print("\n\n2. PARTITION.PY LOGIC TEST:")
print("-"*40)

doc = fitz.open(test_pdf)
page = doc[0]
page_index = 1

text_elements = []
raw_elements = []

try:
    text_dict = page.get_text("dict")
except Exception as e:
    print(f"Error getting text dict: {e}")
    text_dict = {"blocks": []}

# Process text blocks (exact logic from partition.py)
for block in text_dict.get("blocks", []):
    if "lines" in block:  # Text block
        block_text = ""
        block_bbox = block.get("bbox", [0, 0, 0, 0])  # This line from partition.py
        
        # Combine all lines in the block
        for line in block["lines"]:
            for span in line.get("spans", []):
                block_text += span.get("text", "")
        
        # Skip empty blocks
        if not block_text.strip():
            continue
        
        element_id = f"text_page{page_index}_block{len(text_elements)}"
        
        # Create metadata with bbox coordinates (as modified in partition.py)
        metadata = {
            "page_number": page_index,
            "bbox": block_bbox,  # This should preserve bbox
            "extraction_method": "pymupdf_text_dict",
        }
        
        # Create text element
        text_element = {
            "id": element_id,
            "category": "Text",
            "page": page_index,
            "text": block_text,
            "metadata": metadata,
        }
        
        text_elements.append(text_element)

doc.close()

print(f"Text elements created: {len(text_elements)}")

# Check first 3 elements
for i, elem in enumerate(text_elements[:3]):
    print(f"\nElement {i+1}:")
    meta = elem.get("metadata", {})
    bbox = meta.get("bbox")
    print(f"  Has bbox in metadata: {'YES' if bbox else 'NO'}")
    if bbox:
        print(f"  Bbox value: {bbox}")
        print(f"  Bbox type: {type(bbox)}")
    print(f"  Text: {elem['text'][:50]}...")

# Step 3: Test metadata cleaning function
print("\n\n3. METADATA CLEANING TEST:")
print("-"*40)

def _clean_metadata(metadata):
    """Clean metadata by removing unnecessary fields (from partition.py)"""
    cleaned = {}
    
    # Keep only essential metadata fields (as modified)
    essential_fields = [
        "page_number", 
        "filename", 
        "image_path", 
        "bbox",  # This was added to preserve bbox
        "font_size",
        "font_name",
        "is_bold",
        "extraction_method",
        "processing_strategy",
        "table_id",
        "text_as_html"
    ]
    
    for field in essential_fields:
        if field in metadata:
            cleaned[field] = metadata[field]
    
    return cleaned

# Test cleaning on our metadata
if text_elements:
    original_meta = text_elements[0]["metadata"]
    cleaned_meta = _clean_metadata(original_meta)
    
    print("Original metadata keys:", list(original_meta.keys()))
    print("Original bbox:", original_meta.get("bbox"))
    print("\nCleaned metadata keys:", list(cleaned_meta.keys()))
    print("Cleaned bbox:", cleaned_meta.get("bbox"))

# Step 4: Write test output for inspection
print("\n\n4. WRITING TEST OUTPUT:")
print("-"*40)

output_file = "bbox_debug_output.json"
output_data = {
    "raw_blocks": [
        {
            "block_index": i,
            "has_bbox": "bbox" in block,
            "bbox": block.get("bbox") if "bbox" in block else None,
            "type": "text" if "lines" in block else "other"
        }
        for i, block in enumerate(blocks[:5])
    ],
    "text_elements": [
        {
            "id": elem["id"],
            "metadata": elem["metadata"],
            "text_preview": elem["text"][:50]
        }
        for elem in text_elements[:3]
    ]
}

with open(output_file, "w") as f:
    json.dump(output_data, f, indent=2)

print(f"Debug output written to: {output_file}")

# Final summary
print("\n\n" + "="*60)
print("SUMMARY")
print("="*60)

bbox_in_raw = sum(1 for b in blocks if "lines" in b and "bbox" in b)
bbox_in_elements = sum(1 for e in text_elements if e["metadata"].get("bbox"))

print(f"✓ Bbox in raw PyMuPDF blocks: {bbox_in_raw}/{len([b for b in blocks if 'lines' in b])}")
print(f"✓ Bbox in text_elements: {bbox_in_elements}/{len(text_elements)}")

if bbox_in_raw > 0 and bbox_in_elements == 0:
    print("\n❌ PROBLEM: Bbox is extracted but lost during element creation!")
elif bbox_in_raw == 0:
    print("\n❌ PROBLEM: PyMuPDF is not extracting bbox from this PDF!")
elif bbox_in_elements > 0:
    print("\n✅ SUCCESS: Bbox is being preserved in elements!")
    
print("\nNext step: Check if bbox survives through metadata and chunking steps")