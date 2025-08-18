#!/usr/bin/env python3
"""
Comprehensive Chunk Quality Analysis
Analyzes the quality issues in the chunking pipeline
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter
from dotenv import load_dotenv

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
load_dotenv()

from src.config.database import get_supabase_admin_client


async def fetch_all_chunks_with_details(run_id: str) -> List[Dict[str, Any]]:
    """Fetch all chunks from indexing run with full details"""
    print(f"📂 Fetching all chunks from indexing run: {run_id}")
    
    db = get_supabase_admin_client()
    
    response = (
        db.table("document_chunks")
        .select("*")
        .eq("indexing_run_id", run_id)
        .execute()
    )
    
    chunks = response.data
    print(f"✅ Found {len(chunks)} total chunks")
    
    return chunks


def analyze_chunk_quality_issues(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze various quality issues in chunks"""
    
    print("\n🔍 Analyzing chunk quality issues...")
    
    analysis = {
        "total_chunks": len(chunks),
        "size_distribution": {},
        "content_type_analysis": {},
        "problematic_chunks": {
            "tiny_chunks": [],
            "duplicate_content": [],
            "fragmented_lists": [],
            "poor_table_captions": [],
            "poor_image_captions": []
        },
        "processing_strategy_analysis": {},
        "vlm_captioning_analysis": {}
    }
    
    # Size analysis
    sizes = [len(chunk.get("content", "")) for chunk in chunks]
    analysis["size_distribution"] = {
        "min": min(sizes),
        "max": max(sizes),
        "mean": sum(sizes) / len(sizes),
        "median": sorted(sizes)[len(sizes)//2],
        "under_10_chars": sum(1 for s in sizes if s < 10),
        "under_50_chars": sum(1 for s in sizes if s < 50),
        "under_100_chars": sum(1 for s in sizes if s < 100),
        "over_1000_chars": sum(1 for s in sizes if s > 1000),
        "over_2000_chars": sum(1 for s in sizes if s > 2000),
    }
    
    # Content type analysis
    categories = [chunk.get("metadata", {}).get("element_category", "unknown") for chunk in chunks]
    category_counts = Counter(categories)
    analysis["content_type_analysis"] = {
        "category_distribution": dict(category_counts),
        "total_categories": len(category_counts)
    }
    
    # Processing strategy analysis
    strategies = [chunk.get("metadata", {}).get("processing_strategy", "unknown") for chunk in chunks]
    strategy_counts = Counter(strategies)
    analysis["processing_strategy_analysis"] = dict(strategy_counts)
    
    # Find problematic chunks
    content_map = {}  # Track duplicate content
    
    for chunk in chunks:
        content = chunk.get("content", "")
        metadata = chunk.get("metadata", {})
        
        # Tiny chunks (< 50 characters)
        if len(content) < 50:
            analysis["problematic_chunks"]["tiny_chunks"].append({
                "chunk_id": chunk.get("chunk_id"),
                "content": content,
                "size": len(content),
                "page_number": metadata.get("page_number"),
                "element_category": metadata.get("element_category"),
                "processing_strategy": metadata.get("processing_strategy")
            })
        
        # Track content for duplicate detection
        content_key = content[:100]  # First 100 chars as key
        if content_key in content_map:
            content_map[content_key].append(chunk)
        else:
            content_map[content_key] = [chunk]
        
        # Fragmented list items (single bullets/references)
        if (metadata.get("element_category") == "NarrativeText" and 
            any(indicator in content for indicator in ["•", "I12727", ".pdf"])):
            analysis["problematic_chunks"]["fragmented_lists"].append({
                "chunk_id": chunk.get("chunk_id"),
                "content": content[:200] + "..." if len(content) > 200 else content,
                "size": len(content),
                "page_number": metadata.get("page_number")
            })
        
        # Poor table captions (tables without meaningful descriptions)
        if metadata.get("element_category") == "Table":
            if len(content) < 100 or "Table" in content and len(content.split()) < 10:
                analysis["problematic_chunks"]["poor_table_captions"].append({
                    "chunk_id": chunk.get("chunk_id"),
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "size": len(content),
                    "page_number": metadata.get("page_number"),
                    "enrichment_metadata": metadata.get("enrichment_metadata")
                })
    
    # Find duplicates
    for content_key, chunk_list in content_map.items():
        if len(chunk_list) > 1:
            analysis["problematic_chunks"]["duplicate_content"].append({
                "content_preview": content_key,
                "duplicate_count": len(chunk_list),
                "chunk_ids": [c.get("chunk_id") for c in chunk_list],
                "pages": [c.get("metadata", {}).get("page_number") for c in chunk_list]
            })
    
    # VLM Captioning Analysis
    vlm_chunks = [c for c in chunks if c.get("metadata", {}).get("enrichment_metadata")]
    analysis["vlm_captioning_analysis"] = {
        "total_chunks_with_vlm": len(vlm_chunks),
        "percentage_with_vlm": (len(vlm_chunks) / len(chunks)) * 100 if chunks else 0
    }
    
    # Analyze VLM quality
    if vlm_chunks:
        vlm_analysis = analyze_vlm_quality(vlm_chunks)
        analysis["vlm_captioning_analysis"].update(vlm_analysis)
    
    return analysis


def analyze_vlm_quality(vlm_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze quality of VLM-generated captions"""
    
    vlm_analysis = {
        "table_captions": {"count": 0, "examples": []},
        "image_captions": {"count": 0, "examples": []},
        "full_page_captions": {"count": 0, "examples": []}
    }
    
    for chunk in vlm_chunks:
        enrichment = chunk.get("metadata", {}).get("enrichment_metadata", {})
        
        # Table captions
        if enrichment.get("table_image_caption") or enrichment.get("table_html_caption"):
            vlm_analysis["table_captions"]["count"] += 1
            if len(vlm_analysis["table_captions"]["examples"]) < 3:
                vlm_analysis["table_captions"]["examples"].append({
                    "chunk_id": chunk.get("chunk_id"),
                    "page_number": chunk.get("metadata", {}).get("page_number"),
                    "content_preview": chunk.get("content", "")[:200],
                    "table_image_caption": enrichment.get("table_image_caption"),
                    "table_html_caption": enrichment.get("table_html_caption")
                })
        
        # Image captions
        if enrichment.get("full_page_image_caption"):
            vlm_analysis["image_captions"]["count"] += 1
            if len(vlm_analysis["image_captions"]["examples"]) < 3:
                vlm_analysis["image_captions"]["examples"].append({
                    "chunk_id": chunk.get("chunk_id"),
                    "page_number": chunk.get("metadata", {}).get("page_number"),
                    "content_preview": chunk.get("content", "")[:200],
                    "full_page_image_caption": enrichment.get("full_page_image_caption")
                })
    
    return vlm_analysis


def identify_processing_issues(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Identify specific processing and extraction issues"""
    
    issues = {
        "missing_section_titles": 0,
        "unknown_filenames": 0,
        "processing_strategy_inconsistencies": [],
        "image_extraction_issues": [],
        "table_extraction_issues": []
    }
    
    strategies_by_page = {}
    
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        
        # Missing section titles
        if not metadata.get("section_title_inherited") or metadata.get("section_title_inherited") == "Unknown Section":
            issues["missing_section_titles"] += 1
        
        # Unknown filenames
        if not metadata.get("source_filename") or metadata.get("source_filename") == "Unknown":
            issues["unknown_filenames"] += 1
        
        # Track processing strategies by page
        page = metadata.get("page_number")
        strategy = metadata.get("processing_strategy")
        if page and strategy:
            if page not in strategies_by_page:
                strategies_by_page[page] = set()
            strategies_by_page[page].add(strategy)
    
    # Find pages with multiple processing strategies (inconsistencies)
    for page, strategies in strategies_by_page.items():
        if len(strategies) > 1:
            issues["processing_strategy_inconsistencies"].append({
                "page": page,
                "strategies": list(strategies)
            })
    
    return issues


async def main():
    """Main analysis function"""
    
    print("=" * 60)
    print("CHUNK QUALITY ANALYSIS")
    print("=" * 60)
    
    INDEXING_RUN_ID = "1ed7dc55-25ea-4b37-8f03-33d9f7aeeff8"
    
    # Create output directory
    output_dir = Path("chunk_analysis_output")
    output_dir.mkdir(exist_ok=True)
    
    # Fetch all chunks
    chunks = await fetch_all_chunks_with_details(INDEXING_RUN_ID)
    
    if not chunks:
        print("❌ No chunks found for analysis")
        return
    
    # Analyze quality issues
    quality_analysis = analyze_chunk_quality_issues(chunks)
    
    # Identify processing issues
    processing_issues = identify_processing_issues(chunks)
    
    # Combine results
    results = {
        "analysis_metadata": {
            "indexing_run_id": INDEXING_RUN_ID,
            "total_chunks_analyzed": len(chunks),
            "analysis_timestamp": datetime.now().isoformat()
        },
        "quality_analysis": quality_analysis,
        "processing_issues": processing_issues,
        "recommendations": generate_recommendations(quality_analysis, processing_issues)
    }
    
    # Save results
    output_file = output_dir / f"chunk_quality_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Analysis complete! Results saved to {output_file}")
    
    # Print summary
    print_summary(results)


def generate_recommendations(quality_analysis: Dict[str, Any], processing_issues: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on analysis"""
    
    recommendations = []
    
    # Chunk size issues
    tiny_chunks = len(quality_analysis["problematic_chunks"]["tiny_chunks"])
    if tiny_chunks > 0:
        recommendations.append(f"CRITICAL: Implement minimum chunk size validation - found {tiny_chunks} chunks under 50 characters")
    
    # Duplicate content
    duplicates = len(quality_analysis["problematic_chunks"]["duplicate_content"])
    if duplicates > 0:
        recommendations.append(f"HIGH: Fix duplicate content issue - found {duplicates} sets of duplicate chunks")
    
    # Fragmented lists
    fragmented = len(quality_analysis["problematic_chunks"]["fragmented_lists"])
    if fragmented > 0:
        recommendations.append(f"HIGH: Improve list item grouping - found {fragmented} fragmented list items")
    
    # VLM captioning
    vlm_percentage = quality_analysis["vlm_captioning_analysis"]["percentage_with_vlm"]
    if vlm_percentage < 10:
        recommendations.append(f"MEDIUM: Low VLM usage - only {vlm_percentage:.1f}% of chunks use VLM captions")
    
    # Processing inconsistencies
    inconsistencies = len(processing_issues["processing_strategy_inconsistencies"])
    if inconsistencies > 0:
        recommendations.append(f"LOW: Processing strategy inconsistencies on {inconsistencies} pages")
    
    # Add semantic chunking recommendation
    recommendations.append("CRITICAL: Implement semantic text splitter to replace element-only chunking")
    recommendations.append("HIGH: Add chunk merging logic for chunks under min_chunk_size")
    recommendations.append("MEDIUM: Implement HNSW index usage for 3x faster retrieval")
    
    return recommendations


def print_summary(results: Dict[str, Any]):
    """Print analysis summary"""
    
    print("\n" + "=" * 60)
    print("CHUNK QUALITY SUMMARY")
    print("=" * 60)
    
    qa = results["quality_analysis"]
    pi = results["processing_issues"]
    
    print(f"\n📊 BASIC STATISTICS:")
    print(f"  Total chunks: {qa['total_chunks']}")
    print(f"  Size range: {qa['size_distribution']['min']} - {qa['size_distribution']['max']} characters")
    print(f"  Mean size: {qa['size_distribution']['mean']:.1f} characters")
    
    print(f"\n⚠️  QUALITY ISSUES:")
    print(f"  Chunks under 10 chars: {qa['size_distribution']['under_10_chars']}")
    print(f"  Chunks under 50 chars: {qa['size_distribution']['under_50_chars']}")  
    print(f"  Chunks under 100 chars: {qa['size_distribution']['under_100_chars']}")
    print(f"  Duplicate content sets: {len(qa['problematic_chunks']['duplicate_content'])}")
    print(f"  Fragmented list items: {len(qa['problematic_chunks']['fragmented_lists'])}")
    
    print(f"\n🔧 PROCESSING ANALYSIS:")
    print(f"  Processing strategy: {list(qa['processing_strategy_analysis'].keys())}")
    print(f"  Missing section titles: {pi['missing_section_titles']}")
    print(f"  Unknown filenames: {pi['unknown_filenames']}")
    
    print(f"\n🤖 VLM ANALYSIS:")
    print(f"  Chunks with VLM captions: {qa['vlm_captioning_analysis']['total_chunks_with_vlm']}")
    print(f"  VLM usage percentage: {qa['vlm_captioning_analysis']['percentage_with_vlm']:.1f}%")
    
    print(f"\n📋 TOP RECOMMENDATIONS:")
    for i, rec in enumerate(results["recommendations"][:5], 1):
        print(f"  {i}. {rec}")


if __name__ == "__main__":
    asyncio.run(main())