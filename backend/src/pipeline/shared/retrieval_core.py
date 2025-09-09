"""
Core retrieval functionality shared between query and wiki generation pipelines.

This module provides the base retrieval infrastructure including pgvector search,
HNSW optimization, and fallback mechanisms that can be used by both pipelines.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import ast

from src.config.database import get_supabase_admin_client

from .retrieval_config import SharedRetrievalConfig
from .embedding_service import VoyageEmbeddingService
from .similarity_service import SimilarityService

logger = logging.getLogger(__name__)


class RetrievalCore:
    """Core retrieval functionality for pgvector search operations"""
    
    def __init__(
        self, 
        config: SharedRetrievalConfig,
        db_client=None,
        embedding_service: Optional[VoyageEmbeddingService] = None
    ):
        """
        Initialize retrieval core.
        
        Args:
            config: Shared retrieval configuration
            db_client: Database client (defaults to admin client)
            embedding_service: Embedding service (created if not provided)
        """
        self.config = config
        self.db = db_client or get_supabase_admin_client()
        self.embedding_service = embedding_service or VoyageEmbeddingService()
        self.similarity_service = SimilarityService(config)
    
    async def generate_query_embedding(self, query_text: str) -> List[float]:
        """
        Generate embedding for query text.
        
        Args:
            query_text: Text to embed
            
        Returns:
            Query embedding vector
        """
        embedding = await self.embedding_service.get_embedding(query_text)
        
        if not self.embedding_service.validate_embedding(embedding):
            logger.warning(
                f"Query embedding dimension mismatch: got {len(embedding)}, "
                f"expected {self.embedding_service.expected_dimensions}"
            )
        
        return embedding
    
    async def search_pgvector_hnsw(
        self,
        query_embedding: List[float],
        indexing_run_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
        similarity_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search using pgvector HNSW optimization with match_chunks function.
        
        Args:
            query_embedding: Query vector
            indexing_run_id: Filter to specific indexing run
            allowed_document_ids: Filter to specific documents
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            List of matching chunks with similarity scores
        """
        logger.info(f"🔍 HNSW search with threshold={similarity_threshold}, count={self.config.top_k * 2}, top_k={self.config.top_k}")
        
        try:
            # Prepare RPC parameters - use 0.0 threshold and 15 results like test file
            rpc_params = {
                'query_embedding': query_embedding,
                'match_threshold': 0.0,  # No threshold filtering, like test file
                'match_count': 15,  # Fixed 15 results like test file
            }
            
            # Add optional filters
            if indexing_run_id:
                rpc_params['indexing_run_id_filter'] = indexing_run_id
                logger.info(f"🔍 Filtering to indexing run: {indexing_run_id}")
            
            # Execute HNSW search
            hnsw_start = datetime.utcnow()
            response = self.db.rpc('match_chunks', rpc_params).execute()
            hnsw_duration = (datetime.utcnow() - hnsw_start).total_seconds() * 1000
            
            # Debug response
            logger.info(f"🔍 HNSW response type: {type(response.data)}, has data: {response.data is not None}")
            if response.data is not None:
                logger.info(f"🔍 HNSW raw response count: {len(response.data)}")
            
            # Filter by document IDs if specified (post-query filtering)
            results = response.data if response.data else []
            if allowed_document_ids and results:
                results = [r for r in results if r.get('document_id') in allowed_document_ids]
                logger.info(f"🔍 After document ID filtering: {len(results)} results")
            
            if results:
                logger.info(f"🔍 ✅ HNSW search SUCCESS in {hnsw_duration:.1f}ms - {len(results)} results")
                return self._format_hnsw_results(results, query_embedding)
            else:
                logger.warning(f"🔍 ⚠️ HNSW returned no results in {hnsw_duration:.1f}ms")
                return []
                
        except Exception as e:
            logger.error(f"🔍 ❌ HNSW search failed: {e}")
            raise
    
    async def search_pgvector_fallback(
        self,
        query_embedding: List[float],
        indexing_run_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fallback Python-based similarity calculation.
        
        Args:
            query_embedding: Query vector
            indexing_run_id: Filter to specific indexing run
            allowed_document_ids: Filter to specific documents
            
        Returns:
            List of matching chunks with similarity scores
        """
        logger.info("🐍 Using Python similarity calculation fallback")
        
        # Build query
        query = (
            self.db.table("document_chunks")
            .select("id,content,metadata,embedding_1024,document_id,indexing_run_id")
            .not_.is_("embedding_1024", "null")
        )
        
        # Apply filters
        if indexing_run_id:
            query = query.eq("indexing_run_id", indexing_run_id)
        if allowed_document_ids:
            query = query.in_("document_id", allowed_document_ids)
        
        # Execute query
        response = query.execute()
        chunks = response.data
        results_with_scores = []
        
        # Calculate similarities in Python
        for chunk in chunks:
            if chunk.get("embedding_1024"):
                chunk_embedding = self._parse_embedding(chunk["embedding_1024"])
                if chunk_embedding:
                    similarity = self.similarity_service.cosine_similarity(query_embedding, chunk_embedding)
                    
                    results_with_scores.append({
                        "id": chunk["id"],
                        "content": chunk["content"],
                        "metadata": chunk["metadata"],
                        "similarity_score": similarity,
                        "document_id": chunk.get("document_id"),
                        "indexing_run_id": chunk.get("indexing_run_id")
                    })
        
        # Sort by similarity (highest first)
        results_with_scores.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Return top 15 results like HNSW
        return results_with_scores[:15]
    
    async def search_with_fallback(
        self,
        query_embedding: List[float],
        indexing_run_id: Optional[str] = None,
        allowed_document_ids: Optional[List[str]] = None,
        language: str = "danish"
    ) -> List[Dict[str, Any]]:
        """
        Search using Python similarity calculation as primary method.
        HNSW is commented out due to production issues.
        
        Args:
            query_embedding: Query vector
            indexing_run_id: Filter to specific indexing run
            allowed_document_ids: Filter to specific documents
            language: Language for threshold selection
            
        Returns:
            List of matching chunks with similarity scores
        """
        # Try HNSW search first for better performance
        try:
            # Try HNSW search first
            logger.info("🚀 Attempting HNSW search for better performance")
            results = await self.search_pgvector_hnsw(
                query_embedding, indexing_run_id, allowed_document_ids, 0.0
            )
            
            if results:
                logger.info(f"✅ HNSW search successful - found {len(results)} results")
                return self._post_process_results(results, language)
        except Exception as e:
            logger.error(f"HNSW search failed: {e}")
            logger.info("⚠️ Falling back to Python similarity calculation")
        
        # Use Python similarity as fallback method
        try:
            logger.info("🐍 Using Python similarity calculation as fallback")
            python_results = await self.search_pgvector_fallback(
                query_embedding, indexing_run_id, allowed_document_ids
            )
            
            return self._post_process_results(python_results, language)
            
        except Exception as e:
            logger.error(f"Python similarity search failed: {e}")
            raise
    
    def _format_hnsw_results(self, results: List[Dict], query_embedding: List[float]) -> List[Dict[str, Any]]:
        """Format results from HNSW search with calculated similarity scores"""
        formatted_results = []
        
        for result in results:
            # Calculate actual similarity using stored embeddings
            chunk_embedding = self._parse_embedding(result.get("embedding_1024"))
            if chunk_embedding:
                similarity = self.similarity_service.cosine_similarity(query_embedding, chunk_embedding)
            else:
                # Fallback to estimated similarity based on HNSW ordering
                similarity = max(0.1, 1.0 - (len(formatted_results) * 0.05))
            
            formatted_results.append({
                "id": result["id"],
                "content": result["content"],
                "metadata": result.get("metadata", {}),
                "similarity_score": max(similarity, 0.0),
                "source_filename": result.get("metadata", {}).get("source_filename", "unknown"),
                "page_number": result.get("metadata", {}).get("page_number"),
                "document_id": result.get("document_id"),
                "indexing_run_id": result.get("indexing_run_id")
            })
        
        return formatted_results
    
    def _post_process_results(self, results: List[Dict[str, Any]], language: str) -> List[Dict[str, Any]]:
        """Post-process results with deduplication and sorting (no threshold filtering)"""
        if not results:
            return []
        
        # Skip threshold filtering - let LLM decide relevance
        # filtered = self.similarity_service.filter_by_similarity_threshold(results, language)
        
        # Deduplicate by content
        deduplicated = self.similarity_service.deduplicate_by_content(results)
        
        # Sort by similarity (highest first)
        sorted_results = self.similarity_service.sort_by_similarity(deduplicated, descending=True)
        
        # Return top 15 results like test file
        return sorted_results[:15]
    
    def _parse_embedding(self, embedding_str: str) -> Optional[List[float]]:
        """Parse embedding string to list of floats"""
        if not embedding_str:
            return None
        
        try:
            # Handle both string and list formats
            if isinstance(embedding_str, str):
                embedding = ast.literal_eval(embedding_str)
            else:
                embedding = embedding_str
            
            # Ensure it's a list of floats
            if isinstance(embedding, list):
                return [float(x) for x in embedding]
            else:
                return None
                
        except (ValueError, SyntaxError) as e:
            logger.warning(f"Failed to parse embedding: {e}")
            return None