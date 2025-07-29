# Core Pipeline Migration Design Document

## Overview
This document outlines the architectural design and implementation plan for migrating the notebook-based RAG pipeline into a production-ready system. Based on analysis of the existing notebooks and production requirements, we've identified two distinct pipeline types that require different architectural approaches.

## 🏗️ Architecture Overview

### Two-Pipeline Architecture
The RAG system consists of two fundamentally different pipeline types:

#### 1. **INDEXING PIPELINE** (Background Processing)
- **Trigger**: PDF upload
- **Nature**: Heavy, slow, background processing 
- **Processing**: Multiple documents in parallel, sequential steps per document
- **Duration**: Minutes to hours
- **User Interaction**: Progress tracking only
- **Steps**: 01→02→03→04→05→06 (partition→metadata→enrich→chunk→embed→store)

#### 2. **QUERY PIPELINE** (Real-time Processing)
- **Trigger**: User question
- **Nature**: Fast, real-time, user-facing
- **Processing**: Immediate response required
- **Duration**: Seconds
- **User Interaction**: Direct response expected
- **Steps**: 07→08→11 (query_processing→retrieval→generation)

## 📁 Directory Structure

```
backend/src/pipeline/
├── indexing/
│   ├── orchestrator.py              # Background processing coordinator
│   ├── steps/
│   │   ├── partition.py            # Step 01: PDF → structured elements
│   │   ├── metadata.py             # Step 02: Extract metadata
│   │   ├── enrichment.py           # Step 03: Enrich with context
│   │   ├── chunking.py             # Step 04: Text chunking
│   │   ├── embedding.py            # Step 05: Voyage API → pgvector
│   │   └── storage.py              # Step 06: Validation & indexing
│   └── config/
│       └── indexing_config.yaml
├── querying/
│   ├── orchestrator.py              # Real-time query coordinator  
│   ├── steps/
│   │   ├── query_processing.py     # Step 07: Query expansion & routing
│   │   ├── retrieval.py            # Step 08: Hybrid search
│   │   └── generation.py           # Step 11: LLM response
│   └── config/
│       └── query_config.yaml
└── shared/
    ├── base_step.py                 # Common step interface
    ├── progress_tracker.py          # Progress tracking utilities
    ├── config_manager.py            # Configuration management
    └── models.py                    # Shared pipeline models
```

## 🗄️ Database Schema

### Enhanced Pipeline Tracking
```sql
-- Separate indexing pipeline tracking
indexing_runs (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    status TEXT NOT NULL,                    -- pending, running, completed, failed
    step_results JSONB DEFAULT '{}',         -- Detailed results from each step
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT
);

-- Query pipeline tracking (store all queries)
query_runs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    project_id UUID,                         -- Future: group queries by project
    query_text TEXT NOT NULL,
    response_text TEXT,
    retrieval_metadata JSONB,               -- Search results, confidence scores
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User configuration overrides (future UI configurability)
user_config_overrides (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    config_type TEXT NOT NULL,              -- 'indexing' or 'querying'
    config_key TEXT NOT NULL,               -- 'chunking.chunk_size'
    config_value JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## 📊 Data Flow Architecture

### Indexing Pipeline Data Flow
```
PDF Upload → Sequential Processing → Vector Database

Step 1: Partition     → partitioned elements in Supabase Storage (temp files)
Step 2: Metadata      → document metadata in PostgreSQL  
Step 3: Enrich        → enriched metadata in PostgreSQL
Step 4: Chunk         → text chunks in PostgreSQL
Step 5: Embed         → embeddings directly to pgvector (no temp storage)
Step 6: Store         → validation + final indexing in pgvector
```

**Data Storage Strategy:**
- **Small data** (metadata, status, chunks): PostgreSQL tables
- **Large temp files** (partitioned elements): Supabase Storage (deleted after processing)
- **Final vectors**: pgvector (permanent)
- **Step outputs**: Stored for inspection and debugging

### Query Pipeline Data Flow
```
User Query → Real-time Processing → Response

Step 7: Query Processing → query expansion and routing
Step 8: Retrieval        → pgvector + metadata filters  
Step 11: Generation      → LLM response with citations
```

## ⚙️ Configuration Management

### Separate Configuration Files

#### indexing_config.yaml
```yaml
steps:
  partition:
    ocr_strategy: "auto"
    extract_tables: true
    extract_images: true
    max_image_size_mb: 10
    
  metadata:
    extract_page_structure: true
    detect_sections: true
    preserve_formatting: true
    
  enrichment:
    add_context_headers: true
    merge_related_elements: true
    min_content_length: 50
    
  chunking:
    chunk_size: 1000
    overlap: 200
    strategy: "semantic"
    separators: ["\n\n", "\n", " ", ""]
    min_chunk_size: 100
    max_chunk_size: 2000
    
  embedding:
    model: "voyage-large-2"
    dimensions: 1536
    batch_size: 100
    
  storage:
    collection_prefix: "construction_docs"
    validation_sample_size: 50
    
