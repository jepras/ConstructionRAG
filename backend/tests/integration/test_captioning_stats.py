"""
Test to analyze image and table captioning statistics for an indexing run.
This helps understand what content is being detected and captioned.
"""

import asyncio
from typing import Dict, Any, List
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(supabase_url, supabase_key)


async def get_indexing_run_stats(indexing_run_id: str) -> Dict[str, Any]:
    """Get statistics for a specific indexing run"""
    
    # Get indexing run details
    run_response = supabase.table("indexing_runs").select("*").eq("id", indexing_run_id).execute()
    if not run_response.data:
        print(f"ERROR: Indexing run {indexing_run_id} not found!")
        return {}
    run_data = run_response.data[0]
    
    print(f"\n{'='*80}")
    print(f"INDEXING RUN ANALYSIS: {indexing_run_id}")
    print(f"{'='*80}")
    print(f"Status: {run_data['status']}")
    print(f"Upload Type: {run_data['upload_type']}")
    print(f"Started: {run_data['started_at']}")
    print(f"Completed: {run_data['completed_at']}")
    
    # Get pipeline config to see OCR strategy
    pipeline_config = run_data.get("pipeline_config", {})
    ocr_strategy = pipeline_config.get("partition", {}).get("ocr_strategy", "unknown")
    print(f"OCR Strategy: {ocr_strategy}")
    
    # Get all documents for this indexing run
    docs_response = supabase.table("documents").select("*").eq("index_run_id", indexing_run_id).execute()
    documents = docs_response.data
    
    print(f"\nTotal Documents: {len(documents)}")
    
    # Check if any document has drawing stats in summary
    for doc in documents:
        partition_summary = doc.get("step_results", {}).get("PartitionStep", {}).get("summary_stats", {})
        if "total_drawing_items" in partition_summary:
            print(f"✅ Drawing statistics found in partition summary!")
            print(f"   - Total drawing items: {partition_summary.get('total_drawing_items', 0)}")
            print(f"   - Pages with vector drawings: {partition_summary.get('pages_with_vector_drawings', 0)}")
            print(f"   - Pages with any drawings: {partition_summary.get('pages_with_any_drawings', 0)}")
        else:
            print(f"⚠️  No drawing statistics in partition summary (old indexing run)")
    
    print(f"{'='*80}\n")
    
    # Analyze each document
    document_stats = []
    total_images_detected = 0
    total_tables_detected = 0
    total_pages_extracted = 0
    total_images_captioned = 0
    total_tables_captioned = 0
    total_vector_drawing_pages = 0
    total_pages_with_drawings = 0
    
    for doc in documents:
        doc_id = doc["id"]
        filename = doc["filename"]
        
        # Get partition step results
        partition_results = doc.get("step_results", {}).get("PartitionStep", {})
        summary_stats = partition_results.get("summary_stats", {})
        metadata = partition_results.get("metadata", {})
        data = partition_results.get("data", {})
        
        # Get processing strategy
        processing_strategy = summary_stats.get("processing_strategy", "unknown")
        
        # Get counts from summary stats
        text_elements = summary_stats.get("text_elements", 0)
        table_elements_count = summary_stats.get("table_elements", 0)
        extracted_pages_count = summary_stats.get("extracted_pages", 0)
        pages_analyzed = summary_stats.get("pages_analyzed", 0)
        
        # Get original counts (what PyMuPDF detected)
        original_image_count = summary_stats.get("original_image_count", 0)
        
        # Get enrichment step results to see what was captioned
        enrichment_results = doc.get("step_results", {}).get("EnrichmentStep", {})
        enrichment_stats = enrichment_results.get("summary_stats", {})
        enrichment_data = enrichment_results.get("data", {})
        
        # Count captioned items from the actual enrichment data
        # The enrichment step stores captions in extracted_pages dictionary
        extracted_pages = enrichment_data.get("extracted_pages", {})
        captions_list = []
        images_captioned = 0
        tables_captioned = 0
        
        # Check extracted pages for captions (full page images)
        for page_num, page_data in extracted_pages.items():
            if "enrichment_metadata" in page_data:
                enrich_meta = page_data["enrichment_metadata"]
                if enrich_meta.get("vlm_processed") and enrich_meta.get("full_page_image_caption"):
                    images_captioned += 1
                    captions_list.append({
                        "page_number": page_num,
                        "type": "image",
                        "caption": enrich_meta.get("full_page_image_caption", ""),
                        "word_count": enrich_meta.get("caption_word_count", 0)
                    })
        
        # Check table elements for captions
        table_elements = enrichment_data.get("table_elements", [])
        for table in table_elements:
            if "enrichment_metadata" in table and table["enrichment_metadata"].get("vlm_processed"):
                if table["enrichment_metadata"].get("vlm_caption"):
                    tables_captioned += 1
                    captions_list.append({
                        "page_number": table.get("page", "?"),
                        "type": "table",
                        "caption": table["enrichment_metadata"].get("vlm_caption", "")
                    })
        
        # Use summary stats if direct counting didn't work
        if images_captioned == 0 and tables_captioned == 0:
            # Use summary stats as the source of truth
            images_captioned = enrichment_stats.get("images_processed", 0)
            tables_captioned = enrichment_stats.get("tables_processed", 0)
        
        # Get page-level analysis
        page_analysis = data.get("page_analysis", {})
        
        # Count pages with meaningful images and vector drawings
        pages_with_images = 0
        total_meaningful_images = 0
        pages_with_vector_drawings = 0
        pages_with_any_drawings = 0
        total_drawing_items = 0
        
        for page_num, page_data in page_analysis.items():
            if page_data.get("meaningful_images", 0) > 0:
                pages_with_images += 1
                total_meaningful_images += page_data.get("meaningful_images", 0)
            
            # Count vector drawings - check both drawing_items and drawing_item_count
            drawing_items = page_data.get("drawing_items", page_data.get("drawing_item_count", 0))
            if drawing_items > 0:
                pages_with_any_drawings += 1
                total_drawing_items += drawing_items
            
            if page_data.get("has_vector_drawings", False):
                pages_with_vector_drawings += 1
        
        # Store document stats
        doc_stats = {
            "filename": filename[:25] + "..." if len(filename) > 25 else filename,
            "processing": processing_strategy,
            "pages": pages_analyzed,
            "text_elems": text_elements,
            "tables_detected": table_elements_count,
            "images_detected": original_image_count,
            "meaningful_imgs": total_meaningful_images,
            "vector_pages": pages_with_vector_drawings,
            "pages_extracted": extracted_pages_count,
            "imgs_captioned": images_captioned,
            "tables_captioned": tables_captioned,
            "total_drawings": total_drawing_items,
        }
        
        document_stats.append(doc_stats)
        
        # Update totals
        total_images_detected += original_image_count
        total_tables_detected += table_elements_count
        total_pages_extracted += extracted_pages_count
        total_images_captioned += images_captioned
        total_tables_captioned += tables_captioned
        total_vector_drawing_pages += pages_with_vector_drawings
        total_pages_with_drawings += pages_with_any_drawings
        
        # Print detailed page analysis for documents with images
        if original_image_count > 0 or table_elements_count > 0 or captions_list:
            print(f"\n📄 Document: {filename}")
            print(f"   Processing Strategy: {processing_strategy}")
            print(f"   Pages Analyzed: {pages_analyzed}")
            
            # Show page-by-page breakdown
            if page_analysis:
                print(f"\n   Page-by-Page Analysis:")
                for page_num in sorted(page_analysis.keys(), key=lambda x: int(x)):
                    page_data = page_analysis[page_num]
                    img_count = page_data.get("image_count", 0)
                    meaningful = page_data.get("meaningful_images", 0)
                    tables = page_data.get("table_count", 0)
                    drawing_items = page_data.get("drawing_items", page_data.get("drawing_item_count", 0))
                    has_vector = page_data.get("has_vector_drawings", False)
                    complexity = page_data.get("complexity", "unknown")
                    needs_extraction = page_data.get("needs_extraction", False)
                    
                    if img_count > 0 or tables > 0 or drawing_items > 0:
                        extraction_status = "✅ EXTRACTED" if needs_extraction else "❌ SKIPPED"
                        vector_indicator = " 🎨 VECTOR" if has_vector else ""
                        print(f"      Page {page_num}: {img_count} imgs ({meaningful} meaningful), "
                              f"{tables} tables, {drawing_items:,} drawing items, "
                              f"complexity={complexity}{vector_indicator} → {extraction_status}")
            
            # Show enrichment captions if available
            if captions_list:
                print(f"\n   📝 Captions Generated ({len(captions_list)} total):")
                for caption in captions_list[:5]:  # Show first 5 captions
                    page_num = caption.get("page_number", "?")
                    caption_type = caption.get("type", "unknown")
                    caption_text = caption.get("caption", "")
                    # Truncate long captions
                    if len(caption_text) > 100:
                        caption_text = caption_text[:100] + "..."
                    print(f"      Page {page_num} ({caption_type}): {caption_text}")
    
    # Print summary table
    print(f"\n{'='*80}")
    print("DOCUMENT SUMMARY TABLE")
    print(f"{'='*80}\n")
    
    # Print header
    print(f"{'Document':<28} {'Proc':<10} {'Pgs':<4} {'Txt':<5} {'Tbls':<5} {'Imgs':<5} {'Mean':<5} {'Vec':<4} {'Extr':<5} {'ICap':<5} {'TCap':<5}")
    print("-" * 110)
    
    # Print each document's stats
    for stats in document_stats:
        print(f"{stats['filename']:<28} {stats['processing']:<10} {stats['pages']:<4} {stats['text_elems']:<5} "
              f"{stats['tables_detected']:<5} {stats['images_detected']:<5} {stats['meaningful_imgs']:<5} "
              f"{stats['vector_pages']:<4} {stats['pages_extracted']:<5} {stats['imgs_captioned']:<5} {stats['tables_captioned']:<5}")
    
    # Print overall statistics
    print(f"\n{'='*80}")
    print("OVERALL STATISTICS")
    print(f"{'='*80}")
    print(f"Total Images Detected (PyMuPDF get_images): {total_images_detected}")
    print(f"Total Tables Detected: {total_tables_detected}")
    print(f"Total Pages with Vector Drawings (≥4000 items): {total_vector_drawing_pages}")
    print(f"Total Pages with Any Drawing Items: {total_pages_with_drawings}")
    print(f"Total Pages Extracted as Images: {total_pages_extracted}")
    print(f"Total Images Captioned (VLM): {total_images_captioned}")
    print(f"Total Tables Captioned (VLM): {total_tables_captioned}")
    
    # Calculate detection vs captioning ratio
    total_captions = total_images_captioned + total_tables_captioned
    if total_pages_extracted > 0:
        caption_rate = (total_captions / total_pages_extracted) * 100
        print(f"\nCaptioning Rate: {caption_rate:.1f}% of extracted pages were captioned ({total_captions}/{total_pages_extracted})")
    
    # Print detailed enrichment info
    print(f"\n📊 Enrichment Details:")
    print(f"   - Image captions generated: {total_images_captioned}")
    print(f"   - Table captions generated: {total_tables_captioned}")
    print(f"   - Total captions: {total_captions}")
    
    # Try to get chunks if table exists
    try:
        chunks_response = supabase.table("chunks").select("id, metadata").eq("index_run_id", indexing_run_id).execute()
        chunks_with_captions = 0
        for chunk in chunks_response.data:
            metadata = chunk.get("metadata", {})
            if metadata.get("enriched_content") or metadata.get("captions"):
                chunks_with_captions += 1
        
        print(f"\nChunks with Captions: {chunks_with_captions}/{len(chunks_response.data)}")
    except:
        print("\nNote: Chunks table not available for caption usage analysis")
    
    return {
        "total_documents": len(documents),
        "total_images_detected": total_images_detected,
        "total_tables_detected": total_tables_detected,
        "total_pages_extracted": total_pages_extracted,
        "total_images_captioned": total_images_captioned,
        "total_tables_captioned": total_tables_captioned,
        "total_vector_drawing_pages": total_vector_drawing_pages,
        "total_pages_with_drawings": total_pages_with_drawings,
    }


