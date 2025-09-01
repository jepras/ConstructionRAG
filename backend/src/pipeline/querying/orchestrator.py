"""Query pipeline orchestrator for real-time question answering."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings
from src.middleware.request_id import get_request_id
from src.services.config_service import ConfigService
from src.utils.logging import get_logger

from .models import (
    QualityMetrics,
    QueryRequest,
    QueryResponse,
    QueryVariations,
    to_query_response,
    to_query_variations,
    to_search_results,
)
from .steps.generation import GenerationConfig, ResponseGenerator
from .steps.query_processing import QueryProcessingConfig, QueryProcessor
from .steps.retrieval import DocumentRetriever, RetrievalConfig

logger = get_logger(__name__)


class QueryPipelineOrchestrator:
    """Orchestrates the complete query pipeline from input to response"""

    def __init__(self, config: dict[str, Any] | None = None, db_client=None):
        if config is not None:
            self.config = config
        else:
            # Load from SoT and build effective query config
            effective = ConfigService().get_effective_config("query")
            logger.info(f"🔧 ConfigService loaded effective config: {effective}")
            self.config = {
                "query_processing": {
                    "provider": "openrouter",
                    "model": effective.get("query_processing", {}).get("model", "openai/gpt-3.5-turbo"),
                    "fallback_models": effective.get("query_processing", {}).get("fallback_models", ["anthropic/claude-3-haiku"]),
                    "timeout_seconds": effective.get("query_processing", {}).get("timeout_seconds", 1.0),
                    "max_tokens": effective.get("query_processing", {}).get("max_tokens", 200),
                    "temperature": effective.get("query_processing", {}).get("temperature", 0.1),
                    "variations": effective.get("query_processing", {}).get("variations", {
                        "semantic_expansion": True,
                        "hyde_document": True,
                        "formal_variation": True,
                        "parallel_generation": True,
                    }),
                },
                "retrieval": {
                    "embedding_model": effective["embedding"]["model"],
                    "dimensions": effective["embedding"]["dimensions"],
                    "similarity_metric": effective.get("retrieval", {}).get("similarity_metric", "cosine"),
                    "top_k": effective.get("retrieval", {}).get("top_k", 5),
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
                    "provider": effective.get("generation", {}).get("provider", "openrouter"),
                    "model": effective.get("generation", {}).get("model", "google/gemini-2.5-flash-lite"),
                    "fallback_models": effective.get("generation", {}).get("fallback_models", [
                        "anthropic/claude-3.5-haiku",
                        "meta-llama/llama-3.1-8b-instruct",
                    ]),
                    "timeout_seconds": effective.get("generation", {}).get("timeout_seconds", 5.0),
                    "max_tokens": effective.get("generation", {}).get("max_tokens", 1000),
                    "temperature": effective.get("generation", {}).get("temperature", 0.1),
                    "response_format": effective.get("generation", {}).get("response_format", {
                        "include_citations": True,
                        "include_confidence": True,
                        "language": "danish",
                    }),
                },
            }
        self.settings = get_settings()
        # Default to admin, but allow request-scoped client injection for RLS-aware reads
        self.db = db_client or get_supabase_admin_client()

        # Initialize pipeline steps
        self.query_processor = QueryProcessor(QueryProcessingConfig(**self.config["query_processing"]))
        # Keep admin by default; retrieval step supports DI for future anon usage
        self.retriever = DocumentRetriever(
            RetrievalConfig(self.config["retrieval"]), db_client=self.db, use_admin=False
        )
        self.generator = ResponseGenerator(GenerationConfig(**self.config["generation"]))

        # Log the loaded configuration for debugging
        logger.info(f"🔧 Query pipeline configured with generation model: {self.config['generation']['model']}")
        logger.info(f"🔧 Generation fallback models: {self.config['generation']['fallback_models']}")
        logger.info(f"🔧 Config source: {'ConfigService (SoT)' if config is None else 'Direct injection'}")

        # Progress tracking (simplified for query pipeline)
        self.progress_tracker = None

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration for the query pipeline"""
        return {
            "query_processing": {
                "provider": "openrouter",
                "model": "google/gemini-2.5-flash",
                "fallback_models": ["anthropic/claude-3.5-haiku"],
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
                "model": "google/gemini-2.5-flash",
                "fallback_models": [
                    "anthropic/claude-3.5-haiku",
                    "meta-llama/llama-3.1-8b-instruct",
                ],
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

        start_time = datetime.utcnow()
        query_run_id = str(uuid4())

        # Bind structured context once per run
        rid = get_request_id()
        run_logger = logger.bind(request_id=rid, pipeline_type="query", run_id=query_run_id)

        # Track step timings
        step_timings = {}

        run_logger.info(f"🔍 Starting query pipeline for query: {request.query[:50]}...")
        run_logger.info(f"🔍 Request user_id: {request.user_id}")
        run_logger.info(f"🔍 Request indexing_run_id: {request.indexing_run_id}")
        run_logger.info(f"🔍 Request type: {type(request)}")

        try:
            # Step 1: Query Processing
            run_logger.info("Step 1: Processing query variations...")
            step1_start = datetime.utcnow()

            query_result = await self.query_processor.execute(request.query)
            if query_result.status != "completed":
                raise Exception(f"Query processing failed: {query_result.error_message}")

            step1_duration = (datetime.utcnow() - step1_start).total_seconds()
            step_timings["query_processing"] = step1_duration
            run_logger.info(f"Query processing completed in {step1_duration:.2f}s")

            # Get variations from sample_outputs
            variations = to_query_variations(query_result.sample_outputs)

            # Step 2: Document Retrieval
            run_logger.info("Step 2: Retrieving relevant documents...")
            step2_start = datetime.utcnow()

            # Pass indexing_run_id and allowed_document_ids to retrieval step if provided
            if request.indexing_run_id:
                run_logger.info(f"Querying specific indexing run: {request.indexing_run_id}")
                retrieval_result = await self.retriever.execute(
                    variations, str(request.indexing_run_id), request.allowed_document_ids
                )
            else:
                retrieval_result = await self.retriever.execute(variations, None, request.allowed_document_ids)
            if retrieval_result.status != "completed":
                raise Exception(f"Retrieval failed: {retrieval_result.error_message}")

            step2_duration = (datetime.utcnow() - step2_start).total_seconds()
            step_timings["retrieval"] = step2_duration
            run_logger.info(f"Retrieval completed in {step2_duration:.2f}s")

            # Get search results from sample_outputs and convert to SearchResult objects
            search_results = to_search_results(retrieval_result.sample_outputs)

            # Step 3: Response Generation
            run_logger.info("Step 3: Generating response...")
            step3_start = datetime.utcnow()

            generation_result = await self.generator.execute((request.query, search_results))
            if generation_result.status != "completed":
                raise Exception(f"Generation failed: {generation_result.error_message}")

            step3_duration = (datetime.utcnow() - step3_start).total_seconds()
            step_timings["generation"] = step3_duration
            run_logger.info(f"Generation completed in {step3_duration:.2f}s")

            # Get response from sample_outputs
            response = to_query_response(generation_result.sample_outputs)

            # Add step timings to the response
            response.step_timings = step_timings

            # Calculate total response time
            response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Store query run in database
            await self._store_query_run(
                query_run_id=query_run_id,
                request=request,
                variations=variations,
                search_results=search_results,
                response=response,
                response_time_ms=response_time_ms,
                step_timings=step_timings,
            )

            run_logger.info(f"Query pipeline completed successfully in {response_time_ms}ms")
            run_logger.info(f"Step timings: {step_timings}")

            return response

        except Exception as e:
            run_logger.error(f"Query pipeline failed: {e}")

            # Store failed query run
            await self._store_query_run(
                query_run_id=query_run_id,
                request=request,
                error_message=str(e),
                response_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
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
        variations: QueryVariations | None = None,
        search_results: list | None = None,
        response: QueryResponse | None = None,
        error_message: str | None = None,
        response_time_ms: int = 0,
        step_timings: dict[str, float] | None = None,
    ):
        """Store query run in the database"""

        try:
            logger.bind(run_id=query_run_id).info(f"🔍 Storing query run with ID: {query_run_id}")
            logger.info(f"🔍 Request user_id: {request.user_id}")
            logger.info(f"🔍 Request type: {type(request)}")
            query_run_data = {
                "id": query_run_id,
                "user_id": request.user_id,
                "indexing_run_id": str(request.indexing_run_id) if request.indexing_run_id else None,
                "access_level": ("public" if not request.user_id else "private"),
                "original_query": request.query,
                "query_variations": (variations.model_dump(exclude_none=True) if variations else None),
                "search_results": (
                    [result.model_dump(exclude_none=True) for result in search_results] if search_results else None
                ),
                "final_response": response.response if response else None,
                "performance_metrics": (response.performance_metrics if response else None),
                "quality_metrics": (
                    response.quality_metrics.model_dump(exclude_none=True)
                    if response and response.quality_metrics
                    else None
                ),
                "response_time_ms": response_time_ms,
                "error_message": error_message,
                "step_timings": step_timings,
                "pipeline_config": self.config,
                "created_at": datetime.utcnow().isoformat(),
            }

            # Insert into query_runs table, with fallback if pipeline_config column is missing
            result = self.db.table("query_runs").insert(query_run_data).execute()

            if result.data:
                logger.bind(run_id=query_run_id).info(f"Query run stored with ID: {query_run_id}")
            else:
                # Best-effort fallback: retry without pipeline_config in case column doesn't exist yet
                error_msg = getattr(result, "error", None)
                logger.bind(run_id=query_run_id).warning(
                    f"Primary insert failed, attempting fallback without pipeline_config: {error_msg}"
                )
                fallback_data = {k: v for k, v in query_run_data.items() if k != "pipeline_config"}
                fb_result = self.db.table("query_runs").insert(fallback_data).execute()
                if fb_result.data:
                    logger.bind(run_id=query_run_id).info(f"Query run stored with ID (fallback): {query_run_id}")
                else:
                    logger.bind(run_id=query_run_id).error(
                        f"Failed to store query run even after fallback: {getattr(fb_result, 'error', None)}"
                    )

        except Exception as e:
            # Final defensive fallback on unexpected exceptions: try without pipeline_config once
            logger.bind(run_id=query_run_id).warning(
                f"Exception during insert with pipeline_config, retrying without it: {e}"
            )
            try:
                fallback_data = {k: v for k, v in query_run_data.items() if k != "pipeline_config"}
                fb_result = self.db.table("query_runs").insert(fallback_data).execute()
                if fb_result.data:
                    logger.bind(run_id=query_run_id).info(
                        f"Query run stored with ID (exception fallback): {query_run_id}"
                    )
                else:
                    logger.bind(run_id=query_run_id).error(
                        f"Failed to store query run after exception fallback: {getattr(fb_result, 'error', None)}"
                    )
            except Exception as final_err:
                logger.bind(run_id=query_run_id).error(f"Error storing query run, final failure: {final_err}")

    async def get_pipeline_status(self, query_run_id: str) -> dict[str, Any]:
        """Get the status of a specific query pipeline run"""

        try:
            # Get query run from database
            result = self.db.table("query_runs").select("*").eq("id", query_run_id).execute()

            if result.data:
                query_run = result.data[0]
                return {
                    "query_run_id": query_run_id,
                    "status": ("completed" if query_run.get("final_response") else "failed"),
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

    async def get_pipeline_metrics(self) -> dict[str, Any]:
        """Get overall pipeline performance metrics"""

        try:
            # Get recent query runs
            result = self.db.table("query_runs").select("*").order("created_at", desc=True).limit(100).execute()

            if not result.data:
                return {"total_queries": 0, "avg_response_time": 0, "success_rate": 0}

            query_runs = result.data

            total_queries = len(query_runs)
            successful_queries = len([qr for qr in query_runs if qr.get("final_response")])
            avg_response_time = sum(qr.get("response_time_ms", 0) for qr in query_runs) / total_queries
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
