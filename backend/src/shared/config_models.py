from __future__ import annotations

from pydantic import BaseModel, Field, PositiveInt, validator
from typing import Literal


class ChunkingConfig(BaseModel):
    """Chunking configuration with required critical fields"""
    chunk_size: PositiveInt = Field(..., description="Target chunk size in characters", gt=0)
    overlap: int = Field(..., description="Overlap between chunks", ge=0)
    strategy: Literal["semantic", "fixed", "sentence"] = Field(..., description="Chunking strategy")
    max_chunk_size: PositiveInt = Field(..., description="Maximum chunk size", gt=0)
    
    # Optional fields with sensible defaults
    separators: list[str] = Field(default=["

", "
", " ", ""], description="Text separators")
    min_chunk_size: int = Field(default=100, ge=0, description="Minimum chunk size")
    include_section_titles: bool = Field(default=False, description="Include section titles")
    
    @validator('max_chunk_size')
    def validate_max_chunk_size(cls, v, values):
        """Ensure max_chunk_size > chunk_size"""
        chunk_size = values.get('chunk_size')
        if chunk_size and v <= chunk_size:
            raise ValueError(f"max_chunk_size ({v}) must be > chunk_size ({chunk_size})")
        return v
    
    @validator('overlap')
    def validate_overlap(cls, v, values):
        """Ensure overlap < chunk_size"""
        chunk_size = values.get('chunk_size')
        if chunk_size and v >= chunk_size:
            raise ValueError(f"overlap ({v}) must be < chunk_size ({chunk_size})")
        return v
        
    class Config:
        extra = "forbid"  # Reject unknown fields


class EmbeddingConfig(BaseModel):
    """Embedding configuration with enforced invariants"""
    model: Literal["voyage-multilingual-2"] = Field(..., description="Embedding model (enforced invariant)")
    dimensions: Literal[1024] = Field(..., description="Embedding dimensions (enforced invariant)")
    provider: Literal["voyage"] = Field(..., description="Embedding provider")
    
    # Optional fields with reasonable defaults
    batch_size: PositiveInt = Field(default=100, description="Batch size for API calls")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, ge=0, description="Delay between retries (seconds)")
    timeout_seconds: int = Field(default=30, ge=1, description="Request timeout")
    resume_capability: bool = Field(default=True, description="Enable resume capability")
    
    class Config:
        extra = "forbid"  # Reject unknown fields


class RetrievalConfig(BaseModel):
    method: str | None = None
    top_k: PositiveInt = Field(5)
    similarity_threshold: float | None = None
    similarity_metric: str | None = None


class GenerationConfig(BaseModel):
    model: str
    temperature: float = Field(0.1, ge=0, le=2)
    max_tokens: PositiveInt = Field(1000)


class OrchestrationConfig(BaseModel):
    max_concurrent_documents: PositiveInt | None = None
    step_timeout_minutes: PositiveInt | None = None


class EffectivePipelineConfig(BaseModel):
    chunking: ChunkingConfig
    embedding: EmbeddingConfig
    retrieval: RetrievalConfig
    generation: GenerationConfig
    orchestration: OrchestrationConfig | None = None
