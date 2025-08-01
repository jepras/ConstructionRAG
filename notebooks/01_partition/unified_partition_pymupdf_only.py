# ==============================================================================
# UNIFIED PDF PARTITIONING: PyMuPDF ONLY VERSION
# Uses PyMuPDF for text extraction, table detection, and image extraction
# No unstructured dependencies - lightweight and Docker-friendly
# ==============================================================================

import os
import json
import pickle
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from collections import Counter

# --- Core Libraries ---
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
OCR_LANGUAGES = ["dan"]  # Danish language support (for future OCR integration)

# Create timestamped output directory
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_BASE_DIR = Path("../../data/internal/01_partition_data")
CURRENT_RUN_DIR = OUTPUT_BASE_DIR / f"01_run_pymupdf_{timestamp}"
TABLES_DIR = CURRENT_RUN_DIR / "tables"
IMAGES_DIR = CURRENT_RUN_DIR / "images"
PICKLE_OUTPUT_PATH = CURRENT_RUN_DIR / "pymupdf_only_partition_output.pkl"
JSON_OUTPUT_PATH = CURRENT_RUN_DIR / "pymupdf_only_partition_output.json"

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
# PYMUPDF-ONLY PARTITIONING PIPELINE
# ==============================================================================


class PyMuPDFOnlyPartitioner:
    """PyMuPDF-only PDF partitioning - no unstructured dependencies"""

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

        # Extract document metadata
        document_metadata = self._extract_document_metadata(doc)

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
                    # Get image rectangle
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
            "document_metadata": document_metadata,
        }

    def stage2_pymupdf_text_extraction(self, filepath):
        """Stage 2: PyMuPDF text extraction with metadata preservation"""
        print("🔄 Stage 2: PyMuPDF text extraction...")

        doc = fitz.open(filepath)
        text_elements = []
        raw_elements = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_index = page_num + 1

            # Extract text blocks with metadata
            text_dict = page.get_text("dict")

            # Process text blocks
            for block in text_dict.get("blocks", []):
                if "lines" in block:  # Text block
                    block_text = ""
                    block_bbox = block.get("bbox", [0, 0, 0, 0])

                    # Combine all lines in the block
                    for line in block["lines"]:
                        for span in line.get("spans", []):
                            block_text += span.get("text", "")

                    # Skip empty blocks
                    if not block_text.strip():
                        continue

                    # Create element with metadata similar to unstructured format
                    element_id = f"text_page{page_index}_block{len(text_elements)}"

                    # Determine category based on text characteristics
                    category = self._determine_text_category(block_text, block)

                    # Create metadata similar to unstructured format (without coordinates)
                    metadata = {
                        "page_number": page_index,
                        "font_size": self._get_font_size(block),
                        "font_name": self._get_font_name(block),
                        "is_bold": self._is_bold_text(block),
                        "extraction_method": "pymupdf_text_dict",
                    }

                    # Create element object similar to unstructured format
                    element = self._create_text_element(block_text, category, metadata)

                    # Store raw element
                    raw_elements.append(element)

                    # Only include non-table, non-image elements in processed text
                    if category not in ["Table", "Image"]:
                        text_elements.append(
                            {
                                "id": element_id,
                                "element": element,
                                "category": category,
                                "page": page_index,
                                "text": block_text,
                                "metadata": metadata,
                            }
                        )

        doc.close()

        print(f"📝 Processed {len(text_elements)} text elements")
        print(f"📦 Preserved {len(raw_elements)} raw elements for metadata access")
        return text_elements, raw_elements

    def stage3_table_image_extraction(self, filepath, table_locations):
        """Stage 3: Extract tables as images and enhance with HTML"""
        if not table_locations:
            print("📊 No tables detected, skipping table image extraction")
            return []

        print(f"🔄 Stage 3: Table image extraction ({len(table_locations)} tables)...")

        doc = fitz.open(filepath)
        enhanced_tables = []
        pdf_basename = Path(filepath).stem

        for i, table_info in enumerate(table_locations):
            try:
                page_num = table_info["page"]
                table_bbox = table_info["bbox"]
                table_data = table_info["table_data"]

                # Get the page
                page = doc[page_num - 1]  # PyMuPDF is 0-indexed

                # Create a rectangle for the table area
                table_rect = fitz.Rect(table_bbox)

                # Extract table as image with high DPI for clarity
                matrix = fitz.Matrix(2, 2)  # 200 DPI for tables
                pixmap = page.get_pixmap(matrix=matrix, clip=table_rect)

                # Save table image
                table_id = f"table_{i+1}"
                filename = f"{pdf_basename}_page{page_num:02d}_{table_id}.png"
                save_path = self.tables_dir / filename
                pixmap.save(str(save_path))

                # Extract table text and structure
                table_text = table_data.extract()
                table_html = self._table_to_html(table_data)

                # Create enhanced table element with metadata
                enhanced_table = {
                    "id": table_id,
                    "category": "Table",
                    "page": page_num,
                    "text": table_text,
                    "metadata": {
                        "page_number": page_num,
                        "table_id": table_id,
                        "has_html": bool(table_html),
                        "html_length": len(table_html) if table_html else 0,
                        "extraction_method": "pymupdf_table_image",
                        "text_as_html": table_html,
                        "image_path": str(save_path),
                        "width": pixmap.width,
                        "height": pixmap.height,
                        "dpi": int(matrix.a * 72),  # Convert matrix to DPI
                    },
                }

                enhanced_tables.append(enhanced_table)
                print(f"  ✅ Table {i+1}: {filename} (Page {page_num})")

            except Exception as e:
                print(f"  ❌ Error extracting table {i+1}: {e}")

        doc.close()
        print(f"✅ Extracted {len(enhanced_tables)} table images")
        return enhanced_tables

    def stage4_full_page_extraction(self, filepath, page_analysis):
        """Stage 4: Extract full pages when images are detected"""
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

    def _extract_document_metadata(self, doc):
        """Extract document-level metadata"""
        metadata = {
            "total_pages": len(doc),
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
            "producer": doc.metadata.get("producer", ""),
            "creation_date": doc.metadata.get("creationDate", ""),
            "modification_date": doc.metadata.get("modDate", ""),
        }
        return metadata

    def _determine_text_category(self, text, block):
        """Determine text category based on characteristics"""
        text_upper = text.upper().strip()

        # Check for titles/headers
        if len(text.strip()) < 100 and any(char.isupper() for char in text):
            # Check if it's likely a header based on font size or position
            font_size = self._get_font_size(block)
            if font_size > 12:  # Larger font likely indicates header
                return "Title"

        # Check for list items
        if text.strip().startswith(("•", "-", "*", "1.", "2.", "3.", "a.", "b.", "c.")):
            return "ListItem"

        # Default to narrative text
        return "NarrativeText"

    def _get_font_size(self, block):
        """Extract font size from block"""
        try:
            if "lines" in block and block["lines"]:
                line = block["lines"][0]
                if "spans" in line and line["spans"]:
                    return line["spans"][0].get("size", 12)
        except:
            pass
        return 12

    def _get_font_name(self, block):
        """Extract font name from block"""
        try:
            if "lines" in block and block["lines"]:
                line = block["lines"][0]
                if "spans" in line and line["spans"]:
                    return line["spans"][0].get("font", "unknown")
        except:
            pass
        return "unknown"

    def _is_bold_text(self, block):
        """Check if text is bold"""
        try:
            if "lines" in block and block["lines"]:
                line = block["lines"][0]
                if "spans" in line and line["spans"]:
                    flags = line["spans"][0].get("flags", 0)
                    return bool(flags & 2**4)  # Bold flag
        except:
            pass
        return False

    def _create_text_element(self, text, category, metadata):
        """Create a text element object similar to unstructured format"""
        return TextElement(text, category, metadata)

    def _table_to_html(self, table_data):
        """Convert PyMuPDF table to HTML - improved version"""
        try:
            # Method 1: Convert to pandas DataFrame and then to HTML (primary method)
            df = table_data.to_pandas()
            if not df.empty:
                html = df.to_html(
                    index=False, header=True, classes="table table-striped"
                )
                return html
        except Exception as e:
            print(f"    ⚠️  Pandas HTML conversion failed: {e}")

        try:
            # Method 2: Extract raw text and create simple HTML table
            text = table_data.extract()
            if text and text.strip():
                # Split by lines and create table structure
                lines = [
                    line.strip() for line in text.strip().split("\n") if line.strip()
                ]
                if lines:
                    html = "<table border='1' cellpadding='5' cellspacing='0'>"
                    for i, line in enumerate(lines):
                        # Split by tabs or multiple spaces
                        cells = [
                            cell.strip() for cell in line.split("\t") if cell.strip()
                        ]
                        if not cells:
                            # Try splitting by multiple spaces
                            cells = [
                                cell.strip()
                                for cell in line.split("  ")
                                if cell.strip()
                            ]

                        if cells:
                            html += "<tr>"
                            for cell in cells:
                                html += f"<td>{cell}</td>"
                            html += "</tr>"
                        else:
                            # Single cell
                            html += f"<tr><td>{line}</td></tr>"
                    html += "</table>"
                    return html
        except Exception as e:
            print(f"    ⚠️  Text-to-HTML conversion failed: {e}")

        # Method 3: Fallback - simple table with raw text
        try:
            text = table_data.extract()
            if text:
                return f"<table><tr><td>{text.replace(chr(10), '</td></tr><tr><td>')}</td></tr></table>"
        except:
            pass

        return ""


