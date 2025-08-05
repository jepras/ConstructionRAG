# Partition.py Analysis: Hybrid Partition System

## Overview
The `partition.py` file implements a sophisticated hybrid PDF partitioning system that automatically detects document types and applies the optimal processing strategy for maximum accuracy and performance.

## Core Architecture

### 1. **Main Class: `PartitionStep`**
- Extends `PipelineStep` (base class for all pipeline steps)
- Handles both regular and scanned document processing
- Implements hybrid detection and strategy selection

### 2. **Key Components**

#### **Document Type Detection** (`_detect_document_type`)
```python
def _detect_document_type(self, filepath: str) -> Dict[str, Any]:
```
- **Purpose**: Analyzes PDF to determine if it's scanned or regular
- **Method**: Uses PyMuPDF to extract text from first 3 pages
- **Threshold**: < 25 characters per page = likely scanned
- **Output**: Returns analysis with confidence score

#### **Hybrid Processing Pipeline** (`_partition_document_hybrid`)
```python
async def _partition_document_hybrid(self, filepath: str, document_input: DocumentInput):
```
- **Step 1**: Detect document type using `_detect_document_type`
- **Step 2**: Choose processing strategy:
  - **Scanned documents**: Use Unstructured `hi_res` strategy
  - **Regular documents**: Use PyMuPDF (fast processing)
- **Step 3**: Execute chosen strategy
- **Step 4**: Add hybrid detection metadata to results

### 3. **Processing Strategies**

#### **Strategy A: Unstructured Hi-Res** (`_process_with_unstructured`)
- **When**: Document detected as scanned
- **Method**: Uses `unstructured.partition.pdf` with `hi_res` strategy
- **Features**: 
  - OCR for text extraction
  - Table structure inference
  - Image extraction
  - Danish language support
- **Output**: Normalized to match PyMuPDF format

#### **Strategy B: PyMuPDF** (`_partition_document_async`)
- **When**: Document has selectable text
- **Method**: Uses PyMuPDF for fast processing
- **Features**:
  - Fast text extraction
  - Table detection
  - Image extraction
  - Maintains current performance

### 4. **Unified Partitioner V2** (`UnifiedPartitionerV2`)

This is the core processing engine that handles the actual PDF analysis:

#### **Stage 1: PyMuPDF Analysis** (`stage1_pymupdf_analysis`)
```python
def stage1_pymupdf_analysis(self, filepath):
```
- **Purpose**: Detect tables, images, and page complexity
- **Output**: Page analysis, table locations, image locations
- **Complexity Detection**:
  - `text_only`: No images/tables
  - `simple`: 1-2 images
  - `complex`: 3+ images
  - `fragmented`: Many small images

#### **Stage 2: Fast Text Extraction** (`stage2_fast_text_extraction`)
```python
def stage2_fast_text_extraction(self, filepath):
```
- **Purpose**: Extract text elements using PyMuPDF
- **Method**: Uses `page.get_text("dict")` for detailed metadata
- **Output**: Text elements with font info, categories
- **Categories**: Title, ListItem, NarrativeText

#### **Stage 3: Targeted Table Processing** (`stage3_targeted_table_processing`)
```python
def stage3_targeted_table_processing(self, filepath, table_locations):
```
- **Purpose**: Process detected tables
- **Method**: Extract tables as images + text
- **Output**: Enhanced table elements with HTML
- **Features**: Table-to-HTML conversion, image extraction

#### **Stage 4: Full Page Extraction** (`stage4_full_page_extraction`)
```python
def stage4_full_page_extraction(self, filepath, page_analysis):
```
- **Purpose**: Extract full pages when images detected
- **Method**: Uses PyMuPDF pixmap extraction
- **DPI Selection**: Based on page complexity
- **Output**: Full page images for storage

### 5. **Output Normalization**

#### **Unstructured Output** (`_normalize_unstructured_output`)
- **Purpose**: Convert Unstructured elements to standard format
- **Process**: Maps Unstructured elements to PyMuPDF schema
- **Features**: Preserves metadata, categorizes elements
- **Integration**: Adds full page extraction for images

#### **Post-Processing** (`_post_process_results_async`)
- **Purpose**: Clean and upload results
- **Steps**:
  1. Filter text elements (remove tiny fragments)
  2. Clean metadata
  3. Upload images to Supabase Storage
  4. Prepare final result structure

### 6. **Key Features**

#### **Smart Detection**
- Analyzes text density per page
- Uses confidence scoring
- Fallback to PyMuPDF if Unstructured fails

#### **Performance Optimization**
- Regular docs: Fast PyMuPDF processing
- Scanned docs: Accurate Unstructured processing
- Async image uploads to avoid blocking

#### **Storage Integration**
- Uploads extracted pages to Supabase Storage
- Maintains file structure and metadata
- Handles both table and page images

#### **Error Handling**
- Graceful fallback between strategies
- Comprehensive logging
- Cleanup of temporary files

### 7. **Data Flow**

```
Input PDF → Document Detection → Strategy Selection → Processing → Normalization → Storage Upload → Final Result
```

#### **For Regular Documents**:
```
PDF → PyMuPDF Analysis → Text Extraction → Table Processing → Page Extraction → Storage → Result
```

#### **For Scanned Documents**:
```
PDF → Unstructured Hi-Res → OCR Processing → Output Normalization → PyMuPDF Page Extraction → Storage → Result
```

### 8. **Configuration**

The system uses configuration from `indexing_config.yaml`:
- `scanned_detection.text_threshold`: 25 chars/page
- `ocr_languages`: ["dan"] (Danish)
- `extract_tables`: True
- `extract_images`: True

### 9. **Expected Results**

#### **Regular Documents**:
- Processing time: < 3 seconds
- Text elements: ~66 elements
- Tables: ~1 table
- Full pages: Based on image count

#### **Scanned Documents**:
- Processing time: ~24 seconds
- Text elements: ~130+ elements (vs 8 with PyMuPDF only)
- Tables: ~2 accurate tables (vs 9 false positives)
- Full pages: All pages with content

### 10. **Integration Points**

- **Upstream**: Receives `DocumentInput` from orchestrator
- **Downstream**: Provides `StepResult` to metadata step
- **Storage**: Uploads images to Supabase Storage
- **Progress**: Reports progress through `progress_tracker`

This hybrid system provides the best of both worlds: fast processing for regular documents and accurate extraction for scanned documents, all while maintaining compatibility with the existing pipeline architecture. 