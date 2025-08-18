"""
Shared retrieval configuration for both query and wiki pipelines.

This module provides common configuration settings for retrieval operations,
ensuring consistency across different pipeline components.
"""

from typing import Dict, Any
from pydantic import BaseModel


class RetrievalThresholds(BaseModel):
    """Similarity threshold configuration"""
    excellent: float = 0.75
    good: float = 0.60
    acceptable: float = 0.40
    minimum: float = 0.25


class DanishThresholds(BaseModel):
    """Danish language-optimized similarity thresholds"""
    excellent: float = 0.70
    good: float = 0.55
    acceptable: float = 0.35
    minimum: float = 0.20


class SharedRetrievalConfig(BaseModel):
    """Shared configuration for retrieval operations"""
    
    # Embedding configuration
    embedding_model: str = "voyage-multilingual-2"
    dimensions: int = 1024
    
    # Search configuration  
    similarity_metric: str = "cosine"
    top_k: int = 5
    
    # Similarity thresholds
    similarity_thresholds: RetrievalThresholds = RetrievalThresholds()
    danish_thresholds: DanishThresholds = DanishThresholds()
    
    # Performance configuration
    timeout_seconds: float = 30.0
    max_chunks_per_query: int = 10
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "SharedRetrievalConfig":
        """Create configuration from dictionary"""
        return cls(**config)
    
    def get_thresholds_for_language(self, language: str = "danish") -> RetrievalThresholds:
        """Get appropriate thresholds for language"""
        if language.lower() == "danish":
            return RetrievalThresholds(
                excellent=self.danish_thresholds.excellent,
                good=self.danish_thresholds.good,
                acceptable=self.danish_thresholds.acceptable,
                minimum=self.danish_thresholds.minimum
            )
        return self.similarity_thresholds
    
    def get_minimum_threshold(self, language: str = "danish") -> float:
        """Get minimum similarity threshold for language"""
        thresholds = self.get_thresholds_for_language(language)
        return thresholds.minimum