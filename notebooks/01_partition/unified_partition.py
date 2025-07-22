# ==============================================================================
# UNIFIED PDF PARTITIONING: Fast + Vision Strategy
# Combines speed of fast extraction with precision of vision processing
# ==============================================================================

import os
import json
import pickle
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# --- Core Libraries ---
from unstructured.partition.pdf import partition_pdf
import fitz  # PyMuPDF
from pdf2image import convert_from_path

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
INCLUDE_COORDINATES = True  # Include coordinate metadata for location detection
OCR_LANGUAGES = ["dan"]  # Danish language support

# Create timestamped output directory
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_BASE_DIR = Path("../../data/internal/01_partition_data")
CURRENT_RUN_DIR = OUTPUT_BASE_DIR / f"unified_run_{timestamp}"
TABLES_DIR = CURRENT_RUN_DIR / "tables"
IMAGES_DIR = CURRENT_RUN_DIR / "images"
PICKLE_OUTPUT_PATH = CURRENT_RUN_DIR / "unified_partition_output.pkl"
JSON_OUTPUT_PATH = CURRENT_RUN_DIR / "unified_partition_output.json"

# Create directories
OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_RUN_DIR.mkdir(exist_ok=True)
TABLES_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

print(f"📁 Output directory: {CURRENT_RUN_DIR}")
print(f"📁 Tables directory: {TABLES_DIR}")
print(f"📁 Images directory: {IMAGES_DIR}")

# ==============================================================================
# UNIFIED PARTITIONING PIPELINE
# ==============================================================================


