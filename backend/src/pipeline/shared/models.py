"""Shared pipeline models and data structures."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from pathlib import Path


class DocumentInput(BaseModel):
    """Input data for document processing steps"""

    document_id: UUID = Field(description="Document unique identifier")
    file_path: str = Field(description="Path to the document file")
    filename: str = Field(description="Original filename")
    user_id: UUID = Field(description="User who uploaded the document")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional document metadata"
    )


class PipelineError(Exception):
    """Custom exception for pipeline errors"""

    def __init__(
        self,
        message: str,
        step: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.step = step
        self.details = details or {}
        super().__init__(self.message)


class ProcessingResult(BaseModel):
    """Generic result from any processing step"""

    success: bool = Field(description="Whether processing was successful")
    data: Optional[Any] = Field(None, description="Processed data")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Processing metadata"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")


class StepInput(BaseModel):
    """Input data for any pipeline step"""

    step_name: str = Field(description="Name of the step")
    input_data: Any = Field(description="Input data for the step")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Step-specific configuration"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Context data from previous steps"
    )


class StepOutput(BaseModel):
    """Output data from any pipeline step"""

    step_name: str = Field(description="Name of the step")
    output_data: Any = Field(description="Output data from the step")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Step metadata and statistics"
    )
    context_updates: Dict[str, Any] = Field(
        default_factory=dict, description="Context updates for next steps"
    )
