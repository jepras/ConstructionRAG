"""Production retrieval step for query pipeline."""

import logging
from datetime import datetime
from typing import Any

import httpx

from src.config.database import get_supabase_admin_client, get_supabase_client
from src.config.settings import get_settings
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError

from ...shared.base_step import PipelineStep, StepResult
from ..models import QueryVariations, SearchResult

logger = logging.getLogger(__name__)


class VoyageEmbeddingClient:
    """Client for Voyage AI embedding API - same as indexing pipeline"""

    def __init__(self, api_key: str, model: str = "voyage-multilingual-2"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.voyageai.com/v1/embeddings"
        self.dimensions = 1024  # voyage-multilingual-2 dimensions

    async def get_embedding(self, text: str) -> list[float]:
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
                    raise Exception(f"Voyage API error: {response.status_code} - {response.text}")

                result = response.json()
                return result["data"][0]["embedding"]

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise


class RetrievalConfig:
    """Configuration for retrieval step"""

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
    """Retrieval step that searches document chunks using vector similarity"""

    def __init__(self, config: RetrievalConfig, *, db_client=None, use_admin: bool = True):
        super().__init__(config.__dict__, None)
        self.config = config
        # Allow DI to choose client; default to admin for server-side pipeline safety
        if db_client is not None:
            self.db = db_client
        else:
            self.db = get_supabase_admin_client() if use_admin else get_supabase_client()

        # Initialize Voyage client
        settings = get_settings()
        api_key = settings.voyage_api_key
        if not api_key:
            raise ValueError("VOYAGE_API_KEY not found in environment variables")

        self.voyage_client = VoyageEmbeddingClient(api_key=api_key, model=self.config.embedding_model)

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
        # TODO: Implement variation selection logic
        best_query = self.select_best_variation(variations)
        logger.info(f"🔍 SEARCH: Selected best query: '{best_query[:100]}...'")

        # Embed query using same model as documents
        logger.info(f"🔍 SEARCH: Generating embedding with model: {self.config.embedding_model}")
        embed_start = datetime.utcnow()
        query_embedding = await self.embed_query(best_query)
        embed_duration = (datetime.utcnow() - embed_start).total_seconds() * 1000
        logger.info(f"🔍 SEARCH: Embedding generated in {embed_duration:.1f}ms, dimensions: {len(query_embedding)}")

        # Search pgvector using embedding_1024 column
        logger.info(f"🔍 SEARCH: Starting pgvector search")
        search_start = datetime.utcnow()
        results = await self.search_pgvector(query_embedding, indexing_run_id, allowed_document_ids)
        search_duration = (datetime.utcnow() - search_start).total_seconds() * 1000
        logger.info(f"🔍 SEARCH: Pgvector search completed in {search_duration:.1f}ms, found {len(results)} raw results")

        # Filter by similarity threshold
        logger.info(f"🔍 SEARCH: Applying similarity filtering")
        filtered_results = self.filter_by_similarity(results)
        logger.info(f"🔍 SEARCH: After filtering: {len(filtered_results)} results")

        if filtered_results:
            top_similarity = max(r.similarity_score for r in filtered_results)
            avg_similarity = sum(r.similarity_score for r in filtered_results) / len(filtered_results)
            logger.info(f"🔍 SEARCH: Top similarity: {top_similarity:.3f}, Average: {avg_similarity:.3f}")

        logger.info(f"🔍 SEARCH: Search completed, returning {len(filtered_results)} results")
        return filtered_results

    def select_best_variation(self, variations: QueryVariations) -> str:
        """Select the best variation for retrieval"""
        # For now, just return the original
        # TODO: Implement selection logic based on query type, language, etc.
        return variations.original

    async def embed_query(self, query: str) -> list[float]:
        """Embed query using Voyage API"""
        logger.info(f"Embedding query: {query[:50]}...")
        return await self.voyage_client.get_embedding(query)

    async def search_pgvector(
        self,
        query_embedding: list[float],
        indexing_run_id: str | None = None,
        allowed_document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search pgvector using HNSW index and native similarity functions"""

        # Convert embedding to string format for pgvector
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        logger.info(f"🔍 PGVECTOR: Starting pgvector search with embedding dims: {len(query_embedding)}")
        logger.info(f"🔍 PGVECTOR: Config - top_k: {self.config.top_k}, threshold: {self.config.danish_thresholds['minimum']}")

        try:
            # First check if we have match_chunks function available (HNSW optimized)
            try:
                logger.info(f"🔍 PGVECTOR: Attempting match_chunks HNSW function")
                # Try to use HNSW-optimized match_chunks function 
                # IMPORTANT: match_chunks uses SIMILARITY thresholds (higher = more similar)  
                # Function checks: 1 - (embedding <=> query) > match_threshold
                # So we need similarity threshold, not distance threshold
                # Use very permissive similarity threshold, let pipeline do quality filtering
                hnsw_threshold = 0.1  # Similarity threshold: accept 10%+ similar results
                rpc_params = {
                    'query_embedding': query_embedding,  # Use raw embedding, not string format
                    'match_threshold': hnsw_threshold,
                    'match_count': self.config.top_k * 2,  # Get extra for deduplication
                }
                
                # Add optional filters
                if indexing_run_id:
                    rpc_params['indexing_run_id_filter'] = indexing_run_id
                    logger.info(f"🔍 PGVECTOR: Filtering search to indexing run: {indexing_run_id}")
                    
                # Note: match_chunks doesn't support document_ids filter directly
                if allowed_document_ids:
                    logger.info(f"🔍 PGVECTOR: Will filter {len(allowed_document_ids)} document IDs post-query")

                logger.info(f"🔍 PGVECTOR: HNSW params: threshold={rpc_params['match_threshold']}, count={rpc_params['match_count']}")

                # Use HNSW-optimized match_chunks function  
                hnsw_start = datetime.utcnow()
                response = self.db.rpc('match_chunks', rpc_params).execute()
                hnsw_duration = (datetime.utcnow() - hnsw_start).total_seconds() * 1000
                
                # Filter by document IDs if specified (post-query filtering)
                filtered_results = response.data if response.data else []
                if allowed_document_ids and filtered_results:
                    filtered_results = [r for r in response.data if r.get('document_id') in allowed_document_ids]
                    logger.info(f"🔍 PGVECTOR: After document ID filtering: {len(filtered_results)} results")
                
                if filtered_results:
                    logger.info(f"🔍 PGVECTOR: ✅ HNSW search SUCCESS in {hnsw_duration:.1f}ms - {len(filtered_results)} results")
                    return self._format_match_chunks_results(filtered_results, query_embedding)
                else:
                    logger.warning(f"🔍 PGVECTOR: ⚠️  HNSW returned no results in {hnsw_duration:.1f}ms with threshold {hnsw_threshold}")
                    logger.warning(f"🔍 PGVECTOR: ⚠️  This means no chunks passed HNSW threshold {hnsw_threshold} for this query")
                    logger.warning(f"🔍 PGVECTOR: 🚨 FALLING BACK TO PYTHON to compare results - investigate threshold mismatch!")
                    
                    # Compare with Python fallback to understand threshold differences
                    python_start = datetime.utcnow()
                    python_results = await self._fallback_python_similarity(
                        query_embedding, indexing_run_id, allowed_document_ids
                    )
                    python_duration = (datetime.utcnow() - python_start).total_seconds() * 1000
                    
                    if python_results:
                        logger.warning(f"🔍 PGVECTOR: 🐍 Python found {len(python_results)} results in {python_duration:.1f}ms")
                        logger.warning(f"🔍 PGVECTOR: 🐍 Top Python similarity: {python_results[0]['similarity_score']:.4f}")
                        logger.warning(f"🔍 PGVECTOR: 🚨 HNSW threshold {hnsw_threshold} too restrictive - Python found results!")
                        return python_results
                    else:
                        logger.info(f"🔍 PGVECTOR: 🐍 Python also found no results in {python_duration:.1f}ms - query genuinely has no matches")
                        return []
                    
            except Exception as rpc_error:
                logger.error(f"🔍 PGVECTOR: ❌ HNSW match_chunks function failed!")
                logger.error(f"🔍 PGVECTOR: Error type: {type(rpc_error).__name__}")
                logger.error(f"🔍 PGVECTOR: Error message: {str(rpc_error)}")
                logger.error(f"🔍 PGVECTOR: RPC params were: {rpc_params}")
                logger.warning(f"🔍 PGVECTOR: 🚨 FALLING BACK TO PYTHON SIMILARITY - this should be rare!")
                
                # Fallback to Python similarity
                python_start = datetime.utcnow()
                python_results = await self._fallback_python_similarity(
                    query_embedding, indexing_run_id, allowed_document_ids
                )
                python_duration = (datetime.utcnow() - python_start).total_seconds() * 1000
                
                if python_results:
                    logger.warning(f"🔍 PGVECTOR: 🐍 Python fallback SUCCESS in {python_duration:.1f}ms - {len(python_results)} results")
                    logger.warning(f"🔍 PGVECTOR: 🐍 Top Python similarity: {python_results[0]['similarity_score']:.4f}")
                    logger.warning(f"🔍 PGVECTOR: 🚨 HNSW FAILED but Python found results - investigate threshold mismatch!")
                else:
                    logger.info(f"🔍 PGVECTOR: 🐍 Python fallback also found no results in {python_duration:.1f}ms")
                
                return python_results

        except Exception as e:
            logger.error(f"Error in pgvector search: {e}")
            raise

    def _format_similarity_search_results(self, results: list[dict]) -> list[dict[str, Any]]:
        """Format results from similarity_search stored procedure"""
        formatted_results = []
        seen_content = set()
        
        for result in results:
            # Deduplicate by content hash
            content_hash = result["content"][:200]
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)
            
            formatted_results.append({
                "id": result["id"],
                "content": result["content"],
                "metadata": result.get("metadata", {}),
                "source_filename": result.get("metadata", {}).get("source_filename", "unknown"),
                "page_number": result.get("metadata", {}).get("page_number"),
                "similarity_score": result.get("distance", 0),  # Note: this should be similarity, not distance
            })
            
            if len(formatted_results) >= self.config.top_k:
                break
                
        return formatted_results

    def _format_match_chunks_results(self, results: list[dict], query_embedding: list[float]) -> list[dict[str, Any]]:
        """Format results from match_chunks HNSW function"""
        formatted_results = []
        seen_content = set()
        
        for result in results:
            # Deduplicate by content hash
            content_hash = result["content"][:200]
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)
            
            # Calculate REAL similarity using actual embeddings
            chunk_embedding_str = result.get("embedding_1024")
            if chunk_embedding_str:
                try:
                    # Parse the stored embedding
                    import ast
                    if isinstance(chunk_embedding_str, str):
                        chunk_embedding = ast.literal_eval(chunk_embedding_str)
                    else:
                        chunk_embedding = chunk_embedding_str
                    
                    # Calculate actual cosine similarity
                    actual_similarity = self.cosine_similarity(query_embedding, chunk_embedding)
                except Exception as e:
                    logger.warning(f"Failed to calculate similarity for chunk {result['id']}: {e}")
                    # Fall back to estimated similarity based on HNSW ordering
                    actual_similarity = 1.0 - (len(formatted_results) * 0.05)
            else:
                # Fall back to estimated similarity if no embedding available
                actual_similarity = 1.0 - (len(formatted_results) * 0.05)
            
            formatted_results.append({
                "id": result["id"],
                "content": result["content"],
                "metadata": result.get("metadata", {}),
                "source_filename": result.get("metadata", {}).get("source_filename", "unknown"),
                "page_number": result.get("metadata", {}).get("page_number"),
                "similarity_score": max(actual_similarity, 0.0),  # Real similarity score
            })
            
            if len(formatted_results) >= self.config.top_k:
                break
                
        return formatted_results

    def _format_pgvector_results(self, results: list[dict]) -> list[dict[str, Any]]:
        """Format results from native pgvector SQL query"""
        formatted_results = []
        seen_content = set()
        
        for result in results:
            # Deduplicate by content hash
            content_hash = result["content"][:200]
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)
            
            # Convert distance to similarity
            distance = result.get("distance", 1.0)
            similarity = 1.0 - distance
            
            formatted_results.append({
                "id": result["id"],
                "content": result["content"],
                "metadata": result.get("metadata", {}),
                "source_filename": result.get("metadata", {}).get("source_filename", "unknown"),
                "page_number": result.get("metadata", {}).get("page_number"),
                "similarity_score": similarity,
            })
            
            if len(formatted_results) >= self.config.top_k:
                break
                
        return formatted_results

    async def _fallback_python_similarity(
        self,
        query_embedding: list[float], 
        indexing_run_id: str | None = None,
        allowed_document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fallback Python-based similarity calculation (original implementation)"""
        logger.info("Using Python similarity calculation fallback")
        
        # Get chunks and calculate similarity in Python
        query = (
            self.db.table("document_chunks")
            .select("id,content,metadata,embedding_1024,document_id,indexing_run_id")
            .not_.is_("embedding_1024", "null")
        )

        # Filter by indexing_run_id if provided
        if indexing_run_id:
            query = query.eq("indexing_run_id", indexing_run_id)
        # Apply document filter if provided
        if allowed_document_ids:
            query = query.in_("document_id", allowed_document_ids)

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
                        similarity = self.cosine_similarity(query_embedding, chunk_embedding)
                    else:
                        logger.warning(f"Invalid embedding format for chunk {chunk['id']}")
                        continue

                except (ValueError, SyntaxError) as e:
                    logger.warning(f"Failed to parse embedding for chunk {chunk['id']}: {e}")
                    continue

                results_with_scores.append({
                    "id": chunk["id"],
                    "content": chunk["content"],
                    "metadata": chunk["metadata"],
                    "distance": 1 - similarity,  # Convert to distance
                })

        # Sort by distance (lowest first)
        results_with_scores.sort(key=lambda x: x["distance"])

        # Deduplicate and format results
        seen_content = set()
        formatted_results = []

        for result in results_with_scores:
            content_hash = result["content"][:200]
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                formatted_results.append({
                    "id": result["id"],
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "source_filename": (
                        result["metadata"].get("source_filename", "unknown") if result["metadata"] else "unknown"
                    ),
                    "page_number": (result["metadata"].get("page_number") if result["metadata"] else None),
                    "similarity_score": 1 - result.get("distance", 1),  # Convert distance to similarity
                })
                
                if len(formatted_results) >= self.config.top_k * 2:
                    break

        if formatted_results:
            top_similarity = max(r["similarity_score"] for r in formatted_results)
            avg_similarity = sum(r["similarity_score"] for r in formatted_results) / len(formatted_results)
            logger.info(f"🐍 Python fallback returned {len(formatted_results)} results")
            logger.info(f"🐍 Python similarity range: {top_similarity:.4f} (top) to {avg_similarity:.4f} (avg)")
        else:
            logger.info(f"🐍 Python fallback found no results")
        return formatted_results

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import math

        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have the same length")

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def filter_by_similarity(self, results: list[dict[str, Any]]) -> list[SearchResult]:
        """Filter results by similarity threshold"""

        # Determine threshold based on query language
        # For now, use Danish thresholds
        thresholds = self.config.danish_thresholds
        min_threshold = thresholds["minimum"]

        filtered_results = []

        for result in results:
            # Check if this is already a similarity score (HNSW results) or distance (SQL results)
            # HNSW results come with estimated similarity scores (0.1 to 1.0)
            # SQL results come with distance values that need conversion
            if result["similarity_score"] <= 1.0 and result["similarity_score"] >= 0.1:
                # This looks like a similarity score from HNSW (estimated)
                similarity_score = result["similarity_score"]
            else:
                # This looks like a distance score from SQL, convert to similarity
                similarity_score = 1 - result["similarity_score"]

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
