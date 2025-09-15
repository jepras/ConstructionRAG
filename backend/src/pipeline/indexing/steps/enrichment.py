"""Production enrichment step for document processing pipeline."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage

# VLM Components
from langchain_openai import ChatOpenAI

from src.models import StepResult
from src.services.storage_service import StorageService
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError

# Pipeline components
from ...shared.base_step import PipelineStep
from ...shared.models import PipelineError

logger = logging.getLogger(__name__)


def extract_url_string(url_data: Any) -> str | None:
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

    # HTML table captioning removed - relying on image captions only

    async def caption_table_image_async(self, image_url: str, element_context: dict) -> dict:
        """Generate caption for table using extracted image"""

        page_num = element_context.get("page_number", "unknown")
        source_file = element_context.get("source_filename", "unknown")

        # Add optional bbox focus hint if available
        focus_hint = ""
        if bbox := element_context.get("bbox"):
            focus_hint = f"\n\nNote: The table is located at coordinates {bbox} on the page (x0, y0, x1, y1)."

        prompt = f"""You are analyzing a table image extracted from page {page_num} of a construction/technical document ({source_file}).{focus_hint}

Please provide a comprehensive description that captures ALL content on this section of the page:

1. **All Visible Text in Table**: Read and transcribe ALL text visible in the table, including headers, data, footnotes, cell contents.
2. **Table Structure**: Number of rows, columns, organization, table borders and layout
3. **Data Relationships**: How the data is organized and what it represents
4. **Surrounding Text**: Any text labels, captions, references, or annotations around the table
5. **Technical Details**: Any measurements, specifications, material references, or technical codes visible

