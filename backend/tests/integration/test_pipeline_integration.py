#!/usr/bin/env python3
"""
Integration test for pipeline steps working together
Tests partition, metadata, and enrichment steps in sequence
"""

import asyncio
import os
import sys
from uuid import UUID
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from config.database import get_supabase_admin_client
from pipeline.indexing.orchestrator import IndexingOrchestrator
from pipeline.shared.models import DocumentInput
from services.pipeline_service import PipelineService


async def test_pipeline_integration():
    """Test partition, metadata, and enrichment steps working together"""
    try:
        print("🧪 Testing Pipeline Integration (Partition + Metadata + Enrichment)")
        print("=" * 60)

        # Configuration
        document_id = "550e8400-e29b-41d4-a716-446655440000"
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        test_pdf_path = Path(
            "../data/external/construction_pdfs/test-with-little-variety.pdf"
        )

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
            metadata={},
        )

        # Get orchestrator with admin client
        db = get_supabase_admin_client()
        pipeline_service = PipelineService(use_admin_client=True)

        orchestrator = IndexingOrchestrator(
            db=db,
            pipeline_service=pipeline_service,
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
            if not await orchestrator.partition_step.validate_prerequisites_async(
                document_input
            ):
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
                print(f"\n📊 Partition Summary:")
                stats = partition_result.summary_stats
                print(f"   Text Elements: {stats.get('text_elements', 0)}")
                print(f"   Table Elements: {stats.get('table_elements', 0)}")
                print(f"   Extracted Pages: {stats.get('extracted_pages', 0)}")

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
            metadata_result = await orchestrator.metadata_step.execute(
                str(indexing_run.id)
            )

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
                print(f"\n📊 Metadata Summary:")
                stats = metadata_result.summary_stats
                print(f"   Total Elements: {stats.get('total_elements', 0)}")
                print(f"   Text Elements: {stats.get('text_elements', 0)}")
                print(f"   Table Elements: {stats.get('table_elements', 0)}")
                print(
                    f"   Elements with Numbers: {stats.get('elements_with_numbers', 0)}"
                )
                print(
                    f"   Elements with Sections: {stats.get('elements_with_sections', 0)}"
                )
                print(
                    f"   Page Sections Detected: {stats.get('page_sections_detected', 0)}"
                )

        except Exception as e:
            print(f"❌ Metadata step failed: {e}")
            return False

        # Test Step 3: Enrichment
        print("\n" + "=" * 50)
        print("🚀 STEP 3: ENRICHMENT")
        print("=" * 50)

        try:
            # Execute enrichment step with metadata result
            print(f"📥 Processing metadata output for enrichment")

            # Execute enrichment step with metadata result
            enrichment_result = await orchestrator.enrichment_step.execute(
                metadata_result
            )

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
                print(f"\n📊 Enrichment Summary:")
                stats = enrichment_result.summary_stats
                print(f"   Tables processed: {stats.get('tables_processed', 0)}")
                print(f"   Images processed: {stats.get('images_processed', 0)}")
                print(f"   Total caption words: {stats.get('total_caption_words', 0)}")
                print(f"   VLM model: {stats.get('vlm_model', 'unknown')}")
                print(
                    f"   Caption language: {stats.get('caption_language', 'unknown')}"
                )

            if enrichment_result.sample_outputs:
                print(f"\n📋 Sample Outputs:")
                sample_tables = enrichment_result.sample_outputs.get(
                    "sample_tables", []
                )
                sample_images = enrichment_result.sample_outputs.get(
                    "sample_images", []
                )

                if sample_tables:
                    print(f"   Sample tables: {len(sample_tables)}")
                    for table in sample_tables:
                        print(
                            f"     - Table {table['id']}: {table['caption_words']} words"
                        )

                if sample_images:
                    print(f"   Sample images: {len(sample_images)}")
                    for image in sample_images:
                        print(
                            f"     - Page {image['page']}: {image['caption_words']} words"
                        )

        except Exception as e:
            print(f"❌ Enrichment step failed: {e}")
            return False

        # TODO: Future steps (placeholders)
        print("\n" + "=" * 50)
        print("📋 FUTURE STEPS (Not Yet Implemented)")
        print("=" * 50)
        print("   Step 4: Chunking (text segmentation)")
        print("   Step 5: Embedding (vector creation)")
        print("   Step 6: Storage (vector database)")

        # Final validation
        print("\n" + "=" * 50)
        print("🔍 FINAL VALIDATION")
        print("=" * 50)

        # Check that both steps are stored in database
        final_run = await pipeline_service.get_indexing_run(indexing_run.id)
        if not final_run:
            print("❌ Could not retrieve final indexing run")
            return False

        step_results = final_run.step_results
        print(f"✅ Stored step results: {list(step_results.keys())}")

        if "partition" not in step_results:
            print("❌ Partition results not found in database")
            return False

        if "metadata" not in step_results:
            print("❌ Metadata results not found in database")
            return False

        if "enrichment" not in step_results:
            print("❌ Enrichment results not found in database")
            return False

        print("✅ All three steps successfully stored in database")
        print("✅ Pipeline integration test completed successfully!")

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
