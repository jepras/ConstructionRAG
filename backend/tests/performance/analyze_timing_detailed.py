#!/usr/bin/env python3
"""Detailed timing analysis including VLM metrics and parallelization effects."""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

def analyze_detailed_timings(run_id: str):
    """Analyze timing data with VLM and parallelization details."""
    
    # Get indexing run info
    indexing_run = supabase.table('indexing_runs').select('*').eq('id', run_id).execute()
    if not indexing_run.data:
        print("No indexing run found")
        return
    
    run = indexing_run.data[0]
    start = datetime.fromisoformat(run['started_at'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(run['completed_at'].replace('Z', '+00:00'))
    actual_wall_time = (end - start).total_seconds()
    
    print("=" * 70)
    print("DETAILED TIMING ANALYSIS WITH VLM METRICS")
    print("=" * 70)
    print("\n📊 INDEXING RUN OVERVIEW")
    print(f"Run ID: {run_id}")
    print(f"Status: {run['status']}")
    print(f"Started: {run['started_at']}")
    print(f"Completed: {run['completed_at']}")
    
    # Get all documents via junction table
    doc_links = supabase.table('indexing_run_documents').select('document_id').eq('indexing_run_id', run_id).execute()
    doc_ids = [link['document_id'] for link in doc_links.data]
    
    # Get all documents with their step results
    docs = supabase.table('documents').select('*').in_('id', doc_ids).execute()
    
    print(f"\n📄 DOCUMENTS: {len(docs.data)} files")
    
    # Collect timing and VLM data
    step_totals = {
        'PartitionStep': 0,
        'MetadataStep': 0,
        'EnrichmentStep': 0,
        'ChunkingStep': 0,
    }
    
    vlm_stats = {
        'total_images': 0,
        'total_tables': 0,
        'total_vlm_time': 0,
        'docs_with_vlm': 0
    }
    
    doc_timings = []
    
    for doc in docs.data:
        step_results = doc.get('step_results', {})
        doc_total = 0
        doc_steps = {}
        
        # Collect step timings
        for step_name in step_totals.keys():
            if step_name in step_results:
                duration = step_results[step_name].get('duration_seconds', 0)
                step_totals[step_name] += duration
                doc_steps[step_name] = duration
                doc_total += duration
        
        # Extract VLM/Enrichment details
        enrichment_data = step_results.get('EnrichmentStep', {})
        if enrichment_data:
            # Look for summary stats
            summary = enrichment_data.get('summary_stats', {})
            images = summary.get('images_processed', 0) or summary.get('total_images', 0)
            tables = summary.get('tables_processed', 0) or summary.get('total_tables', 0)
            
            # Also check sample_outputs for more details
            samples = enrichment_data.get('sample_outputs', {})
            if not images and not tables and samples:
                # Try to count from sample outputs
                if 'captions' in samples:
                    captions = samples.get('captions', [])
                    if isinstance(captions, list):
                        images = len(captions)
            
            if images > 0 or tables > 0:
                vlm_stats['total_images'] += images
                vlm_stats['total_tables'] += tables
                vlm_stats['total_vlm_time'] += enrichment_data.get('duration_seconds', 0)
                vlm_stats['docs_with_vlm'] += 1
            
            doc_steps['vlm_images'] = images
            doc_steps['vlm_tables'] = tables
        
        doc_timings.append({
            'filename': doc['filename'],
            'pages': doc.get('page_count', 0),
            'total': doc_total,
            'steps': doc_steps
        })
    
    # Sort by total time
    doc_timings.sort(key=lambda x: x['total'], reverse=True)
    
    # Get embedding time from indexing run
    embedding_time = 0
    if run.get('step_results') and 'embedding' in run['step_results']:
        embedding_time = run['step_results']['embedding'].get('duration_seconds', 0)
    
    # Calculate totals
    sequential_total = sum(step_totals.values()) + embedding_time
    
    print("\n⏱️  TIMING COMPARISON")
    print("-" * 50)
    print(f"Actual Wall Clock Time:     {actual_wall_time:8.1f} sec ({actual_wall_time/60:5.1f} min)")
    print(f"Sum of All Step Times:      {sequential_total:8.1f} sec ({sequential_total/60:5.1f} min)")
    print(f"Parallelization Savings:    {sequential_total - actual_wall_time:8.1f} sec")
    print(f"Parallelization Factor:     {sequential_total/actual_wall_time if actual_wall_time > 0 else 0:8.2f}x")
    
    print("\n📸 VLM (ENRICHMENT) ANALYSIS")
    print("-" * 50)
    print(f"Documents with VLM:         {vlm_stats['docs_with_vlm']}")
    print(f"Total Images Processed:     {vlm_stats['total_images']}")
    print(f"Total Tables Processed:     {vlm_stats['total_tables']}")
    print(f"Total VLM Processing Time:  {vlm_stats['total_vlm_time']:.1f} sec")
    
    total_vlm_items = vlm_stats['total_images'] + vlm_stats['total_tables']
    if total_vlm_items > 0:
        avg_per_item = vlm_stats['total_vlm_time'] / total_vlm_items
        print(f"Average Time per Item:      {avg_per_item:.1f} sec/item")
        print(f"VLM Processing Rate:        {total_vlm_items/vlm_stats['total_vlm_time'] if vlm_stats['total_vlm_time'] > 0 else 0:.2f} items/sec")
    
    print("\n📊 STEP TIMING BREAKDOWN")
    print("-" * 50)
    for step, time in step_totals.items():
        if time > 0:
            pct = (time / sequential_total * 100) if sequential_total > 0 else 0
            step_display = step.replace('Step', '')
            print(f"{step_display:12s}: {time:8.1f} sec ({pct:5.1f}%)")
    
    print(f"{'Embedding':12s}: {embedding_time:8.1f} sec ({(embedding_time/sequential_total*100) if sequential_total > 0 else 0:5.1f}%) [Run-level]")
    print("-" * 50)
    print(f"{'TOTAL':12s}: {sequential_total:8.1f} sec ({sequential_total/60:5.1f} min)")
    
    print("\n📈 TOP 5 SLOWEST DOCUMENTS (WITH VLM DETAILS)")
    print("-" * 50)
    for i, doc in enumerate(doc_timings[:5], 1):
        print(f"\n{i}. {doc['filename'][:40]}")
        print(f"   Total: {doc['total']:.1f} sec, Pages: {doc['pages'] or 'N/A'}")
        
        # Show VLM details if present
        if 'vlm_images' in doc['steps'] or 'vlm_tables' in doc['steps']:
            images = doc['steps'].get('vlm_images', 0)
            tables = doc['steps'].get('vlm_tables', 0)
            enrichment_time = doc['steps'].get('EnrichmentStep', 0)
            
            if images > 0 or tables > 0:
                print(f"   VLM: {images} images, {tables} tables → {enrichment_time:.1f} sec")
                total_items = images + tables
                if total_items > 0 and enrichment_time > 0:
                    print(f"        ({enrichment_time/total_items:.1f} sec per item)")
        
        # Show step breakdown
        for step in ['PartitionStep', 'MetadataStep', 'EnrichmentStep', 'ChunkingStep']:
            if step in doc['steps'] and doc['steps'][step] > 0:
                print(f"   - {step.replace('Step', ''):12s}: {doc['steps'][step]:6.1f} sec")
    
    # Get wiki generation
    wiki = supabase.table('wiki_generation_runs').select('*').eq('indexing_run_id', run_id).execute()
    if wiki.data:
        w = wiki.data[0]
        if w.get('started_at') and w.get('completed_at'):
            wiki_start = datetime.fromisoformat(w['started_at'].replace('Z', '+00:00'))
            wiki_end = datetime.fromisoformat(w['completed_at'].replace('Z', '+00:00'))
            wiki_duration = (wiki_end - wiki_start).total_seconds()
            
            print("\n📖 WIKI GENERATION")
            print("-" * 50)
            print(f"Duration: {wiki_duration:.1f} seconds ({wiki_duration/60:.1f} minutes)")
    
    print("\n💡 PERFORMANCE INSIGHTS")
    print("=" * 70)
    
    # Parallelization insights
    if sequential_total > actual_wall_time:
        print(f"✅ Parallelization is working! Saved {(sequential_total - actual_wall_time)/60:.1f} minutes")
        print(f"   Running at {sequential_total/actual_wall_time:.2f}x speed vs sequential")
    else:
        print("⚠️  No parallelization detected or overhead exceeds savings")
    
    # VLM insights
    if vlm_stats['total_vlm_time'] > 0:
        vlm_pct = (vlm_stats['total_vlm_time'] / sequential_total * 100)
        print(f"\n• VLM/Enrichment takes {vlm_pct:.1f}% of processing time")
        if vlm_pct > 50:
            print("  ⚠️  VLM is the major bottleneck!")
            if total_vlm_items > 0:
                print(f"  Each image/table takes ~{vlm_stats['total_vlm_time']/total_vlm_items:.1f} seconds")
                print("  Consider: Batch processing, faster models, or selective enrichment")
    
    # Overall performance
    total_pages = sum(doc['pages'] or 0 for doc in doc_timings)
    if total_pages > 0 and actual_wall_time > 0:
        pages_per_sec = total_pages / actual_wall_time
        print(f"\n• Overall processing rate: {pages_per_sec:.2f} pages/second (wall clock)")
        print(f"• Average per document: {actual_wall_time/len(doc_timings):.1f} seconds (wall clock)")

if __name__ == "__main__":
    run_id = "ca079abb-b746-45fb-b448-0c4f5f185f8c"
    analyze_detailed_timings(run_id)