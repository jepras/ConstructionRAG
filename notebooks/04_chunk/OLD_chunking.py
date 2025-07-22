# ==============================================================================
# CHUNKING PIPELINE (NO EMBEDDING)
# Intelligent chunking with rich metadata preservation
# Outputs chunked data and chunking analysis/validation only
# ==============================================================================

import os
import sys
import pickle
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# --- Environment & Config ---
from dotenv import load_dotenv

# --- LangChain Components ---
from langchain.text_splitter import RecursiveCharacterTextSplitter

# --- Pydantic for Enhanced Metadata ---
from pydantic import BaseModel, Field
from typing import Literal

# ==============================================================================
# 1. ENHANCED METADATA MODELS (for pickle compatibility)
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
# CONFIGURATION - SPECIFY WHICH ENRICH DATA RUN TO LOAD
# ==============================================================================
ENRICH_DATA_RUN_TO_LOAD = (
    "03_run_20250722_115913"  # Change this to load different enrich_data runs
    # Update this to match your latest enrich_data_from_meta.py run
)

# ==============================================================================
# LOAD CONFIGURATION
# ==============================================================================

# --- Load config ---
CONFIG_PATH = Path(__file__).parent / "config" / "chunking_config.json"
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

# ==============================================================================
# PATH CONFIGURATION
# ==============================================================================

# --- Base directories (relative to project root) ---
DATA_BASE_DIR = "data/internal"
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


# --- Load enriched elements ---
def load_enriched_elements(path: Path):
    with open(path, "rb") as f:
        return pickle.load(f)


def save_json(data, path: Path):
    # If data is a list, process for serializability
    if isinstance(data, list):

        def make_serializable(chunk):
            serializable_chunk = chunk.copy()
            serializable_chunk["metadata"] = (
                extract_structural_metadata(chunk["metadata"])
                if "metadata" in chunk
                else {}
            )
            return serializable_chunk

        serializable_data = [make_serializable(chunk) for chunk in data]
    else:
        # For dicts or other types, just save as-is
        serializable_data = data
    with open(path, "w") as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=2)


def save_pickle(data, path: Path):
    with open(path, "wb") as f:
        pickle.dump(data, f)


# --- List grouping logic ---
def group_lists_with_context(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped = []
    buffer = []
    for el in elements:
        if el.get("element_category") == "ListItem":
            buffer.append(el)
        else:
            if buffer:
                # Attach buffered list items to previous narrative
                if grouped and grouped[-1].get("element_category") == "NarrativeText":
                    grouped[-1]["list_items"] = buffer.copy()
                else:
                    grouped.extend(buffer)
                buffer = []
            grouped.append(el)
    if buffer:
        grouped.extend(buffer)
    return grouped


# --- Helper to extract metadata from element (robust to structure) ---
def extract_structural_metadata(el: dict) -> dict:
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
    # 2. Nested in original_element (NEW: handle enriched elements from enrich_data_from_meta.py)
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
    # 3. Fallback: try top-level keys (including new unified fields)
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
            # NEW: Unified approach fields
            "processing_strategy",
            "element_id",
            "image_filepath",
            "html_text",
        ]
        if k in el
    }


# --- Helper to extract text content from element ---
def extract_text_content(el: dict) -> str:
    """Extract text content from element, prioritizing VLM captions for tables/images."""

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
        if hasattr(struct_meta, "html_text") and struct_meta.html_text:
            return struct_meta.html_text
        elif hasattr(struct_meta, "model_dump"):
            struct_dict = struct_meta.model_dump()
            if struct_dict.get("html_text"):
                return struct_dict["html_text"]

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
# INTELLIGENT CHUNKING FUNCTION
# New approach: Filter noise, group related elements, compose context-rich content
# ==============================================================================


