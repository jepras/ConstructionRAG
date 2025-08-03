#!/usr/bin/env python3
"""
Debug individual pipeline steps to identify failure points
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


async def debug_individual_steps():
    """Debug individual pipeline steps"""

    print("🔍 Debugging Individual Pipeline Steps")
    print("=" * 50)

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

        # Initialize steps
        print("🔧 Initializing pipeline steps...")
        await orchestrator.initialize_steps(document_input.user_id)

        # Test each step individually
        print("\n🧪 Testing PartitionStep...")
        await test_partition_step(orchestrator, document_input)

        print("\n🧪 Testing MetadataStep...")
        await test_metadata_step(orchestrator, document_input)

        print("\n🧪 Testing EnrichmentStep...")
        await test_enrichment_step(orchestrator, document_input)

        print("\n🧪 Testing ChunkingStep...")
        await test_chunking_step(orchestrator, document_input)

    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback

        traceback.print_exc()


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
        return None


async def test_metadata_step(orchestrator, document_input):
    """Test metadata step in isolation"""
    try:
        metadata_step = orchestrator.metadata_step

        # First, we need partition data
        print("  📋 Getting partition data...")
        partition_result = await test_partition_step(orchestrator, document_input)

        if not partition_result or partition_result.status != "completed":
            print("    ❌ Cannot test metadata step without partition data")
            return None

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
        return None


async def test_enrichment_step(orchestrator, document_input):
    """Test enrichment step in isolation"""
    try:
        enrichment_step = orchestrator.enrichment_step

        # First, we need metadata data
        print("  📋 Getting metadata data...")
        metadata_result = await test_metadata_step(orchestrator, document_input)

        if not metadata_result or metadata_result.status != "completed":
            print("    ❌ Cannot test enrichment step without metadata data")
            return None

        # Test prerequisites with metadata data
        print("  📋 Testing prerequisites...")
        prereq_result = await enrichment_step.validate_prerequisites_async(
            metadata_result
        )
        print(f"    Prerequisites: {'✅ PASS' if prereq_result else '❌ FAIL'}")

        if prereq_result:
            # Test execution
            print("  🚀 Testing execution...")
            result = await enrichment_step.execute(metadata_result)
            print(f"    Status: {result.status}")
            print(f"    Duration: {result.duration_seconds:.2f}s")

            if result.status == "completed":
                print("    ✅ EnrichmentStep completed successfully")
                print(f"    📊 Summary: {result.summary_stats}")
                return result
            else:
                print(f"    ❌ EnrichmentStep failed: {result.error_message}")
                return None
        else:
            print("    ❌ Prerequisites failed")
            return None

    except Exception as e:
        print(f"    ❌ Exception: {e}")
        return None


async def test_chunking_step(orchestrator, document_input):
    """Test chunking step in isolation"""
    try:
        chunking_step = orchestrator.chunking_step

        # First, we need enrichment data
        print("  📋 Getting enrichment data...")
        enrichment_result = await test_enrichment_step(orchestrator, document_input)

        if not enrichment_result or enrichment_result.status != "completed":
            print("    ❌ Cannot test chunking step without enrichment data")
            return None

        # Test prerequisites with enrichment data
        print("  📋 Testing prerequisites...")
        prereq_result = await chunking_step.validate_prerequisites_async(
            enrichment_result
        )
        print(f"    Prerequisites: {'✅ PASS' if prereq_result else '❌ FAIL'}")

        if prereq_result:
            # Test execution
            print("  🚀 Testing execution...")
            result = await chunking_step.execute(
                enrichment_result,
                document_input.index_run_id,
                document_input.document_id,
            )
            print(f"    Status: {result.status}")
            print(f"    Duration: {result.duration_seconds:.2f}s")

            if result.status == "completed":
                print("    ✅ ChunkingStep completed successfully")
                print(f"    📊 Summary: {result.summary_stats}")
                return result
            else:
                print(f"    ❌ ChunkingStep failed: {result.error_message}")
                return None
        else:
            print("    ❌ Prerequisites failed")
            return None

    except Exception as e:
        print(f"    ❌ Exception: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(debug_individual_steps())
