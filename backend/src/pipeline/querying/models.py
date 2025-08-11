from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class QueryVariations(BaseModel):
    """Query variations generated during processing"""

    original: str
    semantic: str | None = None
    hyde: str | None = None
    formal: str | None = None


class SearchResult(BaseModel):
    """Individual search result from vector search"""

    content: str
    metadata: dict[str, Any]
    similarity_score: float
    source_filename: str
    page_number: int | None = None
    chunk_id: str | None = None


class QualityMetrics(BaseModel):
    """Quality metrics for search results"""

    relevance_score: float
    confidence: str  # "excellent", "good", "acceptable", "low"
    top_similarity: float | None = None
    result_count: int | None = None


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
    suggestions: list[str]
    confidence: str


class QueryResponse(BaseModel):
    """Final response from query pipeline"""

    response: str
    search_results: list[SearchResult]
    performance_metrics: dict[str, Any]
    quality_metrics: QualityMetrics | None = None
    quality_decision: QualityDecision | None = None
    step_timings: dict[str, float] | None = None


class QueryRequest(BaseModel):
    """Request model for query processing"""

    query: str = Field(..., min_length=1, max_length=1000)
    user_id: str | None = None
    indexing_run_id: UUID | None = Field(None, description="Specific indexing run to query against")
    allowed_document_ids: list[str] | None = Field(default=None, description="Restrict retrieval to these document IDs")


class QueryFeedback(BaseModel):
    """User feedback on query results"""

    relevance_score: int = Field(ge=1, le=5)  # 1-5 scale
    helpfulness_score: int = Field(ge=1, le=5)
    accuracy_score: int = Field(ge=1, le=5)
    comments: str | None = None


class QueryRun(BaseModel):
    """Database model for storing query runs"""

    id: UUID | None = None
    user_id: str | None = None
    original_query: str
    query_variations: dict[str, Any] | None = None
    selected_variation: str | None = None
    search_results: list[dict[str, Any]] | None = None
    final_response: str | None = None
    performance_metrics: dict[str, Any] | None = None
    quality_metrics: dict[str, Any] | None = None
    created_at: datetime | None = None


# --- Adapters: convert sample_outputs dicts into typed models ---


def to_query_variations(sample_outputs: dict[str, Any]) -> QueryVariations:
    variations_data = sample_outputs.get("variations", {}) or {}
    if isinstance(variations_data, QueryVariations):
        return variations_data
    return QueryVariations(**variations_data)


def to_search_results(sample_outputs: dict[str, Any]) -> list[SearchResult]:
    raw = sample_outputs.get("search_results", []) or []
    results: list[SearchResult] = []
    for item in raw:
        if isinstance(item, SearchResult):
            results.append(item)
        else:
            results.append(SearchResult(**item))
    return results


def to_query_response(sample_outputs: dict[str, Any]) -> QueryResponse:
    response_data = sample_outputs.get("response", {}) or {}
    if isinstance(response_data, QueryResponse):
        return response_data
    return QueryResponse(**response_data)
