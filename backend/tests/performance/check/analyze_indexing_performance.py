#!/usr/bin/env python3
"""Comprehensive indexing run performance analysis.

Analyzes velocity, captioning, chunk statistics, and content distribution
for a given indexing run. Outputs both JSON and CSV for tracking.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
from supabase import create_client, Client
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

# Performance tracking directory
PERF_DIR = Path("tests/performance/check")
PERF_DIR.mkdir(parents=True, exist_ok=True)


def analyze_velocity_metrics(run_id: str) -> Dict[str, Any]:
    """Analyze timing and velocity metrics for the indexing run."""
    
    # Get indexing run info
    indexing_run = supabase.table('indexing_runs').select('*').eq('id', run_id).execute()
    if not indexing_run.data:
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
    
    # Collect timing data
    step_totals = {
        'partition': 0,
        'metadata': 0,
        'enrichment': 0,
        'chunking': 0,
    }
    
    for doc in docs.data:
        step_results = doc.get('step_results', {})
        
        # Collect step timings
        for step_name in ['PartitionStep', 'MetadataStep', 'EnrichmentStep', 'ChunkingStep']:
            if step_name in step_results:
                duration = step_results[step_name].get('duration_seconds', 0)
                key = step_name.replace('Step', '').lower()
                step_totals[key] += duration
    
    # Get embedding time from indexing run
    embedding_time = 0
    if run.get('step_results') and 'embedding' in run['step_results']:
        embedding_time = run['step_results']['embedding'].get('duration_seconds', 0)
    
    # Calculate totals
    sequential_total = sum(step_totals.values()) + embedding_time
    parallelization_factor = sequential_total / actual_wall_time if actual_wall_time > 0 else 1
    
    # Get total pages from partition summary stats
    total_pages = 0
    for doc in docs.data:
        partition_stats = doc.get('step_results', {}).get('PartitionStep', {}).get('summary_stats', {})
        total_pages += partition_stats.get('pages_analyzed', 0)
    
    return {
        'wall_clock_seconds': round(actual_wall_time, 1),
        'wall_clock_minutes': round(actual_wall_time / 60, 1),
        'sequential_sum_seconds': round(sequential_total, 1),
        'parallelization_factor': round(parallelization_factor, 2),
        'step_timings': {k: round(v, 1) for k, v in step_totals.items()},
        'embedding_seconds': round(embedding_time, 1),
        'pages_per_second': round(total_pages / actual_wall_time, 2) if actual_wall_time > 0 and total_pages > 0 else 0,
        'docs_per_minute': round(len(docs.data) / (actual_wall_time / 60), 1) if actual_wall_time > 0 else 0,
        'total_documents': len(docs.data),
        'total_pages': total_pages
    }


def analyze_captioning_metrics(run_id: str) -> Dict[str, Any]:
    """Analyze captioning and VLM metrics for the indexing run."""
    
    # Get all documents
    doc_links = supabase.table('indexing_run_documents').select('document_id').eq('indexing_run_id', run_id).execute()
    doc_ids = [link['document_id'] for link in doc_links.data]
    docs = supabase.table('documents').select('*').in_('id', doc_ids).execute()
    
    # Initialize counters
    metrics = {
        'total_pages_extracted': 0,  # Full pages extracted as images
        'total_tables_detected': 0,
        'total_pages_captioned': 0,  # Full pages that got captions
        'total_tables_captioned': 0,
        'total_drawing_items': 0,
        'pages_with_drawings': 0,
        'pages_with_vector_drawings': 0,
        'total_vlm_time': 0,
        'docs_with_vlm': 0
    }
    
    for doc in docs.data:
        step_results = doc.get('step_results', {})
        
        # Get partition results for detection counts
        partition_results = step_results.get('PartitionStep', {})
        summary_stats = partition_results.get('summary_stats', {})
        data = partition_results.get('data', {})
        
        # Count extracted pages and detected tables
        metrics['total_pages_extracted'] += summary_stats.get('extracted_pages', 0)
        metrics['total_tables_detected'] += summary_stats.get('table_elements', 0)
        
        # Count drawing items from page analysis
        page_analysis = data.get('page_analysis', {})
        for page_data in page_analysis.values():
            drawing_items = page_data.get('drawing_items', page_data.get('drawing_item_count', 0))
            if drawing_items > 0:
                metrics['pages_with_drawings'] += 1
                metrics['total_drawing_items'] += drawing_items
            
            if page_data.get('has_vector_drawings', False):
                metrics['pages_with_vector_drawings'] += 1
        
        # Get enrichment results for caption counts
        enrichment_results = step_results.get('EnrichmentStep', {})
        enrichment_stats = enrichment_results.get('summary_stats', {})
        
        if enrichment_stats:
            # Full pages captioned (was images_processed)
            pages_captioned = enrichment_stats.get('images_processed', 0) or enrichment_stats.get('total_images', 0)
            tables_captioned = enrichment_stats.get('tables_processed', 0) or enrichment_stats.get('total_tables', 0)
            
            metrics['total_pages_captioned'] += pages_captioned
            metrics['total_tables_captioned'] += tables_captioned
            
            if pages_captioned > 0 or tables_captioned > 0:
                metrics['docs_with_vlm'] += 1
                metrics['total_vlm_time'] += enrichment_results.get('duration_seconds', 0)
    
    # Calculate rates
    total_vlm_items = metrics['total_pages_captioned'] + metrics['total_tables_captioned']
    metrics['avg_vlm_seconds_per_item'] = round(metrics['total_vlm_time'] / total_vlm_items, 2) if total_vlm_items > 0 else 0
    metrics['caption_rate'] = round((total_vlm_items / (metrics['total_pages_extracted'] + metrics['total_tables_detected'])) * 100, 1) if (metrics['total_pages_extracted'] + metrics['total_tables_detected']) > 0 else 0
    
    return metrics


def analyze_chunk_metrics(run_id: str) -> Dict[str, Any]:
    """Analyze chunk size distribution and statistics."""
    
    # Get all chunks for this indexing run
    chunks_response = supabase.table('document_chunks').select('content, metadata').eq('indexing_run_id', run_id).execute()
    chunks = chunks_response.data
    
    if not chunks:
        return {
            'total_chunks': 0,
            'avg_chunk_size': 0,
            'chunks_over_1200': 0,
            'chunks_under_50': 0,
            'longest_chunk_size': 0,
            'shortest_chunk_size': 0
        }
    
    # Calculate chunk sizes
    chunk_sizes = [len(chunk.get('content', '')) for chunk in chunks]
    
    # Calculate metrics
    metrics = {
        'total_chunks': len(chunks),
        'avg_chunk_size': round(sum(chunk_sizes) / len(chunk_sizes), 1),
        'chunks_over_1200': sum(1 for size in chunk_sizes if size > 1200),
        'chunks_under_50': sum(1 for size in chunk_sizes if size < 50),
        'longest_chunk_size': max(chunk_sizes),
        'shortest_chunk_size': min(chunk_sizes),
        'median_chunk_size': sorted(chunk_sizes)[len(chunk_sizes) // 2],
        'chunks_over_1200_pct': round((sum(1 for size in chunk_sizes if size > 1200) / len(chunks)) * 100, 1),
        'chunks_under_50_pct': round((sum(1 for size in chunk_sizes if size < 50) / len(chunks)) * 100, 1)
    }
    
    return metrics


def analyze_content_distribution(run_id: str) -> Dict[str, Any]:
    """Analyze content type distribution across all documents."""
    
    # Get all documents
    doc_links = supabase.table('indexing_run_documents').select('document_id').eq('indexing_run_id', run_id).execute()
    doc_ids = [link['document_id'] for link in doc_links.data]
    docs = supabase.table('documents').select('*').in_('id', doc_ids).execute()
    
    # Initialize counters
    content_types = {
        'text_elements': 0,
        'list_elements': 0,
        'table_elements': 0,
        'image_elements': 0,
        'title_elements': 0,
        'narrative_text': 0,
        'form_elements': 0
    }
    
    for doc in docs.data:
        step_results = doc.get('step_results', {})
        partition_results = step_results.get('PartitionStep', {})
        summary_stats = partition_results.get('summary_stats', {})
        data = partition_results.get('data', {})
        
        # Get element counts from summary stats
        content_types['text_elements'] += summary_stats.get('text_elements', 0)
        content_types['table_elements'] += summary_stats.get('table_elements', 0)
        content_types['image_elements'] += summary_stats.get('original_image_count', 0)
        
        # Get additional element types from elements list if available
        elements = data.get('elements', [])
        for element in elements:
            elem_type = element.get('type', '').lower()
            if 'list' in elem_type:
                content_types['list_elements'] += 1
            elif 'title' in elem_type:
                content_types['title_elements'] += 1
            elif 'narrative' in elem_type:
                content_types['narrative_text'] += 1
            elif 'form' in elem_type:
                content_types['form_elements'] += 1
    
    # Calculate total and percentages
    total_elements = sum(content_types.values())
    
    distribution = {
        'total_elements': total_elements,
        'text_elements': content_types['text_elements'],
        'list_elements': content_types['list_elements'],
        'table_elements': content_types['table_elements'],
        'image_elements': content_types['image_elements'],
        'text_pct': round((content_types['text_elements'] / total_elements) * 100, 1) if total_elements > 0 else 0,
        'list_pct': round((content_types['list_elements'] / total_elements) * 100, 1) if total_elements > 0 else 0,
        'table_pct': round((content_types['table_elements'] / total_elements) * 100, 1) if total_elements > 0 else 0,
        'image_pct': round((content_types['image_elements'] / total_elements) * 100, 1) if total_elements > 0 else 0
    }
    
    return distribution


def analyze_and_save_performance(run_id: str, description: str = None) -> Dict[str, Any]:
    """Main function to analyze all performance metrics and save results."""
    
    print(f"\nAnalyzing indexing run: {run_id[:8]}...")
    
    # Collect all metrics
    velocity = analyze_velocity_metrics(run_id)
    if not velocity:
        print("No indexing run found")
        return {}
    
    captioning = analyze_captioning_metrics(run_id)
    chunks = analyze_chunk_metrics(run_id)
    content = analyze_content_distribution(run_id)
    
    # Create comprehensive results
    results = {
        'metadata': {
            'indexing_run_id': run_id,
            'analysis_timestamp': datetime.now().isoformat(),
            'description': description or 'Performance analysis',
            'version': '2.0'
        },
        'velocity_metrics': velocity,
        'captioning_metrics': captioning,
        'chunk_metrics': chunks,
        'content_distribution': content
    }
    
    return results


def save_results(results: Dict[str, Any], run_id: str) -> Tuple[Path, Path]:
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
            # Header line
            f.write("timestamp,run_id,description,")
            f.write("docs,pages,wall_min,parallel_factor,")
            f.write("pages_extracted,pages_caption,tables_detect,tables_caption,drawing_items,caption_rate,")
            f.write("chunks,avg_chunk,over_1200,under_50,longest,")
            f.write("text_elem,list_elem,table_elem,img_elem\n")
    
    # Append results
    v = results['velocity_metrics']
    cap = results['captioning_metrics']
    ch = results['chunk_metrics']
    cont = results['content_distribution']
    
    with open(csv_file, 'a') as f:
        f.write(f"{results['metadata']['analysis_timestamp']},")
        f.write(f"{results['metadata']['indexing_run_id'][:8]},")
        f.write(f'"{results["metadata"]["description"]}",')
        f.write(f"{v['total_documents']},{v['total_pages']},{v['wall_clock_minutes']},{v['parallelization_factor']},")
        f.write(f"{cap['total_pages_extracted']},{cap['total_pages_captioned']},")
        f.write(f"{cap['total_tables_detected']},{cap['total_tables_captioned']},")
        f.write(f"{cap['total_drawing_items']},{cap['caption_rate']},")
        f.write(f"{ch['total_chunks']},{ch['avg_chunk_size']},{ch['chunks_over_1200']},{ch['chunks_under_50']},{ch['longest_chunk_size']},")
        f.write(f"{cont['text_elements']},{cont['list_elements']},{cont['table_elements']},{cont['image_elements']}\n")
    
    return json_file, csv_file


def print_results(results: Dict[str, Any]):
    """Print formatted results to console."""
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE INDEXING RUN PERFORMANCE ANALYSIS")
    print("=" * 80)
    
    print(f"\n📊 RUN: {results['metadata']['indexing_run_id'][:8]}...")
    print(f"Description: {results['metadata']['description']}")
    print(f"Analyzed: {results['metadata']['analysis_timestamp']}")
    
    # Velocity Metrics
    v = results['velocity_metrics']
    print(f"\n⏱️  VELOCITY METRICS")
    print("-" * 50)
    print(f"Wall Clock Time:      {v['wall_clock_minutes']:.1f} minutes")
    print(f"Parallelization:      {v['parallelization_factor']}x")
    print(f"Pages/second:         {v['pages_per_second']}")
    print(f"Docs/minute:          {v['docs_per_minute']}")
    print(f"Total Documents:      {v['total_documents']}")
    print(f"Total Pages:          {v['total_pages']}")
    
    # Captioning Metrics
    cap = results['captioning_metrics']
    print(f"\n📸 CAPTIONING & VLM METRICS")
    print("-" * 50)
    print(f"Full Pages Extracted: {cap['total_pages_extracted']}")
    print(f"Full Pages Captioned: {cap['total_pages_captioned']}")
    print(f"Tables Detected:      {cap['total_tables_detected']}")
    print(f"Tables Captioned:     {cap['total_tables_captioned']}")
    print(f"Drawing Items:        {cap['total_drawing_items']:,}")
    print(f"Pages w/ Drawings:    {cap['pages_with_drawings']}")
    print(f"Vector Drawing Pages: {cap['pages_with_vector_drawings']}")
    print(f"Caption Rate:         {cap['caption_rate']}%")
    print(f"Avg VLM Time/Item:    {cap['avg_vlm_seconds_per_item']}s")
    
    # Chunk Metrics
    ch = results['chunk_metrics']
    print(f"\n📝 CHUNK ANALYSIS")
    print("-" * 50)
    print(f"Total Chunks:         {ch['total_chunks']}")
    print(f"Average Size:         {ch['avg_chunk_size']} chars")
    if ch['total_chunks'] > 0:
        print(f"Median Size:          {ch['median_chunk_size']} chars")
        print(f"Chunks > 1200:        {ch['chunks_over_1200']} ({ch['chunks_over_1200_pct']}%)")
        print(f"Chunks < 50:          {ch['chunks_under_50']} ({ch['chunks_under_50_pct']}%)")
        print(f"Longest Chunk:        {ch['longest_chunk_size']} chars")
        print(f"Shortest Chunk:       {ch['shortest_chunk_size']} chars")
    
    # Content Distribution
    cont = results['content_distribution']
    print(f"\n📊 CONTENT TYPE DISTRIBUTION")
    print("-" * 50)
    print(f"Total Elements:       {cont['total_elements']}")
    print(f"Text Elements:        {cont['text_elements']} ({cont['text_pct']}%)")
    print(f"List Elements:        {cont['list_elements']} ({cont['list_pct']}%)")
    print(f"Table Elements:       {cont['table_elements']} ({cont['table_pct']}%)")
    print(f"Image Elements:       {cont['image_elements']} ({cont['image_pct']}%)")
    
    # Warnings/Alerts
    print(f"\n⚠️  ALERTS")
    print("-" * 50)
    alerts = []
    
    if ch['chunks_over_1200'] > ch['total_chunks'] * 0.1:
        alerts.append(f"High number of oversized chunks: {ch['chunks_over_1200_pct']}% > 1200 chars")
    
    if ch['chunks_under_50'] > ch['total_chunks'] * 0.05:
        alerts.append(f"High number of tiny chunks: {ch['chunks_under_50_pct']}% < 50 chars")
    
    if cap['caption_rate'] < 50:
        alerts.append(f"Low caption rate: {cap['caption_rate']}% of detected items")
    
    if v['parallelization_factor'] < 2:
        alerts.append(f"Low parallelization: {v['parallelization_factor']}x")
    
    if alerts:
        for alert in alerts:
            print(f"  • {alert}")
    else:
        print("  ✅ All metrics within expected ranges")


if __name__ == "__main__":
    import sys
    
    # Get run ID and optional description
    if len(sys.argv) < 2:
        print("Usage: python analyze_indexing_performance.py <indexing_run_id> [description]")
        print("Example: python analyze_indexing_performance.py abc123def \"Added new VLM model\"")
        sys.exit(1)
    
    run_id = sys.argv[1]
    description = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Performance check"
    
    # Analyze and save
    results = analyze_and_save_performance(run_id, description)
    
    if results:
        json_file, csv_file = save_results(results, run_id)
        print_results(results)
        
        print(f"\n📁 RESULTS SAVED")
        print("-" * 50)
        print(f"JSON: {json_file}")
        print(f"CSV:  {csv_file}")
        
        # Show recent history
        print(f"\n📊 RECENT PERFORMANCE HISTORY (last 5)")
        print("-" * 50)
        if csv_file.exists():
            with open(csv_file, 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    # Print shortened header for readability
                    print("Date        | Run      | Docs | Pages | Time  | Chunks | Avg Size | Caption% | Drawings")
                    print("-" * 85)
                    # Print last 5 runs (skip header)
                    for line in lines[-5:] if len(lines) > 5 else lines[1:]:
                        parts = line.strip().split(',')
                        if len(parts) >= 13:  # Ensure we have enough fields
                            # Extract key metrics
                            timestamp = parts[0].split('T')[0]  # Just date
                            run = parts[1]
                            docs = parts[3]
                            pages = parts[4]
                            time_min = parts[5]
                            chunks = parts[13]
                            avg_chunk = parts[14]
                            caption_rate = parts[12]
                            drawing_items = parts[11]
                            print(f"{timestamp} | {run} | {docs:>4} | {pages:>5} | {time_min:>5} | {chunks:>6} | {avg_chunk:>8} | {caption_rate:>7} | {drawing_items:>8}")
    else:
        print("Failed to analyze run")