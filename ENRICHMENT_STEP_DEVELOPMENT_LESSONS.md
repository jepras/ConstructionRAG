# Enrichment Step Development Lessons

## Overview
This document captures the key lessons learned during the development of the enrichment step for the ConstructionRAG pipeline. The enrichment step adds VLM (Vision Language Model) captions to tables and images extracted from construction documents.

## Architecture Decisions

### 1. Storage Security: Signed URLs vs Public URLs
**Problem**: Initially used public URLs for Supabase storage, which created security vulnerabilities.

**Solution**: Implemented signed URLs with time-limited access tokens.

**Implementation**:
```python
# Before (insecure)
url = self.supabase.storage.from_(self.bucket_name).get_public_url(storage_path)

# After (secure)
url = self.supabase.storage.from_(self.bucket_name).create_signed_url(
    storage_path,
    expires_in=3600 * 24 * 7,  # 7 days
)
```

**Benefits**:
- Secure access to private storage buckets
- Time-limited access tokens
- Works with external APIs (VLM services)
- No need to make buckets public

### 2. Orchestrator Integration Pattern
**Pattern**: Single step execution through orchestrator context.

**Key Principles**:
- Each step can be executed independently
- Steps receive data from previous steps
- Results are stored in database with run ID
- Consistent error handling and logging

**Example Integration Test Structure**:
```python
# Initialize orchestrator
orchestrator = IndexingOrchestrator(db=db, pipeline_service=pipeline_service)
await orchestrator.initialize_steps(user_id=UUID(user_id))

# Execute step with previous step's result
enrichment_result = await orchestrator.enrichment_step.execute(metadata_result)

# Store result
await pipeline_service.store_step_result(
    indexing_run_id=indexing_run.id,
    step_name="enrichment",
    step_result=enrichment_result,
)
```

## Data Formats

### Input Data Structure (from Metadata Step)
The enrichment step expects metadata step output with this structure:

```json
{
  "text_elements": [
    {
      "id": "1",
      "page": 1,
      "text": "1.2 Demonstrationsejendommen",
      "category": "Header",
      "metadata": {
        "filename": "test-with-little-variety.pdf",
        "page_number": 1
      },
      "structural_metadata": {
        "element_id": "1",
        "has_numbers": true,
        "page_number": 1,
        "content_type": "text",
        "content_length": 28,
        "source_filename": "test-with-little-variety.pdf",
        "text_complexity": "complex",
        "element_category": "Header",
        "processing_strategy": "unified_fast_vision",
        "section_title_pattern": "1.2 Demonstrationsejendommen",
        "section_title_category": "1.2 Demonstrationsejendommen",
        "section_title_inherited": "1.2 Demonstrationsejendommen"
      }
    }
  ],
  "table_elements": [
    {
      "id": "table_125",
      "page": 5,
      "text": "Aktiviteter Vanskelig sag Normal sag Bemærkninger",
      "category": "Table",
      "metadata": {
        "image_url": "https://lvvykzddbyrxcxgiahuo.supabase.co/storage/v1/object/sign/pipeline-assets/...",
        "image_path": "/var/folders/.../table-5-1.jpg",
        "page_number": 5,
        "image_storage_path": "429d7943-284c-4c52-805a-bcc3e02dd285/processing/550e8400-e29b-41d4-a716-446655440000/table-images/table-5-1.jpg"
      },
      "structural_metadata": {
        "html_text": "",
        "element_id": "77",
        "has_numbers": false,
        "page_number": 5,
        "content_type": "table",
        "content_length": 49,
        "source_filename": "Unknown",
        "text_complexity": "complex",
        "element_category": "Table",
        "has_tables_on_page": true,
        "processing_strategy": "unified_fast_vision",
        "section_title_pattern": null,
        "section_title_category": null,
        "section_title_inherited": "1.2 Demonstrationsejendommen"
      }
    }
  ],
  "extracted_pages": {
    "1": {
      "dpi": 144,
      "url": "https://lvvykzddbyrxcxgiahuo.supabase.co/storage/v1/object/sign/pipeline-assets/...",
      "width": 1190,
      "height": 1682,
      "filename": "test-with-little-variety_page01_complex_68d60de7.png",
      "complexity": "complex",
      "image_type": "extracted_page",
      "storage_path": "429d7943-284c-4c52-805a-bcc3e02dd285/processing/550e8400-e29b-41d4-a716-446655440000/extracted-pages/test-with-little-variety_page01_complex_68d60de7.png",
      "structural_metadata": {
        "element_id": "78",
        "page_number": 1,
        "content_type": "full_page_with_images",
        "page_context": "image_page",
        "image_filepath": "",
        "source_filename": "test-with-little-variety_page01_complex_68d60de7.png",
        "text_complexity": "complex",
        "element_category": "ExtractedPage",
        "has_images_on_page": true,
        "processing_strategy": "unified_fast_vision",
        "section_title_pattern": null,
        "section_title_category": null,
        "section_title_inherited": "1.2 Demonstrationsejendommen"
      },
      "original_image_count": 9,
      "original_table_count": 0
    }
  },
  "page_sections": {
    "1": "1.2 Demonstrationsejendommen"
  }
}
```

