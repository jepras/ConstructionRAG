"""Production partition step for document processing pipeline."""

import os
import json
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Core libraries
from unstructured.partition.pdf import partition_pdf
import fitz  # PyMuPDF
from pdf2image import convert_from_path

from ...shared.base_step import PipelineStep
from ....models import StepResult
from ...shared.models import DocumentInput, PipelineError

logger = logging.getLogger(__name__)


class PartitionStep(PipelineStep):
    """Production partition step implementing the unified partitioning pipeline"""

    def __init__(
        self, config: Dict[str, Any], storage_client=None, progress_tracker=None
    ):
        super().__init__(config, progress_tracker)
        self.storage_client = storage_client

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
                input_data.file_path
            )

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Create summary statistics
            summary_stats = {
                "text_elements": len(partition_result.get("text_elements", [])),
                "table_elements": len(partition_result.get("table_elements", [])),
                "raw_elements": len(partition_result.get("raw_elements", [])),
                "extracted_pages": len(partition_result.get("extracted_pages", [])),
                "table_locations": len(partition_result.get("table_locations", [])),
                "image_locations": len(partition_result.get("image_locations", [])),
                "pages_analyzed": len(partition_result.get("page_analysis", {})),
                "processing_strategy": partition_result.get("metadata", {}).get(
                    "processing_strategy", "unknown"
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
                        "category": getattr(elem, "category", "Unknown"),
                        "text_preview": (
                            getattr(elem, "text", "")[:200] + "..."
                            if len(getattr(elem, "text", "")) > 200
                            else getattr(elem, "text", "")
                        ),
                    }
                    for elem in partition_result.get("table_elements", [])[:2]
                ],
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
                    "raw_elements": partition_result.get("raw_elements", []),
                    "extracted_pages": partition_result.get("extracted_pages", {}),
                    "page_analysis": partition_result.get("page_analysis", {}),
                    "table_locations": partition_result.get("table_locations", []),
                    "image_locations": partition_result.get("image_locations", []),
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

    async def _partition_document_async(self, filepath: str) -> Dict[str, Any]:
        """Execute the unified partitioning pipeline asynchronously"""

        # Run the CPU-intensive partitioning in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self._partition_document_sync, filepath
        )

        return result

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

        # Clean up data for serialization
        def clean_for_pickle(obj):
            """Remove non-serializable objects"""
            if isinstance(obj, dict):
                cleaned = {}
                for key, value in obj.items():
                    if key in ["image_data", "table_data"]:  # Skip PyMuPDF objects
                        continue
                    cleaned[key] = clean_for_pickle(value)
                return cleaned
            elif isinstance(obj, list):
                return [clean_for_pickle(item) for item in obj]
            else:
                return obj

        # Combine all results
        combined_data = {
            "text_elements": text_elements,
            "table_elements": enhanced_tables,
            "raw_elements": raw_elements,
            "extracted_pages": extracted_pages,
            "table_locations": clean_for_pickle(stage1_results["table_locations"]),
            "image_locations": clean_for_pickle(stage1_results["image_locations"]),
            "page_analysis": stage1_results["page_analysis"],
            "metadata": {
                "processing_strategy": "unified_v2_pymupdf_fast",
                "timestamp": datetime.now().isoformat(),
                "source_file": os.path.basename(filepath),
                "text_count": len(text_elements),
                "raw_count": len(raw_elements),
                "table_count": len(stage1_results["table_locations"]),
                "image_count": len(stage1_results["image_locations"]),
                "enhanced_tables": len(enhanced_tables),
                "extracted_pages": len(extracted_pages),
                "pages_analyzed": len(stage1_results["page_analysis"]),
            },
        }

        logger.info(
            f"Partitioning completed: {len(text_elements)} text elements, {len(enhanced_tables)} tables"
        )
        return combined_data

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
        }

    def stage2_fast_text_extraction(self, filepath):
        """Stage 2: Fast unstructured extraction for text content with language support"""
        logger.info("Stage 2: Fast text extraction with unstructured...")

        # Fast extraction to get text content
        fast_elements = partition_pdf(
            filename=filepath,
            strategy="fast",
            languages=["dan"],  # Danish language support
            max_characters=50000,
            combine_text_under_n_chars=200,
            include_metadata=True,
            include_page_breaks=True,
        )

        logger.info(f"Found {len(fast_elements)} text elements")

        # Process text elements
        text_elements = []
        raw_elements = []  # Preserve raw elements for downstream metadata access

        for i, element in enumerate(fast_elements):
            element_id = str(i + 1)  # Simple numeric ID
            category = getattr(element, "category", "Unknown")
            metadata_dict = getattr(element, "metadata", {})

            if hasattr(metadata_dict, "to_dict"):
                metadata_dict = metadata_dict.to_dict()

            page_num = metadata_dict.get("page_number", 1)

            # Store raw element for downstream access
            raw_elements.append(element)

            # Only include non-table, non-image elements in processed text
            if category not in ["Table", "Image"]:
                # Remove coordinates from metadata
                if "coordinates" in metadata_dict:
                    del metadata_dict["coordinates"]

                text_elements.append(
                    {
                        "id": element_id,
                        "element": element,
                        "category": category,
                        "page": page_num,
                        "text": getattr(element, "text", ""),
                        "metadata": metadata_dict,
                    }
                )

        logger.info(f"Processed {len(text_elements)} text elements")
        return text_elements, raw_elements

    def stage3_targeted_table_processing(self, filepath, table_locations):
        """Stage 3: Targeted vision processing for detected tables"""
        if not table_locations:
            logger.info("No tables detected, skipping vision processing")
            return []

        logger.info(
            f"Stage 3: Targeted table processing ({len(table_locations)} tables)..."
        )

        # Process tables with vision capabilities
        table_elements = partition_pdf(
            filename=filepath,
            strategy="hi_res",
            languages=["dan"],
            extract_images_in_pdf=True,
            extract_image_block_types=["Table"],
            extract_image_block_output_dir=str(self.tables_dir),
            extract_image_block_to_payload=False,
            infer_table_structure=True,
            pdf_infer_table_structure=True,
        )

        # Filter to keep only table elements
        enhanced_tables = []
        for element in table_elements:
            if getattr(element, "category", "") == "Table":
                enhanced_tables.append(element)

        logger.info(f"Enhanced {len(enhanced_tables)} tables with vision processing")
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

                # Save image
                filename = f"{pdf_basename}_page{page_num:02d}_{info['complexity']}.png"
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
