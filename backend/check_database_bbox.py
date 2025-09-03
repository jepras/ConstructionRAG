#!/usr/bin/env python3
"""Check bbox data in database for recent runs."""

import os
import json
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
db = create_client(url, key)

print("="*60)
print("DATABASE BBOX CHECK")
print("="*60)

# Get recent indexing runs
print("\n1. RECENT INDEXING RUNS:")
print("-"*40)

# Get recent runs (last 30 days)
runs_result = db.table('indexing_runs').select('id, created_at, status').order('created_at', desc=True).limit(10).execute()

if not runs_result.data:
    print("No recent indexing runs found")
    exit()

for run in runs_result.data[:3]:
    print(f"\nRun ID: {run['id']}")
    print(f"  Created: {run['created_at']}")
    print(f"  Status: {run['status']}")

# Check the most recent run
latest_run = runs_result.data[0]
run_id = latest_run['id']

print(f"\n\n2. CHECKING RUN: {run_id}")
print("-"*40)

# Check document_chunks
print("\nCHECKING DOCUMENT_CHUNKS:")
chunks_result = db.table('document_chunks').select('chunk_id, metadata').eq('indexing_run_id', run_id).limit(5).execute()

if chunks_result.data:
    print(f"Found {len(chunks_result.data)} chunks")
    
    for i, chunk in enumerate(chunks_result.data[:3]):
        print(f"\nChunk {i+1}:")
        meta = chunk['metadata']
        if isinstance(meta, str):
            meta = json.loads(meta)
        
        print(f"  Metadata type: {type(meta)}")
        if meta:
            print(f"  Metadata keys: {list(meta.keys())[:10]}")  # First 10 keys
            bbox = meta.get('bbox')
            print(f"  Has bbox key: {'YES' if 'bbox' in meta else 'NO'}")
            print(f"  Bbox value: {bbox}")
            if bbox:
                print(f"  Bbox type: {type(bbox)}")
else:
    print("No chunks found for this run")

# Check documents table step_results
print("\n\n3. CHECKING DOCUMENTS STEP_RESULTS:")
print("-"*40)

# Get documents for this run
docs_result = db.table('indexing_run_documents').select('document_id').eq('indexing_run_id', run_id).execute()

if docs_result.data:
    doc_id = docs_result.data[0]['document_id']
    
    # Get document with step_results
    doc_result = db.table('documents').select('filename, step_results').eq('id', doc_id).execute()
    
    if doc_result.data:
        doc = doc_result.data[0]
        print(f"Document: {doc['filename']}")
        
        step_results = doc.get('step_results')
        if step_results:
            # Check PartitionStep results
            if 'PartitionStep' in step_results:
                partition = step_results['PartitionStep']
                print("\nPartitionStep found in step_results")
                
                # Check sample_outputs
                if 'sample_outputs' in partition:
                    samples = partition['sample_outputs']
                    print(f"  sample_outputs keys: {list(samples.keys()) if isinstance(samples, dict) else type(samples)}")
                    
                    if isinstance(samples, dict) and 'sample_text_elements' in samples:
                        text_samples = samples['sample_text_elements']
                        if text_samples and len(text_samples) > 0:
                            print(f"\n  Sample text elements: {len(text_samples)}")
                            for i, sample in enumerate(text_samples[:2]):
                                print(f"\n  Sample {i+1}:")
                                print(f"    Keys: {list(sample.keys())}")
                                
                # Check if actual data is stored somewhere
                if 'data' in partition:
                    data = partition['data']
                    print(f"\n  PartitionStep data type: {type(data)}")
                    if isinstance(data, dict):
                        print(f"  Data keys: {list(data.keys())}")

# Check a specific chunk's full metadata
print("\n\n4. FULL METADATA INSPECTION:")
print("-"*40)

if chunks_result.data:
    # Get first chunk with all fields
    chunk = chunks_result.data[0]
    meta = chunk['metadata']
    if isinstance(meta, str):
        meta = json.loads(meta)
    
    print("Complete metadata content:")
    print(json.dumps(meta, indent=2))

print("\n" + "="*60)
print("SUMMARY")
print("="*60)

if chunks_result.data:
    chunks_with_bbox = 0
    chunks_with_null_bbox = 0
    chunks_without_bbox_key = 0
    
    for chunk in chunks_result.data:
        meta = chunk['metadata']
        if isinstance(meta, str):
            meta = json.loads(meta)
        
        if meta:
            if 'bbox' not in meta:
                chunks_without_bbox_key += 1
            elif meta['bbox'] is None:
                chunks_with_null_bbox += 1
            else:
                chunks_with_bbox += 1
    
    print(f"Chunks with bbox data: {chunks_with_bbox}")
    print(f"Chunks with null bbox: {chunks_with_null_bbox}")
    print(f"Chunks without bbox key: {chunks_without_bbox_key}")
    
    if chunks_with_null_bbox > 0:
        print("\n⚠️  ISSUE: Bbox key exists but value is null!")
        print("This suggests bbox is being lost during JSON serialization or database storage")