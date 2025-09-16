"""Retriever step for checklist analysis pipeline."""

import ast
import logging
from typing import Dict, Any, List

import numpy as np

from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings
from src.pipeline.indexing.steps.embedding import VoyageEmbeddingClient

logger = logging.getLogger(__name__)


async def retrieve_chunks_for_query(
    query: str, 
    indexing_run_id: str, 
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Retrieve chunks for a query using existing vector search patterns.
    Following the pattern from wiki generation overview step.
    """
    try:
        # Initialize Voyage client (following wiki generation pattern)
        settings = get_settings()
        voyage_client = VoyageEmbeddingClient(
            api_key=settings.voyage_api_key,
            model="voyage-multilingual-2"
        )
        
        # Generate query embedding
        embeddings = await voyage_client.get_embeddings([query])
        query_embedding = embeddings[0] if embeddings else []
        
        if not query_embedding:
            logger.warning(f"Failed to generate embedding for query: {query[:100]}")
            return []
        
        # Get document IDs and names for this indexing run
        supabase = get_supabase_admin_client()
        docs_result = (
            supabase.table("indexing_run_documents")
            .select("document_id, documents(*)")
            .eq("indexing_run_id", indexing_run_id)
            .execute()
        )
        
        if not docs_result.data:
            logger.warning(f"No documents found for indexing run {indexing_run_id}")
            return []
        
        # Build document lookup map for names
        documents = [item["documents"] for item in docs_result.data if item["documents"]]
        document_lookup = {doc["id"]: doc.get("filename", f"document_{doc['id'][:8]}") for doc in documents}
        document_ids = list(document_lookup.keys())
        logger.info(f"Found {len(document_ids)} documents for indexing run")
        
        # Vector similarity search (following wiki generation pattern)
        query_result = (
            supabase.table("document_chunks")
            .select("id,document_id,content,metadata,embedding_1024")
            .in_("document_id", document_ids)
            .not_.is_("embedding_1024", "null")
            .execute()
        )
        
        if not query_result.data:
            logger.warning(f"No chunks found for documents")
            return []
        
        logger.info(f"Found {len(query_result.data)} chunks to search")
        
        # Calculate cosine similarity (following production pattern)
        results_with_scores = []
        for chunk in query_result.data:
            try:
                embedding_str = chunk["embedding_1024"]
                if not embedding_str:
                    continue
                    
                chunk_embedding = ast.literal_eval(embedding_str)
                
                if isinstance(chunk_embedding, list):
                    chunk_embedding = [float(x) for x in chunk_embedding]
                    similarity = _cosine_similarity(query_embedding, chunk_embedding)
                    
                    # Only include if above threshold (using wiki similarity threshold)
                    if similarity >= 0.15:
                        # Add document name to chunk metadata
                        chunk_with_name = chunk.copy()
                        document_id = chunk.get("document_id")
                        if document_id in document_lookup:
                            # Update chunk metadata to include document name
                            metadata = chunk_with_name.get("metadata", {}) or {}
                            metadata["document_name"] = document_lookup[document_id]
                            chunk_with_name["metadata"] = metadata
                        
                        results_with_scores.append({
                            "chunk": chunk_with_name,
                            "similarity": similarity,
                            "query": query
                        })
            except (ValueError, SyntaxError, TypeError) as e:
                logger.debug(f"Error processing chunk embedding: {e}")
                continue
        
        # Sort by similarity and return top_k
        results_with_scores.sort(key=lambda x: x["similarity"], reverse=True)
        top_results = [result["chunk"] for result in results_with_scores[:top_k]]
        
        logger.info(f"Retrieved {len(top_results)} chunks above threshold for query")
        return top_results
        
    except Exception as e:
        logger.error(f"Error retrieving chunks for query: {e}")
        return []


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity (copied from wiki generation)."""
    try:
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(np.clip(similarity, -1.0, 1.0))
    except Exception as e:
        logger.debug(f"Error calculating similarity: {e}")
        return 0.0


def deduplicate_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate chunks by ID."""
    seen_ids = set()
    unique_chunks = []
    
    for chunk in chunks:
        chunk_id = chunk.get("id")
        if chunk_id and chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            unique_chunks.append(chunk)
    
    return unique_chunks


async def retrieve_chunks_for_queries_batch(
    queries: List[str],
    indexing_run_id: str,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant chunks for multiple queries using batch embedding generation.
    Returns deduplicated chunks across all queries. This is optimized for performance
    by batching the embedding API calls instead of making them sequentially.
    
    This can provide significant performance improvement when processing many queries,
    especially for checklist analysis with 10-20+ generated search queries.
    """
    if not queries:
        return []
        
    try:
        # Initialize Voyage client (following wiki generation pattern)
        settings = get_settings()
        voyage_client = VoyageEmbeddingClient(
            api_key=settings.voyage_api_key,
            model="voyage-multilingual-2"
        )
        
        # Generate embeddings for all queries in batch (key optimization!)
        logger.info(f"🚀 Generating embeddings for {len(queries)} queries in batch")
        query_embeddings = await voyage_client.get_embeddings(queries)
        
        if not query_embeddings or len(query_embeddings) != len(queries):
            logger.warning(f"Failed to generate embeddings for all queries")
            return []
        
        # Get document IDs and names for this indexing run
        supabase = get_supabase_admin_client()
        docs_result = (
            supabase.table("indexing_run_documents")
            .select("document_id, documents(*)")
            .eq("indexing_run_id", indexing_run_id)
            .execute()
        )
        
        if not docs_result.data:
            logger.warning(f"No documents found for indexing run {indexing_run_id}")
            return []
        
        # Build document lookup map for names
        documents = [item["documents"] for item in docs_result.data if item["documents"]]
        document_lookup = {doc["id"]: doc.get("filename", f"document_{doc['id'][:8]}") for doc in documents}
        document_ids = list(document_lookup.keys())
        logger.info(f"Found {len(document_ids)} documents for indexing run")
        
        # Get all chunks once
        query_result = (
            supabase.table("document_chunks")
            .select("id,document_id,content,metadata,embedding_1024")
            .in_("document_id", document_ids)
            .not_.is_("embedding_1024", "null")
            .execute()
        )
        
        if not query_result.data:
            logger.warning(f"No chunks found for documents")
            return []
        
        logger.info(f"Found {len(query_result.data)} chunks to search")
        
        # Calculate similarities for all query-chunk combinations
        all_results = []
        for query_idx, query_embedding in enumerate(query_embeddings):
            query = queries[query_idx]
            results_with_scores = []
            
            for chunk in query_result.data:
                try:
                    embedding_str = chunk["embedding_1024"]
                    if not embedding_str:
                        continue
                        
                    chunk_embedding = ast.literal_eval(embedding_str)
                    
                    if isinstance(chunk_embedding, list):
                        chunk_embedding = [float(x) for x in chunk_embedding]
                        similarity = _cosine_similarity(query_embedding, chunk_embedding)
                        
                        # Only include if above threshold (using wiki similarity threshold)
                        if similarity >= 0.15:
                            # Add document name to chunk metadata
                            chunk_with_name = chunk.copy()
                            document_id = chunk.get("document_id")
                            if document_id in document_lookup:
                                # Update chunk metadata to include document name
                                metadata = chunk_with_name.get("metadata", {}) or {}
                                metadata["document_name"] = document_lookup[document_id]
                                chunk_with_name["metadata"] = metadata
                            
                            results_with_scores.append({
                                "chunk": chunk_with_name,
                                "similarity": similarity,
                                "query": query,
                                "query_idx": query_idx
                            })
                        
                except (ValueError, SyntaxError, TypeError) as e:
                    logger.debug(f"Error processing chunk embedding: {e}")
                    continue
            
            # Sort by similarity and take top results for this query
            results_with_scores.sort(key=lambda x: x["similarity"], reverse=True)
            all_results.extend(results_with_scores[:top_k])
        
        # Deduplicate by chunk ID (prioritizing higher similarity scores)
        unique_results = {}
        for result in all_results:
            chunk_id = result["chunk"]["id"]
            if chunk_id not in unique_results or result["similarity"] > unique_results[chunk_id]["similarity"]:
                unique_results[chunk_id] = result
        
        # Convert back to list and sort by similarity
        final_results = list(unique_results.values())
        final_results.sort(key=lambda x: x["similarity"], reverse=True)
        
        logger.info(f"⚡ Retrieved {len(final_results)} unique chunks across {len(queries)} queries")
        return [result["chunk"] for result in final_results]
        
    except Exception as e:
        logger.error(f"Error retrieving chunks for queries: {e}")
        return []