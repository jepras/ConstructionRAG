#!/usr/bin/env python3
"""Test vector drawing detection using the actual partition code"""
import fitz  # PyMuPDF
import json
from pathlib import Path

def test_vector_detection_logic(pdf_path):
    """Test the vector detection logic directly"""
    doc = fitz.open(pdf_path)
    
    print(f"Testing: {Path(pdf_path).name}")
    print("=" * 80)
    
    results = []
    
    for page_index, page in enumerate(doc, start=1):
        # Get images and tables
        images = page.get_images()
        tables = list(page.find_tables())
        
        # Check for meaningful images (≥50x50 pixels)
        meaningful_images = 0
        for img in images:
            try:
                base_image = doc.extract_image(img[0])
                if base_image["width"] >= 50 and base_image["height"] >= 50:
                    meaningful_images += 1
            except:
                pass
        
        # Check for vector drawings (NEW LOGIC)
        has_vector_drawings = False
        drawing_item_count = 0
        try:
            drawings = page.get_drawings()
            # Count total drawing items
            for drawing in drawings:
                items = drawing.get("items", [])
                drawing_item_count += len(items)
            # Threshold of 4000 items indicates complex vector drawing
            has_vector_drawings = drawing_item_count >= 4000
        except Exception as e:
            print(f"Could not analyze drawings on page {page_index}: {e}")
        
        # Determine complexity using precedence: Images → Drawings → Tables
        complexity = "text_only"
        needs_extraction = False
        reason = []
        
        min_meaningful_images_for_extraction = 2
        
        if meaningful_images >= min_meaningful_images_for_extraction:
            # Images take precedence
            complexity = "complex" if meaningful_images >= 3 else "simple"
            needs_extraction = True
            reason.append(f"{meaningful_images} meaningful images")
        elif has_vector_drawings:
            # Vector drawings are second priority
            complexity = "complex_vector_drawing"
            needs_extraction = True
            reason.append(f"vector drawing ({drawing_item_count:,} items)")
        elif len(tables) > 0:
            # Tables are third priority
            complexity = "simple"
            needs_extraction = True
            reason.append(f"{len(tables)} tables")
        
        # Print results
        decision = "✅ EXTRACT" if needs_extraction else "⏭️ SKIP"
        reason_str = ", ".join(reason) if reason else "no meaningful content"
        
        print(f"Page {page_index}: {decision}")
        print(f"  - Images: {len(images)} total, {meaningful_images} meaningful")
        print(f"  - Drawing items: {drawing_item_count:,}")
        print(f"  - Tables: {len(tables)}")
        print(f"  - Complexity: {complexity}")
        print(f"  - Reason: {reason_str}")
        print()
        
        results.append({
            "page": page_index,
            "images": len(images),
            "meaningful_images": meaningful_images,
            "drawing_items": drawing_item_count,
            "has_vector_drawings": has_vector_drawings,
            "tables": len(tables),
            "complexity": complexity,
            "needs_extraction": needs_extraction,
            "reason": reason_str
        })
    
    doc.close()
    return results

# Test both PDFs
floor_plan_pdf = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/small-complicated/DNI_K07_H1_ETX_N400 Belysningsplan st. og 1sal.pdf"
variety_pdf = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"

print("\n" + "="*80)
print("FLOOR PLAN PDF (Should detect vector drawings)")
print("="*80)
floor_plan_results = test_vector_detection_logic(floor_plan_pdf)

print("\n" + "="*80)
print("VARIETY PDF (Should handle mixed content correctly)")
print("="*80)
variety_results = test_vector_detection_logic(variety_pdf)

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

print(f"\nFloor Plan PDF:")
extracted = [r for r in floor_plan_results if r["needs_extraction"]]
vector_pages = [r for r in floor_plan_results if r["has_vector_drawings"]]
print(f"  - Pages extracted: {len(extracted)}/{len(floor_plan_results)}")
print(f"  - Vector drawing pages: {len(vector_pages)}")

print(f"\nVariety PDF:")
extracted = [r for r in variety_results if r["needs_extraction"]]
vector_pages = [r for r in variety_results if r["has_vector_drawings"]]
print(f"  - Pages extracted: {len(extracted)}/{len(variety_results)}")
print(f"  - Vector drawing pages: {len(vector_pages)}")