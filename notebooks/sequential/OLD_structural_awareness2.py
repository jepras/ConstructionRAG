# ==============================================================================
# STRUCTURAL AWARENESS NOTEBOOK
# Purpose: Add construction document structure awareness to pre-processed elements
# Input: Pickled elements from partitioning notebook
# Output: Enriched elements with structural metadata
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


class ConstructionElementAnalyzer:
    """Analyzes construction document elements for high-impact structural patterns"""

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

        # FOCUSED: Only numbered sections with meaningful content (allows 15-char prefix + trailing periods)
        self.numbered_section_pattern = re.compile(
            r"^\s*.{0,15}?(\d+(?:\.\d+)*\.?)\s+(.{3,})"
        )

        # For tracking section inheritance
        self.current_section_title = None

    def analyze_element_structure(
        self, element, element_id: str, page_analysis: dict, extracted_pages: dict
    ) -> StructuralMetadata:
        """Analyze element for Phase 1 metadata fields + section detection"""

        text = getattr(element, "text", "")
        category = getattr(element, "category", "Unknown")
        metadata_dict = getattr(element, "metadata", {})
        if hasattr(metadata_dict, "to_dict"):
            metadata_dict = metadata_dict.to_dict()

        page_num = metadata_dict.get("page_number", 1)

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

        # Section title detection (3 approaches) - pass category for filtering
        struct_meta = self._detect_section_titles(struct_meta, text, category)

        return struct_meta

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

    def _detect_section_titles(
        self, struct_meta: StructuralMetadata, text: str, category: str
    ) -> StructuralMetadata:
        """Detect section titles using 3 different approaches + debugging"""

        # Method 1: Category-based detection (detect but don't change inheritance)
        if category.lower() in ["title", "header"]:
            struct_meta.section_title_category = text.strip()
            # DEBUG: Show what we found
            print(
                f'    🏷️  DEBUG: Found category title: "{text.strip()}" (category: {category})'
            )

        # Method 2: Inheritance from previous titles (no change here)
        if self.current_section_title:
            struct_meta.section_title_inherited = self.current_section_title

        # Method 3: Pattern-based detection (ONLY these change inheritance)
        pattern_title = self._detect_pattern_based_title(text, category)
        if pattern_title:
            struct_meta.section_title_pattern = pattern_title
            # DEBUG: Show what we found
            print(
                f'    🔍 DEBUG: Found pattern title: "{pattern_title}" (category: {category})'
            )
            print(f'         📝 Original text: "{text.strip()}"')

            # OPTION B: Only pattern-based titles change inheritance
            print(
                f'         🔄 CHANGING inheritance from "{self.current_section_title}" to "{pattern_title}"'
            )
            self.current_section_title = pattern_title

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

    def reset_section_tracking(self):
        """Reset section inheritance tracking (call between documents)"""
        self.current_section_title = None


# ==============================================================================
# 2. MAIN PROCESSING FUNCTIONS
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


