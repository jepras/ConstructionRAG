"""
Shared embedding service for consistent embedding generation across pipelines.

This service provides a unified interface for generating embeddings using Voyage AI,
ensuring consistency between query processing and wiki generation.
"""

import logging
from typing import List
import httpx

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class VoyageEmbeddingService:
    """Shared Voyage AI embedding service"""
    
    def __init__(self, api_key: str | None = None, model: str = "voyage-multilingual-2"):
        """
        Initialize the embedding service.
        
        Args:
            api_key: Voyage API key (defaults to settings if not provided)
            model: Embedding model to use
        """
        self.api_key = api_key or get_settings().voyage_api_key
        self.model = model
        self.base_url = "https://api.voyageai.com/v1/embeddings"
        self.dimensions = 1024  # voyage-multilingual-2 dimensions
        
        if not self.api_key:
            raise ValueError("VOYAGE_API_KEY not found in environment variables")
    
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        embeddings = await self.get_embeddings([text])
        return embeddings[0] if embeddings else []
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not texts:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": self.model, "input": texts},
                )

                if response.status_code != 200:
                    raise Exception(f"Voyage API error: {response.status_code} - {response.text}")

                result = response.json()
                return [data["embedding"] for data in result["data"]]

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """Validate that embedding has correct dimensions"""
        return len(embedding) == self.dimensions
    
    @property
    def expected_dimensions(self) -> int:
        """Get expected embedding dimensions"""
        return self.dimensions