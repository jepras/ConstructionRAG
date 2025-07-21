# --- Core Libraries ---
import os
from datetime import datetime
from dotenv import load_dotenv
from pdf2image import convert_from_path
import fitz  # PyMuPDF
from pathlib import Path

# --- PDF Parsing ---
from unstructured.partition.pdf import partition_pdf

# ==============================================================================
# 1. DEFINE PAGE EXTRACTOR
# ==============================================================================


class VLMPageExtractor:
    """Extracts full pages for image-rich content with intelligent complexity detection"""

    def __init__(self, output_dir="vlm_pages", high_quality_dpi=300, standard_dpi=200):
        self.output_dir = Path(output_dir)
        self.high_quality_dpi = high_quality_dpi
        self.standard_dpi = standard_dpi
        self.output_dir.mkdir(exist_ok=True)

    def analyze_pdf_for_image_pages(self, pdf_path):
        """Analyze PDF structure to identify pages needing full-page extraction"""
        doc = fitz.open(pdf_path)
        page_analysis = {}

        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images()

            # Detect fragmentation pattern
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

            # Determine extraction strategy
            if len(images) == 0:
                complexity = "text_only"
                needs_full_page = False
            elif is_fragmented:
                complexity = "fragmented"
                needs_full_page = True
            elif len(images) >= 3:
                complexity = "complex"
                needs_full_page = True
            else:
                complexity = "simple"
                needs_full_page = False

            page_analysis[page_num + 1] = {
                "image_count": len(images),
                "complexity": complexity,
                "needs_full_page_extraction": needs_full_page,
                "is_fragmented": is_fragmented,
            }

        doc.close()
        return page_analysis

    def extract_image_rich_pages(self, pdf_path, page_analysis):
        """Extract full pages as high-quality images for VLM processing"""
        pages_to_extract = {
            page_num: info
            for page_num, info in page_analysis.items()
            if info["needs_full_page_extraction"]
        }

        if not pages_to_extract:
            return {}

        extracted_pages = {}
        pdf_basename = Path(pdf_path).stem

        print(f"📄 Extracting {len(pages_to_extract)} image-rich pages...")

        for page_num, info in pages_to_extract.items():
            try:
                # Use high DPI for fragmented pages, standard for complex
                dpi = (
                    self.high_quality_dpi
                    if info["is_fragmented"]
                    else self.standard_dpi
                )

                page_images = convert_from_path(
                    pdf_path, first_page=page_num, last_page=page_num, dpi=dpi
                )

                if page_images:
                    filename = (
                        f"{pdf_basename}_page{page_num:02d}_{info['complexity']}.png"
                    )
                    filepath = self.output_dir / filename
                    page_images[0].save(filepath, "PNG", optimize=False)

                    extracted_pages[page_num] = {
                        "filepath": str(filepath),
                        "filename": filename,
                        "width": page_images[0].width,
                        "height": page_images[0].height,
                        "dpi": dpi,
                        "complexity": info["complexity"],
                        "original_image_count": info["image_count"],
                    }

                    print(f"  ✅ Page {page_num}: {filename} ({info['complexity']})")

            except Exception as e:
                print(f"  ❌ Page {page_num}: Error - {e}")

        return extracted_pages


print("✅ Page extractor defined.")

# ==============================================================================
# 2. LOAD ENVIRONMENT & CONFIGURATION
# ==============================================================================
load_dotenv()

# --- Configuration ---
PDF_SOURCE_DIR = "../../data/external/construction_pdfs"
FILES_TO_PROCESS = ["test-with-little-variety.pdf"]  # Updated to your test file
OCR_LANGUAGES = ["dan"]

# Create timestamped output directory
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_BASE_DIR = Path("../../data/internal/01_partition_data")
CURRENT_RUN_DIR = OUTPUT_BASE_DIR / f"01_run_{timestamp}"
VLM_PAGES_DIR = CURRENT_RUN_DIR / "vlm_pages"
TABLES_DIR = CURRENT_RUN_DIR / "tables"
PICKLE_OUTPUT_PATH = CURRENT_RUN_DIR / "partition_data_output.pkl"
JSON_OUTPUT_PATH = CURRENT_RUN_DIR / "partition_data_output.json"

# Create directories
OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_RUN_DIR.mkdir(exist_ok=True)
VLM_PAGES_DIR.mkdir(exist_ok=True)
TABLES_DIR.mkdir(exist_ok=True)

