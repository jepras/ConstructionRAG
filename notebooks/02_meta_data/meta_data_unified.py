# ==============================================================================
# META DATA PROCESSING FOR UNIFIED PARTITIONING OUTPUT
# Adapter for the new unified_fast_vision strategy
# ==============================================================================

import os
import pickle
import json
from pathlib import Path
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

# --- Pydantic for Enhanced Metadata ---
from pydantic import BaseModel, Field
from typing import Literal

# ==============================================================================
# CONFIGURATION - SPECIFY WHICH UNIFIED PARTITION RUN TO LOAD
# ==============================================================================
UNIFIED_PARTITION_RUN_TO_LOAD = (
    "01_run_20250722_113203"  # Change this to load different unified partition runs
)

# ==============================================================================
# 1. ENHANCED METADATA MODELS (Same as original)
# ==============================================================================


class StructuralMetadata(BaseModel):
    """Enhanced metadata focusing on high-impact, easy-to-implement fields"""

    # Core metadata
    source_filename: str
    page_number: int
    content_type: Literal["text", "table", "full_page_with_images", "extracted_image"]

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

    # New fields for unified approach
    processing_strategy: str = "unified_fast_vision"
    element_id: Optional[str] = None  # Original element ID from unified processing
    image_filepath: Optional[str] = None  # For extracted images
    html_text: Optional[str] = None  # HTML representation for tables


# ==============================================================================
# 2. UNIFIED DATA LOADING FUNCTIONS
# ==============================================================================


def load_unified_partition_data(pickle_file_path: str):
    """Load unified partition data from the new approach"""
    print(f"📂 Loading unified partition data from: {pickle_file_path}")

    try:
        with open(pickle_file_path, "rb") as f:
            data = pickle.load(f)

        print(f"✅ Loaded unified data with keys: {list(data.keys())}")
        return data

    except FileNotFoundError:
        print(f"❌ File not found: {pickle_file_path}")
        print("Make sure you've run the unified_partition.py notebook first!")
        return None
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None


# ==============================================================================
# 3. UNIFIED ELEMENT PROCESSING
# ==============================================================================


