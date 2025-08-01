"""Shared pipeline models and data structures."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from pathlib import Path
from enum import Enum


class UploadType(str, Enum):
    """Type of upload - email-based or user project."""

    EMAIL = "email"
    USER_PROJECT = "user_project"


class DocumentInput(BaseModel):
    """Input data for document processing steps"""

    document_id: UUID = Field(description="Document unique identifier")
    run_id: UUID = Field(description="Pipeline run unique identifier")
    file_path: str = Field(description="Path to the document file")
    filename: str = Field(description="Original filename")
    user_id: UUID = Field(description="User who uploaded the document")
    upload_type: UploadType = Field(description="Type of upload")
    upload_id: Optional[str] = Field(None, description="Upload ID for email uploads")
    project_id: Optional[UUID] = Field(None, description="Project ID for user projects")
    index_run_id: Optional[UUID] = Field(
        None, description="Index run ID for user projects"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional document metadata"
    )


class PipelineError(Exception):
    """Custom exception for pipeline errors"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ProcessingResult(BaseModel):
    """Result of a processing operation"""

    success: bool = Field(description="Whether the operation was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Processing result data")
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
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Step metadata")
    success: bool = Field(description="Whether the step was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")
