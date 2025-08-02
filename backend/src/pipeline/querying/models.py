from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class QueryVariations(BaseModel):
    """Query variations generated during processing"""

    original: str
    semantic: Optional[str] = None
    hyde: Optional[str] = None
    formal: Optional[str] = None


class SearchResult(BaseModel):
    """Individual search result from vector search"""

    content: str
    metadata: Dict[str, Any]
    similarity_score: float
    source_filename: str
    page_number: Optional[int] = None
    chunk_id: Optional[str] = None


class QualityMetrics(BaseModel):
    """Quality metrics for search results"""

    relevance_score: float
    confidence: str  # "excellent", "good", "acceptable", "low"
    top_similarity: Optional[float] = None
    result_count: Optional[int] = None


class DiversityMetrics(BaseModel):
    """Diversity metrics for search results"""

    document_diversity: float
    page_spread: int
    unique_sources: int


class ResponseQuality(BaseModel):
    """Quality assessment of generated response"""

    length_score: float
    keyword_coverage: float
    has_citations: bool
    overall_score: float


class QualityDecision(BaseModel):
    """Overall quality decision and suggestions"""

    overall_score: float
    quality_level: str  # "excellent", "good", "acceptable", "poor"
    suggestions: List[str]
    confidence: str


class QueryResponse(BaseModel):
    """Final response from query pipeline"""

    response: str
    search_results: List[SearchResult]
    performance_metrics: Dict[str, Any]
    quality_metrics: Optional[QualityMetrics] = None
    quality_decision: Optional[QualityDecision] = None


class QueryRequest(BaseModel):
    """Request model for query processing"""

    query: str = Field(..., min_length=1, max_length=1000)
    user_id: Optional[str] = None
    indexing_run_id: Optional[UUID] = Field(
        None, description="Specific indexing run to query against"
    )


class QueryFeedback(BaseModel):
    """User feedback on query results"""

    relevance_score: int = Field(ge=1, le=5)  # 1-5 scale
    helpfulness_score: int = Field(ge=1, le=5)
    accuracy_score: int = Field(ge=1, le=5)
    comments: Optional[str] = None


class QueryRun(BaseModel):
    """Database model for storing query runs"""

    id: Optional[UUID] = None
    user_id: Optional[str] = None
    original_query: str
    query_variations: Optional[Dict[str, Any]] = None
    selected_variation: Optional[str] = None
    search_results: Optional[List[Dict[str, Any]]] = None
    final_response: Optional[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
