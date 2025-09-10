"""Production chunking step for document processing pipeline."""

import re
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal
from uuid import UUID
import logging
from pathlib import Path

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    # Fallback if langchain is not available
    RecursiveCharacterTextSplitter = None

from ...shared.base_step import PipelineStep
from src.models import StepResult
from ...shared.models import PipelineError
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError
from src.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class IntelligentChunker:
    """Intelligent chunking engine that preserves core logic from notebook"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Configuration parameters
        self.min_content_length = config.get("min_content_length", 20)
        self.exclude_categories = config.get("exclude_categories", ["Header", "Footer", "PageBreak", "Title"])
        self.enable_list_grouping = config.get("enable_list_grouping", True)
        self.max_list_items_per_group = config.get("max_list_items_per_group", 10)
        self.include_section_titles = config.get("include_section_titles", False)  # Changed default to False
        self.format_tables_with_context = config.get("format_tables_with_context", True)
        self.format_images_with_context = config.get("format_images_with_context", True)
        self.prioritize_vlm_captions = config.get("prioritize_vlm_captions", True)
        self.fallback_to_original_text = config.get("fallback_to_original_text", True)

        # Semantic chunking parameters
        self.strategy = config.get("strategy", "semantic")  # HARDCODED: Force semantic strategy
        self.chunk_size = config.get("chunk_size", 1000)
        self.overlap = config.get("overlap", 200)
        self.separators = config.get("separators", ["\n\n", "\n", " ", ""])
        self.min_chunk_size = config.get("min_chunk_size", 100)
        self.max_chunk_size = config.get("max_chunk_size", 1200)  # HARDCODED: Force aggressive splitting

        # BEAM DEBUG: Print configuration as received
        print(f"🔧 BEAM CHUNKING CONFIG:")
        print(f"  strategy: {self.strategy} (config value: {config.get('strategy', 'NOT_SET')})")
        print(f"  max_chunk_size: {self.max_chunk_size} (config value: {config.get('max_chunk_size', 'NOT_SET')})")
        print(f"  chunk_size: {self.chunk_size}")
        print(f"  overlap: {self.overlap}")

        # FORCE HARDCODED VALUES FOR BEAM TESTING
        self.strategy = "semantic"
        self.max_chunk_size = 1000  # Force split anything over 1000 chars
        self.chunk_size = 800  # Force smaller target chunk size
        self.overlap = 200  # Ensure good overlap

        print(f"🔧 BEAM FORCED VALUES:")
        print(f"  strategy: {self.strategy} (HARDCODED)")
        print(f"  max_chunk_size: {self.max_chunk_size} (HARDCODED - will split chunks > 1000 chars)")
        print(f"  chunk_size: {self.chunk_size} (HARDCODED - target chunk size)")
        print(f"  overlap: {self.overlap} (HARDCODED - overlap size)")

    def extract_structural_metadata(self, el: dict) -> dict:
        """Extract structural metadata from element, handling various formats"""
        element_type = el.get("element_type", "unknown")
        element_id = el.get("id", el.get("element_id", "unknown"))

        # Try to get structural_metadata from various possible locations
        # 1. Directly as a dict
        if "structural_metadata" in el:
            meta = el["structural_metadata"]
            # If it's a Pydantic model, convert to dict
            if hasattr(meta, "model_dump"):
                meta = meta.model_dump()
            elif hasattr(meta, "dict"):
                meta = meta.model_dump(exclude_none=True)

            bbox = meta.get("bbox")
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
                    meta = meta.model_dump(exclude_none=True)
                bbox = meta.get("bbox")
                return meta
            # If it's a Pydantic model
            if hasattr(orig, "structural_metadata"):
                meta = getattr(orig, "structural_metadata")
                if hasattr(meta, "model_dump"):
                    meta = meta.model_dump()
                elif hasattr(meta, "dict"):
                    meta = meta.model_dump(exclude_none=True)
                bbox = meta.get("bbox")
                return meta

        # 3. Fallback: try top-level keys
        fallback_meta = {
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
                "bbox",  # Include bbox in fallback extraction
            ]
            if k in el
        }
        bbox = fallback_meta.get("bbox")
        return fallback_meta

    def extract_text_content(self, el: dict, extracted_meta: dict = None) -> str:
        """Extract text content from element, prioritizing VLM captions for tables/images"""

        # Check if this element has VLM enrichment metadata
        enrichment_meta = el.get("enrichment_metadata")
        if enrichment_meta and self.prioritize_vlm_captions:
            # For tables, use VLM image caption if available
            if el.get("element_type") == "table" or el.get("category") == "Table":
                # Use image caption for tables (HTML captions removed)
                if enrichment_meta.get("table_image_caption"):
                    return enrichment_meta["table_image_caption"]

            # For full-page images, use VLM caption
            elif el.get("element_type") == "full_page_image" or el.get("content_type") == "full_page_with_images":
                if enrichment_meta.get("full_page_image_caption"):
                    return enrichment_meta["full_page_image_caption"]

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
            if hasattr(struct_meta, "narrative_text") and hasattr(struct_meta, "list_texts"):
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
        if extracted_meta and "narrative_text" in extracted_meta and "list_texts" in extracted_meta:
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
            or (hasattr(meta, "model_dump") and meta.model_dump().get("content_type") == "full_page_with_images")
        ):
            return "[IMAGE PAGE]"

        return ""

    def filter_noise_elements(self, elements: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Filter out noise elements and return filtering statistics"""
        logger.debug(f"Starting with {len(elements)} elements")

        filtered_elements = []
        filtering_stats = {
            "total_elements": len(elements),
            "filtered_out": 0,
            "filtered_by_category": {},
            "filtered_by_length": 0,
            "filtered_elements": [],
        }

        for el in elements:
            # Extract metadata and category
            meta = self.extract_structural_metadata(el)
            category = meta.get("element_category", "unknown")

            # Exclude headers, footers, page breaks
            if category in self.exclude_categories:
                filtering_stats["filtered_out"] += 1
                filtering_stats["filtered_by_category"][category] = (
                    filtering_stats["filtered_by_category"].get(category, 0) + 1
                )
                filtering_stats["filtered_elements"].append(
                    {
                        "category": category,
                        "reason": f"Excluded category: {category}",
                        "content_preview": (
                            self.extract_text_content(el)[:100] + "..."
                            if len(self.extract_text_content(el)) > 100
                            else self.extract_text_content(el)
                        ),
                    }
                )
                continue

            # Exclude short uncategorized text (OCR noise)
            if category == "UncategorizedText":
                text_content = self.extract_text_content(el)
                if len(text_content) < self.min_content_length:
                    filtering_stats["filtered_out"] += 1
                    filtering_stats["filtered_by_length"] += 1
                    filtering_stats["filtered_elements"].append(
                        {
                            "category": category,
                            "reason": f"Too short: {len(text_content)} chars (min: {self.min_content_length})",
                            "content_preview": text_content,
                        }
                    )
                    continue

            filtered_elements.append(el)

        logger.debug(f"After filtering: {len(filtered_elements)} elements")
        return filtered_elements, filtering_stats

    def group_list_items(self, elements: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Group consecutive list items with their narrative introduction and return grouping statistics"""
        if not self.enable_list_grouping:
            return elements, {"list_grouping_enabled": False}

        grouped_elements = []
        grouping_stats = {
            "list_grouping_enabled": True,
            "total_elements": len(elements),
            "groups_created": 0,
            "total_list_items_grouped": 0,
            "narrative_texts_found": 0,
            "list_items_found": 0,
            "group_examples": [],
        }

        i = 0

        while i < len(elements):
            current_el = elements[i]
            meta = self.extract_structural_metadata(current_el)
            category = meta.get("element_category", "unknown")

            # Count narrative texts and list items
            if category == "NarrativeText":
                grouping_stats["narrative_texts_found"] += 1
            elif category == "ListItem":
                grouping_stats["list_items_found"] += 1

            # Check if this is a NarrativeText followed by ListItems
            if category == "NarrativeText" and i + 1 < len(elements):
                next_el = elements[i + 1]
                next_meta = self.extract_structural_metadata(next_el)
                next_category = next_meta.get("element_category", "unknown")

                if next_category == "ListItem":
                    # Start collecting list items
                    list_items = [current_el]  # Include the narrative introduction
                    j = i + 1

                    # Collect all consecutive ListItems (up to max limit)
                    while j < len(elements) and len(list_items) <= self.max_list_items_per_group:
                        j_el = elements[j]
                        j_meta = self.extract_structural_metadata(j_el)
                        j_category = j_meta.get("element_category", "unknown")

                        if j_category == "ListItem":
                            list_items.append(j_el)
                            j += 1
                        else:
                            break

                    logger.debug(
                        f"Combined list: {len(list_items)} items (1 narrative + {len(list_items) - 1} list items)"
                    )

                    # Track grouping statistics
                    grouping_stats["groups_created"] += 1
                    grouping_stats["total_list_items_grouped"] += len(list_items) - 1  # Exclude narrative text

                    # Store example of grouped list (up to 2 examples)
                    if len(grouping_stats["group_examples"]) < 2:
                        narrative_text = self.extract_text_content(list_items[0])
                        list_texts = [self.extract_text_content(item) for item in list_items[1:]]
                        grouping_stats["group_examples"].append(
                            {
                                "narrative_text": (
                                    narrative_text[:200] + "..." if len(narrative_text) > 200 else narrative_text
                                ),
                                "list_items": [
                                    text[:100] + "..." if len(text) > 100 else text for text in list_texts[:3]
                                ],  # Show first 3 list items
                                "total_list_items": len(list_texts),
                                "page_number": meta.get("page_number"),
                                "section_title": meta.get("section_title_inherited"),
                            }
                        )

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
                            "content_length": 0,  # Will be calculated
                            "has_numbers": meta.get("has_numbers", False),
                            "has_tables_on_page": meta.get("has_tables_on_page", False),
                            "has_images_on_page": meta.get("has_images_on_page", False),
                            "section_title_category": meta.get("section_title_category"),
                            "section_title_pattern": meta.get("section_title_pattern"),
                            "processing_strategy": meta.get("processing_strategy"),
                            "image_filepath": meta.get("image_filepath"),
                            "page_context": meta.get("page_context", "unknown"),
                            # Store narrative and list texts separately for composition
                            "narrative_text": self.extract_text_content(list_items[0]),
                            "list_texts": [self.extract_text_content(item) for item in list_items[1:]],
                        },
                    }

                    # Calculate content length
                    narrative_text = combined_element["structural_metadata"]["narrative_text"]
                    list_texts = combined_element["structural_metadata"]["list_texts"]
                    combined_element["structural_metadata"]["content_length"] = len(narrative_text) + len(
                        "\n\n".join(list_texts)
                    )

                    grouped_elements.append(combined_element)
                    i = j  # Skip to after the list items
                    continue

            # If not part of a list group, add as-is
            grouped_elements.append(current_el)
            i += 1

        # Calculate success rate
        if grouping_stats["list_items_found"] > 0:
            grouping_stats["grouping_success_rate"] = round(
                (grouping_stats["total_list_items_grouped"] / grouping_stats["list_items_found"]) * 100,
                2,
            )
        else:
            grouping_stats["grouping_success_rate"] = 0

        logger.debug(f"After grouping: {len(grouped_elements)} elements")
        return grouped_elements, grouping_stats

    def compose_final_content(self, el: Dict[str, Any], meta: dict) -> str:
        """Compose final content based on element type and category"""
        category = meta.get("element_category", "unknown")
        element_type = el.get("element_type", "text")
        section_title = meta.get("section_title_inherited", "Unknown Section")

        # Check if this is a split element with pre-computed content
        if "split_content" in el:
            content = el["split_content"]
            if self.include_section_titles:
                return f"Section: {section_title}\n\n{content}"
            else:
                return content

        # Check if this is a merged element
        if "merged_content" in el:
            content = el["merged_content"]
            if self.include_section_titles:
                return f"Section: {section_title}\n\n{content}"
            else:
                return content

        if category == "List":
            # Special formatting for combined lists: narrative + list items
            narrative_text = meta.get("narrative_text", "")
            list_texts = meta.get("list_texts", [])

            if narrative_text and list_texts:
                content = f"{narrative_text}\n\n{chr(10).join(list_texts)}"
            elif narrative_text:
                content = narrative_text
            elif list_texts:
                content = chr(10).join(list_texts)
            else:
                content = "[Empty list]"

            if self.include_section_titles:
                return f"Section: {section_title}\n\n{content}"
            else:
                return content

        elif category == "NarrativeText":
            text_content = self.extract_text_content(el, meta)
            if self.include_section_titles:
                return f"Section: {section_title}\n\n{text_content}"
            else:
                return text_content

        elif element_type == "table" or category == "Table":
            text_content = self.extract_text_content(el, meta)
            if self.format_tables_with_context:
                if self.include_section_titles:
                    return f"Context: {section_title}\n\nType: Table\n\nSummary: {text_content}"
                else:
                    return f"Type: Table\n\nSummary: {text_content}"
            else:
                return text_content

        elif element_type == "full_page_image" or meta.get("content_type") == "full_page_with_images":
            text_content = self.extract_text_content(el, meta)
            if self.format_images_with_context:
                if self.include_section_titles:
                    return f"Context: {section_title}\n\nType: Image\n\nSummary: {text_content}"
                else:
                    return f"Type: Image\n\nSummary: {text_content}"
            else:
                return text_content

        elif category == "ListItem":
            # Handle list items that weren't grouped (should be rare)
            text_content = self.extract_text_content(el, meta)
            if self.include_section_titles:
                return f"Section: {section_title}\n\n{text_content}"
            else:
                return text_content

        elif category == "UncategorizedText":
            # Handle uncategorized text that might be table references
            text_content = self.extract_text_content(el, meta)
            if any(keyword in text_content.lower() for keyword in ["tabel", "table", "figur", "figure"]):
                if self.include_section_titles:
                    return f"Context: {section_title}\n\nType: Reference\n\nContent: {text_content}"
                else:
                    return f"Type: Reference\n\nContent: {text_content}"
            else:
                if self.include_section_titles:
                    return f"Section: {section_title}\n\n{text_content}"
                else:
                    return text_content

        else:
            # For other elements, use their text as-is
            text_content = self.extract_text_content(el, meta)
            return text_content

    def apply_semantic_text_splitting_to_chunks(
        self, chunks: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Apply semantic text splitting to composed chunks that exceed max_chunk_size"""

        # BEAM DEBUG: Print configuration and chunk analysis
        print(
            f"🔍 BEAM CHUNKING: strategy={self.strategy}, max_chunk_size={self.max_chunk_size}, chunk_size={self.chunk_size}"
        )
        chunk_sizes = [len(chunk["content"]) for chunk in chunks]
        print(
            f"🔍 BEAM CHUNKING: {len(chunks)} chunks, sizes: min={min(chunk_sizes) if chunk_sizes else 0}, max={max(chunk_sizes) if chunk_sizes else 0}, avg={sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0:.1f}"
        )

        # Print details about large chunks
        large_chunks = [i for i, size in enumerate(chunk_sizes) if size > 1000]
        if large_chunks:
            print(f"🔍 BEAM CHUNKING: Found {len(large_chunks)} chunks > 1000 chars at indices: {large_chunks}")
            for i in large_chunks[:3]:  # Print details for first 3 large chunks
                chunk = chunks[i]
                content_preview = chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"]
                print(
                    f"🔍 BEAM LARGE CHUNK {i}: {len(chunk['content'])} chars, type={chunk['metadata'].get('element_category', 'unknown')}, preview='{content_preview}'"
                )

        if self.strategy != "semantic" or RecursiveCharacterTextSplitter is None:
            print(
                f"🔍 BEAM CHUNKING: Semantic splitting disabled - strategy={self.strategy}, RecursiveCharacterTextSplitter available={RecursiveCharacterTextSplitter is not None}"
            )
            return chunks, {"semantic_splitting_enabled": False}

        print(
            f"🔍 BEAM CHUNKING: Applying semantic text splitting to chunks larger than {self.max_chunk_size} characters..."
        )

        # Initialize text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.overlap,
            separators=self.separators,
            length_function=len,
            is_separator_regex=False,
        )

        print(f"🔍 BEAM CHUNKING: Text splitter initialized with chunk_size={self.chunk_size}, overlap={self.overlap}")

        split_chunks = []
        splitting_stats = {
            "chunks_processed": 0,
            "chunks_split": 0,
            "total_new_chunks": 0,
            "chunks_unchanged": 0,
            "largest_chunk_before": 0,
            "largest_chunk_after": 0,
        }

        for chunk_idx, chunk in enumerate(chunks):
            splitting_stats["chunks_processed"] += 1
            content = chunk["content"]
            content_length = len(content)

            # Track largest chunk sizes
            if content_length > splitting_stats["largest_chunk_before"]:
                splitting_stats["largest_chunk_before"] = content_length

            # BEAM DEBUG: Print processing of each chunk
            if content_length > 500:  # Print chunks that might need splitting
                content_preview = content[:100] + "..." if len(content) > 100 else content
                print(
                    f"🔍 BEAM PROCESSING CHUNK {chunk_idx}: {content_length} chars, type={chunk['metadata'].get('element_category', 'unknown')}, preview='{content_preview}'"
                )

            # FORCE SPLIT: Change threshold to 1000 chars instead of max_chunk_size
            split_threshold = 1000  # HARDCODED: Force split anything over 1000 chars
            if content_length <= split_threshold:
                if content_length > 500:  # Print decision for potentially splittable chunks
                    print(
                        f"🔍 BEAM SKIPPING CHUNK {chunk_idx}: {content_length} <= {split_threshold} (HARDCODED threshold)"
                    )
                split_chunks.append(chunk)
                splitting_stats["chunks_unchanged"] += 1
                if content_length > splitting_stats["largest_chunk_after"]:
                    splitting_stats["largest_chunk_after"] = content_length
                continue

            # Split large content

            try:
                text_chunks = text_splitter.split_text(content)

                if len(text_chunks) <= 1:
                    # No splitting occurred

                    split_chunks.append(chunk)
                    splitting_stats["chunks_unchanged"] += 1
                    if content_length > splitting_stats["largest_chunk_after"]:
                        splitting_stats["largest_chunk_after"] = content_length
                    continue

                splitting_stats["chunks_split"] += 1
                splitting_stats["total_new_chunks"] += len(text_chunks)

                # Create new chunks from splits
                original_bbox = chunk["metadata"].get("bbox")

                for i, chunk_text in enumerate(text_chunks):
                    new_chunk = chunk.copy()
                    new_chunk["chunk_id"] = f"{chunk['chunk_id']}_split_{i}"
                    new_chunk["content"] = chunk_text

                    # Update metadata for split chunk
                    new_metadata = chunk["metadata"].copy()
                    new_metadata["content_length"] = len(chunk_text)
                    new_metadata["is_semantic_split"] = True
                    new_metadata["split_index"] = i
                    new_metadata["total_splits"] = len(text_chunks)
                    new_metadata["original_chunk_id"] = chunk["chunk_id"]

                    # EXPLICIT FIX: Ensure bbox is preserved in split chunks
                    if original_bbox is not None:
                        new_metadata["bbox"] = original_bbox

                    new_chunk["metadata"] = new_metadata

                    # Verify bbox is preserved
                    split_bbox = new_metadata.get("bbox")

                    split_chunks.append(new_chunk)

                    # Track largest chunk after splitting
                    if len(chunk_text) > splitting_stats["largest_chunk_after"]:
                        splitting_stats["largest_chunk_after"] = len(chunk_text)

            except Exception as e:
                print(f"🔍 BEAM ERROR: Failed to split chunk {chunk.get('chunk_id', 'unknown')}: {e}")
                split_chunks.append(chunk)
                splitting_stats["chunks_unchanged"] += 1
                if content_length > splitting_stats["largest_chunk_after"]:
                    splitting_stats["largest_chunk_after"] = content_length

        splitting_stats["semantic_splitting_enabled"] = True

        # BEAM DEBUG: Final summary
        final_sizes = [len(chunk["content"]) for chunk in split_chunks]
        print(
            f"🔍 BEAM FINAL CHUNKING SUMMARY: {len(split_chunks)} chunks, sizes: min={min(final_sizes) if final_sizes else 0}, max={max(final_sizes) if final_sizes else 0}, avg={sum(final_sizes) / len(final_sizes) if final_sizes else 0:.1f}"
        )
        print(f"🔍 BEAM Semantic splitting complete: {splitting_stats}")
        logger.info(f"Semantic splitting complete: {splitting_stats}")
        return split_chunks, splitting_stats

    def merge_small_chunks(self, elements: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Merge small adjacent chunks to enforce minimum chunk size"""
        if not elements:
            return elements, {"merging_enabled": False, "no_elements": True}

        logger.info(f"Merging small chunks (min_size: {self.min_chunk_size})...")

        merged_elements = []
        current_merge_group = []
        merging_stats = {
            "elements_processed": 0,
            "small_elements_found": 0,
            "merge_groups_created": 0,
            "final_elements": 0,
        }

        for el in elements:
            merging_stats["elements_processed"] += 1

            # Get element content and metadata
            meta = self.extract_structural_metadata(el)
            content = self.compose_final_content(el, meta)
            content_length = len(content)

            if content_length < self.min_chunk_size:
                merging_stats["small_elements_found"] += 1
                current_merge_group.append(el)
            else:
                # Process any pending merge group
                if current_merge_group:
                    merged_element = self._merge_element_group(current_merge_group)
                    if merged_element:
                        merged_elements.append(merged_element)
                        merging_stats["merge_groups_created"] += 1
                    current_merge_group = []

                # Add current large element as-is
                merged_elements.append(el)

        # Handle remaining merge group
        if current_merge_group:
            merged_element = self._merge_element_group(current_merge_group)
            if merged_element:
                merged_elements.append(merged_element)
                merging_stats["merge_groups_created"] += 1

        merging_stats["final_elements"] = len(merged_elements)
        merging_stats["merging_enabled"] = True
        logger.info(f"Chunk merging complete: {merging_stats}")

        return merged_elements, merging_stats

    def _merge_element_group(self, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Merge a group of small elements into one"""
        if not elements:
            return None

        if len(elements) == 1:
            return elements[0]

        # Use the first element as base
        base_element = elements[0].copy()
        base_meta = self.extract_structural_metadata(base_element)

        # Combine content from all elements (extract raw text without section headers)
        combined_content_parts = []
        for el in elements:
            meta = self.extract_structural_metadata(el)
            # Get raw text content without section headers
            raw_content = self.extract_text_content(el, meta)
            if raw_content.strip():
                combined_content_parts.append(raw_content.strip())

        combined_content = "\n\n".join(combined_content_parts)

        # Update metadata for merged element
        base_meta["element_id"] = f"merged_{base_meta.get('element_id', 'unknown')}"
        base_meta["content_length"] = len(combined_content)
        base_meta["is_merged"] = True
        base_meta["merged_count"] = len(elements)
        base_meta["element_category"] = "MergedContent"

        # Store merged content
        base_element["merged_content"] = combined_content
        base_element["structural_metadata"] = base_meta

        return base_element

    def create_final_chunks(self, elements: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Main orchestrator: transform elements into final chunks with processing statistics"""
        logger.info("=== INTELLIGENT CHUNKING PIPELINE ===")

        # Step 1: Filter noise
        filtered_elements, filtering_stats = self.filter_noise_elements(elements)

        # Step 2: Group list items
        grouped_elements, grouping_stats = self.group_list_items(filtered_elements)

        # Step 3: Merge small chunks BEFORE text splitting
        merged_elements, merging_stats = self.merge_small_chunks(grouped_elements)

        # Step 4: Compose content for each element
        composed_chunks = []
        for el in merged_elements:
            meta = self.extract_structural_metadata(el)
            text_content = self.extract_text_content(el, meta)
            section_title = meta.get("section_title_inherited", "Unknown Section")

            # Skip elements without meaningful content
            if not text_content or text_content.strip() == "":
                continue

            # Compose content
            content = self.compose_final_content(el, meta)

            # BEAM DEBUG: Print content composition for large content
            if len(content) > 1000:
                content_preview = content[:200] + "..." if len(content) > 200 else content
                print(
                    f"🔍 BEAM COMPOSING LARGE CONTENT: {len(content)} chars, type={meta.get('element_category', 'unknown')}, preview='{content_preview}'"
                )

            # Create chunk object with composed content
            chunk_bbox = meta.get("bbox")
            chunk_id = str(uuid.uuid4())
            element_type = el.get("element_type", "unknown")
            element_category = meta.get("element_category", "unknown")

            chunk = {
                "chunk_id": chunk_id,
                "content": content,
                "metadata": {
                    "source_filename": meta.get("source_filename"),
                    "page_number": meta.get("page_number"),
                    "bbox": chunk_bbox,  # Preserve bounding box coordinates
                    "element_category": element_category,
                    "section_title_inherited": section_title,
                    "text_complexity": meta.get("text_complexity", "medium"),
                    "content_length": len(content),  # Use composed content length
                    "has_numbers": meta.get("has_numbers", False),
                    "has_tables_on_page": meta.get("has_tables_on_page", False),
                    "has_images_on_page": meta.get("has_images_on_page", False),
                    "section_title_category": meta.get("section_title_category"),
                    "section_title_pattern": meta.get("section_title_pattern"),
                    "processing_strategy": meta.get("processing_strategy"),
                    "image_filepath": meta.get("image_filepath"),
                    "page_context": meta.get("page_context", "unknown"),
                    # Preserve enrichment metadata if available
                    "enrichment_metadata": el.get("enrichment_metadata"),
                    # Preserve original structural metadata
                    "structural_metadata": meta,
                },
            }

            composed_chunks.append(chunk)

        # Step 5: Apply semantic text splitting to composed chunks
        final_chunks, splitting_stats = self.apply_semantic_text_splitting_to_chunks(composed_chunks)

        # Combine all processing statistics
        processing_stats = {
            "filtering_stats": filtering_stats,
            "grouping_stats": grouping_stats,
            "splitting_stats": splitting_stats,
            "merging_stats": merging_stats,
            "total_elements_processed": len(elements),
            "final_chunks_created": len(final_chunks),
        }

        logger.info(f"Final chunks created: {len(final_chunks)}")
        return final_chunks, processing_stats

    def analyze_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate enhanced analysis of chunks with examples and quality metrics"""
        if not chunks:
            return {"error": "No chunks to analyze"}

        total = len(chunks)
        avg_words = sum(len(c["content"].split()) for c in chunks) / total
        avg_chars = sum(len(c["content"]) for c in chunks) / total

        # Content type distribution with examples
        type_dist = {}
        type_examples = {}
        section_headers_distribution = {}

        for c in chunks:
            meta = c["metadata"]
            cat = meta.get("element_category", "unknown")
            type_dist[cat] = type_dist.get(cat, 0) + 1

            # Collect section headers distribution
            section_title = meta.get("section_title_inherited", "Unknown Section")
            section_headers_distribution[section_title] = section_headers_distribution.get(section_title, 0) + 1

            # Collect examples for each type (up to 2 per type)
            if cat not in type_examples:
                type_examples[cat] = []
            if len(type_examples[cat]) < 2:
                type_examples[cat].append(
                    {
                        "content_preview": (c["content"][:300] + "..." if len(c["content"]) > 300 else c["content"]),
                        "page_number": meta.get("page_number"),
                        "section_title": meta.get("section_title_inherited"),
                        "size": len(c["content"]),
                    }
                )

        # Chunk size distribution
        chunk_sizes = [len(c["content"]) for c in chunks]
        size_distribution = {
            "small": len([s for s in chunk_sizes if s < 500]),
            "medium": len([s for s in chunk_sizes if 500 <= s < 1000]),
            "large": len([s for s in chunk_sizes if s >= 1000]),
        }

        # Additional size tracking for quality analysis
        very_small_chunks = len([s for s in chunk_sizes if s < 150])
        very_large_chunks = len([s for s in chunk_sizes if s > 750])

        # Find shortest and longest chunks
        sorted_chunks = sorted(chunks, key=lambda x: len(x["content"]))
        shortest_chunks = sorted_chunks[:3] if len(sorted_chunks) >= 3 else sorted_chunks
        longest_chunks = sorted_chunks[-3:] if len(sorted_chunks) >= 3 else sorted_chunks

        shortest_examples = [
            {
                "chunk_id": c["chunk_id"],
                "content": c["content"],
                "size": len(c["content"]),
                "type": c["metadata"].get("element_category"),
                "page": c["metadata"].get("page_number"),
            }
            for c in shortest_chunks
        ]

        longest_examples = [
            {
                "chunk_id": c["chunk_id"],
                "content": c["content"],
                "size": len(c["content"]),
                "type": c["metadata"].get("element_category"),
                "page": c["metadata"].get("page_number"),
            }
            for c in longest_chunks
        ]

        return {
            "total_chunks": total,
            "average_words_per_chunk": round(avg_words, 2),
            "average_chars_per_chunk": round(avg_chars, 2),
            "content_type_distribution": type_dist,
            "chunk_type_examples": type_examples,
            "section_headers_distribution": section_headers_distribution,
            "chunk_size_distribution": size_distribution,
            "min_chunk_size": min(chunk_sizes) if chunk_sizes else 0,
            "max_chunk_size": max(chunk_sizes) if chunk_sizes else 0,
            "shortest_chunks": shortest_examples,
            "longest_chunks": longest_examples,
            "very_small_chunks": very_small_chunks,
            "very_large_chunks": very_large_chunks,
        }

    def validate_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
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


class ChunkingStep(PipelineStep):
    """Production chunking step that preserves intelligent chunking logic"""

    def __init__(
        self,
        config: Dict[str, Any],
        storage_client=None,
        progress_tracker=None,
        db=None,
        pipeline_service=None,
        storage_service=None,
    ):
        super().__init__(config, progress_tracker)
        self.storage_client = storage_client
        self.db = db
        self.pipeline_service = pipeline_service
        self.storage_service = storage_service or StorageService()

        # Create database client if not provided
        if self.db is None:
            from src.config.database import get_supabase_admin_client

            self.db = get_supabase_admin_client()

        # Initialize chunking engine
        chunking_config = config.get("chunking", {})
        self.chunker = IntelligentChunker(chunking_config)

    async def execute(self, input_data: Any, indexing_run_id: UUID = None, document_id: UUID = None) -> StepResult:
        """Execute the chunking step with enriched data from previous step"""
        start_time = datetime.now()

        try:
            logger.info("Starting chunking step execution")

            # Extract enriched data from input
            enriched_data = input_data
            if hasattr(input_data, "data"):
                enriched_data = input_data.data
            elif hasattr(input_data, "output_data"):
                enriched_data = input_data.output_data

            # Combine all elements from enriched data
            all_elements = []

            # Add text elements
            text_elements = enriched_data.get("text_elements", [])

            for element in text_elements:
                element["element_type"] = "text"
            all_elements.extend(text_elements)

            # Add table elements
            table_elements = enriched_data.get("table_elements", [])

            for element in table_elements:
                element["element_type"] = "table"
            all_elements.extend(table_elements)

            # Add extracted pages (full page images)
            extracted_pages = enriched_data.get("extracted_pages", {})

            for page_num, page_info in extracted_pages.items():
                # Check bbox before modification
                bbox_before = None
                if "structural_metadata" in page_info:
                    bbox_before = page_info["structural_metadata"].get("bbox")

                page_info["element_type"] = "full_page_image"
                page_info["page_number"] = int(page_num)

                # Check bbox after modification
                bbox_after = None
                if "structural_metadata" in page_info:
                    bbox_after = page_info["structural_metadata"].get("bbox")

                all_elements.append(page_info)

            logger.info(f"Processing {len(all_elements)} total elements")

            # Create chunks using intelligent chunking
            final_chunks, processing_stats = self.chunker.create_final_chunks(all_elements)

            # Generate analysis and validation
            analysis = self.chunker.analyze_chunks(final_chunks)
            validation = self.chunker.validate_chunks(final_chunks)

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()

            # Create enhanced summary statistics
            summary_stats = {
                "total_elements_processed": len(all_elements),
                "total_chunks_created": len(final_chunks),
                "chunk_type_distribution": analysis.get("content_type_distribution", {}),
                "chunk_size_distribution": analysis.get("chunk_size_distribution", {}),
                "average_chunk_size": analysis.get("average_chars_per_chunk", 0),
                "validation_results": validation,
                # Enhanced statistics
                "shortest_chunks": analysis.get("shortest_chunks", []),
                "longest_chunks": analysis.get("longest_chunks", []),
                "chunk_type_examples": analysis.get("chunk_type_examples", {}),
                "section_headers_distribution": analysis.get("section_headers_distribution", {}),
                "very_small_chunks": analysis.get("very_small_chunks", 0),
                "very_large_chunks": analysis.get("very_large_chunks", 0),
                "list_grouping_stats": processing_stats.get("grouping_stats", {}),
                "noise_filtering_stats": processing_stats.get("filtering_stats", {}),
            }

            # Create enhanced sample outputs for debugging
            sample_outputs = {
                "sample_chunks": [
                    {
                        "chunk_id": chunk["chunk_id"],
                        "content_preview": (
                            chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"]
                        ),
                        "metadata": {
                            "element_category": chunk["metadata"].get("element_category"),
                            "page_number": chunk["metadata"].get("page_number"),
                            "section_title": chunk["metadata"].get("section_title_inherited"),
                        },
                    }
                    for chunk in final_chunks[:3]  # First 3 chunks as samples
                ],
                "shortest_chunks": analysis.get("shortest_chunks", []),
                "longest_chunks": analysis.get("longest_chunks", []),
                "chunk_type_examples": analysis.get("chunk_type_examples", {}),
                "list_grouping_examples": processing_stats.get("grouping_stats", {}).get("group_examples", []),
                "noise_filtering_examples": processing_stats.get("filtering_stats", {}).get("filtered_elements", [])[
                    :3
                ],  # Show first 3 filtered items
            }

            logger.info(f"Chunking completed: {len(final_chunks)} chunks created")
            logger.info(f"Summary: {summary_stats}")

            # Store chunks in database for embedding step
            if indexing_run_id and document_id:
                await self.store_chunks_in_database(final_chunks, indexing_run_id, document_id)
            else:
                logger.warning("No run information provided, skipping database storage")

            return StepResult(
                step="chunking",
                status="completed",
                duration_seconds=duration,
                summary_stats=summary_stats,
                sample_outputs=sample_outputs,
                data={
                    "chunks": final_chunks,
                    "chunking_metadata": {
                        "total_chunks": len(final_chunks),
                        "chunk_types": analysis.get("content_type_distribution", {}),
                        "processing_strategy": "intelligent_chunking",
                        "analysis": analysis,
                        "validation": validation,
                        "processing_stats": processing_stats,
                    },
                },
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Chunking step failed: {str(e)}")
            raise AppError(
                "Chunking step failed",
                error_code=ErrorCode.INTERNAL_ERROR,
                details={"reason": str(e)},
            ) from e

    async def store_chunks_in_database(self, chunks: List[Dict[str, Any]], indexing_run_id: UUID, document_id: UUID):
        """Store chunks in document_chunks table for embedding step"""
        if not self.db:
            logger.warning("No database client available, skipping chunk storage")
            return

        try:
            logger.info(f"Storing {len(chunks)} chunks in document_chunks table")

            # Store each chunk in database
            for chunk_index, chunk in enumerate(chunks):
                self.db.table("document_chunks").insert(
                    {
                        "indexing_run_id": str(indexing_run_id),
                        "document_id": str(document_id),
                        "chunk_id": chunk["chunk_id"],
                        "content": chunk["content"],
                        "metadata": chunk["metadata"],
                        # Embedding fields will be NULL initially
                        "embedding_1024": None,
                        "embedding_model": None,
                        "embedding_provider": None,
                        "embedding_metadata": {},
                        "embedding_created_at": None,
                    }
                ).execute()

            logger.info(f"Successfully stored {len(chunks)} chunks in database")

        except Exception as e:
            logger.error(f"Failed to store chunks in database: {e}")
            # Don't raise the exception - chunk storage failure shouldn't fail the entire step
            # The chunks are still returned in the StepResult for backward compatibility

    async def validate_prerequisites_async(self, input_data: Any) -> bool:
        """Validate that input data contains enriched elements"""
        try:
            # Check if input_data has the expected structure
            enriched_data = input_data
            if hasattr(input_data, "data"):
                enriched_data = input_data.data
            elif hasattr(input_data, "output_data"):
                enriched_data = input_data.output_data

            # Validate that we have at least some elements to process
            text_elements = enriched_data.get("text_elements", [])
            table_elements = enriched_data.get("table_elements", [])
            extracted_pages = enriched_data.get("extracted_pages", {})

            total_elements = len(text_elements) + len(table_elements) + len(extracted_pages)

            if total_elements == 0:
                logger.warning("No elements found in enriched data")
                return False

            logger.info(f"Prerequisites validated: {total_elements} elements found")
            return True

        except Exception as e:
            logger.error(f"Prerequisites validation failed: {str(e)}")
            return False

    def estimate_duration(self, input_data: Any) -> int:
        """Estimate chunking duration based on input size"""
        try:
            enriched_data = input_data
            if hasattr(input_data, "data"):
                enriched_data = input_data.data
            elif hasattr(input_data, "output_data"):
                enriched_data = input_data.output_data

            # Count elements
            text_elements = len(enriched_data.get("text_elements", []))
            table_elements = len(enriched_data.get("table_elements", []))
            extracted_pages = len(enriched_data.get("extracted_pages", {}))

            total_elements = text_elements + table_elements + extracted_pages

            # Rough estimate: 0.1 seconds per element
            estimated_seconds = max(5, total_elements * 0.1)

            logger.info(f"Estimated chunking duration: {estimated_seconds:.1f} seconds for {total_elements} elements")
            return int(estimated_seconds)

        except Exception as e:
            logger.warning(f"Could not estimate duration: {str(e)}")
            return 30  # Default estimate
