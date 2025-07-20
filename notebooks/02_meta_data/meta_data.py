# ==============================================================================
# COMPLETE ENHANCED STRUCTURAL AWARENESS NOTEBOOK
# Enhanced section inheritance with page-aware tracking
# ==============================================================================

import os
import pickle
import json
from pathlib import Path
import re
from typing import Dict, List, Any, Optional

# --- Pydantic for Enhanced Metadata ---
from pydantic import BaseModel, Field
from typing import Literal

# ==============================================================================
# CONFIGURATION - SPECIFY WHICH PARTITION RUN TO LOAD
# ==============================================================================
PARTITION_RUN_TO_LOAD = (
    "run_20250720_080612"  # Change this to load different partition runs
)

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


# ==============================================================================
# 2. LOADING FUNCTIONS
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
# 3. ENHANCED SECTION INHERITANCE - PAGE AWARE VERSION
# ==============================================================================


class ConstructionElementAnalyzer:
    """Enhanced analyzer with page-aware section inheritance"""

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

    def analyze_element_structure(
        self, element, element_id: str, page_analysis: dict, extracted_pages: dict
    ) -> StructuralMetadata:
        """Analyze element with page-aware section inheritance"""

        text = getattr(element, "text", "")
        category = getattr(element, "category", "Unknown")
        metadata_dict = getattr(element, "metadata", {})
        if hasattr(metadata_dict, "to_dict"):
            metadata_dict = metadata_dict.to_dict()

        page_num = metadata_dict.get("page_number", 1)

        # Track page changes
        if page_num != self.current_page:
            print(f"📄 Page change: {self.current_page} → {page_num}")
            self.current_page = page_num

        # Initialize metadata
        struct_meta = StructuralMetadata(
            source_filename=metadata_dict.get("filename", "Unknown"),
            page_number=page_num,
            content_type=self._determine_content_type(element, metadata_dict),
            element_category=category,
        )

        # Phase 1: High-impact, easy analysis
        struct_meta.page_context = self._determine_page_context(
            page_num, page_analysis, extracted_pages
        )
        struct_meta.content_length = len(text)
        struct_meta.has_numbers = self._detect_numbers(text)
        struct_meta.has_tables_on_page = self._page_has_tables(page_num, page_analysis)
        struct_meta.has_images_on_page = self._page_has_images(
            page_num, page_analysis, extracted_pages
        )
        struct_meta.text_complexity = self._assess_text_complexity(text)

        # ENHANCED: Page-aware section title detection
        struct_meta = self._detect_section_titles_page_aware(
            struct_meta, text, category, page_num
        )

        return struct_meta

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

    def _determine_content_type(self, element, metadata_dict):
        """Determine enhanced content type"""
        category = getattr(element, "category", "Unknown")

        if "image_filepath" in metadata_dict:
            return "full_page_with_images"
        elif category == "Table":
            return "table"
        else:
            return "text"

    def _determine_page_context(
        self, page_num: int, page_analysis: dict, extracted_pages: dict
    ) -> str:
        """Determine what type of page this element comes from"""

        # Check if this page was extracted as an image
        if page_num in extracted_pages:
            return "image_page"

        # Check page analysis for image content
        page_info = page_analysis.get(page_num, {})
        image_count = page_info.get("image_count", 0)

        if image_count == 0:
            return "text_only_page"
        elif image_count >= 3:
            return "page_with_many_images"
        else:
            return "page_with_images"

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

    def _page_has_tables(self, page_num: int, page_analysis: dict) -> bool:
        """Check if this page contains tables (simplified - would need full element scan)"""
        # This is a placeholder - in reality we'd need to scan all elements on this page
        # For now, return False, but this could be enhanced
        return False

    def _page_has_images(
        self, page_num: int, page_analysis: dict, extracted_pages: dict
    ) -> bool:
        """Check if this page contains images"""

        # Check if page was extracted as image page
        if page_num in extracted_pages:
            return True

        # Check page analysis
        page_info = page_analysis.get(page_num, {})
        return page_info.get("image_count", 0) > 0

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

        # Method 1: Category-based detection (unchanged)
        if category.lower() in ["title", "header"]:
            struct_meta.section_title_category = text.strip()
            print(
                f'    🏷️  DEBUG: Found category title: "{text.strip()}" (category: {category})'
            )

        # Method 2: Pattern-based detection (enhanced with page tracking)
        pattern_title = self._detect_pattern_based_title(text, category)
        if pattern_title:
            struct_meta.section_title_pattern = pattern_title
            print(
                f'    🔍 DEBUG: Found pattern title: "{pattern_title}" (category: {category}, page: {page_num})'
            )
            print(f'         📝 Original text: "{text.strip()}"')

            # Check if this is a MAJOR section (should update page inheritance)
            is_major_section = self._is_major_section(text, category)

            if is_major_section:
                print(
                    f"         🎯 MAJOR SECTION: Updating page {page_num} inheritance"
                )
                print(
                    f'         🔄 Page {page_num}: "{self.page_sections.get(page_num)}" → "{pattern_title}"'
                )

                # Update page-level section
                self.page_sections[page_num] = pattern_title
                self.current_section_title = pattern_title
            else:
                print(f"         📋 Minor section: Not changing page inheritance")

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

        # Check for major section patterns
        if self.major_section_pattern.match(text.strip()):
            return True

        # Special patterns for your document
        if any(
            keyword in text.lower() for keyword in ["tema:", "demonstrationsejendommen"]
        ):
            return True

        return False

    def process_image_pages_with_context(self, extracted_pages: dict) -> list:
        """Process image pages with proper page-aware inheritance"""

        print(
            f"🖼️ Processing {len(extracted_pages)} image pages with page-aware inheritance..."
        )

        image_elements = []

        for page_num, page_info in extracted_pages.items():
            element_id = f"image_page_{page_num}"

            print(f"\n🔍 DEBUG Image Page {page_num}:")
            print(f"    Filepath: {page_info.get('filepath', 'Unknown')}")
            print(f"    Complexity: {page_info.get('complexity', 'Unknown')}")

            # Get page-specific section (PRIORITY: page-level section first)
            page_section = self.page_sections.get(page_num)
            inherited_section = page_section or self.current_section_title

            print(
                f"    📋 Page {page_num} sections: {self.page_sections.get(page_num)}"
            )
            print(f'    📥 Final inheritance: "{inherited_section}"')

            # Create metadata for image page
            image_meta = StructuralMetadata(
                source_filename=Path(page_info["filepath"]).name,
                page_number=page_num,
                content_type="full_page_with_images",
                page_context="image_page",
                element_category="ImagePage",
                content_length=0,
                has_numbers=True,
                has_images_on_page=True,
                text_complexity="complex",
                section_title_inherited=inherited_section,
            )

            image_elements.append(
                {
                    "id": element_id,
                    "original_element": page_info,
                    "structural_metadata": image_meta,
                    "element_type": "image_page",
                }
            )

        return image_elements

    def reset_section_tracking(self):
        """Reset all tracking (call between documents)"""
        self.page_sections = {}
        self.current_page = None
        self.current_section_title = None


