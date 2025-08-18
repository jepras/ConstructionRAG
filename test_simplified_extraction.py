#!/usr/bin/env python3
"""
Test the simplified extraction approach
"""
import sys
import os
import tempfile
from pathlib import Path

# Add the backend to the path
sys.path.append('/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/backend')

from src.pipeline.indexing.steps.partition import UnifiedPartitionerV2

def test_simplified_extraction(pdf_path):
    """Test the simplified extraction approach"""
    print(f"Testing simplified extraction on: {pdf_path}")
    
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
            print(f"\n=== STAGE 1: ANALYSIS ===")
            print(f"Tables detected: {len(results['table_locations'])}")
            pages_needing_extraction = sum(1 for analysis in results["page_analysis"].values() 
                                         if analysis["needs_extraction"])
            print(f"Pages needing extraction: {pages_needing_extraction}")
            
            # Stage 4: Full pages (priority)
            extracted_pages = partitioner.stage4_full_page_extraction(
                pdf_path, results['page_analysis']
            )
            print(f"\n=== STAGE 4: FULL PAGE EXTRACTION ===")
            print(f"Full pages extracted: {len(extracted_pages)}")
            for page_num, page_info in extracted_pages.items():
                print(f"  Page {page_num}: {page_info['complexity']}")
            
            # Stage 3: Table processing (simplified)
            if extracted_pages:
                # New simplified approach - no individual table images
                enhanced_tables = partitioner.stage3_create_table_elements_only(
                    pdf_path, results['table_locations']
                )
                print(f"\n=== STAGE 3: TABLE ELEMENTS (NO IMAGES) ===")
                print(f"Table elements created: {len(enhanced_tables)}")
                print("✅ Table content preserved, images covered by full-pages")
            else:
                # Fallback - individual table extraction
                enhanced_tables = partitioner.stage3_targeted_table_processing(
                    pdf_path, results['table_locations']
                )
                print(f"\n=== STAGE 3: INDIVIDUAL TABLE EXTRACTION ===")
                print(f"Individual table images extracted: {len(enhanced_tables)}")
            
            # Summary
            print(f"\n=== EXTRACTION SUMMARY ===")
            total_images_stored = len(extracted_pages)
            if not extracted_pages:
                total_images_stored += len(enhanced_tables)
                
            print(f"Total images stored: {total_images_stored}")
            print(f"VLM processing needed: {len(extracted_pages)} full-page captions")
            
            if enhanced_tables and extracted_pages:
                print(f"✅ Tables preserved as metadata (no redundant images)")
            elif enhanced_tables and not extracted_pages:
                print(f"✅ Individual table images extracted (no full-page coverage)")
            else:
                print(f"ℹ️ No tables detected")
            
            # Check for files actually created
            table_files = list(tables_dir.glob("*.png"))
            image_files = list(images_dir.glob("*.png"))
            print(f"\n=== FILES CREATED ===")
            print(f"Table image files: {len(table_files)}")
            print(f"Page image files: {len(image_files)}")
            
            return {
                "full_pages": len(extracted_pages),
                "table_elements": len(enhanced_tables),
                "files_created": len(table_files) + len(image_files)
            }
            
        except Exception as e:
            print(f"Error during simplified extraction test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Test on your variety PDF
    pdf_path = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"
    
    if os.path.exists(pdf_path):
        print("=== TESTING ON VARIETY PDF ===")
        test_simplified_extraction(pdf_path)
    
    # Test on technical drawings PDF if it exists
    technical_pdf = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/projects/guldberg/Tegninger samlet .pdf"
    if os.path.exists(technical_pdf):
        print("\n" + "="*50)
        print("=== TESTING ON TECHNICAL DRAWINGS PDF ===")
        test_simplified_extraction(technical_pdf)
    else:
        print(f"\nTechnical PDF not found: {technical_pdf}")