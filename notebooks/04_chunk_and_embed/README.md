# Chunking & Embedding Pipeline

## Overview

This notebook implements intelligent chunking with rich metadata preservation before embedding and storing construction documents in a vector database. It represents the final stage of the ConstructionRAG processing pipeline.

## Features

### 🧠 Intelligent Adaptive Chunking
- **Content-aware chunking**: Different chunk sizes based on text complexity
- **Construction-specific optimization**: Special handling for technical content
- **Section preservation**: Maintains document structure and relationships

### 📊 Rich Metadata Preservation
- **Complete context**: Preserves all metadata from previous pipeline stages
- **VLM integration**: Includes AI-generated captions and descriptions
- **Processing traceability**: Tracks chunking strategy and parameters

### 🗄️ Advanced Vector Database
- **ChromaDB integration**: Persistent storage with rich metadata
- **Metadata filtering**: Enable precise queries by content characteristics
- **Construction-specific collection**: Optimized for technical documents

## Pipeline Integration

This notebook follows the three previous stages:

```
PDF Files → partition_pdf.py → meta_data.py → enrich_data_from_meta.py → chunk_and_embed.py
```

**Input**: `enrich_data_output.pkl` from the VLM enrichment stage
**Output**: Vector database with chunked, embedded content

## Configuration

### Quick Setup

1. **Update the run configuration**:
```python
ENRICH_DATA_RUN_TO_LOAD = "03_run_20250721_100823"  # Your latest enrich_data run
```

2. **Configure chunking strategy**:
```python
CHUNKING_STRATEGY = "adaptive"  # Options: "adaptive", "fixed", "semantic"
```

3. **Adjust chunking parameters** (if needed):
```python
ADAPTIVE_CHUNK_SIZES = {
    "simple": 1500,      # Simple text gets larger chunks
    "medium": 1000,      # Medium complexity gets standard chunks
    "complex": 600,      # Complex text gets smaller chunks
    "table": 800,        # Tables get medium chunks
    "image_page": 1200   # Image pages get larger chunks
}
```

### Advanced Configuration

Use the JSON configuration file for detailed settings:
```bash
# Edit configuration
nano config/chunking_config.json
```

## Usage

### Basic Execution

```bash
cd notebooks/04_chunk_and_embed/
python chunk_and_embed.py
```

### Expected Output

```
🏗️ CONSTRUCTION RAG - CHUNKING & EMBEDDING PIPELINE
============================================================

📂 Input: ../../data/internal/03_enrich_data/03_run_20250721_100823/enrich_data_output.pkl
📁 Output: ../../data/internal/04_chunk_and_embed/04_run_20250121_143022

📂 STEP 1: LOADING ENRICHED ELEMENTS
----------------------------------------
✅ Loaded 45 enriched elements

🔪 STEP 2: INITIALIZING CHUNKER
----------------------------------------
✅ Initialized adaptive chunking strategy

🔪 STEP 3: CHUNKING ELEMENTS
----------------------------------------
✅ Created 127 total chunks

📊 STEP 4: ANALYZING RESULTS
----------------------------------------
📈 Chunking Analysis:
   Total chunks: 127
   Average words per chunk: 45.2
   Average chars per chunk: 234.7
   VLM processed: 23 chunks

📋 Content Type Distribution:
   text: 89 chunks
   table: 15 chunks
   full_page_with_images: 23 chunks

🗄️ STEP 5: INITIALIZING VECTOR DATABASE
----------------------------------------
✅ Created new collection: construction_docs
✅ Embedding model produces 1536-dimensional vectors

💾 STEP 6: STORING IN VECTOR DATABASE
----------------------------------------
✅ Successfully stored 127 chunks

🔍 STEP 8: TESTING QUERY
----------------------------------------
📋 Top 3 Results:
  Result 1 (Distance: 0.2341):
    📄 Source: test-with-little-variety.pdf | Page: 3
    📝 Type: text | Complexity: medium
    🔗 Section: 2.1 Technical Specifications
    📖 Content: The construction specifications require...

🎉 CHUNKING & EMBEDDING PIPELINE COMPLETE!
============================================================
📊 Summary:
   📄 Input elements: 45
   🔪 Output chunks: 127
   💾 Stored in vector DB: 127
   🗄️ Total DB items: 127
   📁 Output directory: ../../data/internal/04_chunk_and_embed/04_run_20250121_143022

🚀 Ready for RAG queries!
```

## Output Files

### Generated Files

```
data/internal/04_chunk_and_embed/04_run_20250121_143022/
├── chunked_elements.pkl          # Complete chunked data (pickle)
├── chunking_analysis.json        # Processing statistics and analysis
├── sample_chunks.json           # Sample chunks for inspection
└── vector_db_log.json           # Database operations log
```

### Vector Database

