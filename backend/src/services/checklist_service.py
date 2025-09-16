"""Service layer for checklist analysis functionality."""

import logging
from typing import Optional
from uuid import UUID

from src.config.database import get_supabase_admin_client
from src.models.checklist import (
    AnalysisStatus,
    ChecklistAnalysisRun,
    ChecklistResult,
)
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError

logger = logging.getLogger(__name__)


class ChecklistService:
    """Service for managing checklist analysis operations."""

    def __init__(self, db_client=None):
        self.supabase = db_client or get_supabase_admin_client()

    async def create_analysis_run(
        self,
        indexing_run_id: str,
        checklist_content: str,
        checklist_name: str,
        model_name: str,
        user_id: Optional[str] = None,
    ) -> ChecklistAnalysisRun:
        """Create a new checklist analysis run."""
        try:
            # Fetch access level from indexing run
            indexing_run_result = (
                self.supabase.table("indexing_runs")
                .select("access_level")
                .eq("id", indexing_run_id)
                .execute()
            )

            if not indexing_run_result.data:
                raise AppError(
                    f"Indexing run {indexing_run_id} not found",
                    error_code=ErrorCode.NOT_FOUND,
                )

            access_level = indexing_run_result.data[0]["access_level"]

            # Create analysis run
            result = (
                self.supabase.table("checklist_analysis_runs")
                .insert(
                    {
                        "indexing_run_id": indexing_run_id,
                        "user_id": user_id,
                        "checklist_name": checklist_name,
                        "checklist_content": checklist_content,
                        "model_name": model_name,
                        "status": AnalysisStatus.PENDING.value,
                        "access_level": access_level,
                        "progress_current": 0,
                        "progress_total": 4,
                    }
                )
                .execute()
            )

            if not result.data:
                raise AppError(
                    "Failed to create analysis run",
                    error_code=ErrorCode.INTERNAL_ERROR,
                )

            return ChecklistAnalysisRun(**result.data[0])

        except Exception as e:
            logger.error(f"Error creating analysis run: {e}")
            raise

    async def get_analysis_run_by_id(
        self, analysis_run_id: str
    ) -> Optional[ChecklistAnalysisRun]:
        """Get analysis run by ID."""
        try:
            result = (
                self.supabase.table("checklist_analysis_runs")
                .select("*")
                .eq("id", analysis_run_id)
                .execute()
            )

            if not result.data:
                return None

            return ChecklistAnalysisRun(**result.data[0])

        except Exception as e:
            logger.error(f"Error fetching analysis run: {e}")
            raise

    async def get_analysis_run_with_results(
        self, run_id: str
    ) -> Optional[ChecklistAnalysisRun]:
        """Get analysis run with its results."""
        try:
            # Get analysis run
            run_result = (
                self.supabase.table("checklist_analysis_runs")
                .select("*")
                .eq("id", run_id)
                .execute()
            )

            if not run_result.data:
                return None

            analysis_run = ChecklistAnalysisRun(**run_result.data[0])

            # Get results if completed
            if analysis_run.status == AnalysisStatus.COMPLETED:
                results_result = (
                    self.supabase.table("checklist_results")
                    .select("*")
                    .eq("analysis_run_id", run_id)
                    .order("item_number")
                    .execute()
                )

                # Parse all_sources JSON field for each result
                parsed_results = []
                for result in results_result.data:
                    # Parse all_sources from JSON string if present
                    if result.get("all_sources"):
                        try:
                            import json
                            result["all_sources"] = json.loads(result["all_sources"])
                        except (json.JSONDecodeError, TypeError):
                            result["all_sources"] = None
                    parsed_results.append(ChecklistResult(**result))
                
                analysis_run.results = parsed_results

            return analysis_run

        except Exception as e:
            logger.error(f"Error fetching analysis run with results: {e}")
            raise

    async def list_analysis_runs_for_user(
        self,
        user_id: Optional[str] = None,
        indexing_run_id: Optional[str] = None,
    ) -> list[ChecklistAnalysisRun]:
        """List analysis runs for a user or indexing run."""
        try:
            query = self.supabase.table("checklist_analysis_runs").select("*")

            if indexing_run_id:
                query = query.eq("indexing_run_id", indexing_run_id)

            # Note: RLS policies will automatically filter based on user access
            result = query.order("created_at", desc=True).execute()

            return [ChecklistAnalysisRun(**run) for run in result.data]

        except Exception as e:
            logger.error(f"Error listing analysis runs: {e}")
            raise

    async def store_checklist_results(
        self, analysis_run_id: str, structured_results: list[dict]
    ):
        """Store structured results in database."""
        try:
            # Convert structured results to database format
            db_results = []
            for result in structured_results:
                # Store all_sources as JSON for multi-source support
                all_sources_json = None
                if result.get("all_sources"):
                    import json
                    all_sources_json = json.dumps(result["all_sources"])
                
                db_results.append(
                    {
                        "analysis_run_id": analysis_run_id,
                        "item_number": result.get("item_number", ""),
                        "item_name": result.get("item_name", ""),
                        "status": result.get("status", "missing"),
                        "description": result.get("description", ""),
                        "confidence_score": result.get("confidence_score"),
                        "source_document": result.get("source_document"),
                        "source_page": result.get("source_page"),
                        "source_excerpt": result.get("source_excerpt"),
                        "all_sources": all_sources_json,  # Add multi-source support
                    }
                )

            # Batch insert results
            if db_results:
                self.supabase.table("checklist_results").insert(db_results).execute()

            logger.info(
                f"Stored {len(db_results)} results for analysis {analysis_run_id}"
            )

        except Exception as e:
            logger.error(f"Error storing checklist results: {e}")
            raise

    async def update_progress(
        self, analysis_run_id: str, current: int, total: int
    ):
        """Update analysis progress."""
        try:
            self.supabase.table("checklist_analysis_runs").update(
                {
                    "progress_current": current,
                    "progress_total": total,
                    "updated_at": "NOW()",
                }
            ).eq("id", analysis_run_id).execute()

        except Exception as e:
            logger.error(f"Error updating progress: {e}")
            raise

    async def update_analysis_status(
        self, analysis_run_id: str, status: AnalysisStatus
    ):
        """Update analysis status."""
        try:
            self.supabase.table("checklist_analysis_runs").update(
                {"status": status.value, "updated_at": "NOW()"}
            ).eq("id", analysis_run_id).execute()

            logger.info(f"Updated analysis {analysis_run_id} status to {status.value}")

        except Exception as e:
            logger.error(f"Error updating analysis status: {e}")
            raise

    async def update_analysis_raw_output(
        self, analysis_run_id: str, raw_output: str
    ):
        """Store raw analysis output."""
        try:
            self.supabase.table("checklist_analysis_runs").update(
                {"raw_output": raw_output, "updated_at": "NOW()"}
            ).eq("id", analysis_run_id).execute()

        except Exception as e:
            logger.error(f"Error updating raw output: {e}")
            raise

    async def update_analysis_error(
        self, analysis_run_id: str, error_message: str
    ):
        """Update analysis with error message."""
        try:
            self.supabase.table("checklist_analysis_runs").update(
                {"error_message": error_message, "updated_at": "NOW()"}
            ).eq("id", analysis_run_id).execute()

        except Exception as e:
            logger.error(f"Error updating error message: {e}")
            raise

    async def delete_analysis_run_by_id(
        self, run_id: str, user_id: str
    ):
        """Delete an analysis run."""
        try:
            # Check if user owns the run
            run_result = (
                self.supabase.table("checklist_analysis_runs")
                .select("user_id")
                .eq("id", run_id)
                .execute()
            )

            if not run_result.data:
                raise AppError(
                    "Analysis run not found",
                    error_code=ErrorCode.NOT_FOUND,
                )

            if run_result.data[0]["user_id"] != user_id:
                raise AppError(
                    "You don't have permission to delete this analysis",
                    error_code=ErrorCode.FORBIDDEN,
                )

            # Delete the run (results will cascade delete)
            self.supabase.table("checklist_analysis_runs").delete().eq(
                "id", run_id
            ).execute()

            logger.info(f"Deleted analysis run {run_id}")

        except Exception as e:
            logger.error(f"Error deleting analysis run: {e}")
            raise

    async def validate_indexing_run_access(
        self, indexing_run_id: str, user
    ):
        """Validate user has access to indexing run."""
        try:
            # Fetch indexing run with access level
            result = (
                self.supabase.table("indexing_runs")
                .select("id, access_level, user_id")
                .eq("id", indexing_run_id)
                .execute()
            )

            if not result.data:
                raise AppError(
                    f"Indexing run {indexing_run_id} not found",
                    error_code=ErrorCode.NOT_FOUND,
                )

            indexing_run = result.data[0]
            access_level = indexing_run["access_level"]

            # Check access based on level
            if access_level == "public":
                return True
            elif access_level == "auth" and user:
                return True
            elif access_level == "private" and user and indexing_run["user_id"] == str(user.id):
                return True
            else:
                raise AppError(
                    "You don't have access to this indexing run",
                    error_code=ErrorCode.FORBIDDEN,
                )

        except Exception as e:
            logger.error(f"Error validating access: {e}")
            raise

    async def get_language_from_indexing_run(self, indexing_run_id: str) -> str:
        """Fetch language from indexing run's stored pipeline_config."""
        try:
            result = (
                self.supabase.table("indexing_runs")
                .select("pipeline_config")
                .eq("id", indexing_run_id)
                .execute()
            )

            if result.data and result.data[0].get("pipeline_config"):
                pipeline_config = result.data[0]["pipeline_config"]
                language = pipeline_config.get("defaults", {}).get(
                    "language", "english"
                )
                logger.info(f"Found language '{language}' for indexing run {indexing_run_id}")
                return language

            logger.info(f"No language found, defaulting to 'english'")
            return "english"

        except Exception as e:
            logger.error(f"Error fetching language: {e}")
            return "english"  # fallback