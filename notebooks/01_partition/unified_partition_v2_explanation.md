# Unified PDF Partitioning V2: Step-by-Step Explanation

## Overview

The `unified_partition_v2.py` file implements an advanced PDF processing pipeline that combines multiple strategies to extract text, tables, and images from construction-related PDF documents. This approach uses PyMuPDF for initial analysis and detection, followed by targeted processing with the unstructured library.

## Architecture

The pipeline follows a 4-stage approach:

1. **Stage 1**: PyMuPDF Analysis - Detect tables and images
2. **Stage 2**: Fast Text Extraction - Extract text content efficiently
3. **Stage 3**: Targeted Table Processing - Enhanced table extraction with vision
4. **Stage 4**: Full Page Extraction - Extract complex pages as images

## Configuration Setup

### Directory Structure
```python
# Creates timestamped output directories
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_BASE_DIR = Path("../../data/internal/01_partition_data")
CURRENT_RUN_DIR = OUTPUT_BASE_DIR / f"unified_v2_run_{timestamp}"
TABLES_DIR = CURRENT_RUN_DIR / "tables"
IMAGES_DIR = CURRENT_RUN_DIR / "images"
```

### Processing Options
- `INCLUDE_COORDINATES = True` - Include coordinate metadata (though later removed)
- `OCR_LANGUAGES = ["dan"]` - Danish language support for OCR
- `FILES_TO_PROCESS` - List of PDF files to process

## Stage 1: PyMuPDF Analysis (`stage1_pymupdf_analysis`)

### Purpose
Analyze each page to detect tables and images, determine page complexity, and decide which pages need full extraction.

### Step-by-Step Process

1. **Open PDF Document**
   ```python
   doc = fitz.open(filepath)
   ```

2. **Iterate Through Pages**
   - For each page, get images and tables using PyMuPDF's built-in detection
   - Images: `page.get_images()`
   - Tables: `page.find_tables()`

3. **Analyze Page Complexity**
   ```python
   # Determine if page is fragmented (many small images)
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
   ```

4. **Classify Page Complexity**
   - `text_only`: No images or tables
   - `fragmented`: Many small images (likely diagrams)
   - `complex`: 3+ images
   - `simple`: 1-2 images

5. **Store Analysis Results**
   ```python
   page_analysis[page_index] = {
       "image_count": len(images),
       "table_count": len(tables),
       "complexity": complexity,
       "needs_extraction": needs_extraction,
       "is_fragmented": is_fragmented,
   }
   ```

6. **Record Table and Image Locations**
   - Store bounding boxes and metadata for each detected element
   - Assign unique IDs (e.g., `table_page1_table0`, `image_page2_img1`)

### Output
- `page_analysis`: Dictionary of page complexity and extraction needs
- `table_locations`: List of detected tables with metadata
- `image_locations`: List of detected images with metadata

## Stage 2: Fast Text Extraction (`stage2_fast_text_extraction`)

### Purpose
Extract text content efficiently using unstructured's fast strategy, avoiding the overhead of vision-based processing.

### Step-by-Step Process

1. **Fast PDF Partitioning**
   ```python
   fast_elements = partition_pdf(
       filename=filepath,
       strategy="fast",
       max_characters=50000,
       combine_text_under_n_chars=200,
       include_metadata=True,
       include_page_breaks=True,
   )
   ```

2. **Filter and Process Elements**
   - Exclude tables and images (handled separately)
   - Remove coordinate metadata (not needed for text)
   - Extract text content and metadata

3. **Create Text Elements**
   ```python
   text_elements.append({
       "id": element_id,
       "element": element,
       "category": category,
       "page": page_num,
       "text": getattr(element, "text", ""),
       "metadata": metadata_dict,
   })
   ```

### Output
- List of text elements with full content and metadata

## Stage 3: Targeted Table Processing (`stage3_targeted_table_processing`)

### Purpose
Use vision-based processing specifically for detected tables to get enhanced table structure and content.

### Step-by-Step Process

1. **Check for Tables**
   - Skip if no tables were detected in Stage 1

2. **Vision-Based Table Extraction**
   ```python
   table_elements = partition_pdf(
       filename=filepath,
       strategy="hi_res",
       languages=OCR_LANGUAGES,
       extract_images_in_pdf=True,
       extract_image_block_types=["Table"],
       extract_image_block_output_dir=str(self.tables_dir),
       extract_image_block_to_payload=False,
       infer_table_structure=True,
       pdf_infer_table_structure=True,
   )
   ```

