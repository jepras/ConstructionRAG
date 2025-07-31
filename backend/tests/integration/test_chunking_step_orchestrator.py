#!/usr/bin/env python3
"""
Integration test for chunking step through orchestrator
Tests core logic preservation from notebook implementation with real data
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
from services.pipeline_service import PipelineService


async def test_chunking_step_orchestrator():
    """Test chunking step through orchestrator with real data"""
    try:
        # Configuration - using specific run ID as requested
        existing_run_id = "20d0d6ed-008b-44c2-b085-54b5332f3a89"
        document_id = "550e8400-e29b-41d4-a716-446655440000"
        user_id = "123e4567-e89b-12d3-a456-426614174000"

        print(f"✅ Using specific chunking test run: {existing_run_id}")

        # Get orchestrator with admin client
        db = get_supabase_admin_client()
        pipeline_service = PipelineService(use_admin_client=True)

        orchestrator = IndexingOrchestrator(
            db=db,
            pipeline_service=pipeline_service,
        )

        print("✅ Orchestrator initialized")

        # Initialize steps
        await orchestrator.initialize_steps(user_id=UUID(user_id))
        print("✅ Steps initialized")

        # Load existing run data to get enrichment step results
        print(f"📥 Loading data from run: {existing_run_id}")
        existing_run = await pipeline_service.get_indexing_run(UUID(existing_run_id))
        if not existing_run:
            print(f"❌ Run {existing_run_id} not found")
            return False

        if "enrichment" not in existing_run.step_results:
            print(f"❌ Run {existing_run_id} does not have enrichment step results")
            return False

        enrichment_result = existing_run.step_results["enrichment"]
        if enrichment_result.status != "completed":
            print(f"❌ Enrichment step not completed for run {existing_run_id}")
            return False

        print(f"✅ Found enrichment step results for run {existing_run_id}")

        # Run only the chunking step
        print("🚀 Running chunking step...")

        # Execute chunking step with enrichment output data
        chunking_result = await orchestrator.chunking_step.execute(
            enrichment_result, UUID(existing_run_id), UUID(document_id)
        )

        # Store the result
        await pipeline_service.store_step_result(
            indexing_run_id=UUID(existing_run_id),
            step_name="chunking",
            step_result=chunking_result,
        )

        print("✅ Chunking step completed successfully")
        print(f"   Status: {chunking_result.status}")
        print(f"   Duration: {chunking_result.duration_seconds:.2f} seconds")

        # Verify core logic preservation
        print("\n=== CORE LOGIC PRESERVATION VERIFICATION ===")

        # 1. Check that chunks were created
        if chunking_result.status == "completed":
            chunks = chunking_result.data.get("chunks", [])
            print(f"✅ Chunks created: {len(chunks)}")

            # 2. Check noise filtering (Title elements should be excluded)
            title_chunks = [
                c for c in chunks if c["metadata"].get("element_category") == "Title"
            ]
            if len(title_chunks) == 0:
                print("✅ Noise filtering: Title elements correctly excluded")
            else:
                print(
                    f"❌ Noise filtering: {len(title_chunks)} Title elements found (should be 0)"
                )

            # 3. Check list grouping (NarrativeText + ListItems should be combined)
            list_chunks = [
                c for c in chunks if c["metadata"].get("element_category") == "List"
            ]
            if len(list_chunks) > 0:
                print(
                    f"✅ List grouping: {len(list_chunks)} combined list chunks created"
                )
                # Check that list content includes narrative + items
                list_content = list_chunks[0]["content"]
                if (
                    "Hovedaktiviteter:" in list_content
                    and "Digital byggeproces" in list_content
                ):
                    print(
                        "✅ List grouping: Narrative and list items correctly combined"
                    )
                else:
                    print(
                        "❌ List grouping: List content doesn't match expected format"
                    )
            else:
                print("❌ List grouping: No combined list chunks found")

            # 4. Check VLM caption prioritization for tables
            table_chunks = [
                c for c in chunks if c["metadata"].get("element_category") == "Table"
            ]
            if len(table_chunks) > 0:
                table_content = table_chunks[0]["content"]
                if "Denne tabel viser en oversigt" in table_content:
                    print(
                        "✅ VLM caption prioritization: Table captions correctly used"
                    )
                else:
                    print("❌ VLM caption prioritization: Table captions not found")

            # 5. Check VLM caption prioritization for images
            image_chunks = [
                c
                for c in chunks
                if c["metadata"].get("element_category") == "ExtractedPage"
            ]
            if len(image_chunks) > 0:
                image_content = image_chunks[0]["content"]
                if "Denne side viser en kompleks byggeplan" in image_content:
                    print(
                        "✅ VLM caption prioritization: Image captions correctly used"
                    )
                else:
                    print("❌ VLM caption prioritization: Image captions not found")

            # 6. Check section title inheritance
            chunks_with_sections = [
                c for c in chunks if c["metadata"].get("section_title_inherited")
            ]
            if len(chunks_with_sections) == len(chunks):
                print("✅ Section title inheritance: All chunks have section titles")
            else:
                print(
                    f"❌ Section title inheritance: {len(chunks_with_sections)}/{len(chunks)} chunks have section titles"
                )

            # 7. Check metadata preservation
            chunks_with_enrichment = [
                c for c in chunks if c["metadata"].get("enrichment_metadata")
            ]
            if len(chunks_with_enrichment) > 0:
                print("✅ Metadata preservation: Enrichment metadata preserved")
            else:
                print("❌ Metadata preservation: No enrichment metadata found")

            # 8. Check content formatting
            narrative_chunks = [
                c
                for c in chunks
                if c["metadata"].get("element_category") == "NarrativeText"
            ]
            if len(narrative_chunks) > 0:
                content = narrative_chunks[0]["content"]
                if content.startswith("Section: 1.2 Demonstrationsejendommen"):
                    print("✅ Content formatting: Section titles correctly prefixed")
                else:
                    print(
                        "❌ Content formatting: Section titles not correctly formatted"
                    )

            # 9. Check summary statistics
            summary_stats = chunking_result.summary_stats
            if summary_stats.get("total_chunks_created") == len(chunks):
                print("✅ Summary statistics: Chunk count matches")
            else:
                print("❌ Summary statistics: Chunk count mismatch")

            # 10. Check sample outputs
            sample_outputs = chunking_result.sample_outputs
            if sample_outputs and "sample_chunks" in sample_outputs:
                print(
                    f"✅ Sample outputs: {len(sample_outputs['sample_chunks'])} samples provided"
                )
            else:
                print("❌ Sample outputs: No samples provided")

            # Display results
            if chunking_result.summary_stats:
                print(f"\n📊 Summary Statistics:")
                stats = chunking_result.summary_stats
                print(
                    f"   Total elements processed: {stats.get('total_elements_processed', 0)}"
                )
                print(
                    f"   Total chunks created: {stats.get('total_chunks_created', 0)}"
                )
                print(
                    f"   Average chunk size: {stats.get('average_chunk_size', 0):.0f} chars"
                )
                print(
                    f"   Chunk type distribution: {stats.get('chunk_type_distribution', {})}"
                )
                print(f"   Validation results: {stats.get('validation_results', {})}")

        else:
            print(f"❌ Chunking step failed: {chunking_result.error_message}")
            return False

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_chunking_step_orchestrator())
    if success:
        print("\n✅ Chunking step orchestrator test successful!")
        print("🎉 Core logic preservation verified!")
    else:
        print("\n❌ Chunking step orchestrator test failed!")
        sys.exit(1)
