# ==============================================================================
# VLM ENRICHMENT PIPELINE
# Enhanced captioning for tables and images using Claude 3.5 Sonnet
# ==============================================================================

import os
import base64
import pickle
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# --- Environment & API ---
from dotenv import load_dotenv

# --- LangChain VLM Components ---
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# --- Pydantic for Enhanced Metadata ---
from pydantic import BaseModel, Field

# ==============================================================================
# CONFIGURATION - SPECIFY WHICH PARTITION RUN TO LOAD
# ==============================================================================
PARTITION_RUN_TO_LOAD = (
    "run_20250720_080612"  # Change this to load different partition runs
)

# ==============================================================================
# LANGUAGE CONFIGURATION
# ==============================================================================
CAPTION_LANGUAGE = (
    "Danish"  # Language for VLM captions (e.g., "Danish", "English", "German", etc.)
)

# ==============================================================================
# 1. ENHANCED METADATA MODELS
# ==============================================================================


class VLMEnrichmentMetadata(BaseModel):
    """Metadata for VLM-enriched content"""

    # VLM Processing Info
    vlm_model: str = "claude-3.5-sonnet"
    vlm_processed: bool = False
    vlm_processing_timestamp: Optional[str] = None
    vlm_processing_error: Optional[str] = None

    # Table Captions
    table_html_caption: Optional[str] = None
    table_image_caption: Optional[str] = None
    table_image_filepath: Optional[str] = None

    # Image Captions
    full_page_image_caption: Optional[str] = None
    full_page_image_filepath: Optional[str] = None
    page_text_context: Optional[str] = None

    # Processing Statistics
    caption_word_count: int = 0
    processing_duration_seconds: Optional[float] = None


# ==============================================================================
# 2. VLM CAPTION GENERATOR
# ==============================================================================


