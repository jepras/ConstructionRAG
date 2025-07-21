# ==============================================================================
# VLM ENRICHMENT PIPELINE - META DATA VERSION
# Enhanced captioning for tables and images using Claude 3.5 Sonnet
# Works with enriched elements from meta_data.py instead of raw partition data
# ==============================================================================

import os
import sys
import base64
import pickle
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# --- PDF Parsing (for pickle compatibility) ---
from unstructured.partition.pdf import partition_pdf

# --- Environment & API ---
from dotenv import load_dotenv

# --- LangChain VLM Components ---
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# --- Pydantic for Enhanced Metadata ---
from pydantic import BaseModel, Field
from typing import Literal

# ==============================================================================
# CONFIGURATION - ALL CONFIGURABLE VARIABLES
# ==============================================================================

# --- Data Source Configuration ---
META_DATA_RUN_TO_LOAD = (
    "02_run_20250721_100823"  # Change this to load different meta_data runs
)

# --- Language Configuration ---
CAPTION_LANGUAGE = (
    "Danish"  # Language for VLM captions (e.g., "Danish", "English", "German", etc.)
)

# --- Model Configuration ---
VLM_MODEL_NAME = "anthropic/claude-3-5-sonnet"  # VLM model to use for captioning

# --- Path Configuration ---
# Base directories (relative to project root)
DATA_BASE_DIR = "../../data/internal"
META_DATA_DIR = f"{DATA_BASE_DIR}/02_meta_data"
OUTPUT_BASE_DIR = f"{DATA_BASE_DIR}/03_enrich_data"

# --- Processing Configuration ---
MAX_TEXT_CONTEXT_LENGTH = 1500  # Max characters of text context for image captioning
MAX_PAGE_TEXT_ELEMENTS = 5  # Max text elements to include in page context

# ==============================================================================
# 1. ENHANCED METADATA MODELS
# ==============================================================================


