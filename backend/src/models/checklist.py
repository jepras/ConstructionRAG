"""Pydantic models for checklist analysis feature."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChecklistStatus(str, Enum):
    """Status of individual checklist items."""
    FOUND = "found"
    MISSING = "missing"
    RISK = "risk"
    CONDITIONS = "conditions"
    PENDING_CLARIFICATION = "pending_clarification"


class AnalysisStatus(str, Enum):
    """Status of checklist analysis run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ChecklistAnalysisRequest(BaseModel):
    """Request model for creating checklist analysis."""
    indexing_run_id: str = Field(..., description="ID of the indexing run to analyze")
    checklist_content: str = Field(..., description="The checklist content to analyze against")
    checklist_name: str = Field(..., description="Name of the checklist")
    model_name: str = Field(
        default="google/gemini-2.0-flash-experimental",
        description="LLM model to use for analysis"
    )


class ChecklistResult(BaseModel):
    """Individual checklist item result."""
    id: UUID
    item_number: str = Field(..., description="Item number in checklist (e.g., '1.1')")
    item_name: str = Field(..., description="Name of the checklist item")
    status: ChecklistStatus = Field(..., description="Status of the item")
    description: str = Field(..., description="Detailed findings for this item")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Confidence score (0-1)")
    source_document: Optional[str] = Field(None, description="Source document name")
    source_page: Optional[int] = Field(None, description="Page number in source")
    source_chunk_id: Optional[UUID] = Field(None, description="ID of source chunk")
    source_excerpt: Optional[str] = Field(None, description="Relevant text excerpt")
    all_sources: Optional[List[Dict[str, Any]]] = Field(None, description="All sources supporting this finding")
    created_at: Optional[datetime] = None


class ChecklistAnalysisRun(BaseModel):
    """Checklist analysis run model."""
    id: UUID
    indexing_run_id: UUID
    user_id: Optional[UUID] = None
    checklist_name: str
    checklist_content: str
    model_name: str
    status: AnalysisStatus
    raw_output: Optional[str] = None
    progress_current: int = 0
    progress_total: int = 4
    error_message: Optional[str] = None
    access_level: str = "private"
    results: Optional[list[ChecklistResult]] = None
    created_at: datetime
    updated_at: datetime


class ChecklistAnalysisResponse(BaseModel):
    """Response model for checklist analysis creation."""
    analysis_run_id: UUID
    status: str
    message: str


class ChecklistTemplate(BaseModel):
    """Checklist template model for future use."""
    id: UUID
    user_id: Optional[UUID] = None
    name: str
    content: str
    category: str = "custom"
    is_public: bool = False
    access_level: str = "private"
    created_at: datetime
    updated_at: datetime