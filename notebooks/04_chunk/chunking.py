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
    "03_run_20250721_115255"  # Change this to load different enrich_data runs
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
    # 2. Nested in original_element
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
        ]
        if k in el
    }


# --- Helper to extract text content from element ---
def extract_text_content(el: dict) -> str:
    """Extract text content from element, handling various nested structures"""
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

    # Try enrichment_metadata for captions
    enrichment = el.get("enrichment_metadata")
    if enrichment:
        # For tables, use HTML caption
        if hasattr(enrichment, "table_html_caption") and enrichment.table_html_caption:
            return enrichment.table_html_caption
        # For images, use full page caption
        if (
            hasattr(enrichment, "full_page_image_caption")
            and enrichment.full_page_image_caption
        ):
            return enrichment.full_page_image_caption

    return ""


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
    print(
        f"[DEBUG] Grouping produced {len(grouped_elements)} elements. Example: {grouped_elements[0] if grouped_elements else 'EMPTY'}"
    )
    for el in grouped_elements:
        meta = extract_structural_metadata(el)
        print(
            f"[DEBUG] Element category: {meta.get('element_category')}, keys: {list(el.keys())}"
        )
    results = {"adaptive": [], "recursive": []}
    for el in grouped_elements:
        meta = extract_structural_metadata(el)
        cat = meta.get("element_category")
        if cat in ["Table", "Image", "ImageTable"]:
            # Keep as single chunk
            chunk = {
                "chunk_id": str(uuid.uuid4()),
                "content": extract_text_content(el),
                "metadata": el,
                "chunking_info": {
                    "strategy": "single",
                    "chunk_size": len(extract_text_content(el)),
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            }
            results["adaptive"].append(chunk)
            results["recursive"].append(chunk.copy())
        elif cat == "NarrativeText" or cat == "ListItem":
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


# --- Analysis & Validation ---
def analyze_chunks(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(chunks)
    avg_words = sum(len(c["content"].split()) for c in chunks) / total if total else 0
    avg_chars = sum(len(c["content"]) for c in chunks) / total if total else 0
    type_dist = {}
    for c in chunks:
        cat = c["metadata"].get("element_category", "unknown")
        type_dist[cat] = type_dist.get(cat, 0) + 1
    return {
        "total_chunks": total,
        "average_words_per_chunk": round(avg_words, 2),
        "average_chars_per_chunk": round(avg_chars, 2),
        "content_type_distribution": type_dist,
    }


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
        # Use the same metadata extraction logic as the rest of the code
        meta = extract_structural_metadata(chunk["metadata"])
        print(f"  Element category: {meta.get('element_category', 'N/A')}")
        print(f"  Page: {meta.get('page_number', 'N/A')}")
        print(f"  Section: {meta.get('section_title_inherited', 'N/A')}")
        print(f"  Text complexity: {meta.get('text_complexity', 'N/A')}")
        print(f"  ---")


# --- Main ---
def main():
    elements = load_enriched_elements(INPUT_PICKLE_PATH)
    print(
        f"[DEBUG] Loaded {len(elements)} elements. Example: {elements[0] if elements else 'EMPTY'}"
    )
    if not elements:
        print("[WARNING] No elements loaded from input. Exiting.")
        return
    chunked = chunk_elements(elements, config)
    # Save chunked outputs (main: .pkl, also .json for readability)
    save_pickle(chunked["adaptive"], CURRENT_RUN_DIR / "chunked_elements_adaptive.pkl")
    save_pickle(
        chunked["recursive"], CURRENT_RUN_DIR / "chunked_elements_recursive.pkl"
    )
    save_json(chunked["adaptive"], CURRENT_RUN_DIR / "chunked_elements_adaptive.json")
    save_json(chunked["recursive"], CURRENT_RUN_DIR / "chunked_elements_recursive.json")
    # Save analysis
    analysis = {
        "adaptive": analyze_chunks(chunked["adaptive"]),
        "recursive": analyze_chunks(chunked["recursive"]),
    }
    save_json(analysis, CURRENT_RUN_DIR / "chunking_analysis.json")
    # Save samples
    save_json(chunked["adaptive"][:5], CURRENT_RUN_DIR / "sample_chunks_adaptive.json")
    save_json(
        chunked["recursive"][:5], CURRENT_RUN_DIR / "sample_chunks_recursive.json"
    )
    # --- Debug/console output ---
    print("\n================ CHUNKING SUMMARY ================")
    for strategy in ["adaptive", "recursive"]:
        if not chunked[strategy]:
            print(f"[WARNING] No chunks produced for {strategy} strategy.")
            continue
        print_analysis_summary(analysis[strategy], strategy)
        print_chunk_preview(chunked[strategy], strategy, n=2)
    print("\nChunking complete. Outputs written to", CURRENT_RUN_DIR)


if __name__ == "__main__":
    main()