class ConstructionVLMCaptioner:
    """Specialized VLM captioner for construction/technical content"""

    def __init__(self, model_name="anthropic/claude-3-5-sonnet"):
        # Initialize VLM client
        self.model_name = model_name
        self.vlm_client = ChatOpenAI(
            model=model_name,
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base="https://openrouter.ai/api/v1",
            default_headers={"HTTP-Referer": "http://localhost"},
        )

        print(f"✅ VLM Captioner initialized with {model_name}")
        print(f"📝 Caption language set to: {CAPTION_LANGUAGE}")

    def caption_table_html(self, table_html: str, element_context: dict) -> str:
        """Generate caption for table using HTML representation"""

        page_num = element_context.get("page_number", "unknown")
        source_file = element_context.get("source_filename", "unknown")

        prompt = f"""You are analyzing a table from page {page_num} of a construction/technical document ({source_file}).

Below is the HTML representation of the table. Please provide a comprehensive caption that includes:

1. **Table Purpose**: What type of information does this table contain?
2. **Structure**: How many rows/columns, what are the headers?
3. **Key Data**: What are the most important values, measurements, or specifications?
4. **Technical Details**: Any codes, standards, measurements, or specifications mentioned
5. **Context**: How this table might relate to construction/engineering work

HTML Table:
{table_html}

IMPORTANT: Please provide your detailed, technical caption in {CAPTION_LANGUAGE}."""

        try:
            response = self.vlm_client.invoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            print(f"    ❌ Error captioning table HTML: {e}")
            return f"Error generating caption: {str(e)}"

    def caption_table_image(self, image_path: str, element_context: dict) -> str:
        """Generate caption for table using extracted image"""

        page_num = element_context.get("page_number", "unknown")
        source_file = element_context.get("source_filename", "unknown")

        # Read and encode image
        try:
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        except Exception as e:
            return f"Error reading image: {str(e)}"

        prompt = f"""You are analyzing a table image extracted from page {page_num} of a construction/technical document ({source_file}).

Please provide a comprehensive description that captures:

1. **All Visible Text**: Read and transcribe ALL text visible in the table, including headers, data, footnotes
2. **Table Structure**: Number of rows, columns, organization
3. **Technical Content**: Any measurements, codes, specifications, standards mentioned
4. **Data Relationships**: How the data is organized and what it represents
5. **Construction Context**: How this information relates to building/engineering work

Focus on being extremely detailed about all visible text and numbers - this will be used for search and retrieval.

IMPORTANT: Please provide your detailed description in {CAPTION_LANGUAGE}."""

        try:
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                ]
            )
            response = self.vlm_client.invoke([message])
            return response.content.strip()
        except Exception as e:
            print(f"    ❌ Error captioning table image: {e}")
            return f"Error generating caption: {str(e)}"

    def caption_full_page_image(
        self, image_path: str, page_context: dict, page_text_context: str = ""
    ) -> str:
        """Generate caption for full page image with surrounding text context"""

        page_num = page_context.get("page_number", "unknown")
        source_file = page_context.get("source_filename", "unknown")
        complexity = page_context.get("complexity", "unknown")

        # Read and encode image
        try:
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        except Exception as e:
            return f"Error reading image: {str(e)}"

        # Build context-aware prompt
        context_section = ""
        if page_text_context.strip():
            context_section = f"""

**Text Context from this page:**
{page_text_context[:1500]}"""  # Increased context limit

        prompt = f"""You are analyzing a full-page technical drawing/image from page {page_num} of a construction document ({source_file}). This page has {complexity} visual complexity.

Please provide an EXTREMELY DETAILED description that captures:

1. **ALL VISIBLE TEXT**: Read and transcribe every piece of text, including:
   - Titles, headings, labels
   - Dimension annotations and measurements  
   - Callout numbers and reference codes
   - Notes, specifications, and descriptions
   - Legend items and explanations
   - All technical annotations and comments

2. **Technical Drawing Details**: 
   - Type of drawing (floor plan, elevation, detail, etc.)
   - Architectural/engineering elements shown
   - Dimensions, scales, and measurements
   - Materials and construction details
   - Symbols and technical notations

3. **Spatial Relationships**:
   - Layout and arrangement of elements
   - How different parts connect or relate
   - Reference points and orientations

4. **Pointers and Annotations**:
   - What specific elements are being highlighted
   - Technical specifications for highlighted areas
   - Connection between callouts and drawing elements

5. **Building Materials and Construction**:
   - Specific building materials mentioned
   - Construction techniques and methods
   - Technical standards and codes

{context_section}

CRITICAL: Focus on extracting ALL text and technical information - this will be used for search and retrieval. Be extremely thorough with visible text, numbers, codes, and technical details. There is NO LIMIT to how long the description can be - include all relevant information.

IMPORTANT: Please provide your comprehensive description in {CAPTION_LANGUAGE}."""

        try:
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                ]
            )
            response = self.vlm_client.invoke([message])
            return response.content.strip()
        except Exception as e:
            print(f"    ❌ Error captioning full page image: {e}")
            return f"Error generating caption: {str(e)}"


# ==============================================================================
# 3. LOADING FUNCTIONS
# ==============================================================================


def load_processed_elements(pickle_file_path: str):
    """Load pre-processed elements from partitioning notebook"""
    print(f"📂 Loading processed elements from: {pickle_file_path}")

    try:
        with open(pickle_file_path, "rb") as f:
            data = pickle.load(f)

        print(f"✅ Loaded data with keys: {list(data.keys())}")
        return data

    except FileNotFoundError:
        print(f"❌ File not found: {pickle_file_path}")
        print("Make sure you've run the partitioning notebook first!")
        return None
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None


# ==============================================================================
# 4. TABLE ENRICHMENT FUNCTIONS
# ==============================================================================


