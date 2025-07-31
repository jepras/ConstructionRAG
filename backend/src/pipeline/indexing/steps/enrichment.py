"""Production enrichment step for document processing pipeline."""

import os
import asyncio
import base64
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

# VLM Components
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Pipeline components
from ...shared.base_step import PipelineStep
from src.models import StepResult
from ...shared.models import PipelineError

logger = logging.getLogger(__name__)


def extract_url_string(url_data: Any) -> Optional[str]:
    """Extract URL string from various URL formats"""
    if isinstance(url_data, str):
        return url_data
    elif isinstance(url_data, dict):
        # Handle dictionary format with signedURL/signedUrl keys
        if "signedURL" in url_data:
            return url_data["signedURL"]
        elif "signedUrl" in url_data:
            return url_data["signedUrl"]
        elif "url" in url_data:
            return url_data["url"]
        else:
            logger.warning(f"Unknown URL dictionary format: {url_data}")
            return None
    else:
        logger.warning(f"Unknown URL data type: {type(url_data)} - {url_data}")
        return None


class ConstructionVLMCaptioner:
    """Specialized VLM captioner for construction/technical content"""

    def __init__(self, model_name: str, api_key: str, caption_language: str = "Danish"):
        self.model_name = model_name
        self.caption_language = caption_language

        # Initialize VLM client
        self.vlm_client = ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            default_headers={"HTTP-Referer": "http://localhost"},
        )

        logger.info(f"VLM Captioner initialized with {self.model_name}")
        logger.info(f"Caption language set to: {self.caption_language}")

    async def caption_table_html_async(
        self, table_html: str, element_context: dict
    ) -> str:
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

IMPORTANT: Please provide your detailed, technical caption in {self.caption_language}."""

        try:
            response = await self.vlm_client.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            logger.error(f"Error captioning table HTML: {e}")
            return f"Error generating caption: {str(e)}"

    async def caption_table_image_async(
        self, image_url: str, element_context: dict
    ) -> str:
        """Generate caption for table using image URL"""

        page_num = element_context.get("page_number", "unknown")
        source_file = element_context.get("source_filename", "unknown")

        # DEBUG: Log the URL being sent to VLM
        logger.info(f"VLM DEBUG: Sending table image URL to VLM: {image_url}")
        logger.info(f"VLM DEBUG: Context - Page: {page_num}, File: {source_file}")

        prompt = f"""You are analyzing a table image extracted from page {page_num} of a construction/technical document ({source_file}).

Please provide a comprehensive description that captures:

1. **All Visible Text**: Read and transcribe ALL text visible in the table, including headers, data, footnotes
2. **Table Structure**: Number of rows, columns, organization
3. **Technical Content**: Any measurements, codes, specifications, standards mentioned
4. **Data Relationships**: How the data is organized and what it represents
5. **Construction Context**: How this information relates to building/engineering work

Focus on being extremely detailed about all visible text and numbers - this will be used for search and retrieval.

IMPORTANT: Please provide your detailed description in {self.caption_language}."""

        try:
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    },
                ]
            )

            # DEBUG: Log the message structure being sent
            logger.info(
                f"VLM DEBUG: Sending message with image_url type and URL: {image_url}"
            )

            response = await self.vlm_client.ainvoke([message])

            # DEBUG: Log the response
            logger.info(f"VLM DEBUG: Received response length: {len(response.content)}")
            logger.info(f"VLM DEBUG: Response preview: {response.content[:200]}...")

            return response.content.strip()
        except Exception as e:
            logger.error(f"Error captioning table image: {e}")
            logger.error(f"VLM DEBUG: Failed to process image URL: {image_url}")
            return f"Error generating caption: {str(e)}"

    async def caption_full_page_image_async(
        self, image_url: str, page_context: dict, page_text_context: str = ""
    ) -> str:
        """Generate caption for full page image with surrounding text context"""

        page_num = page_context.get("page_number", "unknown")
        source_file = page_context.get("source_filename", "unknown")
        complexity = page_context.get("text_complexity", "unknown")

        # DEBUG: Log the URL being sent to VLM
        logger.info(f"VLM DEBUG: Sending full-page image URL to VLM: {image_url}")
        logger.info(
            f"VLM DEBUG: Context - Page: {page_num}, File: {source_file}, Complexity: {complexity}"
        )

        # Build context-aware prompt
        context_section = ""
        if page_text_context.strip():
            context_section = f"""