The chunks are stored in ChromaDB with rich metadata:
- **Collection**: `construction_docs`
- **Location**: `../../chroma_db/`
- **Metadata**: Complete preservation of all structural and VLM metadata

## Chunking Strategies

### 1. Adaptive Chunking (Default)

Intelligently adjusts chunk size based on content characteristics:

| Content Type | Chunk Size | Overlap | Use Case |
|--------------|------------|---------|----------|
| Simple text | 1500 chars | 100 | Descriptive content |
| Medium text | 1000 chars | 200 | Standard content |
| Complex text | 600 chars | 300 | Technical specifications |
| Tables | 800 chars | 150 | Structured data |
| Image pages | 1200 chars | 250 | Visual content with captions |

### 2. Fixed Chunking

Uses consistent chunk size for all content:
```python
CHUNKING_STRATEGY = "fixed"
BASE_CHUNK_SIZE = 1000
BASE_CHUNK_OVERLAP = 200
```

### 3. Semantic Chunking (Future)

Topic-based chunking with sentence boundary detection (planned enhancement).

## Metadata Preservation

### Structural Metadata
- Source filename and page number
- Content type and element category
- Text complexity and content length
- Section inheritance and titles
- Page context (text-only, with images, etc.)

### VLM Enrichment Metadata
- VLM processing status
- Table HTML captions
- Image page captions
- Page text context

### Chunking Metadata
- Chunk ID and source element ID
- Chunk index and total chunks in element
- Chunking strategy and parameters
- Word and character counts

## Querying the Vector Database

### Basic Query

```python
from chunk_and_embed import ConstructionVectorDB

# Initialize database
vector_db = ConstructionVectorDB("../../chroma_db", "construction_docs")
vector_db.initialize()

# Simple query
results = vector_db.query_chunks("construction specifications", n_results=5)
```

### Filtered Query

```python
# Query with metadata filters
filters = {
    "content_type": "text",
    "text_complexity": "complex",
    "page_number": {"$gte": 1, "$lte": 5}
}

results = vector_db.query_chunks(
    "technical requirements", 
    n_results=3, 
    filters=filters
)
```

### Advanced Queries

```python
# Query by section
section_filter = {
    "section_title_inherited": {"$contains": "Technical Specifications"}
}

# Query VLM-processed content
vlm_filter = {"vlm_processed": True}

# Query tables only
table_filter = {"content_type": "table"}
```

## Performance Considerations

### Chunking Performance
- **Processing speed**: ~100-500 elements per minute
- **Memory usage**: Moderate (depends on document size)
- **CPU usage**: Low to moderate

### Embedding Performance
- **API calls**: One per chunk (batch processing available)
- **Rate limiting**: Respects OpenAI API limits
- **Cost**: ~$0.0001 per 1K tokens (varies by model)

### Database Performance
- **Storage**: Efficient with metadata compression
- **Query speed**: Fast with cosine similarity
- **Scalability**: Supports millions of chunks

## Troubleshooting

### Common Issues

1. **Missing enriched elements file**
   ```
   FileNotFoundError: Enriched elements file not found
   ```
   **Solution**: Verify the `ENRICH_DATA_RUN_TO_LOAD` path

2. **API key issues**
   ```
   ValueError: OPENAI_API_KEY not found in .env file
   ```
   **Solution**: Check your `.env` file configuration

3. **ChromaDB dimension mismatch**
   ```
   ValueError: Embedding dimensions don't match
   ```
   **Solution**: Clear the ChromaDB directory and re-run

4. **Memory issues with large documents**
   ```
   MemoryError: Unable to process large document
   ```
   **Solution**: Reduce chunk sizes or process in batches

### Debug Mode

Enable detailed logging by modifying the script:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with RAG System

### Next Steps

After running this notebook, your construction documents are ready for RAG queries:

1. **Query Interface**: Build a chat interface using the vector database
2. **Retrieval Augmentation**: Combine with LLM for answer generation
3. **Hybrid Search**: Implement metadata + semantic search
4. **Multi-modal RAG**: Extend to image and table queries

### Example RAG Integration

```python
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA

# Initialize components
llm = ChatOpenAI(model="gpt-3.5-turbo")
vector_db = ConstructionVectorDB("../../chroma_db", "construction_docs")
vector_db.initialize()

# Create RAG chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vector_db.collection.as_retriever()
)

# Query the system
response = qa_chain.run("What are the safety requirements for this project?")
```

## Future Enhancements

### Planned Features
- **Semantic chunking**: Topic-based chunking
- **Hybrid search**: Metadata + semantic ranking
- **Multi-modal queries**: Image and table search
- **Real-time updates**: Incremental document processing

### Contributing
- Report issues in the project repository
- Suggest improvements for construction-specific features
- Contribute to the chunking strategies

---

**Ready to build intelligent construction document search! 🏗️** 