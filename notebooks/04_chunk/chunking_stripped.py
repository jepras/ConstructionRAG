# ==============================================================================
# INTELLIGENT CHUNKING PIPELINE - STRIPPED VERSION
# Clean, focused implementation of intelligent chunking only
# ==============================================================================

import os
import sys
import pickle
import json
import uuid
from datetime import datetime
from pathlib import Path
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

    # New fields for unified approach
    processing_strategy: str = "unified_fast_vision"
    element_id: Optional[str] = None  # Original element ID from unified processing
    image_filepath: Optional[str] = None  # For extracted images


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
# 2. CONFIGURATION
# ==============================================================================

# --- Data Source Configuration ---
ENRICH_DATA_RUN_TO_LOAD = (
    "03_run_20250722_115913"  # Change this to load different enrich_data runs
)

# --- Path Configuration ---
DATA_BASE_DIR = "../../data/internal"
ENRICH_DATA_DIR = f"{DATA_BASE_DIR}/03_enrich_data"
OUTPUT_BASE_DIR = f"{DATA_BASE_DIR}/04_chunking"

# --- Create timestamped output directory ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CURRENT_RUN_DIR = Path(OUTPUT_BASE_DIR) / f"04_run_{timestamp}"

# --- Construct input path from enrich_data run configuration ---
ENRICH_DATA_RUN_DIR = Path(ENRICH_DATA_DIR) / ENRICH_DATA_RUN_TO_LOAD
INPUT_PICKLE_PATH = ENRICH_DATA_RUN_DIR / "enrich_data_output.pkl"

# --- Create directories ---
Path(OUTPUT_BASE_DIR).mkdir(parents=True, exist_ok=True)
CURRENT_RUN_DIR.mkdir(exist_ok=True)

print(f"📁 Output directory: {CURRENT_RUN_DIR}")
print(f"📁 Input from enrich_data run: {ENRICH_DATA_RUN_TO_LOAD}")
print(f"📁 Loading from: {INPUT_PICKLE_PATH}")


# ==============================================================================
# 3. CORE DATA LOADING & SAVING FUNCTIONS
# ==============================================================================


def load_enriched_elements(path: Path) -> List[Dict[str, Any]]:
    """Load enriched elements from pickle file"""
    print(f"📂 Loading enriched elements from: {path}")
    with open(path, "rb") as f:
        elements = pickle.load(f)
    print(f"✅ Loaded {len(elements)} elements")
    return elements


def save_chunks(chunks: List[Dict[str, Any]], base_name: str):
    """Save chunks to both pickle and JSON formats"""
    pickle_path = CURRENT_RUN_DIR / f"{base_name}.pkl"
    json_path = CURRENT_RUN_DIR / f"{base_name}.json"

    # Save pickle (complete data)
    with open(pickle_path, "wb") as f:
        pickle.dump(chunks, f)

    # Save JSON (human-readable)
    with open(json_path, "w") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(chunks)} chunks to:")
    print(f"   📄 {pickle_path}")
    print(f"   📄 {json_path}")


# ==============================================================================
# 4. METADATA & TEXT EXTRACTION HELPERS
# ==============================================================================


def extract_structural_metadata(el: dict) -> dict:
    """Extract structural metadata from element, handling various formats"""
    # Try to get structural_metadata from various possible locations
    # 1. Directly as a dict
    if "structural_metadata" in el:
        meta = el["structural_metadata"]
        # If it's a Pydantic model, convert to dict
        if hasattr(meta, "model_dump"):
            meta = meta.model_dump()
        elif hasattr(meta, "dict"):
            meta = meta.dict()
        return meta

    # 2. Nested in original_element (for enriched elements)
    orig = el.get("original_element")
    if orig:
        # If it's a dict with structural_metadata
        if isinstance(orig, dict) and "structural_metadata" in orig:
            meta = orig["structural_metadata"]
            if hasattr(meta, "model_dump"):
                meta = meta.model_dump()
            elif hasattr(meta, "dict"):
                meta = meta.dict()
            return meta
        # If it's a Pydantic model
        if hasattr(orig, "structural_metadata"):
            meta = getattr(orig, "structural_metadata")
            if hasattr(meta, "model_dump"):
                meta = meta.model_dump()
            elif hasattr(meta, "dict"):
                meta = meta.dict()
            return meta

    # 3. Fallback: try top-level keys
    return {
        k: el.get(k)
        for k in [
            "source_filename",
            "page_number",
            "content_type",
            "page_context",
            "content_length",
            "has_numbers",
            "element_category",
            "has_tables_on_page",
            "has_images_on_page",
            "text_complexity",
            "section_title_category",
            "section_title_inherited",
            "section_title_pattern",
            "processing_strategy",
            "element_id",
            "image_filepath",
            "html_text",
        ]
        if k in el
    }


