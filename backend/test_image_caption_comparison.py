#!/usr/bin/env python3
"""
Image/Table Caption Comparison Tool
Creates HTML visualization to compare extracted images/tables with their VLM captions
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv
import base64

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
load_dotenv()

from src.config.database import get_supabase_admin_client
from src.services.storage_service import StorageService


async def fetch_image_table_chunks(run_id: str) -> List[Dict[str, Any]]:
    """Fetch chunks that should have images or tables with VLM captions"""
    print(f"📂 Fetching image/table chunks from indexing run: {run_id}")
    
    db = get_supabase_admin_client()
    
    # Get chunks that are tables, images, or have VLM enrichment
    response = (
        db.table("document_chunks")
        .select("*")
        .eq("indexing_run_id", run_id)
        .execute()
    )
    
    all_chunks = response.data
    
    # Filter for chunks that should have visual content or VLM captions
    visual_chunks = []
    for chunk in all_chunks:
        metadata = chunk.get("metadata", {})
        
        # Include if it has enrichment metadata (VLM captions)
        if metadata.get("enrichment_metadata"):
            visual_chunks.append(chunk)
            continue
            
        # Include if it's categorized as Table
        if metadata.get("element_category") == "Table":
            visual_chunks.append(chunk)
            continue
            
        # Include if it's ExtractedPage (full page processing)
        if metadata.get("element_category") == "ExtractedPage":
            visual_chunks.append(chunk)
            continue
            
        # Include if it mentions images or tables in content
        content = chunk.get("content", "").lower()
        if any(keyword in content for keyword in ["image", "table", "tabel", "figur", "diagram"]):
            visual_chunks.append(chunk)
    
    print(f"✅ Found {len(visual_chunks)} visual/VLM chunks out of {len(all_chunks)} total")
    
    return visual_chunks


async def get_image_files_for_run(run_id: str) -> Dict[str, str]:
    """Get available image files from storage for this indexing run"""
    
    storage_service = StorageService()
    
    # Try to find image files in storage
    # This is a simplified approach - in practice you'd need to know the exact storage structure
    image_files = {}
    
    # Common image file patterns for indexing runs
    possible_paths = [
        f"indexing_runs/{run_id}/images/",
        f"indexing_runs/{run_id}/partition/images/",
        f"indexing_runs/{run_id}/enrichment/images/",
        f"documents/{run_id}/images/",  # Alternative structure
    ]
    
    print("📁 Searching for image files in storage...")
    
    # Note: This would need to be implemented based on your actual storage structure
    # For now, we'll work with the metadata we have
    
    return image_files


def create_html_comparison(chunks: List[Dict[str, Any]], image_files: Dict[str, str], output_path: Path):
    """Create HTML file comparing images/tables with their captions"""
    
    print("🎨 Creating HTML comparison visualization...")
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image/Table Caption Comparison</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 20px; 
                background-color: #f5f5f5; 
            }
            .header { 
                background-color: #2c3e50; 
                color: white; 
                padding: 20px; 
                border-radius: 8px; 
                margin-bottom: 20px; 
            }
            .chunk-card { 
                background: white; 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                margin: 20px 0; 
                padding: 20px; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
            }
            .chunk-header { 
                background-color: #34495e; 
                color: white; 
                padding: 10px; 
                border-radius: 5px; 
                margin-bottom: 15px; 
            }
            .content-section { 
                margin: 15px 0; 
                padding: 10px; 
                border-left: 4px solid #3498db; 
                background-color: #ecf0f1; 
            }
            .vlm-caption { 
                background-color: #e8f5e8; 
                border: 2px solid #27ae60; 
                padding: 15px; 
                border-radius: 5px; 
                margin: 10px 0; 
            }
            .no-vlm { 
                background-color: #ffeaea; 
                border: 2px solid #e74c3c; 
                padding: 15px; 
                border-radius: 5px; 
                margin: 10px 0; 
            }
            .metadata { 
                background-color: #f8f9fa; 
                padding: 10px; 
                border-radius: 5px; 
                font-size: 0.9em; 
                margin: 10px 0; 
            }
            .image-placeholder { 
                background-color: #bdc3c7; 
                color: #2c3e50; 
                padding: 40px; 
                text-align: center; 
                border-radius: 5px; 
                margin: 10px 0; 
            }
            .stats { 
                background-color: #3498db; 
                color: white; 
                padding: 15px; 
                border-radius: 5px; 
                margin: 10px 0; 
            }
        </style>
    </head>
    <body>
    """
    
    # Header
    html_content += f"""
    <div class="header">
        <h1>📊 Image/Table Caption Comparison</h1>
        <p>Analysis of VLM captioning quality for indexing run</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Total chunks analyzed:</strong> {len(chunks)}</p>
    </div>
    """
    
    # Statistics
    with_vlm = sum(1 for c in chunks if c.get("metadata", {}).get("enrichment_metadata"))
    tables = sum(1 for c in chunks if c.get("metadata", {}).get("element_category") == "Table")
    extracted_pages = sum(1 for c in chunks if c.get("metadata", {}).get("element_category") == "ExtractedPage")
    
    html_content += f"""
    <div class="stats">
        <h2>📈 Statistics</h2>
        <p><strong>Chunks with VLM captions:</strong> {with_vlm} ({(with_vlm/len(chunks)*100):.1f}%)</p>
        <p><strong>Table chunks:</strong> {tables}</p>
        <p><strong>Extracted page chunks:</strong> {extracted_pages}</p>
    </div>
    """
    
    # Process each chunk
    for i, chunk in enumerate(chunks):
        metadata = chunk.get("metadata", {})
        enrichment = metadata.get("enrichment_metadata", {})
        
        chunk_id = chunk.get("chunk_id", "unknown")
        page_number = metadata.get("page_number", "unknown")
        element_category = metadata.get("element_category", "unknown")
        content = chunk.get("content", "")
        
        html_content += f"""
        <div class="chunk-card">
            <div class="chunk-header">
                <h3>Chunk {i+1}: {element_category} (Page {page_number})</h3>
                <p><strong>Chunk ID:</strong> {chunk_id}</p>
            </div>
        """
        
        # Original content
        html_content += f"""
        <div class="content-section">
            <h4>📄 Original Content ({len(content)} characters):</h4>
            <p>{content[:500]}{'...' if len(content) > 500 else ''}</p>
        </div>
        """
        
        # VLM Captions
        if enrichment:
            html_content += '<div class="vlm-caption">'
            html_content += '<h4>🤖 VLM Captions:</h4>'
            
            if enrichment.get("table_image_caption"):
                html_content += f'<p><strong>Table Image Caption:</strong> {enrichment["table_image_caption"]}</p>'
            
            if enrichment.get("table_html_caption"):
                html_content += f'<p><strong>Table HTML Caption:</strong> {enrichment["table_html_caption"]}</p>'
            
            if enrichment.get("full_page_image_caption"):
                html_content += f'<p><strong>Full Page Caption:</strong> {enrichment["full_page_image_caption"]}</p>'
            
            html_content += '</div>'
        else:
            html_content += '''
            <div class="no-vlm">
                <h4>❌ No VLM Captions</h4>
                <p>This chunk should potentially have VLM captions but none were found.</p>
            </div>
            '''
        
        # Image placeholder (since we can't easily access the actual images)
        html_content += '''
        <div class="image-placeholder">
            <h4>🖼️ Image Not Available</h4>
            <p>Image extraction would require access to the original files and storage system.</p>
            <p>In a full implementation, the extracted image would be displayed here.</p>
        </div>
        '''
        
        # Detailed metadata
        html_content += f"""
        <div class="metadata">
            <h4>🔍 Metadata:</h4>
            <p><strong>Processing Strategy:</strong> {metadata.get('processing_strategy', 'unknown')}</p>
            <p><strong>Content Length:</strong> {metadata.get('content_length', 'unknown')}</p>
            <p><strong>Has Images on Page:</strong> {metadata.get('has_images_on_page', 'unknown')}</p>
            <p><strong>Has Tables on Page:</strong> {metadata.get('has_tables_on_page', 'unknown')}</p>
            <p><strong>Image Filepath:</strong> {metadata.get('image_filepath', 'none')}</p>
        </div>
        """
        
        html_content += '</div>'  # Close chunk-card
    
    html_content += """
    </body>
    </html>
    """
    
    # Write HTML file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML comparison saved to {output_path}")


