#!/usr/bin/env python3
"""Improved drawing detection with better thresholds"""

import fitz  # PyMuPDF
from pathlib import Path


def detect_vector_drawing_page(page, page_num=1):
    """
    Detect if a page contains significant vector drawings (architectural plans, diagrams, etc.)
    
    Returns: (is_drawing, confidence, reason)
    """
    
    # Get basic page info
    images = page.get_images()
    text = page.get_text().strip()
    
    # Analyze drawings
    try:
        drawings = page.get_drawings()
        
        # Count drawing items
        total_items = 0
        line_count = 0
        curve_count = 0
        
        for drawing in drawings:
            items = drawing.get("items", [])
            total_items += len(items)
            
            # Count specific types
            for item in items:
                item_type = item[0]
                if item_type == "l":  # Line
                    line_count += 1
                elif item_type == "c":  # Curve
                    curve_count += 1
        
        total_drawing_objects = len(drawings)
        
    except Exception as e:
        print(f"Error analyzing drawings: {e}")
        return False, 0.0, "Error analyzing drawings"
    
    # Detection logic with multiple thresholds
    is_drawing = False
    confidence = 0.0
    reason = ""
    
    # Tier 1: Definitely architectural drawings (very high item count)
    if total_items >= 50000:
        is_drawing = True
        confidence = 1.0
        reason = f"Complex vector drawing ({total_items:,} items)"
    
    # Tier 2: High drawing count with curves (technical diagrams)
    elif total_items >= 10000:
        is_drawing = True
        confidence = 0.9
        reason = f"Significant vector content ({total_items:,} items)"
    
    # Tier 3: Moderate drawings with low text (likely diagrams)
    elif total_items >= 5000 and len(text) < 1000:
        is_drawing = True
        confidence = 0.8
        reason = f"Vector diagram ({total_items:,} items, minimal text)"
    
    # Tier 4: Many drawing objects even if fewer items
    elif total_drawing_objects >= 1000:
        is_drawing = True
        confidence = 0.7
        reason = f"Many drawing objects ({total_drawing_objects:,} objects)"
    
    # Tier 5: Combined criteria for edge cases
    elif total_items >= 1000 and len(images) == 0 and len(text) < 500:
        is_drawing = True
        confidence = 0.6
        reason = f"Vector graphics with no raster images ({total_items:,} items)"
    
    # Not a drawing - regular document
    else:
        is_drawing = False
        confidence = 0.0
        reason = f"Regular content ({total_items} drawing items)"
    
    return is_drawing, confidence, reason


def test_improved_detection():
    """Test the improved detection on our sample files"""
    
    test_files = [
        "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/small-complicated/DNI_K07_H1_ETX_N400 Belysningsplan st. og 1sal.pdf",
        "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"
    ]
    
    for pdf_path in test_files:
        if not Path(pdf_path).exists():
            print(f"File not found: {pdf_path}")
            continue
            
        print(f"\n{'='*80}")
        print(f"Testing: {Path(pdf_path).name}")
        print(f"{'='*80}")
        
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_index = page_num + 1
            
            is_drawing, confidence, reason = detect_vector_drawing_page(page, page_index)
            
            if is_drawing:
                print(f"Page {page_index}: ✅ EXTRACT (confidence: {confidence:.1f}) - {reason}")
            else:
                print(f"Page {page_index}: ⏭️  SKIP - {reason}")
        
        doc.close()


def create_production_function():
    """Generate the function to add to partition.py"""
    
    print("\n" + "="*80)
    print("PRODUCTION FUNCTION FOR partition.py:")
    print("="*80)
    
    code = '''
def _has_significant_vector_drawings(self, page) -> tuple[bool, str]:
    """
    Detect if page contains significant vector graphics (architectural drawings, technical diagrams).
    
    Returns:
        tuple: (needs_extraction, complexity_reason)
    """
    try:
        drawings = page.get_drawings()
        
        # Count total drawing items
        total_items = 0
        for drawing in drawings:
            items = drawing.get("items", [])
            total_items += len(items)
        
        total_drawing_objects = len(drawings)
        
        # Multi-tier detection thresholds
        if total_items >= 50000:
            return True, "complex_vector_drawing"
        elif total_items >= 10000:
            return True, "vector_drawing"
        elif total_items >= 5000 and len(page.get_text()) < 1000:
            return True, "vector_diagram"
        elif total_drawing_objects >= 1000:
            return True, "many_drawing_objects"
        elif total_items >= 1000 and len(page.get_images()) == 0:
            return True, "vector_graphics"
        
        return False, None
        
    except Exception as e:
        logger.debug(f"Could not analyze vector drawings: {e}")
        return False, None
'''
    
    print(code)
    
    print("\nINTEGRATION POINT in stage1_pymupdf_analysis (around line 1214):")
    print("-"*80)
    
    integration = '''
# After getting images and tables
images = page.get_images()
tables = list(page.find_tables())

# NEW: Check for vector drawings
has_vector_drawings, vector_complexity = self._has_significant_vector_drawings(page)

# Count meaningful images (existing code)
meaningful_images = self._count_meaningful_images(doc, page, images)

# Modified complexity determination
if has_vector_drawings:
    complexity = vector_complexity  # Use the specific vector complexity
    needs_extraction = True
elif meaningful_images == 0 and len(tables) == 0:
    complexity = "text_only"
    needs_extraction = False
# ... rest of existing logic
'''
    
    print(integration)


if __name__ == "__main__":
    test_improved_detection()
    create_production_function()