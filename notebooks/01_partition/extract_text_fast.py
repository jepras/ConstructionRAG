# ==============================================================================
# FAST TEXT EXTRACTION WITH UNSTRUCTURED
# Extracts all text using strategy="fast" and outputs as JSON
# ==============================================================================
#
# ABOUT COORDINATES METADATA:
# Coordinates metadata includes bounding box information (x, y, width, height)
# for each text element. This is useful for:
# - Layout analysis and understanding document structure
# - Highlighting text in visual PDF viewers
# - Determining reading order and text flow
# - OCR accuracy assessment and debugging
# - Creating interactive PDF annotations
#
# However, coordinates can make files much larger and aren't needed for
# basic text extraction. Set INCLUDE_COORDINATES = False for smaller files.
# ==============================================================================

import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# --- PDF Parsing ---
from unstructured.partition.pdf import partition_pdf

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Load environment variables
load_dotenv()

# --- Configuration ---
PDF_SOURCE_DIR = "../../data/external/construction_pdfs"
FILES_TO_PROCESS = [
    "test-with-little-variety.pdf"
]  # Change this to process different files

# --- Processing Options ---
INCLUDE_COORDINATES = (
    False  # Set to False to exclude coordinate metadata (smaller files)
)

# Create timestamped output directory
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_BASE_DIR = Path("../../data/internal/01_partition_data")
CURRENT_RUN_DIR = OUTPUT_BASE_DIR / f"fast_text_run_{timestamp}"
JSON_OUTPUT_PATH = CURRENT_RUN_DIR / "fast_text_output.json"

# Create directories
OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_RUN_DIR.mkdir(exist_ok=True)

print(f"📁 Output directory: {CURRENT_RUN_DIR}")
print(f"📄 JSON output: {JSON_OUTPUT_PATH}")

# ==============================================================================
# TEXT EXTRACTION PIPELINE
# ==============================================================================


def element_to_dict(element, include_coordinates=True):
    """Convert an unstructured element to a dictionary"""
    result = {
        "type": type(element).__name__,
        "category": getattr(element, "category", None),
        "text": getattr(element, "text", ""),
    }

    # Add metadata if available
    if hasattr(element, "metadata"):
        metadata = element.metadata
        if hasattr(metadata, "to_dict"):
            metadata_dict = metadata.to_dict()
        elif hasattr(metadata, "__dict__"):
            metadata_dict = metadata.__dict__
        else:
            metadata_dict = str(metadata)

        # Filter out coordinates if requested
        if not include_coordinates and isinstance(metadata_dict, dict):
            # Remove coordinate-related fields
            coordinate_fields = [
                "coordinates",
                "bbox",
                "x",
                "y",
                "width",
                "height",
                "left",
                "top",
                "right",
                "bottom",
            ]
            filtered_metadata = {}
            for key, value in metadata_dict.items():
                if key.lower() not in [field.lower() for field in coordinate_fields]:
                    filtered_metadata[key] = value
            result["metadata"] = filtered_metadata
        else:
            result["metadata"] = metadata_dict

    # Add HTML format for tables
    if hasattr(element, "text_as_html"):
        result["text_as_html"] = element.text_as_html

    # Add list format for lists
    if hasattr(element, "text_as_list"):
        result["text_as_list"] = element.text_as_list

    return result


# Process each file
for filename in FILES_TO_PROCESS:
    filepath = os.path.join(PDF_SOURCE_DIR, filename)
    print(f"\n🔄 Processing: {filename}")

    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        continue

    # Extract text using fast strategy
    print("📄 Extracting text with fast strategy...")
    elements = partition_pdf(
        filename=filepath,
        strategy="fast",  # Fast extraction
        max_characters=50000,  # Maximum characters per partition
        combine_text_under_n_chars=200,  # Combine small text chunks
        include_metadata=True,  # Include page numbers, etc.
        include_page_breaks=True,  # Include page break markers
    )

    print(f"✅ Found {len(elements)} elements")

    # Convert elements to dictionaries
    elements_data = []
    element_types = {}

    for i, element in enumerate(elements):
        element_dict = element_to_dict(element, include_coordinates=INCLUDE_COORDINATES)
        element_dict["index"] = i
        elements_data.append(element_dict)

        # Count element types
        el_type = element_dict["category"]
        element_types[el_type] = element_types.get(el_type, 0) + 1

    # Calculate average length for each element type
    element_lengths = {}
    for element in elements_data:
        el_type = element["category"]
        text_length = len(element["text"])

        if el_type not in element_lengths:
            element_lengths[el_type] = {"count": 0, "total_length": 0, "lengths": []}

        element_lengths[el_type]["count"] += 1
        element_lengths[el_type]["total_length"] += text_length
        element_lengths[el_type]["lengths"].append(text_length)

    # Calculate averages and statistics
    element_stats = {}
    for el_type, data in element_lengths.items():
        avg_length = data["total_length"] / data["count"]
        min_length = min(data["lengths"])
        max_length = max(data["lengths"])

        element_stats[el_type] = {
            "count": data["count"],
            "average_length": round(avg_length, 1),
            "min_length": min_length,
            "max_length": max_length,
            "total_length": data["total_length"],
        }

    # Show element type distribution and statistics
    print(f"\n📊 Element type distribution and statistics:")
    for el_type, stats in element_stats.items():
        print(f"  {el_type}: {stats['count']} elements")
        print(f"    Average length: {stats['average_length']} chars")
        print(f"    Length range: {stats['min_length']} - {stats['max_length']} chars")
        print(f"    Total length: {stats['total_length']} chars")

    # Create output data structure
    output_data = {
        "metadata": {
            "pipeline_stage": "fast_text_extraction",
            "timestamp": datetime.now().isoformat(),
            "source_file": filename,
            "strategy": "fast",
            "max_characters": 50000,
            "combine_text_under_n_chars": 200,
            "include_coordinates": INCLUDE_COORDINATES,
            "total_elements": len(elements),
            "element_types": element_types,
            "element_statistics": element_stats,
        },
        "elements": elements_data,
    }

    # Save to JSON
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved text extraction to: {JSON_OUTPUT_PATH}")

    # Show text preview
    print(f"\n📝 Text Preview (first 3 elements):")
    for i, element in enumerate(elements_data[:3]):
        text_preview = (
            element["text"][:200] + "..."
            if len(element["text"]) > 200
            else element["text"]
        )
        print(f"  Element {i+1} ({element['category']}): {text_preview}")

print(f"\n🎉 Fast Text Extraction Complete!")
print(f"   📄 Processed: {len(FILES_TO_PROCESS)} file(s)")
print(f"   📁 Output: {JSON_OUTPUT_PATH}")
print(f"   🕒 Timestamp: {timestamp}")