print(f"📁 Output directory: {CURRENT_RUN_DIR}")
print(f"📁 VLM pages directory: {VLM_PAGES_DIR}")
print(f"📁 Tables directory: {TABLES_DIR}")

print("✅ Configuration loaded.")

# ==============================================================================
# 3. PDF PARTITIONING PIPELINE
# ==============================================================================

filepath = os.path.join(PDF_SOURCE_DIR, FILES_TO_PROCESS[0])
print(f"\n🔄 Processing: {os.path.basename(filepath)}")

# --- Step 1: Quick Analysis with PyMuPDF ---
print("📊 Step 1: Analyzing PDF structure for image content...")
page_extractor = VLMPageExtractor(output_dir=VLM_PAGES_DIR)
page_analysis = page_extractor.analyze_pdf_for_image_pages(filepath)

print("📋 Page Analysis Results:")
for page_num, info in page_analysis.items():
    status = (
        f"🖼️  IMAGE-RICH" if info["needs_full_page_extraction"] else "📝 text-focused"
    )
    print(
        f"  Page {page_num}: {status} ({info['complexity']}) - {info['image_count']} images"
    )

# --- Step 2: Extract Image-Rich Pages ---
extracted_pages = page_extractor.extract_image_rich_pages(filepath, page_analysis)

# --- Step 3: Unstructured Processing (Table Extraction Only) ---
print(f"\n📄 Step 2: Unstructured processing for text/tables...")
raw_pdf_elements = partition_pdf(
    filename=filepath,
    strategy="hi_res",
    languages=OCR_LANGUAGES,
    extract_images_in_pdf=True,  # Required for extract_image_block_types to work
    extract_image_block_types=["Table"],  # Only extract table blocks
    extract_image_block_output_dir=str(TABLES_DIR),  # Save tables to tables directory
    extract_image_block_to_payload=False,  # Save to files, not payload
    # Enhanced table extraction parameters
    infer_table_structure=True,  # Try to infer table structure
    # Table-specific OCR improvements
    pdf_infer_table_structure=True,  # PDF-specific table inference
)

print(f"✅ Found {len(raw_pdf_elements)} text/table elements")

# --- Filter Extracted Files (Keep only tables, remove figures) ---
print(f"\n🔧 Filtering extracted files...")
all_extracted_files = list(TABLES_DIR.glob("*"))
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
    f"📊 Filtering results: {tables_kept} tables kept, {figures_removed} figures removed"
)

# --- Enhanced Table Inspection ---
import json


def element_to_dict(element):
    """Convert an unstructured element to a dictionary with enhanced table attributes"""
    result = {
        "type": type(element).__name__,
        "category": getattr(element, "category", None),
    }

    # Add text content
    if hasattr(element, "text"):
        result["text"] = element.text

    # Add metadata - convert to dict if it's an object
    if hasattr(element, "metadata"):
        metadata = element.metadata
        if hasattr(metadata, "to_dict"):
            result["metadata"] = metadata.to_dict()
        elif hasattr(metadata, "__dict__"):
            result["metadata"] = metadata.__dict__
        else:
            result["metadata"] = str(metadata)

    # Add standard table attributes
    if hasattr(element, "text_as_html"):
        result["text_as_html"] = element.text_as_html

    if hasattr(element, "text_as_list"):
        result["text_as_list"] = element.text_as_list

    # Add enhanced table-specific attributes that might be available with new parameters
    enhanced_table_attrs = [
        "table_as_cells",
        "table_cells",
        "rows",
        "columns",
        "structured_data",
        "table_data",
        "cells",
        "table_structure",
        "column_headers",
        "row_data",
    ]
    for attr in enhanced_table_attrs:
        if hasattr(element, attr):
            result[attr] = getattr(element, attr)

    # Check for any attribute containing "table" in the name
    for attr_name in dir(element):
        if (
            not attr_name.startswith("_")
            and "table" in attr_name.lower()
            and attr_name not in result
        ):
            try:
                attr_value = getattr(element, attr_name)
                if attr_value is not None and not callable(attr_value):
                    result[attr_name] = attr_value
            except:
                pass

    return result


# Show element type distribution
element_types = {}
for el in raw_pdf_elements:
    el_type = type(el).__name__
    element_types[el_type] = element_types.get(el_type, 0) + 1

