#!/usr/bin/env python3
"""
Test logo filtering on the problematic PDF with headers/logos on every page
"""
import sys
import os
import tempfile
from pathlib import Path

# Add the backend to the path
sys.path.append('/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/backend')

from src.pipeline.indexing.steps.partition import UnifiedPartitionerV2

def test_logo_filtering(pdf_path):
    """Test logo filtering on PDF with repeated headers/logos"""
    print(f"🧪 TESTING LOGO FILTERING: {os.path.basename(pdf_path)}")
    
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
            print("\n" + "="*70)
            print("🔍 ANALYZING DOCUMENT FOR LOGO FILTERING")
            print("="*70)
            
            # Stage 1: Analysis with detailed logging
            results = partitioner.stage1_pymupdf_analysis(pdf_path)
            
            print(f"\n📊 ANALYSIS RESULTS:")
            print(f"   Total pages: {len(results['page_analysis'])}")
            print(f"   Total images detected: {sum(p.get('image_count', 0) for p in results['page_analysis'].values())}")
            print(f"   Total meaningful images: {sum(p.get('meaningful_images', 0) for p in results['page_analysis'].values())}")
            print(f"   Tables detected: {len(results['table_locations'])}")
            
            # Analyze extraction decisions
            pages_for_extraction = {p: data for p, data in results['page_analysis'].items() if data.get('needs_extraction', False)}
            pages_skipped = {p: data for p, data in results['page_analysis'].items() if not data.get('needs_extraction', False)}
            
            print(f"\n📄 EXTRACTION DECISIONS:")
            print(f"   Pages for extraction: {len(pages_for_extraction)}")
            print(f"   Pages skipped: {len(pages_skipped)}")
            
            if len(pages_for_extraction) < len(results['page_analysis']) * 0.8:  # Less than 80% extracted
                print(f"   ✅ GOOD: Logo filtering appears to be working!")
            else:
                print(f"   ⚠️  CONCERN: Most pages still being extracted - logo filtering may need tuning")
            
            # Show details for first few pages
            print(f"\n📋 DETAILED BREAKDOWN (first 5 pages):")
            for page_num in sorted(list(results['page_analysis'].keys())[:5]):
                data = results['page_analysis'][page_num]
                decision = "EXTRACT" if data.get('needs_extraction') else "SKIP"
                print(f"   Page {page_num}: {decision} - {data['meaningful_images']} meaningful images, {data['table_count']} tables, complexity: {data['complexity']}")
            
            # Test actual extraction
            if pages_for_extraction:
                print(f"\n🖼️  TESTING ACTUAL EXTRACTION...")
                extracted_pages = partitioner.stage4_full_page_extraction(
                    pdf_path, results['page_analysis']
                )
                print(f"   Successfully extracted: {len(extracted_pages)} pages")
                
                # Show which pages were extracted
                extracted_page_nums = sorted([int(p) for p in extracted_pages.keys()])
                print(f"   Extracted page numbers: {extracted_page_nums}")
            else:
                print(f"\n🖼️  No pages scheduled for extraction (all filtered out)")
            
            return {
                "total_pages": len(results['page_analysis']),
                "pages_extracted": len(pages_for_extraction),
                "pages_skipped": len(pages_skipped),
                "extraction_ratio": len(pages_for_extraction) / len(results['page_analysis']) if results['page_analysis'] else 0
            }
            
        except Exception as e:
            print(f"❌ ERROR during logo filtering test: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

if __name__ == "__main__":
    # Test the problematic PDF
    pdf_path = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/projects/guldberg/I12727-01_K07_C08.01 Appendiks EL.pdf"
    
    if os.path.exists(pdf_path):
        results = test_logo_filtering(pdf_path)
        
        print(f"\n🎯 FINAL RESULTS:")
        if "error" not in results:
            print(f"   📄 Total pages: {results['total_pages']}")
            print(f"   🖼️  Pages extracted: {results['pages_extracted']}")
            print(f"   ⏭️  Pages skipped: {results['pages_skipped']}")
            print(f"   📊 Extraction ratio: {results['extraction_ratio']:.1%}")
            
            if results['extraction_ratio'] < 0.3:  # Less than 30%
                print(f"   ✅ EXCELLENT: Logo filtering working well!")
            elif results['extraction_ratio'] < 0.6:  # Less than 60%
                print(f"   ✅ GOOD: Logo filtering helping significantly")
            else:
                print(f"   ⚠️  NEEDS TUNING: Still extracting most pages")
        else:
            print(f"   ❌ Test failed: {results['error']}")
    else:
        print(f"❌ PDF file not found: {pdf_path}")