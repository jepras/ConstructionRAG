"""Production retrieval step for query pipeline."""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import httpx
from supabase import Client

from ..models import SearchResult, QueryVariations
from ...shared.base_step import PipelineStep, StepResult
from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings


logger = logging.getLogger(__name__)


class VoyageEmbeddingClient:
    """Client for Voyage AI embedding API - same as indexing pipeline"""

    def __init__(self, api_key: str, model: str = "voyage-multilingual-2"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.voyageai.com/v1/embeddings"
        self.dimensions = 1024  # voyage-multilingual-2 dimensions

    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text using Voyage AI"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": self.model, "input": [text]},
                )

                if response.status_code != 200:
                    raise Exception(
                        f"Voyage API error: {response.status_code} - {response.text}"
                    )

                result = response.json()
                return result["data"][0]["embedding"]

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise


class RetrievalConfig:
    """Configuration for retrieval step"""

    def __init__(self, config: Dict[str, Any]):
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
    """Retrieval step that searches document chunks using vector similarity"""

    def __init__(self, config: RetrievalConfig):
        super().__init__(config.__dict__, None)
        self.config = config
        self.db = get_supabase_admin_client()

        # Initialize Voyage client
        settings = get_settings()
        api_key = settings.voyage_api_key
        if not api_key:
            raise ValueError("VOYAGE_API_KEY not found in environment variables")

        self.voyage_client = VoyageEmbeddingClient(
            api_key=api_key, model=self.config.embedding_model
        )

    async def execute(
        self, input_data: QueryVariations, indexing_run_id: Optional[str] = None
    ) -> StepResult:
        """Execute the retrieval step"""
        start_time = datetime.utcnow()

        try:
            # Search documents using query variations
            results = await self.search(input_data, indexing_run_id)

            # Create sample outputs for debugging
            sample_outputs = {
                "search_results": [result.dict() for result in results],
                "results_count": len(results),
                "top_similarity": results[0].similarity_score if results else 0.0,
            }

            return StepResult(
                step=self.get_step_name(),
                status="completed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                summary_stats={
                    "results_retrieved": len(results),
                    "top_similarity_score": (
                        results[0].similarity_score if results else 0.0
                    ),
                    "avg_similarity_score": (
                        sum(r.similarity_score for r in results) / len(results)
                        if results
                        else 0.0
                    ),
                },
                sample_outputs=sample_outputs,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error in retrieval step: {e}")
            return StepResult(
                step=self.get_step_name(),
                status="failed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

    async def search(
        self, variations: QueryVariations, indexing_run_id: Optional[str] = None
    ) -> List[SearchResult]:
        """Search documents using best query variation"""

        logger.info(f"Searching documents with {len(variations.dict())} variations")

        # Select best variation (for now, use original)
        # TODO: Implement variation selection logic
        best_query = self.select_best_variation(variations)

        # Embed query using same model as documents
        query_embedding = await self.embed_query(best_query)

        # Search pgvector using embedding_1024 column
        results = await self.search_pgvector(query_embedding, indexing_run_id)

        # Filter by similarity threshold
        filtered_results = self.filter_by_similarity(results)

        logger.info(f"Retrieved {len(filtered_results)} results")
        return filtered_results

    def select_best_variation(self, variations: QueryVariations) -> str:
        """Select the best variation for retrieval"""
        # For now, just return the original
        # TODO: Implement selection logic based on query type, language, etc.
        return variations.original

    async def embed_query(self, query: str) -> List[float]:
        """Embed query using Voyage API"""
        logger.info(f"Embedding query: {query[:50]}...")
        return await self.voyage_client.get_embedding(query)

    async def search_pgvector(
        self, query_embedding: List[float], indexing_run_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search pgvector using cosine distance"""

        # Convert embedding to string format for pgvector
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        try:
            # Use pgvector similarity search with proper SQL
            # First, check if we have any chunks with embeddings
            response = (
                self.db.table("document_chunks")
                .select("id,content,metadata,embedding_1024,document_id")
                .not_.is_("embedding_1024", "null")
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.warning("No document chunks with embeddings found")
                return []

            # Use RPC call for vector similarity search
            # This is the proper way to do pgvector similarity search in Supabase
            search_query = f"""
            SELECT 
                id,
                content,
                metadata,
                embedding_1024 <=> '{embedding_str}'::vector AS distance
            FROM document_chunks 
            WHERE embedding_1024 IS NOT NULL
            ORDER BY embedding_1024 <=> '{embedding_str}'::vector
            LIMIT {self.config.top_k * 2}
            """

            # Get all chunks and calculate similarity in Python
            # (RPC function doesn't exist, so we use direct query)
            query = (
                self.db.table("document_chunks")
                .select(
                    "id,content,metadata,embedding_1024,document_id,indexing_run_id"
                )
                .not_.is_("embedding_1024", "null")
            )

            # Filter by indexing_run_id if provided
            if indexing_run_id:
                query = query.eq("indexing_run_id", indexing_run_id)
                logger.info(f"Filtering search to indexing run: {indexing_run_id}")

            response = query.execute()

            chunks = response.data
            results_with_scores = []

            for chunk in chunks:
                if chunk.get("embedding_1024"):
                    # Parse embedding string to list of floats
                    chunk_embedding_str = chunk["embedding_1024"]
                    try:
                        # Parse the string representation of the vector
                        import ast

                        chunk_embedding = ast.literal_eval(chunk_embedding_str)

                        # Ensure it's a list of floats
                        if isinstance(chunk_embedding, list):
                            chunk_embedding = [float(x) for x in chunk_embedding]

                            # Calculate cosine similarity
                            similarity = self.cosine_similarity(
                                query_embedding, chunk_embedding
                            )
                        else:
                            logger.warning(
                                f"Invalid embedding format for chunk {chunk['id']}"
                            )
                            continue

                    except (ValueError, SyntaxError) as e:
                        logger.warning(
                            f"Failed to parse embedding for chunk {chunk['id']}: {e}"
                        )
                        continue

                    results_with_scores.append(
                        {
                            "id": chunk["id"],
                            "content": chunk["content"],
                            "metadata": chunk["metadata"],
                            "distance": 1 - similarity,  # Convert to distance
                        }
                    )

            # Sort by distance (lowest first)
            results_with_scores.sort(key=lambda x: x["distance"])

            # Deduplicate results based on content (keep the one with best similarity)
            seen_content = set()
            unique_results = []

            for result in results_with_scores:
                # Create a content hash for deduplication (first 200 chars)
                content_hash = result["content"][:200]

                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_results.append(result)

                    # Stop when we have enough unique results
                    if len(unique_results) >= self.config.top_k * 2:
                        break

            results = unique_results

            # Convert results to standard format
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "id": result["id"],
                        "content": result["content"],
                        "metadata": result["metadata"],
                        "source_filename": (
                            result["metadata"].get("source_filename", "unknown")
                            if result["metadata"]
                            else "unknown"
                        ),
                        "page_number": (
                            result["metadata"].get("page_number")
                            if result["metadata"]
                            else None
                        ),
                        "similarity_score": result.get("distance", 0),
                    }
                )

            logger.info(f"Search returned {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching pgvector: {e}")
            raise

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import math

        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have the same length")

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def filter_by_similarity(self, results: List[Dict[str, Any]]) -> List[SearchResult]:
        """Filter results by similarity threshold"""

        # Determine threshold based on query language
        # For now, use Danish thresholds
        thresholds = self.config.danish_thresholds
        min_threshold = thresholds["minimum"]

        filtered_results = []

        for result in results:
            similarity_score = (
                1 - result["similarity_score"]
            )  # Convert distance to similarity

            if similarity_score >= min_threshold:
                search_result = SearchResult(
                    content=result["content"],
                    metadata=result["metadata"] or {},
                    similarity_score=similarity_score,
                    source_filename=result["source_filename"],
                    page_number=result.get("page_number"),
                    chunk_id=str(result["id"]),
                )
                filtered_results.append(search_result)

        # Sort by similarity score (highest first)
        filtered_results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Return top_k results
        return filtered_results[: self.config.top_k]

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
