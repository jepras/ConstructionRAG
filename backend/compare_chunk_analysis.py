#!/usr/bin/env python3
"""
Compare Chunk Quality Analysis Results
Compares results from two indexing runs to show improvements
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

def load_analysis_results(file_path: str) -> Dict[str, Any]:
    """Load analysis results from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def compare_chunk_analyses(old_results: Dict[str, Any], new_results: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two chunk analysis results"""
    
    old_qa = old_results["quality_analysis"]
    new_qa = new_results["quality_analysis"]
    old_pi = old_results["processing_issues"]
    new_pi = new_results["processing_issues"]
    
    comparison = {
        "run_ids": {
            "old": old_results["analysis_metadata"]["indexing_run_id"],
            "new": new_results["analysis_metadata"]["indexing_run_id"]
        },
        "basic_metrics": {},
        "quality_improvements": {},
        "processing_improvements": {},
        "vlm_improvements": {},
        "overall_assessment": ""
    }
    
    # Basic metrics comparison
    comparison["basic_metrics"] = {
        "total_chunks": {
            "old": old_qa["total_chunks"],
            "new": new_qa["total_chunks"],
            "change": new_qa["total_chunks"] - old_qa["total_chunks"],
            "percent_change": ((new_qa["total_chunks"] - old_qa["total_chunks"]) / old_qa["total_chunks"]) * 100
        },
        "mean_chunk_size": {
            "old": round(old_qa["size_distribution"]["mean"], 1),
            "new": round(new_qa["size_distribution"]["mean"], 1),
            "change": round(new_qa["size_distribution"]["mean"] - old_qa["size_distribution"]["mean"], 1),
            "percent_change": ((new_qa["size_distribution"]["mean"] - old_qa["size_distribution"]["mean"]) / old_qa["size_distribution"]["mean"]) * 100
        },
        "median_chunk_size": {
            "old": old_qa["size_distribution"]["median"],
            "new": new_qa["size_distribution"]["median"],
            "change": new_qa["size_distribution"]["median"] - old_qa["size_distribution"]["median"],
            "percent_change": ((new_qa["size_distribution"]["median"] - old_qa["size_distribution"]["median"]) / old_qa["size_distribution"]["median"]) * 100
        }
    }
    
    # Quality improvements
    comparison["quality_improvements"] = {
        "tiny_chunks_under_50": {
            "old": old_qa["size_distribution"]["under_50_chars"],
            "new": new_qa["size_distribution"]["under_50_chars"],
            "improvement": old_qa["size_distribution"]["under_50_chars"] - new_qa["size_distribution"]["under_50_chars"],
            "percent_improvement": ((old_qa["size_distribution"]["under_50_chars"] - new_qa["size_distribution"]["under_50_chars"]) / old_qa["size_distribution"]["under_50_chars"]) * 100 if old_qa["size_distribution"]["under_50_chars"] > 0 else 0
        },
        "tiny_chunks_under_100": {
            "old": old_qa["size_distribution"]["under_100_chars"],
            "new": new_qa["size_distribution"]["under_100_chars"],
            "improvement": old_qa["size_distribution"]["under_100_chars"] - new_qa["size_distribution"]["under_100_chars"],
            "percent_improvement": ((old_qa["size_distribution"]["under_100_chars"] - new_qa["size_distribution"]["under_100_chars"]) / old_qa["size_distribution"]["under_100_chars"]) * 100
        },
        "duplicate_content_sets": {
            "old": len(old_qa["problematic_chunks"]["duplicate_content"]),
            "new": len(new_qa["problematic_chunks"]["duplicate_content"]),
            "change": len(new_qa["problematic_chunks"]["duplicate_content"]) - len(old_qa["problematic_chunks"]["duplicate_content"])
        },
        "fragmented_lists": {
            "old": len(old_qa["problematic_chunks"]["fragmented_lists"]),
            "new": len(new_qa["problematic_chunks"]["fragmented_lists"]),
            "improvement": len(old_qa["problematic_chunks"]["fragmented_lists"]) - len(new_qa["problematic_chunks"]["fragmented_lists"])
        }
    }
    
    # VLM improvements
    comparison["vlm_improvements"] = {
        "vlm_usage_percentage": {
            "old": round(old_qa["vlm_captioning_analysis"]["percentage_with_vlm"], 1),
            "new": round(new_qa["vlm_captioning_analysis"]["percentage_with_vlm"], 1),
            "improvement": round(new_qa["vlm_captioning_analysis"]["percentage_with_vlm"] - old_qa["vlm_captioning_analysis"]["percentage_with_vlm"], 1)
        },
        "chunks_with_vlm": {
            "old": old_qa["vlm_captioning_analysis"]["total_chunks_with_vlm"],
            "new": new_qa["vlm_captioning_analysis"]["total_chunks_with_vlm"],
            "change": new_qa["vlm_captioning_analysis"]["total_chunks_with_vlm"] - old_qa["vlm_captioning_analysis"]["total_chunks_with_vlm"]
        }
    }
    
    # Content type analysis
    old_categories = old_qa["content_type_analysis"]["category_distribution"]
    new_categories = new_qa["content_type_analysis"]["category_distribution"]
    
    comparison["content_type_changes"] = {
        "old_distribution": old_categories,
        "new_distribution": new_categories,
        "new_categories": [cat for cat in new_categories.keys() if cat not in old_categories.keys()]
    }
    
    # Generate overall assessment
    assessment_points = []
    
    # Chunk count reduction
    chunk_reduction = comparison["basic_metrics"]["total_chunks"]["percent_change"]
    if chunk_reduction < -50:
        assessment_points.append(f"🎯 EXCELLENT: Massive chunk reduction of {abs(chunk_reduction):.1f}% indicates much better content consolidation")
    elif chunk_reduction < -20:
        assessment_points.append(f"✅ GOOD: Significant chunk reduction of {abs(chunk_reduction):.1f}%")
    elif chunk_reduction > 20:
        assessment_points.append(f"⚠️ CONCERN: Chunk count increased by {chunk_reduction:.1f}%")
    
    # Chunk size improvement
    size_improvement = comparison["basic_metrics"]["mean_chunk_size"]["percent_change"]
    if size_improvement > 100:
        assessment_points.append(f"🎯 EXCELLENT: Mean chunk size increased by {size_improvement:.1f}% (much better consolidation)")
    elif size_improvement > 50:
        assessment_points.append(f"✅ GOOD: Mean chunk size increased by {size_improvement:.1f}%")
    elif size_improvement < -20:
        assessment_points.append(f"⚠️ CONCERN: Mean chunk size decreased by {abs(size_improvement):.1f}%")
    
    # Tiny chunks improvement
    tiny_improvement = comparison["quality_improvements"]["tiny_chunks_under_50"]["percent_improvement"]
    if tiny_improvement > 95:
        assessment_points.append(f"🎯 EXCELLENT: Nearly eliminated tiny chunks ({tiny_improvement:.1f}% reduction)")
    elif tiny_improvement > 50:
        assessment_points.append(f"✅ GOOD: Major reduction in tiny chunks ({tiny_improvement:.1f}%)")
    
    # Content type improvements
    if "MergedContent" in comparison["content_type_changes"]["new_categories"]:
        assessment_points.append("✅ GOOD: New 'MergedContent' category shows chunking consolidation is working")
    
    comparison["overall_assessment"] = assessment_points
    
    return comparison

def print_comparison_report(comparison: Dict[str, Any]):
    """Print formatted comparison report"""
    
    print("=" * 80)
    print("CHUNK QUALITY ANALYSIS COMPARISON")
    print("=" * 80)
    
    print(f"\n📊 COMPARING INDEXING RUNS:")
    print(f"  Old Run: {comparison['run_ids']['old']}")
    print(f"  New Run: {comparison['run_ids']['new']}")
    
    print(f"\n📈 BASIC METRICS COMPARISON:")
    bm = comparison["basic_metrics"]
    print(f"  Total Chunks:")
    print(f"    Old: {bm['total_chunks']['old']:,}")
    print(f"    New: {bm['total_chunks']['new']:,}")
    print(f"    Change: {bm['total_chunks']['change']:+,} ({bm['total_chunks']['percent_change']:+.1f}%)")
    
    print(f"  Mean Chunk Size:")
    print(f"    Old: {bm['mean_chunk_size']['old']:,.1f} chars")
    print(f"    New: {bm['mean_chunk_size']['new']:,.1f} chars")
    print(f"    Change: {bm['mean_chunk_size']['change']:+,.1f} chars ({bm['mean_chunk_size']['percent_change']:+.1f}%)")
    
    print(f"  Median Chunk Size:")
    print(f"    Old: {bm['median_chunk_size']['old']:,} chars")
    print(f"    New: {bm['median_chunk_size']['new']:,} chars")
    print(f"    Change: {bm['median_chunk_size']['change']:+,} chars ({bm['median_chunk_size']['percent_change']:+.1f}%)")
    
    print(f"\n🔧 QUALITY IMPROVEMENTS:")
    qi = comparison["quality_improvements"]
    print(f"  Chunks Under 50 Characters:")
    print(f"    Old: {qi['tiny_chunks_under_50']['old']}")
    print(f"    New: {qi['tiny_chunks_under_50']['new']}")
    if qi['tiny_chunks_under_50']['improvement'] > 0:
        print(f"    ✅ Improvement: -{qi['tiny_chunks_under_50']['improvement']} ({qi['tiny_chunks_under_50']['percent_improvement']:.1f}% reduction)")
    else:
        print(f"    ❌ No improvement: {qi['tiny_chunks_under_50']['improvement']}")
    
    print(f"  Chunks Under 100 Characters:")
    print(f"    Old: {qi['tiny_chunks_under_100']['old']}")
    print(f"    New: {qi['tiny_chunks_under_100']['new']}")
    if qi['tiny_chunks_under_100']['improvement'] > 0:
        print(f"    ✅ Improvement: -{qi['tiny_chunks_under_100']['improvement']} ({qi['tiny_chunks_under_100']['percent_improvement']:.1f}% reduction)")
    else:
        print(f"    ❌ Regression: {qi['tiny_chunks_under_100']['improvement']}")
    
    print(f"  Duplicate Content Sets:")
    print(f"    Old: {qi['duplicate_content_sets']['old']}")
    print(f"    New: {qi['duplicate_content_sets']['new']}")
    print(f"    Change: {qi['duplicate_content_sets']['change']:+}")
    
    print(f"  Fragmented List Items:")
    print(f"    Old: {qi['fragmented_lists']['old']}")
    print(f"    New: {qi['fragmented_lists']['new']}")
    if qi['fragmented_lists']['improvement'] > 0:
        print(f"    ✅ Improvement: -{qi['fragmented_lists']['improvement']}")
    else:
        print(f"    Change: {qi['fragmented_lists']['improvement']}")
    
    print(f"\n🤖 VLM IMPROVEMENTS:")
    vi = comparison["vlm_improvements"]
    print(f"  VLM Usage Percentage:")
    print(f"    Old: {vi['vlm_usage_percentage']['old']:.1f}%")
    print(f"    New: {vi['vlm_usage_percentage']['new']:.1f}%")
    print(f"    Change: {vi['vlm_usage_percentage']['improvement']:+.1f}%")
    
    print(f"\n📝 CONTENT TYPE CHANGES:")
    ct = comparison["content_type_changes"]
    print(f"  Old Categories: {list(ct['old_distribution'].keys())}")
    print(f"  New Categories: {list(ct['new_distribution'].keys())}")
    if ct['new_categories']:
        print(f"  ✅ New Categories Added: {ct['new_categories']}")
    
    print(f"\n🎯 OVERALL ASSESSMENT:")
    for point in comparison["overall_assessment"]:
        print(f"  {point}")
    
    print(f"\n" + "=" * 80)

def main():
    """Main comparison function"""
    
    # File paths
    old_file = "chunk_analysis_output/chunk_quality_analysis_20250818_090602.json"
    new_file = "chunk_analysis_output/chunk_quality_analysis_20250818_121415.json"
    
    # Load results
    print("Loading analysis results...")
    old_results = load_analysis_results(old_file)
    new_results = load_analysis_results(new_file)
    
    # Compare
    comparison = compare_chunk_analyses(old_results, new_results)
    
    # Print report
    print_comparison_report(comparison)
    
    # Save comparison
    output_file = f"chunk_analysis_output/comparison_report_{new_results['analysis_metadata']['analysis_timestamp'][:10].replace('-', '')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Comparison saved to: {output_file}")

if __name__ == "__main__":
    main()