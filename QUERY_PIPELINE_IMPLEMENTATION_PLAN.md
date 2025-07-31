# Query Pipeline Implementation Plan

## Overview

This document outlines the implementation of the real-time query pipeline for the Construction RAG system. Unlike the indexing pipeline which processes documents in the background, the query pipeline must provide fast, user-facing responses to construction-related questions.

## Architecture Approach

### Lightweight Orchestrator Design
We'll implement a lightweight orchestrator that provides:
- **Minimal performance overhead** (~0.1% slower than direct functions)
- **Built-in observability** and monitoring
- **Easy extensibility** for future features (reranking, context enrichment)
- **Clean separation of concerns** between components

### Data Flow
```
User Query → FastAPI Endpoint → Query Orchestrator → Response
                ↓
        ┌─────────────────────────────────────┐
        │         QUERY PIPELINE              │
        │                                     │
        │  ┌─────────────────────────────┐    │
        │  │  1. Query Processing        │    │
        │  │     (Parallel)              │    │
        │  │  ┌─────────┐ ┌─────────┐   │    │
        │  │  │Semantic │ │  HyDE   │   │    │
        │  │  │Expansion│ │Document │   │    │
        │  │  └─────────┘ └─────────┘   │    │
        │  │  ┌─────────┐               │    │
        │  │  │ Formal  │               │    │
        │  │  │Variation│               │    │
        │  │  └─────────┘               │    │
        │  └─────────────────────────────┘    │
        │                                     │
        │  ┌─────────────────────────────┐    │
        │  │  2. Retrieval               │    │
        │  │     (Sequential)            │    │
        │  │  ┌─────────┐               │    │
        │  │  │ pgvector │               │    │
        │  │  │  Search  │               │    │
        │  │  └─────────┘               │    │
        │  └─────────────────────────────┘    │
        │                                     │
        │  ┌─────────────────────────────┐    │
        │  │  3. Generation              │    │
        │  │     (Immediate)             │    │
        │  │  ┌─────────┐               │    │
        │  │  │OpenRouter│               │    │
        │  │  │Response │               │    │
        │  │  └─────────┘               │    │
        │  └─────────────────────────────┘    │
        └─────────────────────────────────────┘
                ↓
        ┌─────────────────────────────────────┐
        │         DATABASE STORAGE            │
        │                                     │
        │  ┌─────────────────────────────┐    │
        │  │    query_runs table         │    │
        │  │  - Store query & response   │    │
        │  │  - Store performance metrics│    │
        │  │  - Store search results     │    │
        │  └─────────────────────────────┘    │
        │                                     │
        │  ┌─────────────────────────────┐    │
        │  │   document_chunks table     │    │
        │  │  - Read-only vector search  │    │
        │  │  - No writes during query   │    │
        │  └─────────────────────────────┘    │
        └─────────────────────────────────────┘
```

## Folder Structure

### New Files to Create

```
backend/src/pipeline/querying/
├── __init__.py
├── orchestrator.py              # Main orchestrator class
├── steps/
│   ├── __init__.py
│   ├── query_processing.py      # Query variation generation
│   ├── retrieval.py             # Vector search with pgvector
│   └── generation.py            # Response generation with OpenRouter
├── config/
│   └── query_config.yaml        # Query pipeline configuration
├── models.py                    # Query-specific data models
├── monitor.py                   # Performance monitoring
└── utils.py                     # Query pipeline utilities

backend/src/api/
├── queries.py                   # Query API endpoints (new)

backend/src/models/
├── query.py                     # Query request/response models (new)

backend/supabase/migrations/
├── 20250129000000_add_query_runs_table.sql  # New migration
```

### Modified Files

```
backend/src/pipeline/
├── shared/
│   ├── base_step.py             # Extend for query steps
│   └── config_manager.py        # Add query config support

backend/src/main.py              # Add query endpoints
```

## Implementation Details

### 1. Query Processing Step