orchestration:
  max_concurrent_documents: 5
  step_timeout_minutes: 30
  retry_attempts: 3
  fail_fast: true
```

#### query_config.yaml
```yaml
steps:
  query_processing:
    semantic_expansion_count: 3
    enable_hyde_documents: true
    content_category_detection: true
    danish_query_variations: true
    
  retrieval:
    top_k: 5
    similarity_threshold: 0.7
    hybrid_search_weight: 0.5
    enable_metadata_filtering: true
    max_results_per_document: 3
    
  generation:
    model: "gpt-4"
    temperature: 0.1
    max_tokens: 1000
    include_citations: true
    response_language: "danish"
    
orchestration:
  response_timeout_seconds: 30
  max_context_tokens: 8000
  fail_fast: true
```

### Future UI Configurability with Async Operations
The YAML files serve as defaults. Users can override specific settings through the UI, with overrides stored in the `user_config_overrides` table:

```python
# Functional config manager with async operations
async def get_indexing_config(user_id: UUID, db: Database = Depends(get_database)) -> IndexingConfig:
    """Get indexing configuration with user overrides using async operations"""
    # 1. Load YAML defaults (async file reading)
    defaults = await load_yaml_async("indexing_config.yaml")
    
    # 2. Apply user overrides from database (async database query)
    user_overrides = await get_user_config_overrides_async(user_id, "indexing", db)
    
    # 3. Merge and validate (pure function)
    return merge_and_validate_config_pure(defaults, user_overrides)

# Pure function for config merging
def merge_and_validate_config_pure(defaults: Dict, overrides: Dict) -> IndexingConfig:
    """Pure function for merging and validating configurations"""
    merged_config = deep_merge_configs(defaults, overrides)
    return IndexingConfig(**merged_config)

# Async dependency injection for config manager
async def get_config_manager(db: Database = Depends(get_database)) -> ConfigManager:
    """Get config manager with injected database dependency"""
    return ConfigManager(db)
```

## 🔧 Pipeline Step Interface

### Common Step Interface with Functional Design
```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel
from fastapi import Depends

class StepResult(BaseModel):
    # Status information
    step: str
    status: str                              # completed, failed
    duration_seconds: float
    
    # Summary statistics
    summary_stats: Dict[str, Any]            # {"chunks_created": 150, "avg_chunk_size": 800}
    
    # Sample outputs for debugging
    sample_outputs: Dict[str, Any]           # {"sample_chunks": ["first chunk...", "second chunk..."]}
    
    # Error information
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

class PipelineStep(ABC):
    """Abstract base class for pipeline steps with functional implementation"""
    
    def __init__(self, config: Dict[str, Any], tracker: ProgressTracker):
        self.config = config
        self.tracker = tracker
    
    @abstractmethod
    async def execute(self, input_data: Any) -> StepResult:
        """
        Execute the pipeline step with given input data.
        
        This method should be implemented as a pure function with:
        - No side effects beyond the return value
        - Explicit dependencies passed as parameters
        - All I/O operations handled asynchronously
        """
        pass
    
    @abstractmethod
    def validate_prerequisites(self, input_data: Any) -> bool:
        """Validate that input data meets step requirements"""
        pass
    
    @abstractmethod
    def estimate_duration(self, input_data: Any) -> int:
        """Estimate step duration in seconds"""
        pass
    
    def get_step_name(self) -> str:
        """Return human-readable step name"""
        return self.__class__.__name__

# Example implementation showing functional approach
class PartitionStep(PipelineStep):
    async def execute(self, input_data: DocumentInput) -> StepResult:
        """
        Pure function implementation of partition step.
        
        All dependencies are explicit, no side effects beyond return value.
        """
        start_time = time.time()
        
        try:
            # Pure function call with explicit dependencies
            elements = await partition_document_pure(
                file_path=input_data.file_path,
                config=self.config,
                storage_client=self.storage_client  # Explicit dependency
            )
            
            duration = time.time() - start_time
            
            return StepResult(
                step="partition",
                status="completed",
                duration_seconds=duration,
                summary_stats={
                    "total_elements": len(elements),
                    "text_elements": len([e for e in elements if e.type == "text"]),
                    "table_elements": len([e for e in elements if e.type == "table"]),
                    "image_elements": len([e for e in elements if e.type == "image"])
                },
                sample_outputs={
                    "sample_elements": [e.content[:200] + "..." for e in elements[:3]]
                }
            )
            
        except Exception as e:
            return StepResult(
                step="partition",
                status="failed",
                duration_seconds=time.time() - start_time,
                error_message=str(e),
                error_details={"exception_type": type(e).__name__}
            )

