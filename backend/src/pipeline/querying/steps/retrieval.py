"""Production retrieval step for query pipeline using shared components."""

import logging
from datetime import datetime
from typing import Any

from src.config.database import get_supabase_admin_client, get_supabase_client
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError

from ...shared.base_step import PipelineStep, StepResult
from ...shared import SharedRetrievalConfig, RetrievalCore
from ..models import QueryVariations, SearchResult

logger = logging.getLogger(__name__)


class RetrievalConfig:
    """Configuration for retrieval step - maintains backward compatibility"""

    def __init__(self, config: dict[str, Any]):
        self.embedding_model = config.get("embedding_model", "voyage-multilingual-2")
        self.dimensions = config.get("dimensions", 1024)
        self.similarity_metric = config.get("similarity_metric", "cosine")
        self.top_k = config.get("top_k", 5)
        self.similarity_thresholds = config.get(
            "similarity_thresholds",
            {"excellent": 0.75, "good": 0.60, "acceptable": 0.40, "minimum": 0.25},
        )
        self.danish_thresholds = config.get(
            "danish_thresholds",
            {"excellent": 0.70, "good": 0.55, "acceptable": 0.35, "minimum": 0.20},
        )


class DocumentRetriever(PipelineStep):
    """Retrieval step using shared retrieval components"""

    def __init__(self, config: RetrievalConfig, *, db_client=None, use_admin: bool = True):
        super().__init__(config.__dict__, None)
        self.config = config
        
        # Set up database client
        if db_client is not None:
            self.db = db_client
        else:
            self.db = get_supabase_admin_client() if use_admin else get_supabase_client()

        # Create shared retrieval configuration
        shared_config = SharedRetrievalConfig(
            embedding_model=self.config.embedding_model,
            dimensions=self.config.dimensions,
            similarity_metric=self.config.similarity_metric,
            top_k=self.config.top_k,
            similarity_thresholds=self.config.similarity_thresholds,
            danish_thresholds=self.config.danish_thresholds
        )
        
        # Initialize shared retrieval core
        self.retrieval_core = RetrievalCore(
            config=shared_config,
            db_client=self.db
        )

    async def execute(
        self,
        input_data: QueryVariations,
        indexing_run_id: str | None = None,
        allowed_document_ids: list[str] | None = None,
    ) -> StepResult:
        """Execute the retrieval step"""
        start_time = datetime.utcnow()

        logger.info(f"🔍 RETRIEVAL EXECUTE: Starting search with run_id={indexing_run_id}")
        logger.info(f"🔍 RETRIEVAL EXECUTE: Input variations - original: '{input_data.original[:50]}...'")
        logger.info(f"🔍 RETRIEVAL EXECUTE: Allowed document IDs: {len(allowed_document_ids) if allowed_document_ids else 'None'}")

        try:
            # Search documents using query variations
            results = await self.search(input_data, indexing_run_id, allowed_document_ids)

            # Create sample outputs for debugging
            sample_outputs = {
                "search_results": [r.model_dump(exclude_none=True) for r in results],
                "results_count": len(results),
                "top_similarity": results[0].similarity_score if results else 0.0,
            }

            return StepResult(
                step=self.get_step_name(),
                status="completed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                summary_stats={
                    "results_retrieved": len(results),
                    "top_similarity_score": (results[0].similarity_score if results else 0.0),
                    "avg_similarity_score": (
                        sum(r.similarity_score for r in results) / len(results) if results else 0.0
                    ),
                },
                sample_outputs=sample_outputs,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error in retrieval step: {e}")
            raise AppError(
                "Retrieval failed",
                error_code=ErrorCode.DATABASE_ERROR,
                details={"reason": str(e)},
            ) from e

    async def search(
        self,
        variations: QueryVariations,
        indexing_run_id: str | None = None,
        allowed_document_ids: list[str] | None = None,
    ) -> list[SearchResult]:
        """Search documents using best query variation"""

        logger.info(f"🔍 SEARCH: Starting search process")

        # Select best variation (for now, use original)
        best_query = self.select_best_variation(variations)
        logger.info(f"🔍 SEARCH: Selected best query: '{best_query[:100]}...'")

        # Generate embedding using shared service
        logger.info(f"🔍 SEARCH: Generating embedding with model: {self.config.embedding_model}")
        embed_start = datetime.utcnow()
        query_embedding = await self.retrieval_core.generate_query_embedding(best_query)
        embed_duration = (datetime.utcnow() - embed_start).total_seconds() * 1000
        logger.info(f"🔍 SEARCH: Embedding generated in {embed_duration:.1f}ms, dimensions: {len(query_embedding)}")

        # Search using shared retrieval core
        logger.info(f"🔍 SEARCH: Starting shared retrieval core search")
        search_start = datetime.utcnow()
        search_results = await self.retrieval_core.search_with_fallback(
            query_embedding, indexing_run_id, allowed_document_ids, language="danish"
        )
        search_duration = (datetime.utcnow() - search_start).total_seconds() * 1000
        logger.info(f"🔍 SEARCH: Shared core search completed in {search_duration:.1f}ms, found {len(search_results)} results")

        # Convert to SearchResult objects
        result_objects = self.convert_to_search_results(search_results)
        
        if result_objects:
            top_similarity = max(r.similarity_score for r in result_objects)
            avg_similarity = sum(r.similarity_score for r in result_objects) / len(result_objects)
            logger.info(f"🔍 SEARCH: Top similarity: {top_similarity:.3f}, Average: {avg_similarity:.3f}")

        logger.info(f"🔍 SEARCH: Search completed, returning {len(result_objects)} results")
        return result_objects

    def select_best_variation(self, variations: QueryVariations) -> str:
        """Select the best variation for retrieval"""
        # For now, just return the original
        # TODO: Implement selection logic based on query type, language, etc.
        return variations.original

    def convert_to_search_results(self, search_results: list[dict[str, Any]]) -> list[SearchResult]:
        """Convert search results to SearchResult objects"""
        result_objects = []
        
        for result in search_results:
            search_result = SearchResult(
                content=result["content"],
                metadata=result.get("metadata", {}),
                similarity_score=result["similarity_score"],
                source_filename=result.get("source_filename", "unknown"),
                page_number=result.get("page_number"),
                chunk_id=str(result["id"]),
            )
            result_objects.append(search_result)
        
        return result_objects

    async def validate_prerequisites_async(self, input_data: QueryVariations) -> bool:
        """Validate retrieval prerequisites"""
        # Check if input is QueryVariations
        if not isinstance(input_data, QueryVariations):
            return False

        # Check if we have at least one query variation
        if not input_data.original:
            return False

        # Check database connection
        try:
            # Simple test query
            response = self.db.table("document_chunks").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def estimate_duration(self, input_data: QueryVariations) -> int:
        """Estimate retrieval duration"""
        # Base time for embedding + search
        base_time = 2

        # Add time for multiple variations if needed
        variation_count = sum(
            [
                1 if input_data.semantic else 0,
                1 if input_data.hyde else 0,
                1 if input_data.formal else 0,
            ]
        )

        return base_time + (variation_count * 1)  # 1 second per variation

    # Legacy methods for backward compatibility
    async def embed_query(self, query: str) -> list[float]:
        """Legacy method - use shared embedding service"""
        return await self.retrieval_core.generate_query_embedding(query)