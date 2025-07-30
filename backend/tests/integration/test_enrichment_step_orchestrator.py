#!/usr/bin/env python3
"""
Integration test for enrichment step through orchestrator
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
from pipeline.indexing.orchestrator import get_indexing_orchestrator
from pipeline.shared.models import DocumentInput
from services.pipeline_service import PipelineService


async def test_enrichment_step_orchestrator():
    """Test enrichment step through orchestrator"""
    try:
        # Configuration - using specific run ID as requested
        existing_run_id = "429d7943-284c-4c52-805a-bcc3e02dd285"
        document_id = "550e8400-e29b-41d4-a716-446655440000"
        user_id = "123e4567-e89b-12d3-a456-426614174000"

        print(f"✅ Using specific enrichment test run: {existing_run_id}")

        # Get orchestrator with admin client
        db = get_supabase_admin_client()

        # Create PipelineService with admin client
        pipeline_service = PipelineService(use_admin_client=True)

        from pipeline.indexing.orchestrator import IndexingOrchestrator

        orchestrator = IndexingOrchestrator(
            db=db,
            pipeline_service=pipeline_service,
        )

        print("✅ Orchestrator initialized")

        # Initialize steps
        await orchestrator.initialize_steps(user_id=UUID(user_id))
        print("✅ Steps initialized")

        # Load existing run data to get metadata step results
        print(f"📥 Loading data from run: {existing_run_id}")
        existing_run = await pipeline_service.get_indexing_run(UUID(existing_run_id))
        if not existing_run:
            print(f"❌ Run {existing_run_id} not found")
            return False

        if "metadata" not in existing_run.step_results:
            print(f"❌ Run {existing_run_id} does not have metadata step results")
            return False

        metadata_result = existing_run.step_results["metadata"]
        if metadata_result.status != "completed":
            print(f"❌ Metadata step not completed for run {existing_run_id}")
            return False

        print(f"✅ Found metadata step results for run {existing_run_id}")

        # Run only the enrichment step
        print("🚀 Running enrichment step...")
        try:
            # Execute enrichment step with metadata output data
            enrichment_result = await orchestrator.enrichment_step.execute(
                metadata_result
            )

            # Store the result
            await pipeline_service.store_step_result(
                indexing_run_id=UUID(existing_run_id),
                step_name="enrichment",
                step_result=enrichment_result,
            )

            print("✅ Enrichment step completed successfully")
            print(f"   Status: {enrichment_result.status}")
            print(f"   Duration: {enrichment_result.duration_seconds:.2f} seconds")

            # Display results
            if enrichment_result.summary_stats:
                print(f"\n📊 Summary Statistics:")
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

            if enrichment_result.data:
                print(f"\n📁 Full Data Structure:")
                data = enrichment_result.data
                print(f"   Text elements: {len(data.get('text_elements', []))}")
                print(f"   Table elements: {len(data.get('table_elements', []))}")
                print(f"   Extracted pages: {len(data.get('extracted_pages', {}))}")

                # Check enrichment metadata
                tables_with_enrichment = sum(
                    1
                    for t in data.get("table_elements", [])
                    if "enrichment_metadata" in t
                )
                images_with_enrichment = sum(
                    1
                    for p in data.get("extracted_pages", {}).values()
                    if "enrichment_metadata" in p
                )

                print(f"   Tables with enrichment: {tables_with_enrichment}")
                print(f"   Images with enrichment: {images_with_enrichment}")

            return True

        except Exception as e:
            print(f"❌ Enrichment step failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_enrichment_step_orchestrator())
    if success:
        print("\n✅ Enrichment step orchestrator test successful!")
    else:
        print("\n❌ Enrichment step orchestrator test failed!")
        sys.exit(1)
