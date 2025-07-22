#!/usr/bin/env python3
"""
Test script to verify unified v2 integration with metadata pipeline
"""

import os
import sys
import pickle
from pathlib import Path

# Add the notebooks directory to the path
sys.path.append("notebooks/01_partition")
sys.path.append("notebooks/02_meta_data")


def test_unified_v2_output():
    """Test that unified v2 preserves raw elements"""
    print("🧪 Testing Unified V2 Output Structure")
    print("=" * 50)

    # Look for the most recent unified v2 run
    partition_data_dir = Path("data/internal/01_partition_data")
    if not partition_data_dir.exists():
        print("❌ Partition data directory not found")
        return False

    # Find the most recent unified v2 run
    unified_runs = list(partition_data_dir.glob("unified_v2_run_*"))
    if not unified_runs:
        print("❌ No unified v2 runs found")
        return False

    latest_run = max(unified_runs, key=lambda x: x.stat().st_mtime)
    print(f"📁 Testing latest run: {latest_run.name}")

    # Check for the pickle file
    pickle_file = latest_run / "unified_v2_partition_output.pkl"
    if not pickle_file.exists():
        print(f"❌ Pickle file not found: {pickle_file}")
        return False

    # Load the data
    try:
        with open(pickle_file, "rb") as f:
            data = pickle.load(f)

        print(f"✅ Successfully loaded unified v2 data")
        print(f"📊 Data keys: {list(data.keys())}")

        # Check for required keys
        required_keys = [
            "text_elements",
            "table_elements",
            "raw_elements",
            "extracted_pages",
        ]
        missing_keys = [key for key in required_keys if key not in data]

        if missing_keys:
            print(f"❌ Missing required keys: {missing_keys}")
            return False

        print(f"✅ All required keys present")

        # Check data counts
        metadata = data.get("metadata", {})
        print(f"\n📈 Data Summary:")
        print(f"  📝 Text elements: {metadata.get('text_count', 0)}")
        print(f"  📦 Raw elements: {metadata.get('raw_count', 0)}")
        print(f"  📊 Table elements: {len(data.get('table_elements', []))}")
        print(f"  🖼️  Extracted pages: {len(data.get('extracted_pages', {}))}")

        # Check that raw elements contain the original unstructured elements
        raw_elements = data.get("raw_elements", [])
        if raw_elements:
            sample_raw = raw_elements[0]
            print(f"\n🔍 Sample raw element type: {type(sample_raw)}")
            print(f"  Has text: {hasattr(sample_raw, 'text')}")
            print(f"  Has metadata: {hasattr(sample_raw, 'metadata')}")
            print(f"  Has text_as_html: {hasattr(sample_raw, 'text_as_html')}")

            # Check metadata for image_path
            if hasattr(sample_raw, "metadata"):
                metadata_dict = sample_raw.metadata
                if hasattr(metadata_dict, "to_dict"):
                    metadata_dict = metadata_dict.to_dict()
                print(f"  Has image_path in metadata: {'image_path' in metadata_dict}")

        # Check table elements for enhanced metadata
        table_elements = data.get("table_elements", [])
        if table_elements:
            sample_table = table_elements[0]
            print(f"\n📊 Sample table element:")
            print(f"  Type: {type(sample_table)}")
            print(f"  Has text_as_html: {hasattr(sample_table, 'text_as_html')}")

            if hasattr(sample_table, "metadata"):
                table_metadata = sample_table.metadata
                if hasattr(table_metadata, "to_dict"):
                    table_metadata = table_metadata.to_dict()
                print(f"  Has image_path: {'image_path' in table_metadata}")
                print(f"  Has text_as_html: {'text_as_html' in table_metadata}")

        print(f"\n✅ Unified V2 output structure test PASSED!")
        return True

    except Exception as e:
        print(f"❌ Error testing unified v2 output: {e}")
        return False


def test_metadata_compatibility():
    """Test that metadata pipeline can handle the new structure"""
    print(f"\n🧪 Testing Metadata Pipeline Compatibility")
    print("=" * 50)

    try:
        # Import the metadata functions
        from meta_data_unified import (
            load_unified_partition_data,
            add_structural_awareness_unified,
        )

        # Look for the most recent unified v2 run
        partition_data_dir = Path("data/internal/01_partition_data")
        unified_runs = list(partition_data_dir.glob("unified_v2_run_*"))
        if not unified_runs:
            print("❌ No unified v2 runs found for metadata test")
            return False

        latest_run = max(unified_runs, key=lambda x: x.stat().st_mtime)
        pickle_file = latest_run / "unified_v2_partition_output.pkl"

        # Test loading
        print(f"📂 Loading from: {pickle_file}")
        unified_data = load_unified_partition_data(str(pickle_file))

        if not unified_data:
            print("❌ Failed to load unified data")
            return False

        print(f"✅ Successfully loaded unified data")
        print(f"📊 Data keys: {list(unified_data.keys())}")

        # Test structural awareness processing
        print(f"\n🏗️ Testing structural awareness processing...")
        enriched_elements = add_structural_awareness_unified(unified_data)

        print(f"✅ Successfully processed {len(enriched_elements)} enriched elements")

        # Check element types
        element_types = {}
        for element in enriched_elements:
            element_type = element.get("element_type", "unknown")
            element_types[element_type] = element_types.get(element_type, 0) + 1

        print(f"\n📋 Enriched element types:")
        for element_type, count in element_types.items():
            print(f"  {element_type}: {count}")

        print(f"\n✅ Metadata pipeline compatibility test PASSED!")
        return True

    except Exception as e:
        print(f"❌ Error testing metadata compatibility: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Testing Unified V2 Integration")
    print("=" * 60)

    # Test 1: Unified V2 output structure
    test1_passed = test_unified_v2_output()

    # Test 2: Metadata pipeline compatibility
    test2_passed = test_metadata_compatibility()

    print(f"\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY:")
    print(
        f"  Unified V2 Output Structure: {'✅ PASSED' if test1_passed else '❌ FAILED'}"
    )
    print(
        f"  Metadata Pipeline Compatibility: {'✅ PASSED' if test2_passed else '❌ FAILED'}"
    )

    if test1_passed and test2_passed:
        print(f"\n🎉 All tests PASSED! Unified V2 integration is working correctly.")
    else:
        print(f"\n⚠️  Some tests FAILED. Please check the issues above.")
