#!/usr/bin/env python3
"""
Detailed image analysis to understand what we're filtering out
"""
import sys
import fitz  # PyMuPDF

def analyze_page_images(pdf_path, page_num):
    """Analyze all images on a specific page in detail"""
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]  # Convert to 0-indexed
    images = page.get_images()
    
    print(f"=== PAGE {page_num} IMAGE ANALYSIS ===")
    print(f"Total images found: {len(images)}")
    print()
    
    for i, img in enumerate(images):
        try:
            base_image = doc.extract_image(img[0])
            width = base_image["width"]
            height = base_image["height"]
            pixels = width * height
            
            print(f"Image {i+1}: {width}x{height} = {pixels:,} pixels")
            
            # Show filtering decision
            meaningful = (width >= 150 and height >= 100 and pixels >= 25000)
            print(f"  Meaningful: {meaningful}")
            
        except Exception as e:
            print(f"Image {i+1}: Error - {e}")
        print()
    
    doc.close()

if __name__ == "__main__":
    pdf_path = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"
    
    # Analyze the problematic pages
    print("Analyzing Page 1 (should have some meaningful images):")
    analyze_page_images(pdf_path, 1)
    
    print("\nAnalyzing Page 4 (technical diagram with many small images):")
    analyze_page_images(pdf_path, 4)