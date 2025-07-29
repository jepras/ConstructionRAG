"""Pipeline service for database operations related to pipeline steps."""

import asyncio
import json
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
import logging

from src.config.database import get_supabase_client
from src.models.pipeline import (
    StepResult,
    IndexingRun,
    IndexingRunCreate,
    IndexingRunUpdate,
)
from src.utils.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class PipelineService:
    """Service for managing pipeline operations in the database."""

    def __init__(self):
        self.supabase = get_supabase_client()

    async def create_indexing_run(
        self, document_id: UUID, user_id: UUID
    ) -> IndexingRun:
        """Create a new indexing run for a document."""
        try:
            indexing_run_data = IndexingRunCreate(
                document_id=document_id, status="pending"
            )

            # Convert UUIDs to strings for JSON serialization
            data_dict = indexing_run_data.model_dump()
            data_dict["document_id"] = str(data_dict["document_id"])

            result = self.supabase.table("indexing_runs").insert(data_dict).execute()

            if not result.data:
                raise DatabaseError("Failed to create indexing run")

            return IndexingRun(**result.data[0])

        except Exception as e:
            logger.error(f"Error creating indexing run: {e}")
            raise DatabaseError(f"Failed to create indexing run: {str(e)}")

    async def update_indexing_run_status(
        self, indexing_run_id: UUID, status: str, error_message: Optional[str] = None
    ) -> IndexingRun:
        """Update the status of an indexing run."""
        try:
            update_data = IndexingRunUpdate(
                status=status,
                error_message=error_message,
                completed_at=(
                    datetime.utcnow() if status in ["completed", "failed"] else None
                ),
            )

            # Convert UUIDs to strings for JSON serialization
            data_dict = update_data.model_dump(exclude_unset=True)

            result = (
                self.supabase.table("indexing_runs")
                .update(data_dict)
                .eq("id", str(indexing_run_id))
                .execute()
            )

            if not result.data:
                raise DatabaseError("Failed to update indexing run")

            return IndexingRun(**result.data[0])

        except Exception as e:
            logger.error(f"Error updating indexing run status: {e}")
            raise DatabaseError(f"Failed to update indexing run status: {str(e)}")

    async def store_step_result(
        self, indexing_run_id: UUID, step_name: str, step_result: StepResult
    ) -> bool:
        """Store a step result in the indexing run's step_results JSONB field."""
        try:
            # First, get the current step_results
            result = (
                self.supabase.table("indexing_runs")
                .select("step_results")
                .eq("id", str(indexing_run_id))
                .execute()
            )

            if not result.data:
                raise DatabaseError("Indexing run not found")

            current_step_results = result.data[0].get("step_results", {})

            # Add the new step result
            current_step_results[step_name] = step_result.model_dump()

            # Update the step_results field
            update_result = (
                self.supabase.table("indexing_runs")
                .update({"step_results": current_step_results})
                .eq("id", str(indexing_run_id))
                .execute()
            )

            if not update_result.data:
                raise DatabaseError("Failed to store step result")

            logger.info(
                f"Stored step result for {step_name} in indexing run {indexing_run_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error storing step result: {e}")
            raise DatabaseError(f"Failed to store step result: {str(e)}")

    async def get_step_result(
        self, indexing_run_id: UUID, step_name: str
    ) -> Optional[StepResult]:
        """Get a specific step result from an indexing run."""
        try:
            result = (
                self.supabase.table("indexing_runs")
                .select("step_results")
                .eq("id", str(indexing_run_id))
                .execute()
            )

            if not result.data:
                return None

            step_results = result.data[0].get("step_results", {})
            step_data = step_results.get(step_name)

            if not step_data:
                return None

            return StepResult(**step_data)

        except Exception as e:
            logger.error(f"Error getting step result: {e}")
            raise DatabaseError(f"Failed to get step result: {str(e)}")

    async def get_indexing_run(self, indexing_run_id: UUID) -> Optional[IndexingRun]:
        """Get a complete indexing run with all step results."""
        try:
            result = (
                self.supabase.table("indexing_runs")
                .select("*")
                .eq("id", str(indexing_run_id))
                .execute()
            )

            if not result.data:
                return None

            return IndexingRun(**result.data[0])

        except Exception as e:
            logger.error(f"Error getting indexing run: {e}")
            raise DatabaseError(f"Failed to get indexing run: {str(e)}")

    async def get_document_indexing_runs(self, document_id: UUID) -> List[IndexingRun]:
        """Get all indexing runs for a document."""
        try:
            result = (
                self.supabase.table("indexing_runs")
                .select("*")
                .eq("document_id", str(document_id))
                .order("started_at", desc=True)
                .execute()
            )

            return [IndexingRun(**run) for run in result.data]

        except Exception as e:
            logger.error(f"Error getting document indexing runs: {e}")
            raise DatabaseError(f"Failed to get document indexing runs: {str(e)}")

    async def get_latest_successful_indexing_run(
        self, document_id: UUID
    ) -> Optional[IndexingRun]:
        """Get the latest successful indexing run for a document."""
        try:
            result = (
                self.supabase.table("indexing_runs")
                .select("*")
                .eq("document_id", str(document_id))
                .eq("status", "completed")
                .order("started_at", desc=True)
                .limit(1)
                .execute()
            )

            if not result.data:
                return None

            return IndexingRun(**result.data[0])

        except Exception as e:
            logger.error(f"Error getting latest successful indexing run: {e}")
            raise DatabaseError(
                f"Failed to get latest successful indexing run: {str(e)}"
            )