class UnifiedPartitioner:
    """Unified PDF partitioning combining fast extraction with targeted vision processing"""

    def __init__(self, tables_dir, images_dir):
        self.tables_dir = Path(tables_dir)
        self.images_dir = Path(images_dir)
        self.tables_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)

    def stage1_fast_location_detection(self, filepath):
        """Stage 1: Fast analysis to detect tables and images"""
        print("🔄 Stage 1: Fast location detection...")

        # Fast extraction to get overview
        fast_elements = partition_pdf(
            filename=filepath,
            strategy="fast",
            max_characters=50000,
            combine_text_under_n_chars=200,
            include_metadata=True,
            include_page_breaks=True,
        )

        print(f"✅ Found {len(fast_elements)} elements in fast analysis")

        # Identify table and image locations
        table_locations = []
        image_locations = []
        text_elements = []

        for i, element in enumerate(fast_elements):
            element_id = f"fast_element_{i}"
            category = getattr(element, "category", "Unknown")
            metadata_dict = getattr(element, "metadata", {})

            if hasattr(metadata_dict, "to_dict"):
                metadata_dict = metadata_dict.to_dict()

            page_num = metadata_dict.get("page_number", 1)
            coordinates = metadata_dict.get("coordinates", None)

            if category == "Table":
                table_locations.append(
                    {
                        "id": element_id,
                        "page": page_num,
                        "bbox": coordinates,
                        "element": element,
                        "text": getattr(element, "text", ""),
                        "html": getattr(element, "text_as_html", None),
                    }
                )
                print(f"  📊 Found table on page {page_num}")

            elif (
                hasattr(metadata_dict, "image_filepath") or "image" in category.lower()
            ):
                image_locations.append(
                    {
                        "id": element_id,
                        "page": page_num,
                        "bbox": coordinates,
                        "element": element,
                        "text": getattr(element, "text", ""),
                        "image_filepath": metadata_dict.get("image_filepath", None),
                    }
                )
                print(f"  🖼️  Found image on page {page_num}")

            else:
                # Regular text element
                text_elements.append(
                    {
                        "id": element_id,
                        "element": element,
                        "category": category,
                        "page": page_num,
                        "text": getattr(element, "text", ""),
                        "metadata": metadata_dict,
                    }
                )

        print(f"📊 Location detection results:")
        print(f"   Text elements: {len(text_elements)}")
        print(f"   Tables found: {len(table_locations)}")
        print(f"   Images found: {len(image_locations)}")

        return {
            "fast_elements": fast_elements,
            "text_elements": text_elements,
            "table_locations": table_locations,
            "image_locations": image_locations,
        }

    def stage2_targeted_table_processing(self, filepath, table_locations):
        """Stage 2: Targeted vision processing for detected tables"""
        if not table_locations:
            print("📊 No tables detected, skipping vision processing")
            return []

        print(
            f"🔄 Stage 2: Targeted table processing ({len(table_locations)} tables)..."
        )

        # Process tables with vision capabilities
        table_elements = partition_pdf(
            filename=filepath,
            strategy="hi_res",
            languages=OCR_LANGUAGES,
            extract_images_in_pdf=True,
            extract_image_block_types=["Table"],
            extract_image_block_output_dir=str(self.tables_dir),
            extract_image_block_to_payload=False,
            infer_table_structure=True,
            pdf_infer_table_structure=True,
        )

        # Filter to keep only table elements
        enhanced_tables = []
        for element in table_elements:
            if getattr(element, "category", "") == "Table":
                enhanced_tables.append(element)

        print(f"✅ Enhanced {len(enhanced_tables)} tables with vision processing")

        # Clean up extracted files (keep only tables, remove figures)
        self._cleanup_extracted_files()

        return enhanced_tables

    def stage3_precise_image_extraction(self, filepath, image_locations):
        """Stage 3: Extract high-quality images based on detected locations"""
        if not image_locations:
            print("🖼️  No images detected, skipping image extraction")
            return {}

        print(
            f"🔄 Stage 3: Precise image extraction ({len(image_locations)} images)..."
        )

        extracted_images = {}
        doc = fitz.open(filepath)

        for location in image_locations:
            page_num = location["page"]
            element_id = location["id"]

            try:
                # Get page (PyMuPDF is 0-indexed)
                page = doc[page_num - 1]

                # Extract high-quality image
                # Use higher DPI for better quality
                matrix = fitz.Matrix(2, 2)  # 2x zoom for higher DPI
                pixmap = page.get_pixmap(matrix=matrix)

                # Save image
                filename = f"image_{element_id}_page{page_num:02d}.png"
                filepath = self.images_dir / filename
                pixmap.save(str(filepath))

                extracted_images[element_id] = {
                    "filepath": str(filepath),
                    "filename": filename,
                    "page": page_num,
                    "width": pixmap.width,
                    "height": pixmap.height,
                    "original_location": location,
                }

                print(f"  ✅ Extracted: {filename}")

            except Exception as e:
                print(f"  ❌ Error extracting image {element_id}: {e}")

        doc.close()
        print(f"✅ Extracted {len(extracted_images)} high-quality images")

        return extracted_images

    def _cleanup_extracted_files(self):
        """Clean up extracted files, keeping only tables"""
        print("🔧 Cleaning up extracted files...")

        all_extracted_files = list(self.tables_dir.glob("*"))
        tables_kept = 0
        figures_removed = 0

        for file_path in all_extracted_files:
            filename = file_path.name.lower()
            if filename.startswith("figure-"):
                # Remove figure files
                try:
                    file_path.unlink()
                    figures_removed += 1
                except Exception as e:
                    print(f"  ⚠️  Could not remove {file_path.name}: {e}")
            elif filename.startswith("table-"):
                # Keep table files
                tables_kept += 1
                print(f"  ✅ Kept: {file_path.name}")
            else:
                # Log other files but don't remove them
                print(f"  ℹ️  Other file: {file_path.name}")

        print(
            f"📊 Cleanup results: {tables_kept} tables kept, {figures_removed} figures removed"
        )

    def element_to_dict(self, element):
        """Convert an unstructured element to a dictionary"""
        result = {
            "type": type(element).__name__,
            "category": getattr(element, "category", None),
            "text": getattr(element, "text", ""),
        }

        # Add metadata
        if hasattr(element, "metadata"):
            metadata = element.metadata
            if hasattr(metadata, "to_dict"):
                result["metadata"] = metadata.to_dict()
            elif hasattr(metadata, "__dict__"):
                result["metadata"] = metadata.__dict__
            else:
                result["metadata"] = str(metadata)

        # Add table-specific attributes
        if hasattr(element, "text_as_html"):
            result["text_as_html"] = element.text_as_html

        if hasattr(element, "text_as_list"):
            result["text_as_list"] = element.text_as_list

        return result


# ==============================================================================
# MAIN PROCESSING
# ==============================================================================


def process_pdf_unified(filepath):
    """Process PDF using unified approach"""
    print(f"\n🔄 Processing: {os.path.basename(filepath)}")

    # Initialize partitioner
    partitioner = UnifiedPartitioner(TABLES_DIR, IMAGES_DIR)

    # Stage 1: Fast location detection
    stage1_results = partitioner.stage1_fast_location_detection(filepath)

    # Stage 2: Targeted table processing
    enhanced_tables = partitioner.stage2_targeted_table_processing(
        filepath, stage1_results["table_locations"]
    )

    # Stage 3: Precise image extraction
    extracted_images = partitioner.stage3_precise_image_extraction(
        filepath, stage1_results["image_locations"]
    )

    # Combine all results
    combined_data = {
        "fast_elements": stage1_results["fast_elements"],
        "text_elements": stage1_results["text_elements"],
        "table_elements": enhanced_tables,
        "extracted_images": extracted_images,
        "table_locations": stage1_results["table_locations"],
        "image_locations": stage1_results["image_locations"],
        "metadata": {
            "processing_strategy": "unified_fast_vision",
            "timestamp": datetime.now().isoformat(),
            "source_file": os.path.basename(filepath),
            "total_elements": len(stage1_results["fast_elements"]),
            "text_count": len(stage1_results["text_elements"]),
            "table_count": len(stage1_results["table_locations"]),
            "image_count": len(stage1_results["image_locations"]),
            "enhanced_tables": len(enhanced_tables),
            "extracted_images": len(extracted_images),
        },
    }

    return combined_data


