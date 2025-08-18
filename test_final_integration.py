#!/usr/bin/env python3
"""
Final integration test to verify the complete pipeline with full logging
"""
import sys
import os
import tempfile
from pathlib import Path

# Add the backend to the path
sys.path.append('/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/backend')

from src.pipeline.indexing.steps.partition import UnifiedPartitionerV2

def test_final_integration(pdf_path):
    """Test the complete integration with full Beam logging"""
    print(f"🧪 TESTING COMPLETE INTEGRATION: {pdf_path}")
    
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
            print("\n" + "="*60)
            print("🔍 STAGE 1: DOCUMENT ANALYSIS")
            print("="*60)
            
            # Stage 1: Analysis
            results = partitioner.stage1_pymupdf_analysis(pdf_path)
            print(f"✅ Analysis complete - {len(results['table_locations'])} tables detected")
            
            print("\n" + "="*60)
            print("📄 STAGE 4: FULL PAGE EXTRACTION")  
            print("="*60)
            
            # Stage 4: Full page extraction (priority)
            extracted_pages = partitioner.stage4_full_page_extraction(
                pdf_path, results['page_analysis']
            )
            print(f"✅ Full page extraction complete - {len(extracted_pages)} pages")
            
            print("\n" + "="*60)
            print("📋 STAGE 3: TABLE METADATA ONLY")
            print("="*60)
            
            # Stage 3: Table processing (no images)
            if extracted_pages:
                enhanced_tables = partitioner.stage3_create_table_elements_only(
                    pdf_path, results['table_locations']
                )
                print(f"✅ Table metadata processing complete - {len(enhanced_tables)} tables")
            else:
                print("⚠️  No full pages extracted, would use individual table extraction")
                
            print("\n" + "="*60)
            print("📊 FINAL RESULTS SUMMARY")
            print("="*60)
            
            # Check actual files created
            table_files = list(tables_dir.glob("*.png"))
            image_files = list(images_dir.glob("*.png"))
            
            print(f"📋 Table metadata elements: {len(enhanced_tables) if 'enhanced_tables' in locals() else 0}")
            print(f"🖼️  Full page images: {len(extracted_pages)}")
            print(f"📁 Table image files created: {len(table_files)} (should be 0)")
            print(f"📁 Page image files created: {len(image_files)}")
            
            # Success check
            if len(table_files) == 0 and len(image_files) == len(extracted_pages):
                print("\n✅ SUCCESS: Full-page-only approach working perfectly!")
                print("   - No individual table images created")
                print("   - Full-page images created as expected")
                print("   - Table metadata preserved")
            else:
                print(f"\n❌ ISSUE: Expected 0 table files and {len(extracted_pages)} image files")
                print(f"   Got: {len(table_files)} table files, {len(image_files)} image files")
            
            return {
                "success": len(table_files) == 0 and len(image_files) == len(extracted_pages),
                "table_files": len(table_files),
                "image_files": len(image_files),
                "extracted_pages": len(extracted_pages),
                "table_elements": len(enhanced_tables) if 'enhanced_tables' in locals() else 0
            }
            
        except Exception as e:
            print(f"❌ ERROR during integration test: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

if __name__ == "__main__":
    pdf_path = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"
    
    if os.path.exists(pdf_path):
        results = test_final_integration(pdf_path)
        print(f"\n🎯 FINAL TEST RESULT: {'✅ PASSED' if results.get('success') else '❌ FAILED'}")
        if not results.get('success'):
            print(f"Error details: {results}")
    else:
        print(f"❌ PDF file not found: {pdf_path}")