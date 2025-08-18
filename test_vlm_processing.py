#!/usr/bin/env python3
"""
Test to see exactly what gets sent to VLM processing
"""
import sys
import os
import tempfile
from pathlib import Path

# Add the backend to the path
sys.path.append('/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/backend')

from src.pipeline.indexing.steps.partition import UnifiedPartitionerV2

def analyze_vlm_inputs(pdf_path):
    """Analyze what will be sent to VLM processing"""
    print(f"Analyzing VLM inputs for: {pdf_path}")
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        tables_dir = temp_path / "tables"
        images_dir = temp_path / "images"
        
        tables_dir.mkdir()
        images_dir.mkdir()
        
        # Initialize partitioner
        partitioner = UnifiedPartitionerV2(str(tables_dir), str(images_dir))
        
        try:
            # Run the complete partitioning pipeline
            results = partitioner.stage1_pymupdf_analysis(pdf_path)
            
            # Stage 3: Tables (will have VLM processing)
            enhanced_tables = partitioner.stage3_targeted_table_processing(
                pdf_path, results['table_locations']
            )
            
            # Stage 4: Full pages (will have VLM processing)
            extracted_pages = partitioner.stage4_full_page_extraction(
                pdf_path, results['page_analysis']
            )
            
            print("\n=== VLM PROCESSING ANALYSIS ===")
            
            print(f"\n📊 TABLES (will get VLM captions):")
            if enhanced_tables:
                for table in enhanced_tables:
                    print(f"  - Table on page {table['page']}: {table['id']}")
            else:
                print("  - No tables found")
            
            print(f"\n🖼️  FULL PAGES (will get VLM captions):")
            if extracted_pages:
                for page_num, page_info in extracted_pages.items():
                    complexity = page_info['complexity']
                    print(f"  - Page {page_num}: {complexity}")
            else:
                print("  - No full pages extracted")
            
            print(f"\n📈 VLM PROCESSING SUMMARY:")
            total_vlm_calls = len(enhanced_tables) + len(extracted_pages)
            print(f"  - Table VLM calls: {len(enhanced_tables)}")
            print(f"  - Full-page VLM calls: {len(extracted_pages)}")
            print(f"  - TOTAL VLM calls: {total_vlm_calls}")
            
            # Check for overlaps (tables on pages with full extraction)
            print(f"\n⚠️  OVERLAP ANALYSIS:")
            overlaps = 0
            if enhanced_tables and extracted_pages:
                table_pages = {table['page'] for table in enhanced_tables}
                full_pages = set(extracted_pages.keys())
                overlap_pages = table_pages.intersection(full_pages)
                overlaps = len(overlap_pages)
                
                if overlap_pages:
                    print(f"  - Pages with BOTH table and full-page VLM: {sorted(overlap_pages)}")
                    print(f"  - This means {overlaps} redundant VLM calls")
                else:
                    print(f"  - No overlaps found")
            else:
                print(f"  - No overlaps possible")
            
            optimized_calls = total_vlm_calls - overlaps
            print(f"\n✅ OPTIMIZED VLM calls (after our fix): {optimized_calls}")
            
        except Exception as e:
            print(f"Error during analysis: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    pdf_path = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        sys.exit(1)
    
    analyze_vlm_inputs(pdf_path)