async def analyze_vector_graphics_detection(indexing_run_id: str, stats: Dict[str, Any]):
    """
    Analyze vector graphics detection with the new implementation.
    """
    print(f"\n{'='*80}")
    print("VECTOR GRAPHICS DETECTION ANALYSIS")
    print(f"{'='*80}\n")
    
    print("✅ NEW DETECTION CAPABILITIES:")
    print("   PyMuPDF's get_drawings() now detects vector graphics!")
    print("   - Lines, curves, paths, and filled shapes")
    print("   - CAD drawings and architectural floor plans")
    print("   - Technical diagrams with vector elements")
    print("   - Threshold: ≥4000 drawing items = complex vector drawing")
    
    print("\n📊 Updated Detection Logic (Precedence Order):")
    print("   1. Meaningful Images (≥2) → Extract as 'complex' or 'simple'")
    print("   2. Vector Drawings (≥4000 items) → Extract as 'complex_vector_drawing'")
    print("   3. Tables (≥1) → Extract as 'simple'")
    print("   4. Special cases (fragmented, diagram) → Extract accordingly")
    
    vector_pages = stats.get('total_vector_drawing_pages', 0)
    pages_with_drawings = stats.get('total_pages_with_drawings', 0)
    
    if vector_pages > 0:
        print(f"\n🎨 Vector Drawing Detection Results:")
        print(f"   - Pages with complex vector drawings: {vector_pages}")
        print(f"   - Pages with any drawing items: {pages_with_drawings}")
        print(f"   - Successfully detected architectural/technical drawings!")
    else:
        print(f"\n📝 No Complex Vector Drawings Detected:")
        print(f"   - Pages with drawing items (below threshold): {pages_with_drawings}")
        print(f"   - May need to adjust threshold if drawings expected")


