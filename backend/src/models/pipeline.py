from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.base import AccessLevel


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


class WikiGenerationStatus(str, Enum):
    """Wiki generation run status"""

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
    summary_stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Key metrics (e.g., chunks created, avg sizes)",
    )

    # Sample outputs for debugging
    sample_outputs: dict[str, Any] = Field(
        default_factory=dict,
        description="First 3-5 examples of generated content for debugging",
    )

    # Real data for downstream processing
    data: dict[str, Any] | None = Field(None, description="Complete data structure for downstream steps")

    # Error information
    error_message: str | None = Field(None, description="Error message if failed")
    error_details: dict[str, Any] | None = Field(None, description="Detailed error info")

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = Field(None)

    model_config = ConfigDict(ser_json_timedelta="iso8601")


class WikiPageMetadata(BaseModel):
    """Metadata for a wiki page"""

    title: str = Field(description="Page title")
    filename: str = Field(description="Markdown filename")
    storage_path: str = Field(description="Storage path to the markdown file")
    storage_url: str | None = Field(None, description="Signed URL to the markdown file")
    file_size: int | None = Field(None, description="File size in bytes")
    order: int = Field(description="Page order in the wiki")


class WikiGenerationRun(BaseModel):
    """Wiki generation run model matching the wiki_generation_runs table"""

    id: UUID = Field(description="Wiki generation run unique identifier")
    indexing_run_id: UUID = Field(description="Associated indexing run ID")
    upload_type: UploadType = Field(UploadType.USER_PROJECT, description="Type of upload")
    user_id: UUID | None = Field(None, description="User ID for user projects")
    access_level: AccessLevel = Field(default=AccessLevel.PRIVATE, description="Access control level")
    project_id: UUID | None = Field(None, description="Project ID for user projects")
    upload_id: str | None = Field(None, description="Upload ID for email uploads")
    status: WikiGenerationStatus = Field(WikiGenerationStatus.PENDING, description="Wiki generation status")
    language: str = Field("danish", description="Wiki language")
    model: str = Field(..., description="LLM model used (from SoT)")
    step_results: dict[str, StepResult] = Field(default_factory=dict, description="Detailed results from each step")
    wiki_structure: dict[str, Any] = Field(default_factory=dict, description="Generated wiki structure")
    pages_metadata: list[WikiPageMetadata] = Field(default_factory=list, description="Metadata for generated pages")
    storage_path: str | None = Field(None, description="Base storage path for this wiki run")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Wiki generation start timestamp")
    completed_at: datetime | None = Field(None, description="Wiki generation completion timestamp")
    error_message: str | None = Field(None, description="Error message if wiki generation failed")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Wiki generation creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Wiki generation last update timestamp",
    )

    @classmethod
    def model_validate(cls, obj):
        """Custom validation to handle pages_metadata conversion"""
        if isinstance(obj, dict) and "pages_metadata" in obj:
            # Convert pages_metadata from dict to list if needed
            pages_metadata = obj.get("pages_metadata", {})
            if isinstance(pages_metadata, dict):
                obj["pages_metadata"] = []
            elif isinstance(pages_metadata, list):
                # Handle storage_url conversion in each page metadata
                for page in pages_metadata:
                    if isinstance(page, dict) and "storage_url" in page:
                        storage_url = page["storage_url"]
                        if isinstance(storage_url, dict):
                            if "signedURL" in storage_url:
                                page["storage_url"] = storage_url["signedURL"]
                            elif "signedUrl" in storage_url:
                                page["storage_url"] = storage_url["signedUrl"]
                            else:
                                page["storage_url"] = str(storage_url)
        return super().model_validate(obj)

    # Computed properties for timing data
    @property
    def step_timings(self) -> dict[str, float]:
        """Extract step timings from step_results"""
        if not self.step_results:
            return {}

        timings = {}
        for step_name, step_result in self.step_results.items():
            if hasattr(step_result, "duration_seconds"):
                timings[step_name] = step_result.duration_seconds
            elif isinstance(step_result, dict) and "duration_seconds" in step_result:
                timings[step_name] = step_result["duration_seconds"]
        return timings

    @property
    def total_processing_time(self) -> float:
        """Calculate total processing time across all steps"""
        return sum(self.step_timings.values())

    @property
    def page_count(self) -> int:
        """Get the number of pages in this wiki"""
        return len(self.pages_metadata)

    model_config = ConfigDict(from_attributes=True)


