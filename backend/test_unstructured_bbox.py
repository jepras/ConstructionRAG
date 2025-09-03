#!/usr/bin/env python3
"""Test Unstructured bbox extraction with different parameter combinations."""

import sys
import json
from pathlib import Path

# Test both scanned and regular PDFs
test_files = {
    "scanned": "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/small-complicated/mole-scannable.pdf",
    "regular": "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"
}

print("=" * 60)
print("TESTING UNSTRUCTURED BBOX EXTRACTION")
print("=" * 60)

# Check version
try:
    import unstructured
    print(f"Unstructured version: {unstructured.__version__}")
except:
    print("Could not determine version")

from unstructured.partition.pdf import partition_pdf

# Test different parameter combinations
test_configs = [
    {
        "name": "No coordinates param (default)",
        "params": {
            "strategy": "hi_res",
            "infer_table_structure": True,
            "languages": ["dan"],
            "include_page_breaks": True,
        }
    },
    {
        "name": "With include_metadata=True",
        "params": {
            "strategy": "hi_res",
            "infer_table_structure": True,
            "languages": ["dan"],
            "include_page_breaks": True,
            "include_metadata": True,
        }
    },
    {
        "name": "With extract_element_coordinates=True",
        "params": {
            "strategy": "hi_res",
            "infer_table_structure": True,
            "languages": ["dan"],
            "include_page_breaks": True,
            "extract_element_coordinates": True,
        }
    }
]

# Test with regular PDF first (faster)
test_pdf = test_files["regular"]
print(f"\nTesting with: {Path(test_pdf).name}")

for config in test_configs:
    print(f"\n{'='*40}")
    print(f"Testing: {config['name']}")
    print(f"{'='*40}")
    
    try:
        # Extract elements
        elements = partition_pdf(
            filename=test_pdf,
            **config["params"]
        )
        
        print(f"✅ Extraction successful - {len(elements)} elements")
        
        # Check for coordinates in first few elements
        coords_found = 0
        for i, elem in enumerate(elements[:5]):
            if hasattr(elem, 'metadata'):
                meta = elem.metadata
                
                # Check different coordinate attributes
                has_coords = False
                coord_info = {}
                
                if hasattr(meta, 'coordinates'):
                    has_coords = True
                    coord_info['coordinates'] = True
                    if meta.coordinates:
                        if hasattr(meta.coordinates, 'points'):
                            coord_info['points'] = meta.coordinates.points
                        if hasattr(meta.coordinates, 'system'):
                            coord_info['system'] = meta.coordinates.system
                
                if hasattr(meta, 'coordinate_system'):
                    coord_info['coordinate_system'] = meta.coordinate_system
                    
                if has_coords:
                    coords_found += 1
                    if i == 0:  # Show details for first element
                        print(f"\nFirst element with coordinates:")
                        print(f"  Category: {elem.category}")
                        print(f"  Text: {str(elem)[:50]}...")
                        print(f"  Coordinate info: {coord_info}")
                        if 'points' in coord_info:
                            points = coord_info['points']
                            if points and len(points) >= 4:
                                # Convert to bbox format
                                bbox = [points[0][0], points[0][1], points[2][0], points[2][1]]
                                print(f"  Converted bbox: {bbox}")
        
        print(f"\n📊 Elements with coordinates: {coords_found}/5")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        # Check if it's the specific coordinates parameter error
        if "coordinates" in str(e):
            print("   -> This is the coordinates parameter conflict!")

# Now test if we need different approach for scanned documents
print("\n" + "="*60)
print("TESTING WITH SCANNED DOCUMENT")
print("="*60)

test_pdf = test_files["scanned"]
print(f"Testing with: {Path(test_pdf).name}")

# Use the config that worked best
best_config = {
    "strategy": "hi_res",
    "infer_table_structure": True,
    "languages": ["dan"],
    "include_page_breaks": True,
}

try:
    elements = partition_pdf(filename=test_pdf, **best_config)
    
    print(f"✅ Extraction successful - {len(elements)} elements")
    
    # Check text elements
    text_elements = [e for e in elements if e.category not in ['Image', 'PageBreak']]
    print(f"Text elements: {len(text_elements)}")
    
    # Check for coordinates
    coords_found = 0
    for elem in elements[:10]:
        if hasattr(elem, 'metadata') and hasattr(elem.metadata, 'coordinates'):
            if elem.metadata.coordinates:
                coords_found += 1
    
    print(f"Elements with coordinates: {coords_found}/10")
    
except Exception as e:
    print(f"❌ Error with scanned document: {e}")

print("\n" + "="*60)
print("RECOMMENDATIONS")
print("="*60)
print("Based on testing, the best approach is:")
print("1. Remove 'coordinates=True' parameter (causes error)")
print("2. Use default parameters with hi_res strategy")
print("3. Coordinates are included automatically with hi_res strategy")