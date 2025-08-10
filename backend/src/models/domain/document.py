import logging
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import ConfigDict, Field, computed_field

from ..base import BaseDocument
from .document_chunk import DocumentChunk

logger = logging.getLogger(__name__)

# Handle StepResult import to avoid circular dependency
if TYPE_CHECKING:  # pragma: no cover
    from src.models.pipeline import StepResult  # noqa: F401


class DocumentStatus(str, Enum):
    """Document processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(BaseDocument):
    """Document model matching the documents table"""

    id: UUID = Field(description="Document unique identifier")
    user_id: UUID | None = Field(None, description="Owner user ID from Supabase Auth")
    status: DocumentStatus = Field(
        DocumentStatus.PENDING, description="Processing status"
    )
    error_message: str | None = Field(
        None, description="Error message if processing failed"
    )
    # Step results from indexing pipeline
    step_results: dict[str, Any] = Field(
        default_factory=dict, description="Step results from indexing pipeline"
    )
    indexing_status: str | None = Field(
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
    @computed_field(return_type=dict[str, float])
    def step_timings(self) -> dict[str, float]:
        """Extract step timings from step_results"""
        if not self.step_results:
            return {}

        timings = {}
        for step_name, step_data in self.step_results.items():
            if isinstance(step_data, dict) and "duration_seconds" in step_data:
                timings[step_name] = step_data["duration_seconds"]
            else:
                logger.warning(f"⚠️ No duration_seconds found for step {step_name}")

        logger.info(f"🔍 Final step_timings: {timings}")
        return timings

    @computed_field(return_type=float)
    def total_processing_time(self) -> float:
        """Calculate total processing time across all steps"""
        step_timings = self.step_timings
        total = sum(step_timings.values())
        return total

    @computed_field(return_type=str | None)
    def current_step(self) -> str | None:
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
        for _i, (full_name, simple_name) in enumerate(
            zip(step_order_full, step_order_simple, strict=False)
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

    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(BaseDocument):
    """Model for creating a new document"""

    model_config = ConfigDict(extra="forbid")


class DocumentUpdate(BaseDocument):
    """Model for updating an existing document"""

    filename: str | None = None
    file_size: int | None = None
    file_path: str | None = None
    page_count: int | None = None
    status: DocumentStatus | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


class DocumentWithChunks(Document):
    """Document model including its chunks"""

    chunks: list[DocumentChunk] = Field(
        default_factory=list, description="Document chunks"
    )