def add_structural_awareness(raw_elements, extracted_pages, page_analysis):
    """Add Phase 1 structural awareness with filtering, section detection, and debugging"""

    print("🏗️ Adding Phase 1 structural awareness...")
    print("   📊 Focus: High-impact metadata + section detection")
    print("   🗑️ Filtering out unstructured image fragments")
    print("   🔍 DEBUG: Tracking numbered section detection")

    analyzer = ConstructionElementAnalyzer()
    enriched_elements = []

    # Filter and process regular elements from unstructured
    filtered_elements = [
        el for el in raw_elements if getattr(el, "category", "") != "Image"
    ]
    skipped_images = len(raw_elements) - len(filtered_elements)

    print(f"📝 Processing {len(filtered_elements)} text/table elements...")
    print(f"🗑️ Filtered out {skipped_images} image fragments")

    for i, element in enumerate(filtered_elements):
        element_id = f"element_{i}"
        text = getattr(element, "text", "").strip()
        category = getattr(element, "category", "Unknown")
        page_num = (
            getattr(element, "metadata", {}).get("page_number", 1)
            if hasattr(getattr(element, "metadata", {}), "get")
            else 1
        )

        # DEBUG: Check for numbered patterns in text elements
        if text and len(text) > 3:
            pattern_match = analyzer.numbered_section_pattern.match(text)
            if pattern_match or any(
                keyword in text.lower()
                for keyword in ["tema:", "emne:", "principper", "figur"]
            ):
                print(f"🔍 DEBUG Element {element_id} (Page {page_num}, {category}):")
                print(f'    Text: "{text}"')
                print(f"    Text length: {len(text)}")
                print(f"    Pattern match: {bool(pattern_match)}")
                if pattern_match:
                    print(f"    Match groups: {pattern_match.groups()}")
                    print(f"    Group 1 (number): '{pattern_match.group(1)}'")
                    print(f"    Group 2 (content): '{pattern_match.group(2)}'")
                    print(f"    Content length: {len(pattern_match.group(2))}")
                else:
                    # Try to debug why it didn't match
                    print(f"    🔍 Detailed regex analysis:")
                    print(f"      Starts with whitespace/prefix: {text[:16]}")
                    # Look for numbers in the text
                    import re

                    numbers_found = re.findall(r"\d+(?:\.\d+)*\.?", text)
                    print(f"      Numbers found: {numbers_found}")

                    # Test just the number part
                    if numbers_found:
                        for num in numbers_found:
                            # Find the position of this number
                            pos = text.find(num)
                            before = text[:pos]
                            after = text[pos + len(num) :]
                            print(f"        Number '{num}' at pos {pos}")
                            print(f"        Before: '{before}' (length: {len(before)})")
                            print(
                                f"        After: '{after}' (starts with space: {after.startswith(' ')})"
                            )

                            # Check if this would match our pattern
                            if (
                                len(before) <= 15
                                and after.startswith(" ")
                                and len(after.strip()) >= 3
                            ):
                                print(
                                    f"        ✅ Should match: prefix≤15, has space, content≥3"
                                )
                            else:
                                print(
                                    f"        ❌ Won't match: prefix={len(before)}, space={after.startswith(' ')}, content={len(after.strip())}"
                                )

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

            # Progress indicator for large documents
            if (i + 1) % 50 == 0:
                print(f"   ✅ Processed {i + 1}/{len(filtered_elements)} elements")

        except Exception as e:
            print(f"  ❌ Error processing element {i}: {e}")

    # Process image pages WITH PATTERN DETECTION
    print(f"🖼️ Processing {len(extracted_pages)} image pages...")
    print(f"🔍 DEBUG: Checking image pages for numbered sections...")

    for page_num, page_info in extracted_pages.items():
        element_id = f"image_page_{page_num}"

        print(f"\n🔍 DEBUG Image Page {page_num}:")
        print(f"    Filepath: {page_info.get('filepath', 'Unknown')}")
        print(f"    Complexity: {page_info.get('complexity', 'Unknown')}")

        # Create metadata for image page
        image_meta = StructuralMetadata(
            source_filename=Path(page_info["filepath"]).name,
            page_number=page_num,
            content_type="full_page_with_images",
            page_context="image_page",
            element_category="ImagePage",
            content_length=0,  # Images don't have text length
            has_numbers=True,  # Assume technical drawings contain numbers
            has_images_on_page=True,
            text_complexity="complex",  # Technical drawings are complex
            # Add section inheritance
            section_title_inherited=analyzer.current_section_title,
        )

        print(f'    📥 Image page inherits section: "{analyzer.current_section_title}"')
        print(f"    💡 VLM caption can later override/refine this section context")

        enriched_elements.append(
            {
                "id": element_id,
                "original_element": page_info,
                "structural_metadata": image_meta,
                "element_type": "image_page",
            }
        )

    print(f"✅ Enhanced analysis complete!")
    print(f"   📊 Total enriched elements: {len(enriched_elements)}")
    print(f"   🗑️ Removed {skipped_images} image fragments")

    # Show enhanced summary statistics
    _show_enhanced_summary(enriched_elements)

    return enriched_elements


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


def save_enriched_elements(enriched_elements, output_path: str):
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

    # Save as both pickle (complete) and JSON (metadata only)
    pickle_path = output_path.replace(".json", ".pkl")

    with open(pickle_path, "wb") as f:
        pickle.dump(enriched_elements, f)

    with open(output_path, "w") as f:
        json.dump(serializable_elements, f, indent=2)

    print(f"✅ Saved complete data to: {pickle_path}")
    print(f"✅ Saved metadata to: {output_path}")


