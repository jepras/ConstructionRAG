"""Query pipeline orchestrator for real-time question answering."""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from uuid import uuid4
from datetime import datetime

from pipeline.shared.base_step import PipelineStep, StepResult
from pipeline.shared.progress_tracker import ProgressTracker
from pipeline.querying.steps.query_processing import (
    QueryProcessor,
    QueryProcessingConfig,
)
from pipeline.querying.steps.retrieval import DocumentRetriever, RetrievalConfig
from pipeline.querying.steps.generation import ResponseGenerator, GenerationConfig
from pipeline.querying.models import (
    QueryVariations,
    QueryResponse,
    QueryRequest,
    QueryRun,
    QualityMetrics,
    SearchResult,
)
from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class QueryPipelineOrchestrator:
    """Orchestrates the complete query pipeline from input to response"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.settings = get_settings()
        self.db = get_supabase_admin_client()

        # Initialize pipeline steps
        self.query_processor = QueryProcessor(
            QueryProcessingConfig(**self.config["query_processing"])
        )
        self.retriever = DocumentRetriever(RetrievalConfig(self.config["retrieval"]))
        self.generator = ResponseGenerator(
            GenerationConfig(**self.config["generation"])
        )

        # Progress tracking (simplified for query pipeline)
        self.progress_tracker = None

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for the query pipeline"""
        return {
            "query_processing": {
                "provider": "openrouter",
                "model": "openai/gpt-3.5-turbo",
                "fallback_models": ["anthropic/claude-3-haiku"],
                "timeout_seconds": 1.0,
                "max_tokens": 200,
                "temperature": 0.1,
                "variations": {
                    "semantic_expansion": True,
                    "hyde_document": True,
                    "formal_variation": True,
                    "parallel_generation": True,
                },
            },
            "retrieval": {
                "embedding_model": "voyage-multilingual-2",
                "dimensions": 1024,
                "similarity_metric": "cosine",
                "top_k": 5,
                "similarity_thresholds": {
                    "excellent": 0.75,
                    "good": 0.60,
                    "acceptable": 0.40,
                    "minimum": 0.25,
                },
                "danish_thresholds": {
                    "excellent": 0.70,
                    "good": 0.55,
                    "acceptable": 0.35,
                    "minimum": 0.20,
                },
            },
            "generation": {
                "provider": "openrouter",
                "model": "anthropic/claude-3.5-sonnet",
                "fallback_models": ["openai/gpt-4", "meta-llama/llama-3.1-8b-instruct"],
                "timeout_seconds": 5.0,
                "max_tokens": 1000,
                "temperature": 0.1,
                "response_format": {
                    "include_citations": True,
                    "include_confidence": True,
                    "language": "danish",
                },
            },
            "quality_analysis": {
                "enable_automatic_metrics": True,
                "enable_user_feedback": True,
                "quality_thresholds": {
                    "excellent": 0.8,
                    "good": 0.6,
                    "acceptable": 0.4,
                    "poor": 0.2,
                },
            },
        }

    async def process_query(self, request: QueryRequest) -> QueryResponse:
        """Process a complete query through the entire pipeline"""

        start_time = time.time()
        query_run_id = str(uuid4())

        logger.info(f"Starting query pipeline for query: {request.query[:50]}...")

        try:
            # Step 1: Query Processing
            logger.info("Step 1: Processing query variations...")

            query_result = await self.query_processor.execute(request.query)
            if query_result.status != "completed":
                raise Exception(
                    f"Query processing failed: {query_result.error_message}"
                )

            # Get variations from sample_outputs
            variations_data = query_result.sample_outputs.get("variations", {})
            variations = QueryVariations(**variations_data)

            # Step 2: Document Retrieval
            logger.info("Step 2: Retrieving relevant documents...")

            retrieval_result = await self.retriever.execute(variations)
            if retrieval_result.status != "completed":
                raise Exception(f"Retrieval failed: {retrieval_result.error_message}")

            # Get search results from sample_outputs and convert to SearchResult objects
            search_results_data = retrieval_result.sample_outputs.get(
                "search_results", []
            )
            search_results = [SearchResult(**result) for result in search_results_data]

            # Step 3: Response Generation
            logger.info("Step 3: Generating response...")

            generation_result = await self.generator.execute(search_results)
            if generation_result.status != "completed":
                raise Exception(f"Generation failed: {generation_result.error_message}")

            # Get response from sample_outputs
            response_data = generation_result.sample_outputs.get("response", {})
            response = QueryResponse(**response_data)

            # Calculate total response time
            response_time_ms = int((time.time() - start_time) * 1000)

            # Store query run in database
            await self._store_query_run(
                query_run_id=query_run_id,
                request=request,
                variations=variations,
                search_results=search_results,
                response=response,
                response_time_ms=response_time_ms,
            )

            logger.info(
                f"Query pipeline completed successfully in {response_time_ms}ms"
            )

            return response

        except Exception as e:
            logger.error(f"Query pipeline failed: {e}")

            # Store failed query run
            await self._store_query_run(
                query_run_id=query_run_id,
                request=request,
                error_message=str(e),
                response_time_ms=int((time.time() - start_time) * 1000),
            )

            # Return error response
            return QueryResponse(
                response=f"Beklager, der opstod en fejl under behandling af dit spørgsmål: {str(e)}",
                search_results=[],
                performance_metrics={
                    "model_used": "error",
                    "tokens_used": 0,
                    "confidence": 0.0,
                    "sources_count": 0,
                    "error": str(e),
                },
                quality_metrics=QualityMetrics(
                    relevance_score=0.0,
                    confidence="low",
                    top_similarity=0.0,
                    result_count=0,
                ),
            )

    async def _store_query_run(
        self,
        query_run_id: str,
        request: QueryRequest,
        variations: Optional[QueryVariations] = None,
        search_results: Optional[List] = None,
        response: Optional[QueryResponse] = None,
        error_message: Optional[str] = None,
        response_time_ms: int = 0,
    ):
        """Store query run in the database"""

        try:
            query_run_data = {
                "id": query_run_id,
                "user_id": request.user_id,
                "original_query": request.query,
                "query_variations": variations.dict() if variations else None,
                "search_results": (
                    [result.dict() for result in search_results]
                    if search_results
                    else None
                ),
                "final_response": response.response if response else None,
                "performance_metrics": (
                    response.performance_metrics if response else None
                ),
                "quality_metrics": (
                    response.quality_metrics.dict()
                    if response and response.quality_metrics
                    else None
                ),
                "response_time_ms": response_time_ms,
                "error_message": error_message,
                "created_at": datetime.utcnow().isoformat(),
            }

            # Insert into query_runs table
            result = self.db.table("query_runs").insert(query_run_data).execute()

            if result.data:
                logger.info(f"Query run stored with ID: {query_run_id}")
            else:
                logger.warning(f"Failed to store query run: {result.error}")

        except Exception as e:
            logger.error(f"Error storing query run: {e}")

    async def get_pipeline_status(self, query_run_id: str) -> Dict[str, Any]:
        """Get the status of a specific query pipeline run"""

        try:
            # Get query run from database
            result = (
                self.db.table("query_runs").select("*").eq("id", query_run_id).execute()
            )

            if result.data:
                query_run = result.data[0]
                return {
                    "query_run_id": query_run_id,
                    "status": (
                        "completed" if query_run.get("final_response") else "failed"
                    ),
                    "original_query": query_run.get("original_query"),
                    "response_time_ms": query_run.get("response_time_ms"),
                    "error_message": query_run.get("error_message"),
                    "created_at": query_run.get("created_at"),
                }
            else:
                return {"error": "Query run not found"}

        except Exception as e:
            logger.error(f"Error getting pipeline status: {e}")
            return {"error": str(e)}

    async def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get overall pipeline performance metrics"""

        try:
            # Get recent query runs
            result = (
                self.db.table("query_runs")
                .select("*")
                .order("created_at", desc=True)
                .limit(100)
                .execute()
            )

            if not result.data:
                return {"total_queries": 0, "avg_response_time": 0, "success_rate": 0}

            query_runs = result.data

            total_queries = len(query_runs)
            successful_queries = len(
                [qr for qr in query_runs if qr.get("final_response")]
            )
            avg_response_time = (
                sum(qr.get("response_time_ms", 0) for qr in query_runs) / total_queries
            )
            success_rate = successful_queries / total_queries

            return {
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "avg_response_time_ms": int(avg_response_time),
                "success_rate": round(success_rate, 3),
                "recent_queries": [
                    {
                        "id": qr.get("id"),
                        "query": qr.get("original_query")[:50] + "...",
                        "response_time_ms": qr.get("response_time_ms"),
                        "status": "success" if qr.get("final_response") else "failed",
                    }
                    for qr in query_runs[:10]
                ],
            }

        except Exception as e:
            logger.error(f"Error getting pipeline metrics: {e}")
            return {"error": str(e)}
