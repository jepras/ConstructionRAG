"""Production metadata step for document processing pipeline."""

import re
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

# Pydantic for enhanced metadata
from pydantic import BaseModel, Field
from typing import Literal

from ...shared.base_step import PipelineStep
from models import StepResult
from ...shared.models import DocumentInput, PipelineError

logger = logging.getLogger(__name__)


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
            logger.debug(f"Page change: {self.current_page} → {page_num}")
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
            logger.debug(f"Page change: {self.current_page} → {page_num}")
            self.current_page = page_num

        # Extract HTML text from table if available
        html_text = None
        if hasattr(table_element, "html"):
            html_text = getattr(table_element, "html", "")
        elif hasattr(table_element, "metadata") and hasattr(
            table_element.metadata, "html"
        ):
            html_text = getattr(table_element.metadata, "html", "")

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
            logger.debug(f"Page change: {self.current_page} → {page_num}")
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
                logger.debug(
                    f'Found numbered category title: "{text.strip()}" (category: {category})'
                )
            else:
                logger.debug(
                    f'Skipping non-numbered title: "{text.strip()}" (category: {category})'
                )

        # Method 2: Pattern-based detection (ONLY for numbered sections)
        pattern_title = self._detect_pattern_based_title(text, category)
        if pattern_title:
            struct_meta.section_title_pattern = pattern_title
            logger.debug(
                f'Found numbered pattern title: "{pattern_title}" (category: {category}, page: {page_num})'
            )

            # Check if this is a MAJOR section (should update page inheritance)
            is_major_section = self._is_major_section(text, category)

            if is_major_section:
                logger.debug(
                    f"MAJOR NUMBERED SECTION: Updating page {page_num} inheritance"
                )
                # Update page-level section
                self.page_sections[page_num] = pattern_title
                self.current_section_title = pattern_title
            else:
                logger.debug(f"Minor numbered section: Not changing page inheritance")

        # Method 3: Page-aware inheritance (NEW!)
        page_section = self.page_sections.get(page_num)
        if page_section:
            struct_meta.section_title_inherited = page_section
            logger.debug(f'Page {page_num} inherits: "{page_section}"')
        elif self.current_section_title:
            # Fall back to document-level inheritance
            struct_meta.section_title_inherited = self.current_section_title
            logger.debug(f'Document fallback: "{self.current_section_title}"')

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


class MetadataStep(PipelineStep):
    """Production metadata step implementing structural awareness analysis"""

    def __init__(
        self, config: Dict[str, Any], storage_client=None, progress_tracker=None
    ):
        super().__init__(config, progress_tracker)
        self.storage_client = storage_client

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
            logger.info("Starting metadata step for partition data")

            # Handle input data - could be StepResult from partition step, raw data, or indexing run ID
            if hasattr(input_data, "data") and input_data.data is not None:
                # Input is a StepResult from partition step
                partition_data = input_data.data
                logger.info("Processing partition data from StepResult")
            elif isinstance(input_data, dict):
                # Input is raw partition data
                partition_data = input_data
                logger.info("Processing raw partition data")
            elif isinstance(input_data, str) and input_data.startswith("run_"):
                # Input is an indexing run ID - load partition data from database
                from ...services.pipeline_service import PipelineService

                pipeline_service = PipelineService()
                indexing_run = await pipeline_service.get_indexing_run(input_data)
                if not indexing_run:
                    raise PipelineError(f"Indexing run not found: {input_data}")

                partition_result = indexing_run.step_results.get("partition")
                if not partition_result:
                    raise PipelineError(
                        f"No partition result found in indexing run: {input_data}"
                    )

                partition_data = partition_result.get("data", {})
                logger.info(f"Loaded partition data from indexing run: {input_data}")
            else:
                raise PipelineError(f"Invalid input data type: {type(input_data)}")

            # Validate input
            if not await self.validate_prerequisites_async(partition_data):
                raise PipelineError("Prerequisites not met for metadata step")

            # Execute metadata analysis
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
                        if e["structural_metadata"].has_numbers
                    ]
                ),
                "elements_with_sections": len(
                    [
                        e
                        for e in enriched_elements
                        if e["structural_metadata"].section_title_inherited
                        or e["structural_metadata"].section_title_pattern
                    ]
                ),
                "complexity_distribution": self._get_complexity_distribution(
                    enriched_elements
                ),
                "page_sections_detected": len(self.analyzer.page_sections),
            }

            # Create sample outputs for debugging
            text_elements = [
                {
                    "id": elem["id"],
                    "content_type": elem["structural_metadata"].content_type,
                    "page": elem["structural_metadata"].page_number,
                    "section_inherited": elem[
                        "structural_metadata"
                    ].section_title_inherited,
                    "has_numbers": elem["structural_metadata"].has_numbers,
                    "complexity": elem["structural_metadata"].text_complexity,
                }
                for elem in enriched_elements
                if elem["element_type"] == "text"
            ][:3]

            table_elements = [
                {
                    "id": elem["id"],
                    "page": elem["structural_metadata"].page_number,
                    "section_inherited": elem[
                        "structural_metadata"
                    ].section_title_inherited,
                    "has_numbers": elem["structural_metadata"].has_numbers,
                }
                for elem in enriched_elements
                if elem["element_type"] == "table"
            ][:2]

            sample_outputs = {
                "sample_text_elements": text_elements,
                "sample_tables": table_elements,
                "page_sections": dict(self.analyzer.page_sections),
            }

            return StepResult(
                step="metadata",
                status="completed",
                duration_seconds=duration,
                summary_stats=summary_stats,
                sample_outputs=sample_outputs,
                # Add real data for downstream steps
                data={
                    "enriched_elements": enriched_elements,
                    "page_sections": dict(self.analyzer.page_sections),
                    "source_partition_data": partition_data,
                },
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Metadata step failed: {e}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            return StepResult(
                step="metadata",
                status="failed",
                duration_seconds=duration,
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

    async def validate_prerequisites_async(self, input_data: Any) -> bool:
        """Validate metadata step prerequisites"""
        try:
            # Check if input_data contains partition results
            if not isinstance(input_data, dict):
                logger.error("Input data is not a dictionary")
                return False

            # Check for required keys from partition step
            required_keys = ["text_elements", "table_elements", "extracted_pages"]
            missing_keys = [key for key in required_keys if key not in input_data]

            if missing_keys:
                logger.error(f"Missing required keys in partition data: {missing_keys}")
                return False

            logger.info("Prerequisites validated for metadata step")
            return True

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
        """Synchronous metadata analysis implementation"""

        logger.info("Adding Enhanced Structural Awareness to Unified Data...")

        # Reset analyzer state for new document
        self.analyzer.reset_section_tracking()

        enriched_elements = []
        current_id = 1

        # Process text elements
        text_elements = partition_data.get("text_elements", [])
        logger.info(f"Processing {len(text_elements)} text elements...")

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
        sorted_pages = sorted(extracted_pages.items(), key=lambda x: x[0])

        for page_num, page_info in sorted_pages:
            try:
                element_id = str(current_id)
                structural_meta = self.analyzer.analyze_extracted_image(
                    page_info, element_id
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

        return enriched_elements

    def _get_complexity_distribution(
        self, enriched_elements: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Get distribution of text complexity levels"""
        distribution = {"simple": 0, "medium": 0, "complex": 0}
        for elem in enriched_elements:
            complexity = elem["structural_metadata"].text_complexity
            distribution[complexity] = distribution.get(complexity, 0) + 1
        return distribution