# ==============================================================================
# UPDATED MAIN PROCESSING FUNCTION
# ==============================================================================


def add_structural_awareness_enhanced(raw_elements, extracted_pages, page_analysis):
    """Enhanced structural awareness with page-aware section inheritance"""

    print("🏗️ Adding Enhanced Structural Awareness...")
    print("   📊 Focus: Page-aware section inheritance")
    print("   🔍 DEBUG: Tracking section inheritance by page")

    analyzer = ConstructionElementAnalyzer()
    enriched_elements = []

    # Filter and process regular elements
    filtered_elements = [
        el for el in raw_elements if getattr(el, "category", "") != "Image"
    ]
    skipped_images = len(raw_elements) - len(filtered_elements)

    print(f"📝 Processing {len(filtered_elements)} text/table elements...")
    print(f"🗑️ Filtered out {skipped_images} image fragments")

    # Sort elements by page number first (CRITICAL FIX!)
    def get_page_number(element):
        metadata_dict = getattr(element, "metadata", {})
        if hasattr(metadata_dict, "to_dict"):
            metadata_dict = metadata_dict.to_dict()
        return metadata_dict.get("page_number", 1)

    sorted_elements = sorted(filtered_elements, key=get_page_number)
    print(f"📄 Sorted elements by page number for proper inheritance")

    for i, element in enumerate(sorted_elements):
        element_id = f"element_{i}"
        text = getattr(element, "text", "").strip()
        category = getattr(element, "category", "Unknown")
        page_num = get_page_number(element)

        try:
            structural_meta = analyzer.analyze_element_structure(
                element, element_id, page_analysis, extracted_pages
            )

            enriched_elements.append(
                {
                    "id": element_id,
                    "original_element": element,
                    "structural_metadata": structural_meta,
                    "element_type": "text_or_table",
                }
            )

            if (i + 1) % 20 == 0:
                print(f"   ✅ Processed {i + 1}/{len(sorted_elements)} elements")

        except Exception as e:
            print(f"  ❌ Error processing element {i}: {e}")

    # Process image pages with enhanced context
    image_elements = analyzer.process_image_pages_with_context(extracted_pages)
    enriched_elements.extend(image_elements)

    print(f"✅ Enhanced analysis complete!")
    print(f"   📊 Total enriched elements: {len(enriched_elements)}")

    # Show page section summary
    print(f"\n📋 PAGE SECTION SUMMARY:")
    for page_num, section in analyzer.page_sections.items():
        print(f'   Page {page_num}: "{section}"')

    return enriched_elements


