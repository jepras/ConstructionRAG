# FastAPI Endpoints Implementation Guide

## Overview

This guide provides all the context and implementation details needed to create FastAPI endpoints for the Construction RAG Query Pipeline. The core pipeline is already implemented and tested - we just need to expose it via REST API endpoints.

## Current Status

### ✅ Completed Components
- **QueryPipelineOrchestrator**: Fully functional orchestrator
- **QueryProcessor**: Query variation generation (semantic, HyDE, formal)
- **DocumentRetriever**: Vector search with deduplication
- **ResponseGenerator**: OpenRouter response generation
- **Database Integration**: `query_runs` table with analytics
- **Integration Testing**: Comprehensive test suite working

### 🔄 Target: FastAPI Endpoints
- **POST /api/query**: Process construction queries
- **GET /api/query/history**: Get user query history
- **POST /api/query/{id}/feedback**: Submit user feedback
- **GET /api/query/quality-dashboard**: Admin quality metrics

## Project Structure

```
backend/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py              # Existing auth endpoints
│   │   ├── pipeline.py          # Existing indexing endpoints
│   │   └── queries.py           # NEW: Query endpoints
│   ├── pipeline/
│   │   └── querying/
│   │       ├── orchestrator.py  # QueryPipelineOrchestrator
│   │       ├── models.py        # QueryRequest, QueryResponse, etc.
│   │       └── steps/
│   │           ├── query_processing.py
│   │           ├── retrieval.py
│   │           └── generation.py
│   ├── config/
│   │   ├── database.py          # get_supabase_admin_client()
│   │   └── settings.py          # Environment variables
│   └── main.py                  # FastAPI app
├── tests/
│   └── integration/
│       └── test_query_pipeline_integration.py  # Working test
└── requirements.txt
```

## Key Models and Classes

### 1. QueryPipelineOrchestrator
**Location**: `src/pipeline/querying/orchestrator.py`

**Main Method**:
```python
async def process_query(self, request: QueryRequest) -> QueryResponse:
    """Process a query through the entire pipeline"""
```

**Usage**:
```python
orchestrator = QueryPipelineOrchestrator()
response = await orchestrator.process_query(query_request)
```

### 2. Data Models
**Location**: `src/pipeline/querying/models.py`

**Key Models**:
```python
class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    search_results: List[SearchResult]
    performance_metrics: Dict[str, Any]
    quality_metrics: QualityMetrics

class QueryFeedback(BaseModel):
    relevance_score: int = Field(ge=1, le=5)
    helpfulness_score: int = Field(ge=1, le=5)
    accuracy_score: int = Field(ge=1, le=5)
    comments: Optional[str] = None
```

## Database Schema

### query_runs Table
```sql
CREATE TABLE query_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT,
    original_query TEXT NOT NULL,
    query_variations JSONB,
    search_results JSONB,
    final_response TEXT,
    performance_metrics JSONB,
    quality_metrics JSONB,
    response_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Database Access
**Function**: `get_supabase_admin_client()` from `src/config/database.py`
**Usage**: For all database operations (read/write)

## Environment Variables

**Location**: `src/config/settings.py`

**Required Variables**:
```python
class Settings(BaseSettings):
    # Database
    supabase_url: str
    supabase_service_role_key: str
    
    # OpenRouter (for query processing and generation)
    openrouter_api_key: str
    
    # Voyage AI (for embeddings)
    voyage_api_key: str