# ==============================================================================
# HELPER CLASSES
# ==============================================================================


class TextElement:
    """Text element class similar to unstructured format - can be pickled"""

    def __init__(self, text, category, metadata):
        self.text = text
        self.category = category
        self.metadata = metadata

    def to_dict(self):
        return {
            "text": self.text,
            "category": self.category,
            "metadata": self.metadata,
        }


# ==============================================================================
# MAIN PROCESSING
# ==============================================================================


def process_pdf_pymupdf_only(filepath):
    """Process PDF using PyMuPDF-only approach"""
    print(f"\n🔄 Processing: {os.path.basename(filepath)}")

    # Initialize partitioner
    partitioner = PyMuPDFOnlyPartitioner(TABLES_DIR, IMAGES_DIR)

    # Stage 1: PyMuPDF analysis
    stage1_results = partitioner.stage1_pymupdf_analysis(filepath)

    # Stage 2: PyMuPDF text extraction
    text_elements, raw_elements = partitioner.stage2_pymupdf_text_extraction(filepath)

    # Stage 3: Table image extraction
    enhanced_tables = partitioner.stage3_table_image_extraction(
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
        "raw_elements": raw_elements,
        "extracted_pages": extracted_pages,
        "table_locations": clean_for_pickle(stage1_results["table_locations"]),
        "image_locations": clean_for_pickle(stage1_results["image_locations"]),
        "page_analysis": stage1_results["page_analysis"],
        "document_metadata": stage1_results["document_metadata"],
        "metadata": {
            "processing_strategy": "pymupdf_only",
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


def save_pymupdf_only_data(combined_data, pickle_path, json_path):
    """Save PyMuPDF-only data in both pickle and JSON formats"""

    print(f"💾 Saving PyMuPDF-only data...")

    # Save pickle file (primary data transfer)
    with open(pickle_path, "wb") as f:
        pickle.dump(combined_data, f)

    print(f"✅ Saved complete data to: {pickle_path}")

    # Calculate statistics for overview
    text_elements = combined_data["text_elements"]

    # Category statistics
    categories = Counter([elem["category"] for elem in text_elements])

    # Font statistics
    font_sizes = Counter()
    font_names = Counter()

    for elem in text_elements:
        metadata = elem["metadata"]
        font_sizes[metadata.get("font_size", "unknown")] += 1
        font_names[metadata.get("font_name", "unknown")] += 1

    # Save JSON file (human-readable metadata with full text)
    json_data = {
        "statistics_overview": {
            "total_text_elements": len(text_elements),
            "total_table_elements": len(combined_data["table_elements"]),
            "total_raw_elements": len(combined_data["raw_elements"]),
            "total_extracted_pages": len(combined_data["extracted_pages"]),
            "total_table_locations": len(combined_data["table_locations"]),
            "total_image_locations": len(combined_data["image_locations"]),
            "total_pages_analyzed": len(combined_data["page_analysis"]),
            "category_breakdown": dict(categories),
            "font_size_breakdown": dict(font_sizes),
            "font_name_breakdown": dict(font_names),
        },
        "metadata": combined_data["metadata"],
        "document_metadata": combined_data["document_metadata"],
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
                "text": elem["text"],
                "page": elem["page"],
                "metadata": {
                    "page_number": elem["metadata"]["page_number"],
                    "font_size": elem["metadata"]["font_size"],
                    "font_name": elem["metadata"]["font_name"],
                    "is_bold": elem["metadata"]["is_bold"],
                    "extraction_method": elem["metadata"]["extraction_method"],
                },
            }
            for elem in combined_data["text_elements"]
        ],
        "table_elements": [
            {
                "id": table["id"],
                "category": table["category"],
                "page": table["page"],
                "text": table["text"],
                "metadata": table["metadata"],
            }
            for table in combined_data["table_elements"]
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
    print("🚀 PYMUPDF-ONLY PDF PARTITIONING PIPELINE")
    print("=" * 50)
    print("Strategy: PyMuPDF only - no unstructured dependencies")
    print(f"🌍 OCR Languages: {OCR_LANGUAGES}")
    print(f"Processing: {len(FILES_TO_PROCESS)} file(s)")

    for filename in FILES_TO_PROCESS:
        filepath = os.path.join(PDF_SOURCE_DIR, filename)

        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            continue

        # Process PDF with PyMuPDF-only approach
        combined_data = process_pdf_pymupdf_only(filepath)

        # Save results
        save_pymupdf_only_data(combined_data, PICKLE_OUTPUT_PATH, JSON_OUTPUT_PATH)

        # Show summary
        print(f"\n📊 PYMUPDF-ONLY PROCESSING SUMMARY:")
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
        print(f"   📄 PyMuPDF-only data (pickle): {PICKLE_OUTPUT_PATH}")
        print(f"   📄 PyMuPDF-only metadata (JSON): {JSON_OUTPUT_PATH}")

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

        print(f"\n🎉 PyMuPDF-only partitioning complete!")
        print(f"📁 Next: Use '{PICKLE_OUTPUT_PATH}' in your meta_data notebook")
        print(f"🕒 Timestamp: {timestamp}")
