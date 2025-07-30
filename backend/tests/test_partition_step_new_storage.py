#!/usr/bin/env python3
"""
Test script for partition step with new storage structure
"""

import asyncio
import os
import sys
from uuid import UUID
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from config.database import get_supabase_admin_client
from models.pipeline import IndexingRun, StepResult
from pipeline.shared.models import DocumentInput
from pipeline.indexing.steps.partition import PartitionStep


class AdminPipelineService:
    """PipelineService that uses admin client to bypass RLS"""

    def __init__(self):
        self.supabase = get_supabase_admin_client()

    async def create_indexing_run(
        self, document_id: UUID, user_id: UUID
    ) -> IndexingRun:
        """Create a new indexing run for a document."""
        try:
            indexing_run_data = {"document_id": str(document_id), "status": "pending"}

            result = (
                self.supabase.table("indexing_runs").insert(indexing_run_data).execute()
            )

            if not result.data:
                raise Exception("Failed to create indexing run")

            return IndexingRun(**result.data[0])

        except Exception as e:
            print(f"Error creating indexing run: {e}")
            raise


async def test_partition_step_new_storage():
    """Test partition step with new storage structure"""

    print("🧪 Testing Partition Step with New Storage Structure")
    print("=" * 60)

    # Configuration
    user_id = "a4be935d-dd17-4db2-aa4e-b4989277bb1a"
    document_id = "550e8400-e29b-41d4-a716-446655440000"

    # Test PDF path
    test_pdf_path = Path(
        "../../data/external/construction_pdfs/test-with-little-variety.pdf"
    )

    if not test_pdf_path.exists():
        print(f"❌ Test PDF not found: {test_pdf_path}")
        return False

    try:
        # Create admin pipeline service
        pipeline_service = AdminPipelineService()
        print("✅ Admin PipelineService created")

        # Test 1: Create indexing run
        print("📝 Creating indexing run...")
        indexing_run = await pipeline_service.create_indexing_run(
            document_id=UUID(document_id), user_id=UUID(user_id)
        )
        print(f"✅ Created indexing run: {indexing_run.id}")

        # Test 2: Create document input with run_id
        print("📄 Creating document input with run_id...")
        document_input = DocumentInput(
            document_id=UUID(document_id),
            run_id=indexing_run.id,  # This is the key difference - we set run_id
            user_id=UUID(user_id),
            file_path=str(test_pdf_path),
            filename=test_pdf_path.name,
            metadata={},
        )
        print(f"✅ Created document input with run_id: {document_input.run_id}")

        # Test 3: Initialize partition step
        print("🔧 Initializing partition step...")
        partition_config = {
            "ocr_strategy": "auto",
            "extract_tables": True,
            "extract_images": True,
            "max_image_size_mb": 10,
            "ocr_languages": ["dan"],
            "include_coordinates": True,
        }

        partition_step = PartitionStep(config=partition_config)
        print("✅ Partition step initialized")

        # Test 4: Execute partition step
        print("🚀 Executing partition step with new storage structure...")
        partition_result = await partition_step.execute(document_input)
        print(f"✅ Partition step completed with status: {partition_result.status}")

        # Test 5: Display results
        print("\n📊 Partition Results Summary:")
        print(f"   Status: {partition_result.status}")
        print(f"   Duration: {partition_result.duration_seconds:.2f} seconds")
        print(f"   Summary Stats: {partition_result.summary_stats}")

        if partition_result.data:
            data = partition_result.data
            print(f"\n📁 Storage Structure Results:")
            print(f"   Text Elements: {len(data.get('text_elements', []))}")
            print(f"   Table Elements: {len(data.get('table_elements', []))}")
            print(f"   Extracted Pages: {len(data.get('extracted_pages', {}))}")

            # Check if extracted pages have Supabase URLs
            extracted_pages = data.get("extracted_pages", {})
            if extracted_pages:
                print(f"\n🖼️  Extracted Pages with Supabase URLs:")
                for page_num, page_info in extracted_pages.items():
                    if "url" in page_info:
                        print(f"   Page {page_num}: {page_info['url']}")
                        print(f"     Storage Path: {page_info['storage_path']}")
                    else:
                        print(f"   Page {page_num}: No URL (fallback to local)")

            # Check if table elements have Supabase URLs
            table_elements = data.get("table_elements", [])
            if table_elements:
                print(f"\n📊 Table Elements with Supabase URLs:")
                for table in table_elements:
                    table_id = table.get("id", "unknown")
                    metadata = table.get("metadata", {})
                    print(f"   Table {table_id}:")
                    print(f"     Image Path: {metadata.get('image_path', 'None')}")
                    print(f"     Has HTML: {metadata.get('has_html', False)}")
                    print(f"     HTML Length: {metadata.get('html_length', 0)}")
                    if "image_url" in metadata:
                        print(f"     Supabase URL: {metadata['image_url']}")
                        print(f"     Storage Path: {metadata['image_storage_path']}")
                    else:
                        print(f"     Supabase URL: No URL (fallback to local)")
                        # Check if the image file exists
                        image_path = metadata.get("image_path")
                        if image_path:
                            import os

                            if os.path.exists(image_path):
                                print(
                                    f"     Local File: EXISTS ({os.path.getsize(image_path)} bytes)"
                                )
                            else:
                                print(f"     Local File: NOT FOUND")
                        else:
                            print(f"     Local File: No path specified")

        # Test 6: Complete the run
        print("\n✅ Marking indexing run as completed...")
        print(f"✅ Final run ID: {indexing_run.id}")

        print("\n🎉 Partition step with new storage structure test completed!")
        return True

    except Exception as e:
        print(f"❌ Partition step test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_partition_step_new_storage())
    if success:
        print("\n✅ Partition step with new storage structure successful!")
    else:
        print("\n❌ Partition step with new storage structure failed!")
        sys.exit(1)