def enrich_table_elements(
    raw_elements, tables_dir: Path, captioner: ConstructionVLMCaptioner
) -> List[dict]:
    """Enrich table elements with VLM captions from both HTML and images"""

    print(f"📊 Enriching table elements...")

    # Find table elements
    table_elements = [
        el for el in raw_elements if getattr(el, "category", "") == "Table"
    ]
    print(f"📋 Found {len(table_elements)} table elements")

    enriched_tables = []

    for i, table_element in enumerate(table_elements):
        print(f"\n📊 Processing table {i+1}/{len(table_elements)}...")

        # Get basic metadata
        metadata_dict = getattr(table_element, "metadata", {})
        if hasattr(metadata_dict, "to_dict"):
            metadata_dict = metadata_dict.to_dict()

        element_context = {
            "page_number": metadata_dict.get("page_number", "unknown"),
            "source_filename": metadata_dict.get("filename", "unknown"),
        }

        print(
            f"    📍 Table metadata: Page {element_context['page_number']}, File: {element_context['source_filename']}"
        )

        # Initialize enrichment metadata
        enrichment_meta = VLMEnrichmentMetadata(
            vlm_processing_timestamp=datetime.now().isoformat()
        )

        try:
            # Caption 1: HTML representation (access from metadata)
            table_html = None

            # Get HTML from metadata
            if "text_as_html" in metadata_dict:
                table_html = metadata_dict["text_as_html"]
            else:
                # Fallback to regular text
                table_html = getattr(table_element, "text", "")

            if table_html and table_html.strip():
                print(
                    f"    🔤 Captioning HTML representation ({len(table_html)} chars)..."
                )
                enrichment_meta.table_html_caption = captioner.caption_table_html(
                    table_html, element_context
                )
                print(
                    f"    ✅ HTML caption generated ({len(enrichment_meta.table_html_caption)} chars)"
                )
            else:
                print(f"    ⚠️ No HTML content found for table")

            # Caption 2: Image representation (direct path from metadata)
            image_path = metadata_dict.get("image_path")

            if image_path:
                image_path_obj = Path(image_path)
                if image_path_obj.exists():
                    print(f"    🖼️ Captioning table image: {image_path_obj.name}")
                    enrichment_meta.table_image_caption = captioner.caption_table_image(
                        str(image_path_obj), element_context
                    )
                    enrichment_meta.table_image_filepath = str(image_path_obj)
                    print(
                        f"    ✅ Image caption generated ({len(enrichment_meta.table_image_caption)} chars)"
                    )
                else:
                    print(f"    ❌ Image file not found: {image_path_obj}")
            else:
                print(f"    ⚠️ No image_path found in metadata")

            enrichment_meta.vlm_processed = True

        except Exception as e:
            print(f"    ❌ Error processing table: {e}")
            enrichment_meta.vlm_processing_error = str(e)

        # Calculate caption statistics
        total_caption_length = 0
        if enrichment_meta.table_html_caption:
            total_caption_length += len(enrichment_meta.table_html_caption.split())
        if enrichment_meta.table_image_caption:
            total_caption_length += len(enrichment_meta.table_image_caption.split())
        enrichment_meta.caption_word_count = total_caption_length

        enriched_tables.append(
            {
                "element_id": f"table_{i}",
                "original_element": table_element,
                "enrichment_metadata": enrichment_meta,
                "element_type": "table",
            }
        )

    print(f"✅ Table enrichment complete: {len(enriched_tables)} tables processed")
    return enriched_tables


# ==============================================================================
# 5. IMAGE ENRICHMENT FUNCTIONS
# ==============================================================================


def get_page_text_context(page_num: int, raw_elements) -> str:
    """Extract text context from the same page for image captioning"""

    page_texts = []
    for element in raw_elements:
        metadata_dict = getattr(element, "metadata", {})
        if hasattr(metadata_dict, "to_dict"):
            metadata_dict = metadata_dict.to_dict()

        element_page = metadata_dict.get("page_number", 0)
        if element_page == page_num:
            text = getattr(element, "text", "").strip()
            if text and getattr(element, "category", "") != "Table":  # Exclude tables
                page_texts.append(text)

    return "\n".join(
        page_texts[:5]
    )  # Limit to first 5 text elements to avoid token limits


