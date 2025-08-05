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

### 6. Testing Strategy

#### Phase 1: Unit Testing (Individual Components)
```python
# Test document detection
def test_document_detection():
    # Regular document should be detected as not scanned
    assert not _detect_document_type("test-with-little-variety.pdf")["is_likely_scanned"]
    
    # Scanned document should be detected as scanned  
    assert _detect_document_type("MOL_K07_C08_ARB_EL.pdf")["is_likely_scanned"]

# Test output normalization
def test_output_normalization():
    # Unstructured elements should normalize to current format
    unstructured_elements = [mock_unstructured_element()]
    text_elements, table_elements = _normalize_unstructured_to_current_format(unstructured_elements)
    
    # Verify exact schema match
    assert all(["id", "category", "page", "text", "metadata"] == list(elem.keys()) for elem in text_elements)
```

#### Phase 2: Integration Testing (Full Pipeline)
```python
# Test with known documents from our comparison results
TEST_DOCUMENTS = {
    "scanned": "small-complicated/MOL_K07_C08_ARB_EL - EL arbejdsbeskrivelse copy.pdf",
    "regular": "test-with-little-variety.pdf", 
    "complex_tables": "small-complicated/Tegninger samlet copy.pdf"
}

def test_scanned_document_processing():
    """Test that scanned docs get full page coverage"""
    result = partition_step.execute(TEST_DOCUMENTS["scanned"])
    
    # Should use hi_res strategy
    assert result.data["metadata"]["processing_strategy"] == "unstructured_hi_res"
    
    # Should extract from all pages (not just 40%)
    pages_with_text = set(elem["page"] for elem in result.data["text_elements"])
    assert len(pages_with_text) >= 3  # Should find text on pages 1,2,3 (not just 4,5)
    
    # Should find more text elements than PyMuPDF (140 vs 8)
    assert len(result.data["text_elements"]) > 100

def test_regular_document_processing():
    """Test that regular docs maintain current performance"""
    result = partition_step.execute(TEST_DOCUMENTS["regular"])
    
    # Should use PyMuPDF strategy
    assert result.data["metadata"]["processing_strategy"] == "pymupdf_only"
    
    # Should maintain current performance characteristics
    assert result.duration_seconds < 5.0  # Fast processing

def test_output_compatibility():
    """Test that both strategies produce identical output schema"""
    scanned_result = partition_step.execute(TEST_DOCUMENTS["scanned"])
    regular_result = partition_step.execute(TEST_DOCUMENTS["regular"])
    
    # Both should have identical top-level keys
    assert set(scanned_result.data.keys()) == set(regular_result.data.keys())
    
    # Elements should have identical schema
    for result in [scanned_result, regular_result]:
        for elem in result.data["text_elements"]:
            assert set(elem.keys()) == {"id", "category", "page", "text", "metadata"}
```

#### Phase 3: Downstream Compatibility Testing
```python
def test_metadata_step_compatibility():
    """Test that metadata step works with both strategies"""
    # Process with both strategies
    scanned_partition = partition_step.execute(TEST_DOCUMENTS["scanned"])
    regular_partition = partition_step.execute(TEST_DOCUMENTS["regular"])
    
    # Both should work with metadata step
    scanned_metadata = metadata_step.execute(scanned_partition)
    regular_metadata = metadata_step.execute(regular_partition)
    
    # Both should succeed
    assert scanned_metadata.status == "completed"
    assert regular_metadata.status == "completed"

def test_chunking_step_compatibility():
    """Test that chunking step works with both strategies"""
    # Similar pattern for chunking step...
```

#### Phase 4: Performance & Accuracy Validation
```python
def test_performance_benchmarks():
    """Validate performance characteristics"""
    # Regular docs should be fast (< 3s)
    regular_result = partition_step.execute(TEST_DOCUMENTS["regular"])
    assert regular_result.duration_seconds < 3.0
    
    # Scanned docs can be slower but should complete (< 30s)
    scanned_result = partition_step.execute(TEST_DOCUMENTS["scanned"])
    assert scanned_result.duration_seconds < 30.0

def test_accuracy_improvements():
    """Validate accuracy improvements for scanned docs"""
    result = partition_step.execute(TEST_DOCUMENTS["scanned"])
    
    # Should extract significantly more content than current system
    # Current: 8 text elements from pages 4-5 only
    # Expected: 100+ text elements from all pages 1-5
    assert len(result.data["text_elements"]) > 100
    
    # Should cover all pages
    pages_covered = set(elem["page"] for elem in result.data["text_elements"])
    assert len(pages_covered) >= 3  # Should cover pages 1,2,3 (currently missed)
```

#### Phase 5: Error Handling & Fallback Testing
```python
def test_unstructured_failure_fallback():
    """Test fallback to PyMuPDF when Unstructured fails"""
    # Mock Unstructured failure
    with mock.patch('unstructured.partition.pdf.partition_pdf', side_effect=Exception("OCR failed")):
        result = partition_step.execute(TEST_DOCUMENTS["scanned"])
        
        # Should fallback to PyMuPDF and still complete
        assert result.status == "completed"
        assert result.data["metadata"]["processing_strategy"] == "pymupdf_fallback"

def test_malformed_pdf_handling():
    """Test handling of corrupted/malformed PDFs"""
    # Test with corrupted PDF should not crash pipeline
```

#### Testing Environment Setup
```bash
# Use existing test environment
cd notebooks/01_partition
source test_venv/bin/activate

# Run tests
python -m pytest test_hybrid_partition.py -v

# Performance benchmarking
python benchmark_hybrid_partition.py
```

### 7. Success Criteria
1. **Accuracy**: Scanned documents extract text from all pages (not just 40%)
2. **Performance**: Regular documents maintain current speed (< 3s)
3. **Compatibility**: All existing tests pass unchanged
4. **Integration**: Metadata and chunking steps work without modification
5. **Reliability**: Robust fallback mechanisms prevent pipeline failures

### 8. Rollout Plan  
1. **Development**: Implement with comprehensive test suite
2. **Testing**: Run against existing document corpus
3. **Staging**: Deploy to staging environment with monitoring
4. **Production**: Gradual rollout with rollback capability

## Implementation Priority
**High Priority**: This directly addresses the core issue where 60% of scanned document content is being lost in the current system.