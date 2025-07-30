#!/usr/bin/env python3
"""
Verify that metadata step preserves partition structure
"""

import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from config.database import get_supabase_admin_client
from pipeline.indexing.steps.metadata import MetadataStep


async def verify_structure():
    """Verify the metadata step preserves partition structure"""

    print("🔍 Verifying Metadata Step Structure Preservation")
    print("=" * 50)

    try:
        # Get the specific indexing run
        supabase = get_supabase_admin_client()
        result = (
            supabase.table("indexing_runs")
            .select("*")
            .eq("id", "7409d996-b839-4fff-a31d-d4de64967aae")
            .execute()
        )

        latest_run = result.data[0]
        partition_data = latest_run["step_results"]["partition"]["data"]

        print(f"📊 Original Partition Structure:")
        print(f"   Keys: {list(partition_data.keys())}")
        print(f"   Text elements: {len(partition_data.get('text_elements', []))}")
        print(f"   Table elements: {len(partition_data.get('table_elements', []))}")
        print(f"   Extracted pages: {len(partition_data.get('extracted_pages', {}))}")

        # Run metadata step
        metadata_config = {
            "enable_section_detection": True,
            "enable_number_detection": True,
            "enable_complexity_analysis": True,
        }

        metadata_step = MetadataStep(config=metadata_config)
        metadata_result = await metadata_step.execute(partition_data)

        if metadata_result.status == "completed":
            enriched_data = metadata_result.data

            print(f"\n📊 Enriched Data Structure:")
            print(f"   Keys: {list(enriched_data.keys())}")
            print(f"   Text elements: {len(enriched_data.get('text_elements', []))}")
            print(f"   Table elements: {len(enriched_data.get('table_elements', []))}")
            print(
                f"   Extracted pages: {len(enriched_data.get('extracted_pages', {}))}"
            )
            print(f"   Page sections: {enriched_data.get('page_sections', {})}")

            # Check if structure is preserved
            structure_preserved = (
                len(enriched_data.get("text_elements", []))
                == len(partition_data.get("text_elements", []))
                and len(enriched_data.get("table_elements", []))
                == len(partition_data.get("table_elements", []))
                and len(enriched_data.get("extracted_pages", {}))
                == len(partition_data.get("extracted_pages", {}))
            )

            print(f"\n✅ Structure Preserved: {structure_preserved}")

            # Check if metadata was added
            if enriched_data.get("text_elements"):
                first_text = enriched_data["text_elements"][0]
                has_structural_metadata = "structural_metadata" in first_text
                print(f"✅ Structural Metadata Added: {has_structural_metadata}")

                if has_structural_metadata:
                    print(f"   Sample metadata: {first_text['structural_metadata']}")

            # Check if page sections were added
            has_page_sections = "page_sections" in enriched_data
            print(f"✅ Page Sections Added: {has_page_sections}")

        else:
            print(f"❌ Metadata step failed: {metadata_result.error_message}")

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import asyncio

    asyncio.run(verify_structure())
