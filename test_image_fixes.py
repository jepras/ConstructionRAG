#!/usr/bin/env python3
"""
Test script to verify image and table extraction fixes
"""
import sys
import os
import tempfile
from pathlib import Path

# Add the backend to the path
sys.path.append('/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/backend')

from src.pipeline.indexing.steps.partition import UnifiedPartitionerV2

def test_pdf_analysis(pdf_path):
    """Test the improved PDF analysis on the provided file"""
    print(f"Testing PDF analysis on: {pdf_path}")
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        tables_dir = temp_path / "tables"
        images_dir = temp_path / "images"
        
        tables_dir.mkdir()
        images_dir.mkdir()
        
        # Initialize partitioner with our fixes
        partitioner = UnifiedPartitionerV2(str(tables_dir), str(images_dir))
        
        print(f"Image filtering thresholds:")
        print(f"  Min width: {partitioner.min_image_width}px")
        print(f"  Min height: {partitioner.min_image_height}px") 
        print(f"  Min total pixels: {partitioner.min_image_pixels}px")
        print()
        
        # Run stage 1 analysis
        try:
            results = partitioner.stage1_pymupdf_analysis(pdf_path)
            
            print("=== PAGE ANALYSIS RESULTS ===")
            for page_num, analysis in results["page_analysis"].items():
                print(f"Page {page_num}:")
                print(f"  Total images: {analysis['image_count']}")
                print(f"  Meaningful images: {analysis['meaningful_images']}")
                print(f"  Tables: {analysis['table_count']}")
                print(f"  Complexity: {analysis['complexity']}")
                print(f"  Needs extraction: {analysis['needs_extraction']}")
                print(f"  Is fragmented: {analysis['is_fragmented']}")
                print()
            
            print("=== SUMMARY ===")
            print(f"Total tables detected: {len(results['table_locations'])}")
            print(f"Total image locations: {len(results['image_locations'])}")
            
            pages_to_extract = sum(1 for analysis in results["page_analysis"].values() 
                                 if analysis["needs_extraction"])
            print(f"Pages that need extraction: {pages_to_extract}")
            
            # Show which specific pages will be extracted
            extract_pages = [page_num for page_num, analysis in results["page_analysis"].items()
                           if analysis["needs_extraction"]]
            print(f"Pages to extract: {extract_pages}")
            
        except Exception as e:
            print(f"Error during analysis: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    pdf_path = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        sys.exit(1)
    
    test_pdf_analysis(pdf_path)