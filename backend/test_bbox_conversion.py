#!/usr/bin/env python3
"""Test Unstructured bbox coordinate conversion."""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from unstructured.partition.pdf import partition_pdf

# Test file
test_file = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/small-complicated/mole-scannable.pdf"

print("\n" + "=" * 60)
print("TESTING UNSTRUCTURED BBOX CONVERSION")
print("=" * 60)
print(f"File: {Path(test_file).name}\n")

print("Running Unstructured partition_pdf with hi_res strategy...")
print("This may take a minute for OCR...\n")

# Run Unstructured directly
elements = partition_pdf(
    filename=test_file,
    strategy="hi_res",
    infer_table_structure=True,
    languages=["dan"],
    include_page_breaks=True,
)

print(f"Extracted {len(elements)} elements\n")

# Check first few elements for coordinates
found_coords = 0
for i, elem in enumerate(elements[:5]):
    print(f"Element {i}: {elem.category}")
    print(f"  Text: {str(elem)[:60]}...")
    
    if hasattr(elem, 'metadata'):
        meta = elem.metadata
        
        if hasattr(meta, 'page_number'):
            print(f"  Page: {meta.page_number}")
        
        if hasattr(meta, 'coordinates'):
            coords = meta.coordinates
            if coords:
                found_coords += 1
                print(f"  ✅ Has coordinates")
                
                if hasattr(coords, 'points'):
                    print(f"  Points: {coords.points}")
                    
                if hasattr(coords, 'system'):
                    system = coords.system
                    print(f"  System: {system}")
                    
                    if hasattr(system, 'width'):
                        print(f"    Width: {system.width}")
                    if hasattr(system, 'height'):
                        print(f"    Height: {system.height}")
                    if hasattr(system, 'orientation'):
                        print(f"    Orientation: {system.orientation}")
            else:
                print(f"  ❌ No coordinates")
        else:
            print(f"  ❌ No coordinates attribute")
    else:
        print(f"  ❌ No metadata")
    
    print()

print(f"\nSummary: {found_coords}/5 elements have coordinates")

if found_coords == 0:
    print("⚠️  No coordinates found - hi_res strategy may not be extracting them")
    print("    The current Unstructured version might need coordinates=True parameter")
else:
    print("✅ Coordinates are being extracted by hi_res strategy")