from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum


class UploadType(str, Enum):
    """Type of upload - email-based or user project."""

    EMAIL = "email"
    USER_PROJECT = "user_project"


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

    # Real data for downstream processing
    data: Optional[Dict[str, Any]] = Field(
        None, description="Complete data structure for downstream steps"
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
        json_encoders = {
            datetime: lambda v: v.isoformat() if hasattr(v, "isoformat") else str(v)
        }


class IndexingRun(BaseModel):
    """Indexing pipeline run model matching the indexing_runs table"""

    id: UUID = Field(description="Indexing run unique identifier")
    document_id: UUID = Field(description="Associated document ID")
    upload_type: UploadType = Field(
        UploadType.USER_PROJECT, description="Type of upload"
    )
    upload_id: Optional[str] = Field(None, description="Upload ID for email uploads")
    project_id: Optional[UUID] = Field(None, description="Project ID for user projects")
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
    upload_type: UploadType = UploadType.USER_PROJECT
    upload_id: Optional[str] = None
    project_id: Optional[UUID] = None
    status: PipelineStatus = PipelineStatus.PENDING


class IndexingRunUpdate(BaseModel):
    """Model for updating an existing indexing run"""

    status: Optional[PipelineStatus] = None
    step_results: Optional[Dict[str, StepResult]] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    upload_type: Optional[UploadType] = None
    upload_id: Optional[str] = None
    project_id: Optional[UUID] = None


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


# New models for storage structure support
class Project(BaseModel):
    """Project model matching the projects table"""

    id: UUID = Field(description="Project unique identifier")
    user_id: UUID = Field(description="User ID from Supabase Auth")
    name: str = Field(description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Project creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Project last update timestamp"
    )

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class EmailUpload(BaseModel):
    """Email upload model matching the email_uploads table"""

    id: str = Field(description="Upload ID from storage path")
    email: str = Field(description="User email address")
    filename: str = Field(description="Original filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    status: str = Field("processing", description="Upload status")
    public_url: Optional[str] = Field(None, description="Generated page URL")
    processing_results: Dict[str, Any] = Field(
        default_factory=dict, description="Processing results"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Upload creation timestamp"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Processing completion timestamp"
    )
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow().replace(
            day=datetime.utcnow().day + 30
        ),
        description="Upload expiration timestamp",
    )

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ProjectCreate(BaseModel):
    """Model for creating a new project"""

    user_id: UUID
    name: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    """Model for updating an existing project"""

    name: Optional[str] = None
    description: Optional[str] = None


class EmailUploadCreate(BaseModel):
    """Model for creating a new email upload"""

    id: str
    email: str
    filename: str
    file_size: Optional[int] = None


class EmailUploadUpdate(BaseModel):
    """Model for updating an existing email upload"""

    status: Optional[str] = None
    public_url: Optional[str] = None
    processing_results: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