# ==============================================================================
# 4. SAVING FUNCTIONS
# ==============================================================================


def save_enriched_elements(enriched_elements, output_path):
    """Save enriched elements for the chunking notebook"""

    print(f"💾 Saving enriched elements to: {output_path}")

    # Convert Pydantic models to dicts for JSON serialization
    serializable_elements = []
    for element in enriched_elements:
        serializable_element = {
            "id": element["id"],
            "element_type": element["element_type"],
            "structural_metadata": element["structural_metadata"].model_dump(),
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


def _show_enhanced_summary(enriched_elements):
    """Show summary of enhanced metadata analysis including section detection"""

    print(f"\n📈 ENHANCED METADATA SUMMARY:")
    print("=" * 45)

    # Content type distribution
    content_types = {}
    page_contexts = {}
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
        page_contexts[meta.page_context] = page_contexts.get(meta.page_context, 0) + 1
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

    print(f"\n🌍 Page Contexts:")
    for context, count in page_contexts.items():
        print(f"   {context}: {count}")

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
# 5. TESTING AND MAIN EXECUTION
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
        print(f"📱 Ready to proceed with structural analysis...")
        return True

    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False


# ==============================================================================
# 6. MAIN EXECUTION
# ==============================================================================


import pandas as pd
import csv
from datetime import datetime


def export_elements_to_csv(
    enriched_elements, output_filename="enhanced_elements_analysis.csv"
):
    """Export enriched elements to CSV for analysis"""

    print(f"📊 Exporting enhanced elements to CSV...")

    # Prepare data for CSV export
    export_data = []

    for element in enriched_elements:
        element_id = element["id"]
        element_type = element["element_type"]
        meta = element["structural_metadata"]
        original_element = element["original_element"]

        # Get text content (if available)
        if element_type == "text_or_table":
            text_content = getattr(original_element, "text", "").strip()
            # Truncate long text for CSV readability
            text_preview = (
                text_content[:200] + "..." if len(text_content) > 200 else text_content
            )
            filepath = None
        else:  # image_page
            text_content = ""
            text_preview = "[IMAGE PAGE]"
            filepath = original_element.get("filepath", "Unknown")

        # Create row for CSV
        row = {
            # Basic identification
            "element_id": element_id,
            "element_type": element_type,
            "page_number": meta.page_number,
            "source_filename": meta.source_filename,
            # Content information
            "content_type": meta.content_type,
            "element_category": meta.element_category,
            "text_preview": text_preview,
            "content_length": meta.content_length,
            "filepath": filepath,
            # Structural metadata
            "page_context": meta.page_context,
            "has_numbers": meta.has_numbers,
            "has_tables_on_page": meta.has_tables_on_page,
            "has_images_on_page": meta.has_images_on_page,
            "text_complexity": meta.text_complexity,
            # Section information
            "section_category": meta.section_title_category,
            "section_inherited": meta.section_title_inherited,
            "section_pattern": meta.section_title_pattern,
            # Full text (for detailed analysis)
            "full_text": text_content,
        }

        export_data.append(row)

    # Create DataFrame and export
    df = pd.DataFrame(export_data)

    # Sort by page number and element type for better readability
    df = df.sort_values(["page_number", "content_type", "element_id"])

    # Export to CSV
    df.to_csv(output_filename, index=False, encoding="utf-8")

    print(f"✅ Exported {len(export_data)} elements to: {output_filename}")

    # Show summary statistics
    print(f"\n📈 EXPORT SUMMARY:")
    print(f"   Total elements: {len(export_data)}")
    print(f"   Text elements: {len(df[df['content_type'] == 'text'])}")
    print(f"   Table elements: {len(df[df['content_type'] == 'table'])}")
    print(f"   Image pages: {len(df[df['content_type'] == 'full_page_with_images'])}")
    print(f"   Pages covered: {df['page_number'].nunique()}")

    # Show content type distribution
    print(f"\n📊 Content Type Distribution:")
    content_counts = df["content_type"].value_counts()
    for content_type, count in content_counts.items():
        print(f"   {content_type}: {count}")

    # Show element category distribution
    print(f"\n📂 Element Category Distribution:")
    category_counts = df["element_category"].value_counts()
    for category, count in category_counts.head(8).items():
        print(f"   {category}: {count}")

    return df


def export_filtered_samples(enriched_elements, output_filename="samples_analysis.csv"):
    """Export specific samples: 5 text types + all tables + all images"""

    print(f"🎯 Exporting filtered samples...")

    # Categorize elements
    text_elements = []
    table_elements = []
    image_elements = []

    # Track text categories for diversity
    text_categories = {}

    for element in enriched_elements:
        element_type = element["element_type"]
        meta = element["structural_metadata"]

        if meta.content_type == "table":
            table_elements.append(element)
        elif meta.content_type == "full_page_with_images":
            image_elements.append(element)
        elif meta.content_type == "text":
            category = meta.element_category
            if category not in text_categories:
                text_categories[category] = []
            text_categories[category].append(element)

    # Select 5 diverse text types (max 2 examples each)
    selected_text = []
    for category, elements in sorted(text_categories.items()):
        # Take up to 2 examples from each category
        sample_size = min(2, len(elements))
        selected_text.extend(elements[:sample_size])
        if len(selected_text) >= 10:  # Ensure we get enough variety
            break

    # Limit to 5 text examples for manageability
    selected_text = selected_text[:5]

    # Combine all selected elements
    all_selected = selected_text + table_elements + image_elements

    print(f"📋 Selected Elements:")
    print(
        f"   Text samples: {len(selected_text)} (from {len(text_categories)} categories)"
    )
    print(f"   Table elements: {len(table_elements)}")
    print(f"   Image pages: {len(image_elements)}")
    print(f"   Total selected: {len(all_selected)}")

    # Export using the main function
    if all_selected:
        df = export_elements_to_csv(all_selected, output_filename)

        print(f"\n🎯 Sample Categories Included:")
        for category in df["element_category"].unique():
            count = len(df[df["element_category"] == category])
            print(f"   {category}: {count}")

        return df
    else:
        print(f"❌ No elements to export")
        return None


# ==============================================================================
# ADD THIS TO THE END OF YOUR MAIN EXECUTION BLOCK
# ==============================================================================

# Add this right before the final print statements in your main execution:


if __name__ == "__main__":
    # Run the test first
    if not test_data_access():
        print("\n🛑 Cannot proceed without valid data. Please fix the issues above.")
        exit()

    print("\n" + "=" * 60)

    # Configuration - Create timestamped output directory like partition_pdf.py
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_BASE_DIR = Path("../../data/internal/02_meta_data")
    CURRENT_RUN_DIR = OUTPUT_BASE_DIR / f"run_{timestamp}"

    # Create directories
    OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_RUN_DIR.mkdir(exist_ok=True)

    # Construct input path from partition run configuration
    PARTITION_DATA_DIR = Path("../../data/internal/01_partition_data")
    INPUT_PICKLE_PATH = (
        PARTITION_DATA_DIR / PARTITION_RUN_TO_LOAD / "processed_elements.pkl"
    )
    OUTPUT_PATH = CURRENT_RUN_DIR / "enriched_elements.json"

    print(f"📁 Output directory: {CURRENT_RUN_DIR}")
    print(f"📁 Input from partition run: {PARTITION_RUN_TO_LOAD}")
    print(f"📁 Loading from: {INPUT_PICKLE_PATH}")
    print(f"📁 Enriched elements will be saved to: {OUTPUT_PATH}")

    print("🏗️ ENHANCED CONSTRUCTION DOCUMENT STRUCTURAL AWARENESS")
    print("=" * 60)

    # Load pre-processed elements
    data = load_processed_elements(INPUT_PICKLE_PATH)

    if data:
        raw_elements = data.get("raw_elements", [])
        extracted_pages = data.get("extracted_pages", {})
        page_analysis = data.get("page_analysis", {})

        print(f"📊 Input Summary:")
        print(f"  Raw elements: {len(raw_elements)}")
        print(f"  Extracted pages: {len(extracted_pages)}")
        print(f"  Analyzed pages: {len(page_analysis)}")

        # Add enhanced structural awareness
        enriched_elements = add_structural_awareness_enhanced(
            raw_elements, extracted_pages, page_analysis
        )

        # Show sample results
        print(f"\n📋 Sample Enhanced Analysis:")
        for element in enriched_elements[:3]:
            meta = element["structural_metadata"]
            print(f"  Element: {element['id']}")
            print(f"    Type: {meta.content_type}")
            print(f"    Page: {meta.page_number}")
            print(f"    Page Context: {meta.page_context}")
            print(f"    Section (inherited): {meta.section_title_inherited}")
            print(f"    Section (pattern): {meta.section_title_pattern}")
            print("    " + "-" * 30)

        # Show enhanced summary
        _show_enhanced_summary(enriched_elements)

        # Save enriched elements
        save_enriched_elements(enriched_elements, OUTPUT_PATH)

        # After save_enriched_elements(enriched_elements, OUTPUT_PATH)
        print(f"\n" + "=" * 60)
        print("📊 EXPORTING TO CSV FOR ANALYSIS")
        print("=" * 60)

        # Export all elements to the timestamped directory
        # full_df = export_elements_to_csv(enriched_elements, CURRENT_RUN_DIR / "all_enhanced_elements.csv")

        # Export filtered samples (5 text types + all tables + all images)
        sample_df = export_filtered_samples(
            enriched_elements, CURRENT_RUN_DIR / "sample_analysis.csv"
        )

        print(f"\n📁 CSV Files Created:")
        print(
            f"   📊 Complete analysis: {CURRENT_RUN_DIR / 'all_enhanced_elements.csv'}"
        )
        print(f"   🎯 Filtered samples: {CURRENT_RUN_DIR / 'sample_analysis.csv'}")
        print(f"\n💡 Use these CSV files for:")
        print(f"   • Quality assessment of metadata")
        print(f"   • Section inheritance validation")
        print(f"   • Content type distribution analysis")
        print(f"   • RAG pipeline optimization")

        print(f"\n🎉 Enhanced structural awareness complete!")
        print(f"📁 Output Files Created:")
        print(f"   📂 Run directory: {CURRENT_RUN_DIR}")
        print(
            f"   📄 Enriched elements (pickle): {CURRENT_RUN_DIR / 'enriched_elements.pkl'}"
        )
        print(
            f"   📄 Enriched elements (JSON): {CURRENT_RUN_DIR / 'enriched_elements.json'}"
        )
        print(f"   📊 Sample analysis CSV: {CURRENT_RUN_DIR / 'sample_analysis.csv'}")
        print(f"   🕒 Timestamp: {timestamp}")
        print(
            f"\n📁 Next: Use '{CURRENT_RUN_DIR / 'enriched_elements.pkl'}' in your chunking notebook"
        )

    else:
        print("❌ Cannot proceed without processed elements")
        print(
            "💡 First run the partitioning notebook to generate 'processed_elements.pkl'"
        )
# ==============================================================================
# CSV EXPORT FOR ENHANCED ELEMENTS ANALYSIS
# Add this to the end of your enhanced structural awareness notebook
# ==============================================================================
