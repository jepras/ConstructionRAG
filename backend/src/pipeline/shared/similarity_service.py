"""
Shared similarity calculation service for consistent similarity metrics across pipelines.

This service provides cosine similarity calculation and threshold-based filtering
optimized for Danish construction documents.
"""

import logging
import math
from typing import List, Dict, Any

from .retrieval_config import SharedRetrievalConfig

logger = logging.getLogger(__name__)


class SimilarityService:
    """Service for similarity calculations and filtering"""
    
    def __init__(self, config: SharedRetrievalConfig):
        """
        Initialize similarity service with configuration.
        
        Args:
            config: Shared retrieval configuration
        """
        self.config = config
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        if len(vec1) != len(vec2):
            logger.warning(f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}")
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
    
    def calculate_similarities(
        self, 
        query_embedding: List[float], 
        document_embeddings: List[List[float]]
    ) -> List[float]:
        """
        Calculate similarity scores for query against multiple document embeddings.
        
        Args:
            query_embedding: Query vector
            document_embeddings: List of document vectors
            
        Returns:
            List of similarity scores
        """
        similarities = []
        for doc_embedding in document_embeddings:
            similarity = self.cosine_similarity(query_embedding, doc_embedding)
            similarities.append(similarity)
        return similarities
    
    def filter_by_similarity_threshold(
        self, 
        results: List[Dict[str, Any]], 
        language: str = "danish"
    ) -> List[Dict[str, Any]]:
        """
        Filter results by similarity threshold for specified language.
        
        Args:
            results: List of result dictionaries with 'similarity_score' key
            language: Language for threshold selection (default: danish)
            
        Returns:
            Filtered results above minimum threshold
        """
        min_threshold = self.config.get_minimum_threshold(language)
        
        filtered_results = []
        for result in results:
            similarity_score = result.get("similarity_score", 0.0)
            if similarity_score >= min_threshold:
                filtered_results.append(result)
        
        return filtered_results
    
    def sort_by_similarity(
        self, 
        results: List[Dict[str, Any]], 
        descending: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Sort results by similarity score.
        
        Args:
            results: List of result dictionaries with 'similarity_score' key
            descending: Sort in descending order (highest similarity first)
            
        Returns:
            Sorted results
        """
        return sorted(
            results, 
            key=lambda x: x.get("similarity_score", 0.0), 
            reverse=descending
        )
    
    def get_quality_category(self, similarity_score: float, language: str = "danish") -> str:
        """
        Categorize similarity score quality.
        
        Args:
            similarity_score: Similarity score to categorize
            language: Language for threshold selection
            
        Returns:
            Quality category: 'excellent', 'good', 'acceptable', or 'poor'
        """
        thresholds = self.config.get_thresholds_for_language(language)
        
        if similarity_score >= thresholds.excellent:
            return "excellent"
        elif similarity_score >= thresholds.good:
            return "good"
        elif similarity_score >= thresholds.acceptable:
            return "acceptable"
        else:
            return "poor"
    
    def deduplicate_by_content(
        self, 
        results: List[Dict[str, Any]], 
        content_key: str = "content",
        hash_length: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate results based on content similarity.
        
        Args:
            results: List of result dictionaries
            content_key: Key containing content for deduplication
            hash_length: Length of content to use for hashing
            
        Returns:
            Deduplicated results
        """
        unique_results = []
        seen_hashes = set()
        
        for result in results:
            content = result.get(content_key, "")
            content_hash = hash(content[:hash_length])
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_results.append(result)
        
        return unique_results