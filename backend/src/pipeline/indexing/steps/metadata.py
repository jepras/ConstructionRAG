"""Production metadata step for document processing pipeline."""

import re
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path
from uuid import UUID

from ...shared.base_step import PipelineStep
from src.models import StepResult
from ...shared.models import DocumentInput, PipelineError
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError
from src.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class UnifiedElementAnalyzer:
    """Enhanced analyzer for unified partition data using pure JSON processing"""

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

        # SECTION DETECTION TRACKING
        self.detection_stats = {
            "total_elements_processed": 0,
            "elements_with_section_titles": 0,
            "detection_breakdown": {
                "category_based_detected": 0,
                "pattern_based_detected": 0,
                "inherited_from_page": 0,
            },
            "filtering_applied": {
                "diagram_contexts_filtered": 0,
                "bullet_points_filtered": 0,
                "truncated_text_filtered": 0,
                "minor_elements_filtered": 0,
            },
            "sample_detections": [],
            "sample_filtered": [],
        }

        # Track recent text elements for context analysis
        self.recent_text_elements = []

    def analyze_text_element(self, text_element: dict) -> dict:
        """Analyze a text element from partition data using pure JSON processing"""

        # Extract data from partition structure
        element_id = text_element["id"]
        text = text_element["text"]
        category = text_element["category"]
        page_num = text_element["page"]
        metadata_dict = text_element["metadata"]

        # Track page changes
        if page_num != self.current_page:
            logger.debug(f"Page change: {self.current_page} → {page_num}")
            self.current_page = page_num

        # Create structural metadata (pure dict, no Pydantic)
        structural_metadata = {
            "source_filename": metadata_dict.get("filename", "Unknown"),
            "page_number": page_num,
            "content_type": "text",
            "element_category": category,
            "element_id": element_id,
            "processing_strategy": "unified_fast_vision",
            "content_length": len(text),
            "has_numbers": self._detect_numbers(text),
            "text_complexity": self._assess_text_complexity(text),
            "section_title_inherited": None,  # Will be set by inheritance logic
            "section_title_pattern": None,  # Will be set by pattern detection
            "section_title_category": None,  # Will be set by category detection
        }

        # Apply section inheritance logic
        structural_metadata = self._detect_section_titles_page_aware(
            structural_metadata, text, category, page_num
        )

        return structural_metadata

    def analyze_table_element(self, table_element: dict, element_id: str) -> dict:
        """Analyze a table element from partition data using pure JSON processing"""

        # Extract data from partition structure
        text = table_element.get("text", "")
        category = table_element.get("category", "Table")
        metadata_dict = table_element.get("metadata", {})
        page_num = metadata_dict.get("page_number", 1)

        # Track page changes
        if page_num != self.current_page:
            logger.debug(f"Page change: {self.current_page} → {page_num}")
            self.current_page = page_num

        # Get HTML text from metadata
        html_text = metadata_dict.get("text_as_html", "")

        # Create structural metadata
        structural_metadata = {
            "source_filename": metadata_dict.get("filename", "Unknown"),
            "page_number": page_num,
            "content_type": "table",
            "element_category": category,
            "element_id": element_id,
            "processing_strategy": "unified_fast_vision",
            "html_text": html_text,
            "content_length": len(text),
            "has_numbers": self._detect_numbers(text),
            "has_tables_on_page": True,
            "text_complexity": "complex",  # Tables are typically complex
            "section_title_inherited": None,
            "section_title_pattern": None,
            "section_title_category": None,
        }

        # Apply section inheritance logic
        structural_metadata = self._detect_section_titles_page_aware(
            structural_metadata, text, category, page_num
        )

        return structural_metadata

    def analyze_extracted_image(
        self, page_num: str, page_info: dict, element_id: str
    ) -> dict:
        """Analyze an extracted page from partition data using pure JSON processing"""

        # Extract data from partition structure
        filename = page_info.get("filename", "Unknown")
        filepath = page_info.get("filepath", "")
        complexity = page_info.get("complexity", "unknown")

        # Track page changes
        page_num_int = int(page_num)
        if page_num_int != self.current_page:
            logger.debug(f"Page change: {self.current_page} → {page_num_int}")
            self.current_page = page_num_int

        # Create structural metadata
        structural_metadata = {
            "source_filename": filename,
            "page_number": page_num_int,  # Convert string key to int
            "content_type": "full_page_with_images",
            "element_category": "ExtractedPage",
            "element_id": element_id,
            "processing_strategy": "unified_fast_vision",
            "image_filepath": filepath,
            "has_images_on_page": True,
            "text_complexity": "complex",  # Images are typically complex
            "page_context": "image_page",
            "section_title_inherited": None,
            "section_title_pattern": None,
            "section_title_category": None,
        }

        # Get inherited section title
        page_section = self.page_sections.get(page_num_int)
        if page_section:
            structural_metadata["section_title_inherited"] = page_section
        elif self.current_section_title:
            structural_metadata["section_title_inherited"] = self.current_section_title

        return structural_metadata

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
        self, struct_meta: dict, text: str, category: str, page_num: int
    ) -> dict:
        """Enhanced section detection with page-aware inheritance (pure dict)"""

        # Track total elements processed
        self.detection_stats["total_elements_processed"] += 1

        # Method 1: Category-based detection (ONLY for numbered titles)
        if category.lower() in ["title", "header"]:
            # Check if title starts with a number pattern
            if self._starts_with_number(text):
                struct_meta["section_title_category"] = text.strip()
                self.detection_stats["detection_breakdown"][
                    "category_based_detected"
                ] += 1
                self.detection_stats["elements_with_section_titles"] += 1

                # Add to sample detections
                if len(self.detection_stats["sample_detections"]) < 5:
                    self.detection_stats["sample_detections"].append(
                        {
                            "text": text.strip(),
                            "detection_method": "category_based",
                            "confidence": "high",
                            "category": category,
                        }
                    )

        # Method 2: Pattern-based detection (ONLY for numbered sections)
        pattern_title = self._detect_pattern_based_title(text, category)
        if pattern_title:
            struct_meta["section_title_pattern"] = pattern_title
            self.detection_stats["detection_breakdown"]["pattern_based_detected"] += 1
            self.detection_stats["elements_with_section_titles"] += 1

            # Check if this is a MAJOR section (should update page inheritance)
            is_major_section = self._is_major_section(text, category)

            if is_major_section:
                # Update page-level section
                self.page_sections[page_num] = pattern_title
                self.current_section_title = pattern_title

                # Add to sample detections
                if len(self.detection_stats["sample_detections"]) < 5:
                    self.detection_stats["sample_detections"].append(
                        {
                            "text": text.strip(),
                            "detection_method": "pattern_based",
                            "confidence": "high",
                            "inherited_to_page": page_num,
                        }
                    )

        # Method 3: Page-aware inheritance (NEW!)
        page_section = self.page_sections.get(page_num)
        if page_section:
            struct_meta["section_title_inherited"] = page_section
            self.detection_stats["detection_breakdown"]["inherited_from_page"] += 1
        elif self.current_section_title:
            # Fall back to document-level inheritance
            struct_meta["section_title_inherited"] = self.current_section_title
            self.detection_stats["detection_breakdown"]["inherited_from_page"] += 1

        return struct_meta

    def _is_major_section(self, text: str, category: str) -> bool:
        """Determine if this is a major section that should update page inheritance"""

        # Filter out minor elements
        if category in ["FigureCaption", "Footer", "ListItem"]:
            self.detection_stats["filtering_applied"]["minor_elements_filtered"] += 1
            if len(self.detection_stats["sample_filtered"]) < 3:
                self.detection_stats["sample_filtered"].append(
                    {
                        "text": text.strip(),
                        "filter_reason": f"minor_element_category: {category}",
                        "detection_method": "filtered_out",
                    }
                )
            return False

        # ONLY numbered sections can be major sections
        if not self._starts_with_number(text):
            return False

        # Avoid truncated text (ends with hyphen, ellipsis, or incomplete words)
        text_stripped = text.strip()
        if (
            text_stripped.endswith("-")
            or text_stripped.endswith("...")
            or text_stripped.endswith("..")
        ):
            self.detection_stats["filtering_applied"]["truncated_text_filtered"] += 1
            if len(self.detection_stats["sample_filtered"]) < 3:
                self.detection_stats["sample_filtered"].append(
                    {
                        "text": text.strip(),
                        "filter_reason": "truncated_text",
                        "detection_method": "filtered_out",
                    }
                )
            return False

        # Option 2: Filter by Content Patterns - Detect diagram-specific patterns
        if self._contains_diagram_patterns(text_stripped):
            self.detection_stats["filtering_applied"]["bullet_points_filtered"] += 1
            if len(self.detection_stats["sample_filtered"]) < 3:
                self.detection_stats["sample_filtered"].append(
                    {
                        "text": text.strip(),
                        "filter_reason": "diagram_patterns",
                        "detection_method": "filtered_out",
                    }
                )
            return False

        # Option 1: Filter by Text Position/Context - Check for multiple numbered items in proximity
        if self._has_diagram_context(text_stripped):
            self.detection_stats["filtering_applied"]["diagram_contexts_filtered"] += 1
            if len(self.detection_stats["sample_filtered"]) < 3:
                self.detection_stats["sample_filtered"].append(
                    {
                        "text": text.strip(),
                        "filter_reason": "diagram_context",
                        "detection_method": "filtered_out",
                    }
                )
            return False

        # Check for major section patterns (numbered sections with meaningful content)
        if self.major_section_pattern.match(text_stripped):
            return True

        # Additional check: numbered sections that are long enough to be major
        if self._starts_with_number(text) and len(text_stripped) > 10:
            return True

        return False

    def _has_diagram_context(self, current_text: str) -> bool:
        """Check if current text appears in context with multiple numbered items (diagram)"""

        if len(self.recent_text_elements) < 3:
            return False

        # Count numbered items in recent context
        numbered_items = 0
        for elem in self.recent_text_elements[-5:]:  # Check last 5 elements
            if self._starts_with_number(elem["text"]):
                numbered_items += 1

        # If we have 3+ numbered items in recent context, likely a diagram
        if numbered_items >= 3:
            return True

        return False

    def _contains_diagram_patterns(self, text: str) -> bool:
        """Detect if text contains diagram-specific patterns that should not be major sections"""

        # Check for bullet point patterns
        if re.search(r"^\s*[-•*]\s+", text):
            return True

        # Check for letter-numbered lists (a) b) c))
        if re.search(r"[a-z]\)\s+", text, re.IGNORECASE):
            return True

        # Check for mixed numbering patterns (like "1. 2. 3." in same text)
        numbers = re.findall(r"\d+\.", text)
        if len(numbers) >= 2:
            return True

        # Check for diagram keywords
        diagram_keywords = [
            "tilbud",
            "licitation",
            "værktøjer",
            "sagsstørrelse",
            "tilstande",
        ]
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in diagram_keywords):
            return True

        return False

    def reset_section_tracking(self):
        """Reset all tracking (call between documents)"""
        self.page_sections = {}
        self.current_page = None
        self.current_section_title = None
        # Reset context tracking for new document
        self.recent_text_elements = []


