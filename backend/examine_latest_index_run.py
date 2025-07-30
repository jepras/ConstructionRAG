#!/usr/bin/env python3
"""Script to examine the latest indexing run data and compare with metadata step expectations."""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from services.pipeline_service import PipelineService
from config.database import get_supabase_client


async def get_latest_indexing_run() -> Optional[Dict[str, Any]]:
    """Get the latest indexing run from the database."""
    try:
        supabase = get_supabase_client()

        # Get the most recent indexing run
        result = (
            supabase.table("indexing_runs")
            .select("*")
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            print("❌ No indexing runs found in database")
            return None

        return result.data[0]

    except Exception as e:
        print(f"❌ Error getting latest indexing run: {e}")
        return None


def analyze_partition_data(partition_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the partition data structure and content."""
    analysis = {
        "structure_valid": True,
        "missing_keys": [],
        "data_counts": {},
        "sample_data": {},
        "issues": [],
    }

    # Check required keys for metadata step
    required_keys = ["text_elements", "table_elements", "extracted_pages"]
    for key in required_keys:
        if key not in partition_data:
            analysis["missing_keys"].append(key)
            analysis["structure_valid"] = False

    # Count data in each section
    if "text_elements" in partition_data:
        text_elements = partition_data["text_elements"]
        analysis["data_counts"]["text_elements"] = len(text_elements)

        # Sample text element structure
        if text_elements:
            sample_text = text_elements[0]
            analysis["sample_data"]["text_element"] = {
                "keys": list(sample_text.keys()),
                "has_required_fields": all(
                    key in sample_text
                    for key in ["element", "id", "text", "category", "page", "metadata"]
                ),
                "sample_content": {
                    "id": sample_text.get("id"),
                    "category": sample_text.get("category"),
                    "page": sample_text.get("page"),
                    "text_length": len(sample_text.get("text", "")),
                    "metadata_keys": list(sample_text.get("metadata", {}).keys()),
                },
            }

    if "table_elements" in partition_data:
        table_elements = partition_data["table_elements"]
        analysis["data_counts"]["table_elements"] = len(table_elements)

        # Sample table element structure
        if table_elements:
            sample_table = table_elements[0]
            analysis["sample_data"]["table_element"] = {
                "keys": (
                    list(sample_table.keys())
                    if isinstance(sample_table, dict)
                    else f"Object type: {type(sample_table)}"
                ),
                "has_text_attr": hasattr(sample_table, "text"),
                "has_category_attr": hasattr(sample_table, "category"),
                "has_metadata_attr": hasattr(sample_table, "metadata"),
            }

    if "extracted_pages" in partition_data:
        extracted_pages = partition_data["extracted_pages"]
        analysis["data_counts"]["extracted_pages"] = len(extracted_pages)

        # Sample extracted page structure
        if extracted_pages:
            sample_page_key = list(extracted_pages.keys())[0]
            sample_page = extracted_pages[sample_page_key]
            analysis["sample_data"]["extracted_page"] = {
                "page_key": sample_page_key,
                "keys": list(sample_page.keys()),
                "has_required_fields": all(
                    key in sample_page
                    for key in ["page_number", "filename", "filepath"]
                ),
            }

    # Check for additional keys that might be useful
    additional_keys = [
        "raw_elements",
        "page_analysis",
        "table_locations",
        "image_locations",
        "metadata",
    ]
    for key in additional_keys:
        if key in partition_data:
            analysis["data_counts"][key] = (
                len(partition_data[key])
                if isinstance(partition_data[key], (list, dict))
                else "present"
            )

    return analysis


def compare_with_metadata_expectations(
    partition_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare partition data with what metadata step expects."""
    comparison = {"compatible": True, "issues": [], "recommendations": []}

    # Check if structure is valid
    if not partition_analysis["structure_valid"]:
        comparison["compatible"] = False
        comparison["issues"].append(
            f"Missing required keys: {partition_analysis['missing_keys']}"
        )

    # Check text elements structure
    if "text_element" in partition_analysis["sample_data"]:
        text_sample = partition_analysis["sample_data"]["text_element"]
        if not text_sample["has_required_fields"]:
            comparison["compatible"] = False
            comparison["issues"].append(
                "Text elements missing required fields (element, id, text, category, page, metadata)"
            )
        else:
            comparison["recommendations"].append(
                "✅ Text elements structure looks good for metadata step"
            )

    # Check table elements structure
    if "table_element" in partition_analysis["sample_data"]:
        table_sample = partition_analysis["sample_data"]["table_element"]
        if not table_sample["has_text_attr"]:
            comparison["issues"].append(
                "Table elements may not have 'text' attribute accessible"
            )
        if not table_sample["has_category_attr"]:
            comparison["issues"].append(
                "Table elements may not have 'category' attribute accessible"
            )
        if not table_sample["has_metadata_attr"]:
            comparison["issues"].append(
                "Table elements may not have 'metadata' attribute accessible"
            )

    # Check extracted pages structure
    if "extracted_page" in partition_analysis["sample_data"]:
        page_sample = partition_analysis["sample_data"]["extracted_page"]
        if not page_sample["has_required_fields"]:
            comparison["compatible"] = False
            comparison["issues"].append(
                "Extracted pages missing required fields (page_number, filename, filepath)"
            )
        else:
            comparison["recommendations"].append(
                "✅ Extracted pages structure looks good for metadata step"
            )

    return comparison


async def main():
    """Main function to examine latest indexing run."""
    print("🔍 Examining Latest Indexing Run Data")
    print("=" * 50)

    # Get latest indexing run
    latest_run = await get_latest_indexing_run()
    if not latest_run:
        return

    print(f"📊 Latest Indexing Run:")
    print(f"   ID: {latest_run['id']}")
    print(f"   Document ID: {latest_run['document_id']}")
    print(f"   Status: {latest_run['status']}")
    print(f"   Started: {latest_run['started_at']}")
    print(f"   Completed: {latest_run.get('completed_at', 'N/A')}")
    print()

    # Check step results
    step_results = latest_run.get("step_results", {})
    print(f"📋 Step Results Available: {list(step_results.keys())}")
    print()

    # Analyze partition step data
    if "partition" in step_results:
        partition_result = step_results["partition"]
        print("🔍 Analyzing Partition Step Data:")
        print(f"   Status: {partition_result.get('status')}")
        print(f"   Duration: {partition_result.get('duration_seconds')} seconds")

        # Get partition data
        partition_data = partition_result.get("data", {})
        if partition_data:
            print("   ✅ Partition data found")

            # Analyze partition data structure
            partition_analysis = analyze_partition_data(partition_data)

            print(f"\n📊 Partition Data Analysis:")
            print(f"   Structure Valid: {partition_analysis['structure_valid']}")
            print(f"   Missing Keys: {partition_analysis['missing_keys']}")
            print(f"   Data Counts: {partition_analysis['data_counts']}")

            # Compare with metadata expectations
            comparison = compare_with_metadata_expectations(partition_analysis)

            print(f"\n🔍 Metadata Step Compatibility:")
            print(f"   Compatible: {comparison['compatible']}")

            if comparison["issues"]:
                print(f"   Issues:")
                for issue in comparison["issues"]:
                    print(f"     ❌ {issue}")

            if comparison["recommendations"]:
                print(f"   Recommendations:")
                for rec in comparison["recommendations"]:
                    print(f"     {rec}")

            # Show sample data structure
            print(f"\n📋 Sample Data Structure:")
            for data_type, sample in partition_analysis["sample_data"].items():
                print(f"   {data_type.upper()}:")
                for key, value in sample.items():
                    print(f"     {key}: {value}")

        else:
            print("   ❌ No partition data found in step result")
    else:
        print("❌ No partition step result found")

    # Check if metadata step exists
    if "metadata" in step_results:
        metadata_result = step_results["metadata"]
        print(f"\n📋 Metadata Step Result:")
        print(f"   Status: {metadata_result.get('status')}")
        print(f"   Duration: {metadata_result.get('duration_seconds')} seconds")

        if metadata_result.get("status") == "completed":
            print("   ✅ Metadata step completed successfully")

            # Show metadata summary stats
            summary_stats = metadata_result.get("summary_stats", {})
            if summary_stats:
                print(f"   Summary Stats: {summary_stats}")

            # Show sample outputs
            sample_outputs = metadata_result.get("sample_outputs", {})
            if sample_outputs:
                print(f"   Sample Outputs Keys: {list(sample_outputs.keys())}")
        else:
            print(f"   ❌ Metadata step failed: {metadata_result.get('error_message')}")
    else:
        print("\n📋 Metadata Step: Not found (not yet executed)")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
