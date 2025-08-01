#!/usr/bin/env python3
"""
Simple test script to run the metadata step on partition data
"""

import asyncio
import sys
import os
from uuid import UUID

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from config.database import get_supabase_admin_client
from src.pipeline.indexing.steps.metadata import MetadataStep


class AdminPipelineService:
    """PipelineService that uses admin client to bypass RLS"""

    def __init__(self):
        self.supabase = get_supabase_admin_client()

    async def store_step_result(
        self, indexing_run_id: UUID, step_name: str, step_result
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

            # Add the new step result
            current_step_results[step_name] = step_result.model_dump(mode="json")

            # Update the step_results field
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


async def test_metadata_step():
    """Test the metadata step with partition data from database"""

    print("🧪 Testing Metadata Step with Partition Data")
    print("=" * 50)

    try:
        # Get the latest indexing run using admin client
        supabase = get_supabase_admin_client()
        result = (
            supabase.table("indexing_runs")
            .select("*")
            .eq(
                "id", "584ec5e1-8a40-4dee-b5d0-4a16f03d7daa"
            )  # Use new partition run ID
            .execute()
        )

        if not result.data:
            print("❌ No indexing runs found in database")
            return False

        latest_run = result.data[0]
        run_id = latest_run["id"]
        print(f"📊 Using indexing run: {run_id}")

        # Get partition data from the run
        step_results = latest_run.get("step_results", {})
        partition_result = step_results.get("partition")

        if not partition_result:
            print("❌ No partition result found in indexing run")
            return False

        partition_data = partition_result.get("data", {})
        print(f"✅ Found partition data with keys: {list(partition_data.keys())}")

        # Show partition data summary
        text_elements = partition_data.get("text_elements", [])
        table_elements = partition_data.get("table_elements", [])
        extracted_pages = partition_data.get("extracted_pages", {})

        print(f"📋 Partition Data Summary:")
        print(f"   Text Elements: {len(text_elements)}")
        print(f"   Table Elements: {len(table_elements)}")
        print(f"   Extracted Pages: {len(extracted_pages)}")

        if text_elements:
            print(f"   Sample Text Element: {text_elements[0]}")
        elif table_elements:
            print(f"   Sample Table Element: {table_elements[0]}")
        elif extracted_pages:
            page_key = list(extracted_pages.keys())[0]
            print(
                f"   Sample Extracted Page: {page_key} -> {extracted_pages[page_key]}"
            )

        # Initialize metadata step
        print("\n🔧 Initializing metadata step...")
        metadata_config = {
            "enable_section_detection": True,
            "enable_number_detection": True,
            "enable_complexity_analysis": True,
        }

        metadata_step = MetadataStep(config=metadata_config)
        print("✅ Metadata step initialized")

        # Execute metadata step
        print("\n🚀 Executing metadata step...")
        metadata_result = await metadata_step.execute(partition_data)

        print(f"✅ Metadata step completed with status: {metadata_result.status}")
        print(f"   Duration: {metadata_result.duration_seconds:.2f} seconds")

        # Show metadata results
        if metadata_result.status == "completed":
            print(f"\n📊 Metadata Results Summary:")
            print(f"   Summary Stats: {metadata_result.summary_stats}")

            # Show sample outputs
            sample_outputs = metadata_result.sample_outputs
            if sample_outputs:
                print(f"\n📋 Sample Outputs:")
                print(
                    f"   Sample Text Elements: {len(sample_outputs.get('sample_text_elements', []))}"
                )
                print(
                    f"   Sample Tables: {len(sample_outputs.get('sample_tables', []))}"
                )
                print(f"   Page Sections: {sample_outputs.get('page_sections', {})}")

                # Show a sample enriched element
                if sample_outputs.get("sample_text_elements"):
                    sample = sample_outputs["sample_text_elements"][0]
                    print(f"\n🔍 Sample Enriched Element:")
                    print(f"   ID: {sample.get('id')}")
                    print(f"   Page: {sample.get('page')}")
                    print(f"   Section Inherited: {sample.get('section_inherited')}")
                    print(f"   Has Numbers: {sample.get('has_numbers')}")
                    print(f"   Complexity: {sample.get('complexity')}")

            # Store the result in database
            print(f"\n💾 Storing metadata result in database...")
            pipeline_service = AdminPipelineService()
            success = await pipeline_service.store_step_result(
                indexing_run_id=UUID(run_id),
                step_name="metadata",
                step_result=metadata_result,
            )
            print(f"✅ Stored metadata result: {success}")

            print(f"\n🎉 Metadata step test completed successfully!")
            return True

        else:
            print(f"❌ Metadata step failed: {metadata_result.error_message}")
            return False

    except Exception as e:
        print(f"❌ Metadata step test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_metadata_step())
    if success:
        print("\n✅ Metadata step test successful!")
    else:
        print("\n❌ Metadata step test failed!")
        sys.exit(1)