**Purpose**: Generate multiple query variations to improve retrieval quality

**Components**:
- **Semantic Expansion**: Generate Danish alternatives using OpenRouter
- **HyDE Document**: Generate hypothetical answer document
- **Formal Variation**: Create formal Danish construction query

**Configuration**:
```yaml
query_processing:
  provider: "openrouter"
  model: "openai/gpt-3.5-turbo"  # Fast model for variations
  fallback_models: ["anthropic/claude-3-haiku"]
  timeout_seconds: 1.0
  max_tokens: 200
  temperature: 0.1
  
  variations:
    semantic_expansion: true
    hyde_document: true
    formal_variation: true
    parallel_generation: true
```

**Implementation**:
```python
class QueryProcessor:
    async def process(self, query: str) -> QueryVariations:
        """Generate query variations in parallel"""
        tasks = {
            'semantic': self.generate_semantic_expansion(query),
            'hyde': self.generate_hyde_document(query),
            'formal': self.generate_formal_variation(query)
        }
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        return QueryVariations(
            original=query,
            semantic=results[0] if not isinstance(results[0], Exception) else query,
            hyde=results[1] if not isinstance(results[1], Exception) else query,
            formal=results[2] if not isinstance(results[2], Exception) else query
        )
```

### 2. Retrieval Step

**Purpose**: Search document chunks using vector similarity

**Components**:
- **Query Embedding**: Embed query using same Voyage model as documents
- **Vector Search**: Search pgvector using cosine distance
- **Result Filtering**: Apply similarity thresholds

**Configuration**:
```yaml
retrieval:
  embedding_model: "${EMBEDDING_CONFIG.model}"  # Reference config file
  dimensions: "${EMBEDDING_CONFIG.dimensions}"  # Reference config file
  similarity_metric: "cosine"                   # <=> operator
  top_k: 5
  similarity_thresholds:
    excellent: 0.75
    good: 0.60
    acceptable: 0.40
    minimum: 0.25
  danish_thresholds:
    excellent: 0.70
    good: 0.55
    acceptable: 0.35
    minimum: 0.20
```

**Implementation**:
```python
class DocumentRetriever:
    async def search(self, variations: QueryVariations) -> List[SearchResult]:
        """Search documents using best query variation"""
        
        # Select best variation (or use all and combine)
        best_query = self.select_best_variation(variations)
        
        # Embed query using same model as documents
        query_embedding = await self.embed_query(best_query)
        
        # Search pgvector using embedding_1024 column
        results = await self.search_pgvector(query_embedding)
        
        # Filter by similarity threshold
        filtered_results = self.filter_by_similarity(results)
        
        return filtered_results
```

### 3. Generation Step

**Purpose**: Generate final response from retrieved documents

**Components**:
- **Context Preparation**: Format retrieved documents for LLM
- **Response Generation**: Generate answer using OpenRouter
- **Citation Addition**: Include source documents

**Configuration**:
```yaml
generation:
  provider: "openrouter"
  model: "anthropic/claude-3.5-sonnet"  # Better model for responses
  fallback_models: ["openai/gpt-4", "meta-llama/llama-3.1-8b-instruct"]
  timeout_seconds: 5.0
  max_tokens: 1000
  temperature: 0.1
  
  response_format:
    include_citations: true
    include_confidence: true
    language: "danish"
```

**Implementation**:
```python
class ResponseGenerator:
    async def generate(self, query: str, results: List[SearchResult]) -> str:
        """Generate response from search results"""
        
        # Prepare context
        context = self.prepare_context(results)
        
        # Generate response
        response = await self.generate_with_openrouter(query, context)
        
        # Add citations
        response_with_citations = self.add_citations(response, results)
        
        return response_with_citations
```

### 4. Orchestrator

**Purpose**: Coordinate all query pipeline steps with monitoring

