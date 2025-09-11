# Indexing Pipeline Structured Logging Plan

## Current Issues Summary

The indexing pipeline has **93 print statements** across 5 steps with these major problems:

- **🚫 Inconsistent logging**: Mix of `print()` and `logger.info()` calls
- **🚫 No correlation tracking**: Can't follow documents through pipeline  
- **🚫 Verbose debug logs**: Too much noise in production
- **🚫 Missing context**: Errors lack debugging information
- **🚫 No progress tracking**: Hard to monitor pipeline status

## Structured Logging Strategy

### 1. **Standard Log Fields** (All Log Entries)

```python
# Base context for every log entry
{
    "run_id": "uuid-string",           # Indexing run ID
    "document_id": "uuid-string",      # Document being processed  
    "step": "partition|metadata|enrichment|chunking|embedding",
    "timestamp": "2025-09-11T10:30:00Z"
}
```

### 2. **Log Levels by Purpose**

| Level | Purpose | Examples |
|-------|---------|----------|
| `INFO` | **Progress & milestones** | Step started/completed, document processed |
| `WARNING` | **Recoverable issues** | Fallback strategies, retries, performance concerns |
| `ERROR` | **Processing failures** | API errors, file processing failures |
| `DEBUG` | **Detailed internals** | Variable values, detailed timing (disabled in production) |

### 3. **Pipeline-Level Logging** (`beam-app.py`)

#### Start/End Events
```python
# Pipeline start
logger.info("indexing_pipeline_started", extra={
    "run_id": indexing_run_id,
    "document_count": len(document_ids),
    "user_id": user_id,
    "project_id": project_id,
    "beam_version": BEAM_VERSION
})

# Pipeline completion  
logger.info("indexing_pipeline_completed", extra={
    "run_id": indexing_run_id,
    "status": "success|failed",
    "duration_seconds": 1205.3,
    "documents_processed": 15,
    "documents_failed": 2,
    "total_chunks_created": 1847,
    "resource_usage": {
        "peak_cpu_percent": 85.2,
        "peak_ram_percent": 67.1
    }
})
```

#### Error Events
```python
# Pipeline errors
logger.error("indexing_pipeline_failed", extra={
    "run_id": indexing_run_id,
    "error_stage": "orchestrator|step_name", 
    "error_type": "timeout|api_error|resource_error",
    "error_message": str(error),
    "duration_before_failure_seconds": 890.1
})
```

### 4. **Document-Level Logging** (`orchestrator.py`)

#### Document Processing
```python
# Document start
logger.info("document_processing_started", extra={
    "run_id": run_id,
    "document_id": doc_id,
    "filename": filename,
    "file_size_mb": 2.4,
    "estimated_pages": 45
})

# Document completion
logger.info("document_processing_completed", extra={
    "run_id": run_id,
    "document_id": doc_id,
    "status": "success|failed",
    "duration_seconds": 180.5,
    "steps_completed": 5,
    "chunks_created": 127,
    "elements_extracted": 89
})
```

### 5. **Step-Level Logging** (Each Pipeline Step)

#### Step Progress
```python
# Step start - ALWAYS log this
logger.info("step_started", extra={
    "run_id": run_id,
    "document_id": doc_id,
    "step": step_name,
    "input_count": input_items_count  # pages, chunks, etc.
})

# Step completion - ALWAYS log this
logger.info("step_completed", extra={
    "run_id": run_id,
    "document_id": doc_id, 
    "step": step_name,
    "status": "success|failed",
    "duration_seconds": 45.2,
    "output_count": output_items_count,
    "processing_rate_per_second": 2.1
})
```

#### Step-Specific Context

**Partition Step:**
```python
# Key milestones only - no verbose page-by-page logs
logger.info("partition_analysis_completed", extra={
    "run_id": run_id,
    "document_id": doc_id,
    "step": "partition",
    "pages_analyzed": 45,
    "strategy_used": "hybrid|pymupdf_only",
    "images_found": 12,
    "tables_found": 8,
    "text_elements": 156
})
```