class BasePipelineRun(BaseModel):
    """Common fields/behavior for pipeline runs."""

    id: UUID
    status: PipelineStatus
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error_message: str | None = None

    # Optional shared timings holder
    step_results: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)

    @property
    def step_timings(self) -> dict[str, float]:
        if not self.step_results:
            return {}
        timings: dict[str, float] = {}
        for step_name, step_result in self.step_results.items():
            if hasattr(step_result, "duration_seconds"):
                timings[step_name] = step_result.duration_seconds  # type: ignore[attr-defined]
            elif isinstance(step_result, dict) and "duration_seconds" in step_result:
                timings[step_name] = float(step_result["duration_seconds"])  # type: ignore[index]
        return timings

    @property
    def total_processing_time(self) -> float:
        return sum(self.step_timings.values())


class IndexingRun(BasePipelineRun):
    """Indexing pipeline run model matching the indexing_runs table"""

    upload_type: UploadType = Field(UploadType.USER_PROJECT, description="Type of upload")
    user_id: UUID | None = Field(None, description="Owner user ID (nullable for anonymous)")
    access_level: AccessLevel = Field(default=AccessLevel.PRIVATE, description="Access control level")
    project_id: UUID | None = Field(None, description="Project ID for user projects")
    step_results: dict[str, StepResult] = Field(default_factory=dict, description="Detailed results from each step")
    pipeline_config: dict[str, Any] | None = Field(None, description="Pipeline configuration used for this run")
    model_config = ConfigDict(from_attributes=True)


class QueryRun(BaseModel):
    """Query pipeline run model matching the query_runs table"""

    id: UUID = Field(description="Query run unique identifier")
    user_id: UUID | None = Field(None, description="User ID from Supabase Auth (nullable for anonymous)")
    access_level: AccessLevel = Field(default=AccessLevel.PRIVATE, description="Access control level")
    project_id: UUID | None = Field(None, description="Future: group queries by project")
    query_text: str = Field(description="User's query text")
    response_text: str | None = Field(None, description="Generated response text")
    retrieval_metadata: dict[str, Any] = Field(default_factory=dict, description="Search results, confidence scores")
    response_time_ms: int | None = Field(None, description="Response time in milliseconds")
    step_timings: dict[str, float] | None = Field(None, description="Individual step execution times in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Query creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class UserConfigOverride(BaseModel):
    """User configuration overrides for future UI configurability"""

    id: UUID = Field(description="Override unique identifier")
    user_id: UUID = Field(description="User ID from Supabase Auth")
    config_type: str = Field(description="'indexing' or 'querying'")
    config_key: str = Field(description="Configuration key (e.g., 'chunking.chunk_size')")
    config_value: dict[str, Any] = Field(description="Configuration value")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


# Legacy models for backward compatibility
## Legacy v1 models removed in v2


## Legacy v1 models removed in v2


## Legacy v1 models removed in v2


## Legacy v1 models removed in v2


# Enhanced create/update models for new pipeline types
class IndexingRunCreate(BaseModel):
    """Model for creating a new indexing run"""

    upload_type: UploadType = UploadType.USER_PROJECT
    user_id: UUID | None = None
    project_id: UUID | None = None
    status: PipelineStatus = PipelineStatus.PENDING


class IndexingRunUpdate(BaseModel):
    """Model for updating an existing indexing run"""

    status: PipelineStatus | None = None
    step_results: dict[str, StepResult] | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    upload_type: UploadType | None = None
    project_id: UUID | None = None
    pipeline_config: dict[str, Any] | None = None


class QueryRunCreate(BaseModel):
    """Model for creating a new query run"""

    user_id: UUID
    query_text: str
    project_id: UUID | None = None


class QueryRunUpdate(BaseModel):
    """Model for updating an existing query run"""

    response_text: str | None = None
    retrieval_metadata: dict[str, Any] | None = None
    response_time_ms: int | None = None


class UserConfigOverrideCreate(BaseModel):
    """Model for creating a new user config override"""

    user_id: UUID
    config_type: str
    config_key: str
    config_value: dict[str, Any]


class UserConfigOverrideUpdate(BaseModel):
    """Model for updating an existing user config override"""

    config_value: dict[str, Any]


class PipelineConfig(BaseModel):
    """Pipeline configuration"""

    chunk_size: int = Field(1000, description="Text chunk size")
    chunk_overlap: int = Field(200, description="Chunk overlap size")
    # Values should be read from SoT; no runtime defaults here
    embedding_model: str = Field(..., description="Embedding model name (from SoT)")
    embedding_dimensions: int = Field(..., description="Embedding dimensions (from SoT)")
    retrieval_top_k: int = Field(5, description="Number of chunks to retrieve")
    similarity_threshold: float = Field(0.7, description="Similarity threshold for retrieval")
    generation_model: str = Field(..., description="Generation model name (from SoT)")
    generation_temperature: float = Field(..., description="Generation temperature (from SoT)")
    generation_max_tokens: int = Field(2000, description="Maximum tokens for generation")


class Project(BaseModel):
    """Project model matching the projects table"""

    id: UUID = Field(description="Project unique identifier")
    user_id: UUID = Field(description="User ID from Supabase Auth")
    name: str = Field(description="Project name")
    description: str | None = Field(None, description="Project description")
    access_level: AccessLevel = Field(default=AccessLevel.OWNER, description="Access control level for the project")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Project creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Project last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class EmailUpload(BaseModel):
    """Email upload model matching the email_uploads table"""

    id: str = Field(description="Upload ID from storage path")
    email: str = Field(description="User email address")
    filename: str = Field(description="Original filename")
    file_size: int | None = Field(None, description="File size in bytes")
    status: str = Field("processing", description="Upload status")
    public_url: str | None = Field(None, description="Generated page URL")
    processing_results: dict[str, Any] = Field(default_factory=dict, description="Processing results")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Upload creation timestamp")
    completed_at: datetime | None = Field(None, description="Processing completion timestamp")
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow().replace(day=datetime.utcnow().day + 30),
        description="Upload expiration timestamp",
    )

    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    """Model for creating a new project"""

    user_id: UUID
    name: str
    description: str | None = None
    access_level: AccessLevel = AccessLevel.OWNER


