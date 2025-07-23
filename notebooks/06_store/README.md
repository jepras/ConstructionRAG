# ChromaDB Storage & Validation - Step 06

This notebook stores embedded chunks from step 05 into ChromaDB with comprehensive validation and performance testing.

## Purpose

Store embedded construction document chunks in ChromaDB vector database with:
- **Persistent Storage**: Long-term vector storage for the RAG pipeline
- **Metadata Indexing**: Flattened metadata for efficient filtering
- **Integrated Validation**: Comprehensive storage integrity testing
- **Performance Benchmarking**: Search speed and accuracy testing

## Features

### 🗄️ **ChromaDB Storage**
- **Single Collection Strategy**: Cross-document search capability
- **Persistent Storage**: Database persists between runs
- **Batch Processing**: Efficient storage in configurable batches
- **Metadata Flattening**: Automatic conversion of nested metadata for ChromaDB compatibility

### 🔍 **Comprehensive Validation**
- **Storage Integrity**: Verifies all chunks were stored correctly
- **Metadata Validation**: Confirms all metadata fields are indexed
- **Search Performance**: Tests query response times with construction-specific queries
- **Filtering Tests**: Validates metadata-based filtering capabilities

### 📊 **Performance Testing**
- **Bilingual Query Testing**: Danish and English construction queries
- **Response Time Measurement**: Millisecond-precision timing
- **Result Quality Assessment**: Top result scoring and relevance
- **Metadata Filter Testing**: Various filtering scenarios

## Configuration

The notebook uses `config/storage_config.json` for:

```json
{
  "batch_size": 100,
  "validation_sample_size": 50,
  "performance_queries": [
    "foundation requirements",
    "fundament krav",
    "structural safety",
    "byggereglement"
  ],
  "validation_thresholds": {
    "max_response_time_ms": 500,
    "min_search_results": 1
  }
}
```

## Input Requirements

### Expected Input Structure
From step 05 embedding output:
```python
{
  "chunk_id": "uuid-string",
  "content": "document content",
  "embedding": [float, float, ...],  # 1024-dim for Voyage
  "metadata": {
    "source_filename": "document.pdf",
    "page_number": 1,
    "element_category": "NarrativeText",
    "section_title_inherited": "Section Title",
    # ... other metadata fields
  },
  "embedding_provider": "voyage",
  "embedding_model": "voyage-multilingual-2"
}
```

### Automatic Input Detection
The script automatically finds the most recent embedding run from:
- `data/internal/05_embedding/05_voyage_run_YYYYMMDD_HHMMSS/`
- `data/internal/05_embedding/05_run_YYYYMMDD_HHMMSS/`

Supports both Voyage and OpenAI embedding formats.

## Usage

### Basic Execution
```bash
# Activate virtual environment
source venv/bin/activate

# Run storage and validation
python notebooks/06_store/store_and_validate.py
```

### What the Script Does

1. **Loads Embedded Chunks**: Finds and loads latest embedding run
2. **Validates Structure**: Ensures all required fields are present
3. **Converts Format**: Flattens metadata for ChromaDB compatibility
4. **Initializes ChromaDB**: Sets up persistent storage
5. **Stores Documents**: Batch storage with progress tracking
6. **Validates Storage**: Confirms all documents stored correctly
7. **Tests Performance**: Runs search speed and accuracy tests
8. **Tests Filtering**: Validates metadata-based filtering
9. **Creates Report**: Comprehensive validation report
10. **Saves Results**: Detailed test results and analysis

## Output Files

The script creates timestamped output in `data/internal/06_store/06_run_YYYYMMDD_HHMMSS/`:

### 📊 **Validation Reports**
- `storage_validation_report.json` - Main validation summary
- `search_performance_details.json` - Detailed search test results  
- `metadata_filtering_tests.json` - Filtering capability tests

### 📦 **ChromaDB Database**
- `../../chroma_db/` - Persistent ChromaDB storage
- Collection: `construction_documents`

## ChromaDB Collection Details

### Collection Configuration
- **Name**: `construction_documents`
- **Strategy**: Single collection for all project documents
- **Embeddings**: 1024-dimensional vectors (Voyage multilingual-2)
- **Metadata**: Flattened for efficient filtering

### Metadata Fields Stored
```python
{
  "source_filename": "document.pdf",
  "page_number": 1,
  "element_category": "NarrativeText", 
  "section_title_inherited": "Section Title",
  "text_complexity": "medium",
  "content_length": 1250,
  "has_numbers": True,
  "has_tables_on_page": False,
  "has_images_on_page": False,
  "processing_strategy": "unified_fast_vision",
  "page_context": "main_content",
  "embedding_provider": "voyage",
  "embedding_model": "voyage-multilingual-2"
}
```

## Validation Tests

### 🔍 **Storage Integrity Tests**
- Document count verification
- Embedding dimension validation
- Metadata field completeness
- Content preservation checks

### ⚡ **Performance Tests**
Bilingual construction queries:
- "foundation requirements" / "fundament krav"
- "insulation standards" / "isolering krav"  
- "building regulations" / "byggereglement"
- "structural safety" / "konstruktiv sikkerhed"

### 🎯 **Filtering Tests**
- Source filename filtering
- Element category filtering
- Page number filtering
- Content type filtering (has_numbers, etc.)

## Validation Report Structure

```python
{
  "total_chunks_stored": 1250,
  "storage_time_seconds": 45.2,
  "metadata_fields_indexed": ["source_filename", "page_number", ...],
  "search_performance_ms": {
    "average_ms": 125.5,
    "min_ms": 89.2,
    "max_ms": 245.1
  },
  "validation_passed": True,
  "issues_found": []
}
```

## Success Criteria

### ✅ **Storage Success**
- All embedded chunks stored in ChromaDB
- No data loss during conversion
- All metadata fields properly indexed
- Persistent storage working correctly

### ✅ **Performance Success**  
- Search queries respond within 500ms
- All test queries return relevant results
- Metadata filtering works correctly
- No failed queries or errors

### ✅ **Quality Success**
- High relevance scores for construction queries
- Bilingual query support working
- Cross-document search capability verified
- Citation-ready metadata preserved

## Troubleshooting

### Common Issues

1. **ChromaDB Import Errors**
   ```bash
   pip install chromadb>=0.4.0
   ```

2. **Permission Errors**
   - Ensure write permissions for `chroma_db/` directory
   - Check virtual environment activation

3. **Memory Issues**
   - Reduce `batch_size` in config for large datasets
   - Monitor system memory during storage

4. **Slow Performance**
   - Check disk I/O performance
   - Consider SSD for ChromaDB storage
   - Verify embedding dimension matches (1024)

### Validation Failures

If validation fails:
1. Check `storage_validation_report.json` for specific issues
2. Review `search_performance_details.json` for failed queries
3. Verify input data structure from step 05
4. Check ChromaDB installation and permissions

## Next Steps

After successful storage and validation:

1. **Review Reports**: Check validation results and performance metrics
2. **Test Custom Queries**: Try construction-specific queries
3. **Proceed to Step 07**: Query processing and expansion
4. **Configure Retrieval**: Set up hybrid search in step 08

## Integration Notes

### For Step 07 (Query Processing)
The stored collection provides:
- Semantic search capability via embeddings
- Rich metadata for query routing
- Bilingual support for Danish/English queries

### For Step 08 (Retrieval)
The collection enables:
- Hybrid search (semantic + keyword)
- Metadata-based filtering
- Cross-document search
- Citation generation from metadata

This storage layer forms the foundation for the remaining RAG pipeline steps. 