**Implementation**:
```python
class QueryOrchestrator:
    def __init__(self, config: QueryConfig):
        self.config = config
        self.monitor = QueryMonitor()
        self.query_processor = QueryProcessor(config)
        self.retriever = DocumentRetriever(config)
        self.generator = ResponseGenerator(config)
        
    async def process_query(self, query: str, user_id: str) -> QueryResponse:
        """Process query with built-in monitoring"""
        
        # Step 1: Query Processing
        with self.monitor.span("query_processing"):
            variations = await self.query_processor.process(query)
            
        # Step 2: Retrieval
        with self.monitor.span("retrieval"):
            results = await self.retriever.search(variations)
            
        # Step 3: Generation
        with self.monitor.span("generation"):
            response = await self.generator.generate(query, results)
            
        # Step 4: Store for analytics (async)
        asyncio.create_task(
            self.store_query_run(user_id, query, variations, results, response)
        )
        
        return QueryResponse(
            response=response,
            search_results=results,
            performance_metrics=self.monitor.get_metrics()
        )
```

## Database Schema

### New Table: query_runs

```sql
-- Migration: 20250129000000_add_query_runs_table.sql
CREATE TABLE query_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    original_query TEXT NOT NULL,
    query_variations JSONB,  -- Store all variations
    selected_variation TEXT, -- Which variation was used
    search_results JSONB,    -- Store top results with scores
    final_response TEXT,
    performance_metrics JSONB, -- Timing and other metrics
    quality_metrics JSONB,   -- Relevance scores, user feedback
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for performance
CREATE INDEX idx_query_runs_user_id ON query_runs(user_id);
CREATE INDEX idx_query_runs_created_at ON query_runs(created_at);
```

### document_chunks Table (Existing - Read Only)

```sql
-- This table already exists from indexing pipeline
-- We only READ from it during queries using embedding_1024 column
SELECT content, metadata, embedding_1024 
FROM document_chunks 
WHERE embedding_1024 <=> $1 < 0.3  -- Cosine distance threshold
ORDER BY embedding_1024 <=> $1 
LIMIT 5;
```

## Quality Analysis Methods

### 1. Automatic Quality Metrics

**Similarity Score Analysis**:
```python
def analyze_similarity_scores(results: List[SearchResult]) -> QualityMetrics:
    """Analyze similarity scores for quality assessment"""
    
    if not results:
        return QualityMetrics(relevance_score=0.0, confidence="low")
    
    similarities = [r.similarity_score for r in results]
    avg_similarity = sum(similarities) / len(similarities)
    max_similarity = max(similarities)
    
    # Determine confidence level
    if max_similarity >= 0.75:
        confidence = "excellent"
    elif max_similarity >= 0.60:
        confidence = "good"
    elif max_similarity >= 0.40:
        confidence = "acceptable"
    else:
        confidence = "low"
    
    return QualityMetrics(
        relevance_score=avg_similarity,
        confidence=confidence,
        top_similarity=max_similarity,
        result_count=len(results)
    )
```

**Content Diversity Analysis**:
```python
def analyze_content_diversity(results: List[SearchResult]) -> DiversityMetrics:
    """Analyze diversity of retrieved content"""
    
    # Check if results come from different documents
    source_docs = set(r.source_filename for r in results)
    doc_diversity = len(source_docs) / len(results)
    
    # Check if results cover different pages
    page_numbers = [r.page_number for r in results]
    page_spread = max(page_numbers) - min(page_numbers) if page_numbers else 0
    
    return DiversityMetrics(
        document_diversity=doc_diversity,
        page_spread=page_spread,
        unique_sources=len(source_docs)
    )
```

### 2. Response Quality Assessment

