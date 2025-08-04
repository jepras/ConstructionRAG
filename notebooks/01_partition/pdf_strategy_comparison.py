# ==============================================================================
# PDF PROCESSING STRATEGY COMPARISON
# Tests multiple approaches: PyMuPDF, Unstructured hi_res, OCR-only, Hybrid
# ==============================================================================

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import logging

# Core libraries
import fitz  # PyMuPDF
from unstructured.partition.pdf import partition_pdf
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
OUTPUT_DIR = Path("../../data/internal/01_partition_data") / f"strategy_comparison_{timestamp}"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"📁 Output directory: {OUTPUT_DIR}")

# ==============================================================================
# STRATEGY IMPLEMENTATIONS
# ==============================================================================

class PDFProcessingStrategies:
    """Collection of different PDF processing strategies"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.temp_dirs = {
            "pymupdf_tables": output_dir / "pymupdf_tables",
            "pymupdf_images": output_dir / "pymupdf_images", 
            "unstructured_tables": output_dir / "unstructured_tables",
            "unstructured_images": output_dir / "unstructured_images",
        }
        
        # Create temp directories
        for temp_dir in self.temp_dirs.values():
            temp_dir.mkdir(exist_ok=True)
    
    def detect_document_type(self, filepath: str) -> Dict[str, Any]:
        """Analyze document to determine best processing strategy"""
        doc = fitz.open(filepath)
        analysis = {
            "total_pages": len(doc),
            "has_selectable_text": False,
            "avg_text_per_page": 0,
            "total_images": 0,
            "total_tables": 0,
            "is_likely_scanned": False,
            "recommended_strategy": "pymupdf"
        }
        
        total_text_length = 0
        total_images = 0
        total_tables = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Check for selectable text
            text = page.get_text()
            if text.strip():
                analysis["has_selectable_text"] = True
                total_text_length += len(text)
            
            # Count images and tables
            images = page.get_images()
            tables = list(page.find_tables())
            
            total_images += len(images)
            total_tables += len(tables)
        
        doc.close()
        
        analysis["avg_text_per_page"] = total_text_length / len(doc) if len(doc) > 0 else 0
        analysis["total_images"] = total_images
        analysis["total_tables"] = total_tables
        
        # Determine if likely scanned
        if analysis["avg_text_per_page"] < 100:  # Very little text per page
            analysis["is_likely_scanned"] = True
            analysis["recommended_strategy"] = "unstructured_ocr"
        elif total_tables > 5 or total_images > 10:  # Complex layout
            analysis["recommended_strategy"] = "unstructured_hi_res"
        else:
            analysis["recommended_strategy"] = "pymupdf"
            
        return analysis
    
    def process_with_pymupdf(self, filepath: str) -> Dict[str, Any]:
        """Process PDF using PyMuPDF only (current approach)"""
        start_time = time.time()
        
        try:
            doc = fitz.open(filepath)
            results = {
                "strategy": "pymupdf",
                "success": True,
                "text_elements": [],
                "table_elements": [],
                "image_elements": [],
                "document_metadata": {},
                "processing_time": 0,
                "error": None
            }
            
            # Extract document metadata
            metadata = doc.metadata
            results["document_metadata"] = {
                "total_pages": len(doc),
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "creation_date": metadata.get("creationDate", ""),
            }
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_index = page_num + 1
                
                # Extract text
                text_dict = page.get_text("dict")
                for block_idx, block in enumerate(text_dict.get("blocks", [])):
                    if "lines" in block:
                        block_text = ""
                        for line in block["lines"]:
                            for span in line.get("spans", []):
                                block_text += span.get("text", "")
                        
                        if block_text.strip():
                            results["text_elements"].append({
                                "id": f"text_page{page_index}_block{block_idx}",
                                "page": page_index,
                                "text": block_text.strip(),
                                "category": "NarrativeText",
                                "length": len(block_text.strip())
                            })
                
                # Extract tables
                table_finder = page.find_tables()
                for table_idx, table in enumerate(table_finder):
                    try:
                        table_text = table.to_markdown()
                        results["table_elements"].append({
                            "id": f"table_page{page_index}_table{table_idx}",
                            "page": page_index,
                            "text": table_text,
                            "category": "Table",
                            "bbox": list(table.bbox),
                            "row_count": len(table.extract()),
                        })
                    except Exception as e:
                        logger.warning(f"Failed to extract table: {e}")
                
                # Count images
                images = page.get_images()
                for img_idx, img in enumerate(images):
                    results["image_elements"].append({
                        "id": f"image_page{page_index}_img{img_idx}",
                        "page": page_index,
                        "category": "Image",
                        "xref": img[0]
                    })
            
            doc.close()
            results["processing_time"] = time.time() - start_time
            
        except Exception as e:
            results = {
                "strategy": "pymupdf",
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "text_elements": [],
                "table_elements": [],
                "image_elements": [],
            }
        
        return results
    
    def process_with_unstructured_hi_res(self, filepath: str) -> Dict[str, Any]:
        """Process PDF using Unstructured hi_res strategy"""
        start_time = time.time()
        
        try:
            elements = partition_pdf(
                filename=filepath,
                strategy="hi_res",
                infer_table_structure=True,
                extract_images_in_pdf=True,
                extract_image_block_types=["Image", "Table"],
                extract_image_block_output_dir=str(self.temp_dirs["unstructured_images"]),
                extract_image_block_to_payload=False,
                chunking_strategy=None,  # No chunking, we'll do that later
                languages=["dan"],  # Danish support
                include_page_breaks=True,
            )
            
            results = {
                "strategy": "unstructured_hi_res", 
                "success": True,
                "text_elements": [],
                "table_elements": [],
                "image_elements": [],
                "processing_time": 0,
                "error": None
            }
            
            # Process elements
            for element in elements:
                element_dict = {
                    "id": getattr(element, 'id', None) or f"element_{len(results['text_elements']) + len(results['table_elements']) + len(results['image_elements'])}",
                    "category": element.category,
                    "text": str(element),
                    "page": getattr(element.metadata, 'page_number', None),
                    "length": len(str(element))
                }
                
                # Add element-specific metadata
                if hasattr(element.metadata, 'text_as_html') and element.metadata.text_as_html:
                    element_dict["html_content"] = element.metadata.text_as_html
                
                if hasattr(element.metadata, 'image_path') and element.metadata.image_path:
                    element_dict["image_path"] = element.metadata.image_path
                
                # Categorize elements
                if element.category in ["Table"]:
                    results["table_elements"].append(element_dict)
                elif element.category in ["Image", "FigureCaption"]:
                    results["image_elements"].append(element_dict)
                else:
                    results["text_elements"].append(element_dict)
            
            results["processing_time"] = time.time() - start_time
            
        except Exception as e:
            results = {
                "strategy": "unstructured_hi_res",
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "text_elements": [],
                "table_elements": [],
                "image_elements": [],
            }
        
        return results
    
    def process_with_unstructured_ocr(self, filepath: str) -> Dict[str, Any]:
        """Process PDF using Unstructured OCR-only strategy"""
        start_time = time.time()
        
        try:
            elements = partition_pdf(
                filename=filepath,
                strategy="ocr_only",
                infer_table_structure=True,
                extract_images_in_pdf=True,
                extract_image_block_types=["Image", "Table"],
                extract_image_block_output_dir=str(self.temp_dirs["unstructured_images"]),
                extract_image_block_to_payload=False,
                chunking_strategy=None,
                languages=["dan"],  # Danish OCR
                include_page_breaks=True,
            )
            
            results = {
                "strategy": "unstructured_ocr",
                "success": True,
                "text_elements": [],
                "table_elements": [],
                "image_elements": [],
                "processing_time": 0,
                "error": None
            }
            
            # Process elements (same logic as hi_res)
            for element in elements:
                element_dict = {
                    "id": getattr(element, 'id', None) or f"element_{len(results['text_elements']) + len(results['table_elements']) + len(results['image_elements'])}",
                    "category": element.category,
                    "text": str(element),
                    "page": getattr(element.metadata, 'page_number', None),
                    "length": len(str(element))
                }
                
                if hasattr(element.metadata, 'text_as_html') and element.metadata.text_as_html:
                    element_dict["html_content"] = element.metadata.text_as_html
                
                if hasattr(element.metadata, 'image_path') and element.metadata.image_path:
                    element_dict["image_path"] = element.metadata.image_path
                
                if element.category in ["Table"]:
                    results["table_elements"].append(element_dict)
                elif element.category in ["Image", "FigureCaption"]:
                    results["image_elements"].append(element_dict)
                else:
                    results["text_elements"].append(element_dict)
            
            results["processing_time"] = time.time() - start_time
            
        except Exception as e:
            results = {
                "strategy": "unstructured_ocr",
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "text_elements": [],
                "table_elements": [],
                "image_elements": [],
            }
        
        return results
    
    def process_with_hybrid(self, filepath: str) -> Dict[str, Any]:
        """Hybrid approach: detect document type and choose best strategy"""
        start_time = time.time()
        
        try:
            # First, analyze the document
            doc_analysis = self.detect_document_type(filepath)
            recommended_strategy = doc_analysis["recommended_strategy"]
        
            # Process with recommended strategy
            if recommended_strategy == "unstructured_ocr":
                processing_result = self.process_with_unstructured_ocr(filepath)
            elif recommended_strategy == "unstructured_hi_res":
                processing_result = self.process_with_unstructured_hi_res(filepath)
            else:
                processing_result = self.process_with_pymupdf(filepath)
            
            # Add hybrid metadata
            processing_result["strategy"] = "hybrid"
            processing_result["hybrid_analysis"] = doc_analysis
            processing_result["chosen_strategy"] = recommended_strategy
            processing_result["total_processing_time"] = time.time() - start_time
            
            return processing_result
            
        except Exception as e:
            return {
                "strategy": "hybrid",
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "text_elements": [],
                "table_elements": [],
                "image_elements": [],
            }

# ==============================================================================
# MAIN PROCESSING LOOP
# ==============================================================================

def run_comparison():
    """Run comparison across all strategies and files"""
    
    processor = PDFProcessingStrategies(OUTPUT_DIR)
    
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
        
        file_results = {
            "filename": filename,
            "filepath": str(filepath),
            "file_size_mb": filepath.stat().st_size / (1024 * 1024),
            "strategies": {}
        }
        
        # Test each strategy
        strategies = [
            ("pymupdf", processor.process_with_pymupdf),
            ("unstructured_hi_res", processor.process_with_unstructured_hi_res),
            ("unstructured_ocr", processor.process_with_unstructured_ocr),
            ("hybrid", processor.process_with_hybrid),
        ]
        
        for strategy_name, strategy_func in strategies:
            print(f"  Testing {strategy_name}...")
            try:
                result = strategy_func(str(filepath))
                file_results["strategies"][strategy_name] = result
                
                # Print summary
                if result["success"]:
                    print(f"    ✅ {len(result['text_elements'])} text, {len(result['table_elements'])} tables, {len(result['image_elements'])} images ({result['processing_time']:.1f}s)")
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
    output_file = OUTPUT_DIR / "strategy_comparison_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Results saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    
    for filename, file_result in comparison_results["results"].items():
        print(f"\n📄 {filename}:")
        print(f"   File size: {file_result['file_size_mb']:.1f} MB")
        
        for strategy_name, strategy_result in file_result["strategies"].items():
            if strategy_result["success"]:
                text_count = len(strategy_result["text_elements"])
                table_count = len(strategy_result["table_elements"])
                image_count = len(strategy_result["image_elements"])
                time_taken = strategy_result["processing_time"]
                
                print(f"   {strategy_name:20}: {text_count:3d} text, {table_count:2d} tables, {image_count:2d} images ({time_taken:5.1f}s)")
                
                # Show hybrid decision if applicable
                if strategy_name == "hybrid" and "chosen_strategy" in strategy_result:
                    chosen = strategy_result["chosen_strategy"]
                    analysis = strategy_result.get("hybrid_analysis", {})
                    is_scanned = analysis.get("is_likely_scanned", False)
                    avg_text = analysis.get("avg_text_per_page", 0)
                    print(f"                        → Chose {chosen} (scanned: {is_scanned}, avg_text_per_page: {avg_text:.0f})")
            else:
                print(f"   {strategy_name:20}: ❌ FAILED - {strategy_result['error']}")
    
    return comparison_results

# ==============================================================================
# RUN THE COMPARISON
# ==============================================================================

if __name__ == "__main__":
    print("🚀 Starting PDF Processing Strategy Comparison")
    print(f"📂 Looking for PDFs in: {PDF_SOURCE_DIR}")
    print(f"🎯 Test files: {TEST_FILES}")
    
    results = run_comparison()
    
    print(f"\n✅ Comparison complete! Check {OUTPUT_DIR} for detailed results.")