3. **Filter Table Elements**
   - Keep only elements with category "Table"
   - Store enhanced table data with structure information

4. **Cleanup Extracted Files**
   - Remove figure files (keep only table files)
   - Clean up temporary extraction artifacts

### Output
- List of enhanced table elements with structure information

## Stage 4: Full Page Extraction (`stage4_full_page_extraction`)

### Purpose
Extract complex pages as high-resolution images for visual analysis or when text extraction is insufficient.

### Step-by-Step Process

1. **Identify Pages for Extraction**
   ```python
   pages_to_extract = {
       page_num: info
       for page_num, info in page_analysis.items()
       if info["needs_extraction"]
   }
   ```

2. **Determine Resolution Based on Complexity**
   ```python
   if info["is_fragmented"]:
       matrix = fitz.Matrix(3, 3)  # Higher DPI for fragmented
   elif info["complexity"] == "complex":
       matrix = fitz.Matrix(2, 2)  # Standard high DPI
   else:
       matrix = fitz.Matrix(1.5, 1.5)  # Lower DPI for simple
   ```

3. **Extract and Save Pages**
   ```python
   pixmap = page.get_pixmap(matrix=matrix)
   filename = f"{pdf_basename}_page{page_num:02d}_{info['complexity']}.png"
   save_path = self.images_dir / filename
   pixmap.save(str(save_path))
   ```

4. **Store Extraction Metadata**
   ```python
   extracted_pages[page_num] = {
       "filepath": str(save_path),
       "filename": filename,
       "width": pixmap.width,
       "height": pixmap.height,
       "dpi": int(matrix.a * 72),
       "complexity": info["complexity"],
       "original_image_count": info["image_count"],
       "original_table_count": info["table_count"],
   }
   ```

### Output
- Dictionary of extracted page images with metadata

## Data Combination and Cleaning

### Purpose
Combine all stage results into a unified data structure, removing non-serializable objects.

### Process

1. **Clean Non-Serializable Objects**
   ```python
   def clean_for_pickle(obj):
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
   ```

2. **Combine All Results**
   ```python
   combined_data = {
       "text_elements": text_elements,
       "table_elements": enhanced_tables,
       "extracted_pages": extracted_pages,
       "table_locations": clean_for_pickle(stage1_results["table_locations"]),
       "image_locations": clean_for_pickle(stage1_results["image_locations"]),
       "page_analysis": stage1_results["page_analysis"],
       "metadata": { ... },
   }
   ```

## Output Generation

### Pickle Output
- Complete data structure with all elements and metadata
- Used for data transfer between processing stages

### JSON Output
- Human-readable metadata and summaries
- Full text content for easy inspection
- Simplified structure for analysis

### File Structure
```
unified_v2_run_YYYYMMDD_HHMMSS/
├── tables/                    # Extracted table images
├── images/                    # Full page extractions
├── unified_v2_partition_output.pkl    # Complete data
└── unified_v2_partition_output.json   # Human-readable metadata
```

## Key Features

### Adaptive Processing
- Different strategies based on page complexity
- Efficient processing for text-only pages
- High-resolution extraction for complex pages

### Comprehensive Detection
- PyMuPDF for initial table/image detection
- Vision-based enhancement for tables
- Full page extraction for complex layouts

### Flexible Output
- Multiple output formats (pickle, JSON)
- Metadata preservation
- Clean serialization

### Error Handling
- Graceful fallbacks for image processing
- Exception handling for file operations
- Robust cleanup procedures

## Usage Example

```python
# Process a single PDF file
filepath = "path/to/document.pdf"
combined_data = process_pdf_unified_v2(filepath)

# Access results
text_elements = combined_data["text_elements"]
table_elements = combined_data["table_elements"]
extracted_pages = combined_data["extracted_pages"]
page_analysis = combined_data["page_analysis"]
```

## Performance Considerations

- **Fast Strategy**: Used for text extraction to avoid vision overhead
- **Targeted Vision**: Only applied to detected tables
- **Adaptive Resolution**: Higher DPI only for complex pages
- **Selective Extraction**: Only extract pages that need it

This approach balances accuracy, performance, and resource usage while providing comprehensive PDF analysis capabilities. 