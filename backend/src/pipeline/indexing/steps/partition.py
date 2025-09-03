"""Production partition step for document processing pipeline."""

import re
import asyncio
import os
import tempfile
import shutil
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
from uuid import UUID, uuid4
import logging

# Initialize logger first
logger = logging.getLogger(__name__)

# PDF processing
import fitz  # PyMuPDF

try:
    from unstructured.partition.pdf import partition_pdf

    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False

# Storage
from src.services.storage_service import StorageService

# Pipeline components
from ...shared.base_step import PipelineStep
from src.models import StepResult
from ...shared.models import DocumentInput, PipelineError
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError


class PartitionStep(PipelineStep):
    """Production partition step implementing the unified partitioning pipeline"""

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
        self.ocr_strategy = config.get("ocr_strategy", "auto")
        self.extract_tables = config.get("extract_tables", True)
        self.extract_images = config.get("extract_images", True)
        self.max_image_size_mb = config.get("max_image_size_mb", 10)
        self.ocr_languages = config.get("ocr_languages", ["dan"])
        self.include_coordinates = config.get("include_coordinates", True)
        
        # Table validation configuration
        self.table_validation = config.get("table_validation", {})
        self.table_validation_enabled = self.table_validation.get("enabled", True)
        self.max_table_size = self.table_validation.get("max_table_size", 5000)
        self.max_columns = self.table_validation.get("max_columns", 20)
        self.max_cells = self.table_validation.get("max_cells", 100)
        self.repetition_threshold = self.table_validation.get("repetition_threshold", 0.7)
        self.min_confidence = self.table_validation.get("min_confidence", 0.3)
        self.reject_on_drawing_pages = self.table_validation.get("reject_on_drawing_pages", True)

        # Create temporary directories for processing
        self.temp_dir = Path(tempfile.mkdtemp(prefix="partition_"))
        self.tables_dir = self.temp_dir / "tables"
        self.images_dir = self.temp_dir / "images"

        # Create directories
        self.tables_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)

        logger.info(f"PartitionStep initialized with temp dir: {self.temp_dir}")

    def _detect_document_type(self, filepath: str) -> Dict[str, Any]:
        """Detect if document is scanned using fast PyMuPDF analysis"""
        try:
            doc = fitz.open(filepath)
            analysis = {
                "total_pages": len(doc),
                "has_selectable_text": False,
                "text_density": [],  # Text chars per page
                "avg_text_per_page": 0,
                "is_likely_scanned": False,
                "detection_confidence": 0.0,
                "sample_pages_analyzed": 0,
            }

            # Analyze sample pages (first 3 or all if fewer)
            sample_pages = min(3, len(doc))
            total_text_chars = 0

            for page_num in range(sample_pages):
                page = doc[page_num]
                try:
                    text = page.get_text().strip()
                    text_length = len(text)
                except Exception as e:
                    # Handle pages without text layers (e.g., pure CAD drawings)
                    logger.debug(f"Could not extract text from page {page_num + 1}: {e}")
                    text = ""
                    text_length = 0

                analysis["text_density"].append(text_length)
                total_text_chars += text_length

                if text_length > 0:
                    analysis["has_selectable_text"] = True

            doc.close()

            # Calculate averages
            analysis["sample_pages_analyzed"] = sample_pages
            analysis["avg_text_per_page"] = (
                total_text_chars / sample_pages if sample_pages > 0 else 0
            )

            # Detection logic based on our testing results
            # Threshold: < 25 chars per page suggests scanned document
            text_threshold = self.config.get("scanned_detection", {}).get(
                "text_threshold", 25
            )

            if analysis["avg_text_per_page"] < text_threshold:
                analysis["is_likely_scanned"] = True
                analysis["detection_confidence"] = max(
                    0.7, 1.0 - (analysis["avg_text_per_page"] / text_threshold)
                )
            else:
                analysis["is_likely_scanned"] = False
                analysis["detection_confidence"] = min(
                    0.9, analysis["avg_text_per_page"] / (text_threshold * 10)
                )

            logger.info(
                f"Document analysis: {analysis['avg_text_per_page']:.1f} chars/page, "
                f"scanned: {analysis['is_likely_scanned']} "
                f"(confidence: {analysis['detection_confidence']:.2f})"
            )
            print(
                f"📊 Document analysis: {analysis['avg_text_per_page']:.1f} chars/page, "
                f"scanned: {analysis['is_likely_scanned']} "
                f"(confidence: {analysis['detection_confidence']:.2f})"
            )

            return analysis

        except Exception as e:
            logger.error(f"Document detection failed: {e}")
            # Fallback to regular processing
            return {
                "total_pages": 0,
                "has_selectable_text": True,  # Assume not scanned if detection fails
                "is_likely_scanned": False,
                "detection_confidence": 0.0,
                "error": str(e),
            }

    async def _process_with_unstructured(
        self, filepath: str, document_input: DocumentInput
    ) -> Dict[str, Any]:
        """Process document using Unstructured hi-res strategy for scanned documents"""
        if not UNSTRUCTURED_AVAILABLE:
            raise PipelineError(
                "Unstructured library not available for scanned document processing"
            )

        try:
            logger.info(
                "Processing with Hybrid strategy: Unstructured OCR + PyMuPDF images"
            )
            print(
                "🔄 Processing with Hybrid strategy: Unstructured OCR + PyMuPDF images"
            )

            # Run Unstructured processing in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            elements = await loop.run_in_executor(
                None, self._run_unstructured_sync, filepath
            )

            # Normalize output to current format
            normalized_result = await self._normalize_unstructured_output(
                elements, filepath, document_input
            )

            return normalized_result

        except Exception as e:
            logger.error(f"Unstructured processing failed: {e}")
            raise PipelineError(f"Unstructured processing failed: {str(e)}")

    def _run_unstructured_sync(self, filepath: str):
        """Run Unstructured processing synchronously (for thread pool execution)"""
        return partition_pdf(
            filename=filepath,
            strategy="hi_res",
            infer_table_structure=True,
            languages=self.ocr_languages,
            include_page_breaks=True,
            # coordinates removed - included automatically with hi_res strategy
        )

    async def _normalize_unstructured_output(
        self, elements, filepath: str, document_input: DocumentInput
    ) -> Dict[str, Any]:
        """Normalize Unstructured output to match current PyMuPDF format exactly"""
        try:
            # Initialize result structure to match current format
            result = {
                "text_elements": [],
                "table_elements": [],
                "extracted_pages": {},
                "page_analysis": {},
                "document_metadata": {},
                "metadata": {
                    "processing_strategy": "unstructured_hi_res",
                    "timestamp": datetime.now().isoformat(),
                    "source_file": document_input.filename if document_input else os.path.basename(filepath),
                },
            }

            # Process each element from Unstructured OCR
            for element in elements:
                # Create normalized element matching current schema
                # Handle None page numbers from Unstructured by assigning to page 1
                page_number = getattr(element.metadata, "page_number", None)
                if page_number is None:
                    page_number = 1  # Default to page 1 if Unstructured doesn't provide page number

                # Extract bbox if available from Unstructured
                bbox = None
                if hasattr(element.metadata, 'coordinates') and element.metadata.coordinates:
                    points = element.metadata.coordinates.points
                    if points and len(points) == 4:
                        # Get raw pixel coordinates
                        pixel_bbox = [points[0][0], points[0][1], points[2][0], points[2][1]]
                        print(f"[UNSTRUCTURED BBOX] Page {page_number}, Element {element.category}")
                        print(f"  Original pixel coordinates: {pixel_bbox}")
                        
                        # Try to get coordinate system dimensions
                        conversion_method = "unknown"
                        if hasattr(element.metadata.coordinates, 'system'):
                            system = element.metadata.coordinates.system
                            if hasattr(system, 'width') and hasattr(system, 'height'):
                                image_width = system.width
                                image_height = system.height
                                print(f"  Image dimensions: {image_width}x{image_height} pixels")
                                
                                # Get PDF page dimensions in points
                                doc = fitz.open(filepath)
                                page = doc[page_number - 1] if page_number > 0 else doc[0]
                                pdf_width = page.rect.width  # in points
                                pdf_height = page.rect.height  # in points
                                doc.close()
                                print(f"  PDF dimensions: {pdf_width}x{pdf_height} points")
                                
                                # Calculate scale factors
                                scale_x = pdf_width / image_width
                                scale_y = pdf_height / image_height
                                print(f"  Scale factors: x={scale_x:.4f}, y={scale_y:.4f}")
                                
                                # Convert pixels to PDF points
                                bbox = [
                                    pixel_bbox[0] * scale_x,
                                    pixel_bbox[1] * scale_y,
                                    pixel_bbox[2] * scale_x,
                                    pixel_bbox[3] * scale_y
                                ]
                                conversion_method = "coordinate_system_scaling"
                            else:
                                # System exists but no dimensions - use DPI fallback
                                print(f"  Coordinate system found but no dimensions available")
                                DPI_SCALE = 72.0 / 200.0  # Assume 200 DPI
                                bbox = [coord * DPI_SCALE for coord in pixel_bbox]
                                conversion_method = "dpi_fallback_200"
                                print(f"  Using DPI fallback: 200 DPI (scale={DPI_SCALE:.4f})")
                        else:
                            # No system info at all - use DPI assumption
                            print(f"  No coordinate system info available")
                            DPI_SCALE = 72.0 / 200.0  # Assume 200 DPI
                            bbox = [coord * DPI_SCALE for coord in pixel_bbox]
                            conversion_method = "dpi_fallback_200_no_system"
                            print(f"  Using DPI fallback: 200 DPI (scale={DPI_SCALE:.4f})")
                        
                        print(f"  Converted PDF coordinates: {bbox}")
                        print(f"  Conversion method: {conversion_method}")

                normalized_element = {
                    "id": getattr(element, "id", None)
                    or f"element_{len(result['text_elements']) + len(result['table_elements'])}",
                    "category": element.category,
                    "page": page_number,
                    "text": str(element),
                    "metadata": {
                        "page_number": page_number,
                        "filename": document_input.filename if document_input else getattr(element.metadata, "filename", None),
                        "extraction_method": "unstructured_ocr",
                        "bbox": bbox,  # Include bounding box coordinates
                    },
                }

                # Skip HTML metadata - we'll rely on VLM captions only

                # Categorize elements like current system
                if element.category in ["Table"]:
                    result["table_elements"].append(normalized_element)
                else:
                    result["text_elements"].append(normalized_element)

            # Step 2: Use PyMuPDF for image detection and full page extraction
            await self._extract_full_pages_with_pymupdf(
                filepath, result, document_input
            )

            # Step 3: Process table images if Unstructured detected any tables
            if result["table_elements"]:
                await self._process_table_images_from_unstructured(
                    filepath, result, document_input
                )

            # Step 3: Add document metadata
            doc = fitz.open(filepath)
            metadata = doc.metadata
            result["document_metadata"] = {
                "total_pages": len(doc),
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "creation_date": metadata.get("creationDate", ""),
            }
            doc.close()

            # Step 4: Add processing metadata
            result["metadata"].update(
                {
                    "text_count": len(result["text_elements"]),
                    "table_count": len(result["table_elements"]),
                    "pages_with_full_extraction": len(result["extracted_pages"]),
                    "ocr_text_elements": len(
                        [
                            e
                            for e in result["text_elements"]
                            if e.get("metadata", {}).get("extraction_method")
                            == "unstructured_ocr"
                        ]
                    ),
                }
            )

            logger.info(
                f"Hybrid processing complete: {len(result['text_elements'])} text (OCR), "
                f"{len(result['table_elements'])} tables, "
                f"{len(result['extracted_pages'])} full pages"
            )
            print(
                f"✅ Hybrid processing complete: {len(result['text_elements'])} text (OCR), "
                f"{len(result['table_elements'])} tables, "
                f"{len(result['extracted_pages'])} full pages"
            )

            return result

        except Exception as e:
            logger.error(f"Output normalization failed: {e}")
            raise PipelineError(f"Output normalization failed: {str(e)}")

    async def _extract_full_pages_with_pymupdf(
        self, filepath: str, result: Dict[str, Any], document_input: DocumentInput
    ):
        """Extract full pages using PyMuPDF when images are detected"""
        try:
            doc = fitz.open(filepath)

            # Analyze which pages have images/tables and need full extraction
            pages_to_extract = set()

            # Check for images on each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                images = page.get_images()

                if len(images) > 0:
                    pages_to_extract.add(page_num + 1)  # 1-indexed

            # Extract full pages
            for page_num in pages_to_extract:
                try:
                    page = doc[page_num - 1]  # Convert to 0-indexed
                    images = page.get_images()

                    # Determine DPI based on image count
                    if len(images) > 10:
                        matrix = fitz.Matrix(3, 3)  # High DPI for many images
                    elif len(images) > 3:
                        matrix = fitz.Matrix(2, 2)  # Standard DPI
                    else:
                        matrix = fitz.Matrix(1.5, 1.5)  # Lower DPI for few images

                    pixmap = page.get_pixmap(matrix=matrix)

                    # Save pixmap to temporary file
                    temp_filename = (
                        f"unstructured_page_{page_num}_{uuid4().hex[:8]}.png"
                    )
                    temp_image_path = self.images_dir / temp_filename
                    pixmap.save(str(temp_image_path))

                    # Upload to storage
                    upload_result = (
                        await self.storage_service.upload_extracted_page_image(
                            image_path=str(temp_image_path),
                            document_id=document_input.document_id,
                            page_num=page_num,
                            complexity="moderate",  # Default for Unstructured pages
                            upload_type=document_input.upload_type,
                            user_id=document_input.user_id,
                            project_id=document_input.project_id,
                            index_run_id=document_input.run_id,
                        )
                    )

                    result["extracted_pages"][page_num] = {
                        "url": upload_result["url"],
                        "storage_path": upload_result["storage_path"],
                        "filename": upload_result["filename"],
                        "complexity": "moderate",
                        "width": pixmap.width,
                        "height": pixmap.height,
                        "dpi": int(matrix.a * 72),
                        "original_image_count": len(images),
                        "image_type": "extracted_page",
                    }

                    logger.info(
                        f"Extracted full page {page_num} with {len(images)} images"
                    )

                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num}: {e}")

            doc.close()

        except Exception as e:
            logger.warning(f"Full page extraction failed: {e}")

    async def _process_table_images_from_unstructured(
        self, filepath: str, result: Dict[str, Any], document_input: DocumentInput
    ):
        """Process table images detected by Unstructured using PyMuPDF extraction"""
        try:
            logger.info(
                f"Processing {len(result['table_elements'])} table images from Unstructured"
            )

            doc = fitz.open(filepath)

            for i, table_element in enumerate(result["table_elements"]):
                try:
                    page_num = table_element.get("page", 1)
                    table_id = table_element.get("id", f"table_{i+1}")

                    # Get the page
                    page = doc[page_num - 1]  # Convert to 0-indexed

                    # For Unstructured tables, we need to extract the table area
                    # Since Unstructured doesn't provide coordinates, we'll extract the full page
                    # and let the enrichment step handle table detection

                    # Extract full page as table image (simplified approach)
                    matrix = fitz.Matrix(2, 2)  # Standard DPI for tables
                    pixmap = page.get_pixmap(matrix=matrix)

                    # Save table image
                    temp_filename = (
                        f"unstructured_table_{table_id}_{uuid4().hex[:8]}.png"
                    )
                    temp_image_path = self.images_dir / temp_filename
                    pixmap.save(str(temp_image_path))

                    # Upload to storage
                    upload_result = await self.storage_service.upload_table_image(
                        image_path=str(temp_image_path),
                        document_id=document_input.document_id,
                        table_id=table_id,
                        upload_type=document_input.upload_type,
                        user_id=document_input.user_id,
                        project_id=document_input.project_id,
                        index_run_id=document_input.run_id,
                    )

                    # Add image URL to table metadata
                    table_element["metadata"]["image_url"] = upload_result["url"]
                    table_element["metadata"]["image_storage_path"] = upload_result[
                        "storage_path"
                    ]
                    table_element["metadata"]["image_path"] = str(temp_image_path)

                    logger.info(f"Uploaded table {table_id}: {upload_result['url']}")

                except Exception as e:
                    logger.warning(f"Failed to process table {i+1}: {e}")

            doc.close()

        except Exception as e:
            logger.warning(f"Table image processing failed: {e}")

    async def _get_local_file_path(self, file_path_or_url: str) -> str:
        """Get a local file path, downloading from URL if necessary"""
        if file_path_or_url.startswith(("http://", "https://")):
            # Download from URL
            logger.info(f"Downloading file from URL: {file_path_or_url}")
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_file_path = temp_file.name
            temp_file.close()

            try:
                response = requests.get(file_path_or_url, timeout=30)
                response.raise_for_status()

                with open(temp_file_path, "wb") as f:
                    f.write(response.content)

                logger.info(f"Downloaded file to: {temp_file_path}")
                return temp_file_path
            except Exception as e:
                # Clean up on error
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                raise PipelineError(f"Failed to download file from URL: {str(e)}")
        else:
            # Already a local file path
            return file_path_or_url

    async def execute(self, input_data: Any) -> StepResult:
        """Execute the partition step with async operations"""
        start_time = datetime.utcnow()
        downloaded_file_path = None

        try:
            # Handle StepResult objects (from unified processing)
            if hasattr(input_data, "sample_outputs") and hasattr(input_data, "step"):
                # This is a StepResult from a previous step - pass it through
                logger.info(
                    f"PartitionStep received StepResult from {input_data.step}, passing through"
                )
                return input_data

            # Handle DocumentInput objects (single PDF processing)
            if hasattr(input_data, "filename") and hasattr(input_data, "file_path"):
                logger.info(
                    f"Starting partition step for document: {input_data.filename}"
                )

                # Validate input
                if not await self.validate_prerequisites_async(input_data):
                    raise PipelineError("Prerequisites not met for partition step")

                # Handle URL or file path
                file_path = await self._get_local_file_path(input_data.file_path)

                # Track if we downloaded a file
                if file_path != input_data.file_path:
                    downloaded_file_path = file_path

                # Execute HYBRID partitioning pipeline
                partition_result = await self._partition_document_hybrid(
                    file_path, input_data
                )
            else:
                raise PipelineError(
                    f"Unknown input type for partition step: {type(input_data)}"
                )

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Calculate drawing statistics from page_analysis
            page_analysis = partition_result.get("page_analysis", {})
            total_drawing_items = sum(
                page_data.get("drawing_items", 0) 
                for page_data in page_analysis.values()
            )
            pages_with_vector_drawings = sum(
                1 for page_data in page_analysis.values()
                if page_data.get("has_vector_drawings", False)
            )
            pages_with_any_drawings = sum(
                1 for page_data in page_analysis.values()
                if page_data.get("drawing_items", 0) > 0
            )
            
            # Create summary statistics
            summary_stats = {
                "text_elements": len(partition_result.get("text_elements", [])),
                "table_elements": len(partition_result.get("table_elements", [])),
                "extracted_pages": len(partition_result.get("extracted_pages", {})),
                "pages_analyzed": len(partition_result.get("page_analysis", {})),
                "processing_strategy": partition_result.get("metadata", {}).get(
                    "processing_strategy", "unknown"
                ),
                "original_raw_count": partition_result.get("metadata", {}).get(
                    "original_raw_count", 0
                ),
                "original_image_count": partition_result.get("metadata", {}).get(
                    "original_image_count", 0
                ),
                "total_drawing_items": total_drawing_items,
                "pages_with_vector_drawings": pages_with_vector_drawings,
                "pages_with_any_drawings": pages_with_any_drawings,
                "document_metadata": {
                    "total_pages": partition_result.get("document_metadata", {}).get(
                        "total_pages", 0
                    ),
                    "has_title": bool(
                        partition_result.get("document_metadata", {}).get("title", "")
                    ),
                },
                "tables_with_vlm_ready": len(partition_result.get("table_elements", [])),
            }

            # Create sample outputs for debugging (keep for backward compatibility)
            sample_outputs = {
                "sample_text_elements": [
                    {
                        "id": elem.get("id"),
                        "category": elem.get("category"),
                        "page": elem.get("page"),
                        "text_preview": (
                            elem.get("text", "")[:200] + "..."
                            if len(elem.get("text", "")) > 200
                            else elem.get("text", "")
                        ),
                    }
                    for elem in partition_result.get("text_elements", [])[:3]
                ],
                "sample_tables": [
                    {
                        "category": elem.get("category", "Unknown"),
                        "text_preview": (
                            elem.get("text", "")[:200] + "..."
                            if len(elem.get("text", "")) > 200
                            else elem.get("text", "")
                        ),
                        "has_image": bool(
                            elem.get("metadata", {}).get("image_url", "")
                        ),
                    }
                    for elem in partition_result.get("table_elements", [])[:2]
                ],
                "document_metadata": partition_result.get("document_metadata", {}),
            }

            # Return real data structure for downstream processing
            return StepResult(
                step="partition",
                status="completed",
                duration_seconds=duration,
                summary_stats=summary_stats,
                sample_outputs=sample_outputs,
                # Add real data for downstream steps
                data={
                    "text_elements": partition_result.get("text_elements", []),
                    "table_elements": partition_result.get("table_elements", []),
                    "extracted_pages": partition_result.get("extracted_pages", {}),
                    "page_analysis": partition_result.get("page_analysis", {}),
                    "document_metadata": partition_result.get(
                        "document_metadata", {}
                    ),  # Add document metadata
                    "metadata": partition_result.get("metadata", {}),
                },
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

        except Exception as e:
            doc_id = getattr(input_data, 'document_id', 'unknown') if input_data else 'unknown'
            logger.error(f"Partition step failed for document {doc_id}: {e}")
            raise AppError(
                f"Partition step failed for document {doc_id}",
                error_code=ErrorCode.INTERNAL_ERROR,
                details={"reason": str(e), "document_id": doc_id},
            ) from e
        finally:
            # Clean up downloaded temporary files
            if downloaded_file_path and os.path.exists(downloaded_file_path):
                try:
                    os.unlink(downloaded_file_path)
                    logger.info(
                        f"Cleaned up downloaded temp file: {downloaded_file_path}"
                    )
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up downloaded file: {cleanup_error}")

    async def validate_prerequisites_async(self, input_data: Any) -> bool:
        """Validate partition step prerequisites"""
        try:
            # Handle StepResult objects (from unified processing)
            if hasattr(input_data, "sample_outputs") and hasattr(input_data, "step"):
                # This is a StepResult from a previous step
                logger.info(f"PartitionStep received StepResult from {input_data.step}")
                return True

            # Handle DocumentInput objects (single PDF processing)
            if hasattr(input_data, "filename") and hasattr(input_data, "file_path"):
                # Check if file is a PDF
                if not input_data.filename.lower().endswith(".pdf"):
                    logger.error(f"File is not a PDF: {input_data.filename}")
                    return False

                # Handle URLs vs local files
                if input_data.file_path.startswith(("http://", "https://")):
                    # For URLs, we'll validate by attempting a HEAD request
                    try:
                        response = requests.head(input_data.file_path, timeout=10)
                        if response.status_code != 200:
                            logger.error(
                                f"URL not accessible: {input_data.file_path} (status: {response.status_code})"
                            )
                            return False

                        # Check content type
                        content_type = response.headers.get("content-type", "")
                        if "pdf" not in content_type.lower():
                            logger.error(f"URL does not point to a PDF: {content_type}")
                            return False

                        # Check file size from headers (if available)
                        content_length = response.headers.get("content-length")
                        if content_length:
                            file_size_mb = int(content_length) / (1024 * 1024)
                            if file_size_mb > 100:  # 100MB limit
                                logger.error(f"File too large: {file_size_mb:.2f}MB")
                                return False

                        logger.info(
                            f"URL prerequisites validated for: {input_data.filename}"
                        )
                        return True

                    except Exception as e:
                        logger.error(f"URL validation failed: {e}")
                        return False
                else:
                    # Local file validation
                    if not os.path.exists(input_data.file_path):
                        logger.error(f"File not found: {input_data.file_path}")
                        return False

                    # Check file size
                    file_size_mb = os.path.getsize(input_data.file_path) / (1024 * 1024)
                    if file_size_mb > 100:  # 100MB limit
                        logger.error(f"File too large: {file_size_mb:.2f}MB")
                        return False

                    logger.info(
                        f"Local file prerequisites validated for: {input_data.filename}"
                    )
                    return True

            # Unknown input type
            logger.error(f"Unknown input type for partition step: {type(input_data)}")
            return False

        except Exception as e:
            logger.error(f"Prerequisites validation failed: {e}")
            return False

    def estimate_duration(self, input_data: DocumentInput) -> int:
        """Estimate partition step duration in seconds"""
        try:
            file_size_mb = os.path.getsize(input_data.file_path) / (1024 * 1024)
            # Estimate: 10 seconds per MB for complex processing
            return int(file_size_mb * 10)
        except:
            return 60  # Default 1 minute

    async def _partition_document_hybrid(
        self, filepath: str, document_input: DocumentInput
    ) -> Dict[str, Any]:
        """Execute hybrid partitioning: detect document type and choose optimal strategy"""
        try:
            # Check if we have an explicit OCR strategy configured
            if self.ocr_strategy != "auto":
                # Use the explicitly configured strategy
                logger.info(f"Using explicitly configured OCR strategy: {self.ocr_strategy}")
                print(f"🎯 Using explicitly configured OCR strategy: {self.ocr_strategy}")
                
                if self.ocr_strategy == "hybrid_ocr_images":
                    if UNSTRUCTURED_AVAILABLE:
                        try:
                            result = await self._process_with_unstructured(filepath, document_input)
                            result["metadata"]["processing_strategy"] = "hybrid_ocr_images"
                            result["metadata"]["forced_strategy"] = True
                            return result
                        except Exception as e:
                            logger.warning(f"Hybrid processing failed: {e} - falling back to PyMuPDF only")
                            # Fall through to PyMuPDF processing
                    else:
                        logger.warning("hybrid_ocr_images strategy requested but Unstructured not available - falling back to PyMuPDF")
                        
                elif self.ocr_strategy == "pymupdf_only":
                    result = await self._partition_document_async(filepath, document_input)
                    result["metadata"]["processing_strategy"] = "pymupdf_only"
                    result["metadata"]["forced_strategy"] = True
                    return result
                    
                # If unknown strategy or fallback needed, continue to auto-detection
            
            # Step 1: Detect document type (for auto mode or fallback)
            doc_analysis = self._detect_document_type(filepath)

            # Step 2: Choose processing strategy based on detection
            if doc_analysis["is_likely_scanned"] and UNSTRUCTURED_AVAILABLE:
                logger.info(
                    f"Document detected as SCANNED (confidence: {doc_analysis['detection_confidence']:.2f}) - using Hybrid: Unstructured OCR + PyMuPDF images"
                )
                print(
                    f"🎯 Document detected as SCANNED (confidence: {doc_analysis['detection_confidence']:.2f}) - using Hybrid: Unstructured OCR + PyMuPDF images"
                )
                try:
                    result = await self._process_with_unstructured(
                        filepath, document_input
                    )
                    result["metadata"]["hybrid_detection"] = doc_analysis
                    result["metadata"]["processing_strategy"] = "hybrid_ocr_images"
                    return result
                except Exception as e:
                    logger.warning(
                        f"Hybrid processing failed: {e} - falling back to PyMuPDF only"
                    )
                    # Fall through to PyMuPDF processing

            # Step 3: Use PyMuPDF for regular documents or as fallback
            if doc_analysis["is_likely_scanned"]:
                logger.warning(
                    "Scanned document detected but using PyMuPDF only (Unstructured unavailable or failed)"
                )
            else:
                logger.info(
                    f"Document detected as REGULAR (confidence: {doc_analysis['detection_confidence']:.2f}) - using PyMuPDF only"
                )
                print(
                    f"🎯 Document detected as REGULAR (confidence: {doc_analysis['detection_confidence']:.2f}) - using PyMuPDF only"
                )

            result = await self._partition_document_async(filepath, document_input)

            # Add hybrid detection info to metadata
            result["metadata"]["hybrid_detection"] = doc_analysis
            result["metadata"]["processing_strategy"] = (
                "pymupdf_only"
                if not doc_analysis["is_likely_scanned"]
                else "pymupdf_fallback"
            )

            return result

        except Exception as e:
            doc_id = getattr(document_input, 'document_id', 'unknown')
            logger.error(f"Hybrid partitioning failed for document {doc_id}: {e}")
            raise PipelineError(f"Hybrid partitioning failed for document {doc_id}: {str(e)}")

    async def _partition_document_async(
        self, filepath: str, document_input: DocumentInput
    ) -> Dict[str, Any]:
        """Execute the unified partitioning pipeline asynchronously"""

        # Run the CPU-intensive partitioning in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self._partition_document_sync, filepath
        )

        # Post-process with async image uploads
        cleaned_result = await self._post_process_results_async(
            text_elements=result["text_elements"],
            raw_elements=result["raw_elements"],
            enhanced_tables=result["enhanced_tables"],
            extracted_pages=result["extracted_pages"],
            stage1_results=result["stage1_results"],
            filepath=filepath,
            document_input=document_input,
        )

        return cleaned_result

    def _partition_document_sync(self, filepath: str) -> Dict[str, Any]:
        """Synchronous partitioning implementation (runs in thread pool)"""

        logger.info(f"Processing PDF: {os.path.basename(filepath)}")

        # Initialize partitioner
        # Pass table validation config to partitioner
        table_validation_config = self.config.get("table_validation", {})
        partitioner = UnifiedPartitionerV2(str(self.tables_dir), str(self.images_dir), table_validation_config)

        # Stage 1: PyMuPDF analysis
        stage1_results = partitioner.stage1_pymupdf_analysis(filepath)

        # Stage 2: Fast text extraction
        text_elements, raw_elements = partitioner.stage2_fast_text_extraction(filepath)

        # Add comprehensive analysis logging for Beam
        total_images = sum(analysis.get("image_count", 0) for analysis in stage1_results["page_analysis"].values())
        meaningful_images = sum(analysis.get("meaningful_images", 0) for analysis in stage1_results["page_analysis"].values())
        pages_needing_extraction = sum(1 for analysis in stage1_results["page_analysis"].values() if analysis.get("needs_extraction", False))
        
        print(f"📊 DOCUMENT ANALYSIS COMPLETE")
        print(f"   📄 Total pages: {stage1_results['document_metadata'].get('total_pages', 0)}")
        print(f"   🖼️  Total images detected: {total_images}")
        print(f"   ✅ Meaningful images: {meaningful_images}")
        print(f"   📋 Tables detected: {len(stage1_results['table_locations'])}")
        print(f"   📄 Pages needing extraction: {pages_needing_extraction}")

        # Stage 3: Full page extraction (ALWAYS FIRST - no conditions)
        extracted_pages = []
        if self.extract_images:
            print(f"📄 FULL PAGE EXTRACTION")
            extracted_pages = partitioner.stage4_full_page_extraction(
                filepath, stage1_results["page_analysis"]
            )
            for page_num, page_info in extracted_pages.items():
                print(f"   ✅ Page {page_num}: {page_info['complexity']} → Full page extracted")
            print(f"📄 Full page extraction complete: {len(extracted_pages)} pages")
        else:
            print(f"📄 Full page extraction: DISABLED")

        # Stage 4: Table metadata processing (ALWAYS metadata only - no individual images)
        enhanced_tables = []
        if self.extract_tables:
            print(f"📋 TABLE METADATA PROCESSING (No individual images)")
            print(f"   📋 Tables to process: {len(stage1_results['table_locations'])}")
            
            enhanced_tables = partitioner.stage3_create_table_elements_only(
                filepath, stage1_results["table_locations"]
            )
            
            for table_info in stage1_results["table_locations"]:
                print(f"   ✅ Table on page {table_info['page']}: Metadata only (covered by full page)")
            print(f"📋 Table metadata complete: {len(enhanced_tables)} elements")
        else:
            print(f"📋 Table processing: DISABLED")

        # Return all raw results for async post-processing
        return {
            "text_elements": text_elements,
            "raw_elements": raw_elements,
            "enhanced_tables": enhanced_tables,
            "extracted_pages": extracted_pages,
            "stage1_results": stage1_results,
        }

    async def _post_process_results_async(
        self,
        text_elements,
        raw_elements,
        enhanced_tables,
        extracted_pages,
        stage1_results,
        filepath,
        document_input,
    ):
        """Post-process results with async image uploads to Supabase Storage"""
        try:
            # 1. Filter and clean text elements
            filtered_text_elements = self._filter_text_elements(text_elements)

            # 2. Clean page analysis data
            cleaned_page_analysis = self._clean_page_analysis(
                stage1_results.get("page_analysis", {})
            )

            # 3. Clean table metadata
            for table in enhanced_tables:
                table["metadata"] = self._clean_metadata(table.get("metadata", {}))

            # 4. Upload extracted page images to Supabase Storage
            uploaded_pages = {}

            if extracted_pages:
                logger.info(
                    f"Uploading {len(extracted_pages)} extracted page images to Supabase Storage..."
                )

                for page_num, page_info in extracted_pages.items():
                    try:
                        # Upload image to Supabase Storage with new structure
                        upload_result = (
                            await self.storage_service.upload_extracted_page_image(
                                image_path=page_info["filepath"],
                                document_id=document_input.document_id,
                                page_num=page_num,
                                complexity=page_info["complexity"],
                                upload_type=document_input.upload_type,
                                user_id=document_input.user_id,
                                project_id=document_input.project_id,
                                index_run_id=document_input.run_id,
                            )
                        )

                        # Update page info with Supabase URL
                        uploaded_pages[page_num] = {
                            "url": upload_result["url"],
                            "storage_path": upload_result["storage_path"],
                            "filename": upload_result["filename"],
                            "complexity": upload_result["complexity"],
                            "width": page_info["width"],
                            "height": page_info["height"],
                            "dpi": page_info["dpi"],
                            "original_image_count": page_info["original_image_count"],
                            "original_table_count": page_info["original_table_count"],
                            "image_type": "extracted_page",
                        }

                        logger.info(f"Uploaded page {page_num}: {upload_result['url']}")

                    except Exception as e:
                        logger.error(f"Failed to upload page {page_num}: {e}")
                        # Keep local file info as fallback
                        uploaded_pages[page_num] = page_info

            # 5. SKIP table image upload - Full-page-only approach
            if enhanced_tables:
                print(f"📋 BEAM: Table metadata preserved for {len(enhanced_tables)} tables")
                logger.info(f"Table metadata preserved for {len(enhanced_tables)} tables - no individual images uploaded (full-page approach)")
                print(f"📋 BEAM: Table images BLOCKED - content will be captured in full-page extractions")
                
                # Clear any individual table image paths to prevent confusion
                cleared_count = 0
                for table_element in enhanced_tables:
                    if table_element["metadata"].pop("image_path", None):
                        cleared_count += 1
                
                print(f"📋 BEAM: Cleared individual image paths from {cleared_count}/{len(enhanced_tables)} tables")

            # 6. Prepare metadata
            metadata = {
                "processing_strategy": "pymupdf_only",
                "timestamp": datetime.now().isoformat(),
                "source_file": document_input.filename if document_input else os.path.basename(filepath),
                "text_count": len(filtered_text_elements),
                "enhanced_tables": len(enhanced_tables),
                "extracted_pages": len(extracted_pages),
                "pages_analyzed": len(cleaned_page_analysis),
                "original_raw_count": len(raw_elements),  # Keep for reference
                "original_image_count": len(
                    stage1_results["image_locations"]
                ),  # Keep for reference
            }

            # 7. Combine cleaned results
            cleaned_data = {
                "text_elements": filtered_text_elements,
                "table_elements": enhanced_tables,
                "extracted_pages": uploaded_pages,  # Updated: with Supabase URLs
                "page_analysis": cleaned_page_analysis,
                "document_metadata": stage1_results.get(
                    "document_metadata", {}
                ),  # Add document metadata
                "metadata": metadata,
            }

            return cleaned_data

        except Exception as e:
            logger.error(f"Post-processing failed: {e}")
            raise PipelineError(f"Post-processing failed: {str(e)}")

    def _filter_text_elements(self, text_elements):
        """Filter text elements to remove tiny fragments and improve quality"""
        filtered_elements = []

        for element in text_elements:
            text = element.get("text", "").strip()

            # Skip elements that are too small or meaningless
            if len(text) < 10:
                # Only keep small elements if they're meaningful (numbers, labels, etc.)
                if not self._is_meaningful_small_element(text):
                    continue

            # Skip pure punctuation or whitespace
            if (
                text
                and text.strip()
                and not text.strip().isalnum()
                and len(text.strip()) < 5
            ):
                continue

            # Clean up the element
            cleaned_element = {
                "id": element.get("id"),
                "category": element.get("category"),
                "page": element.get("page"),
                "text": text,
                "metadata": self._clean_metadata(element.get("metadata", {})),
            }

            filtered_elements.append(cleaned_element)

        return filtered_elements

    def _is_meaningful_small_element(self, text):
        """Check if a small text element is meaningful enough to keep"""
        text = text.strip()

        # Keep numbers and common labels
        if text.isdigit() or text.replace(",", "").replace(".", "").isdigit():
            return True

        # Keep common abbreviations and labels
        meaningful_patterns = [
            r"^[A-Z]{1,3}$",  # Short acronyms
            r"^[0-9]+[A-Z]$",  # Number + letter combinations
            r"^[A-Z][0-9]+$",  # Letter + number combinations
            r"^[IVX]+$",  # Roman numerals
        ]

        import re

        for pattern in meaningful_patterns:
            if re.match(pattern, text):
                return True

        return False

    def _clean_metadata(self, metadata):
        """Clean metadata by removing unnecessary fields"""
        cleaned = {}

        # Keep only essential metadata fields
        essential_fields = [
            "page_number", 
            "filename", 
            "image_path", 
            "bbox",
            "font_size",
            "font_name",
            "is_bold",
            "extraction_method",
            "processing_strategy",
            "table_id",
            "text_as_html"
        ]

        for field in essential_fields:
            if field in metadata:
                cleaned[field] = metadata[field]

        return cleaned

    def _clean_page_analysis(self, page_analysis):
        """Clean page analysis by removing unnecessary fields"""
        cleaned_analysis = {}

        for page_num, analysis in page_analysis.items():
            cleaned_analysis[page_num] = {
                "image_count": analysis.get("image_count"),
                "table_count": analysis.get("table_count"),
                "meaningful_images": analysis.get("meaningful_images"),
                "drawing_items": analysis.get("drawing_items"),
                "has_vector_drawings": analysis.get("has_vector_drawings"),
                "complexity": analysis.get("complexity"),
                "needs_extraction": analysis.get("needs_extraction"),
                "is_fragmented": analysis.get("is_fragmented"),
            }

        return cleaned_analysis

    def __del__(self):
        """Cleanup temporary directories"""
        try:
            import shutil

            if hasattr(self, "temp_dir") and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")


