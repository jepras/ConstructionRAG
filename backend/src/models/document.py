from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum


class DocumentStatus(str, Enum):
    """Document processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(BaseModel):
    """Document model matching the documents table"""

    id: UUID = Field(description="Document unique identifier")
    user_id: UUID = Field(description="Owner user ID from Supabase Auth")
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
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Document creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Document last update timestamp"
    )

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
