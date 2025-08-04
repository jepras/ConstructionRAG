# PDF Processing Strategy Comparison

This directory contains tools to compare different PDF processing strategies for handling scanned documents and complex layouts.

## Quick Start (Safe for Production venv)

Run the PyMuPDF-only comparison first:

```bash
# From project root
cd notebooks/01_partition
python pymupdf_comparison.py
```

This will test your PDFs with different PyMuPDF strategies and save results to JSON.

## Full Comparison (Requires Test Environment)

To test against Unstructured strategies:

1. **Set up test environment:**
   ```bash
   cd notebooks/01_partition
   ./setup_test_env.sh
   ```

2. **Activate test environment:**
   ```bash
   source test_venv/bin/activate
   ```

3. **Run full comparison:**
   ```bash
   python pdf_strategy_comparison.py
   ```

4. **Deactivate when done:**
   ```bash
   deactivate
   ```

## Configuration

Edit the test files in both scripts:

```python
TEST_FILES = [
    "test-with-little-variety.pdf",  # Your existing test file
    "scanned_document.pdf",          # Add your scanned PDF
    "complex_tables.pdf",            # Add PDF with complex tables
]
```

## Strategies Tested

### PyMuPDF-Only Comparison (`pymupdf_comparison.py`)
- **basic_text**: Simple `get_text()` extraction
- **structured**: Detailed `get_text("dict")` with font info
- **table_focused**: Table extraction with image saving
- **image_analysis**: Page complexity analysis + full page extraction

### Full Comparison (`pdf_strategy_comparison.py`)
- **pymupdf**: Your current approach
- **unstructured_hi_res**: Better table/image detection
- **unstructured_ocr**: OCR-only for scanned docs
- **hybrid**: Auto-detection and strategy selection

## Output

Both scripts generate:
- **JSON results**: Detailed comparison data
- **Extracted images**: Table and page images for inspection
- **Performance metrics**: Processing time and success rates
- **Document analysis**: Text density, complexity assessment

## Interpreting Results

### For Scanned Documents:
- Look for `"is_likely_scanned": true` in document analysis
- Compare text extraction quality between strategies
- Check if OCR strategies find more content

### For Table Extraction:
- Compare table counts between strategies
- Check saved table images for accuracy
- Look for HTML table structure in results

### For Performance:
- Compare `processing_time` across strategies
- Balance speed vs. accuracy for your use case

## Recommendations

Based on results, you might:

1. **Implement hybrid detection** in your pipeline
2. **Add OCR fallback** for scanned documents  
3. **Switch to Unstructured hi_res** for better table extraction
4. **Keep PyMuPDF** for simple text-heavy documents

## Files

- `pymupdf_comparison.py` - Safe comparison using only PyMuPDF
- `pdf_strategy_comparison.py` - Full comparison including Unstructured
- `setup_test_env.sh` - Creates isolated test environment
- Results saved to: `../../data/internal/01_partition_data/`