print(f"\n📊 Element type distribution:")
for el_type, count in element_types.items():
    print(f"  {el_type}: {count}")

# --- Enhanced Table Elements JSON Inspection ---
table_elements = [
    el for el in raw_pdf_elements if getattr(el, "category", None) == "Table"
]
if table_elements:
    print(f"\n📊 ENHANCED TABLE INSPECTION ({len(table_elements)} tables found):")
    for i, table in enumerate(table_elements):
        print(f"\n--- Table {i+1} ---")
        table_dict = element_to_dict(table)
        print(json.dumps(table_dict, indent=2, default=str))

        # Additional inspection - show all attributes
        print(
            f"\nAll table attributes: {[attr for attr in dir(table) if not attr.startswith('_')]}"
        )
else:
    print(f"\n📊 No tables found in the document.")

# --- Save Results ---
import pickle
import json

data_to_save = {
    "raw_elements": raw_pdf_elements,
    "extracted_pages": extracted_pages,
    "page_analysis": page_analysis,
    "filepath": filepath,
}

# Save pickle file (primary data transfer)
with open(PICKLE_OUTPUT_PATH, "wb") as f:
    pickle.dump(data_to_save, f)

print(f"✅ Saved partition data to: {PICKLE_OUTPUT_PATH}")


# Save JSON file (human-readable metadata)
def save_partition_data_json(data_to_save, output_path):
    """Save partition data as human-readable JSON"""
    json_data = {
        "metadata": {
            "pipeline_stage": "partition",
            "timestamp": datetime.now().isoformat(),
            "source_file": os.path.basename(data_to_save["filepath"]),
            "total_elements": len(data_to_save["raw_elements"]),
            "extracted_pages": len(data_to_save["extracted_pages"]),
            "analyzed_pages": len(data_to_save["page_analysis"]),
        },
        "elements_summary": [
            {
                "index": i,
                "category": getattr(el, "category", "Unknown"),
                "text_preview": (
                    getattr(el, "text", "")[:200] + "..."
                    if len(getattr(el, "text", "")) > 200
                    else getattr(el, "text", "")
                ),
                "page_number": getattr(
                    getattr(el, "metadata", {}), "page_number", "Unknown"
                ),
            }
            for i, el in enumerate(data_to_save["raw_elements"])
        ],
        "extracted_pages": data_to_save["extracted_pages"],
        "page_analysis": data_to_save["page_analysis"],
    }

    with open(output_path, "w") as f:
        json.dump(json_data, f, indent=2)


save_partition_data_json(data_to_save, JSON_OUTPUT_PATH)
print(f"✅ Saved partition metadata to: {JSON_OUTPUT_PATH}")

print(f"\n📊 Processing Summary:")
print(f"  Total pages: {len(page_analysis)}")
print(f"  Image-rich pages (VLM): {len(extracted_pages)}")
print(f"  Text/table elements: {len(raw_pdf_elements)}")

print(f"\n🎉 PDF Partitioning Pipeline Complete!")
print(f"   📊 Successfully processed {len(page_analysis)} pages")
print(f"   🖼️  Extracted {len(extracted_pages)} image-rich pages")
print(f"   📝 Found {len(raw_pdf_elements)} text/table elements")

print(f"\n📁 Output Files Created:")
print(f"   📂 Run directory: {CURRENT_RUN_DIR}")
print(f"   📂 VLM pages: {VLM_PAGES_DIR}")
print(f"   📂 Tables: {TABLES_DIR}")
print(f"   📄 Partition data (pickle): {PICKLE_OUTPUT_PATH}")
print(f"   📄 Partition metadata (JSON): {JSON_OUTPUT_PATH}")
if extracted_pages:
    print(f"   🖼️  Extracted page images:")
    for page_num, info in extracted_pages.items():
        print(f"      - {info['filename']}")

# Check for extracted figures/tables
figures_list = list(TABLES_DIR.glob("*"))
if figures_list:
    print(f"   📊 Extracted tables ({len(figures_list)} files):")
    for fig_file in figures_list:
        print(f"      - {fig_file.name}")
else:
    print(f"   📊 No tables extracted")

print(f"   🕒 Timestamp: {timestamp}")
print(f"\n📁 Next: Use '{PICKLE_OUTPUT_PATH}' in your meta_data notebook")
