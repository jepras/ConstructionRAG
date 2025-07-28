from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum


class PipelineStatus(str, Enum):
    """Pipeline run status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStep(str, Enum):
    """Pipeline processing steps"""

    PARTITION = "partition"
    METADATA = "metadata"
    ENRICHMENT = "enrichment"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORAGE = "storage"
    QUERY_PROCESSING = "query_processing"
    RETRIEVAL = "retrieval"
    GENERATION = "generation"


class PipelineRun(BaseModel):
    """Pipeline run model matching the pipeline_runs table"""

    id: UUID = Field(description="Pipeline run unique identifier")
    document_id: UUID = Field(description="Associated document ID")
    status: PipelineStatus = Field(
        PipelineStatus.PENDING, description="Pipeline run status"
    )
    step_results: Dict[str, Any] = Field(
        default_factory=dict, description="Results from each pipeline step"
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="Pipeline start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Pipeline completion timestamp"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if pipeline failed"
    )

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class PipelineStepResult(BaseModel):
    """Result from a single pipeline step"""

    step: PipelineStep
    status: PipelineStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class PipelineRunCreate(BaseModel):
    """Model for creating a new pipeline run"""

    document_id: UUID
    status: PipelineStatus = PipelineStatus.PENDING


class PipelineRunUpdate(BaseModel):
    """Model for updating an existing pipeline run"""

    status: Optional[PipelineStatus] = None
    step_results: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class PipelineConfig(BaseModel):
    """Pipeline configuration"""

    chunk_size: int = Field(1000, description="Text chunk size")
    chunk_overlap: int = Field(200, description="Chunk overlap size")
    embedding_model: str = Field("voyage-large-2", description="Embedding model name")
    embedding_dimensions: int = Field(1536, description="Embedding dimensions")
    retrieval_top_k: int = Field(5, description="Number of chunks to retrieve")
    similarity_threshold: float = Field(
        0.7, description="Similarity threshold for retrieval"
    )
    generation_model: str = Field("gpt-4", description="Generation model name")
    generation_temperature: float = Field(0.1, description="Generation temperature")
    generation_max_tokens: int = Field(
        1000, description="Maximum tokens for generation"
    )
