#!/usr/bin/env python3
"""
Integration test for partition step through orchestrator
"""

import asyncio
import os
import sys
from uuid import UUID
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# No longer needed with absolute imports
# sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from src.config.database import get_supabase_admin_client
from src.pipeline.indexing.orchestrator import get_indexing_orchestrator
from src.pipeline.shared.models import DocumentInput
from src.services.pipeline_service import PipelineService


async def test_partition_step_orchestrator():
    """Test partition step through orchestrator"""
    try:
        # Configuration
        document_id = "550e8400-e29b-41d4-a716-446655440000"
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        test_pdf_path = Path(
            "../../data/external/construction_pdfs/test-with-little-variety.pdf"
        )

        if not test_pdf_path.exists():
            print(f"❌ Test PDF not found: {test_pdf_path}")
            return False

        print(f"✅ Created document input for: {test_pdf_path.name}")

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

        # Create custom PipelineService with admin client
        class AdminPipelineService(PipelineService):
            def __init__(self):
                self.supabase = get_supabase_admin_client()

        pipeline_service = AdminPipelineService()

        from src.pipeline.indexing.orchestrator import IndexingOrchestrator

        orchestrator = IndexingOrchestrator(
            db=db,
            pipeline_service=pipeline_service,
        )

        print("✅ Orchestrator initialized")

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

        # Run only the partition step
        print("🚀 Running partition step...")
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

            # Display results
            if partition_result.summary_stats:
                print(f"\n📊 Summary Statistics:")
                stats = partition_result.summary_stats
                print(f"   Text Elements: {stats.get('text_elements', 0)}")
                print(f"   Table Elements: {stats.get('table_elements', 0)}")
                print(f"   Extracted Pages: {stats.get('extracted_pages', 0)}")
                print(f"   Pages Analyzed: {stats.get('pages_analyzed', 0)}")
                print(
                    f"   Processing Strategy: {stats.get('processing_strategy', 'unknown')}"
                )

            if partition_result.sample_outputs:
                print(f"\n📋 Sample Outputs:")
                samples = partition_result.sample_outputs

                if samples.get("sample_text_elements"):
                    print(
                        f"   Sample Text Elements: {len(samples['sample_text_elements'])}"
                    )
                    for i, elem in enumerate(samples["sample_text_elements"][:2]):
                        print(
                            f"     {i+1}. {elem.get('category', 'Unknown')} (Page {elem.get('page', '?')}): {elem.get('text_preview', '')[:100]}..."
                        )

                if samples.get("sample_tables"):
                    print(f"   Sample Tables: {len(samples['sample_tables'])}")
                    for i, table in enumerate(samples["sample_tables"][:2]):
                        print(
                            f"     {i+1}. {table.get('category', 'Unknown')}: {table.get('text_preview', '')[:100]}..."
                        )
                        print(f"        Has HTML: {table.get('has_html', False)}")

            if partition_result.data:
                print(f"\n📁 Full Data Structure:")
                data = partition_result.data
                print(f"   Text Elements: {len(data.get('text_elements', []))}")
                print(f"   Table Elements: {len(data.get('table_elements', []))}")
                print(f"   Extracted Pages: {len(data.get('extracted_pages', {}))}")

                # Check extracted pages
                extracted_pages = data.get("extracted_pages", {})
                if extracted_pages:
                    print(f"\n🖼️  Extracted Pages:")
                    for page_num, page_info in extracted_pages.items():
                        if "url" in page_info:
                            print(f"   Page {page_num}: ✅ Uploaded to Supabase")
                        else:
                            print(f"   Page {page_num}: ❌ Not uploaded")

                # Check table elements
                table_elements = data.get("table_elements", [])
                if table_elements:
                    print(f"\n📊 Table Elements:")
                    for table in table_elements:
                        table_id = table.get("id", "unknown")
                        metadata = table.get("metadata", {})
                        if "image_url" in metadata:
                            print(f"   {table_id}: ✅ Image uploaded to Supabase")
                        elif metadata.get("image_path"):
                            print(f"   {table_id}: ⚠️  Local image only")
                        else:
                            print(f"   {table_id}: ❌ No image")

            return True

        except Exception as e:
            print(f"❌ Partition step failed: {e}")
            return False

    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_partition_step_orchestrator())
    if success:
        print("\n✅ Partition step orchestrator test successful!")
    else:
        print("\n❌ Partition step orchestrator test failed!")
        sys.exit(1)