# Pure function implementation
async def partition_document_pure(
    file_path: str, 
    config: Dict[str, Any], 
    storage_client: StorageClient
) -> List[DocumentElement]:
    """
    Pure function for document partitioning.
    
    - No side effects beyond return value
    - All dependencies explicitly passed
    - All I/O operations are async
    """
    # Async file reading
    file_content = await storage_client.read_file(file_path)
    
    # Async processing with Unstructured
    elements = await process_with_unstructured_async(file_content, config)
    
    return elements
```

### Step Output Specification
Each step must provide:

1. **Status Information**: Success/failure, duration, step identification
2. **Summary Stats**: Key metrics (e.g., number of chunks created, average sizes)  
3. **Sample Outputs**: First 3-5 examples of generated content for debugging
4. **Error Details**: Comprehensive error information for failed steps

Example step result:
```json
{
  "step": "chunking",
  "status": "completed", 
  "duration_seconds": 15.3,
  "summary_stats": {
    "total_chunks": 147,
    "avg_chunk_size": 892,
    "chunks_with_tables": 23,
    "pages_processed": 45
  },
  "sample_outputs": {
    "sample_chunks": [
      "Foundation requirements for residential buildings must comply with...",
      "Insulation standards require R-value of minimum 3.5 for...",
      "Electrical installations must follow DK building code..."
    ]
  }
}
```

## 🔄 Background Processing Strategy

### FastAPI Background Tasks with Asyncio and Dependency Injection
Leveraging FastAPI's built-in background task capabilities and dependency injection for parallel document processing:

```python
# Dependency injection for shared resources
async def get_indexing_orchestrator(
    db: Database = Depends(get_database),
    storage: StorageClient = Depends(get_storage_client),
    config_manager: ConfigManager = Depends(get_config_manager),
    progress_tracker: ProgressTracker = Depends(get_progress_tracker)
) -> IndexingOrchestrator:
    """Get indexing orchestrator with all dependencies injected"""
    return IndexingOrchestrator(db, storage, config_manager, progress_tracker)

@app.post("/api/documents/upload-batch")
async def upload_multiple_pdfs(
    files: List[UploadFile],
    orchestrator: IndexingOrchestrator = Depends(get_indexing_orchestrator)
):
    """Upload multiple PDFs and start parallel indexing with dependency injection"""
    tasks = []
    for file in files:
        # Each PDF gets its own background task with injected dependencies
        task = asyncio.create_task(
            orchestrator.process_document_async(file)
        )
        tasks.append(task)
    
    # All PDFs start processing immediately in parallel
    return {"message": f"Started indexing {len(files)} documents"}

class IndexingOrchestrator:
    """Orchestrator with explicit dependency injection"""
    
    def __init__(
        self, 
        db: Database,
        storage: StorageClient, 
        config_manager: ConfigManager,
        progress_tracker: ProgressTracker
    ):
        self.db = db
        self.storage = storage
        self.config_manager = config_manager
        self.progress_tracker = progress_tracker
        
        # Initialize steps with injected dependencies
        self.partition_step = PartitionStep(
            config=self.config_manager.get_partition_config(),
            storage_client=self.storage,
            progress_tracker=self.progress_tracker
        )
        # ... initialize other steps similarly
    
    async def process_document_async(self, document_id: UUID):
        """Process a single document through all indexing steps sequentially"""
        try:
            # Sequential step execution for single document
            # All steps use async operations and injected dependencies
            partition_result = await self.partition_step.execute(document_id)
            metadata_result = await self.metadata_step.execute(partition_result)
            # ... continue through all steps
            
        except Exception as e:
            # Fail fast: stop processing on first error
            await self.mark_failed(document_id, str(e))
            raise