# ==============================================================================
# SAVING FUNCTIONS
# ==============================================================================


def save_unified_data(combined_data, pickle_path, json_path):
    """Save unified data in both pickle and JSON formats"""

    print(f"💾 Saving unified data...")

    # Save pickle file (primary data transfer)
    with open(pickle_path, "wb") as f:
        pickle.dump(combined_data, f)

    print(f"✅ Saved complete data to: {pickle_path}")

    # Save JSON file (human-readable metadata)
    json_data = {
        "metadata": combined_data["metadata"],
        "summary": {
            "text_elements": len(combined_data["text_elements"]),
            "table_elements": len(combined_data["table_elements"]),
            "extracted_images": len(combined_data["extracted_images"]),
            "table_locations": len(combined_data["table_locations"]),
            "image_locations": len(combined_data["image_locations"]),
        },
        "text_elements_preview": [
            {
                "id": elem["id"],
                "category": elem["category"],
                "page": elem["page"],
                "text_preview": (
                    elem["text"][:200] + "..."
                    if len(elem["text"]) > 200
                    else elem["text"]
                ),
            }
            for elem in combined_data["text_elements"][:10]  # First 10 elements
        ],
        "table_locations": [
            {
                "id": loc["id"],
                "page": loc["page"],
                "text_preview": (
                    loc["text"][:100] + "..." if len(loc["text"]) > 100 else loc["text"]
                ),
            }
            for loc in combined_data["table_locations"]
        ],
        "image_locations": [
            {
                "id": loc["id"],
                "page": loc["page"],
                "text_preview": (
                    loc["text"][:100] + "..." if len(loc["text"]) > 100 else loc["text"]
                ),
            }
            for loc in combined_data["image_locations"]
        ],
        "extracted_images": {
            img_id: {
                "filename": info["filename"],
                "page": info["page"],
                "dimensions": f"{info['width']}x{info['height']}",
            }
            for img_id, info in combined_data["extracted_images"].items()
        },
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved metadata to: {json_path}")


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

if __name__ == "__main__":
    print("🚀 UNIFIED PDF PARTITIONING PIPELINE")
    print("=" * 50)
    print("Strategy: Fast location detection + Targeted vision processing")
    print(f"Processing: {len(FILES_TO_PROCESS)} file(s)")

    for filename in FILES_TO_PROCESS:
        filepath = os.path.join(PDF_SOURCE_DIR, filename)

        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            continue

        # Process PDF with unified approach
        combined_data = process_pdf_unified(filepath)

        # Save results
        save_unified_data(combined_data, PICKLE_OUTPUT_PATH, JSON_OUTPUT_PATH)

        # Show summary
        print(f"\n📊 UNIFIED PROCESSING SUMMARY:")
        print(f"   📄 Source file: {filename}")
        print(f"   📝 Text elements: {combined_data['metadata']['text_count']}")
        print(f"   📊 Tables detected: {combined_data['metadata']['table_count']}")
        print(f"   🖼️  Images detected: {combined_data['metadata']['image_count']}")
        print(f"   🔍 Enhanced tables: {combined_data['metadata']['enhanced_tables']}")
        print(
            f"   💾 Extracted images: {combined_data['metadata']['extracted_images']}"
        )

        print(f"\n📁 Output Files Created:")
        print(f"   📂 Run directory: {CURRENT_RUN_DIR}")
        print(f"   📂 Tables: {TABLES_DIR}")
        print(f"   📂 Images: {IMAGES_DIR}")
        print(f"   📄 Unified data (pickle): {PICKLE_OUTPUT_PATH}")
        print(f"   📄 Unified metadata (JSON): {JSON_OUTPUT_PATH}")

        # Show extracted files
        if combined_data["extracted_images"]:
            print(f"\n🖼️  Extracted Images:")
            for img_id, info in combined_data["extracted_images"].items():
                print(f"   - {info['filename']} (Page {info['page']})")

        table_files = list(TABLES_DIR.glob("table-*"))
        if table_files:
            print(f"\n📊 Extracted Tables:")
            for table_file in table_files:
                print(f"   - {table_file.name}")

        print(f"\n🎉 Unified partitioning complete!")
        print(f"📁 Next: Use '{PICKLE_OUTPUT_PATH}' in your meta_data notebook")
        print(f"🕒 Timestamp: {timestamp}")
