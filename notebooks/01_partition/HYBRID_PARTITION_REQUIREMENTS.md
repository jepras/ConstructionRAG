# Hybrid PDF Partition System Requirements

## Overview
Implement an intelligent hybrid PDF partitioning system that automatically detects document types and applies the optimal processing strategy for maximum accuracy and performance.

## Current System Analysis
Based on comprehensive testing, we've identified clear performance and accuracy trade-offs:

### Performance Comparison (MOL_K07_C08_ARB_EL - 3 pages, scanned):
| Strategy | Text | Tables | Images | Full Pages | Duration | Page Coverage |
|----------|------|--------|--------|------------|----------|---------------|
| **PyMuPDF** | 8 | 0 | 3 | 2 | 0.8s | Pages 4-5 only ❌ |
| **Unstructured Fast** | 31 | 0 | 0 | 0 | 1.5s | Pages 4-5 only ❌ |
| **Unstructured Hi-res** | 127 | 2 | 3 | 0 | 24.5s | All pages 1-5 ✅ |
| **Unstructured OCR** | 140 | 0 | 0 | 0 | 20.9s | All pages 1-5 ✅ |

**Key Finding**: PyMuPDF completely fails on scanned documents (misses 60% of pages), while Unstructured Hi-res provides accurate table detection and full page coverage.

## Requirements

### 1. Document Type Detection
Create a document analysis function that determines:
- **Is document scanned?** (minimal selectable text per page)
- **Detection criteria**: 
  - Average text characters per page < 100 = likely scanned
  - Check first 3 pages for representative analysis
  - Use PyMuPDF's fast text extraction for detection

### 2. Hybrid Processing Strategy

#### Strategy A: Scanned Documents
**When**: Document is detected as scanned
**Process**:
1. Use **Unstructured Hi-res** for extracting all text, but use **PyMuPDF** for full page image extraction when pages contain images/tables. Ideal if we can avoid extracting images that are duplicate like company logos that sometimes are on each page. 
2. Preserve all Unstructured element metadata and structure

#### Strategy B: Regular Documents  
**When**: Document has selectable text
**Process**:
1. Use current **PyMuPDF** implementation as-is (with text extraction and extracting images/tables as full pages)
2. Keep existing table detection and image extraction logic
3. Maintain current performance characteristics

### 3. Output Normalization
**Critical**: The two strategies produce different output formats that must be harmonized for downstream processing. 

#### Required Output Schema (EXACT COMPATIBILITY):
**CRITICAL**: Must maintain exact compatibility with current StepResult.data structure that downstream steps expect.

**Current StepResult.data structure (DO NOT CHANGE):**
```python
StepResult(
    step="partition",
    status="completed",
    duration_seconds=duration,
    summary_stats={...},  # Used for reporting only
    sample_outputs={...}, # Used for debugging only
    data={
        "text_elements": [
            {
                "id": str,
                "category": str,  # NarrativeText, Title, Table, etc.  
                "page": int,
                "text": str,
                "metadata": dict  # Current format must be preserved
            }
        ],
        "table_elements": [
            {
                "id": str,
                "category": str,
                "page": int,
                "text": str,
                "metadata": dict  # Must include text_as_html if available
            }
        ],
        "extracted_pages": dict,  # Current format: {page_num: page_info}
        "page_analysis": dict,    # Current format: {page_num: analysis}
        "document_metadata": dict, # Current format with title, total_pages, etc.
        "metadata": dict         # Current processing metadata
    }
)
```

**Key Compatibility Requirements:**
1. **Exact field names**: `text_elements`, `table_elements`, `extracted_pages`, `page_analysis`, `document_metadata`, `metadata`
2. **Element structure**: Each element must have `id`, `category`, `page`, `text`, `metadata` 
3. **Metadata step expects**: Elements with these exact fields and structure
4. **No new top-level fields**: Don't add `strategy_used` or other new fields to `data`
5. **Strategy info**: Add to existing `metadata.processing_strategy` field only

#### Output Normalization Implementation:
```python
def _normalize_unstructured_to_current_format(self, unstructured_elements, strategy="unstructured_hi_res"):
    """Convert Unstructured output to match current PyMuPDF format exactly"""
    
    text_elements = []
    table_elements = []
    
    for element in unstructured_elements:
        # Convert to exact current format
        normalized_element = {
            "id": getattr(element, 'id', f"element_{len(text_elements + table_elements)}"),
            "category": element.category,  # Keep Unstructured categories
            "page": getattr(element.metadata, 'page_number', None),
            "text": str(element),
            "metadata": {
                "page_number": getattr(element.metadata, 'page_number', None),
                "filename": getattr(element.metadata, 'filename', None),
                # Add text_as_html for tables if available
                "text_as_html": getattr(element.metadata, 'text_as_html', None),
                # Preserve other Unstructured metadata as needed
            }
        }
        
        # Categorize exactly like current system
        if element.category in ["Table"]:
            table_elements.append(normalized_element)
        else:
            text_elements.append(normalized_element) 
    
    return text_elements, table_elements
```

**Zero Breaking Changes**: The implementation must produce identical `StepResult.data` structure regardless of which strategy is used internally.

### 4. Implementation Details

#### File Structure:
- Modify existing `partition.py` to include all hybrid functionality:
  - Add document detection methods within the PartitionStep class
  - Add output normalization methods within the PartitionStep class
  - Add Unstructured processing methods alongside existing PyMuPDF methods
- Update configuration in `indexing_config.yaml`
- Make sure we store in our metadata what strategy we are using and also print it to logs what strategy we are using

**Rationale**: Keep the clean one-file-per-step architecture. The detection and normalization logic are integral parts of the partition step and don't warrant separate files.

#### Configuration Updates:
```yaml
steps:
  partition:
    hybrid_mode: true
    scanned_detection:
      text_threshold: 25  # chars per page
      sample_pages: 10      # pages to analyze
    strategies:
      scanned:
        use_unstructured: true
        strategy: "hi_res"
        extract_full_pages: true
      regular:
        use_pymupdf: true
        maintain_current_behavior: true
```

#### Error Handling:
- Fallback to PyMuPDF if Unstructured fails
- Log strategy decisions for debugging
- Maintain processing time limits per strategy

#### Testing Requirements:
- Test with scanned documents (MOL_K07_C08_ARB_EL type)
- Test with regular documents (current test suite)
- Test with mixed documents (some scanned, some not)
- Verify output compatibility with existing metadata and chunking steps

### 5. Expected Benefits
- **Accuracy**: 100% page coverage for scanned documents
- **Performance**: Keep fast PyMuPDF for regular documents (0.8s vs 24.5s)
- **Table Detection**: Accurate table detection (2 real tables vs 9 false positives)
- **Compatibility**: Seamless integration with existing pipeline

### 6. Success Criteria
1. Scanned documents: Extract text from all pages (not just 40%)
2. Regular documents: Maintain current performance and accuracy
3. Output format: Consistent schema regardless of strategy used
4. Integration: No breaking changes to downstream steps (metadata, chunking, etc.)
5. Reliability: Robust fallback mechanisms for edge cases

## Implementation Priority
**High Priority**: This directly addresses the core issue where 60% of scanned document content is being lost in the current system.