class UnifiedElementAnalyzer:
    """Enhanced analyzer for unified partition data"""

    def __init__(self):
        # Simple patterns that work across languages
        self.number_patterns = {
            "measurement": re.compile(
                r'\d+[\.,]?\d*\s*(?:mm|cm|m|ft|in|inches|″|′|")', re.IGNORECASE
            ),
            "decimal_number": re.compile(r"\d+[\.,]\d+"),
            "whole_number": re.compile(
                r"\b\d{2,}\b"
            ),  # 2+ digit numbers (exclude single digits)
            "code_pattern": re.compile(r"[A-Z]-?\d+(?:\.\d+)?"),  # A-3, S-1, etc.
            "standard_code": re.compile(
                r"\b[A-Z]{2,}\s*\d+\b"
            ),  # DS 411, ISO 9001, etc.
        }

        # FOCUSED: Only numbered sections with meaningful content
        self.numbered_section_pattern = re.compile(
            r"^\s*.{0,15}?(\d+(?:\.\d+)*\.?)\s+(.{3,})"
        )

        # PAGE-AWARE TRACKING: Track section per page
        self.page_sections = {}  # page_num -> section_title
        self.current_page = None
        self.current_section_title = None

        # Track major sections (longer numbered sections like "1.2" or "10.")
        self.major_section_pattern = re.compile(
            r"^\s*.{0,15}?(\d+(?:\.\d+)?\.?)\s+([A-ZÆØÅ].{10,})", re.IGNORECASE
        )

    def analyze_text_element(self, text_element: dict) -> StructuralMetadata:
        """Analyze a text element from unified processing"""

        element = text_element["element"]
        element_id = text_element["id"]
        text = text_element["text"]
        category = text_element["category"]
        page_num = text_element["page"]
        metadata_dict = text_element["metadata"]

        # Track page changes
        if page_num != self.current_page:
            print(f"📄 Page change: {self.current_page} → {page_num}")
            self.current_page = page_num

        # Initialize metadata
        struct_meta = StructuralMetadata(
            source_filename=metadata_dict.get("filename", "Unknown"),
            page_number=page_num,
            content_type="text",
            element_category=category,
            element_id=element_id,
            processing_strategy="unified_fast_vision",
        )

        # Phase 1: High-impact, easy analysis
        struct_meta.content_length = len(text)
        struct_meta.has_numbers = self._detect_numbers(text)
        struct_meta.text_complexity = self._assess_text_complexity(text)

        # ENHANCED: Page-aware section title detection
        struct_meta = self._detect_section_titles_page_aware(
            struct_meta, text, category, page_num
        )

        return struct_meta

    def analyze_table_element(
        self, table_element, element_id: str
    ) -> StructuralMetadata:
        """Analyze a table element from unified processing"""

        text = getattr(table_element, "text", "")
        category = getattr(table_element, "category", "Table")
        metadata_dict = getattr(table_element, "metadata", {})

        if hasattr(metadata_dict, "to_dict"):
            metadata_dict = metadata_dict.to_dict()

        page_num = metadata_dict.get("page_number", 1)

        # Track page changes
        if page_num != self.current_page:
            print(f"📄 Page change: {self.current_page} → {page_num}")
            self.current_page = page_num

        # Extract HTML text from table if available
        html_text = None
        if hasattr(table_element, "html"):
            html_text = getattr(table_element, "html", "")
            if html_text:
                print(
                    f"    📋 Found HTML text for table {element_id} (length: {len(html_text)})"
                )
        elif hasattr(table_element, "metadata") and hasattr(
            table_element.metadata, "html"
        ):
            html_text = getattr(table_element.metadata, "html", "")
            if html_text:
                print(
                    f"    📋 Found HTML text for table {element_id} in metadata (length: {len(html_text)})"
                )

        # Initialize metadata
        struct_meta = StructuralMetadata(
            source_filename=metadata_dict.get("filename", "Unknown"),
            page_number=page_num,
            content_type="table",
            element_category=category,
            element_id=element_id,
            processing_strategy="unified_fast_vision",
            html_text=html_text,
        )

        # Phase 1: High-impact, easy analysis
        struct_meta.content_length = len(text)
        struct_meta.has_numbers = self._detect_numbers(text)
        struct_meta.has_tables_on_page = True
        struct_meta.text_complexity = "complex"  # Tables are typically complex

        # ENHANCED: Page-aware section title detection
        struct_meta = self._detect_section_titles_page_aware(
            struct_meta, text, category, page_num
        )

        return struct_meta

    def analyze_extracted_image(
        self, page_info: dict, element_id: str
    ) -> StructuralMetadata:
        """Analyze an extracted page image from unified processing"""

        page_num = page_info.get("page_number", 1)  # Extract from page_info
        filename = page_info.get("filename", "Unknown")
        filepath = page_info.get("filepath", "")
        complexity = page_info.get("complexity", "unknown")

        # Track page changes
        if page_num != self.current_page:
            print(f"📄 Page change: {self.current_page} → {page_num}")
            self.current_page = page_num

        # Initialize metadata
        struct_meta = StructuralMetadata(
            source_filename=filename,
            page_number=page_num,
            content_type="full_page_with_images",
            element_category="ExtractedPage",
            element_id=element_id,
            processing_strategy="unified_fast_vision",
            image_filepath=filepath,
        )

        # Phase 1: High-impact, easy analysis
        struct_meta.has_images_on_page = True
        struct_meta.text_complexity = "complex"  # Images are typically complex
        struct_meta.page_context = "image_page"

        # Get inherited section title
        page_section = self.page_sections.get(page_num)
        if page_section:
            struct_meta.section_title_inherited = page_section
        elif self.current_section_title:
            struct_meta.section_title_inherited = self.current_section_title

        return struct_meta

    def _starts_with_number(self, text: str) -> bool:
        """Check if text starts with a number pattern (1, 1.2, 1.2.1, 23.2, etc.)"""
        text = text.strip()

        # Pattern to match numbers at the start: 1, 1.2, 1.2.1, 23.2, etc.
        number_start_pattern = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s")

        return bool(number_start_pattern.match(text))

    def _detect_pattern_based_title(self, text: str, category: str) -> Optional[str]:
        """Detect ONLY numbered sections with meaningful content, filtered by element type"""

        text = text.strip()

        # Filter out element categories that shouldn't be sections
        if category in ["FigureCaption", "Footer"]:
            return None

        # ONLY numbered sections: "1.2 Something meaningful"
        numbered_match = self.numbered_section_pattern.match(text)
        if numbered_match:
            section_number = numbered_match.group(1)
            section_text = numbered_match.group(2).strip()

            # Position-based filter: number must appear in first 7 characters
            number_position = text.find(section_number)
            if number_position > 7:
                return None

            return f"{section_number} {section_text}"

        # Everything else is ignored
        return None

    def _detect_numbers(self, text: str) -> bool:
        """Detect if text contains measurements, codes, or significant numbers"""

        # Check for measurements (most important)
        if self.number_patterns["measurement"].search(text):
            return True

        # Check for decimal numbers (specifications)
        if self.number_patterns["decimal_number"].search(text):
            return True

        # Check for standard codes
        if self.number_patterns["standard_code"].search(text):
            return True

        # Check for drawing/detail codes
        if self.number_patterns["code_pattern"].search(text):
            return True

        # Check for multiple larger numbers (could be specifications)
        large_numbers = self.number_patterns["whole_number"].findall(text)
        if len(large_numbers) >= 2:  # Multiple numbers suggests technical content
            return True

        return False

    def _assess_text_complexity(self, text: str) -> str:
        """Simple text complexity assessment"""

        if not text.strip():
            return "simple"

        words = text.split()
        word_count = len(words)

        if word_count == 0:
            return "simple"

        # Average word length
        avg_word_length = sum(len(word.strip(".,!?;:")) for word in words) / word_count

        # Sentence count (rough)
        sentence_count = len([s for s in text.split(".") if s.strip()])
        avg_words_per_sentence = word_count / max(sentence_count, 1)

        # Simple scoring
        complexity_score = 0

        if avg_word_length > 6:  # Longer words suggest technical content
            complexity_score += 1

        if avg_words_per_sentence > 20:  # Long sentences suggest complex content
            complexity_score += 1

        if self._detect_numbers(text):  # Technical numbers suggest complexity
            complexity_score += 1

        if complexity_score >= 2:
            return "complex"
        elif complexity_score == 1:
            return "medium"
        else:
            return "simple"

    def _detect_section_titles_page_aware(
        self, struct_meta: StructuralMetadata, text: str, category: str, page_num: int
    ) -> StructuralMetadata:
        """Enhanced section detection with page-aware inheritance"""

        # Method 1: Category-based detection (ONLY for numbered titles)
        if category.lower() in ["title", "header"]:
            # Check if title starts with a number pattern
            if self._starts_with_number(text):
                struct_meta.section_title_category = text.strip()
                print(
                    f'    🏷️  DEBUG: Found numbered category title: "{text.strip()}" (category: {category})'
                )
            else:
                print(
                    f'    ⏭️  DEBUG: Skipping non-numbered title: "{text.strip()}" (category: {category})'
                )

        # Method 2: Pattern-based detection (ONLY for numbered sections)
        pattern_title = self._detect_pattern_based_title(text, category)
        if pattern_title:
            struct_meta.section_title_pattern = pattern_title
            print(
                f'    🔍 DEBUG: Found numbered pattern title: "{pattern_title}" (category: {category}, page: {page_num})'
            )
            print(f'         📝 Original text: "{text.strip()}"')

            # Check if this is a MAJOR section (should update page inheritance)
            is_major_section = self._is_major_section(text, category)

            if is_major_section:
                print(
                    f"         🎯 MAJOR NUMBERED SECTION: Updating page {page_num} inheritance"
                )
                print(
                    f'         🔄 Page {page_num}: "{self.page_sections.get(page_num)}" → "{pattern_title}"'
                )

                # Update page-level section
                self.page_sections[page_num] = pattern_title
                self.current_section_title = pattern_title
            else:
                print(
                    f"         📋 Minor numbered section: Not changing page inheritance"
                )

        # Method 3: Page-aware inheritance (NEW!)
        page_section = self.page_sections.get(page_num)
        if page_section:
            struct_meta.section_title_inherited = page_section
            print(f'    📥 Page {page_num} inherits: "{page_section}"')
        elif self.current_section_title:
            # Fall back to document-level inheritance
            struct_meta.section_title_inherited = self.current_section_title
            print(f'    📥 Document fallback: "{self.current_section_title}"')

        return struct_meta

    def _is_major_section(self, text: str, category: str) -> bool:
        """Determine if this is a major section that should update page inheritance"""

        # Filter out minor elements
        if category in ["FigureCaption", "Footer", "ListItem"]:
            return False

        # ONLY numbered sections can be major sections
        if not self._starts_with_number(text):
            return False

        # Check for major section patterns (numbered sections with meaningful content)
        if self.major_section_pattern.match(text.strip()):
            return True

        # Additional check: numbered sections that are long enough to be major
        if self._starts_with_number(text) and len(text.strip()) > 10:
            return True

        return False

    def reset_section_tracking(self):
        """Reset all tracking (call between documents)"""
        self.page_sections = {}
        self.current_page = None
        self.current_section_title = None