def create_final_chunks(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transform coarse-grained partitioned elements into final, clean, context-rich chunks.

    Steps:
    1. Filter out noise elements (headers, footers, page breaks, short uncategorized text)
    2. Group consecutive list items with their narrative introduction
    3. Compose final content with section titles and proper formatting
    """

    # Step 1: Filter Noise Elements
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

    # Step 2: Group Consecutive List Items
    grouped_elements = []
    i = 0

    while i < len(filtered_elements):
        current_el = filtered_elements[i]
        meta = extract_structural_metadata(current_el)
        category = meta.get("element_category", "unknown")

        # Check if this is a NarrativeText followed by ListItems
        if category == "NarrativeText" and i + 1 < len(filtered_elements):
            next_el = filtered_elements[i + 1]
            next_meta = extract_structural_metadata(next_el)
            next_category = next_meta.get("element_category", "unknown")

            if next_category == "ListItem":
                # Start collecting list items
                list_items = [current_el]  # Include the narrative introduction
                j = i + 1

                # Collect all consecutive ListItems
                while j < len(filtered_elements):
                    j_el = filtered_elements[j]
                    j_meta = extract_structural_metadata(j_el)
                    j_category = j_meta.get("element_category", "unknown")

                    if j_category == "ListItem":
                        list_items.append(j_el)
                        j += 1
                    else:
                        break

                # Create a combined "List" element with narrative introduction
                combined_text = []

                # First, add the narrative introduction
                narrative_text = extract_text_content(
                    list_items[0]
                )  # First item is the narrative
                if narrative_text:
                    combined_text.append(narrative_text)

                # Then add all list items
                for item in list_items[1:]:  # Skip first item (narrative)
                    text_content = extract_text_content(item)
                    if text_content:
                        combined_text.append(text_content)

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
                        "content_length": len("\n".join(combined_text)),
                        "has_numbers": meta.get("has_numbers", False),
                        "has_tables_on_page": meta.get("has_tables_on_page", False),
                        "has_images_on_page": meta.get("has_images_on_page", False),
                        "section_title_category": meta.get("section_title_category"),
                        "section_title_pattern": meta.get("section_title_pattern"),
                        "processing_strategy": meta.get("processing_strategy"),
                        "image_filepath": meta.get("image_filepath"),
                        "page_context": meta.get("page_context", "unknown"),
                        # Store the combined text in html_text field for extraction
                        "html_text": "\n".join(combined_text),
                    },
                }

                grouped_elements.append(combined_element)
                i = j  # Skip to after the list items
                continue

        # If not part of a list group, add as-is
        grouped_elements.append(current_el)
        i += 1

    print(f"[DEBUG] After grouping: {len(grouped_elements)} elements")

    # Step 3: Compose Final Chunks
    final_chunks = []

    for el in grouped_elements:
        meta = extract_structural_metadata(el)
        category = meta.get("element_category", "unknown")
        text_content = extract_text_content(el)
        section_title = meta.get("section_title_inherited", "Unknown Section")

        # Debug: Check if this is a combined list element
        if el.get("element_id", "").startswith("combined_list_"):
            print(
                f"[DEBUG] Combined list element: category={category}, meta_keys={list(meta.keys())}"
            )

        # Skip elements without meaningful content
        if not text_content or text_content.strip() == "":
            continue

            # Compose content based on category and element type
        element_type = el.get("element_type", "text")

        if category == "List":
            # Combined list with narrative introduction
            content = f"Section: {section_title}\n\n{text_content}"
        elif category == "NarrativeText":
            content = f"Section: {section_title}\n\n{text_content}"
        elif element_type == "table":
            content = (
                f"Context: {section_title}\n\nType: Table\n\nSummary: {text_content}"
            )
        elif element_type == "full_page_image":
            content = (
                f"Context: {section_title}\n\nType: Image\n\nSummary: {text_content}"
            )
        elif category == "ListItem":
            # Handle list items that weren't grouped (should be rare)
            content = f"Section: {section_title}\n\n{text_content}"
        elif category == "UncategorizedText":
            # Handle uncategorized text that might be table references
            if any(
                keyword in text_content.lower()
                for keyword in ["tabel", "table", "figur", "figure"]
            ):
                content = f"Context: {section_title}\n\nType: Reference\n\nContent: {text_content}"
            else:
                content = f"Section: {section_title}\n\n{text_content}"
        else:
            # For other elements, use their text as-is
            content = text_content

        # Create final chunk object
        chunk = {
            "chunk_id": str(uuid.uuid4()),
            "content": content,
            "metadata": {
                "source_filename": meta.get("source_filename"),
                "page_number": meta.get("page_number"),
                "element_category": meta.get(
                    "element_category", "unknown"
                ),  # Always use meta category
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


# --- Chunking strategies ---
def adaptive_chunking(text: str, complexity: str, config: dict) -> List[str]:
    sizes = config["experiments"]["adaptive"]["chunk_sizes"]
    chunk_size = sizes.get(complexity, sizes["medium"])
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=0, separators=["\n\n", "\n", ". ", " ", ""]
    )
    return splitter.split_text(text)


def recursive_chunking(text: str, config: dict) -> List[str]:
    chunk_size = config["experiments"]["recursive"]["chunk_size"]
    chunk_overlap = config["experiments"]["recursive"]["chunk_overlap"]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


# --- Main chunking pipeline ---
def chunk_elements(
    elements: List[Dict[str, Any]], config: dict
) -> Dict[str, List[Dict[str, Any]]]:
    grouped_elements = group_lists_with_context(elements)
    print(f"[DEBUG] Grouping produced {len(grouped_elements)} elements")
    results = {"adaptive": [], "recursive": []}
    for el in grouped_elements:
        meta = extract_structural_metadata(el)
        cat = meta.get("element_category")
        content_type = meta.get("content_type", "text")
        element_type = el.get("element_type", "text")

        # Determine if this should be kept as single chunk
        is_single_chunk = (
            cat in ["Table", "Image", "ImageTable"]
            or content_type in ["table", "full_page_with_images"]
            or element_type in ["table", "full_page_image"]
        )

        if is_single_chunk:
            # For tables/images, use only original text (not VLM captions)
            chunk_content = extract_text_content(el)
            chunk = {
                "chunk_id": str(uuid.uuid4()),
                "content": chunk_content,
                "metadata": el,
                "chunking_info": {
                    "strategy": "single",
                    "chunk_size": len(chunk_content),
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            }
            results["adaptive"].append(chunk)
            results["recursive"].append(chunk.copy())
        elif cat == "NarrativeText" or cat == "ListItem" or content_type == "text":
            text = extract_text_content(el)
            complexity = meta.get("text_complexity", "medium")
            # Adaptive
            adaptive_chunks = adaptive_chunking(text, complexity, config)
            for i, chunk_text in enumerate(adaptive_chunks):
                chunk = {
                    "chunk_id": str(uuid.uuid4()),
                    "content": chunk_text,
                    "metadata": el,
                    "chunking_info": {
                        "strategy": "adaptive",
                        "chunk_size": len(chunk_text),
                        "chunk_index": i,
                        "total_chunks": len(adaptive_chunks),
                    },
                }
                results["adaptive"].append(chunk)
            # Recursive
            recursive_chunks = recursive_chunking(text, config)
            for i, chunk_text in enumerate(recursive_chunks):
                chunk = {
                    "chunk_id": str(uuid.uuid4()),
                    "content": chunk_text,
                    "metadata": el,
                    "chunking_info": {
                        "strategy": "recursive",
                        "chunk_size": len(chunk_text),
                        "chunk_index": i,
                        "total_chunks": len(recursive_chunks),
                    },
                }
                results["recursive"].append(chunk)
    return results


# --- Enhanced Analysis & Validation ---
def analyze_chunks(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(chunks)
    avg_words = sum(len(c["content"].split()) for c in chunks) / total if total else 0
    avg_chars = sum(len(c["content"]) for c in chunks) / total if total else 0

    # Enhanced analysis
    chunk_sizes = [len(c["content"]) for c in chunks]
    size_distribution = {
        "small": len([s for s in chunk_sizes if s < 500]),
        "medium": len([s for s in chunk_sizes if 500 <= s < 1000]),
        "large": len([s for s in chunk_sizes if s >= 1000]),
    }

    type_dist = {}
    complexity_dist = {}
    for c in chunks:
        # For final chunks, metadata is already a flat dictionary
        meta = c["metadata"]
        cat = meta.get("element_category", "unknown")
        complexity = meta.get("text_complexity", "unknown")
        type_dist[cat] = type_dist.get(cat, 0) + 1
        complexity_dist[complexity] = complexity_dist.get(complexity, 0) + 1

    return {
        "total_chunks": total,
        "average_words_per_chunk": round(avg_words, 2),
        "average_chars_per_chunk": round(avg_chars, 2),
        "content_type_distribution": type_dist,
        "text_complexity_distribution": complexity_dist,
        "chunk_size_distribution": size_distribution,
        "min_chunk_size": min(chunk_sizes) if chunk_sizes else 0,
        "max_chunk_size": max(chunk_sizes) if chunk_sizes else 0,
        "std_chunk_size": (
            round(
                sum((s - avg_chars) ** 2 for s in chunk_sizes)
                / len(chunk_sizes) ** 0.5,
                2,
            )
            if chunk_sizes
            else 0
        ),
    }


def compare_strategies(
    adaptive_chunks: List[Dict[str, Any]], recursive_chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Compare adaptive vs recursive chunking strategies"""

    adaptive_analysis = analyze_chunks(adaptive_chunks)
    recursive_analysis = analyze_chunks(recursive_chunks)

    # Strategy-specific metrics
    comparison = {
        "adaptive": adaptive_analysis,
        "recursive": recursive_analysis,
        "comparison": {
            "chunk_count_difference": adaptive_analysis["total_chunks"]
            - recursive_analysis["total_chunks"],
            "avg_size_difference": round(
                adaptive_analysis["average_chars_per_chunk"]
                - recursive_analysis["average_chars_per_chunk"],
                2,
            ),
            "size_variability": {
                "adaptive_std": adaptive_analysis["std_chunk_size"],
                "recursive_std": recursive_analysis["std_chunk_size"],
                "more_variable": (
                    "adaptive"
                    if adaptive_analysis["std_chunk_size"]
                    > recursive_analysis["std_chunk_size"]
                    else "recursive"
                ),
            },
        },
    }

    return comparison


def print_analysis_summary(analysis: Dict[str, Any], strategy_name: str):
    print(f"\n=== {strategy_name.upper()} CHUNKING ANALYSIS ===")
    print(f"  Total chunks: {analysis['total_chunks']}")
    print(f"  Avg words/chunk: {analysis['average_words_per_chunk']}")
    print(f"  Avg chars/chunk: {analysis['average_chars_per_chunk']}")
    print(f"  Content type distribution:")
    for k, v in analysis["content_type_distribution"].items():
        print(f"    {k}: {v}")


def print_chunk_preview(chunks: List[Dict[str, Any]], strategy_name: str, n: int = 2):
    print(f"\n--- {strategy_name.upper()} CHUNK PREVIEW (first {n}) ---")
    for i, chunk in enumerate(chunks[:n]):
        print(f"Chunk {i+1}:")
        print(
            f"  Content: {repr(chunk['content'][:120])}{'...' if len(chunk['content']) > 120 else ''}"
        )
        # For final chunks, metadata is already a flat dictionary
        meta = chunk["metadata"]
        print(f"  Element category: {meta.get('element_category', 'N/A')}")
        print(f"  Page: {meta.get('page_number', 'N/A')}")
        print(f"  Section: {meta.get('section_title_inherited', 'N/A')}")
        print(f"  Text complexity: {meta.get('text_complexity', 'N/A')}")
        print(f"  ---")


# --- Smart Sample Selection ---
def create_smart_samples(
    chunks: List[Dict[str, Any]], sample_size: int = 5
) -> List[Dict[str, Any]]:
    """Create samples that include at least one of each content type if available"""
    if not chunks:
        return []

    # Extract metadata for all chunks
    chunks_with_meta = []
    for chunk in chunks:
        meta = extract_structural_metadata(chunk["metadata"])
        chunks_with_meta.append((chunk, meta))

    # Group by content type
    by_type = {}
    for chunk, meta in chunks_with_meta:
        content_type = meta.get("content_type", "unknown")
        if content_type not in by_type:
            by_type[content_type] = []
        by_type[content_type].append(chunk)

    # Select samples ensuring diversity
    samples = []

    # Priority order: table, image, list, narrative, other
    priority_types = ["table", "full_page_with_images", "text"]

    for content_type in priority_types:
        if content_type in by_type and by_type[content_type]:
            samples.append(by_type[content_type][0])
            if len(samples) >= sample_size:
                break

    # Fill remaining slots with any available chunks
    remaining_slots = sample_size - len(samples)
    if remaining_slots > 0:
        all_chunks = [chunk for chunk, _ in chunks_with_meta]
        for chunk in all_chunks:
            if chunk not in samples:
                samples.append(chunk)
                remaining_slots -= 1
                if remaining_slots <= 0:
                    break

    return samples[:sample_size]


# --- Quality Validation Functions ---
def validate_chunk_boundaries(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate content boundaries and chunk quality"""

    validation_results = {
        "empty_chunks": 0,
        "whitespace_only_chunks": 0,
        "sentence_completeness": {"complete": 0, "incomplete": 0},
        "meaningful_content": {"yes": 0, "no": 0},
        "character_limits": {"within_limits": 0, "exceeds_limits": 0},
    }

    for chunk in chunks:
        content = chunk["content"]

        # Check for empty chunks
        if not content:
            validation_results["empty_chunks"] += 1
            continue

        # Check for whitespace-only chunks
        if content.strip() == "":
            validation_results["whitespace_only_chunks"] += 1
            continue

        # Check sentence completeness (improved heuristic)
        sentences = [s.strip() for s in content.split(".") if s.strip()]
        if sentences:
            last_sentence = sentences[-1]

            # Check if last sentence is complete
            is_complete = True

            # Incomplete if:
            # 1. Last sentence is very short (< 10 chars) and not the only sentence
            if len(last_sentence) < 10 and len(sentences) > 1:
                is_complete = False
            # 2. Last sentence ends with common incomplete patterns
            elif any(
                last_sentence.endswith(pattern)
                for pattern in [
                    "og",
                    "eller",
                    "men",
                    "for",
                    "til",
                    "med",
                    "på",
                    "i",
                    "at",
                    "som",
                ]
            ):
                is_complete = False
            # 3. Last sentence doesn't end with proper punctuation
            elif not last_sentence.endswith((".", "!", "?", ":")):
                is_complete = False
            # 4. Last sentence starts with lowercase (likely mid-sentence)
            elif last_sentence and last_sentence[0].islower():
                is_complete = False

            if is_complete:
                validation_results["sentence_completeness"]["complete"] += 1
            else:
                validation_results["sentence_completeness"]["incomplete"] += 1
        else:
            validation_results["sentence_completeness"]["complete"] += 1

        # Check for meaningful content (improved criteria)
        words = [w for w in content.split() if len(w) > 1]  # Filter out single letters
        unique_words = set(words)

        # Meaningful if:
        # 1. Has sufficient word count
        # 2. Has reasonable vocabulary diversity
        # 3. Contains actual content (not just numbers/symbols)
        is_meaningful = (
            len(words) >= 3  # Minimum word count
            and len(unique_words) >= 2  # Vocabulary diversity
            and any(w.isalpha() for w in words)  # Contains actual words
        )

        if is_meaningful:
            validation_results["meaningful_content"]["yes"] += 1
        else:
            validation_results["meaningful_content"]["no"] += 1

        # Check character limits (reasonable bounds)
        if 10 <= len(content) <= 2000:
            validation_results["character_limits"]["within_limits"] += 1
        else:
            validation_results["character_limits"]["exceeds_limits"] += 1

    return validation_results


def validate_metadata_preservation(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Verify metadata preservation across chunks"""

    validation_results = {
        "metadata_completeness": {"complete": 0, "incomplete": 0},
        "section_inheritance": {"preserved": 0, "missing": 0},
        "page_context": {"preserved": 0, "missing": 0},
        "text_complexity": {"preserved": 0, "missing": 0},
    }

    for chunk in chunks:
        meta = extract_structural_metadata(chunk["metadata"])

        # Check metadata completeness
        required_fields = [
            "source_filename",
            "page_number",
            "content_type",
            "element_category",
        ]
        if all(field in meta and meta[field] for field in required_fields):
            validation_results["metadata_completeness"]["complete"] += 1
        else:
            validation_results["metadata_completeness"]["incomplete"] += 1

        # Check section inheritance
        if meta.get("section_title_inherited"):
            validation_results["section_inheritance"]["preserved"] += 1
        else:
            validation_results["section_inheritance"]["missing"] += 1

        # Check page context
        if meta.get("page_context") and meta["page_context"] != "unknown":
            validation_results["page_context"]["preserved"] += 1
        else:
            validation_results["page_context"]["missing"] += 1

        # Check text complexity
        if meta.get("text_complexity") and meta["text_complexity"] != "unknown":
            validation_results["text_complexity"]["preserved"] += 1
        else:
            validation_results["text_complexity"]["missing"] += 1

    return validation_results


def validate_chunking_strategy(
    chunks: List[Dict[str, Any]], strategy_name: str
) -> Dict[str, Any]:
    """Validate chunking strategy effectiveness"""

    validation_results = {
        "strategy": strategy_name,
        "chunk_size_consistency": {"consistent": 0, "inconsistent": 0},
        "overlap_analysis": {"has_overlap": 0, "no_overlap": 0},
        "content_coherence": {"coherent": 0, "fragmented": 0},
    }

    chunk_sizes = [len(c["content"]) for c in chunks]
    avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0

    for chunk in chunks:
        content = chunk["content"]
        chunk_size = len(content)

        # Check size consistency (within 50% of average)
        if 0.5 * avg_size <= chunk_size <= 1.5 * avg_size:
            validation_results["chunk_size_consistency"]["consistent"] += 1
        else:
            validation_results["chunk_size_consistency"]["inconsistent"] += 1

        # Check for content coherence (has multiple sentences or meaningful length)
        sentences = content.split(".")
        if len(sentences) > 1 or len(content) > 100:
            validation_results["content_coherence"]["coherent"] += 1
        else:
            validation_results["content_coherence"]["fragmented"] += 1

    return validation_results


def generate_quality_report(
    adaptive_chunks: List[Dict[str, Any]], recursive_chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate comprehensive quality report for both strategies"""

    quality_report = {
        "adaptive": {
            "boundary_validation": validate_chunk_boundaries(adaptive_chunks),
            "metadata_validation": validate_metadata_preservation(adaptive_chunks),
            "strategy_validation": validate_chunking_strategy(
                adaptive_chunks, "adaptive"
            ),
        },
        "recursive": {
            "boundary_validation": validate_chunk_boundaries(recursive_chunks),
            "metadata_validation": validate_metadata_preservation(recursive_chunks),
            "strategy_validation": validate_chunking_strategy(
                recursive_chunks, "recursive"
            ),
        },
        "overall_quality_score": {"adaptive": 0, "recursive": 0},
    }

    # Calculate quality scores (0-100)
    for strategy in ["adaptive", "recursive"]:
        report = quality_report[strategy]

        # Boundary quality (30 points)
        boundary = report["boundary_validation"]
        boundary_score = 30 * (
            1
            - (boundary["empty_chunks"] + boundary["whitespace_only_chunks"])
            / len(adaptive_chunks if strategy == "adaptive" else recursive_chunks)
        )

        # Metadata quality (40 points)
        metadata = report["metadata_validation"]
        metadata_score = 40 * (
            metadata["metadata_completeness"]["complete"]
            / len(adaptive_chunks if strategy == "adaptive" else recursive_chunks)
        )

        # Strategy quality (30 points)
        strategy_val = report["strategy_validation"]
        strategy_score = 30 * (
            strategy_val["content_coherence"]["coherent"]
            / len(adaptive_chunks if strategy == "adaptive" else recursive_chunks)
        )

        quality_report["overall_quality_score"][strategy] = round(
            boundary_score + metadata_score + strategy_score, 1
        )

    return quality_report


# --- Main ---
def main():
    elements = load_enriched_elements(INPUT_PICKLE_PATH)
    print(
        f"[DEBUG] Loaded {len(elements)} elements. Example: {elements[0] if elements else 'EMPTY'}"
    )
    if not elements:
        print("[WARNING] No elements loaded from input. Exiting.")
        return

    # NEW: Use intelligent chunking approach
    print("\n=== USING INTELLIGENT CHUNKING APPROACH ===")
    final_chunks = create_final_chunks(elements)

    # Save the intelligent chunks
    save_pickle(final_chunks, CURRENT_RUN_DIR / "final_chunks_intelligent.pkl")
    save_json(final_chunks, CURRENT_RUN_DIR / "final_chunks_intelligent.json")

    # Create analysis for intelligent chunks
    intelligent_analysis = analyze_chunks(final_chunks)
    save_json(
        intelligent_analysis, CURRENT_RUN_DIR / "intelligent_chunking_analysis.json"
    )

    # Create quality validation for intelligent chunks
    intelligent_quality = {
        "boundary_validation": validate_chunk_boundaries(final_chunks),
        "metadata_validation": validate_metadata_preservation(final_chunks),
        "strategy_validation": validate_chunking_strategy(final_chunks, "intelligent"),
    }
    save_json(
        intelligent_quality, CURRENT_RUN_DIR / "intelligent_chunking_quality.json"
    )

    # Create smart samples for intelligent chunks
    smart_samples_intelligent = create_smart_samples(final_chunks, 5)
    save_json(
        smart_samples_intelligent, CURRENT_RUN_DIR / "sample_chunks_intelligent.json"
    )

    # LEGACY: Also run the old chunking approaches for comparison
    print("\n=== RUNNING LEGACY CHUNKING APPROACHES FOR COMPARISON ===")
    chunked = chunk_elements(elements, config)

    # Save legacy chunked outputs
    save_pickle(chunked["adaptive"], CURRENT_RUN_DIR / "chunked_elements_adaptive.pkl")
    save_pickle(
        chunked["recursive"], CURRENT_RUN_DIR / "chunked_elements_recursive.pkl"
    )
    save_json(chunked["adaptive"], CURRENT_RUN_DIR / "chunked_elements_adaptive.json")
    save_json(chunked["recursive"], CURRENT_RUN_DIR / "chunked_elements_recursive.json")

    # Save legacy analysis
    comparison_analysis = compare_strategies(chunked["adaptive"], chunked["recursive"])
    save_json(comparison_analysis, CURRENT_RUN_DIR / "strategy_comparison.json")

    # Legacy quality validation
    quality_report = generate_quality_report(chunked["adaptive"], chunked["recursive"])
    save_json(quality_report, CURRENT_RUN_DIR / "chunking_quality_report.json")

    # Legacy samples
    smart_samples_adaptive = create_smart_samples(chunked["adaptive"], 5)
    smart_samples_recursive = create_smart_samples(chunked["recursive"], 5)
    save_json(smart_samples_adaptive, CURRENT_RUN_DIR / "sample_chunks_adaptive.json")
    save_json(smart_samples_recursive, CURRENT_RUN_DIR / "sample_chunks_recursive.json")

    # --- Debug/console output ---
    print("\n================ INTELLIGENT CHUNKING SUMMARY ================")
    print_analysis_summary(intelligent_analysis, "intelligent")
    print_chunk_preview(final_chunks, "intelligent", n=3)

    print("\n================ LEGACY CHUNKING SUMMARY ================")
    for strategy in ["adaptive", "recursive"]:
        if not chunked[strategy]:
            print(f"[WARNING] No chunks produced for {strategy} strategy.")
            continue
        print_analysis_summary(analyze_chunks(chunked[strategy]), strategy)
        print_chunk_preview(chunked[strategy], strategy, n=2)

    print("\nChunking complete. Outputs written to", CURRENT_RUN_DIR)
    print(f"Intelligent chunks: {len(final_chunks)}")
    print(f"Legacy adaptive chunks: {len(chunked['adaptive'])}")
    print(f"Legacy recursive chunks: {len(chunked['recursive'])}")


if __name__ == "__main__":
    main()
