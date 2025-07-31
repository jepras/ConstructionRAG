"""Pipeline system for the two-pipeline architecture."""

from .shared import (
    PipelineStep,
    StepResult,
    ProgressTracker,
    ConfigManager,
    DocumentInput,
    PipelineError,
)

from .indexing import IndexingOrchestrator
from .querying import QueryPipelineOrchestrator

__all__ = [
    # Shared components
    "PipelineStep",
    "StepResult",
    "ProgressTracker",
    "ConfigManager",
    "DocumentInput",
    "PipelineError",
    # Pipeline orchestrators
    "IndexingOrchestrator",
    "QueryPipelineOrchestrator",
]