# ==============================================================================
# 3. QUICK DATA ACCESS TEST
# ==============================================================================


def test_data_access():
    """Quick test to verify we can access saved data from partitioning notebook"""

    print("🧪 TESTING DATA ACCESS FROM PARTITIONING NOTEBOOK")
    print("=" * 55)

    test_file = "processed_elements.pkl"

    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        print("💡 Make sure you've run the partitioning notebook and saved the data!")
        print("💡 Add this to the end of your partitioning notebook:")
        print(
            """
import pickle
data_to_save = {
    'raw_elements': raw_pdf_elements,
    'extracted_pages': extracted_pages,
    'page_analysis': page_analysis,
    'filepath': filepath
}
with open('processed_elements.pkl', 'wb') as f:
    pickle.dump(data_to_save, f)
print("✅ Saved processed elements for structural analysis")
        """
        )
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

        # Show sample element
        if raw_elements:
            sample_element = raw_elements[0]
            print(f"\n🔍 Sample Element:")
            print(f"  Category: {getattr(sample_element, 'category', 'Unknown')}")
            print(
                f"  Text preview: '{getattr(sample_element, 'text', 'No text')[:80]}...'"
            )

        # Show sample extracted page
        if extracted_pages:
            page_num, page_info = next(iter(extracted_pages.items()))
            print(f"\n🖼️  Sample Extracted Page:")
            print(f"  Page {page_num}: {page_info.get('filename', 'Unknown')}")
            print(f"  Complexity: {page_info.get('complexity', 'Unknown')}")
            print(f"  Original images: {page_info.get('original_image_count', 0)}")

        print(f"\n🎉 Data access test PASSED!")
        print(f"📱 Ready to proceed with structural analysis...")
        return True

    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False


# Run the test first
if not test_data_access():
    print("\n🛑 Cannot proceed without valid data. Please fix the issues above.")
    exit()

print("\n" + "=" * 60)

# ==============================================================================
# 4. MAIN EXECUTION
# ==============================================================================

# Configuration
INPUT_PICKLE_PATH = "processed_elements.pkl"  # From partitioning notebook
OUTPUT_PATH = "enriched_elements.json"

print("🏗️ CONSTRUCTION DOCUMENT STRUCTURAL AWARENESS")
print("=" * 60)

# Load pre-processed elements (we know this works from the test above)
data = load_processed_elements(INPUT_PICKLE_PATH)

if data:
    raw_elements = data.get("raw_elements", [])
    extracted_pages = data.get("extracted_pages", {})
    page_analysis = data.get("page_analysis", {})

    print(f"📊 Input Summary:")
    print(f"  Raw elements: {len(raw_elements)}")
    print(f"  Extracted pages: {len(extracted_pages)}")
    print(f"  Analyzed pages: {len(page_analysis)}")

    # Add structural awareness
    enriched_elements = add_structural_awareness(
        raw_elements, extracted_pages, page_analysis
    )

    # Show sample results
    print(f"\n📋 Sample Enhanced Analysis:")
    for element in enriched_elements[:3]:
        meta = element["structural_metadata"]
        print(f"  Element: {element['id']}")
        print(f"    Type: {meta.content_type}")
        print(f"    Page Context: {meta.page_context}")
        print(f"    Has Numbers: {meta.has_numbers}")
        print(f"    Content Length: {meta.content_length}")
        print(f"    Complexity: {meta.text_complexity}")
        print(f"    Section (category): {meta.section_title_category}")
        print(f"    Section (inherited): {meta.section_title_inherited}")
        print(f"    Section (pattern): {meta.section_title_pattern}")
        print("    " + "-" * 30)

    # Save enriched elements
    save_enriched_elements(enriched_elements, OUTPUT_PATH)

    print(f"\n🎉 Structural awareness complete!")
    print(
        f"📁 Next: Use '{OUTPUT_PATH.replace('.json', '.pkl')}' in your chunking notebook"
    )

else:
    print("❌ Cannot proceed without processed elements")
    print("💡 First run the partitioning notebook to generate 'processed_elements.pkl'")
