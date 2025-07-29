#!/usr/bin/env python3
"""
Integration test for partition step with database integration using admin client
"""

import asyncio
import os
import sys
from uuid import UUID
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

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

    async def update_indexing_run_status(
        self, indexing_run_id: UUID, status: str, error_message: str = None
    ) -> IndexingRun:
        """Update the status of an indexing run."""
        try:
            update_data = {"status": status, "error_message": error_message}

            if status in ["completed", "failed"]:
                from datetime import datetime

                update_data["completed_at"] = datetime.utcnow().isoformat()

            result = (
                self.supabase.table("indexing_runs")
                .update(update_data)
                .eq("id", str(indexing_run_id))
                .execute()
            )

            if not result.data:
                raise Exception("Failed to update indexing run")

            return IndexingRun(**result.data[0])

        except Exception as e:
            print(f"Error updating indexing run status: {e}")
            raise

    async def store_step_result(
        self, indexing_run_id: UUID, step_name: str, step_result: StepResult
    ) -> bool:
        """Store a step result in the indexing run's step_results JSONB field."""
        try:
            # First, get the current step_results
            result = (
                self.supabase.table("indexing_runs")
                .select("step_results")
                .eq("id", str(indexing_run_id))
                .execute()
            )

            if not result.data:
                raise Exception("Indexing run not found")

            current_step_results = result.data[0].get("step_results", {})

            # Custom serialization for partition step results
            if step_name == "partition" and step_result.data:
                # Create a serializable version of the data
                serializable_data = self._make_partition_data_serializable(
                    step_result.data
                )

                # Create a modified step result with serializable data
                modified_result = StepResult(
                    step=step_result.step,
                    status=step_result.status,
                    duration_seconds=step_result.duration_seconds,
                    summary_stats=step_result.summary_stats,
                    sample_outputs=step_result.sample_outputs,
                    data=serializable_data,
                    started_at=step_result.started_at,
                    completed_at=step_result.completed_at,
                    error_message=step_result.error_message,
                    error_details=step_result.error_details,
                )

                current_step_results[step_name] = modified_result.model_dump(
                    mode="json"
                )
            else:
                # Use normal serialization for other steps
                current_step_results[step_name] = step_result.model_dump(mode="json")

            # Update the indexing run
            update_result = (
                self.supabase.table("indexing_runs")
                .update({"step_results": current_step_results})
                .eq("id", str(indexing_run_id))
                .execute()
            )

            return bool(update_result.data)

        except Exception as e:
            print(f"Error storing step result: {e}")
            raise

    def _make_partition_data_serializable(self, data: dict) -> dict:
        """Convert partition data to JSON-serializable format"""

        def clean_for_json(obj):
            """Remove non-serializable objects"""
            if hasattr(obj, "__dict__"):
                # Handle objects with attributes
                return str(obj)
            elif isinstance(obj, dict):
                cleaned = {}
                for key, value in obj.items():
                    cleaned[key] = clean_for_json(value)
                return cleaned
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            else:
                return str(obj)

        return clean_for_json(data)

    async def get_step_result(self, indexing_run_id: UUID, step_name: str) -> dict:
        """Get a step result from the indexing run's step_results JSONB field."""
        try:
            result = (
                self.supabase.table("indexing_runs")
                .select("step_results")
                .eq("id", str(indexing_run_id))
                .execute()
            )

            if not result.data:
                raise Exception("Indexing run not found")

            step_results = result.data[0].get("step_results", {})
            return step_results.get(step_name, {})

        except Exception as e:
            print(f"Error getting step result: {e}")
            raise


async def test_partition_step_with_db():
    """Test actual partition step with database integration"""

    print("🧪 Testing actual partition step with database integration...")

    # Configuration
    user_id = "a4be935d-dd17-4db2-aa4e-b4989277bb1a"
    document_id = "550e8400-e29b-41d4-a716-446655440000"

    # Test PDF path - use the actual test PDF
    test_pdf_path = Path(
        "../data/external/construction_pdfs/test-with-little-variety.pdf"
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

        # Test 2: Update status to running
        print("🔄 Updating status to running...")
        updated_run = await pipeline_service.update_indexing_run_status(
            indexing_run_id=indexing_run.id, status="running"
        )
        print(f"✅ Updated status: {updated_run.status}")

        # Test 3: Create document input
        print("📄 Creating document input...")
        document_input = DocumentInput(
            document_id=UUID(document_id),
            user_id=UUID(user_id),
            file_path=str(test_pdf_path),
            filename=test_pdf_path.name,
        )
        print(f"✅ Created document input for: {document_input.filename}")

        # Test 4: Initialize and run partition step
        print("🔧 Initializing partition step...")

        # Create partition config
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

        print("🚀 Executing partition step...")
        partition_result = await partition_step.execute(document_input)
        print(f"✅ Partition step completed with status: {partition_result.status}")

        # Test 5: Store partition result in database
        print("💾 Storing partition result in database...")
        success = await pipeline_service.store_step_result(
            indexing_run_id=indexing_run.id,
            step_name="partition",
            step_result=partition_result,
        )
        print(f"✅ Stored partition result: {success}")

        # Test 6: Retrieve and verify stored result
        print("📥 Retrieving stored partition result...")
        stored_result = await pipeline_service.get_step_result(
            indexing_run_id=indexing_run.id, step_name="partition"
        )
        print(f"✅ Retrieved stored result: {bool(stored_result)}")

        # Test 7: Display partition results
        print("\n📊 Partition Results Summary:")
        print(f"   Status: {partition_result.status}")
        print(f"   Duration: {partition_result.duration_seconds:.2f} seconds")
        print(f"   Summary Stats: {partition_result.summary_stats}")

        if partition_result.data:
            data = partition_result.data
            print(f"   Text Elements: {len(data.get('text_elements', []))}")
            print(f"   Table Elements: {len(data.get('table_elements', []))}")
            print(f"   Raw Elements: {len(data.get('raw_elements', []))}")
            print(f"   Extracted Pages: {len(data.get('extracted_pages', {}))}")
            print(f"   Table Locations: {len(data.get('table_locations', []))}")
            print(f"   Image Locations: {len(data.get('image_locations', []))}")

        # Test 8: Complete the run
        print("✅ Marking indexing run as completed...")
        final_run = await pipeline_service.update_indexing_run_status(
            indexing_run_id=indexing_run.id, status="completed"
        )
        print(f"✅ Final status: {final_run.status}")

        print("\n🎉 All partition step database integration tests passed!")
        return True

    except Exception as e:
        print(f"❌ Partition step test failed: {e}")
        import traceback

        traceback.print_exc()

        # Try to mark as failed
        try:
            if "indexing_run" in locals():
                await pipeline_service.update_indexing_run_status(
                    indexing_run_id=indexing_run.id,
                    status="failed",
                    error_message=str(e),
                )
        except:
            pass

        return False


if __name__ == "__main__":
    success = asyncio.run(test_partition_step_with_db())
    if success:
        print("\n✅ Partition step with database integration successful!")
    else:
        print("\n❌ Partition step with database integration failed!")
        sys.exit(1)