async def main():
    # Analyze the specific indexing run
    # You can pass an indexing run ID as a command line argument
    import sys
    if len(sys.argv) > 1:
        indexing_run_id = sys.argv[1]
        print(f"Using provided indexing run ID: {indexing_run_id}")
    else:
        indexing_run_id = "9cf7bdc2-8dd5-4f0b-9a90-8c07e3cdbd6b"  # Default run
    
    # Get detailed statistics
    stats = await get_indexing_run_stats(indexing_run_id)
    
    # Analyze vector graphics detection with stats
    await analyze_vector_graphics_detection(indexing_run_id, stats)
    
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}\n")
    
    vector_pages = stats.get('total_vector_drawing_pages', 0)
    
    if vector_pages > 0:
        print("✅ System is now successfully detecting vector graphics!")
        print(f"   - Found {vector_pages} pages with complex vector drawings")
        print("   - These pages are being extracted and captioned")
        print("   - Architectural and technical drawings are preserved")
    else:
        print("Current system capabilities:")
        print("1. ✅ Vector drawing detection via get_drawings()")
        print("2. ✅ Threshold-based classification (≥4000 items)")
        print("3. ✅ Proper precedence: Images → Drawings → Tables")
        
        print("\nIf vector drawings were expected but not found:")
        print("1. Check if drawing item threshold (4000) needs adjustment")
        print("2. Verify PDF contains actual vector graphics (not rasterized)")
        print("3. Some PDFs may have drawings as embedded images instead")


if __name__ == "__main__":
    asyncio.run(main())