**Enrichment Step:**
```python
# VLM processing batches
logger.info("vlm_batch_processed", extra={
    "run_id": run_id,
    "document_id": doc_id,
    "step": "enrichment", 
    "batch_number": "3/7",
    "items_in_batch": 5,
    "vlm_model": "claude-3-5-sonnet",
    "api_duration_seconds": 12.3
})
```

**Embedding Step:**
```python
# Token batching (key for debugging API limits)
logger.info("embedding_batch_processed", extra={
    "run_id": run_id,
    "document_id": doc_id,
    "step": "embedding",
    "batch_number": "2/5",
    "texts_in_batch": 50,
    "estimated_tokens": 89000,
    "api_duration_seconds": 8.7,
    "model": "voyage-multilingual-2"
})
```

### 6. **Error Handling Strategy**

#### Structured Error Context
```python
# Replace generic error prints with structured errors
logger.error("step_processing_error", extra={
    "run_id": run_id,
    "document_id": doc_id,
    "step": step_name,
    "error_type": "api_timeout|rate_limit|validation_error|resource_error",
    "error_category": "external_api|internal_logic|resource_constraint", 
    "is_retryable": True,
    "retry_count": 2,
    "max_retries": 3,
    "error_details": {
        "api_endpoint": "/v1/embeddings",
        "response_status": 429,
        "batch_size": 50,
        "estimated_tokens": 89000
    }
}, exc_info=True)  # Include stack trace
```

### 7. **Performance Monitoring**

#### Resource Tracking
```python
# At step completion - include performance metrics
logger.info("step_performance", extra={
    "run_id": run_id,
    "document_id": doc_id,
    "step": step_name,
    "performance": {
        "duration_seconds": 45.2,
        "throughput_items_per_second": 2.8,
        "memory_peak_mb": 450,
        "cpu_utilization_avg_percent": 72,
        "api_calls_made": 8,
        "api_total_duration_seconds": 28.4
    }
})
```

### 8. **What to STOP Logging**

❌ **Remove these verbose patterns:**
```python
# DON'T log every page/chunk individually  
print(f"Processing page {i} of {total_pages}")
print(f"Chunk {j}: {chunk_text[:100]}...")

# DON'T log internal state repeatedly
print(f"🔄 Processing token batch {token_batch_idx + 1}/{len(token_batches)}")

# DON'T duplicate logger + print calls
logger.info(message)
print(message)  # Remove this
```

### 9. **Implementation Priority**

#### Phase 1: Critical Path (Start Here)
1. **beam-app.py** - Pipeline start/end/error events
2. **orchestrator.py** - Document start/completion events  
3. **Replace all print() with logger calls** across all steps

#### Phase 2: Enhanced Context
1. **Add structured fields** to existing logger calls
2. **Performance metrics** at step completion
3. **Error categorization** with proper context

#### Phase 3: Monitoring Integration
1. **Resource tracking** integration 
2. **Progress percentage** calculations
3. **Alert thresholds** for failures/performance

### 10. **Example Migration**

#### Before (Current):
```python
print(f"🔄 Starting unified document processing for {len(document_inputs)} documents")
# ... processing happens ...
print(f"✅ Completed document {doc_input.document_id}: {'Success' if result else 'Failed'}")
```

#### After (Structured):
```python
logger.info("batch_processing_started", extra={
    "run_id": indexing_run_id,
    "document_count": len(document_inputs),
    "max_concurrent": max_concurrent
})
# ... processing happens ...
logger.info("document_processed", extra={
    "run_id": indexing_run_id,
    "document_id": str(doc_input.document_id),
    "status": "success" if result else "failed",
    "duration_seconds": processing_time,
    "chunks_created": result.chunks_created if result else 0
})
```

## Benefits

✅ **Clear pipeline visibility**: Track documents through all steps  
✅ **Better debugging**: Structured context for all errors  
✅ **Performance monitoring**: Consistent metrics across steps  
✅ **Production readiness**: Proper log levels and filtering  
✅ **Monitoring integration**: Ready for Datadog/Sentry alerts  

This plan reduces noise while providing comprehensive visibility into your indexing pipeline's performance and failures.