```

**Benefits:**
- ✅ Multiple PDFs processed simultaneously
- ✅ No additional infrastructure needed (built into FastAPI)
- ✅ Scales with server resources
- ✅ Simple to implement and maintain
- ✅ **Explicit dependency injection** for better testability
- ✅ **All I/O operations are async** for optimal performance
- ✅ **Shared resources managed by FastAPI** dependency system

## 📈 Progress Tracking

### Step-by-Step Progress Tracking with Async Operations
```python
class ProgressTracker:
    """Progress tracker with comprehensive async operations"""
    
    def __init__(self, indexing_run_id: UUID, db: Database):
        self.run_id = indexing_run_id
        self.db = db
        self.total_steps = 6  # partition, metadata, enrich, chunk, embed, store
        self.completed_steps = 0
        
    async def update_step_progress_async(self, step: str, status: str, result: StepResult):
        """Update progress in database and logs with async operations"""
        # Update indexing_runs table (async database operation)
        await self.update_run_status_async(step, status, result)
        
        # Async structured logging
        await self.log_progress_async(step, status, result)
        
        # Update completion count
        self.completed_steps += 1
        
    async def update_run_status_async(self, step: str, status: str, result: StepResult):
        """Async database update for run status"""
        query = """
            UPDATE indexing_runs 
            SET step_results = jsonb_set(step_results, $1, $2)
            WHERE id = $3
        """
        step_key = f"{{{step}}}"
        await self.db.execute(query, step_key, result.dict(), self.run_id)
        
    async def log_progress_async(self, step: str, status: str, result: StepResult):
        """Async structured logging for progress updates"""
        await logger.ainfo(
            "Step progress updated",
            run_id=self.run_id,
            step=step,
            status=status,
            completed_steps=self.completed_steps,
            total_steps=self.total_steps,
            duration_seconds=result.duration_seconds,
            summary_stats=result.summary_stats
        )
        
    async def mark_pipeline_failed_async(self, error_message: str):
        """Async failure marking"""
        await self.db.execute(
            "UPDATE indexing_runs SET status = 'failed', error_message = $1 WHERE id = $2",
            error_message, self.run_id
        )
        await logger.aerror("Pipeline failed", run_id=self.run_id, error=error_message)

# Dependency injection for progress tracker
async def get_progress_tracker(
    run_id: UUID, 
    db: Database = Depends(get_database)
) -> ProgressTracker:
    """Get progress tracker with injected database dependency"""
    return ProgressTracker(run_id, db)
```

Progress is visible through:
- **Backend logs**: Structured async logging with step progress
- **Railway logs**: Production deployment logs
- **API endpoint**: `/api/documents/{id}/status` for programmatic access
- **Database**: Real-time status in `indexing_runs` table (async updates)

## 🚨 Error Handling Strategy

### Fail Fast Approach with Async Error Handling
Both indexing and query pipelines use fail fast error handling with comprehensive async error management:

- **Stop immediately** on first error
- **No retry logic** initially (can be added later)
- **Comprehensive error logging** for debugging
- **Clear error propagation** to user interface
- **All error handling operations are async**

```python
class PipelineOrchestrator:
    async def execute_pipeline(self, steps: List[PipelineStep], input_data: Any):
        """Execute pipeline steps with fail fast error handling and async operations"""
        try:
            current_data = input_data
            for step in steps:
                # Validate prerequisites (async validation)
                if not await step.validate_prerequisites_async(current_data):
                    raise PipelineError(f"Prerequisites not met for {step.get_step_name()}")
                
                # Execute step (async execution)
                result = await step.execute(current_data)
                
                # Check for errors
                if result.status == "failed":
                    raise PipelineError(f"Step {step.get_step_name()} failed: {result.error_message}")
                
                # Update progress and continue (async progress tracking)
                await self.tracker.update_step_progress_async(step.get_step_name(), "completed", result)
                current_data = result
                
        except Exception as e:
            # Fail fast: mark entire pipeline as failed (async failure handling)
            await self.tracker.mark_pipeline_failed_async(str(e))
            await self.log_error_async(e)  # Async error logging
            raise

# Example of async error handling in steps
class PartitionStep(PipelineStep):
    async def execute(self, input_data: DocumentInput) -> StepResult:
        """Execute partition step with comprehensive async error handling"""
        start_time = time.time()
        
        try:
            # All I/O operations are async
            file_content = await self.storage_client.read_file_async(input_data.file_path)
            elements = await self.process_elements_async(file_content)
            
            # Async result processing
            result = await self.create_step_result_async(elements, start_time)
            return result
            
        except FileNotFoundError as e:
            # Async error handling
            await self.log_file_error_async(input_data.file_path, e)
            return await self.create_error_result_async("file_not_found", str(e), start_time)
            
        except ProcessingError as e:
            # Async processing error handling
            await self.log_processing_error_async(input_data.file_path, e)
            return await self.create_error_result_async("processing_failed", str(e), start_time)
            
        except Exception as e:
            # Generic async error handling
            await self.log_unexpected_error_async(input_data.file_path, e)
            return await self.create_error_result_async("unexpected_error", str(e), start_time)
