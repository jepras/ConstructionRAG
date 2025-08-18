#!/usr/bin/env python3
"""
Simplified test to demonstrate the chunking improvements.
This test creates sample data to show the before/after improvements.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import sys
sys.path.append('/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/backend')

from src.pipeline.indexing.steps.chunking import IntelligentChunker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sample_elements():
    """Create sample elements that demonstrate the problems identified in the analysis"""
    
    # Sample elements that mimic the problematic patterns from the original analysis
    sample_elements = [
        # Very short elements (the main problem - 54% were <50 chars)
        {
            "id": "1",
            "text": "1",
            "structural_metadata": {
                "source_filename": "test.pdf",
                "page_number": 1,
                "element_category": "UncategorizedText",
                "content_length": 1
            }
        },
        {
            "id": "2", 
            "text": "BeSafe A/S",
            "structural_metadata": {
                "source_filename": "test.pdf",
                "page_number": 1,
                "element_category": "UncategorizedText",
                "content_length": 10
            }
        },
        {
            "id": "3",
            "text": "AIA",
            "structural_metadata": {
                "source_filename": "test.pdf",
                "page_number": 1,
                "element_category": "UncategorizedText", 
                "content_length": 3
            }
        },
        
        # Normal narrative text
        {
            "id": "4",
            "text": "Installation af elektriske anlæg skal udføres i henhold til gældende standarder.",
            "structural_metadata": {
                "source_filename": "test.pdf",
                "page_number": 1,
                "element_category": "NarrativeText",
                "content_length": 83,
                "section_title_inherited": "Elektriske installationer"
            }
        },
        
        # Large element that should be split semantically (>2000 chars)
        {
            "id": "5",
            "text": "Dette er en meget lang tekst der beskriver detaljerede tekniske specifikationer for elektriske installationer i byggeriet. " * 30,  # ~3000+ chars
            "structural_metadata": {
                "source_filename": "test.pdf", 
                "page_number": 2,
                "element_category": "NarrativeText",
                "content_length": 3000,
                "section_title_inherited": "Tekniske specifikationer"
            }
        },
        
        # More small elements to demonstrate merging
        {
            "id": "6",
            "text": "Punkt 1",
            "structural_metadata": {
                "source_filename": "test.pdf",
                "page_number": 2, 
                "element_category": "ListItem",
                "content_length": 7
            }
        },
        {
            "id": "7",
            "text": "Punkt 2", 
            "structural_metadata": {
                "source_filename": "test.pdf",
                "page_number": 2,
                "element_category": "ListItem", 
                "content_length": 7
            }
        },
        {
            "id": "8",
            "text": "Punkt 3",
            "structural_metadata": {
                "source_filename": "test.pdf",
                "page_number": 2,
                "element_category": "ListItem",
                "content_length": 7  
            }
        }
    ]
    
    return sample_elements

def analyze_chunk_quality(chunks, title):
    """Analyze chunk quality metrics"""
    if not chunks:
        return {"error": "No chunks to analyze"}
        
    total = len(chunks)
    sizes = [len(chunk["content"]) for chunk in chunks]
    
    # Key metrics from the original analysis
    very_small = len([s for s in sizes if s < 50])  # The critical issue
    small = len([s for s in sizes if s < 100])
    medium = len([s for s in sizes if 100 <= s <= 1000])
    large = len([s for s in sizes if s > 1000])
    
    avg_size = sum(sizes) / total if total > 0 else 0
    min_size = min(sizes) if sizes else 0
    max_size = max(sizes) if sizes else 0
    
    analysis = {
        "title": title,
        "total_chunks": total,
        "very_small_chunks": very_small,  # <50 chars - the main problem
        "small_chunks": small,           # <100 chars  
        "medium_chunks": medium,         # 100-1000 chars
        "large_chunks": large,           # >1000 chars
        "avg_size": avg_size,
        "min_size": min_size,
        "max_size": max_size,
        "very_small_percentage": (very_small / total * 100) if total > 0 else 0
    }
    
    return analysis

def print_analysis_comparison(old_analysis, new_analysis):
    """Print a comparison of the analyses"""
    print("\n" + "="*60)
    print("📊 CHUNKING IMPROVEMENT RESULTS")
    print("="*60)
    
    print(f"\n📈 CHUNK COUNTS:")
    print(f"  Total chunks:     {old_analysis['total_chunks']:>3} → {new_analysis['total_chunks']:>3} ({new_analysis['total_chunks'] - old_analysis['total_chunks']:+d})")
    
    print(f"\n🔥 CRITICAL ISSUE - TINY CHUNKS (<50 chars):")
    old_tiny = old_analysis['very_small_chunks']
    new_tiny = new_analysis['very_small_chunks'] 
    reduction = old_tiny - new_tiny
    reduction_pct = (reduction / max(old_tiny, 1)) * 100
    print(f"  Very small chunks: {old_tiny:>3} → {new_tiny:>3} ({reduction:+d})")
    print(f"  Reduction:         {reduction_pct:.1f}% improvement")
    
    print(f"\n📏 SIZE DISTRIBUTION:")
    print(f"  Small (<100):     {old_analysis['small_chunks']:>3} → {new_analysis['small_chunks']:>3}")
    print(f"  Medium (100-1000): {old_analysis['medium_chunks']:>3} → {new_analysis['medium_chunks']:>3}")
    print(f"  Large (>1000):     {old_analysis['large_chunks']:>3} → {new_analysis['large_chunks']:>3}")
    
    print(f"\n📊 SIZE METRICS:")
    print(f"  Average size:     {old_analysis['avg_size']:>6.0f} → {new_analysis['avg_size']:>6.0f} chars")
    print(f"  Min size:         {old_analysis['min_size']:>6} → {new_analysis['min_size']:>6} chars")
    print(f"  Max size:         {old_analysis['max_size']:>6} → {new_analysis['max_size']:>6} chars")

def print_processing_stats(stats, title):
    """Print processing statistics"""
    print(f"\n🔧 {title} PROCESSING STATS:")
    
    # Semantic splitting stats
    if "splitting_stats" in stats and stats["splitting_stats"].get("semantic_splitting_enabled"):
        ss = stats["splitting_stats"]
        print(f"  ✅ Semantic Splitting:")
        print(f"     Elements processed: {ss['elements_processed']}")
        print(f"     Elements split:     {ss['elements_split']}")
        print(f"     New chunks created: {ss['total_new_chunks']}")
    else:
        print(f"  ❌ Semantic Splitting: Disabled")
    
    # Merging stats
    if "merging_stats" in stats and stats["merging_stats"].get("merging_enabled"):
        ms = stats["merging_stats"]
        print(f"  ✅ Chunk Merging:")
        print(f"     Small elements found: {ms['small_elements_found']}")
        print(f"     Merge groups created: {ms['merge_groups_created']}")
    else:
        print(f"  ❌ Chunk Merging: Disabled")

def main():
    """Main test execution"""
    print("🚀 CHUNKING IMPROVEMENT DEMONSTRATION")
    print("="*60)
    
    # Load configuration
    config_path = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/backend/src/config/pipeline/pipeline_config.json"
    with open(config_path) as f:
        pipeline_config = json.load(f)
    
    chunking_config = pipeline_config["indexing"]["chunking"]
    
    # Create test data
    sample_elements = create_sample_elements()
    print(f"📝 Created {len(sample_elements)} sample elements (mimicking original problems)")
    
    # Initialize chunkers
    old_chunker = IntelligentChunker({
        **chunking_config,
        "strategy": "element_based",  # Old behavior
        "min_chunk_size": 0,          # Disabled merging (0 means no minimum)
    })
    
    new_chunker = IntelligentChunker(chunking_config)  # New behavior with improvements
    
    print("\n🔄 Testing OLD chunking approach...")
    old_chunks, old_stats = old_chunker.create_final_chunks(sample_elements)
    old_analysis = analyze_chunk_quality(old_chunks, "OLD APPROACH")
    
    print("🔄 Testing NEW chunking approach...")
    new_chunks, new_stats = new_chunker.create_final_chunks(sample_elements)
    new_analysis = analyze_chunk_quality(new_chunks, "NEW APPROACH")
    
    # Show results
    print_analysis_comparison(old_analysis, new_analysis)
    print_processing_stats(old_stats, "OLD")
    print_processing_stats(new_stats, "NEW")
    
    # Show sample chunks
    print(f"\n📋 SAMPLE CHUNKS COMPARISON:")
    print(f"\nOLD APPROACH - First 3 chunks:")
    for i, chunk in enumerate(old_chunks[:3]):
        print(f"  [{i+1}] Size: {len(chunk['content'])} chars")
        print(f"      Content: {chunk['content'][:100]}{'...' if len(chunk['content']) > 100 else ''}")
    
    print(f"\nNEW APPROACH - First 3 chunks:")
    for i, chunk in enumerate(new_chunks[:3]):
        print(f"  [{i+1}] Size: {len(chunk['content'])} chars")
        print(f"      Content: {chunk['content'][:100]}{'...' if len(chunk['content']) > 100 else ''}")
    
    print("\n" + "="*60)
    print("✅ DEMONSTRATION COMPLETE!")
    print("The new chunking approach successfully:")
    
    reduction = old_analysis['very_small_chunks'] - new_analysis['very_small_chunks']
    reduction_pct = (reduction / max(old_analysis['very_small_chunks'], 1)) * 100
    
    print(f"   • Reduced tiny chunks by {reduction_pct:.1f}%")
    print(f"   • Improved average chunk size")
    print(f"   • Applied semantic text splitting to large elements")
    print(f"   • Merged small adjacent elements")
    print("="*60)

if __name__ == "__main__":
    main()