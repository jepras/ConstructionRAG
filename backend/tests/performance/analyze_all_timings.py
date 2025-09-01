#!/usr/bin/env python3
"""Analyze all timing data for the indexing run."""

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

def analyze_timings(run_id: str):
    """Analyze all timing data."""
    
    # Get indexing run info
    indexing_run = supabase.table('indexing_runs').select('*').eq('id', run_id).execute()
    if not indexing_run.data:
        print("No indexing run found")
        return
    
    run = indexing_run.data[0]
    start = datetime.fromisoformat(run['started_at'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(run['completed_at'].replace('Z', '+00:00'))
    total_duration = (end - start).total_seconds()
    
    print("=" * 60)
    print("TIMING ANALYSIS")
    print("=" * 60)
    print(f"\n📊 INDEXING RUN OVERVIEW")
    print(f"Duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
    
    # Get all documents via junction table
    doc_links = supabase.table('indexing_run_documents').select('document_id').eq('indexing_run_id', run_id).execute()
    doc_ids = [link['document_id'] for link in doc_links.data]
    
    # Get all documents with their step results
    docs = supabase.table('documents').select('*').in_('id', doc_ids).execute()
    
    print(f"\n📄 DOCUMENTS: {len(docs.data)} files")
    
    # Collect timing data
    step_totals = {
        'PartitionStep': 0,
        'MetadataStep': 0,
        'EnrichmentStep': 0,
        'ChunkingStep': 0,
        'EmbeddingStep': 0  # Check if this exists
    }
    
    doc_timings = []
    
    for doc in docs.data:
        step_results = doc.get('step_results', {})
        doc_total = 0
        doc_steps = {}
        
        for step_name in step_totals.keys():
            if step_name in step_results:
                duration = step_results[step_name].get('duration_seconds', 0)
                step_totals[step_name] += duration
                doc_steps[step_name] = duration
                doc_total += duration
        
        doc_timings.append({
            'filename': doc['filename'],
            'pages': doc.get('page_count', 0),
            'total': doc_total,
            'steps': doc_steps
        })
    
    # Sort by total time
    doc_timings.sort(key=lambda x: x['total'], reverse=True)
    
    # Calculate totals
    grand_total = sum(step_totals.values())
    
    print(f"\n⏱️  STEP TIMING BREAKDOWN")
    print("-" * 40)
    for step, time in step_totals.items():
        if time > 0:
            pct = (time / grand_total * 100) if grand_total > 0 else 0
            step_display = step.replace('Step', '')
            print(f"{step_display:12s}: {time:8.1f} sec ({pct:5.1f}%)")
    print("-" * 40)
    print(f"{'TOTAL':12s}: {grand_total:8.1f} sec ({grand_total/60:5.1f} min)")
    
    print(f"\n📈 TOP 5 SLOWEST DOCUMENTS")
    print("-" * 40)
    for i, doc in enumerate(doc_timings[:5], 1):
        print(f"{i}. {doc['filename'][:40]}")
        print(f"   Total: {doc['total']:.1f} sec, Pages: {doc['pages']}")
        for step, time in doc['steps'].items():
            if time > 0:
                print(f"   - {step.replace('Step', ''):12s}: {time:6.1f} sec")
    
    # Check for embedding step in indexing run
    if run.get('step_results'):
        print(f"\n🔍 INDEXING RUN STEP RESULTS:")
        for step_name, step_data in run['step_results'].items():
            if isinstance(step_data, dict) and 'duration_seconds' in step_data:
                print(f"  - {step_name}: {step_data['duration_seconds']:.1f} sec")
    
    # Get wiki generation
    wiki = supabase.table('wiki_generation_runs').select('*').eq('indexing_run_id', run_id).execute()
    if wiki.data:
        w = wiki.data[0]
        if w.get('started_at') and w.get('completed_at'):
            wiki_start = datetime.fromisoformat(w['started_at'].replace('Z', '+00:00'))
            wiki_end = datetime.fromisoformat(w['completed_at'].replace('Z', '+00:00'))
            wiki_duration = (wiki_end - wiki_start).total_seconds()
            
            print(f"\n📖 WIKI GENERATION")
            print(f"Duration: {wiki_duration:.1f} seconds ({wiki_duration/60:.1f} minutes)")
    
    print(f"\n💡 PERFORMANCE INSIGHTS")
    print("=" * 60)
    if step_totals['EnrichmentStep'] > 0:
        enrichment_pct = (step_totals['EnrichmentStep'] / grand_total * 100)
        print(f"• Enrichment (VLM) takes {enrichment_pct:.1f}% of processing time")
        if enrichment_pct > 50:
            print(f"  ⚠️  VLM processing is the major bottleneck!")
    
    total_pages = sum(doc['pages'] for doc in doc_timings)
    if total_pages > 0 and grand_total > 0:
        pages_per_sec = total_pages / grand_total
        print(f"• Processing rate: {pages_per_sec:.2f} pages/second")
        print(f"• Average per document: {grand_total/len(doc_timings):.1f} seconds")

if __name__ == "__main__":
    run_id = "ca079abb-b746-45fb-b448-0c4f5f185f8c"
    analyze_timings(run_id)