class StructuralMetadata(BaseModel):
    """Enhanced metadata focusing on high-impact, easy-to-implement fields"""

    # Core metadata
    source_filename: str
    page_number: int
    content_type: Literal["text", "table", "full_page_with_images"]

    # Phase 1: High-impact, easy fields
    page_context: str = "unknown"  # "text_only_page", "page_with_images", "image_page"
    content_length: int = 0  # Character count
    has_numbers: bool = False  # Contains measurements/codes/quantities
    element_category: str = "unknown"  # From unstructured: Title, NarrativeText, etc.

    # Phase 1 bonus fields
    has_tables_on_page: bool = False  # Page contains tables
    has_images_on_page: bool = False  # Page contains images
    text_complexity: str = "medium"  # "simple", "medium", "complex"

    # Section title detection (3 approaches for testing)
    section_title_category: Optional[str] = None  # From unstructured Title/Header
    section_title_inherited: Optional[str] = None  # Inherited from previous title
    section_title_pattern: Optional[str] = (
        None  # From numbered patterns like "1.2 Something"
    )


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

    def __init__(self, model_name=VLM_MODEL_NAME):
        # Initialize VLM client
        self.model_name = model_name
        self.vlm_client = ChatOpenAI(
            model=model_name,
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base="https://openrouter.ai/api/v1",
            default_headers={"HTTP-Referer": "http://localhost"},
        )

        print(f"✅ VLM Captioner initialized with {self.model_name}")
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
{page_text_context[:MAX_TEXT_CONTEXT_LENGTH]}"""  # Configurable context limit

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
# 3. LOADING FUNCTIONS - MODIFIED FOR META DATA
# ==============================================================================


def load_enriched_elements_from_meta(pickle_file_path: str):
    """Load enriched elements from meta_data pipeline with robust error handling"""
    print(f"📂 Loading enriched elements from: {pickle_file_path}")

    try:
        with open(pickle_file_path, "rb") as f:
            data = pickle.load(f)

        print(f"✅ Loaded enriched elements: {len(data)} elements")
        return data

    except FileNotFoundError:
        print(f"❌ File not found: {pickle_file_path}")
        print("Make sure you've run the meta_data notebook first!")
        return None
    except ModuleNotFoundError as e:
        print(f"❌ Module not found: {e}")
        print(
            "💡 This is expected - the pickle contains references to external modules"
        )
        print("💡 Trying alternative loading approach...")

        # Try to load with a more robust approach
        try:
            # Create a mock module to handle the dependency
            import types

            mock_unstructured = types.ModuleType("unstructured")
            import sys

            sys.modules["unstructured"] = mock_unstructured

            with open(pickle_file_path, "rb") as f:
                data = pickle.load(f)

            print(f"✅ Successfully loaded with mock module: {len(data)} elements")
            return data

        except Exception as e2:
            print(f"❌ Alternative loading also failed: {e2}")
            print(
                "💡 Consider re-running the meta_data notebook to regenerate the pickle file"
            )
            return None

    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None


# ==============================================================================
# 4. TABLE ENRICHMENT FUNCTIONS - MODIFIED FOR META DATA
# ==============================================================================


def enrich_table_elements_from_meta(
    enriched_elements, captioner: ConstructionVLMCaptioner
) -> List[dict]:
    """Enrich table elements with VLM captions from both HTML and images"""

    print(f"📊 Enriching table elements from meta data...")

    # Find table elements from enriched data
    table_elements = [
        el
        for el in enriched_elements
        if el["structural_metadata"].content_type == "table"
    ]
    print(f"📋 Found {len(table_elements)} table elements")

    enriched_tables = []

    for i, table_element in enumerate(table_elements):
        print(f"\n📊 Processing table {i+1}/{len(table_elements)}...")

        # Get metadata from enriched element
        struct_meta = table_element["structural_metadata"]
        element_id = table_element["id"]

        element_context = {
            "page_number": struct_meta.page_number,
            "source_filename": struct_meta.source_filename,
        }

        print(
            f"    📍 Table metadata: Page {element_context['page_number']}, File: {element_context['source_filename']}"
        )

        # Initialize enrichment metadata
        enrichment_meta = VLMEnrichmentMetadata(
            vlm_processing_timestamp=datetime.now().isoformat()
        )

        try:
            # Get the original element from enriched data
            original_element = table_element["original_element"]

            # Get metadata from original element (same approach as enrich_data.py)
            metadata_dict = getattr(original_element, "metadata", {})
            if hasattr(metadata_dict, "to_dict"):
                metadata_dict = metadata_dict.to_dict()

            # Caption 1: HTML representation (access from metadata)
            table_html = None

            # Get HTML from metadata
            if "text_as_html" in metadata_dict:
                table_html = metadata_dict["text_as_html"]
            else:
                # Fallback to regular text
                table_html = getattr(original_element, "text", "")

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
                "element_id": element_id,
                "original_element": table_element,
                "enrichment_metadata": enrichment_meta,
                "element_type": "table",
            }
        )

    print(f"✅ Table enrichment complete: {len(enriched_tables)} tables processed")
    return enriched_tables


# ==============================================================================
# 5. IMAGE ENRICHMENT FUNCTIONS - MODIFIED FOR META DATA
# ==============================================================================


def get_page_text_context_from_meta(page_num: int, enriched_elements) -> str:
    """Extract text context from the same page for image captioning"""

    page_texts = []
    for element in enriched_elements:
        struct_meta = element["structural_metadata"]
        element_page = struct_meta.page_number

        if element_page == page_num and struct_meta.content_type == "text":
            # Get text from original element if available
            if "original_element" in element and hasattr(
                element["original_element"], "text"
            ):
                text = getattr(element["original_element"], "text", "").strip()
                if text:
                    page_texts.append(text)

    return "\n".join(
        page_texts[:MAX_PAGE_TEXT_ELEMENTS]
    )  # Configurable limit to avoid token limits


def enrich_image_elements_from_meta(
    enriched_elements, captioner: ConstructionVLMCaptioner
) -> List[dict]:
    """Enrich full-page images with VLM captions using page text context"""

    print(f"🖼️ Enriching full-page images from meta data...")

    # Find image page elements
    image_elements = [
        el
        for el in enriched_elements
        if el["structural_metadata"].content_type == "full_page_with_images"
    ]

    print(f"📁 Found {len(image_elements)} image pages to process")

    enriched_images = []

    for i, image_element in enumerate(image_elements):
        print(f"\n🖼️ Processing image page {i+1}/{len(image_elements)}...")

        struct_meta = image_element["structural_metadata"]
        element_id = image_element["id"]
        page_num = struct_meta.page_number

        print(
            f"    📍 Image metadata: Page {page_num}, File: {struct_meta.source_filename}"
        )

        # Get the original element from enriched data
        original_element = image_element["original_element"]

        print(f"    🔍 Original element type: {type(original_element)}")

        # For image elements, original_element is a dict with filepath
        if isinstance(original_element, dict):
            image_path = original_element.get("filepath")
            print(f"    📋 Dictionary keys: {list(original_element.keys())}")
            print(f"    🖼️ Found filepath: {image_path}")
        else:
            # Fallback to metadata approach (for tables)
            metadata_dict = getattr(original_element, "metadata", {})
            if hasattr(metadata_dict, "to_dict"):
                metadata_dict = metadata_dict.to_dict()
            image_path = metadata_dict.get("image_path")
            print(f"    🔍 Looking for image_path in metadata...")
            print(f"    📋 Available metadata keys: {list(metadata_dict.keys())}")
            print(f"    🖼️ Found image_path: {image_path}")

        if not image_path:
            print(f"    ❌ No image path found - skipping page {page_num}")
            continue

        image_path_obj = Path(image_path)
        print(f"    📂 Image file path: {image_path_obj}")
        print(f"    ✅ File exists: {image_path_obj.exists()}")

        if not image_path_obj.exists():
            print(f"    ❌ Image file not found: {image_path_obj}")
            continue

        # Get page text context
        page_text_context = get_page_text_context_from_meta(page_num, enriched_elements)
        context_info = (
            f" (with {len(page_text_context)} chars context)"
            if page_text_context
            else " (no text context)"
        )

        # Initialize enrichment metadata
        enrichment_meta = VLMEnrichmentMetadata(
            vlm_processing_timestamp=datetime.now().isoformat(),
            full_page_image_filepath=str(image_path_obj),
            page_text_context=page_text_context,
        )

        page_context = {
            "page_number": page_num,
            "source_filename": struct_meta.source_filename,
            "complexity": "complex",  # Default for image pages
        }

        try:
            print(f"    🤖 Generating VLM caption{context_info}...")
            enrichment_meta.full_page_image_caption = captioner.caption_full_page_image(
                str(image_path_obj), page_context, page_text_context
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
                "element_id": element_id,
                "original_element": image_element,
                "enrichment_metadata": enrichment_meta,
                "element_type": "full_page_image",
            }
        )

    print(f"✅ Image enrichment complete: {len(enriched_images)} images processed")
    return enriched_images


# ==============================================================================
# 6. SAVING FUNCTIONS
# ==============================================================================


def save_enriched_elements(enriched_elements, json_output_path, pickle_output_path):
    """Save enriched elements with VLM captions"""

    print(f"💾 Saving enriched elements...")

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

    # Save pickle file (primary data transfer)
    with open(pickle_output_path, "wb") as f:
        pickle.dump(enriched_elements, f)

    # Save JSON file (human-readable metadata)
    with open(json_output_path, "w") as f:
        json.dump(serializable_elements, f, indent=2)

    print(f"✅ Saved complete data to: {pickle_output_path}")
    print(f"✅ Saved metadata to: {json_output_path}")


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
    """Quick test to verify we can access saved data from meta_data notebook"""

    print("🧪 TESTING DATA ACCESS FROM META DATA NOTEBOOK")
    print("=" * 55)

    # Construct test file path using configuration
    test_file = Path(META_DATA_DIR) / META_DATA_RUN_TO_LOAD / "meta_data_output.pkl"

    print(f"📂 Looking for: {test_file}")
    print(f"📁 From meta_data run: {META_DATA_RUN_TO_LOAD}")

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        print("💡 Make sure you've run the meta_data notebook and saved the data!")
        print(f"💡 Available meta_data runs:")
        meta_data_path = Path(META_DATA_DIR)
        if meta_data_path.exists():
            for run_dir in meta_data_path.glob("run_*"):
                print(f"   - {run_dir.name}")
        return False

    try:
        with open(test_file, "rb") as f:
            data = pickle.load(f)

        print(f"✅ Successfully loaded: {test_file}")
        print(f"📊 Data contains {len(data)} enriched elements")

        # Test element structure
        if data:
            sample_element = data[0]
            print(f"📋 Sample element structure:")
            print(f"  ID: {sample_element.get('id', 'N/A')}")
            print(f"  Type: {sample_element.get('element_type', 'N/A')}")
            print(
                f"  Has structural_metadata: {'structural_metadata' in sample_element}"
            )

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
    output_base_path = Path(OUTPUT_BASE_DIR)
    CURRENT_RUN_DIR = output_base_path / f"03_run_{timestamp}"

    # Create directories
    output_base_path.mkdir(parents=True, exist_ok=True)
    CURRENT_RUN_DIR.mkdir(exist_ok=True)

    # Construct paths from meta_data run configuration
    META_DATA_RUN_DIR = Path(META_DATA_DIR) / META_DATA_RUN_TO_LOAD
    INPUT_PICKLE_PATH = META_DATA_RUN_DIR / "meta_data_output.pkl"
    OUTPUT_PATH = CURRENT_RUN_DIR / "enrich_data_output.json"
    PICKLE_OUTPUT_PATH = CURRENT_RUN_DIR / "enrich_data_output.pkl"

    print(f"📁 Output directory: {CURRENT_RUN_DIR}")
    print(f"📁 Input from meta_data run: {META_DATA_RUN_TO_LOAD}")
    print(f"📁 Loading from: {INPUT_PICKLE_PATH}")
    print(f"📁 Enriched elements will be saved to: {OUTPUT_PATH}")

    print("🤖 VLM ENRICHMENT PIPELINE - META DATA VERSION")
    print("=" * 60)

    # Load enriched elements from meta_data
    enriched_elements = load_enriched_elements_from_meta(INPUT_PICKLE_PATH)

    if enriched_elements:
        print(f"📊 Input Summary:")
        print(f"  Enriched elements: {len(enriched_elements)}")

        # Initialize VLM captioner
        print(f"\n🤖 Initializing Claude 3.5 Sonnet captioner...")
        captioner = ConstructionVLMCaptioner()

        # Step 1: Enrich table elements
        print(f"\n" + "=" * 40)
        print("📊 STEP 1: TABLE ENRICHMENT")
        print("=" * 40)

        enriched_tables = enrich_table_elements_from_meta(enriched_elements, captioner)

        # Step 2: Enrich image elements
        print(f"\n" + "=" * 40)
        print("🖼️ STEP 2: IMAGE ENRICHMENT")
        print("=" * 40)

        enriched_images = enrich_image_elements_from_meta(enriched_elements, captioner)

        # Combine all enriched elements
        all_enriched_elements = enriched_tables + enriched_images

        print(f"\n" + "=" * 40)
        print("💾 SAVING ENRICHED ELEMENTS")
        print("=" * 40)

        # Show summary
        show_enrichment_summary(all_enriched_elements)

        # Save enriched elements
        save_enriched_elements(all_enriched_elements, OUTPUT_PATH, PICKLE_OUTPUT_PATH)

        print(f"\n🎉 VLM enrichment pipeline complete!")
        print(f"📁 Output Files Created:")
        print(f"   📂 Run directory: {CURRENT_RUN_DIR}")
        print(
            f"   📄 Enrich data output (pickle): {CURRENT_RUN_DIR / 'enrich_data_output.pkl'}"
        )
        print(
            f"   📄 Enrich data output (JSON): {CURRENT_RUN_DIR / 'enrich_data_output.json'}"
        )
        print(f"   🕒 Timestamp: {timestamp}")
        print(
            f"\n📁 Next: Use '{CURRENT_RUN_DIR / 'enrich_data_output.pkl'}' in your chunking/RAG pipeline"
        )

    else:
        print("❌ Cannot proceed without enriched elements")
        print("💡 First run the meta_data notebook to generate 'enriched_elements.pkl'")
