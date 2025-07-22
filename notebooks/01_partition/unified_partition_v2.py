# ==============================================================================
# UNIFIED PDF PARTITIONING V2: PyMuPDF Analysis + Fast Text Extraction
# Uses PyMuPDF for table/image detection, unstructured fast for text
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
CURRENT_RUN_DIR = OUTPUT_BASE_DIR / f"unified_v2_run_{timestamp}"
TABLES_DIR = CURRENT_RUN_DIR / "tables"
IMAGES_DIR = CURRENT_RUN_DIR / "images"
PICKLE_OUTPUT_PATH = CURRENT_RUN_DIR / "unified_v2_partition_output.pkl"
JSON_OUTPUT_PATH = CURRENT_RUN_DIR / "unified_v2_partition_output.json"

# Create directories
OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_RUN_DIR.mkdir(exist_ok=True)
TABLES_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

print(f"📁 Output directory: {CURRENT_RUN_DIR}")
print(f"📁 Tables directory: {TABLES_DIR}")
print(f"📁 Images directory: {IMAGES_DIR}")
print(f"🌍 OCR Languages: {OCR_LANGUAGES}")

# ==============================================================================
# IMPROVED UNIFIED PARTITIONING PIPELINE
# ==============================================================================


class UnifiedPartitionerV2:
    """Improved unified PDF partitioning using PyMuPDF analysis + unstructured fast"""

    def __init__(self, tables_dir, images_dir):
        self.tables_dir = Path(tables_dir)
        self.images_dir = Path(images_dir)
        self.tables_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)

    def stage1_pymupdf_analysis(self, filepath):
        """Stage 1: PyMuPDF analysis to detect tables and images"""
        print("🔄 Stage 1: PyMuPDF analysis for table/image detection...")

        doc = fitz.open(filepath)
        page_analysis = {}
        table_locations = []
        image_locations = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_index = page_num + 1  # 1-indexed for consistency

            # Get images on this page
            images = page.get_images()

            # Get tables on this page (PyMuPDF table detection)
            table_finder = page.find_tables()
            tables = list(table_finder)  # Convert to list

            # Analyze page complexity
            is_fragmented = False
            if len(images) > 10:
                small_count = 0
                for img in images[:5]:  # Sample first 5 images
                    try:
                        base_image = doc.extract_image(img[0])
                        if base_image["width"] * base_image["height"] < 5000:
                            small_count += 1
                    except:
                        continue
                is_fragmented = small_count >= 3

            # Determine page complexity
            if len(images) == 0 and len(tables) == 0:
                complexity = "text_only"
                needs_extraction = False
            elif is_fragmented:
                complexity = "fragmented"
                needs_extraction = True
            elif len(images) >= 3:  # Extract if 3+ images
                complexity = "complex"
                needs_extraction = True
            elif len(images) >= 1:  # Extract if any images
                complexity = "simple"
                needs_extraction = True
            else:
                complexity = "simple"
                needs_extraction = False

            # Store page analysis
            page_analysis[page_index] = {
                "image_count": len(images),
                "table_count": len(tables),
                "complexity": complexity,
                "needs_extraction": needs_extraction,
                "is_fragmented": is_fragmented,
            }

            # Store table locations
            for i, table in enumerate(tables):
                table_bbox = table.bbox  # (x0, y0, x1, y1)
                table_locations.append(
                    {
                        "id": f"table_page{page_index}_table{i}",
                        "page": page_index,
                        "bbox": table_bbox,
                        "table_data": table,
                        "complexity": complexity,
                    }
                )
                print(f"  📊 Found table {i+1} on page {page_index}")

            # Store image locations
            for i, img in enumerate(images):
                try:
                    # Get image rectangle - use a different approach
                    img_rect = page.get_image_bbox(img)
                    if img_rect:
                        image_locations.append(
                            {
                                "id": f"image_page{page_index}_img{i}",
                                "page": page_index,
                                "bbox": img_rect,
                                "image_data": img,
                                "complexity": complexity,
                            }
                        )

                    else:
                        # Fallback: store image without bbox
                        image_locations.append(
                            {
                                "id": f"image_page{page_index}_img{i}",
                                "page": page_index,
                                "bbox": None,
                                "image_data": img,
                                "complexity": complexity,
                            }
                        )
                        print(f"  🖼️  Found image {i+1} on page {page_index} (no bbox)")
                except Exception as e:
                    # Fallback: store image without bbox
                    image_locations.append(
                        {
                            "id": f"image_page{page_index}_img{i}",
                            "page": page_index,
                            "bbox": None,
                            "image_data": img,
                            "complexity": complexity,
                        }
                    )
                    print(f"  🖼️  Found image {i+1} on page {page_index} (fallback)")

        doc.close()

        print(f"📊 PyMuPDF analysis results:")
        print(f"   Pages analyzed: {len(page_analysis)}")
        print(f"   Tables found: {len(table_locations)}")
        print(f"   Images found: {len(image_locations)}")

        # Show page-by-page breakdown
        for page_num, info in page_analysis.items():
            status = "🖼️  COMPLEX" if info["needs_extraction"] else "📝 text-focused"
            print(
                f"   Page {page_num}: {status} ({info['complexity']}) - {info['table_count']} tables, {info['image_count']} images"
            )

        return {
            "page_analysis": page_analysis,
            "table_locations": table_locations,
            "image_locations": image_locations,
        }

    def stage2_fast_text_extraction(self, filepath):
        """Stage 2: Fast unstructured extraction for text content with language support"""
        print("🔄 Stage 2: Fast text extraction with unstructured...")
        print(f"   🌍 Using languages: {OCR_LANGUAGES}")

        # Fast extraction to get text content
        fast_elements = partition_pdf(
            filename=filepath,
            strategy="fast",
            languages=OCR_LANGUAGES,  # Use configured languages for better text extraction
            max_characters=50000,
            combine_text_under_n_chars=200,
            include_metadata=True,
            include_page_breaks=True,
        )

        print(f"✅ Found {len(fast_elements)} text elements")

        # Process text elements
        text_elements = []
        raw_elements = []  # Preserve raw elements for downstream metadata access

        for i, element in enumerate(fast_elements):
            element_id = str(i + 1)  # Simple numeric ID
            category = getattr(element, "category", "Unknown")
            metadata_dict = getattr(element, "metadata", {})

            if hasattr(metadata_dict, "to_dict"):
                metadata_dict = metadata_dict.to_dict()

            page_num = metadata_dict.get("page_number", 1)

            # Store raw element for downstream access
            raw_elements.append(element)

            # Only include non-table, non-image elements in processed text
            if category not in ["Table", "Image"]:
                # Remove coordinates from metadata
                if "coordinates" in metadata_dict:
                    del metadata_dict["coordinates"]

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

        print(f"📝 Processed {len(text_elements)} text elements")
        print(f"📦 Preserved {len(raw_elements)} raw elements for metadata access")
        return text_elements, raw_elements

    def stage3_targeted_table_processing(self, filepath, table_locations):
        """Stage 3: Targeted vision processing for detected tables"""
        if not table_locations:
            print("📊 No tables detected, skipping vision processing")
            return []

        print(
            f"🔄 Stage 3: Targeted table processing ({len(table_locations)} tables)..."
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

    def stage4_full_page_extraction(self, filepath, page_analysis):
        """Stage 4: Extract full pages when images are detected (like partition_pdf.py)"""
        # Find pages that need full-page extraction
        pages_to_extract = {
            page_num: info
            for page_num, info in page_analysis.items()
            if info["needs_extraction"]
        }

        if not pages_to_extract:
            print("🖼️  No pages need full-page extraction")
            return {}

        print(f"🔄 Stage 4: Full page extraction ({len(pages_to_extract)} pages)...")

        extracted_pages = {}
        pdf_basename = Path(filepath).stem
        doc = fitz.open(filepath)

        for page_num, info in pages_to_extract.items():
            try:
                # Get page (PyMuPDF is 0-indexed)
                page = doc[page_num - 1]

                # Determine matrix based on complexity
                if info["is_fragmented"]:
                    matrix = fitz.Matrix(3, 3)  # Higher DPI for fragmented
                elif info["complexity"] == "complex":
                    matrix = fitz.Matrix(2, 2)  # Standard high DPI
                else:
                    matrix = fitz.Matrix(1.5, 1.5)  # Lower DPI for simple

                # Extract full page
                pixmap = page.get_pixmap(matrix=matrix)

                # Save image
                filename = f"{pdf_basename}_page{page_num:02d}_{info['complexity']}.png"
                save_path = self.images_dir / filename
                pixmap.save(str(save_path))

                extracted_pages[page_num] = {
                    "filepath": str(save_path),
                    "filename": filename,
                    "width": pixmap.width,
                    "height": pixmap.height,
                    "dpi": int(matrix.a * 72),  # Convert matrix to DPI
                    "complexity": info["complexity"],
                    "original_image_count": info["image_count"],
                    "original_table_count": info["table_count"],
                }

                print(f"  ✅ Page {page_num}: {filename} ({info['complexity']})")

            except Exception as e:
                print(f"  ❌ Error extracting page {page_num}: {e}")

        doc.close()
        print(f"✅ Extracted {len(extracted_pages)} full pages")
        return extracted_pages

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


# ==============================================================================
# MAIN PROCESSING
# ==============================================================================


def process_pdf_unified_v2(filepath):
    """Process PDF using improved unified approach"""
    print(f"\n🔄 Processing: {os.path.basename(filepath)}")

    # Initialize partitioner
    partitioner = UnifiedPartitionerV2(TABLES_DIR, IMAGES_DIR)

    # Stage 1: PyMuPDF analysis
    stage1_results = partitioner.stage1_pymupdf_analysis(filepath)

    # Stage 2: Fast text extraction
    text_elements, raw_elements = partitioner.stage2_fast_text_extraction(filepath)

    # Stage 3: Targeted table processing
    enhanced_tables = partitioner.stage3_targeted_table_processing(
        filepath, stage1_results["table_locations"]
    )

    # Stage 4: Full page extraction
    extracted_pages = partitioner.stage4_full_page_extraction(
        filepath, stage1_results["page_analysis"]
    )

    # Clean up data for pickle serialization
    def clean_for_pickle(obj):
        """Remove non-serializable objects"""
        if isinstance(obj, dict):
            cleaned = {}
            for key, value in obj.items():
                if key in ["image_data", "table_data"]:  # Skip PyMuPDF objects
                    continue
                cleaned[key] = clean_for_pickle(value)
            return cleaned
        elif isinstance(obj, list):
            return [clean_for_pickle(item) for item in obj]
        else:
            return obj

    # Combine all results
    combined_data = {
        "text_elements": text_elements,
        "table_elements": enhanced_tables,
        "raw_elements": raw_elements,  # Preserve raw elements for downstream metadata access
        "extracted_pages": extracted_pages,
        "table_locations": clean_for_pickle(stage1_results["table_locations"]),
        "image_locations": clean_for_pickle(stage1_results["image_locations"]),
        "page_analysis": stage1_results["page_analysis"],
        "metadata": {
            "processing_strategy": "unified_v2_pymupdf_fast",
            "timestamp": datetime.now().isoformat(),
            "source_file": os.path.basename(filepath),
            "text_count": len(text_elements),
            "raw_count": len(raw_elements),
            "table_count": len(stage1_results["table_locations"]),
            "image_count": len(stage1_results["image_locations"]),
            "enhanced_tables": len(enhanced_tables),
            "extracted_pages": len(extracted_pages),
            "pages_analyzed": len(stage1_results["page_analysis"]),
        },
    }

    return combined_data


# ==============================================================================
# SAVING FUNCTIONS
# ==============================================================================


def save_unified_v2_data(combined_data, pickle_path, json_path):
    """Save unified v2 data in both pickle and JSON formats"""

    print(f"💾 Saving unified v2 data...")

    # Save pickle file (primary data transfer)
    with open(pickle_path, "wb") as f:
        pickle.dump(combined_data, f)

    print(f"✅ Saved complete data to: {pickle_path}")

    # Save JSON file (human-readable metadata with full text)
    json_data = {
        "metadata": combined_data["metadata"],
        "summary": {
            "text_elements": len(combined_data["text_elements"]),
            "table_elements": len(combined_data["table_elements"]),
            "raw_elements": len(combined_data["raw_elements"]),
            "extracted_pages": len(combined_data["extracted_pages"]),
            "table_locations": len(combined_data["table_locations"]),
            "image_locations": len(combined_data["image_locations"]),
            "pages_analyzed": len(combined_data["page_analysis"]),
        },
        "text_elements": [
            {
                "id": elem["id"],
                "type": elem["element"].__class__.__name__,
                "category": elem["category"],
                "text": elem["text"],  # Full text, not preview
                "page": elem["page"],
                "metadata": elem["metadata"],
            }
            for elem in combined_data["text_elements"]
        ],
        "table_locations": [
            {
                "id": loc["id"],
                "page": loc["page"],
                "complexity": loc["complexity"],
            }
            for loc in combined_data["table_locations"]
        ],
        "image_locations": [
            {
                "id": loc["id"],
                "page": loc["page"],
                "complexity": loc["complexity"],
            }
            for loc in combined_data["image_locations"]
        ],
        "page_analysis": {
            str(page_num): {
                "complexity": info["complexity"],
                "table_count": info["table_count"],
                "image_count": info["image_count"],
                "needs_extraction": info["needs_extraction"],
            }
            for page_num, info in combined_data["page_analysis"].items()
        },
        "extracted_pages": {
            str(page_num): {
                "filename": info["filename"],
                "page": page_num,
                "complexity": info["complexity"],
                "dimensions": f"{info['width']}x{info['height']}",
                "dpi": info["dpi"],
                "original_image_count": info["original_image_count"],
                "original_table_count": info["original_table_count"],
            }
            for page_num, info in combined_data["extracted_pages"].items()
        },
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved metadata to: {json_path}")


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

if __name__ == "__main__":
    print("🚀 UNIFIED PDF PARTITIONING V2 PIPELINE")
    print("=" * 50)
    print("Strategy: PyMuPDF analysis + Fast text extraction")
    print(f"🌍 OCR Languages: {OCR_LANGUAGES}")
    print(f"Processing: {len(FILES_TO_PROCESS)} file(s)")

    for filename in FILES_TO_PROCESS:
        filepath = os.path.join(PDF_SOURCE_DIR, filename)

        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            continue

        # Process PDF with improved unified approach
        combined_data = process_pdf_unified_v2(filepath)

        # Save results
        save_unified_v2_data(combined_data, PICKLE_OUTPUT_PATH, JSON_OUTPUT_PATH)

        # Show summary
        print(f"\n📊 UNIFIED V2 PROCESSING SUMMARY:")
        print(f"   📄 Source file: {filename}")
        print(f"   📝 Text elements: {combined_data['metadata']['text_count']}")
        print(f"   📦 Raw elements: {combined_data['metadata']['raw_count']}")
        print(f"   📊 Tables detected: {combined_data['metadata']['table_count']}")
        print(f"   🖼️  Images detected: {combined_data['metadata']['image_count']}")
        print(f"   🔍 Enhanced tables: {combined_data['metadata']['enhanced_tables']}")
        print(f"   💾 Extracted pages: {combined_data['metadata']['extracted_pages']}")
        print(f"   📄 Pages analyzed: {combined_data['metadata']['pages_analyzed']}")

        print(f"\n📁 Output Files Created:")
        print(f"   📂 Run directory: {CURRENT_RUN_DIR}")
        print(f"   📂 Tables: {TABLES_DIR}")
        print(f"   📂 Images: {IMAGES_DIR}")
        print(f"   📄 Unified v2 data (pickle): {PICKLE_OUTPUT_PATH}")
        print(f"   📄 Unified v2 metadata (JSON): {JSON_OUTPUT_PATH}")

        # Show extracted files
        if combined_data["extracted_pages"]:
            print(f"\n🖼️  Extracted Pages:")
            for page_num, info in combined_data["extracted_pages"].items():
                print(
                    f"   - {info['filename']} (Page {page_num}, {info['complexity']})"
                )

        table_files = list(TABLES_DIR.glob("table-*"))
        if table_files:
            print(f"\n📊 Extracted Tables:")
            for table_file in table_files:
                print(f"   - {table_file.name}")

        print(f"\n🎉 Unified v2 partitioning complete!")
        print(f"📁 Next: Use '{PICKLE_OUTPUT_PATH}' in your meta_data notebook")
        print(f"🕒 Timestamp: {timestamp}")
