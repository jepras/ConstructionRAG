"""Abstract base class for pipeline steps with functional implementation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel
import time
import asyncio
from ...models import StepResult
from .models import DocumentInput, PipelineError


class PipelineStep(ABC):
    """Abstract base class for pipeline steps with functional implementation"""

    def __init__(self, config: Dict[str, Any], tracker=None):
        self.config = config
        self.tracker = tracker

    @abstractmethod
    async def execute(self, input_data: Any) -> StepResult:
        """
        Execute the pipeline step with given input data.

        This method should be implemented as a pure function with:
        - No side effects beyond the return value
        - Explicit dependencies passed as parameters
        - All I/O operations handled asynchronously
        """
        pass

    @abstractmethod
    async def validate_prerequisites_async(self, input_data: Any) -> bool:
        """Validate that input data meets step requirements (async)"""
        pass

    @abstractmethod
    def estimate_duration(self, input_data: Any) -> int:
        """Estimate step duration in seconds"""
        pass

    def get_step_name(self) -> str:
        """Return human-readable step name"""
        return self.__class__.__name__


class StepExecutor:
    """Helper class for executing steps with error handling and progress tracking"""

    def __init__(self, step: PipelineStep, progress_tracker=None):
        self.step = step
        self.progress_tracker = progress_tracker

    async def execute_with_tracking(self, input_data: Any) -> StepResult:
        """Execute step with comprehensive error handling and progress tracking"""
        start_time = time.time()
        step_name = self.step.get_step_name()

        try:
            # Validate prerequisites
            if not await self.step.validate_prerequisites_async(input_data):
                raise PipelineError(
                    f"Prerequisites not met for {step_name}", step=step_name
                )

            # Execute step
            result = await self.step.execute(input_data)

            # Update timestamps
            result.completed_at = time.time()
            result.duration_seconds = result.completed_at - start_time

            # Update progress if tracker available
            if self.progress_tracker:
                await self.progress_tracker.update_step_progress_async(
                    step_name, "completed", result
                )

            return result

        except Exception as e:
            # Create error result
            error_result = StepResult(
                step=step_name,
                status="failed",
                duration_seconds=time.time() - start_time,
                error_message=str(e),
                error_details={"exception_type": type(e).__name__, "step": step_name},
                completed_at=time.time(),
            )

            # Update progress if tracker available
            if self.progress_tracker:
                await self.progress_tracker.update_step_progress_async(
                    step_name, "failed", error_result
                )

            return error_result


# Example implementation showing functional approach
class ExamplePartitionStep(PipelineStep):
    """Example implementation of partition step showing functional approach"""

    async def execute(self, input_data: DocumentInput) -> StepResult:
        """
        Pure function implementation of partition step.

        All dependencies are explicit, no side effects beyond return value.
        """
        start_time = time.time()

        try:
            # Pure function call with explicit dependencies
            # elements = await partition_document_pure(
            #     file_path=input_data.file_path,
            #     config=self.config,
            #     storage_client=self.storage_client  # Explicit dependency
            # )

            # Placeholder for actual implementation
            elements = []  # This would be the actual partitioned elements

            duration = time.time() - start_time

            return StepResult(
                step="partition",
                status="completed",
                duration_seconds=duration,
                summary_stats={
                    "total_elements": len(elements),
                    "text_elements": len(
                        [e for e in elements if hasattr(e, "type") and e.type == "text"]
                    ),
                    "table_elements": len(
                        [
                            e
                            for e in elements
                            if hasattr(e, "type") and e.type == "table"
                        ]
                    ),
                    "image_elements": len(
                        [
                            e
                            for e in elements
                            if hasattr(e, "type") and e.type == "image"
                        ]
                    ),
                },
                sample_outputs={
                    "sample_elements": [str(e)[:200] + "..." for e in elements[:3]]
                },
            )

        except Exception as e:
            return StepResult(
                step="partition",
                status="failed",
                duration_seconds=time.time() - start_time,
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
            )

    async def validate_prerequisites_async(self, input_data: DocumentInput) -> bool:
        """Validate partition step prerequisites"""
        # Check if file exists and is accessible
        import os

        return os.path.exists(input_data.file_path)

    def estimate_duration(self, input_data: DocumentInput) -> int:
        """Estimate partition step duration"""
        # Simple estimation based on file size
        try:
            import os

            file_size_mb = os.path.getsize(input_data.file_path) / (1024 * 1024)
            return int(file_size_mb * 10)  # 10 seconds per MB
        except:
            return 60  # Default 1 minute