```

## Implementation Requirements

### 1. POST /api/query
**Purpose**: Process construction-related queries

**Request**:
```json
{
    "query": "Hvad er principperne for regnvandshåndtering?",
    "user_id": "optional_user_id"
}
```

**Response**:
```json
{
    "id": "uuid",
    "response": "Baseret på de givne kilder...",
    "search_results": [
        {
            "content": "Taghaven er konstrueret...",
            "source_filename": "test-with-little-variety.pdf",
            "page_number": 4,
            "similarity_score": 0.669
        }
    ],
    "performance_metrics": {
        "model_used": "anthropic/claude-3.5-sonnet",
        "tokens_used": 1062,
        "confidence": 0.575,
        "sources_count": 3
    },
    "quality_metrics": {
        "relevance_score": 0.685,
        "confidence": "good",
        "quality_score": 0.789
    },
    "response_time_ms": 14149
}
```

**Implementation Notes**:
- Use `QueryPipelineOrchestrator.process_query()`
- Store result in `query_runs` table
- Return complete response with metadata
- Handle errors gracefully with fallback responses

### 2. GET /api/query/history
**Purpose**: Get user's query history

**Parameters**:
- `user_id`: Required user identifier
- `limit`: Optional, default 20
- `offset`: Optional, default 0

**Response**:
```json
{
    "queries": [
        {
            "id": "uuid",
            "original_query": "Hvad er principperne for regnvandshåndtering?",
            "final_response": "Baseret på de givne kilder...",
            "performance_metrics": {...},
            "quality_metrics": {...},
            "created_at": "2025-01-29T10:30:00Z"
        }
    ],
    "total_count": 25,
    "has_more": true
}
```

### 3. POST /api/query/{query_id}/feedback
**Purpose**: Submit user feedback on query results

**Request**:
```json
{
    "relevance_score": 4,
    "helpfulness_score": 5,
    "accuracy_score": 4,
    "comments": "Very helpful response about rainwater handling"
}
```

**Response**:
```json
{
    "success": true,
    "message": "Feedback submitted successfully"
}
```

**Implementation Notes**:
- Update `query_runs.quality_metrics` with user feedback
- Validate query_id exists
- Store feedback in JSONB format

### 4. GET /api/query/quality-dashboard
**Purpose**: Admin dashboard for quality metrics

**Parameters**:
- `time_period`: Optional, default "7d" (1d, 7d, 30d)

**Response**:
```json
{
    "period": "7d",
    "total_queries": 150,
    "successful_queries": 145,
    "failed_queries": 5,
    "avg_response_time_ms": 14276,
    "success_rate": 96.7,
    "avg_quality_score": 0.548,
    "quality_distribution": {
        "excellent": 45,
        "good": 60,
        "acceptable": 30,
        "poor": 15
    },
    "recent_queries": [
        {
            "query": "Hvad er principperne for regnvandshåndtering?",
            "quality_score": 0.789,
            "response_time_ms": 14149,
            "created_at": "2025-01-29T10:30:00Z"
        }
    ]
}
```

## Error Handling

### Query Processing Errors
```python
try:
    response = await orchestrator.process_query(request)
    return response
except Exception as e:
    # Store error in database
    await store_error_query(request, str(e))
    
    # Return fallback response
    return QueryResponse(
        response="Beklager, der opstod en fejl under behandling af dit spørgsmål. Prøv venligst igen.",
        search_results=[],
        performance_metrics={"error": str(e)},
        quality_metrics=QualityMetrics(relevance_score=0.0, confidence="low")
    )
```

### Database Errors
- Handle connection failures gracefully
- Use connection pooling
- Log errors for debugging

## Authentication & Authorization

### Current Auth System
**Location**: `src/api/auth.py`

**Key Functions**:
- `get_current_user()`: Get authenticated user
- `security`: HTTPBearer authentication

**Usage**:
```python
from src.api.auth import get_current_user, security

@app.post("/api/query")
async def process_query(
    request: QueryRequest,
    current_user = Depends(get_current_user)
):
    # current_user contains user information
    request.user_id = current_user.id
    return await orchestrator.process_query(request)
