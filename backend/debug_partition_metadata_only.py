#!/usr/bin/env python3
"""
Debug PartitionStep and MetadataStep only (no external API dependencies)
"""

import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.pipeline.indexing.orchestrator import get_indexing_orchestrator
from src.pipeline.shared.models import DocumentInput, UploadType
from src.services.pipeline_service import PipelineService
from src.services.storage_service import StorageService


async def debug_partition_metadata_only():
    """Debug PartitionStep and MetadataStep only"""

    print("🔍 Debugging PartitionStep and MetadataStep Only")
    print("=" * 60)

    # Test with a single PDF first
    pdf_folder = Path("../data/external/construction_pdfs/multiple-pdf-project")
    pdf_files = list(pdf_folder.glob("*.pdf"))

    if not pdf_files:
        print("❌ No PDF files found")
        return

    # Use the first PDF for testing
    test_pdf = pdf_files[0]
    print(f"📄 Testing with: {test_pdf.name}")

    # Create a test document input
    document_input = DocumentInput(
        document_id=UUID("00000000-0000-0000-0000-000000000001"),  # Test ID
        run_id=UUID("00000000-0000-0000-0000-000000000002"),  # Test run ID
        user_id=None,
        file_path=str(test_pdf.absolute()),  # Use local file path
        filename=test_pdf.name,
        upload_type=UploadType.EMAIL,
        upload_id="debug-test",
        index_run_id=UUID("00000000-0000-0000-0000-000000000003"),
        metadata={"email": "debug@test.com"},
    )

    try:
        # Initialize orchestrator
        print("🔧 Initializing orchestrator...")
        orchestrator = await get_indexing_orchestrator()

        # Manually initialize only PartitionStep and MetadataStep
        print("🔧 Initializing PartitionStep and MetadataStep...")
        await initialize_partition_metadata_steps(orchestrator, document_input.user_id)

        # Test PartitionStep
        print("\n🧪 Testing PartitionStep...")
        partition_result = await test_partition_step(orchestrator, document_input)

        if partition_result and partition_result.status == "completed":
            print("\n🧪 Testing MetadataStep...")
            await test_metadata_step(orchestrator, document_input, partition_result)
        else:
            print("❌ Cannot test MetadataStep without successful PartitionStep")

    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback

        traceback.print_exc()


async def initialize_partition_metadata_steps(orchestrator, user_id):
    """Initialize only PartitionStep and MetadataStep"""
    try:
        # Load configuration
        if not orchestrator.config_manager:
            raise ValueError("Config manager is None - cannot initialize steps")

        config = await orchestrator.config_manager.get_indexing_config(user_id)

        # Initialize PartitionStep
        partition_config = config.steps.get("partition", {})
        from src.pipeline.indexing.steps.partition import PartitionStep
        orchestrator.partition_step = PartitionStep(
            config=partition_config,
            storage_client=orchestrator.storage,
            progress_tracker=orchestrator.progress_tracker,
            storage_service=orchestrator.storage_service,
        )

        # Initialize MetadataStep
        metadata_config = config.steps.get("metadata", {})
        from src.pipeline.indexing.steps.metadata import MetadataStep
        orchestrator.metadata_step = MetadataStep(
            config=metadata_config,
            storage_client=orchestrator.storage,
            progress_tracker=orchestrator.progress_tracker,
            storage_service=orchestrator.storage_service,
        )

        print("✅ PartitionStep and MetadataStep initialized successfully")

    except Exception as e:
        print(f"❌ Failed to initialize steps: {e}")
        raise


async def test_partition_step(orchestrator, document_input):
    """Test partition step in isolation"""
    try:
        partition_step = orchestrator.partition_step

        # Test prerequisites
        print("  📋 Testing prerequisites...")
        prereq_result = await partition_step.validate_prerequisites_async(
            document_input
        )
        print(f"    Prerequisites: {'✅ PASS' if prereq_result else '❌ FAIL'}")

        if prereq_result:
            # Test execution
            print("  🚀 Testing execution...")
            result = await partition_step.execute(document_input)
            print(f"    Status: {result.status}")
            print(f"    Duration: {result.duration_seconds:.2f}s")

            if result.status == "completed":
                print("    ✅ PartitionStep completed successfully")
                print(f"    📊 Summary: {result.summary_stats}")
                return result
            else:
                print(f"    ❌ PartitionStep failed: {result.error_message}")
                return None
        else:
            print("    ❌ Prerequisites failed")
            return None

    except Exception as e:
        print(f"    ❌ Exception: {e}")
        import traceback

        traceback.print_exc()
        return None


async def test_metadata_step(orchestrator, document_input, partition_result):
    """Test metadata step in isolation"""
    try:
        metadata_step = orchestrator.metadata_step

        # Test prerequisites with partition data
        print("  📋 Testing prerequisites...")
        prereq_result = await metadata_step.validate_prerequisites_async(
            partition_result
        )
        print(f"    Prerequisites: {'✅ PASS' if prereq_result else '❌ FAIL'}")

        if prereq_result:
            # Test execution
            print("  🚀 Testing execution...")
            result = await metadata_step.execute(partition_result)
            print(f"    Status: {result.status}")
            print(f"    Duration: {result.duration_seconds:.2f}s")

            if result.status == "completed":
                print("    ✅ MetadataStep completed successfully")
                print(f"    📊 Summary: {result.summary_stats}")
                return result
            else:
                print(f"    ❌ MetadataStep failed: {result.error_message}")
                return None
        else:
            print("    ❌ Prerequisites failed")
            return None

    except Exception as e:
        print(f"    ❌ Exception: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(debug_partition_metadata_only())
