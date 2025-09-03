#!/usr/bin/env python3
"""Direct test of PyMuPDF bbox extraction."""

import fitz  # PyMuPDF

test_pdf = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"

print("Testing PyMuPDF bbox extraction")
print("="*60)

doc = fitz.open(test_pdf)
print(f"Document: {test_pdf}")
print(f"Pages: {len(doc)}\n")

# Check first page
page = doc[0]
print(f"Page 1 dimensions: {page.rect}")

# Get text with dict format (includes bbox)
text_dict = page.get_text("dict")

print(f"\nBlocks found: {len(text_dict.get('blocks', []))}")

# Check first few text blocks
blocks_with_bbox = 0
blocks_without_bbox = 0

for i, block in enumerate(text_dict.get("blocks", [])[:5]):
    if "lines" in block:  # Text block
        bbox = block.get("bbox")
        if bbox:
            blocks_with_bbox += 1
            print(f"\n✅ Block {i+1}: HAS BBOX")
            print(f"   Bbox: {bbox}")
            
            # Get text preview
            text = ""
            for line in block["lines"]:
                for span in line.get("spans", []):
                    text += span.get("text", "")
            print(f"   Text: {text[:50]}...")
        else:
            blocks_without_bbox += 1
            print(f"\n❌ Block {i+1}: NO BBOX")

print(f"\n\nSummary: {blocks_with_bbox} blocks have bbox, {blocks_without_bbox} don't")

# Also test if bbox is in the right format
if blocks_with_bbox > 0:
    sample_block = next(b for b in text_dict.get("blocks", []) if "bbox" in b)
    bbox = sample_block["bbox"]
    print(f"\nBbox format: {type(bbox)}")
    print(f"Bbox value: {bbox}")
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        print("✅ Bbox is in correct format (x0, y0, x1, y1)")
    else:
        print("❌ Bbox format is unexpected")

doc.close()