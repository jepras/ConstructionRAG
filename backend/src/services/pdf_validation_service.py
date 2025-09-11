"""PDF validation service for pre-upload security and integrity checks."""

import asyncio
import hashlib
import logging
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFValidationService:
    """Service for validating PDF files before upload and processing."""
    
    # File size limits
    MAX_FILE_SIZE_MB = 50
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    
    # Page limits
    MAX_PAGES_ANONYMOUS = 500
    MAX_PAGES_AUTHENTICATED = 2000
    
    # Security patterns - separated into critical and warning levels
    CRITICAL_PATTERNS = [
        rb"/EmbeddedFile",  # Embedded files could contain malware
        rb"/OpenAction",    # Auto-executing actions are risky
        rb"/SubmitForm",    # Form submission to external servers
        rb"/ImportData",    # Data import from external sources
    ]
    
    WARNING_PATTERNS = [
        rb"/JavaScript",    # JavaScript - common in interactive PDFs
        rb"/JS",           # JavaScript - often used for forms/navigation
        rb"/Launch",       # Can be legitimate for document navigation
        rb"/AA",           # Additional Actions - common in forms
        rb"/URI",          # External links - often legitimate
    ]
    
    # Allowed MIME types
    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "application/x-pdf",
    }
    
    def __init__(self):
        """Initialize the PDF validation service."""
        self.validation_cache: Dict[str, Dict[str, Any]] = {}
        # Thread pool for CPU-bound operations (PyMuPDF)
        # Limit to 4 workers to avoid overwhelming the system
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def _calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content for caching."""
        return hashlib.sha256(file_content).hexdigest()
    
    async def validate_pdf(
        self,
        file_content: bytes,
        filename: str,
        is_authenticated: bool = False,
    ) -> Dict[str, Any]:
        """
        Validate a PDF file for security, integrity, and processing requirements.
        
        Args:
            file_content: The PDF file content as bytes
            filename: The name of the file
            is_authenticated: Whether the user is authenticated (affects limits)
            
        Returns:
            Dictionary containing validation results and metadata
        """
        start_time = time.time()
        
        # Check cache first
        cache_start = time.time()
        file_hash = self._calculate_file_hash(file_content)
        if file_hash in self.validation_cache:
            logger.info(f"Using cached validation for {filename} (cache lookup: {time.time() - cache_start:.2f}s)")
            return self.validation_cache[file_hash]
        logger.info(f"Cache miss for {filename} (hash calc: {time.time() - cache_start:.2f}s)")
        
        result = {
            "filename": filename,
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "metadata": {
                "file_size_bytes": len(file_content),
                "file_size_mb": len(file_content) / (1024 * 1024),
                "file_hash": file_hash,
            },
            "page_analysis": {},
            "security": {
                "has_javascript": False,
                "has_embedded_files": False,
                "has_external_links": False,
                "suspicious_patterns": [],
            },
            "processing_estimate": {},
        }
        
        # 1. Basic file checks
        basic_start = time.time()
        self._validate_file_size(file_content, result)
        self._validate_filename(filename, result)
        logger.info(f"Basic checks for {filename}: {time.time() - basic_start:.2f}s")
        
        # 2. Try to open and analyze PDF (THIS IS LIKELY THE SLOW PART)
        if result["is_valid"]:
            analyze_start = time.time()
            await self._analyze_pdf_content(file_content, filename, result, is_authenticated)
            logger.info(f"PDF analysis for {filename}: {time.time() - analyze_start:.2f}s")
        
        # 3. Security scanning (always run for valid files)
        if result["is_valid"]:
            security_start = time.time()
            self._scan_for_security_threats(file_content, result)
            logger.info(f"Security scan for {filename}: {time.time() - security_start:.2f}s")
        
        # 4. Calculate processing time estimate (always calculate)
        estimate_start = time.time()
        self._estimate_processing_time(result)
        logger.info(f"Time estimation for {filename}: {time.time() - estimate_start:.2f}s")
        
        # Cache the result (for 15 minutes)
        self.validation_cache[file_hash] = result
        
        total_time = time.time() - start_time
        logger.info(f"TOTAL validation time for {filename}: {total_time:.2f}s")
        result["metadata"]["validation_time_seconds"] = round(total_time, 2)
        
        return result
    
    def _validate_file_size(self, file_content: bytes, result: Dict[str, Any]):
        """Validate file size is within limits."""
        file_size = len(file_content)
        
        if file_size == 0:
            result["is_valid"] = False
            result["errors"].append("File is empty")
        elif file_size > self.MAX_FILE_SIZE_BYTES:
            result["is_valid"] = False
            result["errors"].append(
                f"File size ({result['metadata']['file_size_mb']:.1f}MB) exceeds maximum allowed size ({self.MAX_FILE_SIZE_MB}MB)"
            )
    
    def _validate_filename(self, filename: str, result: Dict[str, Any]):
        """Validate and sanitize filename."""
        # Check for path traversal attempts
        if ".." in filename or "/" in filename or "\\" in filename:
            result["is_valid"] = False
            result["errors"].append("Invalid filename: contains path characters")
            return
        
        # Check extension
        if not filename.lower().endswith(".pdf"):
            result["is_valid"] = False
            result["errors"].append("File must be a PDF")
            return
        
        # Warn about special characters (but don't fail)
        if re.search(r'[<>:"|?*]', filename):
            result["warnings"].append("Filename contains special characters that may cause issues")
    
    def _analyze_pdf_content_sync(
        self,
        file_content: bytes,
        filename: str,
        result: Dict[str, Any],
        is_authenticated: bool,
    ):
        """Synchronous PDF content analysis using PyMuPDF (CPU-bound)."""
        try:
            # Write to temporary file for PyMuPDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name
            
            try:
                # Open with PyMuPDF
                doc = fitz.open(tmp_path)
                
                # Get basic metadata
                result["metadata"]["page_count"] = len(doc)
                result["metadata"]["pdf_version"] = doc.metadata.get("format", "Unknown")
                result["metadata"]["title"] = doc.metadata.get("title", "")
                result["metadata"]["author"] = doc.metadata.get("author", "")
                result["metadata"]["creation_date"] = doc.metadata.get("creationDate", "")
                
                # Check page count limits
                max_pages = (
                    self.MAX_PAGES_AUTHENTICATED
                    if is_authenticated
                    else self.MAX_PAGES_ANONYMOUS
                )
                if len(doc) > max_pages:
                    result["is_valid"] = False
                    result["errors"].append(
                        f"Document has {len(doc)} pages, exceeds maximum of {max_pages} pages"
                    )
                    doc.close()
                    return
                
                # Analyze pages for complexity
                pages_to_extract = 0
                text_only_pages = 0
                scanned_pages = 0
                total_text_chars = 0
                total_images = 0
                total_tables = 0
                
                # Smart sampling: analyze more pages for better estimates
                # For small docs (<10 pages): analyze all
                # For medium docs (10-50 pages): analyze 5 pages
                # For large docs (>50 pages): analyze 10% up to 10 pages
                if len(doc) <= 10:
                    sample_pages = len(doc)
                elif len(doc) <= 50:
                    sample_pages = min(5, len(doc))
                else:
                    sample_pages = min(10, max(5, len(doc) // 10))
                
                logger.info(f"Analyzing {sample_pages} sample pages of {len(doc)} total")
                
                for page_num in range(sample_pages):
                    page_start = time.time()
                    page = doc[page_num]
                    
                    # Get text content
                    text_start = time.time()
                    try:
                        text = page.get_text().strip()
                        text_length = len(text)
                        total_text_chars += text_length
                    except Exception as e:
                        logger.debug(f"Could not extract text from page {page_num + 1}: {e}")
                        text_length = 0
                    logger.debug(f"  Page {page_num + 1} text extraction: {time.time() - text_start:.2f}s")
                    
                    # Count images (optimized: only check first few for size)
                    img_start = time.time()
                    image_list = page.get_images()
                    
                    # Quick check: sample first 3 images to estimate if they're meaningful
                    meaningful_images = 0
                    if image_list:
                        # If many images, assume some are meaningful based on sampling
                        if len(image_list) <= 5:
                            # For few images, check them all quickly
                            for img in image_list[:5]:
                                try:
                                    xref = img[0]
                                    pix = fitz.Pixmap(doc, xref)
                                    if pix.width > 100 and pix.height > 100:
                                        meaningful_images += 1
                                    pix = None  # Free memory
                                except:
                                    pass
                        else:
                            # For many images, just estimate 30% are meaningful
                            meaningful_images = len(image_list) // 3
                    
                    total_images += meaningful_images
                    logger.debug(f"  Page {page_num + 1} image analysis: {time.time() - img_start:.2f}s ({meaningful_images}/{len(image_list) if image_list else 0} meaningful)")
                    
                    # Fast table detection: just check for table indicators
                    table_start = time.time()
                    has_likely_table = False
                    
                    # Quick heuristic: check for grid-like patterns in text
                    if text_length > 100:
                        # Look for table indicators: multiple spaces, pipes, tabs
                        text_sample = text[:1000]  # Check first 1000 chars
                        if any(indicator in text_sample for indicator in ['  |  ', '\t\t', '│', '─', '┌', '├']):
                            has_likely_table = True
                        elif text_sample.count('  ') > 10:  # Multiple aligned columns
                            has_likely_table = True
                    
                    if has_likely_table:
                        total_tables += 1
                    
                    logger.debug(f"  Page {page_num + 1} table heuristic: {time.time() - table_start:.2f}s (likely table: {has_likely_table})")
                    
                    # Determine page type
                    if text_length < 25:  # Likely scanned
                        scanned_pages += 1
                        pages_to_extract += 1
                    elif meaningful_images > 0 or total_tables > 0:
                        pages_to_extract += 1
                    else:
                        text_only_pages += 1
                    
                    logger.debug(f"  Page {page_num + 1} total time: {time.time() - page_start:.2f}s")
                
                # Extrapolate to full document
                if sample_pages > 0:
                    multiplier = len(doc) / sample_pages
                    result["page_analysis"] = {
                        "total_pages": len(doc),
                        "estimated_text_pages": int(text_only_pages * multiplier),
                        "estimated_complex_pages": int(pages_to_extract * multiplier),
                        "estimated_scanned_pages": int(scanned_pages * multiplier),
                        "avg_text_per_page": total_text_chars / sample_pages,
                        "is_likely_scanned": (scanned_pages / sample_pages) > 0.5,
                        "sample_pages_analyzed": sample_pages,
                    }
                
                doc.close()
                
            finally:
                # Clean up temporary file
                Path(tmp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Failed to analyze PDF {filename}: {e}")
            # Try to be more forgiving - just because we can't fully analyze doesn't mean it's invalid
            logger.warning(f"Could not fully analyze PDF {filename}, using basic validation only")
            
            # Still try to get basic page count if possible
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                    tmp_file.write(file_content)
                    tmp_path = tmp_file.name
                
                try:
                    doc = fitz.open(tmp_path)
                    result["metadata"]["page_count"] = len(doc)
                    result["page_analysis"] = {
                        "total_pages": len(doc),
                        "estimated_text_pages": len(doc),
                        "estimated_complex_pages": 0,
                        "estimated_scanned_pages": 0,
                        "avg_text_per_page": 0,
                        "is_likely_scanned": False,
                        "sample_pages_analyzed": 0,
                    }
                    doc.close()
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
            except:
                # If we still can't open it, mark as invalid
                result["is_valid"] = False
                result["errors"].append(f"Cannot open or parse PDF file: {str(e)}")
    
    def _is_meaningful_image(self, doc, img_info) -> bool:
        """Check if an image is meaningful (not a small logo/icon)."""
        try:
            # Get image dimensions
            base_image = doc.extract_image(img_info[0])
            width = base_image.get("width", 0)
            height = base_image.get("height", 0)
            
            # Consider meaningful if larger than 100x100
            return width > 100 and height > 100
        except:
            return False
    
    async def _analyze_pdf_content(
        self,
        file_content: bytes,
        filename: str,
        result: Dict[str, Any],
        is_authenticated: bool,
    ):
        """Async wrapper for PDF content analysis - runs in thread pool."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self.executor,
            self._analyze_pdf_content_sync,
            file_content,
            filename,
            result,
            is_authenticated
        )
    
    def _scan_for_security_threats(self, file_content: bytes, result: Dict[str, Any]):
        """Scan PDF content for security threats."""
        critical_found = []
        warning_found = []
        
        # Check for critical patterns
        for pattern in self.CRITICAL_PATTERNS:
            if pattern in file_content:
                pattern_name = pattern.decode("utf-8", errors="ignore").strip("/")
                critical_found.append(pattern_name)
                result["security"]["suspicious_patterns"].append(pattern_name)
                
                # Set specific flags
                if b"EmbeddedFile" in pattern:
                    result["security"]["has_embedded_files"] = True
        
        # Check for warning patterns
        for pattern in self.WARNING_PATTERNS:
            if pattern in file_content:
                pattern_name = pattern.decode("utf-8", errors="ignore").strip("/")
                warning_found.append(pattern_name)
                
                # Set flags but don't add to suspicious_patterns
                if b"JavaScript" in pattern or b"JS" in pattern:
                    result["security"]["has_javascript"] = True
                elif b"URI" in pattern or b"Launch" in pattern:
                    result["security"]["has_external_links"] = True
        
        # Only reject for critical patterns
        if critical_found:
            result["is_valid"] = False
            result["errors"].append(
                f"Security threat detected: PDF contains suspicious patterns ({', '.join(critical_found)})"
            )
        elif warning_found:
            # Create a friendly warning message
            js_patterns = [p for p in warning_found if p in ['JavaScript', 'JS']]
            other_patterns = [p for p in warning_found if p not in ['JavaScript', 'JS']]
            
            if js_patterns and other_patterns:
                result["warnings"].append(
                    f"PDF contains JavaScript and interactive features ({', '.join(warning_found)}) - common in form-based documents"
                )
            elif js_patterns:
                result["warnings"].append(
                    "PDF contains JavaScript - common in interactive forms and navigation"
                )
            elif other_patterns:
                result["warnings"].append(
                    f"PDF contains interactive features: {', '.join(other_patterns)}"
                )
    
    def _estimate_processing_time(self, result: Dict[str, Any]):
        """Estimate processing time based on document complexity - PESSIMISTIC approach."""
        # Ensure we always set a processing estimate
        if "page_analysis" not in result or not result.get("page_analysis"):
            # Default pessimistic estimate for when we can't analyze the document
            page_count = result.get("metadata", {}).get("page_count", 1)
            # Assume worst case: OCR needed for all pages
            estimated_seconds = max(60, page_count * 5)  # 5 seconds per page minimum
            result["processing_estimate"] = {
                "estimated_seconds": estimated_seconds,
                "estimated_minutes": round(estimated_seconds / 60, 1),
                "confidence": "low",
                "note": "Conservative estimate - actual time may be less"
            }
            return
        
        analysis = result["page_analysis"]
        
        # PESSIMISTIC estimates (in seconds) - assume worst case scenarios
        # Real processing might be faster, but users won't be disappointed
        text_page_time = 1.5  # Was 0.5, now assume slower processing
        complex_page_time = 6.0  # Was 3.0, assume VLM captioning + table extraction takes longer
        scanned_page_time = 8.0  # Was 4.0, assume OCR could be slow
        
        # For construction/CAD documents, assume many pages might need OCR
        # even if they appear to have text (could be vector text that needs processing)
        total_pages = analysis["total_pages"]
        estimated_text_pages = analysis.get("estimated_text_pages", 0)
        estimated_complex_pages = analysis.get("estimated_complex_pages", 0)
        estimated_scanned_pages = analysis.get("estimated_scanned_pages", 0)
        
        # PESSIMISTIC: Assume 30% of "text" pages might still need OCR processing
        # (common in CAD exports where text is actually vectors)
        potential_ocr_pages = int(estimated_text_pages * 0.3)
        estimated_text_pages -= potential_ocr_pages
        estimated_scanned_pages += potential_ocr_pages
        
        # Calculate total time with pessimistic estimates
        total_seconds = (
            estimated_text_pages * text_page_time
            + estimated_complex_pages * complex_page_time
            + estimated_scanned_pages * scanned_page_time
        )
        
        # Add MORE overhead for pipeline initialization, embedding, and potential retries
        # Assume 20 seconds base + 0.5 seconds per page for embedding/storage
        overhead = 20 + (total_pages * 0.5)
        
        # Add buffer for potential network delays, retries, etc.
        buffer = total_seconds * 0.2  # Add 20% buffer
        
        total_seconds += overhead + buffer
        
        # Round up to nearest 30 seconds for cleaner estimates
        total_seconds = max(30, (int(total_seconds / 30) + 1) * 30)
        
        result["processing_estimate"] = {
            "estimated_seconds": int(total_seconds),
            "estimated_minutes": round(total_seconds / 60, 1),
            "confidence": "conservative" if analysis["sample_pages_analyzed"] >= 5 else "low",
            "note": "Conservative estimate includes OCR processing - actual time may be less",
            "breakdown": {
                "text_pages_time": estimated_text_pages * text_page_time,
                "complex_pages_time": estimated_complex_pages * complex_page_time,
                "scanned_pages_time": estimated_scanned_pages * scanned_page_time,
                "overhead_time": overhead,
                "buffer_time": buffer,
            },
        }
    
    async def validate_batch(
        self,
        files: List[tuple[str, bytes]],
        is_authenticated: bool = False,
    ) -> Dict[str, Any]:
        """
        Validate a batch of PDF files in parallel.
        
        Args:
            files: List of (filename, content) tuples
            is_authenticated: Whether the user is authenticated
            
        Returns:
            Batch validation results
        """
        import asyncio
        
        batch_start = time.time()
        logger.info(f"Starting parallel validation of {len(files)} files")
        
        # Create validation tasks for all files to run in parallel
        validation_tasks = [
            self.validate_pdf(content, filename, is_authenticated)
            for filename, content in files
        ]
        
        # Run all validations concurrently
        file_results = await asyncio.gather(*validation_tasks)
        
        # Process results
        results = {
            "files": [],
            "is_valid": True,
            "total_pages": 0,
            "total_processing_time_estimate": 0,
            "errors": [],
            "warnings": [],
        }
        
        for file_result in file_results:
            results["files"].append(file_result)
            
            if not file_result["is_valid"]:
                results["is_valid"] = False
                results["errors"].extend(
                    [f"{file_result['filename']}: {error}" for error in file_result["errors"]]
                )
            
            if file_result.get("warnings"):
                results["warnings"].extend(
                    [f"{file_result['filename']}: {warning}" for warning in file_result["warnings"]]
                )
            
            # Aggregate metrics
            if "page_analysis" in file_result and "total_pages" in file_result["page_analysis"]:
                results["total_pages"] += file_result["page_analysis"]["total_pages"]
            elif "metadata" in file_result and "page_count" in file_result["metadata"]:
                results["total_pages"] += file_result["metadata"]["page_count"]
            
            if "processing_estimate" in file_result and "estimated_seconds" in file_result["processing_estimate"]:
                results["total_processing_time_estimate"] += file_result[
                    "processing_estimate"
                ]["estimated_seconds"]
        
        # Convert total time to minutes
        if results["total_processing_time_estimate"] > 0:
            results["total_processing_time_minutes"] = round(
                results["total_processing_time_estimate"] / 60, 1
            )
        
        batch_time = time.time() - batch_start
        logger.info(f"Parallel validation completed in {batch_time:.2f}s for {len(files)} files")
        
        return results
    
    def clear_cache(self):
        """Clear the validation cache."""
        self.validation_cache.clear()
        logger.info("Validation cache cleared")
    
    def __del__(self):
        """Clean up thread pool executor on deletion."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)