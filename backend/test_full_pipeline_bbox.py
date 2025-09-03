#!/usr/bin/env python3
"""Test that bbox coordinates flow through the entire pipeline and get stored."""

import sys
import json
import asyncio
import uuid
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline.indexing.steps.partition import PartitionStep
from src.pipeline.indexing.steps.metadata import MetadataStep
from src.pipeline.indexing.steps.enrichment import EnrichmentStep
from src.pipeline.indexing.steps.chunking import ChunkingStep
from src.pipeline.shared.models import DocumentInput

async def test_full_pipeline():
    """Test the full pipeline with both regular and scanned PDFs."""
    
    test_files = {
        "regular": {
            "path": "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/test-with-little-variety.pdf",
            "name": "test-with-little-variety.pdf"
        },
        "scanned": {
            "path": "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/small-complicated/mole-scannable.pdf",
            "name": "mole-scannable.pdf"
        }
    }
    
    results = {}
    
    for doc_type, file_info in test_files.items():
        print("\n" + "="*60)
        print(f"TESTING {doc_type.upper()} DOCUMENT")
        print("="*60)
        print(f"File: {file_info['name']}")
        
        # Create document input
        doc_input = DocumentInput(
            document_id=uuid.uuid4(),
            filename=file_info['name'],
            file_path=file_info['path'],
            upload_type='email',
            run_id=uuid.uuid4()
        )
        
        # Step 1: Partition
        print("\n1. PARTITION STEP:")
        print("-"*40)
        
        partition_config = {
            'ocr_strategy': 'auto',
            'extract_tables': True,
            'extract_images': True,
            'ocr_languages': ['dan'],
            'include_coordinates': True,
            'table_validation': {'enabled': False}
        }
        
        partition_step = PartitionStep(config=partition_config)
        partition_result = await partition_step.execute(doc_input)
        
        print(f"Status: {partition_result.status}")
        
        # Check bbox in partition output
        bbox_count = 0
        if hasattr(partition_result, 'data') and partition_result.data:
            text_elements = partition_result.data.get('text_elements', [])
            print(f"Text elements: {len(text_elements)}")
            
            for elem in text_elements[:10]:
                meta = elem.get('metadata', {})
                if 'bbox' in meta and meta['bbox'] is not None:
                    bbox_count += 1
            
            print(f"Elements with bbox: {bbox_count}/{min(10, len(text_elements))}")
            
            if bbox_count > 0:
                # Show first element with bbox
                for elem in text_elements:
                    meta = elem.get('metadata', {})
                    if meta.get('bbox'):
                        print(f"\nSample bbox: {meta['bbox']}")
                        print(f"Element text: {elem.get('text', '')[:50]}...")
                        break
        
        # Step 2: Metadata
        print("\n2. METADATA STEP:")
        print("-"*40)
        
        metadata_config = {
            'extract_page_structure': True,
            'detect_sections': True,
            'preserve_formatting': True
        }
        
        metadata_step = MetadataStep(config=metadata_config)
        metadata_result = await metadata_step.execute(partition_result)
        
        print(f"Status: {metadata_result.status}")
        
        # Check bbox preservation
        bbox_after_meta = 0
        if hasattr(metadata_result, 'data') and metadata_result.data:
            text_elements = metadata_result.data.get('text_elements', [])
            for elem in text_elements[:10]:
                # Check in structural_metadata
                struct_meta = elem.get('structural_metadata', {})
                if struct_meta.get('bbox'):
                    bbox_after_meta += 1
            
            print(f"Elements with bbox after metadata: {bbox_after_meta}/{min(10, len(text_elements))}")
        
        # Step 3: Enrichment
        print("\n3. ENRICHMENT STEP:")
        print("-"*40)
        
        enrichment_config = {
            'add_context_headers': True,
            'merge_related_elements': True,
            'min_content_length': 50
        }
        
        enrichment_step = EnrichmentStep(config=enrichment_config)
        enrichment_result = await enrichment_step.execute(metadata_result)
        
        print(f"Status: {enrichment_result.status}")
        
        # Step 4: Chunking
        print("\n4. CHUNKING STEP:")
        print("-"*40)
        
        chunking_config = {
            'chunking': {
                'chunk_size': 1000,
                'overlap': 200,
                'strategy': 'semantic',
                'min_chunk_size': 100,
                'max_chunk_size': 1200
            }
        }
        
        chunking_step = ChunkingStep(config=chunking_config)
        chunking_result = await chunking_step.execute(enrichment_result)
        
        print(f"Status: {chunking_result.status}")
        
        # Check bbox in final chunks
        bbox_in_chunks = 0
        if hasattr(chunking_result, 'data') and chunking_result.data:
            chunks = chunking_result.data.get('chunks', [])
            print(f"Total chunks: {len(chunks)}")
            
            for chunk in chunks:
                meta = chunk.get('metadata', {})
                if meta.get('bbox'):
                    bbox_in_chunks += 1
            
            print(f"Chunks with bbox: {bbox_in_chunks}/{len(chunks)}")
            
            # Show sample chunk with bbox
            for chunk in chunks:
                meta = chunk.get('metadata', {})
                if meta.get('bbox'):
                    print(f"\nSample chunk with bbox:")
                    print(f"  Chunk ID: {chunk.get('chunk_id', 'N/A')}")
                    print(f"  Bbox: {meta['bbox']}")
                    print(f"  Content: {chunk.get('content', '')[:100]}...")
                    break
        
        results[doc_type] = {
            'partition_bbox': bbox_count,
            'metadata_bbox': bbox_after_meta,
            'chunks_with_bbox': bbox_in_chunks,
            'total_chunks': len(chunks) if 'chunks' in locals() else 0
        }
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for doc_type, stats in results.items():
        print(f"\n{doc_type.upper()} DOCUMENT:")
        print(f"  Partition step bbox: {stats['partition_bbox']}")
        print(f"  Metadata step bbox: {stats['metadata_bbox']}")
        print(f"  Final chunks with bbox: {stats['chunks_with_bbox']}/{stats['total_chunks']}")
        
        if stats['chunks_with_bbox'] > 0:
            print(f"  ✅ Bbox preserved through pipeline!")
        else:
            print(f"  ❌ Bbox lost in pipeline!")
    
    # Write results to file
    with open('pipeline_bbox_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\nDetailed results saved to: pipeline_bbox_results.json")

# Run the test
if __name__ == "__main__":
    asyncio.run(test_full_pipeline())