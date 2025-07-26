from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Document metadata"""

    filename: str
    file_size: int
    page_count: Optional[int] = None
    document_type: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    status: str = "pending"  # pending, processing, completed, failed
    error_message: Optional[str] = None


class DocumentChunk(BaseModel):
    """Document chunk for vector storage"""

    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    chunk_index: int
    page_number: Optional[int] = None
    source_document: str


class Document(BaseModel):
    """Document model"""

    id: str
    user_id: str
    metadata: DocumentMetadata
    chunks: List[DocumentChunk] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentUploadResponse(BaseModel):
    """Response for document upload"""

    document_id: str
    status: str
    message: str
    processing_job_id: Optional[str] = None
