"""
FastAPI endpoints for query processing pipeline.

This module provides REST API endpoints for:
- POST /api/query - Process construction queries
- GET /api/query/history - Get user query history
- POST /api/query/{id}/feedback - Submit user feedback
- GET /api/query/quality-dashboard - Admin quality metrics
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
from src.pipeline.querying.models import QueryRequest, QueryResponse, QueryFeedback
from src.api.auth import get_current_user
from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["queries"])


# Pydantic models for API requests/responses
class QueryHistoryResponse(BaseModel):
    """Response model for query history"""

    queries: List[Dict[str, Any]]
    total_count: int
    has_more: bool


class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""

    success: bool
    message: str


class QualityDashboardResponse(BaseModel):
    """Response model for quality dashboard"""

    period: str
    total_queries: int
    successful_queries: int
    failed_queries: int
    avg_response_time_ms: float
    success_rate: float
    avg_quality_score: float
    quality_distribution: Dict[str, int]
    recent_queries: List[Dict[str, Any]]


# Dependency injection for orchestrator
async def get_query_orchestrator() -> QueryPipelineOrchestrator:
    """Get query pipeline orchestrator with dependency injection"""
    return QueryPipelineOrchestrator()


@router.post("/", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    current_user=Depends(get_current_user),
    orchestrator: QueryPipelineOrchestrator = Depends(get_query_orchestrator),
):
    """
    Process a construction-related query through the entire pipeline.

    This endpoint:
    1. Takes a user query and processes it through query processing, retrieval, and generation
    2. Stores the result in the database for history and analytics
    3. Returns the complete response with metadata
    """
    try:
        # Set user_id from authenticated user
        request.user_id = current_user.id

        logger.info(
            f"Processing query for user {current_user.id}: {request.query[:50]}..."
        )

        # Process query through pipeline
        response = await orchestrator.process_query(request)

        logger.info(f"Query processed successfully in {response.response_time_ms}ms")
        return response

    except Exception as e:
        logger.error(f"Error processing query: {e}")

        # Store error in database
        try:
            await store_error_query(request, str(e))
        except Exception as db_error:
            logger.error(f"Failed to store error query: {db_error}")

        # Return fallback response
        return QueryResponse(
            response="Beklager, der opstod en fejl under behandling af dit spørgsmål. Prøv venligst igen.",
            search_results=[],
            performance_metrics={"error": str(e)},
            quality_metrics={"relevance_score": 0.0, "confidence": "low"},
        )


@router.get("/history", response_model=QueryHistoryResponse)
async def get_query_history(
    current_user=Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="Number of queries to return"),
    offset: int = Query(0, ge=0, description="Number of queries to skip"),
    db=Depends(get_supabase_admin_client),
):
    """
    Get user's query history with pagination.

    Returns:
    - List of previous queries with responses and metadata
    - Total count for pagination
    - Has more flag for infinite scrolling
    """
    try:
        # Get total count
        count_result = (
            db.table("query_runs")
            .select("id", count="exact")
            .eq("user_id", current_user.id)
            .execute()
        )
        total_count = count_result.count or 0

        # Get paginated queries
        result = (
            db.table("query_runs")
            .select("*")
            .eq("user_id", current_user.id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        queries = []
        for query_run in result.data:
            queries.append(
                {
                    "id": query_run["id"],
                    "original_query": query_run["original_query"],
                    "final_response": query_run.get("final_response", ""),
                    "performance_metrics": query_run.get("performance_metrics", {}),
                    "quality_metrics": query_run.get("quality_metrics", {}),
                    "created_at": query_run["created_at"],
                }
            )

        has_more = offset + limit < total_count

        return QueryHistoryResponse(
            queries=queries, total_count=total_count, has_more=has_more
        )

    except Exception as e:
        logger.error(f"Error getting query history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve query history")


@router.post("/{query_id}/feedback", response_model=FeedbackResponse)
async def submit_query_feedback(
    query_id: str,
    feedback: QueryFeedback,
    current_user=Depends(get_current_user),
    db=Depends(get_supabase_admin_client),
):
    """
    Submit user feedback on query results.

    This endpoint:
    1. Validates the query_id exists and belongs to the user
    2. Updates the quality_metrics with user feedback
    3. Returns success confirmation
    """
    try:
        # Verify query exists and belongs to user
        result = (
            db.table("query_runs")
            .select("id, quality_metrics")
            .eq("id", query_id)
            .eq("user_id", current_user.id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Query not found")

        query_run = result.data[0]
        current_quality_metrics = query_run.get("quality_metrics", {})

        # Add user feedback to quality metrics
        updated_quality_metrics = {
            **current_quality_metrics,
            "user_feedback": {
                "relevance_score": feedback.relevance_score,
                "helpfulness_score": feedback.helpfulness_score,
                "accuracy_score": feedback.accuracy_score,
                "comments": feedback.comments,
                "submitted_at": datetime.utcnow().isoformat(),
            },
        }

        # Update database
        update_result = (
            db.table("query_runs")
            .update({"quality_metrics": updated_quality_metrics})
            .eq("id", query_id)
            .execute()
        )

        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to update feedback")

        logger.info(
            f"Feedback submitted for query {query_id} by user {current_user.id}"
        )

        return FeedbackResponse(success=True, message="Feedback submitted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


@router.get("/quality-dashboard", response_model=QualityDashboardResponse)
async def get_quality_dashboard(
    time_period: str = Query("7d", description="Time period: 1d, 7d, 30d"),
    current_user=Depends(get_current_user),
    db=Depends(get_supabase_admin_client),
):
    """
    Get admin quality dashboard metrics.

    This endpoint provides:
    - Query volume and success rates
    - Average response times
    - Quality score distribution
    - Recent query examples
    """
    try:
        # Calculate time range
        now = datetime.utcnow()
        if time_period == "1d":
            start_time = now - timedelta(days=1)
        elif time_period == "7d":
            start_time = now - timedelta(days=7)
        elif time_period == "30d":
            start_time = now - timedelta(days=30)
        else:
            raise HTTPException(status_code=400, detail="Invalid time period")

        # Get all queries in time period
        result = (
            db.table("query_runs")
            .select("*")
            .gte("created_at", start_time.isoformat())
            .order("created_at", desc=True)
            .execute()
        )

        queries = result.data
        total_queries = len(queries)

        if total_queries == 0:
            return QualityDashboardResponse(
                period=time_period,
                total_queries=0,
                successful_queries=0,
                failed_queries=0,
                avg_response_time_ms=0.0,
                success_rate=0.0,
                avg_quality_score=0.0,
                quality_distribution={
                    "excellent": 0,
                    "good": 0,
                    "acceptable": 0,
                    "poor": 0,
                },
                recent_queries=[],
            )

        # Calculate metrics
        successful_queries = len([q for q in queries if q.get("final_response")])
        failed_queries = total_queries - successful_queries
        success_rate = (successful_queries / total_queries) * 100

        # Calculate average response time
        response_times = [
            q.get("response_time_ms", 0) for q in queries if q.get("response_time_ms")
        ]
        avg_response_time_ms = (
            sum(response_times) / len(response_times) if response_times else 0.0
        )

        # Calculate quality distribution
        quality_distribution = {"excellent": 0, "good": 0, "acceptable": 0, "poor": 0}
        quality_scores = []

        for query in queries:
            quality_metrics = query.get("quality_metrics", {})
            quality_score = quality_metrics.get("quality_score", 0.0)
            quality_scores.append(quality_score)

            if quality_score >= 0.8:
                quality_distribution["excellent"] += 1
            elif quality_score >= 0.6:
                quality_distribution["good"] += 1
            elif quality_score >= 0.4:
                quality_distribution["acceptable"] += 1
            else:
                quality_distribution["poor"] += 1

        avg_quality_score = (
            sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        )

        # Get recent queries for examples
        recent_queries = []
        for query in queries[:10]:  # Last 10 queries
            recent_queries.append(
                {
                    "query": query["original_query"],
                    "quality_score": query.get("quality_metrics", {}).get(
                        "quality_score", 0.0
                    ),
                    "response_time_ms": query.get("response_time_ms", 0),
                    "created_at": query["created_at"],
                }
            )

        return QualityDashboardResponse(
            period=time_period,
            total_queries=total_queries,
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            avg_response_time_ms=avg_response_time_ms,
            success_rate=success_rate,
            avg_quality_score=avg_quality_score,
            quality_distribution=quality_distribution,
            recent_queries=recent_queries,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quality dashboard: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve quality dashboard"
        )


async def store_error_query(request: QueryRequest, error_message: str):
    """Store failed query in database for analytics"""
    try:
        db = get_supabase_admin_client()

        await db.table("query_runs").insert(
            {
                "user_id": request.user_id,
                "original_query": request.query,
                "error_message": error_message,
                "response_time_ms": 0,
                "created_at": datetime.utcnow().isoformat(),
            }
        ).execute()

    except Exception as e:
        logger.error(f"Failed to store error query: {e}")
