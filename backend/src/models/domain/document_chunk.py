from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from ..base import BaseDocumentChunk


class DocumentChunk(BaseDocumentChunk):
    """Document chunk model matching the document_chunks table."""

    id: UUID = Field(description="Chunk unique identifier")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Chunk creation timestamp"
    )

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkCreate(BaseDocumentChunk):
    """Model for creating a new document chunk"""

    model_config = ConfigDict(extra="forbid")
