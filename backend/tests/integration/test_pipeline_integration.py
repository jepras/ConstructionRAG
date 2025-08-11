from __future__ import annotations

import os

import pytest


@pytest.mark.asyncio
@pytest.mark.skipif(
    not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY")),
    reason="Supabase env not configured",
)
async def test_get_recent_indexing_runs_filters_to_user_projects(async_client, auth_headers):
    # Smoke: just call the endpoint and assert 200 and list response shape
    r = await async_client.get("/pipeline/indexing/runs", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    if body:
        row = body[0]
        assert "id" in row and "status" in row


#!/usr/bin/env python3
"""
Integration test for pipeline steps working together
Tests partition, metadata, enrichment, and chunking steps in sequence
"""

import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
# Also add the backend directory to handle relative imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.config.database import get_supabase_admin_client
from src.pipeline.indexing.orchestrator import IndexingOrchestrator
from src.pipeline.shared.models import DocumentInput, UploadType
from src.services.pipeline_service import PipelineService

# Removed debug functions - no longer needed


async def test_pipeline_integration():
    """Test partition, metadata, enrichment, and chunking steps working together"""
    try:
        print("🧪 Testing Pipeline Integration (Partition + Metadata + Enrichment + Chunking)")
        print("=" * 70)

        # Configuration
        document_id = "550e8400-e29b-41d4-a716-446655440000"
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        test_pdf_path = Path("data/external/construction_pdfs/test-with-little-variety.pdf")

        if not test_pdf_path.exists():
            print(f"❌ Test PDF not found: {test_pdf_path}")
            return False

        print(f"✅ Using test PDF: {test_pdf_path.name}")

        # Create document input
        document_input = DocumentInput(
            document_id=UUID(document_id),
            run_id=UUID(int=0),  # Placeholder - will be updated by orchestrator
            user_id=UUID(user_id),
            file_path=str(test_pdf_path),
            filename=test_pdf_path.name,
            upload_type=UploadType.USER_PROJECT,
            project_id=UUID("123e4567-e89b-12d3-a456-426614174001"),
            index_run_id=UUID("123e4567-e89b-12d3-a456-426614174002"),
            metadata={},
        )

        # Get orchestrator with admin client
        db = get_supabase_admin_client()
        pipeline_service = PipelineService(use_admin_client=True)

        orchestrator = IndexingOrchestrator(
            db=db,
            pipeline_service=pipeline_service,
            use_test_storage=True,  # Use test bucket for integration tests
            upload_type=UploadType.USER_PROJECT,
        )

        print("✅ Orchestrator initialized with admin client")

        # Initialize steps
        await orchestrator.initialize_steps(user_id=UUID(user_id))
        print("✅ Steps initialized")

        # Create indexing run
        indexing_run = await pipeline_service.create_indexing_run(
            document_id=document_input.document_id,
            user_id=document_input.user_id,
        )
        document_input.run_id = indexing_run.id
        print(f"✅ Created indexing run: {indexing_run.id}")

        # Test Step 1: Partition
        print("\n" + "=" * 50)
        print("🚀 STEP 1: PARTITION")
        print("=" * 50)

        try:
            # Validate prerequisites
            if not await orchestrator.partition_step.validate_prerequisites_async(document_input):
                print("❌ Partition step prerequisites failed")
                return False

            # Execute partition step
            partition_result = await orchestrator.partition_step.execute(document_input)

            # Store the result
            await pipeline_service.store_step_result(
                indexing_run_id=indexing_run.id,
                step_name="partition",
                step_result=partition_result,
            )

            print("✅ Partition step completed successfully")
            print(f"   Status: {partition_result.status}")
            print(f"   Duration: {partition_result.duration_seconds:.2f} seconds")

            if partition_result.status != "completed":
                print(f"❌ Partition step failed: {partition_result.error_message}")
                return False

            # Display partition results
            if partition_result.summary_stats:
                print("\n📊 Partition Summary:")
                stats = partition_result.summary_stats
                print(f"   Text Elements: {stats.get('text_elements', 0)}")
                print(f"   Table Elements: {stats.get('table_elements', 0)}")
                print(f"   Extracted Pages: {stats.get('extracted_pages', 0)}")

            # Partition data processed successfully

        except Exception as e:
            print(f"❌ Partition step failed: {e}")
            return False

        # Test Step 2: Metadata
        print("\n" + "=" * 50)
        print("🚀 STEP 2: METADATA")
        print("=" * 50)

        try:
            # Pass the run ID to metadata step
            print(f"📥 Loading partition data from run: {indexing_run.id}")

            # Execute metadata step with run ID
            metadata_result = await orchestrator.metadata_step.execute(str(indexing_run.id))

            # Store the result
            await pipeline_service.store_step_result(
                indexing_run_id=indexing_run.id,
                step_name="metadata",
                step_result=metadata_result,
            )

            print("✅ Metadata step completed successfully")
            print(f"   Status: {metadata_result.status}")
            print(f"   Duration: {metadata_result.duration_seconds:.2f} seconds")

            if metadata_result.status != "completed":
                print(f"❌ Metadata step failed: {metadata_result.error_message}")
                return False

            # Display metadata results
            if metadata_result.summary_stats:
                print("\n📊 Metadata Summary:")
                stats = metadata_result.summary_stats
                print(f"   Total Elements: {stats.get('total_elements', 0)}")
                print(f"   Text Elements: {stats.get('text_elements', 0)}")
                print(f"   Table Elements: {stats.get('table_elements', 0)}")
                print(f"   Elements with Numbers: {stats.get('elements_with_numbers', 0)}")
                print(f"   Elements with Sections: {stats.get('elements_with_sections', 0)}")
                print(f"   Page Sections Detected: {stats.get('page_sections_detected', 0)}")

            # Metadata data processed successfully

        except Exception as e:
            print(f"❌ Metadata step failed: {e}")
            return False

        # Test Step 3: Enrichment
        print("\n" + "=" * 50)
        print("🚀 STEP 3: ENRICHMENT")
        print("=" * 50)

        try:
            # Execute enrichment step with metadata result
            print("📥 Processing metadata output for enrichment")

            # Execute enrichment step with metadata result
            enrichment_result = await orchestrator.enrichment_step.execute(metadata_result)

            # Store the result
            await pipeline_service.store_step_result(
                indexing_run_id=indexing_run.id,
                step_name="enrichment",
                step_result=enrichment_result,
            )

            print("✅ Enrichment step completed successfully")
            print(f"   Status: {enrichment_result.status}")
            print(f"   Duration: {enrichment_result.duration_seconds:.2f} seconds")

            if enrichment_result.status != "completed":
                print(f"❌ Enrichment step failed: {enrichment_result.error_message}")
                return False

            # Display enrichment results
            if enrichment_result.summary_stats:
                print("\n📊 Enrichment Summary:")
                stats = enrichment_result.summary_stats
                print(f"   Tables processed: {stats.get('tables_processed', 0)}")
                print(f"   Images processed: {stats.get('images_processed', 0)}")
                print(f"   Total caption words: {stats.get('total_caption_words', 0)}")
                print(f"   VLM model: {stats.get('vlm_model', 'unknown')}")
                print(f"   Caption language: {stats.get('caption_language', 'unknown')}")

            if enrichment_result.sample_outputs:
                print("\n📋 Sample Outputs:")
                sample_tables = enrichment_result.sample_outputs.get("sample_tables", [])
                sample_images = enrichment_result.sample_outputs.get("sample_images", [])

                if sample_tables:
                    print(f"   Sample tables: {len(sample_tables)}")
                    for table in sample_tables:
                        print(f"     - Table {table['id']}: {table['caption_words']} words")

                if sample_images:
                    print(f"   Sample images: {len(sample_images)}")
                    for image in sample_images:
                        print(f"     - Page {image['page']}: {image['caption_words']} words")

        except Exception as e:
            print(f"❌ Enrichment step failed: {e}")
            return False

        # Test Step 4: Chunking
        print("\n" + "=" * 50)
        print("🚀 STEP 4: CHUNKING")
        print("=" * 50)

        try:
            # Execute chunking step with enrichment result
            print("📥 Processing enrichment output for chunking")

            # Execute chunking step with enrichment result
            chunking_result = await orchestrator.chunking_step.execute(enrichment_result, indexing_run.id, document_id)

            # Store the result
            await pipeline_service.store_step_result(
                indexing_run_id=indexing_run.id,
                step_name="chunking",
                step_result=chunking_result,
            )

            print("✅ Chunking step completed successfully")
            print(f"   Status: {chunking_result.status}")
            print(f"   Duration: {chunking_result.duration_seconds:.2f} seconds")

            if chunking_result.status != "completed":
                print(f"❌ Chunking step failed: {chunking_result.error_message}")
                return False

            # Display chunking results
            if chunking_result.summary_stats:
                print("\n📊 Chunking Summary:")
                stats = chunking_result.summary_stats
                print(f"   Total chunks created: {stats.get('total_chunks_created', 0)}")
                print(f"   Elements processed: {stats.get('total_elements_processed', 0)}")
                print(f"   Average chunk size: {stats.get('average_chunk_size', 0)} chars")

                # Show chunk type distribution
                chunk_types = stats.get("chunk_type_distribution", {})
                if chunk_types:
                    print("   Chunk types:")
                    for chunk_type, count in chunk_types.items():
                        print(f"     - {chunk_type}: {count}")

            if chunking_result.sample_outputs:
                print("\n📋 Sample Chunks:")
                sample_chunks = chunking_result.sample_outputs.get("sample_chunks", [])
                if sample_chunks:
                    print(f"   Sample chunks: {len(sample_chunks)}")
                    for i, chunk in enumerate(sample_chunks[:3]):
                        chunk_type = chunk.get("metadata", {}).get("element_category", "unknown")
                        content_preview = chunk.get("content_preview", "")
                        print(f"     - Chunk {i + 1}: {chunk_type} - {len(content_preview)} chars")
                        print(f"       Preview: {content_preview[:100]}...")

        except Exception as e:
            print(f"❌ Chunking step failed: {e}")
            return False

        # Test Step 5: Embedding
        print("\n" + "=" * 50)
        print("🚀 STEP 5: EMBEDDING")
        print("=" * 50)

        try:
            # Execute embedding step with chunking result
            print("📥 Processing chunking output for embedding")

            # Execute embedding step with chunking result
            embedding_result = await orchestrator.embedding_step.execute(chunking_result, indexing_run.id, document_id)

            # Store the result
            await pipeline_service.store_step_result(
                indexing_run_id=indexing_run.id,
                step_name="embedding",
                step_result=embedding_result,
            )

            print("✅ Embedding step completed successfully")
            print(f"   Status: {embedding_result.status}")
            print(f"   Duration: {embedding_result.duration_seconds:.2f} seconds")

            if embedding_result.status != "completed":
                print(f"❌ Embedding step failed: {embedding_result.error_message}")
                return False

            # Display embedding results
            if embedding_result.summary_stats:
                print("\n📊 Embedding Summary:")
                stats = embedding_result.summary_stats
                print(f"   Total chunks: {stats.get('total_chunks', 0)}")
                print(f"   Embeddings generated: {stats.get('embeddings_generated', 0)}")
                print(f"   Embedding model: {stats.get('embedding_model', 'unknown')}")
                print(f"   Embedding dimensions: {stats.get('embedding_dimensions', 0)}")
                print(f"   Batch size used: {stats.get('batch_size_used', 0)}")
                print(f"   Average time per chunk: {stats.get('average_embedding_time', 0):.3f}s")

            if embedding_result.sample_outputs:
                print("\n📋 Sample Embeddings:")
                sample_embeddings = embedding_result.sample_outputs.get("sample_embeddings", [])
                if sample_embeddings:
                    print(f"   Sample embeddings: {len(sample_embeddings)}")
                    for i, embedding in enumerate(sample_embeddings[:3]):
                        print(f"     - Embedding {i + 1}: {embedding.get('embedding_preview', 'unknown')}")
                        print(f"       Content: {embedding.get('content_preview', 'unknown')}")

        except Exception as e:
            print(f"❌ Embedding step failed: {e}")
            return False

        # Pipeline completed - all steps stored in database

        # Final validation
        print("\n" + "=" * 50)
        print("🔍 FINAL VALIDATION")
        print("=" * 50)

        # Check that all steps are stored in database
        final_run = await pipeline_service.get_indexing_run(indexing_run.id)
        if not final_run:
            print("❌ Could not retrieve final indexing run")
            return False

        step_results = final_run.step_results
        print(f"✅ Stored step results: {list(step_results.keys())}")

        required_steps = [
            "partition",
            "metadata",
            "enrichment",
            "chunking",
            "embedding",
        ]
        for step in required_steps:
            if step not in step_results:
                print(f"❌ {step} results not found in database")
                return False
            else:
                print(f"✅ {step} results found in database")

        print("✅ All five steps successfully stored in database")
        print("✅ Pipeline integration test completed successfully!")

        # Output indexing run ID for easy database lookup
        print(f"\n📋 INDEXING RUN ID: {indexing_run.id}")
        print("   Use this ID to query the database for detailed results")

        return True

    except Exception as e:
        print(f"❌ Pipeline integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_pipeline_integration())
    if success:
        print("\n🎉 Pipeline integration test successful!")
    else:
        print("\n❌ Pipeline integration test failed!")
        sys.exit(1)
