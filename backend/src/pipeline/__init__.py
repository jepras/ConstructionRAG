"""Pipeline system for the two-pipeline architecture."""

from .shared import (
    PipelineStep,
    StepResult,
    ProgressTracker,
    ConfigManager,
    DocumentInput,
    PipelineError,
)

# Conditional imports - indexing only available on Beam
try:
    from .indexing import IndexingOrchestrator
    INDEXING_AVAILABLE = True
except ImportError:
    IndexingOrchestrator = None
    INDEXING_AVAILABLE = False

from .querying import QueryPipelineOrchestrator

__all__ = [
    # Shared components
    "PipelineStep",
    "StepResult",
    "ProgressTracker",
    "ConfigManager",
    "DocumentInput",
    "PipelineError",
    # Pipeline orchestrators (IndexingOrchestrator only available on Beam)
    "QueryPipelineOrchestrator",
]

# Add IndexingOrchestrator to __all__ only if available
if INDEXING_AVAILABLE:
    __all__.append("IndexingOrchestrator")