**Response Completeness**:
```python
def assess_response_quality(response: str, query: str) -> ResponseQuality:
    """Assess quality of generated response"""
    
    # Check response length
    response_length = len(response.split())
    
    # Check if response addresses the query
    query_keywords = set(query.lower().split())
    response_keywords = set(response.lower().split())
    keyword_coverage = len(query_keywords.intersection(response_keywords)) / len(query_keywords)
    
    # Check for citations
    has_citations = "[" in response and "]" in response
    
    return ResponseQuality(
        length_score=min(response_length / 100, 1.0),  # Normalize to 0-1
        keyword_coverage=keyword_coverage,
        has_citations=has_citations,
        overall_score=(keyword_coverage + (1 if has_citations else 0)) / 2
    )
```

### 3. User Feedback Integration

**Feedback Collection**:
```python
@app.post("/api/query/{query_id}/feedback")
async def submit_query_feedback(
    query_id: UUID,
    feedback: QueryFeedback
):
    """Collect user feedback on query results"""
    
    await db.execute("""
        UPDATE query_runs 
        SET quality_metrics = jsonb_set(
            COALESCE(quality_metrics, '{}'),
            '{user_feedback}',
            $1
        )
        WHERE id = $2
    """, [feedback.dict(), query_id])
```

**Feedback Model**:
```python
class QueryFeedback(BaseModel):
    relevance_score: int = Field(ge=1, le=5)  # 1-5 scale
    helpfulness_score: int = Field(ge=1, le=5)
    accuracy_score: int = Field(ge=1, le=5)
    comments: Optional[str] = None
```

### 4. Quality Thresholds and Decision Making

**Quality Decision Logic**:
```python
def determine_response_quality(
    similarity_metrics: QualityMetrics,
    diversity_metrics: DiversityMetrics,
    response_quality: ResponseQuality
) -> QualityDecision:
    """Determine overall quality and suggest improvements"""
    
    # Calculate overall quality score
    overall_score = (
        similarity_metrics.relevance_score * 0.4 +
        diversity_metrics.document_diversity * 0.2 +
        response_quality.overall_score * 0.4
    )
    
    # Determine quality level
    if overall_score >= 0.8:
        quality_level = "excellent"
        suggestions = []
    elif overall_score >= 0.6:
        quality_level = "good"
        suggestions = ["Consider expanding query for more specific results"]
    elif overall_score >= 0.4:
        quality_level = "acceptable"
        suggestions = [
            "Query may need refinement",
            "Consider adding more context to question"
        ]
    else:
        quality_level = "poor"
        suggestions = [
            "Query too vague or specific",
            "Consider rephrasing question",
            "May need additional documents in collection"
        ]
    
    return QualityDecision(
        overall_score=overall_score,
        quality_level=quality_level,
        suggestions=suggestions,
        confidence=similarity_metrics.confidence
    )
```

### 5. Continuous Quality Monitoring

**Quality Dashboard Metrics**:
```python
class QualityDashboard:
    async def get_quality_metrics(self, time_period: str = "7d") -> QualityReport:
        """Generate quality report for monitoring"""
        
        # Get recent queries
        recent_queries = await self.get_recent_queries(time_period)
        
        # Calculate metrics
        avg_similarity = sum(q.similarity_score for q in recent_queries) / len(recent_queries)
        avg_response_quality = sum(q.response_quality for q in recent_queries) / len(recent_queries)
        user_satisfaction = sum(q.user_feedback for q in recent_queries) / len(recent_queries)
        
        return QualityReport(
            period=time_period,
            total_queries=len(recent_queries),
            avg_similarity_score=avg_similarity,
            avg_response_quality=avg_response_quality,
            user_satisfaction=user_satisfaction,
            quality_trends=self.calculate_trends(recent_queries)
        )
```

## Configuration

### query_config.yaml