# ==============================================================================
# 4. UNIFIED PROCESSING FUNCTION
# ==============================================================================


def add_structural_awareness_unified(unified_data):
    """Add structural awareness to unified partition data"""

    print("🏗️ Adding Enhanced Structural Awareness to Unified Data...")
    print("   📊 Focus: Unified fast + vision strategy")
    print("   🔍 DEBUG: Processing text, tables, and extracted images")
    print("   🔢 Section inheritance: ONLY for numbered titles (1, 1.2, 1.2.1, etc.)")

    analyzer = UnifiedElementAnalyzer()
    enriched_elements = []
    current_id = 1

    # Process text elements
    text_elements = unified_data.get("text_elements", [])
    print(f"📝 Processing {len(text_elements)} text elements...")

    # Sort text elements by page number for proper inheritance
    sorted_text_elements = sorted(text_elements, key=lambda x: x["page"])

    for text_element in sorted_text_elements:
        try:
            structural_meta = analyzer.analyze_text_element(text_element)

            enriched_elements.append(
                {
                    "id": str(current_id),
                    "original_element": text_element,
                    "structural_metadata": structural_meta,
                    "element_type": "text",
                }
            )
            current_id += 1

        except Exception as e:
            print(f"  ❌ Error processing text element {text_element['id']}: {e}")

    # Process table elements
    table_elements = unified_data.get("table_elements", [])
    print(f"📊 Processing {len(table_elements)} table elements...")

    for table_element in table_elements:
        try:
            element_id = str(current_id)
            structural_meta = analyzer.analyze_table_element(table_element, element_id)

            enriched_elements.append(
                {
                    "id": element_id,
                    "original_element": table_element,
                    "structural_metadata": structural_meta,
                    "element_type": "table",
                }
            )
            current_id += 1

        except Exception as e:
            print(f"  ❌ Error processing table element: {e}")

    # Process extracted pages (full page images)
    extracted_pages = unified_data.get("extracted_pages", {})
    print(f"🖼️  Processing {len(extracted_pages)} extracted pages...")

    # Sort pages by page number for consistent numbering
    sorted_pages = sorted(extracted_pages.items(), key=lambda x: x[0])

    for page_num, page_info in sorted_pages:
        try:
            element_id = str(current_id)
            structural_meta = analyzer.analyze_extracted_image(page_info, element_id)

            enriched_elements.append(
                {
                    "id": element_id,
                    "original_element": page_info,
                    "structural_metadata": structural_meta,
                    "element_type": "full_page_with_images",
                }
            )
            current_id += 1

        except Exception as e:
            print(f"  ❌ Error processing page {page_num}: {e}")

    print(f"✅ Enhanced analysis complete!")
    print(f"   📊 Total enriched elements: {len(enriched_elements)}")

    # Show page section summary
    print(f"\n📋 PAGE SECTION SUMMARY:")
    for page_num, section in analyzer.page_sections.items():
        print(f'   Page {page_num}: "{section}"')

    return enriched_elements


