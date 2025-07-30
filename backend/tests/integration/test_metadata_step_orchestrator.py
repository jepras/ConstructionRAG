#!/usr/bin/env python3
"""
Integration test for metadata step through orchestrator
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


async def test_metadata_step_orchestrator():
    """Test metadata step through orchestrator"""
    try:
        # Configuration - using existing partition run
        existing_run_id = "995ac851-7d05-40ad-8149-9a5004f55239"
        document_id = "550e8400-e29b-41d4-a716-446655440000"
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        test_pdf_path = Path(
            "../../data/external/construction_pdfs/test-with-little-variety.pdf"
        )

        print(f"✅ Using existing partition run: {existing_run_id}")

        # Create document input with existing run ID
        document_input = DocumentInput(
            document_id=UUID(document_id),
            run_id=UUID(existing_run_id),
            user_id=UUID(user_id),
            file_path=str(test_pdf_path),
            filename=test_pdf_path.name,
            metadata={},
        )

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

        # Use existing indexing run
        print(f"✅ Using existing indexing run: {existing_run_id}")

        # Run only the metadata step
        print("🚀 Running metadata step...")
        try:
            # Pass the run ID directly to the metadata step
            print(f"📥 Loading partition data from run: {existing_run_id}")

            # Execute metadata step with run ID
            metadata_result = await orchestrator.metadata_step.execute(existing_run_id)

            # Store the result
            await pipeline_service.store_step_result(
                indexing_run_id=UUID(existing_run_id),
                step_name="metadata",
                step_result=metadata_result,
            )

            print("✅ Metadata step completed successfully")
            print(f"   Status: {metadata_result.status}")
            print(f"   Duration: {metadata_result.duration_seconds:.2f} seconds")

            # Display results
            if metadata_result.summary_stats:
                print(f"\n📊 Summary Statistics:")
                stats = metadata_result.summary_stats
                print(f"   Elements Processed: {stats.get('elements_processed', 0)}")
                print(f"   Metadata Extracted: {stats.get('metadata_extracted', 0)}")
                print(
                    f"   Processing Strategy: {stats.get('processing_strategy', 'unknown')}"
                )

            if metadata_result.sample_outputs:
                print(f"\n📋 Sample Outputs:")
                samples = metadata_result.sample_outputs

                if samples.get("sample_metadata"):
                    print(f"   Sample Metadata: {len(samples['sample_metadata'])}")
                    for i, metadata in enumerate(samples["sample_metadata"][:3]):
                        print(
                            f"     {i+1}. {metadata.get('category', 'Unknown')}: {metadata.get('text_preview', '')[:100]}..."
                        )

            if metadata_result.data:
                print(f"\n📁 Full Data Structure:")
                data = metadata_result.data
                print(
                    f"   Text Elements with Metadata: {len(data.get('text_elements', []))}"
                )
                print(
                    f"   Table Elements with Metadata: {len(data.get('table_elements', []))}"
                )

                # Check text elements with metadata
                text_elements = data.get("text_elements", [])
                if text_elements:
                    print(f"\n📝 Text Elements with Metadata:")
                    for elem in text_elements[:3]:
                        elem_id = elem.get("id", "unknown")
                        metadata = elem.get("metadata", {})
                        print(f"   {elem_id}: {len(metadata)} metadata fields")

                # Check table elements with metadata
                table_elements = data.get("table_elements", [])
                if table_elements:
                    print(f"\n📊 Table Elements with Metadata:")
                    for table in table_elements[:3]:
                        table_id = table.get("id", "unknown")
                        metadata = table.get("metadata", {})
                        print(f"   {table_id}: {len(metadata)} metadata fields")

            return True

        except Exception as e:
            print(f"❌ Metadata step failed: {e}")
            return False

    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_metadata_step_orchestrator())
    if success:
        print("\n✅ Metadata step orchestrator test successful!")
    else:
        print("\n❌ Metadata step orchestrator test failed!")
        sys.exit(1)
