#!/usr/bin/env python3
"""Test script to analyze vector drawing detection in PDFs"""

import fitz  # PyMuPDF
import json
from pathlib import Path


def analyze_drawings_in_pdf(pdf_path):
    """Analyze drawing commands in a PDF to detect vector graphics"""
    
    print(f"\n{'='*80}")
    print(f"Analyzing: {Path(pdf_path).name}")
    print(f"{'='*80}")
    
    doc = fitz.open(pdf_path)
    
    results = {
        "filename": Path(pdf_path).name,
        "total_pages": len(doc),
        "pages": {}
    }
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_index = page_num + 1
        
        # Get basic page info
        images = page.get_images()
        text = page.get_text().strip()
        
        # Analyze drawings
        drawing_stats = {
            "total_items": 0,
            "paths": 0,
            "lines": 0,
            "curves": 0,
            "rectangles": 0,
            "filled_shapes": 0,
            "stroked_shapes": 0
        }
        
        try:
            drawings = page.get_drawings()
            
            for drawing in drawings:
                items = drawing.get("items", [])
                drawing_stats["total_items"] += len(items)
                
                # Analyze drawing types
                for item in items:
                    item_type = item[0]  # First element is the command type
                    
                    if item_type == "l":  # Line
                        drawing_stats["lines"] += 1
                    elif item_type == "c":  # Curve
                        drawing_stats["curves"] += 1
                    elif item_type == "re":  # Rectangle
                        drawing_stats["rectangles"] += 1
                    elif item_type in ["f", "F"]:  # Fill
                        drawing_stats["filled_shapes"] += 1
                    elif item_type == "s":  # Stroke
                        drawing_stats["stroked_shapes"] += 1
                    elif item_type == "qu":  # Path/quad
                        drawing_stats["paths"] += 1
                
                # Check fill and stroke properties
                if drawing.get("fill"):
                    drawing_stats["filled_shapes"] += 1
                if drawing.get("stroke"):
                    drawing_stats["stroked_shapes"] += 1
            
            # Count total drawing objects
            total_drawing_objects = len(drawings)
            
        except Exception as e:
            print(f"  Error analyzing drawings on page {page_index}: {e}")
            total_drawing_objects = 0
        
        # Store page results
        page_info = {
            "images_count": len(images),
            "text_length": len(text),
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "drawing_objects": total_drawing_objects,
            "drawing_items": drawing_stats["total_items"],
            "drawing_details": drawing_stats
        }
        
        results["pages"][page_index] = page_info
        
        # Print page summary
        print(f"\nPage {page_index}:")
        print(f"  - Images: {len(images)}")
        print(f"  - Text length: {len(text)} chars")
        print(f"  - Drawing objects: {total_drawing_objects}")
        print(f"  - Total drawing items: {drawing_stats['total_items']}")
        if drawing_stats["total_items"] > 0:
            print(f"    Details: {drawing_stats['lines']} lines, {drawing_stats['curves']} curves, "
                  f"{drawing_stats['rectangles']} rects, {drawing_stats['filled_shapes']} filled, "
                  f"{drawing_stats['paths']} paths")
        
        # Determine if this looks like an architectural drawing
        is_likely_drawing = False
        reason = ""
        
        if drawing_stats["total_items"] > 100:
            is_likely_drawing = True
            reason = f"High drawing count ({drawing_stats['total_items']} items)"
        elif drawing_stats["total_items"] > 50 and len(text) < 500:
            is_likely_drawing = True
            reason = f"Many drawings ({drawing_stats['total_items']}) with minimal text"
        elif total_drawing_objects > 20:
            is_likely_drawing = True
            reason = f"Many drawing objects ({total_drawing_objects})"
        
        if is_likely_drawing:
            print(f"  ⚠️  LIKELY ARCHITECTURAL DRAWING: {reason}")
        
        page_info["is_likely_drawing"] = is_likely_drawing
        page_info["detection_reason"] = reason
    
    doc.close()
    
    # Summary statistics
    print(f"\n{'='*50}")
    print("SUMMARY:")
    print(f"{'='*50}")
    
    total_drawing_items = sum(p["drawing_items"] for p in results["pages"].values())
    pages_with_drawings = sum(1 for p in results["pages"].values() if p["drawing_items"] > 0)
    likely_drawing_pages = sum(1 for p in results["pages"].values() if p["is_likely_drawing"])
    
    print(f"Total pages: {results['total_pages']}")
    print(f"Pages with drawings: {pages_with_drawings}")
    print(f"Total drawing items across all pages: {total_drawing_items}")
    print(f"Average drawing items per page: {total_drawing_items / results['total_pages']:.1f}")
    print(f"Pages detected as architectural drawings: {likely_drawing_pages}")
    
    return results


def main():
    """Test drawing detection on sample PDFs"""
    
    # Test PDFs
    test_files = [
        "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/small-complicated/DNI_K07_H1_ETX_N400 Belysningsplan st. og 1sal.pdf",
        "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"
    ]
    
    all_results = []
    
    for pdf_path in test_files:
        if Path(pdf_path).exists():
            results = analyze_drawings_in_pdf(pdf_path)
            all_results.append(results)
        else:
            print(f"⚠️  File not found: {pdf_path}")
    
    # Save detailed results to JSON
    output_file = "drawing_detection_results.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n📊 Detailed results saved to: {output_file}")
    
    # Propose thresholds based on results
    print(f"\n{'='*80}")
    print("PROPOSED DETECTION THRESHOLDS:")
    print(f"{'='*80}")
    
    if all_results:
        # Analyze the architectural drawing (first file)
        arch_drawing = all_results[0] if len(all_results) > 0 else None
        regular_doc = all_results[1] if len(all_results) > 1 else None
        
        if arch_drawing:
            max_arch_items = max(p["drawing_items"] for p in arch_drawing["pages"].values())
            avg_arch_items = sum(p["drawing_items"] for p in arch_drawing["pages"].values()) / len(arch_drawing["pages"])
            print(f"\nArchitectural drawing stats:")
            print(f"  - Max items on a page: {max_arch_items}")
            print(f"  - Avg items per page: {avg_arch_items:.1f}")
        
        if regular_doc:
            max_reg_items = max(p["drawing_items"] for p in regular_doc["pages"].values())
            avg_reg_items = sum(p["drawing_items"] for p in regular_doc["pages"].values()) / len(regular_doc["pages"])
            print(f"\nRegular document stats:")
            print(f"  - Max items on a page: {max_reg_items}")
            print(f"  - Avg items per page: {avg_reg_items:.1f}")
        
        print(f"\n🎯 Suggested threshold: ")
        print(f"   - Extract page if drawing_items > 100")
        print(f"   - OR if drawing_items > 50 AND text < 500 chars")
        print(f"   - OR if drawing_objects > 20")


if __name__ == "__main__":
    main()