def extract_text_content(el: dict, extracted_meta: dict = None) -> str:
    """Extract text content from element, prioritizing VLM captions for tables/images"""

    # Check if this element has VLM enrichment metadata
    enrichment_meta = el.get("enrichment_metadata")
    if enrichment_meta:
        # For tables, use VLM captions if available
        if el.get("element_type") == "table":
            # Prefer image caption over HTML caption for tables
            if (
                hasattr(enrichment_meta, "table_image_caption")
                and enrichment_meta.table_image_caption
            ):
                return enrichment_meta.table_image_caption
            elif (
                hasattr(enrichment_meta, "table_html_caption")
                and enrichment_meta.table_html_caption
            ):
                return enrichment_meta.table_html_caption
            elif hasattr(enrichment_meta, "model_dump"):
                meta_dict = enrichment_meta.model_dump()
                if meta_dict.get("table_image_caption"):
                    return meta_dict["table_image_caption"]
                elif meta_dict.get("table_html_caption"):
                    return meta_dict["table_html_caption"]

        # For full-page images, use VLM caption
        elif el.get("element_type") == "full_page_image":
            if (
                hasattr(enrichment_meta, "full_page_image_caption")
                and enrichment_meta.full_page_image_caption
            ):
                return enrichment_meta.full_page_image_caption
            elif hasattr(enrichment_meta, "model_dump"):
                meta_dict = enrichment_meta.model_dump()
                if meta_dict.get("full_page_image_caption"):
                    return meta_dict["full_page_image_caption"]

    # Fallback to original text extraction logic
    # Try direct text field
    if "text" in el:
        return el["text"]

    # Try original_element
    orig = el.get("original_element")
    if orig:
        # If it's a dict with text
        if isinstance(orig, dict) and "text" in orig:
            return orig["text"]
        # If it's an object with text attribute
        if hasattr(orig, "text"):
            return getattr(orig, "text", "")

    # Try structural_metadata for HTML text (for tables from unified approach)
    struct_meta = el.get("structural_metadata")
    if struct_meta:
        # Handle combined list elements
        if hasattr(struct_meta, "narrative_text") and hasattr(
            struct_meta, "list_texts"
        ):
            narrative = struct_meta.narrative_text or ""
            list_texts = struct_meta.list_texts or []
            if narrative and list_texts:
                return narrative + "\n\n" + "\n".join(list_texts)
            elif narrative:
                return narrative
            elif list_texts:
                return "\n".join(list_texts)
        elif hasattr(struct_meta, "model_dump"):
            struct_dict = struct_meta.model_dump()
            # Handle combined list elements (dict version)
            if "narrative_text" in struct_dict and "list_texts" in struct_dict:
                narrative = struct_dict.get("narrative_text", "")
                list_texts = struct_dict.get("list_texts", [])
                if narrative and list_texts:
                    return narrative + "\n\n" + "\n".join(list_texts)
                elif narrative:
                    return narrative
                elif list_texts:
                    return "\n".join(list_texts)
            elif struct_dict.get("html_text"):
                return struct_dict["html_text"]
        elif hasattr(struct_meta, "html_text") and struct_meta.html_text:
            return struct_meta.html_text

    # Check if we have extracted metadata with narrative_text and list_texts (for combined lists)
    if (
        extracted_meta
        and "narrative_text" in extracted_meta
        and "list_texts" in extracted_meta
    ):
        narrative = extracted_meta.get("narrative_text", "")
        list_texts = extracted_meta.get("list_texts", [])
        if narrative and list_texts:
            return narrative + "\n\n" + "\n".join(list_texts)
        elif narrative:
            return narrative
        elif list_texts:
            return "\n".join(list_texts)

    # For images, if no text, return a placeholder
    meta = el.get("structural_metadata")
    if meta and (
        getattr(meta, "content_type", None) == "full_page_with_images"
        or (
            hasattr(meta, "model_dump")
            and meta.model_dump().get("content_type") == "full_page_with_images"
        )
    ):
        return "[IMAGE PAGE]"

    return ""