### Output Data Structure (Enriched Data)
The enrichment step adds `enrichment_metadata` to tables and images:

```json
{
  "text_elements": [...], // Unchanged
  "table_elements": [
    {
      "id": "table_125",
      "page": 5,
      "text": "Aktiviteter Vanskelig sag Normal sag Bemærkninger",
      "category": "Table",
      "metadata": {...},
      "structural_metadata": {...},
      "enrichment_metadata": {
        "vlm_model": "anthropic/claude-3-5-sonnet",
        "vlm_processed": true,
        "vlm_processing_timestamp": "2025-07-30T12:11:30.397480",
        "vlm_processing_error": null,
        "table_html_caption": "Tabel 2. Skøn over timeforbrug og udlæg til udarbejdelse af tilbud fra B. Nygaard Sørensen A/S...",
        "table_image_caption": "Denne tabel viser en oversigt over aktiviteter, vanskelige sager, normale sager og bemærkninger...",
        "table_image_filepath": "https://lvvykzddbyrxcxgiahuo.supabase.co/storage/v1/object/sign/pipeline-assets/...",
        "caption_word_count": 82,
        "processing_duration_seconds": 0.400428
      }
    }
  ],
  "extracted_pages": {
    "1": {
      "dpi": 144,
      "url": "https://lvvykzddbyrxcxgiahuo.supabase.co/storage/v1/object/sign/pipeline-assets/...",
      "width": 1190,
      "height": 1682,
      "filename": "test-with-little-variety_page01_complex_68d60de7.png",
      "complexity": "complex",
      "image_type": "extracted_page",
      "storage_path": "...",
      "structural_metadata": {...},
      "original_image_count": 9,
      "original_table_count": 0,
      "enrichment_metadata": {
        "vlm_model": "anthropic/claude-3-5-sonnet",
        "vlm_processed": true,
        "vlm_processing_timestamp": "2025-07-30T12:11:30.397480",
        "vlm_processing_error": null,
        "full_page_image_caption": "Denne side viser en kompleks byggeplan med flere tekniske detaljer...",
        "full_page_image_filepath": "https://lvvykzddbyrxcxgiahuo.supabase.co/storage/v1/object/sign/pipeline-assets/...",
        "page_text_context": "1.2 Demonstrationsejendommen\nBEDRE BYGGEETIK\nMinimeret udbudsmateriale...",
        "caption_word_count": 131,
        "processing_duration_seconds": 0.400428
      }
    }
  },
  "page_sections": {...} // Unchanged
}
```

## Testing Patterns

### 1. Integration Test Structure
**File Location**: `backend/tests/integration/test_[step_name]_orchestrator.py`

**Pattern**:
```python
#!/usr/bin/env python3
"""
Integration test for [step_name] step through orchestrator
"""

import asyncio
import os
import sys
from uuid import UUID
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from config.database import get_supabase_admin_client
from pipeline.indexing.orchestrator import get_indexing_orchestrator
from pipeline.shared.models import DocumentInput
from services.pipeline_service import PipelineService

async def test_[step_name]_step_orchestrator():
    """Test [step_name] step through orchestrator"""
    try:
        # Configuration
        existing_run_id = "specific-run-id-if-testing-existing-data"
        
        # Get orchestrator with admin client
        db = get_supabase_admin_client()
        pipeline_service = PipelineService(use_admin_client=True)
        
        orchestrator = IndexingOrchestrator(
            db=db,
            pipeline_service=pipeline_service,
        )
        
        # Initialize steps
        await orchestrator.initialize_steps(user_id=UUID(user_id))
        
        # Execute step
        result = await orchestrator.[step_name]_step.execute(input_data)
        
        # Store result
        await pipeline_service.store_step_result(
            indexing_run_id=UUID(run_id),
            step_name="[step_name]",
            step_result=result,
        )
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_[step_name]_step_orchestrator())
    if success:
        print("\n✅ [Step name] step orchestrator test successful!")
    else:
        print("\n❌ [Step name] step orchestrator test failed!")
        sys.exit(1)
```