def enrich_image_elements(
    extracted_pages: dict,
    vlm_pages_dir: Path,
    raw_elements,
    captioner: ConstructionVLMCaptioner,
) -> List[dict]:
    """Enrich full-page images with VLM captions using page text context"""

    print(f"🖼️ Enriching full-page images...")

    if not vlm_pages_dir.exists():
        print(f"❌ VLM pages directory not found: {vlm_pages_dir}")
        return []

    print(f"📁 Found {len(extracted_pages)} image pages to process")

    enriched_images = []

    for page_num, page_info in extracted_pages.items():
        print(f"\n🖼️ Processing image page {page_num}...")

        # Find corresponding image file
        expected_filepath = Path(page_info.get("filepath", ""))
        if not expected_filepath.exists():
            print(f"    ❌ Image file not found: {expected_filepath}")
            continue

        # Get page text context
        page_text_context = get_page_text_context(page_num, raw_elements)
        context_info = (
            f" (with {len(page_text_context)} chars context)"
            if page_text_context
            else " (no text context)"
        )

        # Initialize enrichment metadata
        enrichment_meta = VLMEnrichmentMetadata(
            vlm_processing_timestamp=datetime.now().isoformat(),
            full_page_image_filepath=str(expected_filepath),
            page_text_context=page_text_context,
        )

        page_context = {
            "page_number": page_num,
            "source_filename": page_info.get("filename", "unknown"),
            "complexity": page_info.get("complexity", "unknown"),
        }

        try:
            print(f"    🤖 Generating VLM caption{context_info}...")
            enrichment_meta.full_page_image_caption = captioner.caption_full_page_image(
                str(expected_filepath), page_context, page_text_context
            )

            enrichment_meta.vlm_processed = True
            enrichment_meta.caption_word_count = len(
                enrichment_meta.full_page_image_caption.split()
            )

            print(
                f"    ✅ Caption generated ({enrichment_meta.caption_word_count} words)"
            )

        except Exception as e:
            print(f"    ❌ Error processing image: {e}")
            enrichment_meta.vlm_processing_error = str(e)

        enriched_images.append(
            {
                "element_id": f"image_page_{page_num}",
                "original_element": page_info,
                "enrichment_metadata": enrichment_meta,
                "element_type": "full_page_image",
            }
        )

    print(f"✅ Image enrichment complete: {len(enriched_images)} images processed")
    return enriched_images


# ==============================================================================
# 6. SAVING FUNCTIONS
# ==============================================================================


def save_enriched_elements(enriched_elements, output_path):
    """Save enriched elements with VLM captions"""

    print(f"💾 Saving enriched elements to: {output_path}")

    # Convert Pydantic models to dicts for JSON serialization
    serializable_elements = []
    for element in enriched_elements:
        serializable_element = {
            "element_id": element["element_id"],
            "element_type": element["element_type"],
            "enrichment_metadata": element["enrichment_metadata"].model_dump(),
            # Note: original_element is not JSON serializable, so we'll use pickle
        }
        serializable_elements.append(serializable_element)

    # Handle both string and Path objects
    if isinstance(output_path, Path):
        pickle_path = output_path.with_suffix(".pkl")
    else:
        pickle_path = output_path.replace(".json", ".pkl")

    with open(pickle_path, "wb") as f:
        pickle.dump(enriched_elements, f)

    with open(output_path, "w") as f:
        json.dump(serializable_elements, f, indent=2)

    print(f"✅ Saved complete data to: {pickle_path}")
    print(f"✅ Saved metadata to: {output_path}")


def show_enrichment_summary(enriched_elements):
    """Show summary of VLM enrichment results"""

    print(f"\n📈 VLM ENRICHMENT SUMMARY:")
    print("=" * 40)

    total_elements = len(enriched_elements)
    successful_processing = 0
    failed_processing = 0

    table_elements = 0
    image_elements = 0

    total_caption_words = 0
    html_captions = 0
    image_captions = 0
    page_captions = 0

    for element in enriched_elements:
        meta = element["enrichment_metadata"]
        element_type = element["element_type"]

        if meta.vlm_processed:
            successful_processing += 1
        else:
            failed_processing += 1

        if element_type == "table":
            table_elements += 1
            if meta.table_html_caption:
                html_captions += 1
            if meta.table_image_caption:
                image_captions += 1
        elif element_type == "full_page_image":
            image_elements += 1
            if meta.full_page_image_caption:
                page_captions += 1

        total_caption_words += meta.caption_word_count

    print(f"📊 Processing Results:")
    print(f"   Total elements: {total_elements}")
    print(f"   Successfully processed: {successful_processing}")
    print(f"   Failed processing: {failed_processing}")

    print(f"\n📋 Element Types:")
    print(f"   Table elements: {table_elements}")
    print(f"   Full-page images: {image_elements}")

    print(f"\n📝 Caption Generation:")
    print(f"   HTML table captions: {html_captions}")
    print(f"   Image table captions: {image_captions}")
    print(f"   Full-page captions: {page_captions}")
    print(f"   Total caption words: {total_caption_words:,}")

    if total_elements > 0:
        avg_words = total_caption_words / total_elements
        print(f"   Average words per element: {avg_words:.1f}")


