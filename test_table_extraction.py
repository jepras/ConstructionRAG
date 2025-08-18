#!/usr/bin/env python3
"""
Test the complete table extraction pipeline with our fixes
"""
import sys
import os
import tempfile
from pathlib import Path

# Add the backend to the path
sys.path.append('/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/backend')

from src.pipeline.indexing.steps.partition import UnifiedPartitionerV2

def test_table_extraction(pdf_path):
    """Test that table extraction now uses full pages instead of cropped fragments"""
    print(f"Testing table extraction on: {pdf_path}")
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        tables_dir = temp_path / "tables"
        images_dir = temp_path / "images"
        
        tables_dir.mkdir()
        images_dir.mkdir()
        
        # Initialize partitioner
        partitioner = UnifiedPartitionerV2(str(tables_dir), str(images_dir))
        
        # Run analysis and table processing
        try:
            results = partitioner.stage1_pymupdf_analysis(pdf_path)
            print(f"Tables found: {len(results['table_locations'])}")
            
            if results['table_locations']:
                # Run table processing
                enhanced_tables = partitioner.stage3_targeted_table_processing(
                    pdf_path, results['table_locations']
                )
                
                print(f"Enhanced tables: {len(enhanced_tables)}")
                
                for i, table in enumerate(enhanced_tables):
                    table_path = table['metadata']['image_path']
                    print(f"\nTable {i+1}:")
                    print(f"  ID: {table['id']}")
                    print(f"  Page: {table['page']}")
                    print(f"  Image saved to: {table_path}")
                    
                    # Check if the file exists and get its size
                    if os.path.exists(table_path):
                        file_size = os.path.getsize(table_path)
                        print(f"  Image file size: {file_size:,} bytes")
                        
                        # Get image dimensions using PIL
                        try:
                            from PIL import Image
                            with Image.open(table_path) as img:
                                width, height = img.size
                                print(f"  Image dimensions: {width}x{height}")
                                
                                # Full page should be much larger than a cropped table
                                if width > 1000 and height > 1000:
                                    print("  ✅ LOOKS LIKE FULL PAGE (good!)")
                                else:
                                    print("  ⚠️ Looks like cropped fragment (might be issue)")
                        except ImportError:
                            print("  (PIL not available for dimension check)")
                        except Exception as e:
                            print(f"  Error checking dimensions: {e}")
                    else:
                        print("  ❌ Image file not found")
                        
        except Exception as e:
            print(f"Error during table extraction test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    pdf_path = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        sys.exit(1)
    
    test_table_extraction(pdf_path)