Focus on being extremely thorough - capture every piece of text and technical information visible in this image, as this will be the only source of this content.

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
            response = self.vlm_client.invoke([message])
            return {
                "caption": response.content.strip(),
                "prompt": prompt,
                "prompt_template": "table_image_caption_v1",
            }
        except Exception as e:
            logger.error(f"    ❌ Error captioning table image: {e}")
            return {
                "caption": f"Error generating caption: {str(e)}",
                "prompt": prompt,
                "prompt_template": "table_image_caption_v1",
                "error": str(e),
            }

    async def caption_full_page_image_async(
        self, image_url: str, page_context: dict, page_text_context: str = ""
    ) -> dict:
        """Generate caption for full-page image with context"""

        page_num = page_context.get("page_number", "unknown")
        source_file = page_context.get("source_filename", "unknown")
        complexity = page_context.get("text_complexity", "unknown")

        # Build context-aware prompt
        context_section = ""
        if page_text_context.strip():
            context_section = f"""

**Text Context from this page:**
{page_text_context[:1500]}"""  # Configurable context limit

        prompt = f"""You are analyzing a full-page image from page {page_num} of a construction/technical document ({source_file}). This page has {complexity} visual complexity and contains visual content that requires comprehensive text extraction.

This image is the PRIMARY SOURCE for all text content on this page. Please provide an extremely detailed description that captures:

1. **ALL Text Content**: Extract and transcribe ALL visible text including:
   - Headers, titles, and section headings
   - Body text, paragraphs, and descriptions  
   - Table content, data, and headers
   - Labels, annotations, and callouts
   - Measurements, dimensions, and specifications
   - Material references and technical codes
   - Footnotes, legends, and captions

2. **Technical Drawing Details**: What type of drawing, elements shown, dimensions, materials, construction details

3. **Spatial Relationships**: How different parts relate, connect, or reference each other

4. **Visual Context**: How text relates to diagrams, what the visual elements represent

5. **Construction-Specific Information**: Building materials, techniques, standards, compliance codes

Read this page as if you are digitizing all text content - be extremely thorough as this VLM caption will replace any OCR text extraction.

{context_section}

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

            response = await self.vlm_client.ainvoke([message])

            return {
                "caption": response.content.strip(),
                "prompt": prompt,
                "prompt_template": "full_page_image_caption_v1",
            }
        except Exception as e:
            logger.error(f"Error captioning full page image: {e}")
            return {
                "caption": f"Error generating caption: {str(e)}",
                "prompt": prompt,
                "prompt_template": "full_page_image_caption_v1",
                "error": str(e),
            }


class EnrichmentStep(PipelineStep):
    """Production enrichment step implementing VLM captioning for tables and images"""

    def __init__(
        self,
        config: dict[str, Any],
        storage_client=None,
        progress_tracker=None,
        storage_service=None,
    ):
        super().__init__(config, progress_tracker)
        self.storage_client = storage_client
        self.storage_service = storage_service or StorageService()

        # Use config passed from orchestrator (no fresh ConfigService calls)
        # Get generation model from config, with fallback
        generation_config = config.get("generation", {})
        default_generation_model = generation_config.get("model", "google/gemini-2.5-flash-lite")
        
        self.vlm_model = config.get("vlm_model", default_generation_model)
        
        # Get language from config with fallback to English
        language = config.get("language", "english")
        # Map language to caption language
        language_mapping = {
            "english": "English", 
            "danish": "Danish"
        }
        self.caption_language = language_mapping.get(language, "English")
        self.max_text_context_length = config.get("max_text_context_length", 1500)
        self.max_page_text_elements = config.get("max_page_text_elements", 5)

        # Initialize VLM captioner
        from src.config.settings import get_settings

        settings = get_settings()
        api_key = settings.openrouter_api_key
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
            if hasattr(input_data, "sample_outputs") and hasattr(input_data, "step"):
                # Input is a StepResult from metadata step (unified processing)
                # Check data field first, then fall back to sample_outputs
                metadata_output = (
                    input_data.data
                    if hasattr(input_data, "data") and input_data.data
                    else input_data.sample_outputs.get("metadata_data", {})
                )
                logger.info(f"Processing metadata output from StepResult ({input_data.step})")
            elif hasattr(input_data, "data") and input_data.data is not None:
                # Input is a StepResult from metadata step (legacy)
                metadata_output = input_data.data
                logger.info("Processing metadata output from StepResult (legacy)")
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
                    [t for t in enriched_data.get("table_elements", []) if "enrichment_metadata" in t]
                ),
                "images_processed": len(
                    [p for p in enriched_data.get("extracted_pages", {}).values() if "enrichment_metadata" in p]
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
                    "has_vlm_caption": bool(table.get("enrichment_metadata", {}).get("table_image_caption")),
                    "has_image_caption": bool(table.get("enrichment_metadata", {}).get("table_image_caption")),
                    "caption_words": table.get("enrichment_metadata", {}).get("caption_word_count", 0),
                }
                for table in enriched_data.get("table_elements", [])
                if "enrichment_metadata" in table
            ][:3]

            sample_images = [
                {
                    "page": page_info["structural_metadata"].get("page_number", 0),
                    "has_caption": bool(page_info.get("enrichment_metadata", {}).get("full_page_image_caption")),
                    "caption_words": page_info.get("enrichment_metadata", {}).get("caption_word_count", 0),
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
            raise AppError(
                "Enrichment step failed",
                error_code=ErrorCode.EXTERNAL_API_ERROR,
                details={"reason": str(e)},
            ) from e

    async def validate_prerequisites_async(self, input_data: Any) -> bool:
        """Validate enrichment step prerequisites"""
        try:
            # Debug logging to see what we're receiving
            logger.info(f"🔍 EnrichmentStep validate_prerequisites_async received input_data type: {type(input_data)}")

            # Handle StepResult objects (from unified processing)
            if hasattr(input_data, "sample_outputs") and hasattr(input_data, "step"):
                # This is a StepResult from a previous step
                logger.info(f"EnrichmentStep received StepResult from {input_data.step}")

                # Extract metadata data from StepResult - check both data and sample_outputs
                metadata_data = (
                    input_data.data
                    if hasattr(input_data, "data") and input_data.data
                    else input_data.sample_outputs.get("metadata_data", {})
                )

                # Check for required keys from metadata step
                required_keys = [
                    "text_elements",
                    "table_elements",
                    "extracted_pages",
                    "page_sections",
                ]
                missing_keys = [key for key in required_keys if key not in metadata_data]

                if missing_keys:
                    logger.error(f"Missing required keys in metadata output: {missing_keys}")
                    return False

                # Check that elements have structural_metadata (added by metadata step)
                for element in metadata_data.get("text_elements", []):
                    if "structural_metadata" not in element:
                        logger.error(f"Text element missing structural_metadata: {element.get('id', 'unknown')}")
                        return False

                for element in metadata_data.get("table_elements", []):
                    if "structural_metadata" not in element:
                        logger.error(f"Table element missing structural_metadata: {element.get('id', 'unknown')}")
                        return False

                for page_info in metadata_data.get("extracted_pages", {}).values():
                    if "structural_metadata" not in page_info:
                        logger.error("Extracted page missing structural_metadata")
                        return False

                logger.info("Prerequisites validated for enrichment step (StepResult)")
                return True

            # Handle dict objects (legacy single PDF processing)
            elif isinstance(input_data, dict):
                # Check for required keys from metadata step
                required_keys = [
                    "text_elements",
                    "table_elements",
                    "extracted_pages",
                    "page_sections",
                ]
                missing_keys = [key for key in required_keys if key not in input_data]

                if missing_keys:
                    logger.error(f"Missing required keys in metadata output: {missing_keys}")
                    return False

                # Check that elements have structural_metadata (added by metadata step)
                for element in input_data.get("text_elements", []):
                    if "structural_metadata" not in element:
                        logger.error(f"Text element missing structural_metadata: {element.get('id', 'unknown')}")
                        return False

                for element in input_data.get("table_elements", []):
                    if "structural_metadata" not in element:
                        logger.error(f"Table element missing structural_metadata: {element.get('id', 'unknown')}")
                        return False

                for page_info in input_data.get("extracted_pages", {}).values():
                    if "structural_metadata" not in page_info:
                        logger.error("Extracted page missing structural_metadata")
                        return False

                logger.info("Prerequisites validated for enrichment step (dict)")
                return True

            # Unknown input type
            logger.error(f"Unknown input type for enrichment step: {type(input_data)}")
            return False

        except Exception as e:
            logger.error(f"Prerequisites validation failed: {e}")
            return False

    def estimate_duration(self, input_data: Any) -> int:
        """Estimate enrichment step duration in seconds"""
        try:
            # Estimate based on number of elements to process
            total_elements = len(input_data.get("table_elements", [])) + len(input_data.get("extracted_pages", {}))

            # Rough estimate: 10-15 seconds per element (VLM processing)
            estimated_seconds = total_elements * 12

            return max(estimated_seconds, 30)  # Minimum 30 seconds

        except Exception as e:
            logger.error(f"Duration estimation failed: {e}")
            return 300  # Default 5 minutes

    async def _enrich_with_vlm_async(self, metadata_output: dict[str, Any]) -> dict[str, Any]:
        """Execute VLM enrichment asynchronously"""

        logger.info("Starting VLM enrichment...")

        # Create a copy to avoid modifying original data
        enriched_data = metadata_output.copy()

        # Process tables (but skip VLM if full-page extraction exists for the same page)
        table_elements = enriched_data.get("table_elements", [])
        extracted_pages = enriched_data.get("extracted_pages", {})

        logger.info(f"Processing {len(table_elements)} table elements...")

        # Debug the data types to fix the comparison issue
        extracted_page_keys = list(extracted_pages.keys())

        # Separate tables that need VLM processing from those that don't
        tables_to_process = []
        tables_skipped = 0

        for i, table_element in enumerate(table_elements):
            table_page = table_element.get("page")
            table_id = table_element.get("id", f"table_{i}")

            # Fix data type comparison - try both int and str versions
            has_full_page = table_page in extracted_pages or str(table_page) in extracted_pages

            if has_full_page:
                if tables_skipped < 3:  # Only log first 3 skips in detail
                    logger.info(
                        f"Skipping VLM for table {i + 1}/{len(table_elements)} on page {table_page} - full-page extraction exists"
                    )
                tables_skipped += 1
                # Still add basic metadata but skip VLM processing
                table_element["enrichment_metadata"] = {
                    "vlm_processed": False,
                    "skip_reason": "full_page_extraction_exists",
                    "vlm_processing_timestamp": datetime.now().isoformat(),
                }
            else:
                tables_to_process.append(table_element)

        # Process tables in parallel batches
        if tables_to_process:
            logger.info(f"Processing {len(tables_to_process)} tables with VLM in parallel batches...")

            # Create tasks for parallel processing
            tasks = []
            for table_element in tables_to_process:
                tasks.append(self._enrich_table(table_element))

            # Process in batches of 5 to avoid overwhelming the API
            batch_size = 5
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i : i + batch_size]
                batch_end = min(i + batch_size, len(tasks))

                # Process batch in parallel
                batch_results = await asyncio.gather(*batch)

                # Update table elements with results
                for j, enrichment_metadata in enumerate(batch_results):
                    tables_to_process[i + j]["enrichment_metadata"] = enrichment_metadata

        tables_processed_with_vlm = len(tables_to_process)


        # Process full-page images
        extracted_pages = enriched_data.get("extracted_pages", {})
        logger.info(f"Processing {len(extracted_pages)} full-page images...")

        pages_processed = 0
        if extracted_pages:
            # Prepare tasks for parallel processing
            page_tasks = []
            page_nums = []

            for page_num, page_info in extracted_pages.items():
                complexity = page_info.get("complexity", "unknown")
                logger.info(f"Preparing page {page_num} (complexity: {complexity}) for VLM processing...")
                page_tasks.append(self._enrich_full_page_image(page_info, enriched_data))
                page_nums.append(page_num)

            # Process pages in parallel batches
            batch_size = 5
            for i in range(0, len(page_tasks), batch_size):
                batch = page_tasks[i : i + batch_size]
                batch_nums = page_nums[i : i + batch_size]
                batch_end = min(i + batch_size, len(page_tasks))

                logger.info(f"Processing pages {batch_nums} in parallel...")

                # Process batch in parallel
                batch_results = await asyncio.gather(*batch)

                # Update page_info with results
                for j, enrichment_metadata in enumerate(batch_results):
                    extracted_pages[batch_nums[j]]["enrichment_metadata"] = enrichment_metadata
                    pages_processed += 1

        logger.info("VLM enrichment complete!")
        return enriched_data

    async def _enrich_table(self, table_element: dict) -> dict:
        """Enrich table with VLM captions"""

        enrichment_metadata = {
            "vlm_model": self.vlm_model,
            "vlm_processed": True,
            "vlm_processing_timestamp": datetime.now().isoformat(),
            "vlm_processing_error": None,
            "table_image_caption": None,
            "table_image_filepath": None,
            "caption_word_count": 0,
            "processing_duration_seconds": None,
            "prompt_used": None,
            "prompt_template": None,
            "input_context": {
                "page_number": table_element["structural_metadata"].get("page_number", "unknown"),
                "source_filename": table_element["structural_metadata"].get("source_filename", "unknown"),
                "element_type": "table",
            },
        }

        start_time = datetime.utcnow()

        try:
            # Get table image (Supabase URL or local path) - VLM captions from images only
            image_url_data = table_element.get("metadata", {}).get("image_url")

            # Extract the actual URL string
            image_url = extract_url_string(image_url_data)

            if image_url:
                logger.debug(f"Captioning table image: {image_url}")
                # Use structural_metadata which already contains bbox from metadata step
                context = table_element["structural_metadata"].copy()
                # Bbox is already in structural_metadata, no need to add separately

                vlm_result = await self.vlm_captioner.caption_table_image_async(image_url, context)
                enrichment_metadata["table_image_caption"] = vlm_result["caption"]
                enrichment_metadata["prompt_used"] = vlm_result["prompt"]
                enrichment_metadata["prompt_template"] = vlm_result["prompt_template"]
                enrichment_metadata["table_image_filepath"] = image_url
                logger.debug(f"Image caption generated ({len(enrichment_metadata['table_image_caption'])} chars)")
            else:
                logger.warning(f"No valid image URL extracted from: {image_url_data}")

            # Calculate caption statistics
            if enrichment_metadata["table_image_caption"]:
                enrichment_metadata["caption_word_count"] = len(enrichment_metadata["table_image_caption"].split())
            else:
                enrichment_metadata["caption_word_count"] = 0

        except Exception as e:
            logger.error(f"Error processing table: {e}")
            enrichment_metadata["vlm_processing_error"] = str(e)
            enrichment_metadata["vlm_processed"] = False

        # Calculate processing duration
        enrichment_metadata["processing_duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()

        return enrichment_metadata

    async def _enrich_full_page_image(self, page_info: dict, metadata_output: dict) -> dict:
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
            "prompt_used": None,
            "prompt_template": None,
            "input_context": {
                "page_number": page_info["structural_metadata"].get("page_number", "unknown"),
                "source_filename": page_info["structural_metadata"].get("source_filename", "unknown"),
                "element_type": "image",
            },
        }

        start_time = datetime.utcnow()

        try:
            # Get page text context
            page_num = page_info["structural_metadata"]["page_number"]
            page_text_context = self._get_page_text_context(page_num, metadata_output)
            enrichment_metadata["page_text_context"] = page_text_context

            # Use Supabase URL for image
            image_url_data = page_info.get("url")

            # Extract the actual URL string
            image_url = extract_url_string(image_url_data)

            if image_url:
                logger.debug(f"Captioning full-page image: {image_url}")
                # Use structural_metadata which already contains full_page_bbox from metadata step
                context = page_info["structural_metadata"].copy()
                vlm_result = await self.vlm_captioner.caption_full_page_image_async(
                    image_url, context, page_text_context
                )
                enrichment_metadata["full_page_image_caption"] = vlm_result["caption"]
                enrichment_metadata["prompt_used"] = vlm_result["prompt"]
                enrichment_metadata["prompt_template"] = vlm_result["prompt_template"]
                enrichment_metadata["full_page_image_filepath"] = image_url
                enrichment_metadata["caption_word_count"] = len(enrichment_metadata["full_page_image_caption"].split())
                logger.debug(f"Full-page caption generated ({enrichment_metadata['caption_word_count']} words)")
            else:
                logger.warning(f"No valid image URL extracted for page {page_num} from: {image_url_data}")

        except Exception as e:
            logger.error(f"Error processing full-page image: {e}")
            enrichment_metadata["vlm_processing_error"] = str(e)
            enrichment_metadata["vlm_processed"] = False

        # Calculate processing duration
        enrichment_metadata["processing_duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()

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