# ==============================================================================
# 7. TESTING AND MAIN EXECUTION
# ==============================================================================


def test_data_access():
    """Quick test to verify we can access saved data from partitioning notebook"""

    print("🧪 TESTING DATA ACCESS FROM PARTITIONING NOTEBOOK")
    print("=" * 55)

    # Construct test file path using configuration
    PARTITION_DATA_DIR = Path("../../data/internal/01_partition_data")
    test_file = PARTITION_DATA_DIR / PARTITION_RUN_TO_LOAD / "processed_elements.pkl"

    print(f"📂 Looking for: {test_file}")
    print(f"📁 From partition run: {PARTITION_RUN_TO_LOAD}")

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        print("💡 Make sure you've run the partitioning notebook and saved the data!")
        print(f"💡 Available partition runs:")
        if PARTITION_DATA_DIR.exists():
            for run_dir in PARTITION_DATA_DIR.glob("run_*"):
                print(f"   - {run_dir.name}")
        return False

    try:
        with open(test_file, "rb") as f:
            data = pickle.load(f)

        print(f"✅ Successfully loaded: {test_file}")
        print(f"📊 Data contains keys: {list(data.keys())}")

        # Test each component
        raw_elements = data.get("raw_elements", [])
        extracted_pages = data.get("extracted_pages", {})
        page_analysis = data.get("page_analysis", {})
        filepath = data.get("filepath", "Unknown")

        print(f"\n📋 Data Summary:")
        print(f"  📄 Source file: {os.path.basename(filepath)}")
        print(f"  📝 Raw elements: {len(raw_elements)}")
        print(f"  🖼️  Extracted pages: {len(extracted_pages)}")
        print(f"  📊 Page analysis: {len(page_analysis)} pages")

        print(f"\n🎉 Data access test PASSED!")
        print(f"📱 Ready to proceed with VLM enrichment...")
        return True

    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False


# ==============================================================================
# 8. MAIN EXECUTION
# ==============================================================================