```yaml
# Query Pipeline Configuration
query_pipeline:
  # Query Processing
  query_processing:
    provider: "openrouter"
    model: "openai/gpt-3.5-turbo"
    fallback_models: ["anthropic/claude-3-haiku"]
    timeout_seconds: 1.0
    max_tokens: 200
    temperature: 0.1
    
    variations:
      semantic_expansion: true
      hyde_document: true
      formal_variation: true
      parallel_generation: true
  
  # Retrieval - References embedding config for consistency
  retrieval:
    embedding_model: "${EMBEDDING_CONFIG.model}"  # voyage-multilingual-2
    dimensions: "${EMBEDDING_CONFIG.dimensions}"  # 1024
    similarity_metric: "cosine"
    top_k: 5
    similarity_thresholds:
      excellent: 0.75
      good: 0.60
      acceptable: 0.40
      minimum: 0.25
    danish_thresholds:
      excellent: 0.70
      good: 0.55
      acceptable: 0.35
      minimum: 0.20
  
  # Generation
  generation:
    provider: "openrouter"
    model: "anthropic/claude-3.5-sonnet"
    fallback_models: ["openai/gpt-4", "meta-llama/llama-3.1-8b-instruct"]
    timeout_seconds: 5.0
    max_tokens: 1000
    temperature: 0.1
    
    response_format:
      include_citations: true
      include_confidence: true
      language: "danish"
  
  # Quality Analysis
  quality_analysis:
    enable_automatic_metrics: true
    enable_user_feedback: true
    quality_thresholds:
      excellent: 0.8
      good: 0.6
      acceptable: 0.4
      poor: 0.2
    
    monitoring:
      enable_dashboard: true
      retention_days: 30
      alert_threshold: 0.5  # Alert if avg quality drops below 0.5
```

## API Endpoints

### Query Endpoints

```python
# POST /api/query
@app.post("/api/query")
async def process_query(
    query_request: QueryRequest,
    orchestrator: QueryOrchestrator = Depends(get_query_orchestrator)
):
    """Process a construction-related query"""
    return await orchestrator.process_query(
        query_request.query, 
        query_request.user_id
    )

# GET /api/query/history
@app.get("/api/query/history")
async def get_query_history(
    user_id: str,
    limit: int = 20,
    offset: int = 0
):
    """Get user's query history"""
    return await get_user_query_history(user_id, limit, offset)

# POST /api/query/{query_id}/feedback
@app.post("/api/query/{query_id}/feedback")
async def submit_feedback(
    query_id: UUID,
    feedback: QueryFeedback
):
    """Submit feedback on query results"""
    return await submit_query_feedback(query_id, feedback)

# GET /api/query/quality-dashboard
@app.get("/api/query/quality-dashboard")
async def get_quality_dashboard(
    time_period: str = "7d"
):
    """Get quality metrics dashboard"""
    return await get_quality_metrics(time_period)
```

## Implementation Phases

### Phase 1: Core Pipeline (Week 1)
1. **Basic orchestrator structure**
2. **Query processing step** (OpenRouter integration)
3. **Retrieval step** (pgvector search)
4. **Generation step** (OpenRouter response)
5. **Basic monitoring**

### Phase 2: Quality Analysis (Week 2)
1. **Automatic quality metrics**
2. **Response quality assessment**
3. **User feedback collection**
4. **Quality dashboard**

### Phase 3: Optimization (Week 3)
1. **Performance tuning**
2. **Threshold optimization**
3. **Error handling improvements**
4. **Advanced monitoring**

### Phase 4: Future Enhancements (Week 4+)
1. **Reranking implementation**
2. **Context enrichment**
3. **LangChain integration**
4. **Advanced analytics**

## Success Criteria

### Performance Targets
- **Query processing**: <1 second for variations
- **Retrieval**: <2 seconds for vector search
- **Generation**: <5 seconds for response
- **Total response time**: <8 seconds

### Quality Targets
- **Average similarity score**: >0.6 for Danish content
- **User satisfaction**: >4.0/5.0
- **Response relevance**: >80% keyword coverage
- **Citation accuracy**: >90% correct sources

### Monitoring Targets
- **System uptime**: >99.5%
- **Error rate**: <2%
- **Query success rate**: >95%
- **Quality alert response**: <1 hour

This implementation plan provides a solid foundation for the query pipeline with built-in quality analysis and extensibility for future enhancements. 