```

## Testing Strategy

### Integration Tests
**Location**: `tests/integration/test_query_pipeline_integration.py`

**Test Cases**:
1. Rainwater handling principles
2. Cost comparison analysis
3. Work scope definition
4. Technical specifications
5. Safety standards

**Test Results** (from current implementation):
- ✅ All 5 test cases pass
- ✅ Average response time: 14.3 seconds
- ✅ Quality scores: 0.209-0.789 range
- ✅ Success rate: 100%

### API Tests to Create
1. **POST /api/query** - Test query processing
2. **GET /api/query/history** - Test history retrieval
3. **POST /api/query/{id}/feedback** - Test feedback submission
4. **GET /api/query/quality-dashboard** - Test dashboard metrics

## Performance Considerations

### Current Performance
- **Query Processing**: ~1 second
- **Retrieval**: ~2 seconds
- **Generation**: ~5 seconds
- **Total Response Time**: ~14 seconds (acceptable for complex queries)

### Optimization Opportunities
- **Caching**: Cache frequent queries
- **Async Processing**: Background storage operations
- **Connection Pooling**: Database connection optimization

## Configuration

### Query Pipeline Config
**Location**: `backend/config/query_config.json`

**Key Settings**:
```json
{
    "query_processing": {
        "model": "openai/gpt-3.5-turbo",
        "timeout_seconds": 1.0
    },
    "retrieval": {
        "top_k": 5,
        "similarity_thresholds": {
            "excellent": 0.75,
            "good": 0.60,
            "acceptable": 0.40
        }
    },
    "generation": {
        "model": "anthropic/claude-3.5-sonnet",
        "timeout_seconds": 5.0,
        "max_tokens": 1000
    }
}
```

## Implementation Steps

### Step 1: Create queries.py
1. Create `src/api/queries.py`
2. Import required modules and classes
3. Set up FastAPI router

### Step 2: Implement POST /api/query
1. Create endpoint function
2. Add authentication dependency
3. Call `QueryPipelineOrchestrator.process_query()`
4. Handle errors and return response

### Step 3: Implement GET /api/query/history
1. Create endpoint function
2. Query `query_runs` table
3. Apply pagination
4. Return formatted response

### Step 4: Implement POST /api/query/{id}/feedback
1. Create endpoint function
2. Validate query_id exists
3. Update quality_metrics
4. Return success response

### Step 5: Implement GET /api/query/quality-dashboard
1. Create endpoint function
2. Query analytics data
3. Calculate metrics
4. Return dashboard data

### Step 6: Update main.py
1. Import queries router
2. Include router in app
3. Add route prefix

### Step 7: Create API Tests
1. Test each endpoint
2. Verify error handling
3. Check response formats

## Example Implementation

### Basic Endpoint Structure
```python
from fastapi import APIRouter, Depends, HTTPException
from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
from src.pipeline.querying.models import QueryRequest, QueryResponse
from src.api.auth import get_current_user

router = APIRouter(prefix="/api/query", tags=["queries"])

@router.post("/", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    current_user = Depends(get_current_user),
    orchestrator: QueryPipelineOrchestrator = Depends(get_orchestrator)
):
    """Process a construction-related query"""
    try:
        request.user_id = current_user.id
        response = await orchestrator.process_query(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Success Criteria

### Functional Requirements
- ✅ All 4 endpoints implemented and working
- ✅ Proper error handling and validation
- ✅ Authentication and authorization
- ✅ Database integration working
- ✅ Response formats match specifications

### Performance Requirements
- ✅ Response times under 15 seconds (already achieved)
- ✅ Error rate under 2% (already achieved)
- ✅ Success rate over 95% (already achieved)

### Testing Requirements
- ✅ All endpoints tested
- ✅ Error scenarios covered
- ✅ Authentication tested
- ✅ Database operations verified

## Notes for Implementation

1. **Use existing patterns**: Follow the same structure as `src/api/auth.py` and `src/api/pipeline.py`
2. **Leverage existing code**: The `QueryPipelineOrchestrator` is fully functional
3. **Database access**: Use `get_supabase_admin_client()` for all database operations
4. **Error handling**: Implement graceful error handling with fallback responses
5. **Testing**: Create comprehensive tests for each endpoint
6. **Documentation**: Add proper docstrings and type hints

The core pipeline is production-ready - we just need to expose it via REST API endpoints! 