```

## 🔗 API Design

### Indexing Pipeline Endpoints
```python
# Document upload and indexing management
POST /api/documents/upload          # Upload single PDF, start indexing
POST /api/documents/upload-batch    # Upload multiple PDFs, start parallel indexing
GET  /api/documents                 # List all documents with status
GET  /api/documents/{id}/status     # Get indexing progress
GET  /api/documents/{id}/steps      # View detailed step outputs
DELETE /api/documents/{id}          # Delete document and indexing data
```

### Query Pipeline Endpoints  
```python
# Real-time querying
POST /api/query                     # Ask question (immediate response)
GET  /api/query/history            # List previous queries
GET  /api/query/{id}               # Get specific query details
DELETE /api/query/{id}             # Delete query from history
```

## 📋 Implementation Phases

### Phase 2.1: Foundation (Week 3)
1. **Enhanced Pydantic Models** - Extend existing models for two-pipeline architecture
2. **Configuration Management** - Implement YAML loading and validation
3. **Basic Orchestrator Structure** - Core execution loops for both pipelines
4. **Progress Tracking System** - Database updates and structured logging
5. **Database Schema Updates** - Add indexing_runs and query_runs tables

### Phase 2.2: Indexing Pipeline (Week 4)
1. **Common Step Interface** - Abstract base class implementation ✅
2. **Partition Step Migration** - Convert notebook 01 to production step ✅
3. **Metadata Step Migration** - Convert notebook 02 to production step  
4. **Background Task Integration** - FastAPI background tasks with asyncio ✅
5. **Error Handling Implementation** - Fail fast with comprehensive logging ✅

### Phase 2.3: Step Migration Continuation (Week 4)
1. **Enrichment Step** - Convert notebook 03
2. **Chunking Step** - Convert notebook 04
3. **Embedding Step** - Convert notebook 05  
4. **Storage Step** - Convert notebook 06
5. **End-to-End Testing** - Complete indexing pipeline validation

### Phase 2.4: Query Pipeline (Week 4)
1. **Query Processing Step** - Convert notebook 07
2. **Retrieval Step** - Convert notebook 08
3. **Generation Step** - Convert notebook 11
4. **Real-time Response Optimization** - Sub-second response times
5. **Integration Testing** - Full indexing → query workflow

## ✅ Success Criteria

### Indexing Pipeline Success
- [ ] Multiple PDFs process in parallel
- [ ] Each step provides detailed output for inspection
- [ ] Progress tracking works through API and logs  
- [ ] Failed documents stop processing immediately
- [ ] All notebook functionality preserved in production steps
- [ ] **All I/O operations are async** for optimal performance
- [ ] **Dependency injection** provides clean separation of concerns
- [ ] **Pure functions** ensure testable and maintainable step logic

### Query Pipeline Success
- [ ] Sub-5-second response times for typical queries
- [ ] All query history stored in database
- [ ] Real-time pipeline separate from background indexing
- [ ] Production API matches notebook quality
- [ ] Error handling provides clear user feedback
- [ ] **Async operations** maintain responsiveness under load
- [ ] **Functional design** ensures predictable query processing

### Configuration Success
- [ ] YAML configs load and validate correctly
- [ ] Separate indexing and query configurations
- [ ] Framework ready for future UI configurability
- [ ] Configuration changes don't require code changes
- [ ] **Async config loading** prevents blocking operations
- [ ] **Pure config merging** ensures predictable behavior
- [ ] **Dependency injection** for config management

### FastAPI Best Practices Success
- [ ] **Functional step implementations** with explicit dependencies
- [ ] **Async operations throughout** the pipeline
- [ ] **Dependency injection** for all shared resources
- [ ] **Pure functions** for data transformation and validation
- [ ] **Comprehensive error handling** with async operations
- [ ] **Performance optimization** through non-blocking I/O

## 🔍 Migration Strategy

### Preserve Notebook Parameters
All working parameters from notebooks must be preserved:
- Chunking strategies and sizes
- Embedding models and dimensions
- Query processing variations
- Retrieval methods and thresholds
- Generation model settings

### Incremental Testing
Each migrated step must be thoroughly tested:
1. **Unit tests** for step logic
2. **Integration tests** with sample data
3. **Performance benchmarks** vs. notebook versions
4. **Error scenario testing**

### Configuration Validation
Robust validation ensures production reliability:
- **Schema validation** for all YAML configs
- **Parameter range validation** (e.g., chunk_size > 0)
- **Model availability validation** (API keys, model names)
- **Resource requirement validation** (memory, disk space)

This design document serves as the blueprint for implementing the production pipeline migration while maintaining the quality and functionality of the existing notebook-based system. 