from __future__ import annotations

from pydantic import BaseModel, Field, PositiveInt


class ChunkingConfig(BaseModel):
    chunk_size: PositiveInt = Field(1000)
    overlap: int = Field(200, ge=0)
    strategy: str | None = None
    separators: list[str] | None = None
    min_chunk_size: int | None = None
    max_chunk_size: int | None = None


class EmbeddingConfig(BaseModel):
    model: str = Field("voyage-multilingual-2")
    dimensions: PositiveInt = Field(1024)
    batch_size: PositiveInt | None = None
    provider: str | None = None


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
