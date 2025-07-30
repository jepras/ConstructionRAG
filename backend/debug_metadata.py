#!/usr/bin/env python3
"""
Debug script to see exactly where the metadata step fails
"""

import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from config.database import get_supabase_admin_client
from pipeline.indexing.steps.metadata import MetadataStep


def debug_metadata_step():
    """Debug the metadata step to find the exact error"""

    print("🔍 Debugging Metadata Step")
    print("=" * 30)

    try:
        # Get the latest indexing run using admin client
        supabase = get_supabase_admin_client()
        result = (
            supabase.table("indexing_runs")
            .select("*")
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )

        latest_run = result.data[0]
        partition_data = latest_run["step_results"]["partition"]["data"]

        print(f"Partition data keys: {list(partition_data.keys())}")
        print(f"Text elements: {len(partition_data.get('text_elements', []))}")
        print(f"Table elements: {len(partition_data.get('table_elements', []))}")
        print(f"Extracted pages: {len(partition_data.get('extracted_pages', {}))}")

        # Initialize metadata step
        metadata_config = {
            "enable_section_detection": True,
            "enable_number_detection": True,
            "enable_complexity_analysis": True,
        }

        metadata_step = MetadataStep(config=metadata_config)

        # Try to process just the table element
        if partition_data.get("table_elements"):
            table_element = partition_data["table_elements"][0]
            print(f"\nProcessing table element: {table_element}")

            # Try the analyzer directly
            analyzer = metadata_step.analyzer
            try:
                result = analyzer.analyze_table_element(table_element, "test_id")
                print(f"✅ Table analysis successful: {result}")
            except Exception as e:
                print(f"❌ Table analysis failed: {e}")
                import traceback

                traceback.print_exc()

        # Try to process extracted pages
        if partition_data.get("extracted_pages"):
            page_key = list(partition_data["extracted_pages"].keys())[0]
            page_info = partition_data["extracted_pages"][page_key]
            print(f"\nProcessing extracted page: {page_key} -> {page_info}")

            try:
                result = analyzer.analyze_extracted_image(
                    page_key, page_info, "test_id"
                )
                print(f"✅ Page analysis successful: {result}")
            except Exception as e:
                print(f"❌ Page analysis failed: {e}")
                import traceback

                traceback.print_exc()

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_metadata_step()