**Text Context from this page:**
{page_text_context[:1500]}"""  # Configurable context limit

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

IMPORTANT: Please provide your comprehensive description in {self.caption_language}."""

        try:
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    },
                ]
            )

            # DEBUG: Log the message structure being sent
            logger.info(
                f"VLM DEBUG: Sending full-page message with image_url type and URL: {image_url}"
            )

            response = await self.vlm_client.ainvoke([message])

            # DEBUG: Log the response
            logger.info(
                f"VLM DEBUG: Received full-page response length: {len(response.content)}"
            )
            logger.info(
                f"VLM DEBUG: Full-page response preview: {response.content[:200]}..."
            )

            return response.content.strip()
        except Exception as e:
            logger.error(f"Error captioning full page image: {e}")
            logger.error(
                f"VLM DEBUG: Failed to process full-page image URL: {image_url}"
            )
            return f"Error generating caption: {str(e)}"


class EnrichmentStep(PipelineStep):
    """Production enrichment step implementing VLM captioning for tables and images"""

    def __init__(
        self, config: Dict[str, Any], storage_client=None, progress_tracker=None
    ):
        super().__init__(config, progress_tracker)
        self.storage_client = storage_client

        # Extract configuration
        self.vlm_model = config.get("vlm_model", "anthropic/claude-3-5-sonnet")
        self.caption_language = config.get("caption_language", "Danish")
        self.max_text_context_length = config.get("max_text_context_length", 1500)
        self.max_page_text_elements = config.get("max_page_text_elements", 5)

        # Initialize VLM captioner
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise PipelineError("OPENROUTER_API_KEY not found in environment variables")

        self.vlm_captioner = ConstructionVLMCaptioner(
            model_name=self.vlm_model,
            api_key=api_key,
            caption_language=self.caption_language,
        )

        logger.info("EnrichmentStep initialized")

    async def execute(self, input_data: Any) -> StepResult:
        """Execute the enrichment step with async VLM operations"""
        start_time = datetime.utcnow()

        try:
            logger.info("Starting enrichment step for metadata output")

            # Handle input data - could be StepResult from metadata step or raw data
            if hasattr(input_data, "data") and input_data.data is not None:
                # Input is a StepResult from metadata step
                metadata_output = input_data.data
                logger.info("Processing metadata output from StepResult")
            elif isinstance(input_data, dict):
                # Input is raw metadata output
                metadata_output = input_data
                logger.info("Processing raw metadata output")
            else:
                raise PipelineError(f"Invalid input data type: {type(input_data)}")

            # Validate input
            if not await self.validate_prerequisites_async(metadata_output):
                raise PipelineError("Prerequisites not met for enrichment step")

            # Execute VLM enrichment
            enriched_data = await self._enrich_with_vlm_async(metadata_output)

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Create summary statistics
            summary_stats = {
                "tables_processed": len(
                    [
                        t
                        for t in enriched_data.get("table_elements", [])
                        if "enrichment_metadata" in t
                    ]
                ),
                "images_processed": len(
                    [
                        p
                        for p in enriched_data.get("extracted_pages", {}).values()
                        if "enrichment_metadata" in p
                    ]
                ),
                "total_caption_words": sum(
                    t.get("enrichment_metadata", {}).get("caption_word_count", 0)
                    for t in enriched_data.get("table_elements", [])
                )
                + sum(
                    p.get("enrichment_metadata", {}).get("caption_word_count", 0)
                    for p in enriched_data.get("extracted_pages", {}).values()
                ),
                "vlm_model": self.vlm_model,
                "caption_language": self.caption_language,
            }

            # Create sample outputs for debugging
            sample_tables = [
                {
                    "id": table["id"],
                    "page": table["structural_metadata"].get("page_number", 0),
                    "has_html_caption": bool(
                        table.get("enrichment_metadata", {}).get("table_html_caption")
                    ),
                    "has_image_caption": bool(
                        table.get("enrichment_metadata", {}).get("table_image_caption")
                    ),
                    "caption_words": table.get("enrichment_metadata", {}).get(
                        "caption_word_count", 0
                    ),
                }
                for table in enriched_data.get("table_elements", [])
                if "enrichment_metadata" in table
            ][:3]

            sample_images = [
                {
                    "page": page_info["structural_metadata"].get("page_number", 0),
                    "has_caption": bool(
                        page_info.get("enrichment_metadata", {}).get(
                            "full_page_image_caption"
                        )
                    ),
                    "caption_words": page_info.get("enrichment_metadata", {}).get(
                        "caption_word_count", 0
                    ),
                }
                for page_info in enriched_data.get("extracted_pages", {}).values()
                if "enrichment_metadata" in page_info
            ][:3]

            sample_outputs = {
                "sample_tables": sample_tables,
                "sample_images": sample_images,
            }

            return StepResult(
                step="enrichment",
                status="completed",
                duration_seconds=duration,
                summary_stats=summary_stats,
                sample_outputs=sample_outputs,
                # Return enriched data with same structure
                data=enriched_data,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Enrichment step failed: {e}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            return StepResult(
                step="enrichment",
                status="failed",
                duration_seconds=duration,
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

    async def validate_prerequisites_async(self, input_data: Any) -> bool:
        """Validate enrichment step prerequisites"""
        try:
            # Check if input_data contains metadata step results
            if not isinstance(input_data, dict):
                logger.error("Input data is not a dictionary")
                return False

            # Check for required keys from metadata step
            required_keys = [
                "text_elements",
                "table_elements",
                "extracted_pages",
                "page_sections",
            ]
            missing_keys = [key for key in required_keys if key not in input_data]

            if missing_keys:
                logger.error(
                    f"Missing required keys in metadata output: {missing_keys}"
                )
                return False

            # Check that elements have structural_metadata (added by metadata step)
            for element in input_data.get("text_elements", []):
                if "structural_metadata" not in element:
                    logger.error(
                        f"Text element missing structural_metadata: {element.get('id', 'unknown')}"
                    )
                    return False

            for element in input_data.get("table_elements", []):
                if "structural_metadata" not in element:
                    logger.error(
                        f"Table element missing structural_metadata: {element.get('id', 'unknown')}"
                    )
                    return False

            for page_info in input_data.get("extracted_pages", {}).values():
                if "structural_metadata" not in page_info:
                    logger.error("Extracted page missing structural_metadata")
                    return False

            logger.info("Prerequisites validated for enrichment step")
            return True

        except Exception as e:
            logger.error(f"Prerequisites validation failed: {e}")
            return False

    def estimate_duration(self, input_data: Any) -> int:
        """Estimate enrichment step duration in seconds"""
        try:
            # Estimate based on number of elements to process
            total_elements = len(input_data.get("table_elements", [])) + len(
                input_data.get("extracted_pages", {})
            )

            # Rough estimate: 10-15 seconds per element (VLM processing)
            estimated_seconds = total_elements * 12

            return max(estimated_seconds, 30)  # Minimum 30 seconds

        except Exception as e:
            logger.error(f"Duration estimation failed: {e}")
            return 300  # Default 5 minutes

    async def _enrich_with_vlm_async(
        self, metadata_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute VLM enrichment asynchronously"""

        logger.info("Starting VLM enrichment...")

        # Create a copy to avoid modifying original data
        enriched_data = metadata_output.copy()

        # Process tables
        table_elements = enriched_data.get("table_elements", [])
        logger.info(f"Processing {len(table_elements)} table elements...")

        for i, table_element in enumerate(table_elements):
            logger.info(f"Processing table {i+1}/{len(table_elements)}...")
            table_element["enrichment_metadata"] = await self._enrich_table(
                table_element
            )

        # Process full-page images
        extracted_pages = enriched_data.get("extracted_pages", {})
        logger.info(f"Processing {len(extracted_pages)} full-page images...")

        for page_num, page_info in extracted_pages.items():
            logger.info(f"Processing image page {page_num}...")
            page_info["enrichment_metadata"] = await self._enrich_full_page_image(
                page_info, enriched_data
            )

        logger.info("VLM enrichment complete!")
        return enriched_data

    async def _enrich_table(self, table_element: dict) -> dict:
        """Enrich table with VLM captions"""

        enrichment_metadata = {
            "vlm_model": self.vlm_model,
            "vlm_processed": True,
            "vlm_processing_timestamp": datetime.now().isoformat(),
            "vlm_processing_error": None,
            "table_html_caption": None,
            "table_image_caption": None,
            "table_image_filepath": None,
            "caption_word_count": 0,
            "processing_duration_seconds": None,
        }

        start_time = datetime.utcnow()

        try:
            # Get table HTML
            table_html = table_element.get("metadata", {}).get("text_as_html", "")
            if table_html and table_html.strip():
                logger.debug(f"Captioning table HTML ({len(table_html)} chars)...")
                enrichment_metadata["table_html_caption"] = (
                    await self.vlm_captioner.caption_table_html_async(
                        table_html, table_element["structural_metadata"]
                    )
                )
                logger.debug(
                    f"HTML caption generated ({len(enrichment_metadata['table_html_caption'])} chars)"
                )

            # Get table image (Supabase URL or local path)
            image_url_data = table_element.get("metadata", {}).get("image_url")

            # DEBUG: Log the extracted image URL
            logger.info(
                f"ENRICHMENT DEBUG: Table element ID: {table_element.get('id', 'unknown')}"
            )
            logger.info(f"ENRICHMENT DEBUG: Raw image_url_data: {image_url_data}")
            logger.info(
                f"ENRICHMENT DEBUG: Full metadata keys: {list(table_element.get('metadata', {}).keys())}"
            )

            # Extract the actual URL string
            image_url = extract_url_string(image_url_data)
            logger.info(f"ENRICHMENT DEBUG: Extracted image_url: {image_url}")

            if image_url:
                logger.debug(f"Captioning table image: {image_url}")
                enrichment_metadata["table_image_caption"] = (
                    await self.vlm_captioner.caption_table_image_async(
                        image_url, table_element["structural_metadata"]
                    )
                )
                enrichment_metadata["table_image_filepath"] = image_url
                logger.debug(
                    f"Image caption generated ({len(enrichment_metadata['table_image_caption'])} chars)"
                )
            else:
                logger.warning(
                    f"ENRICHMENT DEBUG: No valid image URL extracted from: {image_url_data}"
                )

            # Calculate caption statistics
            total_caption_length = 0
            if enrichment_metadata["table_html_caption"]:
                total_caption_length += len(
                    enrichment_metadata["table_html_caption"].split()
                )
            if enrichment_metadata["table_image_caption"]:
                total_caption_length += len(
                    enrichment_metadata["table_image_caption"].split()
                )

            enrichment_metadata["caption_word_count"] = total_caption_length

        except Exception as e:
            logger.error(f"Error processing table: {e}")
            enrichment_metadata["vlm_processing_error"] = str(e)
            enrichment_metadata["vlm_processed"] = False

        # Calculate processing duration
        enrichment_metadata["processing_duration_seconds"] = (
            datetime.utcnow() - start_time
        ).total_seconds()

        return enrichment_metadata

    async def _enrich_full_page_image(
        self, page_info: dict, metadata_output: dict
    ) -> dict:
        """Enrich full-page image with VLM caption"""

        enrichment_metadata = {
            "vlm_model": self.vlm_model,
            "vlm_processed": True,
            "vlm_processing_timestamp": datetime.now().isoformat(),
            "vlm_processing_error": None,
            "full_page_image_caption": None,
            "full_page_image_filepath": None,
            "page_text_context": None,
            "caption_word_count": 0,
            "processing_duration_seconds": None,
        }

        start_time = datetime.utcnow()

        try:
            # Get page text context
            page_num = page_info["structural_metadata"]["page_number"]
            page_text_context = self._get_page_text_context(page_num, metadata_output)
            enrichment_metadata["page_text_context"] = page_text_context

            # Use Supabase URL for image
            image_url_data = page_info.get("url")

            # DEBUG: Log the extracted image URL
            logger.info(f"ENRICHMENT DEBUG: Page {page_num}")
            logger.info(f"ENRICHMENT DEBUG: Raw image_url_data: {image_url_data}")
            logger.info(
                f"ENRICHMENT DEBUG: Full page_info keys: {list(page_info.keys())}"
            )

            # Extract the actual URL string
            image_url = extract_url_string(image_url_data)
            logger.info(f"ENRICHMENT DEBUG: Extracted image_url: {image_url}")

            if image_url:
                logger.debug(f"Captioning full-page image: {image_url}")
                enrichment_metadata["full_page_image_caption"] = (
                    await self.vlm_captioner.caption_full_page_image_async(
                        image_url, page_info["structural_metadata"], page_text_context
                    )
                )
                enrichment_metadata["full_page_image_filepath"] = image_url
                enrichment_metadata["caption_word_count"] = len(
                    enrichment_metadata["full_page_image_caption"].split()
                )
                logger.debug(
                    f"Full-page caption generated ({enrichment_metadata['caption_word_count']} words)"
                )
            else:
                logger.warning(
                    f"ENRICHMENT DEBUG: No valid image URL extracted for page {page_num} from: {image_url_data}"
                )

        except Exception as e:
            logger.error(f"Error processing full-page image: {e}")
            enrichment_metadata["vlm_processing_error"] = str(e)
            enrichment_metadata["vlm_processed"] = False

        # Calculate processing duration
        enrichment_metadata["processing_duration_seconds"] = (
            datetime.utcnow() - start_time
        ).total_seconds()

        return enrichment_metadata

    def _get_page_text_context(self, page_num: int, metadata_output: dict) -> str:
        """Extract text context from the same page for image captioning"""

        page_texts = []
        for text_element in metadata_output.get("text_elements", []):
            element_page = text_element["structural_metadata"].get("page_number", 0)

            if element_page == page_num:
                text = text_element.get("text", "").strip()
                if text:
                    page_texts.append(text)

        # Limit to avoid token limits
        return "\n".join(page_texts[: self.max_page_text_elements])