### 2. Full Pipeline Integration Test
**File Location**: `backend/tests/integration/test_pipeline_integration.py`

**Purpose**: Tests multiple steps working together sequentially.

**Pattern**:
```python
# Test Step 1: Partition
partition_result = await orchestrator.partition_step.execute(document_input)
await pipeline_service.store_step_result(indexing_run_id, "partition", partition_result)

# Test Step 2: Metadata  
metadata_result = await orchestrator.metadata_step.execute(str(indexing_run.id))
await pipeline_service.store_step_result(indexing_run_id, "metadata", metadata_result)

# Test Step 3: Enrichment
enrichment_result = await orchestrator.enrichment_step.execute(metadata_result)
await pipeline_service.store_step_result(indexing_run_id, "enrichment", enrichment_result)
```

### 3. Running Tests
**Activate Virtual Environment**:
```bash
cd backend
source ../venv/bin/activate
```

**Run Individual Step Test**:
```bash
python tests/integration/test_enrichment_step_orchestrator.py
```

**Run Full Pipeline Test**:
```bash
python tests/integration/test_pipeline_integration.py
```

## Environment Configuration

### Required Environment Variables
```bash
# Database (Supabase)
SUPABASE_URL=your_supabase_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here

# AI/ML APIs
OPENAI_API_KEY=your_openai_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here  # For VLM processing
VOYAGE_API_KEY=your_voyage_api_key_here

# Server
HOST=0.0.0.0
PORT=8000
```

### Settings Configuration
**File**: `backend/src/config/settings.py`

**Add new API keys**:
```python
class Settings(BaseSettings):
    # AI/ML APIs
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None  # Added for VLM
    voyage_api_key: Optional[str] = None
    # ... other settings
```

## Key Lessons Learned

### 1. Storage Security
- **Always use signed URLs** for private storage buckets
- **Never make buckets public** for security-sensitive data
- **Time-limit signed URLs** (7 days is reasonable for processing)

### 2. Step Integration
- **Each step should be independently testable**
- **Use orchestrator pattern** for consistent execution
- **Store results in database** for persistence and debugging
- **Pass data between steps** rather than regenerating

### 3. Error Handling
- **Graceful degradation** when VLM APIs fail
- **Detailed error logging** for debugging
- **Continue processing** even if some elements fail

### 4. Testing Strategy
- **Integration tests** for step interactions
- **Individual step tests** for isolated functionality
- **Full pipeline tests** for end-to-end validation
- **Use real data** when possible for realistic testing

### 5. Data Validation
- **Validate input structure** before processing
- **Check prerequisites** (API keys, storage access)
- **Verify output format** matches expectations

## Next Steps for RAG Pipeline

### 4. Chunking Step
**Purpose**: Segment enriched text into searchable chunks.

**Input**: Enriched data from enrichment step
**Output**: Chunked text with metadata and embeddings

**Data Format**:
```json
{
  "chunks": [
    {
      "id": "chunk_1",
      "text": "Enriched text content...",
      "metadata": {
        "source_element_id": "1",
        "source_page": 1,
        "chunk_type": "text|table|image",
        "enrichment_metadata": {...}
      },
      "structural_metadata": {...}
    }
  ]
}
```

### 5. Embedding Step
**Purpose**: Generate vector embeddings for chunks.

**Input**: Chunked data from chunking step
**Output**: Chunks with vector embeddings

### 6. Storage Step
**Purpose**: Store vectors in vector database.

**Input**: Embedded chunks from embedding step
**Output**: Indexed vectors ready for retrieval

## Performance Considerations

### VLM Processing
- **Async processing** for multiple images/tables
- **Rate limiting** to avoid API quotas
- **Error retry logic** for transient failures
- **Caching** for repeated requests

### Storage Operations
- **Batch uploads** for multiple files
- **Signed URL generation** on-demand
- **Cleanup** of temporary files
- **Monitoring** of storage usage

### Database Operations
- **Transaction handling** for step results
- **Indexing** for efficient queries
- **Backup** of processing results
- **Cleanup** of old runs

## Monitoring and Debugging

### Logging
- **Structured logging** with step context
- **Performance metrics** (duration, success rates)
- **Error tracking** with stack traces
- **API usage** monitoring

### Metrics to Track
- **Processing time** per step
- **Success rates** for VLM calls
- **Storage usage** and costs
- **API quota** consumption
- **Error frequencies** by type

This document should serve as a guide for implementing the remaining RAG pipeline steps while maintaining consistency with the established patterns and lessons learned. 