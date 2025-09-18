"""Service layer for checklist analysis functionality."""

import logging
from typing import Optional
from uuid import UUID

from src.config.database import get_supabase_admin_client
from src.models.checklist import (
    AnalysisStatus,
    ChecklistAnalysisRun,
    ChecklistResult,
    ChecklistTemplate,
    ChecklistTemplateRequest,
    ChecklistTemplateResponse,
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
        """List analysis runs for a user or indexing run.
        
        For public projects: returns all analysis runs
        For auth projects: returns all analysis runs if user is authenticated
        For private projects: returns only the user's own analysis runs
        """
        try:
            if indexing_run_id:
                # First, check the access level of the indexing run
                indexing_result = (
                    self.supabase.table("indexing_runs")
                    .select("access_level, user_id")
                    .eq("id", indexing_run_id)
                    .execute()
                )
                
                if not indexing_result.data:
                    return []
                
                access_level = indexing_result.data[0]["access_level"]
                indexing_run_owner = indexing_result.data[0]["user_id"]
                
                # Build query based on access level
                query = self.supabase.table("checklist_analysis_runs").select("*")
                query = query.eq("indexing_run_id", indexing_run_id)
                
                if access_level == "public":
                    # For public projects, return all analysis runs
                    pass  # No additional filtering needed
                elif access_level == "auth" and user_id:
                    # For auth projects, return all runs if user is authenticated
                    pass  # No additional filtering needed
                elif access_level == "private" and user_id == indexing_run_owner:
                    # For private projects, only owner can see runs
                    pass  # No additional filtering needed
                else:
                    # No access - return empty list
                    return []
                
                result = query.order("created_at", desc=True).execute()
                return [ChecklistAnalysisRun(**run) for run in result.data]
            
            # If no indexing_run_id specified, return user's runs only
            if user_id:
                query = self.supabase.table("checklist_analysis_runs").select("*")
                query = query.eq("user_id", user_id)
                result = query.order("created_at", desc=True).execute()
                return [ChecklistAnalysisRun(**run) for run in result.data]
            
            return []

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
            elif access_level == "private" and user and indexing_run["user_id"] == str(user["id"]):
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

    # Template Management Methods

    async def create_template(
        self,
        request: ChecklistTemplateRequest,
        user_id: Optional[str] = None,
    ) -> ChecklistTemplateResponse:
        """Create a new checklist template.
        
        For anonymous users: Creates public template with user_id=null
        For authenticated users: Can create public or private templates
        """
        try:
            # For anonymous users, always create public templates
            if not user_id:
                is_public = True
                access_level = "public"
            else:
                is_public = request.is_public
                access_level = "public" if is_public else "private"

            result = (
                self.supabase.table("checklist_templates")
                .insert(
                    {
                        "user_id": user_id,
                        "name": request.name,
                        "content": request.content,
                        "category": request.category,
                        "is_public": is_public,
                        "access_level": access_level,
                    }
                )
                .execute()
            )

            if not result.data:
                raise AppError(
                    "Failed to create template",
                    error_code=ErrorCode.INTERNAL_ERROR,
                )

            template = result.data[0]
            return ChecklistTemplateResponse(
                **template,
                is_owner=True  # Creator is always the owner
            )

        except Exception as e:
            logger.error(f"Error creating template: {e}")
            raise

    async def list_templates_for_user(
        self, user_id: Optional[str] = None
    ) -> list[ChecklistTemplateResponse]:
        """List templates available to a user.
        
        For authenticated users: Returns only templates they created (both public and private).
        For anonymous users: Returns only public templates.
        """
        try:
            templates = []
            
            if user_id:
                # For authenticated users: show only their own templates (both public and private)
                user_query = (
                    self.supabase.table("checklist_templates")
                    .select("*")
                    .eq("user_id", user_id)
                )
                user_result = user_query.execute()
                
                for template in user_result.data:
                    templates.append(ChecklistTemplateResponse(
                        **template,
                        is_owner=True
                    ))
            else:
                # For anonymous users: show only public templates
                public_query = (
                    self.supabase.table("checklist_templates")
                    .select("*")
                    .eq("is_public", True)
                )
                public_result = public_query.execute()
                
                for template in public_result.data:
                    templates.append(ChecklistTemplateResponse(
                        **template,
                        is_owner=False
                    ))
            
            # Sort by created_at descending
            templates.sort(key=lambda x: x.created_at, reverse=True)
            return templates

        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            # For table not found or similar database issues, return empty list
            # This handles fresh systems without the checklist_templates table
            if "relation" in str(e).lower() and "does not exist" in str(e).lower():
                logger.warning("Checklist templates table does not exist, returning empty list")
                return []
            raise

    async def get_template_by_id(
        self, template_id: str, user_id: Optional[str] = None
    ) -> Optional[ChecklistTemplateResponse]:
        """Get a specific template by ID.
        
        Validates access based on template visibility and ownership.
        """
        try:
            result = (
                self.supabase.table("checklist_templates")
                .select("*")
                .eq("id", template_id)
                .execute()
            )

            if not result.data:
                return None

            template = result.data[0]
            
            # Check access
            if not template["is_public"] and template["user_id"] != user_id:
                raise AppError(
                    "You don't have access to this template",
                    error_code=ErrorCode.FORBIDDEN,
                )

            return ChecklistTemplateResponse(
                **template,
                is_owner=bool(user_id and template.get("user_id") == user_id)
            )

        except Exception as e:
            logger.error(f"Error fetching template: {e}")
            raise

    async def update_template(
        self,
        template_id: str,
        request: ChecklistTemplateRequest,
        user_id: Optional[str] = None,
    ) -> ChecklistTemplateResponse:
        """Update an existing template.
        
        Only the owner can update a template.
        For anonymous users, we'll rely on frontend tracking.
        """
        try:
            # Get existing template
            existing = (
                self.supabase.table("checklist_templates")
                .select("*")
                .eq("id", template_id)
                .execute()
            )

            if not existing.data:
                raise AppError(
                    "Template not found",
                    error_code=ErrorCode.NOT_FOUND,
                )

            template = existing.data[0]
            
            # Check ownership
            # For anonymous templates (user_id=null), we trust frontend validation
            if template["user_id"] and template["user_id"] != user_id:
                raise AppError(
                    "You don't have permission to update this template",
                    error_code=ErrorCode.FORBIDDEN,
                )

            # Update access level based on is_public
            access_level = "public" if request.is_public else "private"

            # Update template
            result = (
                self.supabase.table("checklist_templates")
                .update(
                    {
                        "name": request.name,
                        "content": request.content,
                        "category": request.category,
                        "is_public": request.is_public,
                        "access_level": access_level,
                        "updated_at": "NOW()",
                    }
                )
                .eq("id", template_id)
                .execute()
            )

            if not result.data:
                raise AppError(
                    "Failed to update template",
                    error_code=ErrorCode.INTERNAL_ERROR,
                )

            return ChecklistTemplateResponse(
                **result.data[0],
                is_owner=True
            )

        except Exception as e:
            logger.error(f"Error updating template: {e}")
            raise

    async def delete_template(
        self, template_id: str, user_id: Optional[str] = None
    ):
        """Delete a template.
        
        Only the owner can delete a template.
        """
        try:
            # Get existing template
            existing = (
                self.supabase.table("checklist_templates")
                .select("*")
                .eq("id", template_id)
                .execute()
            )

            if not existing.data:
                raise AppError(
                    "Template not found",
                    error_code=ErrorCode.NOT_FOUND,
                )

            template = existing.data[0]
            
            # Check ownership
            # For anonymous templates (user_id=null), we trust frontend validation
            if template["user_id"] and template["user_id"] != user_id:
                raise AppError(
                    "You don't have permission to delete this template",
                    error_code=ErrorCode.FORBIDDEN,
                )

            # Delete template
            self.supabase.table("checklist_templates").delete().eq(
                "id", template_id
            ).execute()

            logger.info(f"Deleted template {template_id}")

        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            raise