# ==============================================================================
# 5. INTELLIGENT CHUNKING PIPELINE
# ==============================================================================


def filter_noise_elements(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out noise elements (headers, footers, page breaks, short text, titles)"""
    print(f"[DEBUG] Starting with {len(elements)} elements")

    filtered_elements = []
    for el in elements:
        # Extract metadata and category
        meta = extract_structural_metadata(el)
        category = meta.get("element_category", "unknown")

        # Exclude headers, footers, page breaks
        if category in ["Header", "Footer", "PageBreak"]:
            continue

        # Exclude short uncategorized text (OCR noise)
        if category == "UncategorizedText":
            text_content = extract_text_content(el)
            if len(text_content) < 20:
                continue

        # Exclude Title elements (content will be inherited by other chunks)
        if category == "Title":
            continue

        filtered_elements.append(el)

    print(f"[DEBUG] After filtering: {len(filtered_elements)} elements")
    return filtered_elements


def group_list_items(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group consecutive list items with their narrative introduction"""
    grouped_elements = []
    i = 0

    while i < len(elements):
        current_el = elements[i]
        meta = extract_structural_metadata(current_el)
        category = meta.get("element_category", "unknown")

        # Check if this is a NarrativeText followed by ListItems
        if category == "NarrativeText" and i + 1 < len(elements):
            next_el = elements[i + 1]
            next_meta = extract_structural_metadata(next_el)
            next_category = next_meta.get("element_category", "unknown")

            if next_category == "ListItem":
                # Start collecting list items
                list_items = [current_el]  # Include the narrative introduction
                j = i + 1

                # Collect all consecutive ListItems
                while j < len(elements):
                    j_el = elements[j]
                    j_meta = extract_structural_metadata(j_el)
                    j_category = j_meta.get("element_category", "unknown")

                    if j_category == "ListItem":
                        list_items.append(j_el)
                        j += 1
                    else:
                        break

                # Create a combined "List" element
                narrative_text = extract_text_content(
                    list_items[0]
                )  # First item is the narrative
                list_texts = []

                # Add all list items
                for item in list_items[1:]:  # Skip first item (narrative)
                    text_content = extract_text_content(item)
                    if text_content:
                        list_texts.append(text_content)

                print(
                    f"[DEBUG] Combined list: {len(list_items)} items (1 narrative + {len(list_items)-1} list items)"
                )
                print(f"[DEBUG] Narrative intro: {narrative_text[:100]}...")

                # Create new meta-element with category "List"
                combined_element = {
                    "element_id": f"combined_list_{i}",
                    "element_type": "text",
                    "structural_metadata": {
                        "source_filename": meta.get("source_filename"),
                        "page_number": meta.get("page_number"),
                        "content_type": "text",
                        "element_category": "List",
                        "section_title_inherited": meta.get("section_title_inherited"),
                        "text_complexity": meta.get("text_complexity", "medium"),
                        "content_length": len(narrative_text)
                        + len("\n\n".join(list_texts)),
                        "has_numbers": meta.get("has_numbers", False),
                        "has_tables_on_page": meta.get("has_tables_on_page", False),
                        "has_images_on_page": meta.get("has_images_on_page", False),
                        "section_title_category": meta.get("section_title_category"),
                        "section_title_pattern": meta.get("section_title_pattern"),
                        "processing_strategy": meta.get("processing_strategy"),
                        "image_filepath": meta.get("image_filepath"),
                        "page_context": meta.get("page_context", "unknown"),
                        # Store narrative and list texts separately for composition
                        "narrative_text": narrative_text,
                        "list_texts": list_texts,
                    },
                }

                grouped_elements.append(combined_element)
                i = j  # Skip to after the list items
                continue

        # If not part of a list group, add as-is
        grouped_elements.append(current_el)
        i += 1

    print(f"[DEBUG] After grouping: {len(grouped_elements)} elements")
    return grouped_elements


def compose_final_content(el: Dict[str, Any], meta: dict) -> str:
    """Compose final content based on element type and category"""
    category = meta.get("element_category", "unknown")
    element_type = el.get("element_type", "text")
    section_title = meta.get("section_title_inherited", "Unknown Section")

    if category == "List":
        # Special formatting for combined lists: narrative + list items
        narrative_text = meta.get("narrative_text", "")
        list_texts = meta.get("list_texts", [])

        if narrative_text and list_texts:
            return f"Section: {section_title}\n\n{narrative_text}\n\n{chr(10).join(list_texts)}"
        elif narrative_text:
            return f"Section: {section_title}\n\n{narrative_text}"
        elif list_texts:
            return f"Section: {section_title}\n\n{chr(10).join(list_texts)}"
        else:
            return f"Section: {section_title}\n\n[Empty list]"

    elif category == "NarrativeText":
        text_content = extract_text_content(el, meta)
        return f"Section: {section_title}\n\n{text_content}"

    elif element_type == "table":
        text_content = extract_text_content(el, meta)
        return f"Context: {section_title}\n\nType: Table\n\nSummary: {text_content}"

    elif element_type == "full_page_image":
        text_content = extract_text_content(el, meta)
        return f"Context: {section_title}\n\nType: Image\n\nSummary: {text_content}"

    elif category == "ListItem":
        # Handle list items that weren't grouped (should be rare)
        text_content = extract_text_content(el, meta)
        return f"Section: {section_title}\n\n{text_content}"

    elif category == "UncategorizedText":
        # Handle uncategorized text that might be table references
        text_content = extract_text_content(el, meta)
        if any(
            keyword in text_content.lower()
            for keyword in ["tabel", "table", "figur", "figure"]
        ):
            return f"Context: {section_title}\n\nType: Reference\n\nContent: {text_content}"
        else:
            return f"Section: {section_title}\n\n{text_content}"

    else:
        # For other elements, use their text as-is
        text_content = extract_text_content(el, meta)
        return text_content


def create_final_chunks(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Main orchestrator: transform elements into final chunks"""
    print("\n=== INTELLIGENT CHUNKING PIPELINE ===")

    # Step 1: Filter noise
    filtered_elements = filter_noise_elements(elements)

    # Step 2: Group list items
    grouped_elements = group_list_items(filtered_elements)

    # Step 3: Compose final chunks
    final_chunks = []

    for el in grouped_elements:
        meta = extract_structural_metadata(el)
        text_content = extract_text_content(el, meta)
        section_title = meta.get("section_title_inherited", "Unknown Section")

        # Skip elements without meaningful content
        if not text_content or text_content.strip() == "":
            continue

        # Compose content
        content = compose_final_content(el, meta)

        # Create final chunk object
        chunk = {
            "chunk_id": str(uuid.uuid4()),
            "content": content,
            "metadata": {
                "source_filename": meta.get("source_filename"),
                "page_number": meta.get("page_number"),
                "element_category": meta.get("element_category", "unknown"),
                "section_title_inherited": section_title,
                "text_complexity": meta.get("text_complexity", "medium"),
                "content_length": len(text_content),
                "has_numbers": meta.get("has_numbers", False),
                "has_tables_on_page": meta.get("has_tables_on_page", False),
                "has_images_on_page": meta.get("has_images_on_page", False),
                "section_title_category": meta.get("section_title_category"),
                "section_title_pattern": meta.get("section_title_pattern"),
                "processing_strategy": meta.get("processing_strategy"),
                "image_filepath": meta.get("image_filepath"),
                "page_context": meta.get("page_context", "unknown"),
            },
        }

        final_chunks.append(chunk)

    print(f"[DEBUG] Final chunks created: {len(final_chunks)}")
    return final_chunks


# ==============================================================================
# 6. ANALYSIS & VALIDATION FUNCTIONS
# ==============================================================================


def analyze_chunks(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate basic analysis of chunks"""
    if not chunks:
        return {"error": "No chunks to analyze"}

    total = len(chunks)
    avg_words = sum(len(c["content"].split()) for c in chunks) / total
    avg_chars = sum(len(c["content"]) for c in chunks) / total

    # Content type distribution
    type_dist = {}
    for c in chunks:
        meta = c["metadata"]
        cat = meta.get("element_category", "unknown")
        type_dist[cat] = type_dist.get(cat, 0) + 1

    # Chunk size distribution
    chunk_sizes = [len(c["content"]) for c in chunks]
    size_distribution = {
        "small": len([s for s in chunk_sizes if s < 500]),
        "medium": len([s for s in chunk_sizes if 500 <= s < 1000]),
        "large": len([s for s in chunk_sizes if s >= 1000]),
    }

    return {
        "total_chunks": total,
        "average_words_per_chunk": round(avg_words, 2),
        "average_chars_per_chunk": round(avg_chars, 2),
        "content_type_distribution": type_dist,
        "chunk_size_distribution": size_distribution,
        "min_chunk_size": min(chunk_sizes) if chunk_sizes else 0,
        "max_chunk_size": max(chunk_sizes) if chunk_sizes else 0,
    }


def validate_chunks(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Basic validation of chunk quality"""
    if not chunks:
        return {"error": "No chunks to validate"}

    validation_results = {
        "empty_chunks": 0,
        "missing_metadata": 0,
        "missing_section_title": 0,
    }

    for chunk in chunks:
        content = chunk["content"]
        metadata = chunk["metadata"]

        # Check for empty chunks
        if not content or content.strip() == "":
            validation_results["empty_chunks"] += 1

        # Check for missing metadata
        if not metadata.get("source_filename") or not metadata.get("page_number"):
            validation_results["missing_metadata"] += 1

        # Check for missing section title
        if not metadata.get("section_title_inherited"):
            validation_results["missing_section_title"] += 1

    return validation_results


def print_summary(analysis: Dict[str, Any], validation: Dict[str, Any]):
    """Print summary to console"""
    print(f"\n=== INTELLIGENT CHUNKING SUMMARY ===")
    print(f"  Total chunks: {analysis['total_chunks']}")
    print(f"  Avg words/chunk: {analysis['average_words_per_chunk']}")
    print(f"  Avg chars/chunk: {analysis['average_chars_per_chunk']}")
    print(f"  Content type distribution:")
    for k, v in analysis["content_type_distribution"].items():
        print(f"    {k}: {v}")

    print(f"\n=== VALIDATION RESULTS ===")
    print(f"  Empty chunks: {validation['empty_chunks']}")
    print(f"  Missing metadata: {validation['missing_metadata']}")
    print(f"  Missing section title: {validation['missing_section_title']}")


# ==============================================================================
# 7. MAIN EXECUTION
# ==============================================================================


def main():
    """Main execution function"""
    print("🤖 INTELLIGENT CHUNKING PIPELINE - STRIPPED VERSION")
    print("=" * 60)

    # Load enriched elements
    elements = load_enriched_elements(INPUT_PICKLE_PATH)
    if not elements:
        print("[ERROR] No elements loaded from input. Exiting.")
        return

    # Run intelligent chunking
    final_chunks = create_final_chunks(elements)

    # Save results
    save_chunks(final_chunks, "final_chunks_intelligent")

    # Generate analysis and validation
    analysis = analyze_chunks(final_chunks)
    validation = validate_chunks(final_chunks)

    # Save analysis
    analysis_path = CURRENT_RUN_DIR / "intelligent_chunking_analysis.json"
    with open(analysis_path, "w") as f:
        json.dump(analysis, f, indent=2)

    validation_path = CURRENT_RUN_DIR / "intelligent_chunking_validation.json"
    with open(validation_path, "w") as f:
        json.dump(validation, f, indent=2)

    # Print summary
    print_summary(analysis, validation)

    print(f"\n🎉 Intelligent chunking complete!")
    print(f"📁 Output directory: {CURRENT_RUN_DIR}")
    print(f"📄 Final chunks: {len(final_chunks)} chunks created")


if __name__ == "__main__":
    main()