if __name__ == "__main__":
    # Load environment
    load_dotenv()

    # Verify API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ OPENROUTER_API_KEY not found in .env file")
        print("💡 Please add your OpenRouter API key to the .env file")
        exit()

    # Run the test first
    if not test_data_access():
        print("\n🛑 Cannot proceed without valid data. Please fix the issues above.")
        exit()

    print("\n" + "=" * 60)

    # Configuration - Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_BASE_DIR = Path("../../data/internal/03_enrich_data")
    CURRENT_RUN_DIR = OUTPUT_BASE_DIR / f"run_{timestamp}"

    # Create directories
    OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_RUN_DIR.mkdir(exist_ok=True)

    # Construct paths from partition run configuration
    PARTITION_DATA_DIR = Path("../../data/internal/01_partition_data")
    PARTITION_RUN_DIR = PARTITION_DATA_DIR / PARTITION_RUN_TO_LOAD
    INPUT_PICKLE_PATH = PARTITION_RUN_DIR / "processed_elements.pkl"
    TABLES_DIR = PARTITION_RUN_DIR / "tables"
    VLM_PAGES_DIR = PARTITION_RUN_DIR / "vlm_pages"
    OUTPUT_PATH = CURRENT_RUN_DIR / "enriched_elements.json"

    print(f"📁 Output directory: {CURRENT_RUN_DIR}")
    print(f"📁 Input from partition run: {PARTITION_RUN_TO_LOAD}")
    print(f"📁 Loading from: {INPUT_PICKLE_PATH}")
    print(f"📁 Tables directory: {TABLES_DIR}")
    print(f"📁 VLM pages directory: {VLM_PAGES_DIR}")
    print(f"📁 Enriched elements will be saved to: {OUTPUT_PATH}")

    print("🤖 VLM ENRICHMENT PIPELINE - CLAUDE 3.5 SONNET")
    print("=" * 60)

    # Load pre-processed elements
    data = load_processed_elements(INPUT_PICKLE_PATH)

    # DEBUG: Check what table attributes are available
    print("\n🔍 DEBUG: INSPECTING TABLE ELEMENTS FROM RAW DATA")
    print("=" * 50)

    if data:
        raw_elements_debug = data.get("raw_elements", [])

        # Find table elements
        table_elements = [
            el for el in raw_elements_debug if getattr(el, "category", "") == "Table"
        ]
        print(f"📊 Found {len(table_elements)} table elements")

        if table_elements:
            # Show metadata of first table
            sample_table = table_elements[0]
            metadata_dict = getattr(sample_table, "metadata", {})
            if hasattr(metadata_dict, "to_dict"):
                metadata_dict = metadata_dict.to_dict()

            print(f"\n📋 Sample Table Metadata Keys: {list(metadata_dict.keys())}")

            # Check if text_as_html is in metadata
            if "text_as_html" in metadata_dict:
                html_content = metadata_dict["text_as_html"]
                print(f"    📋 text_as_html available: {len(str(html_content))} chars")

            # Check if image_path is in metadata
            if "image_path" in metadata_dict:
                image_path = metadata_dict["image_path"]
                print(f"    🖼️ image_path available: {Path(image_path).name}")

            # Show all table elements summary
            print(f"\n📊 All Table Elements:")
            for i, table in enumerate(table_elements):
                metadata_dict = getattr(table, "metadata", {})
                if hasattr(metadata_dict, "to_dict"):
                    metadata_dict = metadata_dict.to_dict()
                page_num = metadata_dict.get("page_number", "unknown")
                text_len = len(getattr(table, "text", ""))
                html_len = len(str(metadata_dict.get("text_as_html", "")))
                has_image = "image_path" in metadata_dict
                print(
                    f"    Table {i+1}: Page {page_num} | Text: {text_len} chars | HTML: {html_len} chars | Image: {'✅' if has_image else '❌'}"
                )

        else:
            print("❌ No table elements found in raw data")

    print("=" * 50)
    print("🔄 Proceeding with enrichment pipeline...\n")

    if data:
        raw_elements = data.get("raw_elements", [])
        extracted_pages = data.get("extracted_pages", {})
        page_analysis = data.get("page_analysis", {})

        print(f"📊 Input Summary:")
        print(f"  Raw elements: {len(raw_elements)}")
        print(f"  Extracted pages: {len(extracted_pages)}")
        print(f"  Analyzed pages: {len(page_analysis)}")

        # Initialize VLM captioner
        print(f"\n🤖 Initializing Claude 3.5 Sonnet captioner...")
        captioner = ConstructionVLMCaptioner()

        # Step 1: Enrich table elements
        print(f"\n" + "=" * 40)
        print("📊 STEP 1: TABLE ENRICHMENT")
        print("=" * 40)

        enriched_tables = enrich_table_elements(raw_elements, TABLES_DIR, captioner)

        # Step 2: Enrich image elements
        print(f"\n" + "=" * 40)
        print("🖼️ STEP 2: IMAGE ENRICHMENT")
        print("=" * 40)

        enriched_images = enrich_image_elements(
            extracted_pages, VLM_PAGES_DIR, raw_elements, captioner
        )

        # Combine all enriched elements
        all_enriched_elements = enriched_tables + enriched_images

        print(f"\n" + "=" * 40)
        print("💾 SAVING ENRICHED ELEMENTS")
        print("=" * 40)

        # Show summary
        show_enrichment_summary(all_enriched_elements)

        # Save enriched elements
        save_enriched_elements(all_enriched_elements, OUTPUT_PATH)

        print(f"\n🎉 VLM enrichment pipeline complete!")
        print(f"📁 Output Files Created:")
        print(f"   📂 Run directory: {CURRENT_RUN_DIR}")
        print(
            f"   📄 Enriched elements (pickle): {CURRENT_RUN_DIR / 'enriched_elements.pkl'}"
        )
        print(
            f"   📄 Enriched elements (JSON): {CURRENT_RUN_DIR / 'enriched_elements.json'}"
        )
        print(f"   🕒 Timestamp: {timestamp}")
        print(
            f"\n📁 Next: Use '{CURRENT_RUN_DIR / 'enriched_elements.pkl'}' in your chunking/RAG pipeline"
        )

    else:
        print("❌ Cannot proceed without processed elements")
        print(
            "💡 First run the partitioning notebook to generate 'processed_elements.pkl'"
        )
