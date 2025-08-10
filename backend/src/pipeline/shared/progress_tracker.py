"""Progress tracking system with comprehensive async operations."""

import asyncio
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from src.models import StepResult

from src.middleware.request_id import get_request_id
from src.utils.logging import get_logger

# Configure logging
logger = get_logger(__name__)


class ProgressTracker:
    """Progress tracker with comprehensive async operations"""

    def __init__(self, indexing_run_id: UUID, db=None):
        self.run_id = indexing_run_id
        self.db = db
        self.total_steps = 6  # partition, metadata, enrich, chunk, embed, store
        self.completed_steps = 0
        # Bind context for all tracker logs
        self._logger = logger.bind(
            run_id=str(indexing_run_id),
            pipeline_type="indexing",
            request_id=get_request_id(),
        )

    async def update_step_progress_async(
        self, step: str, status: str, result: StepResult
    ):
        """Update progress in database and logs with async operations"""
        # Only update indexing run for batch operations (like embedding)
        # Individual document steps should only be stored in document.step_results
        if self._is_batch_operation(step):
            await self.update_run_status_async(step, status, result)

        # Async structured logging
        await self.log_progress_async(step, status, result)

        # Update completion count
        self.completed_steps += 1

    def _is_batch_operation(self, step: str) -> bool:
        """Determine if a step is a batch operation that affects all documents"""
        batch_operations = [
            "EmbeddingStep",
            "embedding",
            "batch_embedding",
            "batch_embed_all_chunks",
        ]
        return step in batch_operations

    async def update_run_status_async(self, step: str, status: str, result: StepResult):
        """Async database update for run status - ONLY for batch operations"""
        if not self.db:
            return

        try:
            # Get current step_results from database
            current_result = (
                self.db.table("indexing_runs")
                .select("step_results")
                .eq("id", str(self.run_id))
                .execute()
            )

            if not current_result.data:
                print(f"❌ Indexing run {self.run_id} not found for step update")
                return

            current_step_results = current_result.data[0].get("step_results", {})

            # Add the new step result
            current_step_results[step] = {
                "step": step,  # Add the required step field
                "status": status,
                "duration_seconds": result.duration_seconds,
                "summary_stats": result.summary_stats,
                "completed_at": (
                    result.completed_at.isoformat() if result.completed_at else None
                ),
                "error_message": (
                    result.error_message if hasattr(result, "error_message") else None
                ),
            }

            # Update the step_results field
            update_result = (
                self.db.table("indexing_runs")
                .update({"step_results": current_step_results})
                .eq("id", str(self.run_id))
                .execute()
            )

            if not update_result.data:
                print(f"❌ Failed to update step results for run {self.run_id}")
                return

            print(f"✅ Updated batch step results for {step} in run {self.run_id}")

        except Exception as e:
            print(f"❌ Failed to update run status: {e}")

    async def log_progress_async(self, step: str, status: str, result: StepResult):
        """Async structured logging for progress updates"""
        try:
            log_data = {
                "run_id": str(self.run_id),
                "step": step,
                "status": status,
                "completed_steps": self.completed_steps,
                "total_steps": self.total_steps,
                "duration_seconds": result.duration_seconds,
                "summary_stats": result.summary_stats,
            }

            if status == "completed":
                self._logger.info(
                    "Step completed",
                    step=step,
                    duration_seconds=result.duration_seconds,
                )
            elif status == "failed":
                self._logger.error(
                    "Step failed",
                    step=step,
                    error_message=(
                        result.error_message
                        if hasattr(result, "error_message")
                        else "Unknown error"
                    ),
                )
            else:
                self._logger.info("Step status update", step=step, status=status)

        except Exception as e:
            print(f"❌ Failed to log progress: {e}")

    async def mark_pipeline_failed_async(self, error_message: str):
        """Async failure marking"""
        if not self.db:
            return

        try:
            # Update indexing_runs table to mark as failed
            update_result = (
                self.db.table("indexing_runs")
                .update(
                    {
                        "status": "failed",
                        "error_message": error_message,
                        "completed_at": datetime.utcnow().isoformat(),
                    }
                )
                .eq("id", str(self.run_id))
                .execute()
            )

            if not update_result.data:
                print(f"❌ Failed to mark pipeline as failed for run {self.run_id}")
                return

            self._logger.error("Pipeline marked failed", error_message=error_message)

        except Exception as e:
            print(f"❌ Failed to mark pipeline as failed: {e}")

    async def get_progress_summary_async(self) -> Dict[str, Any]:
        """Get current progress summary"""
        return {
            "run_id": str(self.run_id),
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "progress_percentage": (self.completed_steps / self.total_steps) * 100,
            "estimated_remaining_time": self.estimate_remaining_time(),
        }

    def estimate_remaining_time(self) -> Optional[int]:
        """Estimate remaining time in seconds"""
        if self.completed_steps == 0:
            return None

        # Simple estimation based on completed steps
        # In a real implementation, this would use actual step durations
        avg_time_per_step = 60  # 1 minute per step
        remaining_steps = self.total_steps - self.completed_steps
        return remaining_steps * avg_time_per_step


class QueryProgressTracker:
    """Progress tracker for query pipeline (simpler, real-time focused)"""

    def __init__(self, query_run_id: UUID, db=None):
        self.run_id = query_run_id
        self.db = db
        self.start_time = datetime.utcnow()

    async def log_query_start_async(self, query_text: str):
        """Log query start"""
        try:
            logger.info(
                "Query started",
                extra={
                    "run_id": str(self.run_id),
                    "query_text": (
                        query_text[:100] + "..."
                        if len(query_text) > 100
                        else query_text
                    ),
                },
            )
        except Exception as e:
            logger.error(f"Failed to log query start: {e}")

    async def log_query_completion_async(self, response_time_ms: int, success: bool):
        """Log query completion"""
        try:
            log_data = {
                "run_id": str(self.run_id),
                "response_time_ms": response_time_ms,
                "success": success,
            }

            if success:
                logger.info("Query completed successfully", extra=log_data)
            else:
                logger.error("Query failed", extra=log_data)

        except Exception as e:
            logger.error(f"Failed to log query completion: {e}")

    async def update_query_run_async(
        self,
        response_text: str = None,
        retrieval_metadata: Dict[str, Any] = None,
        response_time_ms: int = None,
    ):
        """Update query run in database"""
        if not self.db:
            return

        try:
            # Update query_runs table
            # await self.db.execute(
            #     "UPDATE query_runs SET response_text = $1, retrieval_metadata = $2, response_time_ms = $3 WHERE id = $4",
            #     response_text, retrieval_metadata, response_time_ms, self.run_id
            # )

            # Placeholder for actual implementation
            logger.info(f"Updated query run {self.run_id}")

        except Exception as e:
            logger.error(f"Failed to update query run: {e}")
