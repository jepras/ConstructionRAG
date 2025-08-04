# Beam.cloud Migration Plan for ConstructionRAG Indexing Pipeline

## Overview

This document outlines the plan to migrate the ConstructionRAG indexing pipeline from Railway background tasks to Beam.cloud for improved scalability, resource management, and cost efficiency.

## Current Architecture

### Railway (Current)
```
FastAPI Upload Endpoint → Background Task → IndexingOrchestrator → 5-Step Pipeline
```

**Issues:**
- Long-running tasks (up to 30 minutes) on Railway
- Resource-intensive operations block API responsiveness
- Limited GPU access for ML operations
- Single point of failure for pipeline processing

### Beam.cloud (Target)
```
FastAPI Upload Endpoint → Beam Task Queue → IndexingOrchestrator → 5-Step Pipeline → Callback to Railway
```

**Benefits:**
- Dedicated GPU resources for ML operations
- Scalable task queue with automatic retries
- Railway remains responsive for real-time operations
- Cost-effective resource utilization

## Architecture Design

### Component Responsibilities

#### Railway Backend
- **File Upload & Storage**: Handle PDF uploads to Supabase Storage
- **Task Triggering**: Send indexing requests to Beam
- **Status Management**: Receive callbacks and update database
- **Query Pipeline**: Real-time query processing (stays on Railway)
- **API Endpoints**: User-facing operations

#### Beam.cloud Worker
- **Document Processing**: Execute 5-step indexing pipeline
- **Progress Tracking**: Real-time updates to Supabase
- **Batch Operations**: Handle single and multi-document uploads
- **Error Handling**: Comprehensive error reporting
- **Resource Management**: GPU-optimized processing

### Data Flow

```
1. User Upload → Railway API
2. Railway → Supabase Storage (file)
3. Railway → Beam Task Queue (indexing_run_id + document_ids)
4. Beam → Supabase Storage (download files)
5. Beam → Supabase (fetch configs)
6. Beam → Execute Pipeline (partition → metadata → enrichment → chunking → embedding)
7. Beam → Supabase (progress updates)
8. Beam → Railway (per-document callbacks)
9. Railway → Update final status
```

## Implementation Phases

### Phase 1: Infrastructure Setup (Week 1)

#### 1.1 Beam Configuration
- [ ] Create `beam-app.py` configuration file (Beam v2 approach)
- [ ] Set up Beam project and authentication
- [ ] Configure GPU resources (T4, 8Gi memory, 4 CPU)
- [ ] Set up secrets management for API keys

#### 1.2 Requirements Separation
- [ ] Create `beam_requirements.txt` with ML dependencies
- [ ] Clean up main `requirements.txt` for Railway
- [ ] Verify dependency compatibility

#### 1.3 Environment Configuration
- [ ] Configure Beam secrets for:
  - Supabase credentials
  - Voyage AI API key
  - OpenRouter API key
  - Anthropic API key
- [ ] Deploy to production and test Beam environment setup

### Phase 2: Core Beam Worker (Week 2)

#### 2.1 Basic Worker Structure
- [ ] Create `backend/src/pipeline/indexing/beam_worker.py`
- [ ] Create `backend/beam-app.py` with task queue configuration
- [ ] Implement basic task queue structure
- [ ] Add configuration fetching from Supabase
- [ ] Deploy and test basic Beam task execution in production

#### 2.2 Document Processing Logic
- [ ] Port `process_documents()` method to Beam
- [ ] Implement file download from Supabase Storage
- [ ] Add progress tracking integration
- [ ] Deploy and test single document processing in production

#### 2.3 Error Handling
- [ ] Implement comprehensive error handling
- [ ] Add retry logic for transient failures
- [ ] Deploy and test error scenarios in production

### Phase 3: Railway Integration (Week 3)

#### 3.1 API Endpoint Refactoring
- [ ] Modify `documents.py` upload endpoints
- [ ] Remove background task calls
- [ ] Add Beam task triggering
- [ ] Implement immediate response (202 Accepted)

#### 3.2 Callback System
- [ ] Create callback endpoint on Railway
- [ ] Implement per-document status updates
- [ ] Add error handling for failed callbacks
- [ ] Deploy and test callback reliability in production

#### 3.3 Legacy Code Cleanup
- [ ] Remove `/pipeline/indexing/start` endpoint
- [ ] Clean up unused background task functions
- [ ] Update documentation

### Phase 4: Testing & Validation (Week 4)

#### 4.1 Integration Testing
- [ ] Deploy and test single document upload flow in production
- [ ] Deploy and test multi-document batch upload in production
- [ ] Deploy and test error scenarios and recovery in production
- [ ] Validate progress tracking in production

#### 4.2 Performance Testing
- [ ] Deploy and benchmark processing times in production
- [ ] Deploy and test concurrent upload handling in production
- [ ] Deploy and validate resource utilization in production
- [ ] Compare with previous Railway performance in production