async def main():
    """Main execution function"""
    
    print("=" * 60)
    print("IMAGE/TABLE CAPTION COMPARISON")
    print("=" * 60)
    
    INDEXING_RUN_ID = "1ed7dc55-25ea-4b37-8f03-33d9f7aeeff8"
    
    # Create output directory
    output_dir = Path("chunk_analysis_output")
    output_dir.mkdir(exist_ok=True)
    
    # Fetch visual chunks
    visual_chunks = await fetch_image_table_chunks(INDEXING_RUN_ID)
    
    if not visual_chunks:
        print("❌ No visual chunks found")
        return
    
    # Get image files (would need storage access implementation)
    image_files = await get_image_files_for_run(INDEXING_RUN_ID)
    
    # Create HTML comparison
    html_output = output_dir / f"image_caption_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    create_html_comparison(visual_chunks, image_files, html_output)
    
    # Also save detailed JSON analysis
    analysis = {
        "indexing_run_id": INDEXING_RUN_ID,
        "total_visual_chunks": len(visual_chunks),
        "analysis_timestamp": datetime.now().isoformat(),
        "chunks": []
    }
    
    for chunk in visual_chunks:
        metadata = chunk.get("metadata", {})
        enrichment = metadata.get("enrichment_metadata", {})
        
        chunk_analysis = {
            "chunk_id": chunk.get("chunk_id"),
            "page_number": metadata.get("page_number"),
            "element_category": metadata.get("element_category"),
            "content_length": len(chunk.get("content", "")),
            "content_preview": chunk.get("content", "")[:200],
            "has_vlm_captions": bool(enrichment),
            "vlm_caption_types": [],
            "processing_strategy": metadata.get("processing_strategy"),
            "has_images_on_page": metadata.get("has_images_on_page"),
            "has_tables_on_page": metadata.get("has_tables_on_page"),
            "image_filepath": metadata.get("image_filepath")
        }
        
        if enrichment:
            if enrichment.get("table_image_caption"):
                chunk_analysis["vlm_caption_types"].append("table_image_caption")
            if enrichment.get("table_html_caption"):
                chunk_analysis["vlm_caption_types"].append("table_html_caption")
            if enrichment.get("full_page_image_caption"):
                chunk_analysis["vlm_caption_types"].append("full_page_image_caption")
        
        analysis["chunks"].append(chunk_analysis)
    
    # Save JSON analysis
    json_output = output_dir / f"image_caption_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Analysis complete!")
    print(f"📄 HTML visualization: {html_output}")
    print(f"📊 JSON analysis: {json_output}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    with_vlm = sum(1 for c in visual_chunks if c.get("metadata", {}).get("enrichment_metadata"))
    tables = sum(1 for c in visual_chunks if c.get("metadata", {}).get("element_category") == "Table")
    extracted_pages = sum(1 for c in visual_chunks if c.get("metadata", {}).get("element_category") == "ExtractedPage")
    
    print(f"Total visual chunks analyzed: {len(visual_chunks)}")
    print(f"Chunks with VLM captions: {with_vlm} ({(with_vlm/len(visual_chunks)*100):.1f}%)")
    print(f"Table chunks: {tables}")
    print(f"ExtractedPage chunks: {extracted_pages}")
    print(f"Average content length: {sum(len(c.get('content', '')) for c in visual_chunks) / len(visual_chunks):.1f} chars")


if __name__ == "__main__":
    asyncio.run(main())