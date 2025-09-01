#!/usr/bin/env python3
"""Analyze timing and track performance improvements over time."""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

# Performance tracking directory
PERF_DIR = Path("tests/performance")
PERF_DIR.mkdir(parents=True, exist_ok=True)

def analyze_and_save_timings(run_id: str, description: str = None) -> Dict[str, Any]:
    """Analyze timing data and save results for tracking."""
    
    # Get indexing run info
    indexing_run = supabase.table('indexing_runs').select('*').eq('id', run_id).execute()
    if not indexing_run.data:
        print("No indexing run found")
        return {}
    
    run = indexing_run.data[0]
    start = datetime.fromisoformat(run['started_at'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(run['completed_at'].replace('Z', '+00:00'))
    actual_wall_time = (end - start).total_seconds()
    
    # Get all documents via junction table
    doc_links = supabase.table('indexing_run_documents').select('document_id').eq('indexing_run_id', run_id).execute()
    doc_ids = [link['document_id'] for link in doc_links.data]
    
    # Get all documents with their step results
    docs = supabase.table('documents').select('*').in_('id', doc_ids).execute()
    
    # Collect timing and VLM data
    step_totals = {
        'partition': 0,
        'metadata': 0,
        'enrichment': 0,
        'chunking': 0,
    }
    
    vlm_stats = {
        'total_images': 0,
        'total_tables': 0,
        'total_vlm_time': 0,
        'docs_with_vlm': 0
    }
    
    doc_details = []
    
    for doc in docs.data:
        step_results = doc.get('step_results', {})
        doc_total = 0
        
        # Collect step timings (handle both naming conventions)
        for step_name in ['PartitionStep', 'MetadataStep', 'EnrichmentStep', 'ChunkingStep']:
            if step_name in step_results:
                duration = step_results[step_name].get('duration_seconds', 0)
                key = step_name.replace('Step', '').lower()
                step_totals[key] += duration
                doc_total += duration
        
        # Extract VLM/Enrichment details
        enrichment_data = step_results.get('EnrichmentStep', {})
        if enrichment_data:
            summary = enrichment_data.get('summary_stats', {})
            images = summary.get('images_processed', 0) or summary.get('total_images', 0)
            tables = summary.get('tables_processed', 0) or summary.get('total_tables', 0)
            
            if images > 0 or tables > 0:
                vlm_stats['total_images'] += images
                vlm_stats['total_tables'] += tables
                vlm_stats['total_vlm_time'] += enrichment_data.get('duration_seconds', 0)
                vlm_stats['docs_with_vlm'] += 1
        
        doc_details.append({
            'filename': doc['filename'],
            'pages': doc.get('page_count'),
            'total_seconds': doc_total
        })
    
    # Get embedding time from indexing run
    embedding_time = 0
    if run.get('step_results') and 'embedding' in run['step_results']:
        embedding_time = run['step_results']['embedding'].get('duration_seconds', 0)
    
    # Calculate totals
    sequential_total = sum(step_totals.values()) + embedding_time
    
    # Get wiki generation
    wiki_duration = None
    wiki = supabase.table('wiki_generation_runs').select('*').eq('indexing_run_id', run_id).execute()
    if wiki.data:
        w = wiki.data[0]
        if w.get('started_at') and w.get('completed_at'):
            wiki_start = datetime.fromisoformat(w['started_at'].replace('Z', '+00:00'))
            wiki_end = datetime.fromisoformat(w['completed_at'].replace('Z', '+00:00'))
            wiki_duration = (wiki_end - wiki_start).total_seconds()
    
    # Calculate metrics
    total_vlm_items = vlm_stats['total_images'] + vlm_stats['total_tables']
    avg_vlm_per_item = vlm_stats['total_vlm_time'] / total_vlm_items if total_vlm_items > 0 else 0
    parallelization_factor = sequential_total / actual_wall_time if actual_wall_time > 0 else 1
    
    # Create results object
    results = {
        'metadata': {
            'indexing_run_id': run_id,
            'analysis_timestamp': datetime.now().isoformat(),
            'description': description or 'Manual analysis',
            'version': '1.0'  # Track analysis version for schema changes
        },
        'summary': {
            'total_documents': len(docs.data),
            'total_pages': sum(d.get('page_count', 0) for d in docs.data if d.get('page_count')),
            'wall_clock_seconds': round(actual_wall_time, 1),
            'wall_clock_minutes': round(actual_wall_time / 60, 1),
            'sequential_sum_seconds': round(sequential_total, 1),
            'parallelization_factor': round(parallelization_factor, 2),
            'parallelization_savings_seconds': round(sequential_total - actual_wall_time, 1)
        },
        'step_timings': {
            'partition_seconds': round(step_totals['partition'], 1),
            'metadata_seconds': round(step_totals['metadata'], 1),
            'enrichment_seconds': round(step_totals['enrichment'], 1),
            'chunking_seconds': round(step_totals['chunking'], 1),
            'embedding_seconds': round(embedding_time, 1)
        },
        'step_percentages': {
            'partition_pct': round(step_totals['partition'] / sequential_total * 100, 1) if sequential_total > 0 else 0,
            'metadata_pct': round(step_totals['metadata'] / sequential_total * 100, 1) if sequential_total > 0 else 0,
            'enrichment_pct': round(step_totals['enrichment'] / sequential_total * 100, 1) if sequential_total > 0 else 0,
            'chunking_pct': round(step_totals['chunking'] / sequential_total * 100, 1) if sequential_total > 0 else 0,
            'embedding_pct': round(embedding_time / sequential_total * 100, 1) if sequential_total > 0 else 0
        },
        'vlm_metrics': {
            'total_images': vlm_stats['total_images'],
            'total_tables': vlm_stats['total_tables'],
            'total_items': total_vlm_items,
            'total_vlm_seconds': round(vlm_stats['total_vlm_time'], 1),
            'avg_seconds_per_item': round(avg_vlm_per_item, 1),
            'items_per_second': round(1 / avg_vlm_per_item, 2) if avg_vlm_per_item > 0 else 0,
            'docs_with_vlm': vlm_stats['docs_with_vlm']
        },
        'wiki_generation': {
            'duration_seconds': round(wiki_duration, 1) if wiki_duration else None,
            'duration_minutes': round(wiki_duration / 60, 1) if wiki_duration else None
        },
        'performance_rates': {
            'pages_per_second': round(sum(d.get('page_count', 0) for d in docs.data if d.get('page_count')) / actual_wall_time, 2) if actual_wall_time > 0 and any(d.get('page_count') for d in docs.data) else 0,
            'docs_per_minute': round(len(docs.data) / (actual_wall_time / 60), 1) if actual_wall_time > 0 else 0,
            'avg_seconds_per_doc': round(actual_wall_time / len(docs.data), 1) if len(docs.data) > 0 else 0
        },
        'top_slowest_docs': sorted(doc_details, key=lambda x: x['total_seconds'], reverse=True)[:5]
    }
    
    return results

def save_results(results: Dict[str, Any], run_id: str):
    """Save results to both JSON and CSV for tracking."""
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save detailed JSON
    json_file = PERF_DIR / f"perf_{timestamp}_{run_id[:8]}.json"
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Append to master CSV for easy tracking
    csv_file = PERF_DIR / "performance_history.csv"
    
    # Create CSV header if file doesn't exist
    if not csv_file.exists():
        with open(csv_file, 'w') as f:
            f.write("timestamp,run_id,description,docs,wall_time_min,sequential_min,parallelization,")
            f.write("partition_pct,enrichment_pct,embedding_pct,")
            f.write("vlm_items,vlm_sec_per_item,pages_per_sec\n")
    
    # Append results
    with open(csv_file, 'a') as f:
        f.write(f"{results['metadata']['analysis_timestamp']},")
        f.write(f"{results['metadata']['indexing_run_id'][:8]},")
        f.write(f"\"{results['metadata']['description']}\",")
        f.write(f"{results['summary']['total_documents']},")
        f.write(f"{results['summary']['wall_clock_minutes']},")
        f.write(f"{results['summary']['sequential_sum_seconds']/60:.1f},")
        f.write(f"{results['summary']['parallelization_factor']},")
        f.write(f"{results['step_percentages']['partition_pct']},")
        f.write(f"{results['step_percentages']['enrichment_pct']},")
        f.write(f"{results['step_percentages']['embedding_pct']},")
        f.write(f"{results['vlm_metrics']['total_items']},")
        f.write(f"{results['vlm_metrics']['avg_seconds_per_item']},")
        f.write(f"{results['performance_rates']['pages_per_second']}\n")
    
    return json_file, csv_file

def print_results(results: Dict[str, Any]):
    """Print formatted results to console."""
    
    print("\n" + "=" * 70)
    print("PERFORMANCE ANALYSIS RESULTS")
    print("=" * 70)
    
    print(f"\n📊 RUN: {results['metadata']['indexing_run_id'][:8]}...")
    print(f"Description: {results['metadata']['description']}")
    print(f"Analyzed: {results['metadata']['analysis_timestamp']}")
    
    print(f"\n⏱️  TIMING SUMMARY")
    print("-" * 50)
    print(f"Wall Clock Time:      {results['summary']['wall_clock_minutes']:.1f} minutes")
    print(f"Sequential Sum:       {results['summary']['sequential_sum_seconds']/60:.1f} minutes")
    print(f"Parallelization:      {results['summary']['parallelization_factor']}x")
    print(f"Time Saved:           {results['summary']['parallelization_savings_seconds']/60:.1f} minutes")
    
    print(f"\n📸 VLM METRICS")
    print("-" * 50)
    print(f"Total Items:          {results['vlm_metrics']['total_items']} ({results['vlm_metrics']['total_images']} images, {results['vlm_metrics']['total_tables']} tables)")
    print(f"Avg Time per Item:    {results['vlm_metrics']['avg_seconds_per_item']} seconds")
    print(f"Processing Rate:      {results['vlm_metrics']['items_per_second']} items/second")
    
    print(f"\n📈 STEP BREAKDOWN")
    print("-" * 50)
    for step in ['partition', 'metadata', 'enrichment', 'chunking', 'embedding']:
        pct = results['step_percentages'][f'{step}_pct']
        seconds = results['step_timings'][f'{step}_seconds']
        marker = " ⚠️ BOTTLENECK" if pct > 40 else ""
        print(f"{step.capitalize():12s}: {seconds:7.1f}s ({pct:5.1f}%){marker}")
    
    print(f"\n🚀 PERFORMANCE RATES")
    print("-" * 50)
    print(f"Pages/second:         {results['performance_rates']['pages_per_second']}")
    print(f"Docs/minute:          {results['performance_rates']['docs_per_minute']}")
    print(f"Avg sec/doc:          {results['performance_rates']['avg_seconds_per_doc']}")

def compare_runs(run_ids: list):
    """Compare performance across multiple runs."""
    
    comparisons = []
    for run_id in run_ids:
        # Find latest analysis for this run
        pattern = f"*_{run_id[:8]}.json"
        files = list(PERF_DIR.glob(pattern))
        if files:
            latest = max(files, key=lambda p: p.stat().st_mtime)
            with open(latest, 'r') as f:
                comparisons.append(json.load(f))
    
    if len(comparisons) >= 2:
        print("\n" + "=" * 70)
        print("PERFORMANCE COMPARISON")
        print("=" * 70)
        
        first = comparisons[0]
        last = comparisons[-1]
        
        wall_time_change = last['summary']['wall_clock_minutes'] - first['summary']['wall_clock_minutes']
        wall_time_pct = (wall_time_change / first['summary']['wall_clock_minutes'] * 100)
        
        print(f"\nWall Time: {first['summary']['wall_clock_minutes']:.1f} min → {last['summary']['wall_clock_minutes']:.1f} min")
        print(f"Change: {wall_time_change:+.1f} min ({wall_time_pct:+.1f}%)")
        
        if 'vlm_metrics' in first and 'vlm_metrics' in last:
            vlm_change = last['vlm_metrics']['avg_seconds_per_item'] - first['vlm_metrics']['avg_seconds_per_item']
            print(f"\nVLM per item: {first['vlm_metrics']['avg_seconds_per_item']:.1f}s → {last['vlm_metrics']['avg_seconds_per_item']:.1f}s")
            print(f"Change: {vlm_change:+.1f}s")

if __name__ == "__main__":
    import sys
    
    # Get run ID and optional description
    run_id = sys.argv[1] if len(sys.argv) > 1 else "ca079abb-b746-45fb-b448-0c4f5f185f8c"
    description = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Baseline performance"
    
    # Analyze and save
    results = analyze_and_save_timings(run_id, description)
    
    if results:
        json_file, csv_file = save_results(results, run_id)
        print_results(results)
        
        print(f"\n📁 RESULTS SAVED")
        print("-" * 50)
        print(f"JSON: {json_file}")
        print(f"CSV:  {csv_file}")
        
        # Show recent history
        print(f"\n📊 RECENT PERFORMANCE HISTORY")
        print("-" * 50)
        if csv_file.exists():
            with open(csv_file, 'r') as f:
                lines = f.readlines()
                print(lines[0].strip())  # Header
                for line in lines[-5:]:  # Last 5 runs
                    print(line.strip())
    else:
        print("Failed to analyze run")