class MetadataStep(PipelineStep):
    """Production metadata step implementing structural awareness analysis with pure JSON processing"""

    def __init__(
        self,
        config: Dict[str, Any],
        storage_client=None,
        progress_tracker=None,
        storage_service=None,
    ):
        super().__init__(config, progress_tracker)
        self.storage_client = storage_client
        self.storage_service = storage_service or StorageService()

        # Extract configuration
        self.enable_section_detection = config.get("enable_section_detection", True)
        self.enable_number_detection = config.get("enable_number_detection", True)
        self.enable_complexity_analysis = config.get("enable_complexity_analysis", True)

        # Initialize analyzer
        self.analyzer = UnifiedElementAnalyzer()

        logger.info("MetadataStep initialized")

    async def execute(self, input_data: Any) -> StepResult:
        """Execute the metadata step with async operations"""
        start_time = datetime.utcnow()

        try:
            # Debug logging to see what we're receiving in execute
            logger.info(
                f"🔍 MetadataStep execute received input_data type: {type(input_data)}"
            )
            logger.info(f"🔍 MetadataStep execute received input_data: {input_data}")

            logger.info("Starting metadata step for partition data")

            # Handle input data - could be StepResult from partition step, raw data, or indexing run ID
            if hasattr(input_data, "sample_outputs") and hasattr(input_data, "step"):
                # Input is a StepResult from partition step (unified processing)
                # Check data field first, then fall back to sample_outputs
                partition_data = (
                    input_data.data
                    if hasattr(input_data, "data") and input_data.data
                    else input_data.sample_outputs.get("partition_data", {})
                )
                logger.info(
                    f"Processing partition data from StepResult ({input_data.step})"
                )
            elif hasattr(input_data, "data") and input_data.data is not None:
                # Input is a StepResult from partition step (legacy)
                partition_data = input_data.data
                logger.info("Processing partition data from StepResult (legacy)")
            elif isinstance(input_data, dict):
                # Input is raw partition data
                partition_data = input_data
                logger.info("Processing raw partition data")
            elif isinstance(input_data, str):
                # Input is an indexing run ID (UUID string) - load partition data from database
                from src.services.pipeline_service import PipelineService

                # Use admin client for testing (bypass RLS)
                pipeline_service = PipelineService(use_admin_client=True)
                indexing_run = await pipeline_service.get_indexing_run(UUID(input_data))
                if not indexing_run:
                    raise PipelineError(f"Indexing run not found: {input_data}")

                partition_result = indexing_run.step_results.get("partition")
                if not partition_result:
                    raise PipelineError(
                        f"No partition result found in indexing run: {input_data}"
                    )

                # Handle both dict and StepResult objects
                if hasattr(partition_result, "data"):
                    # It's a StepResult object
                    partition_data = partition_result.data
                elif isinstance(partition_result, dict):
                    # It's a dictionary
                    partition_data = partition_result.get("data", {})
                else:
                    raise PipelineError(
                        f"Unexpected partition result type: {type(partition_result)}"
                    )

                logger.info(f"Loaded partition data from indexing run: {input_data}")
            else:
                raise PipelineError(f"Invalid input data type: {type(input_data)}")

            # Show partition data summary for debugging
            text_elements = partition_data.get("text_elements", [])
            table_elements = partition_data.get("table_elements", [])
            extracted_pages = partition_data.get("extracted_pages", {})

            logger.info(f"📋 Partition Data Summary:")
            logger.info(f"   Text Elements: {len(text_elements)}")
            logger.info(f"   Table Elements: {len(table_elements)}")
            logger.info(f"   Extracted Pages: {len(extracted_pages)}")

            # Validate input
            if not await self.validate_prerequisites_async(partition_data):
                raise PipelineError("Prerequisites not met for metadata step")

            # Execute metadata analysis
            logger.info("🚀 Executing metadata analysis...")
            enriched_elements = await self._analyze_metadata_async(partition_data)

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Create summary statistics
            summary_stats = {
                "total_elements": len(enriched_elements),
                "text_elements": len(
                    [e for e in enriched_elements if e["element_type"] == "text"]
                ),
                "table_elements": len(
                    [e for e in enriched_elements if e["element_type"] == "table"]
                ),
                "image_elements": len(
                    [
                        e
                        for e in enriched_elements
                        if e["element_type"] == "full_page_with_images"
                    ]
                ),
                "elements_with_numbers": len(
                    [
                        e
                        for e in enriched_elements
                        if e["structural_metadata"].get("has_numbers", False)
                    ]
                ),
                "elements_with_sections": len(
                    [
                        e
                        for e in enriched_elements
                        if e["structural_metadata"].get("section_title_inherited")
                        or e["structural_metadata"].get("section_title_pattern")
                    ]
                ),
                "complexity_distribution": self._get_complexity_distribution(
                    enriched_elements
                ),
                "page_sections_detected": len(self.analyzer.page_sections),
                # Enhanced section detection statistics
                "section_detection_stats": self.analyzer.detection_stats,
                "regex_patterns_used": {
                    "numbered_section_pattern": self.analyzer.numbered_section_pattern.pattern,
                    "major_section_pattern": self.analyzer.major_section_pattern.pattern,
                    "number_start_pattern": r"^\s*\d+(?:\.\d+)*\.?\s",
                },
            }

            # Create sample outputs for debugging
            text_elements = [
                {
                    "id": elem["id"],
                    "content_type": elem["structural_metadata"].get(
                        "content_type", "unknown"
                    ),
                    "page": elem["structural_metadata"].get("page_number", 0),
                    "section_inherited": elem["structural_metadata"].get(
                        "section_title_inherited"
                    ),
                    "has_numbers": elem["structural_metadata"].get(
                        "has_numbers", False
                    ),
                    "complexity": elem["structural_metadata"].get(
                        "text_complexity", "unknown"
                    ),
                }
                for elem in enriched_elements
                if elem["element_type"] == "text"
            ][:3]

            table_elements = [
                {
                    "id": elem["id"],
                    "page": elem["structural_metadata"].get("page_number", 0),
                    "section_inherited": elem["structural_metadata"].get(
                        "section_title_inherited"
                    ),
                    "has_numbers": elem["structural_metadata"].get(
                        "has_numbers", False
                    ),
                }
                for elem in enriched_elements
                if elem["element_type"] == "table"
            ][:2]

            sample_outputs = {
                "sample_text_elements": text_elements,
                "sample_tables": table_elements,
                "page_sections": dict(self.analyzer.page_sections),
            }

            # Log detailed results for debugging
            logger.info(f"✅ Metadata analysis completed!")
            logger.info(f"📊 Summary Stats: {summary_stats}")
            logger.info(
                f"📋 Sample Outputs: {len(sample_outputs.get('sample_text_elements', []))} text, {len(sample_outputs.get('sample_tables', []))} tables"
            )
            logger.info(f"📄 Page Sections: {sample_outputs.get('page_sections', {})}")

            # Show a sample enriched element
            if sample_outputs.get("sample_text_elements"):
                sample = sample_outputs["sample_text_elements"][0]
                logger.info(f"🔍 Sample Enriched Element:")
                logger.info(f"   ID: {sample.get('id')}")
                logger.info(f"   Page: {sample.get('page')}")
                logger.info(f"   Section Inherited: {sample.get('section_inherited')}")
                logger.info(f"   Has Numbers: {sample.get('has_numbers')}")
                logger.info(f"   Complexity: {sample.get('complexity')}")

            # Create enriched partition data by adding structural metadata to original elements
            enriched_partition_data = partition_data.copy()

            # Add structural metadata to text elements
            for i, text_element in enumerate(
                enriched_partition_data.get("text_elements", [])
            ):
                if i < len(enriched_elements):
                    text_element["structural_metadata"] = enriched_elements[i][
                        "structural_metadata"
                    ]

            # Add structural metadata to table elements
            table_start_idx = len(enriched_partition_data.get("text_elements", []))
            for i, table_element in enumerate(
                enriched_partition_data.get("table_elements", [])
            ):
                if table_start_idx + i < len(enriched_elements):
                    table_element["structural_metadata"] = enriched_elements[
                        table_start_idx + i
                    ]["structural_metadata"]

            # Add structural metadata to extracted pages
            page_start_idx = table_start_idx + len(
                enriched_partition_data.get("table_elements", [])
            )
            for i, (page_num, page_info) in enumerate(
                enriched_partition_data.get("extracted_pages", {}).items()
            ):
                if page_start_idx + i < len(enriched_elements):
                    page_info["structural_metadata"] = enriched_elements[
                        page_start_idx + i
                    ]["structural_metadata"]

            # Add page sections to the enriched data
            enriched_partition_data["page_sections"] = dict(self.analyzer.page_sections)

            return StepResult(
                step="metadata",
                status="completed",
                duration_seconds=duration,
                summary_stats=summary_stats,
                sample_outputs=sample_outputs,
                # Return enriched partition data with same structure
                data=enriched_partition_data,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"❌ Metadata step failed: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            raise AppError(
                "Metadata step failed",
                error_code=ErrorCode.INTERNAL_ERROR,
                details={"reason": str(e)},
            ) from e

    async def validate_prerequisites_async(self, input_data: Any) -> bool:
        """Validate metadata step prerequisites"""
        try:
            # Debug logging to see what we're receiving
            logger.info(
                f"🔍 MetadataStep validate_prerequisites_async received input_data type: {type(input_data)}"
            )

            # Handle StepResult objects (from unified processing)
            if hasattr(input_data, "sample_outputs") and hasattr(input_data, "step"):
                # This is a StepResult from a previous step
                logger.info(f"MetadataStep received StepResult from {input_data.step}")

                # Extract partition data from StepResult - check both data and sample_outputs
                partition_data = (
                    input_data.data
                    if hasattr(input_data, "data") and input_data.data
                    else input_data.sample_outputs.get("partition_data", {})
                )

                # Check for required keys from partition step
                required_keys = ["text_elements", "table_elements", "extracted_pages"]
                missing_keys = [
                    key for key in required_keys if key not in partition_data
                ]

                if missing_keys:
                    logger.error(
                        f"Missing required keys in partition data: {missing_keys}"
                    )
                    return False

                logger.info("Prerequisites validated for metadata step (StepResult)")
                return True

            # Handle dict objects (legacy single PDF processing)
            if isinstance(input_data, dict):
                # Check for required keys from partition step
                required_keys = ["text_elements", "table_elements", "extracted_pages"]
                missing_keys = [key for key in required_keys if key not in input_data]

                if missing_keys:
                    logger.error(
                        f"Missing required keys in partition data: {missing_keys}"
                    )
                    return False

                logger.info("Prerequisites validated for metadata step (dict)")
                return True

            # Unknown input type
            logger.error(f"Unknown input type for metadata step: {type(input_data)}")
            return False

        except Exception as e:
            logger.error(f"Prerequisites validation failed: {e}")
            return False

    def estimate_duration(self, input_data: Any) -> int:
        """Estimate metadata step duration in seconds"""
        try:
            # Estimate based on number of elements to process
            total_elements = (
                len(input_data.get("text_elements", []))
                + len(input_data.get("table_elements", []))
                + len(input_data.get("extracted_pages", {}))
            )
            # Rough estimate: 0.1 seconds per element
            return max(10, int(total_elements * 0.1))
        except:
            return 30  # Default 30 seconds

    async def _analyze_metadata_async(
        self, partition_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute the metadata analysis asynchronously"""

        # Run the CPU-intensive analysis in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self._analyze_metadata_sync, partition_data
        )

        return result

    def _analyze_metadata_sync(
        self, partition_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Synchronous metadata analysis with pure JSON processing"""

        logger.info("Adding Enhanced Structural Awareness to Unified Data...")

        # Reset analyzer state for new document
        self.analyzer.reset_section_tracking()

        enriched_elements = []
        current_id = 1

        # Process text elements
        text_elements = partition_data.get("text_elements", [])
        logger.info(f"Processing {len(text_elements)} text elements...")

        # Show category distribution
        categories = {}
        for elem in text_elements:
            cat = elem.get("category", "Unknown")
            categories[cat] = categories.get(cat, 0) + 1
        logger.info(f"Category distribution: {categories}")

        # Sort text elements by page number for proper inheritance
        sorted_text_elements = sorted(text_elements, key=lambda x: x["page"])

        for text_element in sorted_text_elements:
            try:
                structural_meta = self.analyzer.analyze_text_element(text_element)

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
                logger.error(f"Error processing text element {text_element['id']}: {e}")

        # Process table elements
        table_elements = partition_data.get("table_elements", [])
        logger.info(f"Processing {len(table_elements)} table elements...")

        for table_element in table_elements:
            try:
                element_id = str(current_id)
                structural_meta = self.analyzer.analyze_table_element(
                    table_element, element_id
                )

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
                logger.error(f"Error processing table element: {e}")

        # Process extracted pages (full page images)
        extracted_pages = partition_data.get("extracted_pages", {})
        logger.info(f"Processing {len(extracted_pages)} extracted pages...")

        # Sort pages by page number for consistent numbering
        sorted_pages = sorted(extracted_pages.items(), key=lambda x: int(x[0]))

        for page_num, page_info in sorted_pages:
            try:
                element_id = str(current_id)
                structural_meta = self.analyzer.analyze_extracted_image(
                    page_num, page_info, element_id
                )

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
                logger.error(f"Error processing page {page_num}: {e}")

        logger.info(
            f"Enhanced analysis complete! Total enriched elements: {len(enriched_elements)}"
        )

        # Show page section summary
        logger.info("PAGE SECTION SUMMARY:")
        for page_num, section in self.analyzer.page_sections.items():
            logger.info(f'Page {page_num}: "{section}"')

        # Count elements with section inheritance
        elements_with_sections = sum(
            1
            for elem in enriched_elements
            if elem.get("structural_metadata", {}).get("section_title_inherited")
        )
        logger.info(
            f"Elements with section inheritance: {elements_with_sections}/{len(enriched_elements)}"
        )

        # Show section inheritance summary (reduced verbosity)
        section_summary = {}
        for elem in enriched_elements:
            inherited = elem.get("structural_metadata", {}).get(
                "section_title_inherited"
            )
            if inherited:
                section_summary[inherited] = section_summary.get(inherited, 0) + 1

        logger.info(
            f"Section inheritance summary: {len(section_summary)} unique sections"
        )

        return enriched_elements

    def _get_complexity_distribution(
        self, enriched_elements: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Get distribution of text complexity levels"""
        distribution = {"simple": 0, "medium": 0, "complex": 0}
        for elem in enriched_elements:
            complexity = elem["structural_metadata"].get("text_complexity", "unknown")
            distribution[complexity] = distribution.get(complexity, 0) + 1
        return distribution
