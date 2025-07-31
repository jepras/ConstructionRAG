# Embedding Step Implementation Plan

## Overview
This document outlines the implementation plan for the embedding step in the ConstructionRAG pipeline, including database schema, data flow, and technical decisions.

## 🎯 Embedding Step Purpose
The embedding step takes chunked document elements from the `document_chunks` table and generates vector embeddings using the Voyage API, then stores them directly in the same table for efficient retrieval.

## 📊 Database Schema

### Document Chunks Table
```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indexing_run_id UUID REFERENCES indexing_runs(id),
    document_id UUID REFERENCES documents(id),
    
    -- Core chunk data (for embedding generation)
    chunk_id TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    
    -- Embedding data (for retrieval)
    embedding vector(1024),
    embedding_model TEXT,
    embedding_provider TEXT,
    embedding_metadata JSONB DEFAULT '{}',
    embedding_created_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_chunk_per_document UNIQUE (document_id, chunk_id)
);
```

### Indexes for Performance
```sql
-- HNSW index for vector similarity search (Supabase recommended)
CREATE INDEX idx_document_chunks_embedding_hnsw 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL;

-- GIN index for JSONB metadata queries
CREATE INDEX idx_document_chunks_metadata_gin 
ON document_chunks 
USING gin (metadata);

-- B-tree index for document filtering
CREATE INDEX idx_document_chunks_document_id ON document_chunks (document_id);
```

## 🔄 Data Flow

### Input
- **Source**: `document_chunks` table (chunks without embeddings)
- **Filter**: `WHERE embedding IS NULL`
- **Content**: `content` field from chunks

### Process
1. **Read chunks** from `document_chunks` table
2. **Generate embeddings** via Voyage API
3. **Update same table** with embeddings
4. **Track progress** in step_results

### Output
- **Updated**: `document_chunks` table with embeddings
- **Step Results**: Summary stats and sample outputs in JSON

## 🛠️ Technical Decisions

### 1. Single Step: Embed & Store
- **Approach**: Combine embedding generation and storage in one step
- **Benefits**: Atomic operations, better error handling, progress tracking
- **Implementation**: Read chunks → Generate embeddings → Update table

### 2. Voyage API Integration
- **Model**: `voyage-multilingual-2` (1024 dimensions)
- **Provider**: Voyage AI
- **Batch Size**: 100 chunks per API call
- **Retry Logic**: Exponential backoff with max 3 retries

### 3. Database Integration
- **Storage**: Direct pgvector storage in PostgreSQL
- **No External DB**: No ChromaDB or other vector databases
- **Atomic Updates**: Each chunk embedded and stored together

### 4. Progress Tracking
- **Per-chunk tracking**: Update progress as each chunk is processed
- **Resume capability**: Can restart from where it left off
- **Error handling**: Mark failed chunks for retry

## 📋 Implementation Steps

### Step 1: Database Schema Setup
1. Create `document_chunks` table with pgvector support
2. Create HNSW index for vector similarity
3. Create GIN index for metadata queries
4. Create B-tree indexes for filtering

### Step 2: Embedding Step Implementation
1. Create `EmbeddingStep` class extending `PipelineStep`
2. Implement chunk reading from database
3. Implement Voyage API integration
4. Implement embedding storage back to database
5. Implement progress tracking and error handling

### Step 3: Configuration
1. Add embedding configuration to `indexing_config.yaml`
2. Configure Voyage API settings
3. Configure batch processing parameters
4. Configure retry and timeout settings

### Step 4: Testing
1. Unit tests for embedding generation
2. Integration tests with sample chunks
3. Performance tests with large documents
4. Error handling tests

## ⚙️ Configuration

### indexing_config.yaml
```yaml
embedding:
  model: "voyage-multilingual-2"
  provider: "voyage"
  dimensions: 1024
  batch_size: 100
  max_retries: 3
  retry_delay: 1.0
  timeout_seconds: 30
  cost_tracking: true
```

