from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Handle StepResult import to avoid circular dependency
if TYPE_CHECKING:
    from src.models.pipeline import StepResult


class DocumentStatus(str, Enum):
    """Document processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(BaseModel):
    """Document model matching the documents table"""

    id: UUID = Field(description="Document unique identifier")
    user_id: Optional[UUID] = Field(
        None, description="Owner user ID from Supabase Auth"
    )
    filename: str = Field(description="Original filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    file_path: Optional[str] = Field(None, description="Supabase Storage path")
    page_count: Optional[int] = Field(None, description="Number of pages in PDF")
    status: DocumentStatus = Field(
        DocumentStatus.PENDING, description="Processing status"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if processing failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    # Step results from indexing pipeline
    step_results: Dict[str, Any] = Field(
        default_factory=dict, description="Step results from indexing pipeline"
    )
    indexing_status: Optional[str] = Field(
        None,
        description="Current indexing status (pending, running, completed, failed)",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Document creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Document last update timestamp"
    )

    # Computed properties for timing data
    @property
    def step_timings(self) -> Dict[str, float]:
        """Extract step timings from step_results"""
        logger.info(
            f"🔍 Computing step_timings for document {self.filename} (ID: {self.id})"
        )
        logger.info(f"🔍 Raw step_results: {self.step_results}")

        if not self.step_results:
            logger.warning(f"⚠️ No step_results found for document {self.filename}")
            return {}

        timings = {}
        for step_name, step_data in self.step_results.items():
            logger.info(f"🔍 Processing step: {step_name}, data: {step_data}")
            if isinstance(step_data, dict) and "duration_seconds" in step_data:
                timings[step_name] = step_data["duration_seconds"]
                logger.info(
                    f"✅ Added timing for {step_name}: {step_data['duration_seconds']}s"
                )
            else:
                logger.warning(f"⚠️ No duration_seconds found for step {step_name}")

        logger.info(f"🔍 Final step_timings: {timings}")
        return timings

    @property
    def total_processing_time(self) -> float:
        """Calculate total processing time across all steps"""
        step_timings = self.step_timings
        total = sum(step_timings.values())
        logger.info(
            f"🔍 Total processing time for {self.filename}: {total}s (from {step_timings})"
        )
        return total

    @property
    def current_step(self) -> Optional[str]:
        """Get the current step being processed (last incomplete step)"""
        if not self.step_results:
            return "partition"  # First step

        # Define step order (both class names and simple names)
        step_order_full = [
            "PartitionStep",
            "MetadataStep",
            "EnrichmentStep",
            "ChunkingStep",
            "EmbeddingStep",
        ]
        step_order_simple = [
            "partition",
            "metadata",
            "enrichment",
            "chunking",
            "embedding",
        ]

        # Find the first step that is not completed or is failed
        for i, (full_name, simple_name) in enumerate(
            zip(step_order_full, step_order_simple)
        ):
            # Check if step exists in either naming convention
            step_data = self.step_results.get(full_name) or self.step_results.get(
                simple_name
            )

            if not step_data:
                return simple_name  # Next step to run

            status = step_data.get("status") if isinstance(step_data, dict) else None
            if status not in ["completed"]:
                return simple_name  # This step needs attention (running, failed, etc.)

        return None  # All steps completed

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class DocumentChunk(BaseModel):
    """Document chunk model matching the document_chunks table"""

    id: UUID = Field(description="Chunk unique identifier")
    document_id: UUID = Field(description="Parent document ID")
    chunk_index: int = Field(description="Chunk index within document")
    content: str = Field(description="Chunk text content")
    embedding: Optional[List[float]] = Field(
        None, description="Vector embedding (1536 dimensions)"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    page_number: Optional[int] = Field(None, description="Source page number")
    section_title: Optional[str] = Field(None, description="Section title if available")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Chunk creation timestamp"
    )

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class DocumentCreate(BaseModel):
    """Model for creating a new document"""

    filename: str
    file_size: Optional[int] = None
    file_path: Optional[str] = None
    page_count: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentUpdate(BaseModel):
    """Model for updating an existing document"""

    filename: Optional[str] = None
    file_size: Optional[int] = None
    file_path: Optional[str] = None
    page_count: Optional[int] = None
    status: Optional[DocumentStatus] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentChunkCreate(BaseModel):
    """Model for creating a new document chunk"""

    document_id: UUID
    chunk_index: int
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    page_number: Optional[int] = None
    section_title: Optional[str] = None


class DocumentWithChunks(Document):
    """Document model including its chunks"""

    chunks: List[DocumentChunk] = Field(
        default_factory=list, description="Document chunks"
    )
