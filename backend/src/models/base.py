from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AccessLevel(str, Enum):
    """Access control levels for resources.

    Semantics align with API redesign plan:
    - public: accessible to anyone (anonymous or authenticated)
    - auth: accessible to any authenticated user
    - owner: reserved for owner-only semantics (used primarily for policies)
    - private: accessible only to the resource owner (and explicit shares, future)
    """

    PUBLIC = "public"
    AUTH = "auth"
    OWNER = "owner"
    PRIVATE = "private"


class BaseDocument(BaseModel):
    """Shared fields for document-like models.

    Keep validation minimal in Phase 2 to avoid regressions; business rules
    (like filetype checks) live in services.
    """

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    filename: str = Field(..., min_length=1, description="Original filename")
    file_size: int | None = Field(None, ge=0, description="File size in bytes")
    file_path: str | None = Field(None, description="Supabase Storage path")
    page_count: int | None = Field(None, ge=1, description="Number of pages in PDF")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class BaseDocumentChunk(BaseModel):
    """Shared fields for document chunks without DB-only fields."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    document_id: UUID = Field(..., description="Parent document ID")
    chunk_index: int = Field(..., description="Chunk index within document")
    content: str = Field(..., description="Chunk text content")
    embedding: list[float] | None = Field(None, description="Vector embedding")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    page_number: int | None = Field(None, description="Source page number")
    section_title: str | None = Field(None, description="Section title if available")
