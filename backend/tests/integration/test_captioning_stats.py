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
    print(f"{'='*80}\n")
    
    # Analyze each document
    document_stats = []
    total_images_detected = 0
    total_tables_detected = 0
    total_pages_extracted = 0
    total_images_captioned = 0
    total_tables_captioned = 0
    
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
        table_elements = summary_stats.get("table_elements", 0)
        extracted_pages = summary_stats.get("extracted_pages", 0)
        pages_analyzed = summary_stats.get("pages_analyzed", 0)
        
        # Get original counts (what PyMuPDF detected)
        original_image_count = summary_stats.get("original_image_count", 0)
        
        # Get enrichment step results to see what was captioned
        enrichment_results = doc.get("step_results", {}).get("EnrichmentStep", {})
        enrichment_stats = enrichment_results.get("summary_stats", {})
        
        # Count captioned items
        images_captioned = enrichment_stats.get("images_captioned", 0)
        tables_captioned = enrichment_stats.get("tables_captioned", 0)
        
        # Get page-level analysis
        page_analysis = data.get("page_analysis", {})
        
        # Count pages with meaningful images
        pages_with_images = 0
        total_meaningful_images = 0
        for page_num, page_data in page_analysis.items():
            if page_data.get("meaningful_images", 0) > 0:
                pages_with_images += 1
                total_meaningful_images += page_data.get("meaningful_images", 0)
        
        # Store document stats
        doc_stats = {
            "filename": filename[:30] + "..." if len(filename) > 30 else filename,
            "processing": processing_strategy,
            "pages": pages_analyzed,
            "text_elems": text_elements,
            "tables_detected": table_elements,
            "images_detected": original_image_count,
            "meaningful_imgs": total_meaningful_images,
            "pages_extracted": extracted_pages,
            "imgs_captioned": images_captioned,
            "tables_captioned": tables_captioned,
        }
        
        document_stats.append(doc_stats)
        
        # Update totals
        total_images_detected += original_image_count
        total_tables_detected += table_elements
        total_pages_extracted += extracted_pages
        total_images_captioned += images_captioned
        total_tables_captioned += tables_captioned
        
        # Print detailed page analysis for documents with images
        if original_image_count > 0 or table_elements > 0:
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
                    complexity = page_data.get("complexity", "unknown")
                    needs_extraction = page_data.get("needs_extraction", False)
                    
                    if img_count > 0 or tables > 0:
                        extraction_status = "✅ EXTRACTED" if needs_extraction else "❌ SKIPPED"
                        print(f"      Page {page_num}: {img_count} imgs ({meaningful} meaningful), "
                              f"{tables} tables, complexity={complexity} → {extraction_status}")
    
    # Print summary table
    print(f"\n{'='*80}")
    print("DOCUMENT SUMMARY TABLE")
    print(f"{'='*80}\n")
    
    # Print header
    print(f"{'Document':<35} {'Proc':<12} {'Pgs':<4} {'Txt':<5} {'Tbls':<5} {'Imgs':<5} {'Mean':<5} {'Extr':<5} {'ICap':<5} {'TCap':<5}")
    print("-" * 100)
    
    # Print each document's stats
    for stats in document_stats:
        print(f"{stats['filename']:<35} {stats['processing']:<12} {stats['pages']:<4} {stats['text_elems']:<5} "
              f"{stats['tables_detected']:<5} {stats['images_detected']:<5} {stats['meaningful_imgs']:<5} "
              f"{stats['pages_extracted']:<5} {stats['imgs_captioned']:<5} {stats['tables_captioned']:<5}")
    
    # Print overall statistics
    print(f"\n{'='*80}")
    print("OVERALL STATISTICS")
    print(f"{'='*80}")
    print(f"Total Images Detected (PyMuPDF get_images): {total_images_detected}")
    print(f"Total Tables Detected: {total_tables_detected}")
    print(f"Total Pages Extracted as Images: {total_pages_extracted}")
    print(f"Total Images Captioned (VLM): {total_images_captioned}")
    print(f"Total Tables Captioned (VLM): {total_tables_captioned}")
    
    # Calculate detection vs captioning ratio
    if total_pages_extracted > 0:
        caption_rate = (total_images_captioned / total_pages_extracted) * 100
        print(f"\nCaptioning Rate: {caption_rate:.1f}% of extracted pages were captioned")
    
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
    }


async def analyze_vector_graphics_detection(indexing_run_id: str):
    """
    Analyze why vector graphics (like architectural drawings) might not be detected.
    """
    print(f"\n{'='*80}")
    print("VECTOR GRAPHICS DETECTION ANALYSIS")
    print(f"{'='*80}\n")
    
    print("⚠️  IMPORTANT: PyMuPDF's get_images() only detects embedded raster images (JPG, PNG, etc.)")
    print("   It does NOT detect:")
    print("   - Vector graphics (SVG-like drawings)")
    print("   - CAD drawings rendered as vectors")
    print("   - Architectural floor plans drawn with lines/shapes")
    print("   - Technical diagrams created with drawing commands")
    print("\n   These are often the most important visuals in construction documents!")
    
    print("\n📊 Current Detection Logic:")
    print("   1. PyMuPDF get_images() → counts embedded raster images")
    print("   2. Meaningful image filter → width≥150px, height≥100px, area≥25000px²")
    print("   3. Extraction threshold → needs ≥2 meaningful images OR ≥1 table")
    print("   4. Special case → ≥15 images with 0 meaningful (likely diagram) → EXTRACT")
    
    print("\n💡 Why Your Architectural Drawings Were Missed:")
    print("   - They're likely vector graphics, not raster images")
    print("   - PyMuPDF reported 0 images because no embedded JPG/PNG found")
    print("   - Page marked as 'text_only' and skipped for extraction")
    
    print("\n🔧 Potential Solutions:")
    print("   1. Always extract pages with high drawing command density")
    print("   2. Use PyMuPDF's get_drawings() to detect vector content")
    print("   3. Analyze page ink coverage to detect visual-heavy pages")
    print("   4. Lower extraction thresholds for construction documents")
    print("   5. Force extraction of all pages (performance trade-off)")


async def main():
    # Analyze the specific indexing run
    indexing_run_id = "9cf7bdc2-8dd5-4f0b-9a90-8c07e3cdbd6b"  # Most recent completed run
    
    # Get detailed statistics
    stats = await get_indexing_run_stats(indexing_run_id)
    
    # Analyze vector graphics detection issue
    await analyze_vector_graphics_detection(indexing_run_id)
    
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}\n")
    
    print("Based on this analysis, the system is missing important visual content because:")
    print("1. Architectural drawings are vector graphics, not detected by get_images()")
    print("2. Current logic requires ≥2 'meaningful' raster images for extraction")
    print("3. No detection of vector/CAD drawings that are crucial for construction")
    
    print("\nSuggested improvements:")
    print("1. Add PyMuPDF get_drawings() check to detect vector content")
    print("2. For construction docs, extract ANY page with tables OR drawings")
    print("3. Consider page complexity metrics beyond just image count")


if __name__ == "__main__":
    asyncio.run(main())