class UnifiedPartitionerV2:
    """Improved unified PDF partitioning using PyMuPDF analysis + unstructured fast"""

    def __init__(self, tables_dir, images_dir, table_validation_config=None):
        self.tables_dir = Path(tables_dir)
        self.images_dir = Path(images_dir)
        self.tables_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)
        
        # Image filtering thresholds (configurable)
        self.min_image_width = 150  # Reduced from 200 for technical diagrams
        self.min_image_height = 100  # Reduced from 150 for technical diagrams
        self.min_image_pixels = 25000  # Reduced from 50k for technical diagrams
        
        # Table validation configuration (with defaults)
        if table_validation_config is None:
            table_validation_config = {}
        
        self.table_validation_enabled = table_validation_config.get("enabled", True)
        self.max_table_size = table_validation_config.get("max_table_size", 5000)
        self.max_columns = table_validation_config.get("max_columns", 20)
        self.max_cells = table_validation_config.get("max_cells", 100)
        self.repetition_threshold = table_validation_config.get("repetition_threshold", 0.7)
        self.min_confidence = table_validation_config.get("min_confidence", 0.3)
        self.reject_on_drawing_pages = table_validation_config.get("reject_on_drawing_pages", True)

    def _count_meaningful_images(self, doc, page, images):
        """Count images that are large enough to be meaningful (not logos/icons)"""
        meaningful_count = 0
        
        for img in images:
            try:
                base_image = doc.extract_image(img[0])
                width = base_image["width"]
                height = base_image["height"]
                
                # Filter out small images (logos, icons, etc.)
                if (width >= self.min_image_width and 
                    height >= self.min_image_height and 
                    width * height >= self.min_image_pixels):
                    meaningful_count += 1
                    
            except Exception as e:
                logger.debug(f"Could not analyze image {img[0]}: {e}")
                continue
        
        return meaningful_count

    def stage1_pymupdf_analysis(self, filepath):
        """Stage 1: PyMuPDF analysis to detect tables and images"""
        logger.info("Stage 1: PyMuPDF analysis for table/image detection...")

        doc = fitz.open(filepath)
        page_analysis = {}
        table_locations = []
        image_locations = []

        # Extract document metadata
        document_metadata = self._extract_document_metadata(doc)

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_index = page_num + 1  # 1-indexed for consistency

            # Get images on this page
            try:
                images = page.get_images()
            except Exception as e:
                logger.warning(f"Could not get images from page {page_index}: {e}")
                images = []

            # Get tables on this page (PyMuPDF table detection)
            try:
                table_finder = page.find_tables()
                tables = list(table_finder)  # Convert to list
            except Exception as e:
                logger.warning(f"Could not find tables on page {page_index}: {e}")
                tables = []

            # Count meaningful images (filter out logos/icons)
            meaningful_images = self._count_meaningful_images(doc, page, images)
            
            # Analyze page complexity with improved logic
            is_fragmented = False
            if len(images) > 10:
                small_count = 0
                for img in images[:5]:  # Sample first 5 images
                    try:
                        base_image = doc.extract_image(img[0])
                        if base_image["width"] * base_image["height"] < 5000:
                            small_count += 1
                    except:
                        continue
                is_fragmented = small_count >= 3

            # Special case: many small images might form a technical diagram
            is_likely_diagram = (len(images) >= 15 and meaningful_images == 0 and len(tables) == 0)
            
            # Check for vector drawings (architectural plans, technical drawings)
            has_vector_drawings = False
            drawing_item_count = 0
            try:
                drawings = page.get_drawings()
                # Count total drawing items (lines, curves, rects, etc.)
                for drawing in drawings:
                    items = drawing.get("items", [])
                    drawing_item_count += len(items)
                # Threshold of 4000 items indicates complex vector drawing
                has_vector_drawings = drawing_item_count >= 4000
            except Exception as e:
                logger.debug(f"Could not analyze drawings on page {page_index}: {e}")
            
            # Determine page complexity using meaningful images and tables
            # IMPROVED: Require minimum meaningful content threshold to avoid logo-only extractions
            min_meaningful_images_for_extraction = 2  # Require at least 2 meaningful images (filters out single logos)
            
            # Precedence: Images → Drawings → Tables
            if meaningful_images >= min_meaningful_images_for_extraction:
                # Images take precedence
                if is_fragmented:
                    complexity = "fragmented"
                elif meaningful_images >= 3:
                    complexity = "complex"
                else:
                    complexity = "simple"
                needs_extraction = True
            elif has_vector_drawings:
                # Vector drawings are second priority
                complexity = "complex_vector_drawing"
                needs_extraction = True
            elif len(tables) > 0:
                # Tables are third priority
                complexity = "simple"
                needs_extraction = True
            elif is_likely_diagram:
                # Special case for diagrams
                complexity = "diagram"
                needs_extraction = True
            else:
                # No significant visual content
                complexity = "text_only"
                needs_extraction = False

            # Store page analysis
            page_analysis[page_index] = {
                "image_count": len(images),
                "meaningful_images": meaningful_images,
                "table_count": len(tables),
                "drawing_items": drawing_item_count,
                "has_vector_drawings": has_vector_drawings,
                "complexity": complexity,
                "needs_extraction": needs_extraction,
                "is_fragmented": is_fragmented,
            }
            
            # Add detailed logging for extraction decisions (first 3 pages + any extracted)
            if page_index <= 3 or needs_extraction:
                reason = []
                if meaningful_images >= min_meaningful_images_for_extraction:
                    reason.append(f"{meaningful_images} meaningful images (≥{min_meaningful_images_for_extraction})")
                if has_vector_drawings:
                    reason.append(f"vector drawing ({drawing_item_count:,} items)")
                if len(tables) > 0:
                    reason.append(f"{len(tables)} tables")
                if is_likely_diagram:
                    reason.append("likely diagram")
                if not needs_extraction:
                    if drawing_item_count > 0:
                        reason.append(f"only {drawing_item_count:,} drawing items (<4000)")
                    else:
                        reason.append(f"only {meaningful_images} meaningful images (<{min_meaningful_images_for_extraction})")
                
                decision = "EXTRACT" if needs_extraction else "SKIP"
                reason_str = ", ".join(reason) if reason else "no meaningful content"
                print(f"📄 BEAM: Page {page_index}: {decision} ({reason_str})")

            # Store table locations
            for i, table in enumerate(tables):
                table_bbox = table.bbox  # (x0, y0, x1, y1)
                table_locations.append(
                    {
                        "id": f"table_page{page_index}_table{i}",
                        "page": page_index,
                        "bbox": table_bbox,
                        "table_data": table,
                        "complexity": complexity,
                        "page_analysis": {
                            "image_count": meaningful_images,
                            "text_blocks": len(page.get_text_blocks()) if hasattr(page, 'get_text_blocks') else 0,
                            "complexity": complexity
                        }
                    }
                )

            # Store image locations
            for i, img in enumerate(images):
                try:
                    # Try to get image rectangle, but handle "not a textpage" errors gracefully
                    img_rect = None
                    try:
                        img_rect = page.get_image_bbox(img)
                    except Exception as bbox_error:
                        # This commonly fails with "not a textpage of this page" for drawing-heavy PDFs
                        logger.debug(f"Could not get image bbox on page {page_index}: {bbox_error}")
                        img_rect = None
                    
                    # Store image info regardless of whether we got bbox or not
                    image_locations.append(
                        {
                            "id": f"image_page{page_index}_img{i}",
                            "page": page_index,
                            "bbox": img_rect,
                            "image_data": img,
                            "complexity": complexity,
                        }
                    )
                    
                except Exception as e:
                    # Final fallback: log the error but continue processing
                    logger.warning(f"Error processing image {i} on page {page_index}: {e}")
                    # Still store the image data so we don't lose it completely
                    image_locations.append(
                        {
                            "id": f"image_page{page_index}_img{i}",
                            "page": page_index,
                            "bbox": None,
                            "image_data": img,
                            "complexity": complexity,
                        }
                    )

        doc.close()

        logger.info(
            f"Stage 1 complete: {len(table_locations)} tables, {len(image_locations)} images"
        )

        return {
            "page_analysis": page_analysis,
            "table_locations": table_locations,
            "image_locations": image_locations,
            "document_metadata": document_metadata,
        }

    def _extract_document_metadata(self, doc):
        """Extract comprehensive document metadata from PyMuPDF"""
        metadata = doc.metadata

        # Get page dimensions from first page
        first_page = doc[0]
        page_rect = first_page.rect

        return {
            "total_pages": len(doc),
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
            "page_dimensions": {"width": page_rect.width, "height": page_rect.height},
        }

    def stage2_fast_text_extraction(self, filepath):
        """Stage 2: PyMuPDF text extraction (replacing unstructured)"""
        logger.info("Stage 2: PyMuPDF text extraction...")

        doc = fitz.open(filepath)
        text_elements = []
        raw_elements = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_index = page_num + 1  # 1-indexed

            # Get text blocks with detailed metadata
            try:
                text_dict = page.get_text("dict")
            except Exception as text_error:
                # Handle pages that don't have text layers (e.g., pure CAD drawings)
                logger.warning(f"Could not extract text dict from page {page_index}: {text_error}")
                text_dict = {"blocks": []}  # Continue with empty blocks

            # Process text blocks
            for block in text_dict.get("blocks", []):
                if "lines" in block:  # Text block
                    block_text = ""
                    block_bbox = block.get("bbox", [0, 0, 0, 0])

                    # Combine all lines in the block
                    for line in block["lines"]:
                        for span in line.get("spans", []):
                            block_text += span.get("text", "")

                    # Skip empty blocks
                    if not block_text.strip():
                        continue

                    # Create element with metadata similar to unstructured format
                    element_id = f"text_page{page_index}_block{len(text_elements)}"

                    # Determine category based on text characteristics
                    category = self._determine_text_category(block_text, block)

                    # Create metadata with bbox coordinates
                    metadata = {
                        "page_number": page_index,
                        "bbox": block_bbox,  # Preserve bounding box coordinates
                        "font_size": self._get_font_size(block),
                        "font_name": self._get_font_name(block),
                        "is_bold": self._is_bold_text(block),
                        "extraction_method": "pymupdf_text_dict",
                    }

                    # Create text element similar to unstructured format
                    text_element = {
                        "id": element_id,
                        "category": category,
                        "page": page_index,
                        "text": block_text,
                        "metadata": metadata,
                    }

                    text_elements.append(text_element)
                    raw_elements.append(text_element)

        doc.close()
        logger.info(f"Found {len(text_elements)} text elements")
        logger.info(f"Processed {len(text_elements)} text elements")
        return text_elements, raw_elements

    def stage3_targeted_table_processing(self, filepath, table_locations):
        """Stage 3: PyMuPDF table processing (replacing unstructured)"""
        if not table_locations:
            logger.info("No tables detected, skipping table processing")
            return []

        logger.info(
            f"Stage 3: PyMuPDF table processing ({len(table_locations)} tables)..."
        )

        doc = fitz.open(filepath)
        enhanced_tables = []
        pdf_basename = Path(filepath).stem
        rejected_tables = []

        for i, table_info in enumerate(table_locations):
            try:
                page_num = table_info["page"]
                table_data = table_info["table_data"]
                page_analysis = table_info.get("page_analysis", None)
                
                # Validate table before processing
                is_valid, validation_result = self._validate_table(table_data, page_analysis)
                
                if not is_valid:
                    logger.warning(f"Table {i+1} on page {page_num} rejected: {validation_result['issues']}")
                    rejected_tables.append({
                        "page": page_num,
                        "table_index": i,
                        "validation": validation_result
                    })
                    # Skip this table - it will be captured in full-page extraction
                    continue

                # Get the page
                page = doc[page_num - 1]  # PyMuPDF is 0-indexed

                # Extract full page as table image for better VLM context
                # Store table bbox for reference but don't clip the image
                table_bbox = table_data.bbox
                table_rect = fitz.Rect(table_bbox)
                matrix = fitz.Matrix(2, 2)  # 200 DPI for tables
                pixmap = page.get_pixmap(matrix=matrix)  # Full page for VLM context

                # Save table image
                table_id = f"table_{i+1}"
                filename = f"{pdf_basename}_page{page_num:02d}_{table_id}.png"
                save_path = self.tables_dir / filename
                pixmap.save(str(save_path))

                # Extract table text only (no HTML needed)
                try:
                    table_text = table_data.to_markdown()
                except AttributeError:
                    # Fallback if to_markdown not available
                    table_text = str(table_data) if table_data else ""

                # Create enhanced table element
                enhanced_table = {
                    "id": table_id,
                    "category": "Table",
                    "page": page_num,
                    "text": table_text,
                    "metadata": {
                        "page_number": page_num,
                        "table_id": table_id,
                        "extraction_method": "pymupdf_table_image",
                        "image_path": str(save_path),
                        "width": pixmap.width,
                        "height": pixmap.height,
                        "dpi": int(matrix.a * 72),
                    },
                }

                enhanced_tables.append(enhanced_table)
                logger.info(f"Processed table {i+1}: {filename}")

            except Exception as e:
                logger.error(f"Error processing table {i+1}: {e}")

        doc.close()
        
        # Log validation summary
        if rejected_tables:
            logger.warning(f"Rejected {len(rejected_tables)} tables due to quality issues")
            for rejected in rejected_tables:
                logger.debug(f"  - Page {rejected['page']}: {rejected['validation']['issues']}")
        
        logger.info(
            f"Enhanced {len(enhanced_tables)} valid tables, rejected {len(rejected_tables)} invalid tables"
        )
        return enhanced_tables

    def stage3_create_table_elements_only(self, filepath, table_locations):
        """Create table elements with metadata only (no individual image extraction)"""
        if not table_locations:
            logger.info("No tables detected")
            return []

        logger.info(f"Creating {len(table_locations)} table elements without individual image extraction")
        
        doc = fitz.open(filepath)
        table_elements = []
        rejected_tables = []
        
        for i, table_info in enumerate(table_locations):
            try:
                page_num = table_info["page"]
                table_data = table_info["table_data"]
                page_analysis = table_info.get("page_analysis", None)
                
                # Validate table before processing
                is_valid, validation_result = self._validate_table(table_data, page_analysis)
                
                if not is_valid:
                    logger.warning(f"Table {i+1} on page {page_num} rejected: {validation_result['issues']}")
                    rejected_tables.append({
                        "page": page_num,
                        "table_index": i,
                        "validation": validation_result
                    })
                    # Skip this table - it will be captured in full-page extraction
                    continue
                
                # Extract table text only (no HTML, no image)
                try:
                    table_text = table_data.to_markdown()
                except AttributeError:
                    # Fallback if to_markdown not available
                    table_text = str(table_data) if table_data else ""
                
                # Create table element with metadata only
                table_id = f"table_{i+1}"
                table_element = {
                    "id": table_id,
                    "category": "Table",
                    "page": page_num,
                    "text": table_text,
                    "metadata": {
                        "page_number": page_num,
                        "table_id": table_id,
                        "extraction_method": "text_only_full_page_covers_image",
                        # No image_path - covered by full-page extraction
                    },
                }
                
                table_elements.append(table_element)
                logger.info(f"Created table element {table_id} on page {page_num} (no individual image)")
                
            except Exception as e:
                logger.error(f"Error creating table element {i+1}: {e}")
        
        doc.close()
        
        # Log validation summary
        if rejected_tables:
            logger.warning(f"Rejected {len(rejected_tables)} tables due to quality issues")
            for rejected in rejected_tables:
                logger.debug(f"  - Page {rejected['page']}: {rejected['validation']['issues']}")
        
        logger.info(f"Created {len(table_elements)} valid table elements, rejected {len(rejected_tables)} invalid tables")
        return table_elements

    def stage4_full_page_extraction(self, filepath, page_analysis):
        """Stage 4: Extract full pages when images are detected (like partition_pdf.py)"""
        # Find pages that need full-page extraction
        pages_to_extract = {
            page_num: info
            for page_num, info in page_analysis.items()
            if info["needs_extraction"]
        }

        if not pages_to_extract:
            logger.info("No pages need full-page extraction")
            return {}

        logger.info(f"Stage 4: Full page extraction ({len(pages_to_extract)} pages)...")

        extracted_pages = {}
        pdf_basename = Path(filepath).stem
        doc = fitz.open(filepath)

        for page_num, info in pages_to_extract.items():
            try:
                # Get page (PyMuPDF is 0-indexed)
                page = doc[page_num - 1]

                # Determine matrix based on complexity
                if info["is_fragmented"]:
                    matrix = fitz.Matrix(3, 3)  # Higher DPI for fragmented
                elif info["complexity"] == "complex":
                    matrix = fitz.Matrix(2, 2)  # Standard high DPI
                else:
                    matrix = fitz.Matrix(1.5, 1.5)  # Lower DPI for simple

                # Extract full page
                pixmap = page.get_pixmap(matrix=matrix)

                # Save image with UUID to avoid conflicts
                unique_id = uuid4().hex[:8]  # Use first 8 chars of UUID
                filename = f"{pdf_basename}_page{page_num:02d}_{info['complexity']}_{unique_id}.png"
                save_path = self.images_dir / filename
                pixmap.save(str(save_path))

                extracted_pages[page_num] = {
                    "filepath": str(save_path),
                    "filename": filename,
                    "width": pixmap.width,
                    "height": pixmap.height,
                    "dpi": int(matrix.a * 72),  # Convert matrix to DPI
                    "complexity": info["complexity"],
                    "original_image_count": info["image_count"],
                    "original_table_count": info["table_count"],
                }

                logger.info(f"Page {page_num}: {filename} ({info['complexity']})")

            except Exception as e:
                logger.error(f"Error extracting page {page_num}: {e}")

        doc.close()
        logger.info(f"Extracted {len(extracted_pages)} full pages")
        return extracted_pages

    def _determine_text_category(self, text, block):
        """Determine text category based on characteristics"""
        text_upper = text.upper().strip()

        # Check for titles/headers
        if len(text.strip()) < 100 and any(char.isupper() for char in text):
            # Check if it's likely a header based on font size or position
            font_size = self._get_font_size(block)
            if font_size > 12:  # Larger font likely indicates header
                return "Title"

        # Check for list items
        if text.strip().startswith(("•", "-", "*", "1.", "2.", "3.", "a.", "b.", "c.")):
            return "ListItem"

        # Default to narrative text
        return "NarrativeText"

    def _get_font_size(self, block):
        """Extract font size from block"""
        try:
            if "lines" in block and block["lines"]:
                line = block["lines"][0]
                if "spans" in line and line["spans"]:
                    return line["spans"][0].get("size", 12)
        except:
            pass
        return 12

    def _get_font_name(self, block):
        """Extract font name from block"""
        try:
            if "lines" in block and block["lines"]:
                line = block["lines"][0]
                if "spans" in line and line["spans"]:
                    return line["spans"][0].get("font", "unknown")
        except:
            pass
        return "unknown"

    def _is_bold_text(self, block):
        """Check if text is bold"""
        try:
            if "lines" in block and block["lines"]:
                line = block["lines"][0]
                if "spans" in line and line["spans"]:
                    flags = line["spans"][0].get("flags", 0)
                    return bool(flags & 2**4)  # Bold flag
        except:
            pass
        return False

    def _validate_table(self, table_data, page_analysis=None) -> Tuple[bool, Dict[str, Any]]:
        """Validate table quality and determine if it should be processed"""
        validation_result = {
            "is_valid": True,
            "confidence": 1.0,
            "issues": [],
            "metrics": {}
        }
        
        if not self.table_validation_enabled:
            return True, validation_result
            
        try:
            # Extract table content for analysis
            table_text = table_data.to_markdown() if hasattr(table_data, 'to_markdown') else str(table_data)
            table_cells = table_data.extract() if hasattr(table_data, 'extract') else []
            
            # Check table size
            text_length = len(table_text)
            validation_result["metrics"]["text_length"] = text_length
            
            if text_length > self.max_table_size:
                validation_result["is_valid"] = False
                validation_result["issues"].append(f"Table too large: {text_length} chars (max: {self.max_table_size})")
                validation_result["confidence"] *= 0.3
            
            # Check number of columns
            if hasattr(table_data, 'col_count'):
                col_count = table_data.col_count
                validation_result["metrics"]["columns"] = col_count
                
                if col_count > self.max_columns:
                    validation_result["is_valid"] = False
                    validation_result["issues"].append(f"Too many columns: {col_count} (max: {self.max_columns})")
                    validation_result["confidence"] *= 0.4
            
            # Check for repetition
            repetition_score = self._calculate_repetition_score(table_text)
            validation_result["metrics"]["repetition_score"] = repetition_score
            
            if repetition_score > self.repetition_threshold:
                validation_result["is_valid"] = False
                validation_result["issues"].append(f"High repetition: {repetition_score:.2f} (threshold: {self.repetition_threshold})")
                validation_result["confidence"] *= 0.2
            
            # Check if page is primarily a drawing
            if page_analysis and self.reject_on_drawing_pages:
                if self._is_drawing_page(page_analysis):
                    validation_result["is_valid"] = False
                    validation_result["issues"].append("Page appears to be a drawing/diagram")
                    validation_result["confidence"] *= 0.3
            
            # Final confidence check
            if validation_result["confidence"] < self.min_confidence:
                validation_result["is_valid"] = False
                validation_result["issues"].append(f"Low confidence: {validation_result['confidence']:.2f}")
            
        except Exception as e:
            logger.warning(f"Table validation error: {e}")
            # On error, be conservative and reject
            validation_result["is_valid"] = False
            validation_result["issues"].append(f"Validation error: {str(e)}")
            
        return validation_result["is_valid"], validation_result
    
    def _calculate_repetition_score(self, text: str) -> float:
        """Calculate how repetitive the text content is"""
        if not text or len(text) < 100:
            return 0.0
            
        # Split into words and count duplicates
        words = text.split()
        if len(words) == 0:
            return 0.0
            
        # Count word frequencies
        word_counts = Counter(words)
        
        # Calculate repetition score
        total_words = len(words)
        unique_words = len(word_counts)
        
        # Also check for repeated sequences
        repeated_sequences = 0
        sequence_length = 5
        for i in range(len(words) - sequence_length):
            sequence = ' '.join(words[i:i+sequence_length])
            if text.count(sequence) > 2:  # Sequence appears more than twice
                repeated_sequences += 1
        
        # Combine metrics
        word_repetition = 1 - (unique_words / total_words)
        sequence_repetition = min(1.0, repeated_sequences / 10)  # Normalize to 0-1
        
        return (word_repetition * 0.7) + (sequence_repetition * 0.3)
    
    def _is_drawing_page(self, page_analysis: Dict[str, Any]) -> bool:
        """Determine if a page is primarily a drawing/diagram"""
        if not page_analysis:
            return False
            
        # Check image count vs text blocks
        image_count = page_analysis.get("image_count", 0)
        text_blocks = page_analysis.get("text_blocks", 0)
        
        # If many images and few text blocks, likely a drawing
        if image_count > 3 and text_blocks < 10:
            return True
            
        # Check page complexity score if available
        complexity = page_analysis.get("complexity", "")
        if complexity in ["complex", "very_complex"]:
            # Complex pages with images are often drawings
            if image_count > 0:
                return True
                
        return False

    # HTML conversion removed - relying on VLM captions only

    def _cleanup_extracted_files(self):
        """Clean up extracted files, keeping only table images"""
        logger.info("Cleaning up extracted files...")

        all_extracted_files = list(self.tables_dir.glob("*"))
        tables_kept = 0
        figures_removed = 0

        for file_path in all_extracted_files:
            filename = file_path.name.lower()
            if filename.startswith("figure-"):
                # Remove figure files
                try:
                    file_path.unlink()
                    figures_removed += 1
                    logger.debug(f"Removed figure file: {file_path.name}")
                except Exception as e:
                    logger.warning(f"Could not remove {file_path.name}: {e}")
            elif filename.startswith("table-"):
                # Keep table files
                tables_kept += 1
                logger.debug(f"Kept table file: {file_path.name}")
            else:
                # Log other files but don't remove them
                logger.debug(f"Other file found: {file_path.name}")

        logger.info(
            f"Cleanup results: {tables_kept} tables kept, {figures_removed} figures removed"
        )