class ProjectUpdate(BaseModel):
    """Model for updating an existing project"""

    name: str | None = None
    description: str | None = None
    access_level: AccessLevel | None = None


class EmailUploadCreate(BaseModel):
    """Model for creating a new email upload"""

    id: str
    email: str
    filename: str
    file_size: int | None = None


class EmailUploadUpdate(BaseModel):
    """Model for updating an existing email upload"""

    status: str | None = None
    public_url: str | None = None
    processing_results: dict[str, Any] | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict()


class IndexingRunDocument(BaseModel):
    """Junction table model for indexing_run_documents"""

    id: UUID = Field(description="Junction record unique identifier")
    indexing_run_id: UUID = Field(description="Indexing run ID")
    document_id: UUID = Field(description="Document ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class IndexingRunDocumentCreate(BaseModel):
    """Model for creating a new indexing run document relationship"""

    indexing_run_id: UUID
    document_id: UUID


# Wiki Generation Models
class WikiGenerationRunCreate(BaseModel):
    """Model for creating a new wiki generation run"""

    indexing_run_id: UUID
    upload_type: UploadType = UploadType.USER_PROJECT
    user_id: UUID | None = None
    project_id: UUID | None = None
    upload_id: str | None = None
    language: str = "danish"  # Default, but should be overridden from indexing run config
    model: str = "google/gemini-2.5-flash-lite"
    status: WikiGenerationStatus = WikiGenerationStatus.PENDING


class WikiGenerationRunUpdate(BaseModel):
    """Model for updating an existing wiki generation run"""

    status: WikiGenerationStatus | None = None
    step_results: dict[str, StepResult] | None = None
    wiki_structure: dict[str, Any] | None = None
    pages_metadata: list[WikiPageMetadata] | None = None
    storage_path: str | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class WikiPageMetadataCreate(BaseModel):
    """Model for creating wiki page metadata"""

    title: str
    filename: str
    storage_path: str
    storage_url: str | None = None
    file_size: int | None = None
    order: int


class WikiPageMetadataUpdate(BaseModel):
    """Model for updating wiki page metadata"""

    title: str | None = None
    filename: str | None = None
    storage_path: str | None = None
    storage_url: str | None = None
    file_size: int | None = None
    order: int | None = None