### Environment Variables
```bash
VOYAGE_API_KEY=your_voyage_api_key
```

## 🔍 Expected Output Structure

### Step Results JSON
```json
{
  "step": "embedding",
  "status": "completed",
  "duration_seconds": 45.2,
  "summary_stats": {
    "total_chunks": 150,
    "chunks_embedded": 150,
    "chunks_failed": 0,
    "average_embedding_time_ms": 150,
    "total_api_cost": 0.00075,
    "embedding_model": "voyage-multilingual-2",
    "embedding_provider": "voyage"
  },
  "sample_outputs": {
    "sample_embeddings": [
      {
        "chunk_id": "chunk_001",
        "content_preview": "Foundation requirements...",
        "embedding_dimensions": 1024,
        "api_response_time_ms": 145
      }
    ]
  }
}
```

## 🚨 Error Handling Strategy

### Retry Logic
- **API failures**: Exponential backoff (1s, 2s, 4s)
- **Rate limits**: Wait and retry with backoff
- **Network issues**: Retry up to 3 times
- **Invalid responses**: Log error and skip chunk

### Failure Recovery
- **Partial failures**: Continue with remaining chunks
- **Complete failure**: Mark step as failed, allow retry
- **Database errors**: Rollback and retry
- **Memory issues**: Process in smaller batches

## 📊 Performance Considerations

### Batch Processing
- **Optimal batch size**: 100 chunks per API call
- **Memory management**: Process batches sequentially
- **Progress tracking**: Update after each batch
- **Error isolation**: Failed batch doesn't stop others

### Rate Limiting
- **Voyage API limits**: Respect rate limits
- **Backoff strategy**: Exponential backoff on 429 errors
- **Monitoring**: Track API usage and costs
- **Optimization**: Batch requests efficiently

## 🔧 Integration with Pipeline

### Orchestrator Integration
- **Trigger**: After chunking step completes
- **Input**: Read chunks from `document_chunks` table
- **Output**: Update same table with embeddings
- **Progress**: Update `step_executions` table

### Next Step Preparation
- **Storage step**: Will validate embeddings and create final indexes
- **Query pipeline**: Will use embeddings for similarity search
- **Metadata**: Preserved for filtering and context

## 🎯 Success Criteria

### Functional Requirements
- [ ] All chunks get embeddings generated
- [ ] Embeddings stored in pgvector format
- [ ] Metadata preserved and accessible
- [ ] Progress tracking works correctly
- [ ] Error handling prevents data loss

### Performance Requirements
- [ ] Process 1000 chunks in < 5 minutes
- [ ] API cost < $0.01 per document
- [ ] Memory usage < 1GB for large documents
- [ ] Can resume interrupted processing

### Quality Requirements
- [ ] Embeddings match Voyage API quality
- [ ] No duplicate embeddings generated
- [ ] All metadata fields preserved
- [ ] Vector dimensions correct (1024)

## 📚 Key Learnings from Notebook

### What to Keep
- **Voyage API integration**: Proven to work well with Danish construction documents
- **Quality validation**: Comprehensive embedding validation
- **Error handling**: Robust retry logic and error recovery
- **Cost tracking**: Monitor API usage and costs

### What to Change
- **Storage**: Use pgvector instead of ChromaDB
- **Processing**: Stream chunks instead of batch processing
- **Progress**: Track per-chunk progress instead of all-or-nothing
- **Integration**: Direct database integration instead of file I/O

## 🚀 Next Steps

1. **Database migration**: Create document_chunks table with pgvector
2. **Embedding step implementation**: Build the core embedding functionality
3. **Configuration setup**: Add embedding config to pipeline
4. **Testing**: Comprehensive test suite
5. **Integration**: Connect to orchestrator and pipeline
6. **Validation**: Test with real construction documents

This plan provides a clear roadmap for implementing the embedding step with optimal performance, reliability, and integration with the existing pipeline architecture. 