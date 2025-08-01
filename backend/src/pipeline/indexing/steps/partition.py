"""Production partition step for document processing pipeline."""

import re
import asyncio
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4
import logging

# PDF processing
import fitz  # PyMuPDF

# Storage
from src.services.storage_service import StorageService

# Pipeline components
from ...shared.base_step import PipelineStep
from src.models import StepResult
from ...shared.models import DocumentInput, PipelineError

logger = logging.getLogger(__name__)


class PartitionStep(PipelineStep):
    """Production partition step implementing the unified partitioning pipeline"""

    def __init__(
        self, config: Dict[str, Any], storage_client=None, progress_tracker=None
    ):
        super().__init__(config, progress_tracker)
        self.storage_client = storage_client
        self.storage_service = StorageService()

        # Extract configuration
        self.ocr_strategy = config.get("ocr_strategy", "auto")
        self.extract_tables = config.get("extract_tables", True)
        self.extract_images = config.get("extract_images", True)
        self.max_image_size_mb = config.get("max_image_size_mb", 10)
        self.ocr_languages = config.get("ocr_languages", ["dan"])
        self.include_coordinates = config.get("include_coordinates", True)

        # Create temporary directories for processing
        self.temp_dir = Path(tempfile.mkdtemp(prefix="partition_"))
        self.tables_dir = self.temp_dir / "tables"
        self.images_dir = self.temp_dir / "images"

        # Create directories
        self.tables_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)

        logger.info(f"PartitionStep initialized with temp dir: {self.temp_dir}")

    async def execute(self, input_data: DocumentInput) -> StepResult:
        """Execute the partition step with async operations"""
        start_time = datetime.utcnow()

        try:
            logger.info(f"Starting partition step for document: {input_data.filename}")

            # Validate input
            if not await self.validate_prerequisites_async(input_data):
                raise PipelineError("Prerequisites not met for partition step")

            # Execute partitioning pipeline
            partition_result = await self._partition_document_async(
                input_data.file_path, input_data
            )

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

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
                "document_metadata": {
                    "total_pages": partition_result.get("document_metadata", {}).get(
                        "total_pages", 0
                    ),
                    "has_title": bool(
                        partition_result.get("document_metadata", {}).get("title", "")
                    ),
                },
                "tables_with_html": sum(
                    1
                    for table in partition_result.get("table_elements", [])
                    if table.get("metadata", {}).get("text_as_html")
                ),
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
                        "has_html": bool(
                            elem.get("metadata", {}).get("text_as_html", "")
                        ),
                        "html_preview": (
                            elem.get("metadata", {}).get("text_as_html", "")[:100]
                            + "..."
                            if len(elem.get("metadata", {}).get("text_as_html", ""))
                            > 100
                            else elem.get("metadata", {}).get("text_as_html", "")
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
            logger.error(f"Partition step failed: {e}")
            duration = (datetime.utcnow() - start_time).total_seconds()

            return StepResult(
                step="partition",
                status="failed",
                duration_seconds=duration,
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

    async def validate_prerequisites_async(self, input_data: DocumentInput) -> bool:
        """Validate partition step prerequisites"""
        try:
            # Check if file exists and is accessible
            if not os.path.exists(input_data.file_path):
                logger.error(f"File not found: {input_data.file_path}")
                return False

            # Check if file is a PDF
            if not input_data.filename.lower().endswith(".pdf"):
                logger.error(f"File is not a PDF: {input_data.filename}")
                return False

            # Check file size
            file_size_mb = os.path.getsize(input_data.file_path) / (1024 * 1024)
            if file_size_mb > 100:  # 100MB limit
                logger.error(f"File too large: {file_size_mb:.2f}MB")
                return False

            logger.info(f"Prerequisites validated for: {input_data.filename}")
            return True

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
        partitioner = UnifiedPartitionerV2(str(self.tables_dir), str(self.images_dir))

        # Stage 1: PyMuPDF analysis
        stage1_results = partitioner.stage1_pymupdf_analysis(filepath)

        # Stage 2: Fast text extraction
        text_elements, raw_elements = partitioner.stage2_fast_text_extraction(filepath)

        # Stage 3: Targeted table processing (if enabled)
        enhanced_tables = []
        if self.extract_tables:
            enhanced_tables = partitioner.stage3_targeted_table_processing(
                filepath, stage1_results["table_locations"]
            )

        # Stage 4: Full page extraction (if enabled)
        extracted_pages = []
        if self.extract_images:
            extracted_pages = partitioner.stage4_full_page_extraction(
                filepath, stage1_results["page_analysis"]
            )

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
                        upload_result = await self.storage_service.upload_extracted_page_image(
                            image_path=page_info["filepath"],
                            run_id=document_input.run_id,  # Use run_id from DocumentInput
                            document_id=document_input.document_id,  # Use document_id from DocumentInput
                            page_num=page_num,
                            complexity=page_info["complexity"],
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

            # 5. Upload table images to Supabase Storage
            if enhanced_tables:
                logger.info(
                    f"Uploading {len(enhanced_tables)} table images to Supabase Storage..."
                )

                for table_element in enhanced_tables:
                    try:
                        table_id = table_element["id"]
                        image_path = table_element["metadata"].get("image_path")

                        if image_path and Path(image_path).exists():
                            # Upload table image to Supabase Storage with new structure
                            upload_result = await self.storage_service.upload_table_image(
                                image_path=image_path,
                                run_id=document_input.run_id,  # Use run_id from DocumentInput
                                document_id=document_input.document_id,  # Use document_id from DocumentInput
                                table_id=table_id,
                            )

                            # Add Supabase URL to table metadata
                            table_element["metadata"]["image_url"] = upload_result[
                                "url"
                            ]
                            table_element["metadata"]["image_storage_path"] = (
                                upload_result["storage_path"]
                            )

                            logger.info(
                                f"Uploaded table {table_id}: {upload_result['url']}"
                            )
                        else:
                            logger.debug(f"No image path found for table {table_id}")

                    except Exception as e:
                        logger.error(
                            f"Failed to upload table image for {table_id}: {e}"
                        )
                        # Keep local path as fallback

            # 6. Prepare metadata
            metadata = {
                "processing_strategy": "pymupdf_only",
                "timestamp": datetime.now().isoformat(),
                "source_file": os.path.basename(filepath),
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
        essential_fields = ["page_number", "filename", "image_path"]

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

    def __init__(self, tables_dir, images_dir):
        self.tables_dir = Path(tables_dir)
        self.images_dir = Path(images_dir)
        self.tables_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)

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
            images = page.get_images()

            # Get tables on this page (PyMuPDF table detection)
            table_finder = page.find_tables()
            tables = list(table_finder)  # Convert to list

            # Analyze page complexity
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

            # Determine page complexity (matching original notebook logic)
            if len(images) == 0 and len(tables) == 0:
                complexity = "text_only"
                needs_extraction = False
            elif is_fragmented:
                complexity = "fragmented"
                needs_extraction = True
            elif len(images) >= 3:  # Extract if 3+ images
                complexity = "complex"
                needs_extraction = True
            elif len(images) >= 1:  # Extract if any images
                complexity = "simple"
                needs_extraction = True
            else:
                complexity = "simple"
                needs_extraction = False

            # Store page analysis
            page_analysis[page_index] = {
                "image_count": len(images),
                "table_count": len(tables),
                "complexity": complexity,
                "needs_extraction": needs_extraction,
                "is_fragmented": is_fragmented,
            }

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
                    }
                )

            # Store image locations
            for i, img in enumerate(images):
                try:
                    # Get image rectangle - use a different approach
                    img_rect = page.get_image_bbox(img)
                    if img_rect:
                        image_locations.append(
                            {
                                "id": f"image_page{page_index}_img{i}",
                                "page": page_index,
                                "bbox": img_rect,
                                "image_data": img,
                                "complexity": complexity,
                            }
                        )
                    else:
                        # Fallback: store image without bbox
                        image_locations.append(
                            {
                                "id": f"image_page{page_index}_img{i}",
                                "page": page_index,
                                "bbox": None,
                                "image_data": img,
                                "complexity": complexity,
                            }
                        )
                except Exception as e:
                    # Fallback: store image without bbox
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
            text_dict = page.get_text("dict")

            for block in text_dict["blocks"]:
                if "lines" in block:  # Text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                # Create text element similar to unstructured format
                                text_element = {
                                    "id": f"text_page{page_index}_block{len(text_elements)}",
                                    "category": self._determine_text_category(
                                        text, span
                                    ),
                                    "page": page_index,
                                    "text": text,
                                    "metadata": {
                                        "page_number": page_index,
                                        "font_size": span["size"],
                                        "font_name": span["font"],
                                        "is_bold": "Bold" in span["font"],
                                        "extraction_method": "pymupdf_text_dict",
                                    },
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

        for i, table_info in enumerate(table_locations):
            try:
                page_num = table_info["page"]
                table_data = table_info["table_data"]

                # Get the page
                page = doc[page_num - 1]  # PyMuPDF is 0-indexed

                # Extract table as image
                table_bbox = table_data.bbox
                table_rect = fitz.Rect(table_bbox)
                matrix = fitz.Matrix(2, 2)  # 200 DPI for tables
                pixmap = page.get_pixmap(matrix=matrix, clip=table_rect)

                # Save table image
                table_id = f"table_{i+1}"
                filename = f"{pdf_basename}_page{page_num:02d}_{table_id}.png"
                save_path = self.tables_dir / filename
                pixmap.save(str(save_path))

                # Extract table text and HTML
                table_text = table_data.to_markdown()
                table_html = self._table_to_html(table_data)

                # Create enhanced table element
                enhanced_table = {
                    "id": table_id,
                    "category": "Table",
                    "page": page_num,
                    "text": table_text,
                    "metadata": {
                        "page_number": page_num,
                        "table_id": table_id,
                        "has_html": bool(table_html),
                        "html_length": len(table_html) if table_html else 0,
                        "extraction_method": "pymupdf_table_image",
                        "text_as_html": table_html,  # This is what enrichment step expects
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
        logger.info(
            f"Enhanced {len(enhanced_tables)} tables with PyMuPDF processing and metadata"
        )
        return enhanced_tables

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

    def _determine_text_category(self, text, span):
        """Determine text category based on font size and content"""
        font_size = span["size"]
        is_bold = "Bold" in span["font"]

        if font_size > 15 or is_bold:
            return "Title"
        elif text.strip().startswith(("•", "-", "1.", "2.", "3.")):
            return "ListItem"
        else:
            return "NarrativeText"

    def _table_to_html(self, table_data):
        """Convert PyMuPDF table to HTML"""
        try:
            # Convert to pandas DataFrame and then to HTML
            df = table_data.to_pandas()
            if not df.empty:
                html = df.to_html(
                    index=False, header=True, classes="table table-striped"
                )
                return html
        except Exception as e:
            logger.warning(f"Pandas HTML conversion failed: {e}")

        # Fallback: simple text-to-HTML
        try:
            text = table_data.extract()
            if text:
                return f"<table><tr><td>{text.replace(chr(10), '</td></tr><tr><td>')}</td></tr></table>"
        except:
            pass

        return ""

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