# ==============================================================================
# 5. SAVING FUNCTIONS (Same as original)
# ==============================================================================


def save_enriched_elements(enriched_elements, json_output_path, pickle_output_path):
    """Save enriched elements for the chunking notebook"""

    print(f"💾 Saving enriched elements...")

    # Convert Pydantic models to dicts for JSON serialization with text content
    serializable_elements = []
    for element in enriched_elements:
        # Extract text content based on element type
        text_content = ""
        if element["element_type"] == "text":
            # For text elements, get text from the original_element
            original_element = element["original_element"]
            text_content = original_element.get("text", "")
        elif element["element_type"] == "table":
            # For table elements, get text from the unstructured element
            original_element = element["original_element"]
            text_content = getattr(original_element, "text", "")
            # HTML text is already included in structural_metadata.html_text
        elif element["element_type"] == "full_page_with_images":
            # For image pages, no text content
            text_content = "[IMAGE PAGE]"

        serializable_element = {
            "id": element["id"],
            "element_type": element["element_type"],
            "text_content": text_content,  # Include actual text content
            "structural_metadata": element["structural_metadata"].model_dump(),
        }
        serializable_elements.append(serializable_element)

    # Save pickle file (primary data transfer - includes full original elements)
    with open(pickle_output_path, "wb") as f:
        pickle.dump(enriched_elements, f)

    # Save JSON file (human-readable with text content)
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(serializable_elements, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved complete data to: {pickle_output_path}")
    print(f"✅ Saved metadata + text content to: {json_output_path}")


def _show_enhanced_summary(enriched_elements):
    """Show summary of enhanced metadata analysis including section detection"""

    print(f"\n📈 ENHANCED METADATA SUMMARY:")
    print("=" * 45)

    # Content type distribution
    content_types = {}
    element_types = {}
    categories = {}
    complexity_levels = {}

    numbers_count = 0
    total_length = 0

    # Section title statistics
    category_titles = 0
    inherited_titles = 0
    pattern_titles = 0
    elements_with_sections = 0

    for element in enriched_elements:
        meta = element["structural_metadata"]

        # Count distributions
        content_types[meta.content_type] = content_types.get(meta.content_type, 0) + 1
        element_types[element["element_type"]] = (
            element_types.get(element["element_type"], 0) + 1
        )
        categories[meta.element_category] = categories.get(meta.element_category, 0) + 1
        complexity_levels[meta.text_complexity] = (
            complexity_levels.get(meta.text_complexity, 0) + 1
        )

        # Aggregate stats
        if meta.has_numbers:
            numbers_count += 1
        total_length += meta.content_length

        # Section title statistics
        if meta.section_title_category:
            category_titles += 1
        if meta.section_title_inherited:
            inherited_titles += 1
        if meta.section_title_pattern:
            pattern_titles += 1
        if (
            meta.section_title_category
            or meta.section_title_inherited
            or meta.section_title_pattern
        ):
            elements_with_sections += 1

    print(f"📊 Content Types:")
    for content_type, count in content_types.items():
        print(f"   {content_type}: {count}")

    print(f"\n📂 Element Types:")
    for element_type, count in element_types.items():
        print(f"   {element_type}: {count}")

    print(f"\n📂 Element Categories (Top 8):")
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[
        :8
    ]:
        print(f"   {category}: {count}")

    print(f"\n🧠 Text Complexity:")
    for complexity, count in complexity_levels.items():
        print(f"   {complexity}: {count}")

    print(f"\n🔢 Number Detection:")
    print(
        f"   Elements with numbers: {numbers_count}/{len(enriched_elements)} ({numbers_count/len(enriched_elements)*100:.1f}%)"
    )

    print(f"\n📏 Content Statistics:")
    avg_length = total_length / len(enriched_elements) if enriched_elements else 0
    print(f"   Average content length: {avg_length:.0f} characters")

    print(f"\n📋 Section Title Detection:")
    print(f"   Category-based titles: {category_titles}")
    print(f"   Inherited titles: {inherited_titles}")
    print(f"   Pattern-based titles: {pattern_titles}")
    print(
        f"   Elements with sections: {elements_with_sections}/{len(enriched_elements)} ({elements_with_sections/len(enriched_elements)*100:.1f}%)"
    )

    print("\n💡 Enhanced Phase 1 fields successfully added!")
    print("🧪 Ready to test which section detection method works best!")


# ==============================================================================
# 6. TESTING AND MAIN EXECUTION
# ==============================================================================


def test_unified_data_access():
    """Quick test to verify we can access unified partition data"""

    print("🧪 TESTING UNIFIED DATA ACCESS")
    print("=" * 55)

    # Construct test file path using configuration
    PARTITION_DATA_DIR = Path("../../data/internal/01_partition_data")
    test_file = (
        PARTITION_DATA_DIR
        / UNIFIED_PARTITION_RUN_TO_LOAD
        / "unified_v2_partition_output.pkl"
    )

    print(f"📂 Looking for: {test_file}")
    print(f"📁 From unified partition run: {UNIFIED_PARTITION_RUN_TO_LOAD}")

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        print(
            "💡 Make sure you've run the unified_partition.py notebook and saved the data!"
        )
        print(f"💡 Available unified partition runs:")
        if PARTITION_DATA_DIR.exists():
            for run_dir in PARTITION_DATA_DIR.glob("01_run_*"):
                print(f"   - {run_dir.name}")
        return False

    try:
        with open(test_file, "rb") as f:
            data = pickle.load(f)

        print(f"✅ Successfully loaded: {test_file}")
        print(f"📊 Data contains keys: {list(data.keys())}")

        # Test each component
        text_elements = data.get("text_elements", [])
        table_elements = data.get("table_elements", [])
        raw_elements = data.get("raw_elements", [])
        extracted_pages = data.get("extracted_pages", {})
        metadata = data.get("metadata", {})

        print(f"\n📋 Unified Data Summary:")
        print(f"  📄 Source file: {metadata.get('source_file', 'Unknown')}")
        print(f"  📝 Text elements: {len(text_elements)}")
        print(f"  📦 Raw elements: {len(raw_elements)}")
        print(f"  📊 Table elements: {len(table_elements)}")
        print(f"  🖼️  Extracted pages: {len(extracted_pages)}")
        print(
            f"  🔍 Processing strategy: {metadata.get('processing_strategy', 'Unknown')}"
        )

        print(f"\n🎉 Unified data access test PASSED!")
        print(f"📱 Ready to proceed with structural analysis...")
        return True

    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False


# ==============================================================================
# 7. MAIN EXECUTION
# ==============================================================================

if __name__ == "__main__":
    # Run the test first
    if not test_unified_data_access():
        print(
            "\n🛑 Cannot proceed without valid unified data. Please fix the issues above."
        )
        exit()

    print("\n" + "=" * 60)

    # Configuration - Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_BASE_DIR = Path("../../data/internal/02_meta_data")
    CURRENT_RUN_DIR = OUTPUT_BASE_DIR / f"02_run_{timestamp}"

    # Create directories
    OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_RUN_DIR.mkdir(exist_ok=True)

    # Construct input path from unified partition run configuration
    PARTITION_DATA_DIR = Path("../../data/internal/01_partition_data")
    INPUT_PICKLE_PATH = (
        PARTITION_DATA_DIR
        / UNIFIED_PARTITION_RUN_TO_LOAD
        / "unified_v2_partition_output.pkl"
    )
    OUTPUT_PATH = CURRENT_RUN_DIR / "unified_meta_data_output.json"
    PICKLE_OUTPUT_PATH = CURRENT_RUN_DIR / "unified_meta_data_output.pkl"

    print(f"📁 Output directory: {CURRENT_RUN_DIR}")
    print(f"📁 Input from unified partition run: {UNIFIED_PARTITION_RUN_TO_LOAD}")
    print(f"📁 Loading from: {INPUT_PICKLE_PATH}")
    print(f"📁 Enriched elements will be saved to: {OUTPUT_PATH}")

    print("🏗️ UNIFIED CONSTRUCTION DOCUMENT STRUCTURAL AWARENESS")
    print("=" * 60)

    # Load unified partition data
    unified_data = load_unified_partition_data(INPUT_PICKLE_PATH)

    if unified_data:
        metadata = unified_data.get("metadata", {})

        print(f"📊 Input Summary:")
        print(f"  📄 Source file: {metadata.get('source_file', 'Unknown')}")
        print(f"  📝 Text elements: {metadata.get('text_count', 0)}")
        print(f"  📦 Raw elements: {metadata.get('raw_count', 0)}")
        print(f"  📊 Tables detected: {metadata.get('table_count', 0)}")
        print(f"  🖼️  Images detected: {metadata.get('image_count', 0)}")
        print(f"  🔍 Enhanced tables: {metadata.get('enhanced_tables', 0)}")
        print(f"  💾 Extracted pages: {metadata.get('extracted_pages', 0)}")

        # Add enhanced structural awareness
        enriched_elements = add_structural_awareness_unified(unified_data)

        # Show sample results
        print(f"\n📋 Sample Enhanced Analysis:")
        for element in enriched_elements[:3]:
            meta = element["structural_metadata"]
            print(f"  Element: {element['id']}")
            print(f"    Type: {meta.content_type}")
            print(f"    Page: {meta.page_number}")
            print(f"    Section (inherited): {meta.section_title_inherited}")
            print(f"    Section (pattern): {meta.section_title_pattern}")
            print("    " + "-" * 30)

        # Show enhanced summary
        _show_enhanced_summary(enriched_elements)

        # Save enriched elements
        save_enriched_elements(enriched_elements, OUTPUT_PATH, PICKLE_OUTPUT_PATH)

        print(f"\n🎉 Unified structural awareness complete!")
        print(f"📁 Output Files Created:")
        print(f"   📂 Run directory: {CURRENT_RUN_DIR}")
        print(
            f"   📄 Meta data output (pickle): {CURRENT_RUN_DIR / 'unified_meta_data_output.pkl'}"
        )
        print(
            f"   📄 Meta data + text output (JSON): {CURRENT_RUN_DIR / 'unified_meta_data_output.json'}"
        )
        print(f"   🕒 Timestamp: {timestamp}")
        print(f"\n📋 Output Contents:")
        print(f"   📄 Pickle: Complete enriched elements with original data")
        print(f"   📄 JSON: Structural metadata + text content for analysis")
        print(
            f"\n📁 Next: Use '{CURRENT_RUN_DIR / 'unified_meta_data_output.pkl'}' in your enrich_data notebook"
        )

    else:
        print("❌ Cannot proceed without unified partition data")
        print(
            "💡 First run the unified_partition.py notebook to generate unified partition data"
        )
