# ==============================================================================
# PYMUPDF-ONLY PDF PROCESSING COMPARISON
# Tests different PyMuPDF approaches without unstructured dependencies
# Safe to run in production venv
# ==============================================================================

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import logging

# Core libraries (already in your venv)
import fitz  # PyMuPDF
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Test files - add your problematic PDFs here
TEST_FILES = [
    "test-with-little-variety.pdf",  # Original test file
    "small-complicated/I12727-01_K07_C08.01 Appendiks EL copy.pdf",
    "small-complicated/MOL_K07_C08_ARB_EL - EL arbejdsbeskrivelse copy.pdf", 
    "small-complicated/Tegninger samlet  copy.pdf",
]

# Source directory
PDF_SOURCE_DIR = Path("../../data/external/construction_pdfs")

# Output directory
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = Path("../../data/internal/01_partition_data") / f"pymupdf_comparison_{timestamp}"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"📁 Output directory: {OUTPUT_DIR}")

# ==============================================================================
# PYMUPDF STRATEGIES
# ==============================================================================

class PyMuPDFStrategies:
    """Different PyMuPDF processing approaches"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.images_dir = output_dir / "extracted_images"
        self.tables_dir = output_dir / "extracted_tables"
        self.images_dir.mkdir(exist_ok=True)
        self.tables_dir.mkdir(exist_ok=True)
    
    def analyze_document_characteristics(self, filepath: str) -> Dict[str, Any]:
        """Analyze document to understand its characteristics"""
        doc = fitz.open(filepath)
        analysis = {
            "total_pages": len(doc),
            "has_selectable_text": False,
            "text_density": [],  # Text per page
            "image_density": [],  # Images per page
            "table_density": [],  # Tables per page
            "font_analysis": {},
            "is_likely_scanned": False,
            "complexity_assessment": "unknown"
        }
        
        total_text_chars = 0
        total_images = 0
        total_tables = 0
        font_sizes = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Text analysis
            text = page.get_text()
            text_length = len(text.strip())
            analysis["text_density"].append(text_length)
            total_text_chars += text_length
            
            if text.strip():
                analysis["has_selectable_text"] = True
            
            # Image analysis
            images = page.get_images()
            analysis["image_density"].append(len(images))
            total_images += len(images)
            
            # Table analysis
            tables = list(page.find_tables())
            analysis["table_density"].append(len(tables))
            total_tables += len(tables)
            
            # Font analysis
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line.get("spans", []):
                            font_sizes.append(span.get("size", 0))
        
        # Calculate averages before closing document
        page_count = len(doc)
        avg_text_per_page = total_text_chars / page_count if page_count > 0 else 0
        avg_images_per_page = total_images / page_count if page_count > 0 else 0
        avg_tables_per_page = total_tables / page_count if page_count > 0 else 0
        
        doc.close()
        
        analysis["averages"] = {
            "text_per_page": avg_text_per_page,
            "images_per_page": avg_images_per_page,
            "tables_per_page": avg_tables_per_page
        }
        
        # Font analysis
        if font_sizes:
            analysis["font_analysis"] = {
                "avg_font_size": sum(font_sizes) / len(font_sizes),
                "min_font_size": min(font_sizes),
                "max_font_size": max(font_sizes),
                "font_variety": len(set(font_sizes))
            }
        
        # Determine if likely scanned
        if avg_text_per_page < 100:  # Very little selectable text
            analysis["is_likely_scanned"] = True
            analysis["complexity_assessment"] = "scanned_document"
        elif avg_tables_per_page > 2 or avg_images_per_page > 3:
            analysis["complexity_assessment"] = "complex_layout"
        elif avg_text_per_page > 1000:
            analysis["complexity_assessment"] = "text_heavy"
        else:
            analysis["complexity_assessment"] = "simple_document"
            
        return analysis
    
    def basic_text_extraction(self, filepath: str) -> Dict[str, Any]:
        """Basic PyMuPDF text extraction (get_text())"""
        start_time = time.time()
        
        try:
            doc = fitz.open(filepath)
            results = {
                "strategy": "pymupdf_basic_text",
                "success": True,
                "text_elements": [],
                "total_text_length": 0,
                "processing_time": 0,
                "error": None
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                if text.strip():
                    results["text_elements"].append({
                        "page": page_num + 1,
                        "text": text,
                        "length": len(text),
                        "method": "get_text"
                    })
                    results["total_text_length"] += len(text)
            
            doc.close()
            results["processing_time"] = time.time() - start_time
            
        except Exception as e:
            results = {
                "strategy": "pymupdf_basic_text",
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
        
        return results
    
    def structured_text_extraction(self, filepath: str) -> Dict[str, Any]:
        """Structured PyMuPDF text extraction (get_text('dict'))"""
        start_time = time.time()
        
        try:
            doc = fitz.open(filepath)
            results = {
                "strategy": "pymupdf_structured",
                "success": True,
                "text_elements": [],
                "block_count": 0,
                "processing_time": 0,
                "error": None
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_dict = page.get_text("dict")
                
                for block_idx, block in enumerate(text_dict.get("blocks", [])):
                    if "lines" in block:
                        block_text = ""
                        font_info = []
                        
                        for line in block["lines"]:
                            for span in line.get("spans", []):
                                span_text = span.get("text", "")
                                block_text += span_text
                                if span_text.strip():
                                    font_info.append({
                                        "font": span.get("font", ""),
                                        "size": span.get("size", 0),
                                        "flags": span.get("flags", 0)
                                    })
                        
                        if block_text.strip():
                            results["text_elements"].append({
                                "id": f"page{page_num + 1}_block{block_idx}",
                                "page": page_num + 1,
                                "text": block_text.strip(),
                                "length": len(block_text.strip()),
                                "bbox": block.get("bbox", []),
                                "font_info": font_info,
                                "method": "get_text_dict"
                            })
                            results["block_count"] += 1
            
            doc.close()
            results["processing_time"] = time.time() - start_time
            
        except Exception as e:
            results = {
                "strategy": "pymupdf_structured",
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
        
        return results
    
    def table_focused_extraction(self, filepath: str) -> Dict[str, Any]:
        """PyMuPDF with focus on table extraction"""
        start_time = time.time()
        
        try:
            doc = fitz.open(filepath)
            results = {
                "strategy": "pymupdf_table_focused",
                "success": True,
                "text_elements": [],
                "table_elements": [],
                "table_images_saved": [],
                "processing_time": 0,
                "error": None
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Basic text extraction
                text = page.get_text()
                if text.strip():
                    results["text_elements"].append({
                        "page": page_num + 1,
                        "text": text,
                        "length": len(text)
                    })
                
                # Table extraction with images
                table_finder = page.find_tables()
                for table_idx, table in enumerate(table_finder):
                    try:
                        # Extract table data
                        table_data = table.extract()
                        table_text = table.to_markdown()
                        
                        # Save table as image
                        table_bbox = table.bbox
                        table_rect = fitz.Rect(table_bbox)
                        matrix = fitz.Matrix(2, 2)  # 2x zoom for clarity
                        pixmap = page.get_pixmap(matrix=matrix, clip=table_rect)
                        
                        filename = f"page{page_num + 1:02d}_table{table_idx + 1}.png"
                        save_path = self.tables_dir / filename
                        pixmap.save(str(save_path))
                        
                        results["table_elements"].append({
                            "id": f"table_page{page_num + 1}_table{table_idx}",
                            "page": page_num + 1,
                            "text": table_text,
                            "row_count": len(table_data),
                            "col_count": len(table_data[0]) if table_data else 0,
                            "bbox": list(table_bbox),
                            "image_path": str(save_path),
                            "image_filename": filename
                        })
                        
                        results["table_images_saved"].append(str(save_path))
                        
                    except Exception as e:
                        logger.warning(f"Failed to process table {table_idx} on page {page_num + 1}: {e}")
            
            doc.close()
            results["processing_time"] = time.time() - start_time
            
        except Exception as e:
            results = {
                "strategy": "pymupdf_table_focused",
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
        
        return results
    
    def image_analysis_extraction(self, filepath: str) -> Dict[str, Any]:
        """PyMuPDF with image analysis and full page extraction for complex pages"""
        start_time = time.time()
        
        try:
            doc = fitz.open(filepath)
            results = {
                "strategy": "pymupdf_image_analysis",
                "success": True,
                "text_elements": [],
                "image_elements": [],
                "extracted_pages": [],
                "processing_time": 0,
                "error": None
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Analyze page complexity
                images = page.get_images()
                tables = list(page.find_tables())
                text = page.get_text()
                
                page_complexity = "simple"
                if len(images) > 5 or len(tables) > 2:
                    page_complexity = "complex"
                elif len(images) > 0 or len(tables) > 0:
                    page_complexity = "moderate"
                
                # Extract text
                if text.strip():
                    results["text_elements"].append({
                        "page": page_num + 1,
                        "text": text,
                        "length": len(text),
                        "complexity": page_complexity
                    })
                
                # Analyze images
                for img_idx, img in enumerate(images):
                    try:
                        # Get image info
                        base_image = doc.extract_image(img[0])
                        results["image_elements"].append({
                            "page": page_num + 1,
                            "image_index": img_idx,
                            "width": base_image["width"],
                            "height": base_image["height"],
                            "ext": base_image["ext"],
                            "size_bytes": len(base_image["image"])
                        })
                    except Exception as e:
                        logger.warning(f"Could not analyze image {img_idx} on page {page_num + 1}: {e}")
                
                # Extract full page if complex
                if page_complexity in ["complex", "moderate"]:
                    try:
                        if page_complexity == "complex":
                            matrix = fitz.Matrix(3, 3)  # High DPI for complex pages
                        else:
                            matrix = fitz.Matrix(2, 2)  # Standard DPI
                        
                        pixmap = page.get_pixmap(matrix=matrix)
                        filename = f"page{page_num + 1:02d}_{page_complexity}.png"
                        save_path = self.images_dir / filename
                        pixmap.save(str(save_path))
                        
                        results["extracted_pages"].append({
                            "page": page_num + 1,
                            "complexity": page_complexity,
                            "image_path": str(save_path),
                            "image_filename": filename,
                            "width": pixmap.width,
                            "height": pixmap.height,
                            "dpi": int(matrix.a * 72)
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num + 1}: {e}")
            
            doc.close()
            results["processing_time"] = time.time() - start_time
            
        except Exception as e:
            results = {
                "strategy": "pymupdf_image_analysis",
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
        
        return results

# ==============================================================================
# MAIN COMPARISON FUNCTION
# ==============================================================================

def run_pymupdf_comparison():
    """Run PyMuPDF strategy comparison"""
    
    processor = PyMuPDFStrategies(OUTPUT_DIR)
    
    comparison_results = {
        "run_timestamp": datetime.now().isoformat(),
        "output_directory": str(OUTPUT_DIR),
        "test_files": TEST_FILES,
        "results": {}
    }
    
    for filename in TEST_FILES:
        filepath = PDF_SOURCE_DIR / filename
        
        if not filepath.exists():
            print(f"❌ File not found: {filepath}")
            continue
            
        print(f"\n🔄 Processing: {filename}")
        
        # First, analyze document characteristics
        doc_analysis = processor.analyze_document_characteristics(str(filepath))
        
        file_results = {
            "filename": filename,
            "filepath": str(filepath),
            "file_size_mb": filepath.stat().st_size / (1024 * 1024),
            "document_analysis": doc_analysis,
            "strategies": {}
        }
        
        print(f"   📊 Analysis: {doc_analysis['complexity_assessment']} "
              f"({doc_analysis['averages']['text_per_page']:.0f} chars/page, "
              f"{doc_analysis['averages']['tables_per_page']:.1f} tables/page)")
        
        # Test each PyMuPDF strategy
        strategies = [
            ("basic_text", processor.basic_text_extraction),
            ("structured", processor.structured_text_extraction),
            ("table_focused", processor.table_focused_extraction),
            ("image_analysis", processor.image_analysis_extraction),
        ]
        
        for strategy_name, strategy_func in strategies:
            print(f"  Testing {strategy_name}...")
            try:
                result = strategy_func(str(filepath))
                file_results["strategies"][strategy_name] = result
                
                # Print summary
                if result["success"]:
                    if "text_elements" in result:
                        text_count = len(result["text_elements"])
                        print(f"    ✅ {text_count} text elements ({result['processing_time']:.1f}s)")
                    
                    if "table_elements" in result and result["table_elements"]:
                        table_count = len(result["table_elements"])
                        print(f"       {table_count} tables extracted")
                    
                    if "extracted_pages" in result and result["extracted_pages"]:
                        page_count = len(result["extracted_pages"])
                        print(f"       {page_count} pages extracted as images")
                        
                else:
                    print(f"    ❌ Failed: {result['error']}")
                    
            except Exception as e:
                print(f"    ❌ Exception: {e}")
                file_results["strategies"][strategy_name] = {
                    "strategy": strategy_name,
                    "success": False,
                    "error": str(e),
                    "processing_time": 0
                }
        
        comparison_results["results"][filename] = file_results
    
    # Save results
    output_file = OUTPUT_DIR / "pymupdf_comparison_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Results saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("PYMUPDF COMPARISON SUMMARY")
    print("="*80)
    
    for filename, file_result in comparison_results["results"].items():
        print(f"\n📄 {filename}:")
        print(f"   File size: {file_result['file_size_mb']:.1f} MB")
        
        analysis = file_result["document_analysis"]
        print(f"   Document type: {analysis['complexity_assessment']}")
        print(f"   Avg text/page: {analysis['averages']['text_per_page']:.0f} chars")
        print(f"   Avg tables/page: {analysis['averages']['tables_per_page']:.1f}")
        print(f"   Likely scanned: {analysis['is_likely_scanned']}")
        
        for strategy_name, strategy_result in file_result["strategies"].items():
            if strategy_result["success"]:
                time_taken = strategy_result["processing_time"]
                print(f"   {strategy_name:15}: ✅ ({time_taken:5.1f}s)", end="")
                
                if "text_elements" in strategy_result:
                    print(f" - {len(strategy_result['text_elements'])} text elements", end="")
                if "table_elements" in strategy_result:
                    print(f" - {len(strategy_result['table_elements'])} tables", end="")
                if "extracted_pages" in strategy_result:
                    print(f" - {len(strategy_result['extracted_pages'])} page images", end="")
                print()
            else:
                print(f"   {strategy_name:15}: ❌ FAILED - {strategy_result['error']}")
    
    return comparison_results

# ==============================================================================
# RUN THE COMPARISON
# ==============================================================================

if __name__ == "__main__":
    print("🚀 Starting PyMuPDF Strategy Comparison")
    print(f"📂 Looking for PDFs in: {PDF_SOURCE_DIR}")
    print(f"🎯 Test files: {TEST_FILES}")
    
    results = run_pymupdf_comparison()
    
    print(f"\n✅ Comparison complete! Check {OUTPUT_DIR} for detailed results and extracted images/tables.")