#### 4.3 Production Validation
- [ ] Monitor real-world usage in production
- [ ] Validate callback reliability in production
- [ ] Check error rates and recovery in production
- [ ] Gather performance metrics and user feedback

## Technical Implementation Details

### Beam Worker Structure

```python
# beam-app.py
from beam import Image, task_queue, env

@task_queue(
    name="construction-rag-indexing",
    cpu=4,
    memory="8Gi", 
    gpu="T4",
    image=Image(
        python_version="python3.12",
        python_packages="beam_requirements.txt",
    ),
)
def run_indexing_pipeline(
    indexing_run_id: str,
    document_ids: list,
    user_id: str,
    project_id: str
):
    return run_indexing_pipeline_on_beam(
        indexing_run_id, document_ids, user_id, project_id
    )

# beam_worker.py
async def run_indexing_pipeline_on_beam(
    indexing_run_id: str,
    document_ids: List[str],
    user_id: str,
    project_id: str
):
    # 1. Initialize services
    # 2. Fetch configuration from Supabase
    # 3. Download documents from Supabase Storage
    # 4. Execute process_documents()
    # 5. Send per-document callbacks
```

### Configuration Management

```python
# Beam fetches configs at runtime
config_manager = ConfigManager(db)
config = await config_manager.get_stored_run_config(indexing_run_id)
```

### Callback Structure

```python
# Per-document callback
{
    "indexing_run_id": str,
    "document_id": str,
    "status": "individual_steps_complete" | "failed" | "completed",
    "step_results": {...},
    "error_message": str  # if failed
}

# Final batch callback
{
    "indexing_run_id": str,
    "status": "completed" | "failed",
    "document_results": {
        "successful": [doc_id1, doc_id2],
        "failed": [doc_id3]
    },
    "embedding_stats": {...}
}
```

## Testing Strategy

### Production Testing
- [ ] Deploy Beam worker and test in production
- [ ] Validate Supabase interactions in real environment
- [ ] Test configuration fetching from production database
- [ ] Validate error handling in production

### Integration Testing
- [ ] Deploy and test end-to-end upload → processing → callback flow in production
- [ ] Test with real PDF files in production environment
- [ ] Validate database state consistency in production
- [ ] Test concurrent processing in production

### Load Testing
- [ ] Deploy and test multiple simultaneous uploads in production
- [ ] Validate Beam queue handling in production
- [ ] Monitor resource utilization in production
- [ ] Test callback reliability under load in production

### Error Testing
- [ ] Deploy and test network failures during processing in production
- [ ] Deploy and test invalid file formats in production
- [ ] Deploy and test API key failures in production
- [ ] Deploy and test database connection issues in production

## Risk Mitigation

### High-Risk Areas
1. **Callback Reliability**: If callbacks fail, Railway won't know processing is complete
2. **Configuration Sync**: Beam must have access to correct pipeline configs
3. **File Access**: Beam must reliably download files from Supabase Storage
4. **Error Propagation**: Errors must be properly communicated back to Railway

### Mitigation Strategies
1. **Redundant Callbacks**: Implement retry logic for failed callbacks
2. **Configuration Validation**: Verify configs before processing starts
3. **File Validation**: Check file integrity after download
4. **Comprehensive Logging**: Log all operations for debugging

## Success Metrics

### Performance
- [ ] Processing time < 30 minutes for large documents
- [ ] Railway API response time < 2 seconds
- [ ] 99%+ callback success rate
- [ ] Zero data loss during processing

### Reliability
- [ ] 99.9% uptime for Beam workers
- [ ] Automatic recovery from transient failures
- [ ] Proper error reporting and logging
- [ ] Graceful degradation under load

### Cost Efficiency
- [ ] Reduced Railway resource usage
- [ ] Optimized GPU utilization on Beam
- [ ] Predictable cost per document processed
- [ ] No idle resource consumption

## Rollback Plan

If issues arise during migration:

1. **Immediate Rollback**: Revert to Railway background tasks
2. **Gradual Migration**: Process subset of documents on Beam
3. **Monitoring**: Enhanced monitoring during transition
4. **Documentation**: Keep Railway code functional during transition

## Post-Migration Tasks

### Optimization
- [ ] Fine-tune Beam resource allocation
- [ ] Optimize batch processing parameters
- [ ] Implement advanced error recovery
- [ ] Add performance monitoring

### Feature Enhancements
- [ ] Real-time progress streaming
- [ ] Advanced queue management
- [ ] Predictive resource scaling
- [ ] Enhanced error reporting

## Conclusion

This migration will significantly improve the ConstructionRAG system's scalability and reliability while maintaining the existing user experience. The phased approach ensures minimal disruption and allows for thorough testing at each stage.

The key success factors are:
1. **Thorough testing** at each phase
2. **Comprehensive error handling**
3. **Reliable callback system**
4. **Proper resource management**

By following this plan, we can successfully migrate the indexing pipeline to Beam.cloud while maintaining system reliability and user satisfaction. 