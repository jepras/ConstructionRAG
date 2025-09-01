#!/usr/bin/env python3
"""Check database structure and data for timing analysis."""

import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

def check_indexing_run(run_id: str):
    """Check indexing run and related data."""
    
    print("=" * 60)
    print("CHECKING DATABASE STRUCTURE")
    print("=" * 60)
    
    # 1. Check indexing run
    print("\n1. INDEXING RUN:")
    print("-" * 40)
    result = supabase.table('indexing_runs').select('*').eq('id', run_id).execute()
    if result.data:
        run = result.data[0]
        print(f"Found indexing run: {run_id}")
        print(f"Columns: {list(run.keys())}")
        print(f"Status: {run.get('status')}")
        print(f"Started: {run.get('started_at')}")
        print(f"Completed: {run.get('completed_at')}")
    else:
        print(f"❌ No indexing run found with ID: {run_id}")
        return
    
    # 2. Check indexing_run_documents junction table
    print("\n2. INDEXING_RUN_DOCUMENTS:")
    print("-" * 40)
    result = supabase.table('indexing_run_documents').select('*').eq('indexing_run_id', run_id).limit(1).execute()
    if result.data:
        print(f"Found {len(result.data)} document links")
        print(f"Columns: {list(result.data[0].keys())}")
        
        # Get all document IDs
        all_docs = supabase.table('indexing_run_documents').select('document_id').eq('indexing_run_id', run_id).execute()
        doc_ids = [doc['document_id'] for doc in all_docs.data]
        print(f"Document IDs linked: {len(doc_ids)}")
    else:
        print("❌ No documents found in indexing_run_documents table")
        
        # Try alternative: documents with index_run_id
        print("\n2b. CHECKING DOCUMENTS WITH index_run_id:")
        result = supabase.table('documents').select('id, filename, index_run_id').eq('index_run_id', run_id).limit(5).execute()
        if result.data:
            print(f"Found {len(result.data)} documents with index_run_id")
            doc_ids = [doc['id'] for doc in result.data]
        else:
            print("❌ No documents found with index_run_id either")
            return
    
    # 3. Check documents table structure
    print("\n3. DOCUMENTS TABLE:")
    print("-" * 40)
    if doc_ids:
        result = supabase.table('documents').select('*').eq('id', doc_ids[0]).execute()
        if result.data:
            doc = result.data[0]
            print(f"Document columns: {list(doc.keys())}")
            
            # Check step_results structure
            if 'step_results' in doc and doc['step_results']:
                print(f"\nstep_results structure:")
                step_results = doc['step_results']
                if isinstance(step_results, dict):
                    for step, data in step_results.items():
                        print(f"  - {step}:")
                        if isinstance(data, dict):
                            if 'duration_seconds' in data:
                                print(f"    ✓ duration_seconds: {data['duration_seconds']}")
                            else:
                                print(f"    ❌ No duration_seconds field")
                                print(f"    Available fields: {list(data.keys())[:5]}")
                else:
                    print(f"  step_results is not a dict: {type(step_results)}")
            else:
                print("  ❌ No step_results data")
    
    # 4. Check wiki_generation_runs
    print("\n4. WIKI_GENERATION_RUNS:")
    print("-" * 40)
    result = supabase.table('wiki_generation_runs').select('*').eq('indexing_run_id', run_id).execute()
    if result.data:
        wiki = result.data[0]
        print(f"Found wiki generation run")
        print(f"Columns: {list(wiki.keys())}")
        print(f"Status: {wiki.get('status')}")
        print(f"Started: {wiki.get('started_at')}")
        print(f"Completed: {wiki.get('completed_at')}")
    else:
        print("❌ No wiki generation run found")
    
    # 5. Sample query to test timing extraction
    print("\n5. TESTING TIMING EXTRACTION:")
    print("-" * 40)
    
    # Try to get timing data
    if doc_ids:
        query = f"""
        SELECT 
            filename,
            page_count,
            step_results->'partition'->>'duration_seconds' as partition_time
        FROM documents 
        WHERE id = '{doc_ids[0]}'
        """
        
        # Since Supabase doesn't support raw SQL easily, let's check with Python
        result = supabase.table('documents').select('filename, page_count, step_results').eq('id', doc_ids[0]).execute()
        if result.data:
            doc = result.data[0]
            print(f"Document: {doc['filename']}")
            if doc.get('step_results') and 'partition' in doc['step_results']:
                partition_data = doc['step_results']['partition']
                if 'duration_seconds' in partition_data:
                    print(f"✓ Partition duration: {partition_data['duration_seconds']} seconds")
                else:
                    print(f"❌ No duration_seconds in partition step")
            else:
                print(f"❌ No partition data in step_results")

if __name__ == "__main__":
    run_id = "ca079abb-b746-45fb-b448-0c4f5f185f8c"
    check_indexing_run(run_id)