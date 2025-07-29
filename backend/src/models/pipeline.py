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


class StepResult(BaseModel):
    """Enhanced step result with comprehensive output specification"""

    step: str = Field(description="Step name")
    status: PipelineStatus = Field(description="Step status")
    duration_seconds: float = Field(description="Step execution time in seconds")

    # Summary statistics
    summary_stats: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key metrics (e.g., chunks created, avg sizes)",
    )

    # Sample outputs for debugging
    sample_outputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="First 3-5 examples of generated content for debugging",
    )

    # Error information
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_details: Optional[Dict[str, Any]] = Field(
        None, description="Detailed error info"
    )

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class IndexingRun(BaseModel):
    """Indexing pipeline run model matching the indexing_runs table"""

    id: UUID = Field(description="Indexing run unique identifier")
    document_id: UUID = Field(description="Associated document ID")
    status: PipelineStatus = Field(
        PipelineStatus.PENDING, description="Indexing run status"
    )
    step_results: Dict[str, StepResult] = Field(
        default_factory=dict, description="Detailed results from each step"
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="Indexing start timestamp"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Indexing completion timestamp"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if indexing failed"
    )

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class QueryRun(BaseModel):
    """Query pipeline run model matching the query_runs table"""

    id: UUID = Field(description="Query run unique identifier")
    user_id: UUID = Field(description="User ID from Supabase Auth")
    project_id: Optional[UUID] = Field(
        None, description="Future: group queries by project"
    )
    query_text: str = Field(description="User's query text")
    response_text: Optional[str] = Field(None, description="Generated response text")
    retrieval_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Search results, confidence scores"
    )
    response_time_ms: Optional[int] = Field(
        None, description="Response time in milliseconds"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Query creation timestamp"
    )

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class UserConfigOverride(BaseModel):
    """User configuration overrides for future UI configurability"""

    id: UUID = Field(description="Override unique identifier")
    user_id: UUID = Field(description="User ID from Supabase Auth")
    config_type: str = Field(description="'indexing' or 'querying'")
    config_key: str = Field(
        description="Configuration key (e.g., 'chunking.chunk_size')"
    )
    config_value: Dict[str, Any] = Field(description="Configuration value")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


# Legacy models for backward compatibility
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


# Enhanced create/update models for new pipeline types
class IndexingRunCreate(BaseModel):
    """Model for creating a new indexing run"""

    document_id: UUID
    status: PipelineStatus = PipelineStatus.PENDING


class IndexingRunUpdate(BaseModel):
    """Model for updating an existing indexing run"""

    status: Optional[PipelineStatus] = None
    step_results: Optional[Dict[str, StepResult]] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class QueryRunCreate(BaseModel):
    """Model for creating a new query run"""

    user_id: UUID
    query_text: str
    project_id: Optional[UUID] = None


class QueryRunUpdate(BaseModel):
    """Model for updating an existing query run"""

    response_text: Optional[str] = None
    retrieval_metadata: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[int] = None


class UserConfigOverrideCreate(BaseModel):
    """Model for creating a new user config override"""

    user_id: UUID
    config_type: str
    config_key: str
    config_value: Dict[str, Any]


class UserConfigOverrideUpdate(BaseModel):
    """Model for updating an existing user config override"""

    config_value: Dict[str, Any]


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
