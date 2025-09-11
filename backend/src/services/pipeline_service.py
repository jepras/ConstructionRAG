"""Pipeline service for database operations related to pipeline steps."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from src.config.database import get_supabase_client
from src.models.pipeline import (
    EmailUpload,
    IndexingRun,
    IndexingRunCreate,
    IndexingRunUpdate,
    Project,
    StepResult,
    UploadType,
)
from src.utils.exceptions import DatabaseError

logger = logging.getLogger(__name__)

try:
    # For type hints (optional import)
    from supabase import Client as SupabaseClient  # type: ignore
except Exception:  # pragma: no cover

    class SupabaseClient:  # type: ignore
        ...


class PipelineService:
    """Service for managing pipeline operations in the database."""

    def __init__(self, use_admin_client: bool = False, client: SupabaseClient | None = None):
        if client is not None:
            self.supabase = client
        else:
            if use_admin_client:
                from src.config.database import get_supabase_admin_client

                self.supabase = get_supabase_admin_client()
            else:
                self.supabase = get_supabase_client()

    async def create_indexing_run(
        self,
        upload_type: UploadType = UploadType.USER_PROJECT,
        user_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> IndexingRun:
        """Create a new indexing run."""
        try:
            indexing_run_data = IndexingRunCreate(
                upload_type=upload_type,
                user_id=user_id,
                project_id=project_id,
                status="pending",
            )

            # Convert UUIDs to strings for JSON serialization
            data_dict = indexing_run_data.model_dump()
            if data_dict.get("user_id"):
                data_dict["user_id"] = str(data_dict["user_id"])
            if data_dict.get("project_id"):
                data_dict["project_id"] = str(data_dict["project_id"])

            result = self.supabase.table("indexing_runs").insert(data_dict).execute()

            if not result.data:
                raise DatabaseError("Failed to create indexing run")

            return IndexingRun(**result.data[0])

        except Exception as e:
            logger.error(f"Error creating indexing run: {e}")
            raise DatabaseError(f"Failed to create indexing run: {str(e)}")

    async def link_document_to_indexing_run(
        self,
        indexing_run_id: UUID,
        document_id: UUID,
    ) -> bool:
        """Link a document to an indexing run."""
        try:
            from src.models.pipeline import IndexingRunDocumentCreate

            link_data = IndexingRunDocumentCreate(
                indexing_run_id=indexing_run_id,
                document_id=document_id,
            )

            data_dict = link_data.model_dump()
            data_dict["indexing_run_id"] = str(data_dict["indexing_run_id"])
            data_dict["document_id"] = str(data_dict["document_id"])

            # Check if the link already exists
            existing_result = (
                self.supabase.table("indexing_run_documents")
                .select("id")
                .eq("indexing_run_id", str(indexing_run_id))
                .eq("document_id", str(document_id))
                .execute()
            )

            if existing_result.data:
                print(f"📋 Document {document_id} already linked")
                return True

            result = self.supabase.table("indexing_run_documents").insert(data_dict).execute()

            if not result.data:
                raise DatabaseError("Failed to link document to indexing run")

            return True

        except Exception as e:
            logger.error(f"Error linking document to indexing run: {e}")
            raise DatabaseError(f"Failed to link document to indexing run: {str(e)}")

    async def create_project(self, user_id: UUID, name: str, description: str | None = None) -> Project:
        """Create a new project for a user."""
        try:
            from src.models.pipeline import Project, ProjectCreate

            project_data = ProjectCreate(user_id=user_id, name=name, description=description)

            # Convert UUIDs to strings for JSON serialization
            data_dict = project_data.model_dump()
            data_dict["user_id"] = str(data_dict["user_id"])

            result = self.supabase.table("projects").insert(data_dict).execute()

            if not result.data:
                raise DatabaseError("Failed to create project")

            return Project(**result.data[0])

        except Exception as e:
            logger.error(f"Error creating project: {e}")
            raise DatabaseError(f"Failed to create project: {str(e)}")

    async def create_email_upload(
        self, upload_id: str, email: str, filename: str, file_size: int | None = None
    ) -> EmailUpload:
        """Create a new email upload record."""
        try:
            from src.models.pipeline import EmailUpload, EmailUploadCreate

            email_upload_data = EmailUploadCreate(id=upload_id, email=email, filename=filename, file_size=file_size)

            data_dict = email_upload_data.model_dump()

            result = self.supabase.table("email_uploads").insert(data_dict).execute()

            if not result.data:
                raise DatabaseError("Failed to create email upload")

            return EmailUpload(**result.data[0])

        except Exception as e:
            logger.error(f"Error creating email upload: {e}")
            raise DatabaseError(f"Failed to create email upload: {str(e)}")

    async def update_email_upload_status(
        self,
        upload_id: str,
        status: str,
        public_url: str | None = None,
        processing_results: dict[str, Any] | None = None,
    ) -> EmailUpload:
        """Update the status of an email upload."""
        try:
            from src.models.pipeline import EmailUpload, EmailUploadUpdate

            # Ensure processing_results doesn't contain datetime objects
            if processing_results:
                # Convert any datetime objects to ISO strings
                def convert_datetime(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    elif isinstance(obj, dict):
                        return {k: convert_datetime(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_datetime(item) for item in obj]
                    return obj

                processing_results = convert_datetime(processing_results)

            update_data = EmailUploadUpdate(
                status=status,
                public_url=public_url,
                processing_results=processing_results,
                completed_at=(datetime.utcnow().isoformat() if status in ["completed", "failed"] else None),
            )

            data_dict = update_data.model_dump(exclude_unset=True)

            result = self.supabase.table("email_uploads").update(data_dict).eq("id", upload_id).execute()

            if not result.data:
                raise DatabaseError("Failed to update email upload")

            return EmailUpload(**result.data[0])

        except Exception as e:
            logger.error(f"Error updating email upload status: {e}")
            raise DatabaseError(f"Failed to update email upload status: {str(e)}")

    async def update_indexing_run_status(
        self, indexing_run_id: UUID, status: str, error_message: str | None = None
    ) -> IndexingRun:
        """Update the status of an indexing run."""
        try:
            update_data = IndexingRunUpdate(
                status=status,
                error_message=error_message,
                completed_at=(datetime.utcnow() if status in ["completed", "failed"] else None),
            )

            # Convert UUIDs to strings for JSON serialization
            data_dict = update_data.model_dump(exclude_unset=True, mode="json")

            result = self.supabase.table("indexing_runs").update(data_dict).eq("id", str(indexing_run_id)).execute()

            if not result.data:
                raise DatabaseError("Failed to update indexing run")

            return IndexingRun(**result.data[0])

        except Exception as e:
            logger.error(f"Error updating indexing run status: {e}")
            raise DatabaseError(f"Failed to update indexing run status: {str(e)}")

    def _serialize_step_result(self, step_result: StepResult) -> dict:
        """Serialize step result with proper datetime handling and size optimization"""
        try:
            # Convert to dict and handle datetime serialization
            result_dict = step_result.model_dump()

            # Convert datetime objects to ISO format strings
            if isinstance(result_dict.get("started_at"), datetime):
                result_dict["started_at"] = result_dict["started_at"].isoformat()
            if isinstance(result_dict.get("completed_at"), datetime):
                result_dict["completed_at"] = result_dict["completed_at"].isoformat()

            # OPTIMIZATION: Limit large data fields to prevent JSON size issues
            if "data" in result_dict and result_dict["data"]:
                data = result_dict["data"]
                
                # For chunking step, don't store all chunk content - just statistics
                if "chunks" in data and isinstance(data["chunks"], list):
                    chunk_count = len(data["chunks"])
                    total_size = sum(len(str(chunk.get("content", ""))) for chunk in data["chunks"])
                    # Replace large chunks array with summary
                    data["chunks"] = f"[{chunk_count} chunks, total size: {total_size} chars]"
                    logger.info(f"Reduced chunking data size: {chunk_count} chunks -> summary string")
                
                # Limit sample_outputs to prevent large payloads
                if "sample_outputs" in result_dict and isinstance(result_dict["sample_outputs"], dict):
                    sample_outputs = result_dict["sample_outputs"]
                    for key, value in sample_outputs.items():
                        if isinstance(value, list) and len(value) > 3:
                            # Limit arrays to first 3 items
                            sample_outputs[key] = value[:3] + [f"... and {len(value) - 3} more items"]

            return result_dict
        except Exception as e:
            logger.error(f"Error serializing step result: {e}")
            # Fallback: convert to minimal representation
            return {
                "step": getattr(step_result, "step", "unknown"),
                "status": getattr(step_result, "status", "unknown"),
                "error_message": getattr(step_result, "error_message", None),
                "duration_seconds": getattr(step_result, "duration_seconds", 0),
                "serialization_error": f"Full serialization failed: {str(e)}"
            }

    async def store_step_result(self, indexing_run_id: UUID, step_name: str, step_result: StepResult) -> bool:
        """Store a step result in the indexing run's step_results JSONB field."""
        try:
            # First, get the current step_results
            result = (
                self.supabase.table("indexing_runs").select("step_results").eq("id", str(indexing_run_id)).execute()
            )

            if not result.data:
                raise DatabaseError("Indexing run not found")

            current_step_results = result.data[0].get("step_results", {})

            # Add the new step result with custom serialization
            current_step_results[step_name] = self._serialize_step_result(step_result)

            # Update the step_results field
            update_result = (
                self.supabase.table("indexing_runs")
                .update({"step_results": current_step_results})
                .eq("id", str(indexing_run_id))
                .execute()
            )

            if not update_result.data:
                raise DatabaseError("Failed to store step result")

            logger.info(f"Stored step result for {step_name} in indexing run {indexing_run_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing step result: {e}")
            raise DatabaseError(f"Failed to store step result: {str(e)}")

    async def get_step_result(self, indexing_run_id: UUID, step_name: str) -> StepResult | None:
        """Get a specific step result from an indexing run."""
        try:
            result = (
                self.supabase.table("indexing_runs").select("step_results").eq("id", str(indexing_run_id)).execute()
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

    async def store_document_step_result(self, document_id: UUID, step_name: str, step_result: StepResult) -> bool:
        """Store a step result in the document's step_results JSONB field with retry logic."""
        import asyncio
        
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # First, get the current step_results
                result = self.supabase.table("documents").select("step_results").eq("id", str(document_id)).execute()

                if not result.data:
                    raise DatabaseError("Document not found")

                current_step_results = result.data[0].get("step_results", {})

                # Add the new step result with custom serialization (size-optimized)
                serialized_result = self._serialize_step_result(step_result)
                current_step_results[step_name] = serialized_result

                # Determine indexing status based on step result
                indexing_status = "running"
                error_message = None
                
                if step_result.status == "failed":
                    indexing_status = "failed"
                    error_message = getattr(step_result, 'error_message', f"{step_name} step failed")
                elif step_name == "ChunkingStep" and step_result.status == "completed":
                    # Document is completed after chunking (embedding happens in batch)
                    indexing_status = "completed"
                elif step_name == "EmbeddingStep" and step_result.status == "completed":
                    # For single document processing, embedding completes the document
                    indexing_status = "completed"

                # Debug logging
                logger.info(
                    f"📊 Document {document_id} - Step: {step_name}, Status: {step_result.status}, Setting indexing_status: {indexing_status}"
                )

                # Prepare update data
                update_data = {
                    "step_results": current_step_results,
                    "indexing_status": indexing_status,
                }
                
                # Add error message if step failed
                if error_message:
                    update_data["error_message"] = error_message

                # Update the step_results field and indexing_status
                update_result = (
                    self.supabase.table("documents")
                    .update(update_data)
                    .eq("id", str(document_id))
                    .execute()
                )

                if not update_result.data:
                    raise DatabaseError("Failed to store document step result")

                logger.info(f"Stored step result for {step_name} in document {document_id}")
                return True

            except Exception as e:
                error_str = str(e).lower()
                
                # Check for retryable errors (size, timeouts, temporary failures)
                is_retryable = any(keyword in error_str for keyword in [
                    "json could not be generated",
                    "520", "502", "503", "504",  # HTTP errors
                    "timeout",
                    "connection",
                    "temporary",
                    "payload too large"
                ])
                
                if attempt < max_retries - 1 and is_retryable:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Retrying document step result storage (attempt {attempt + 1}/{max_retries}) after {delay}s delay. Error: {e}"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final attempt failed or non-retryable error
                    detailed_error = f"Failed to store {step_name} step result for document {document_id}: {str(e)}"
                    logger.error(detailed_error)
                    
                    # Try to store minimal error information if the main storage failed
                    try:
                        await self._store_minimal_step_error(document_id, step_name, step_result.status, str(e))
                    except:
                        pass  # Don't fail if even minimal storage fails
                    
                    raise DatabaseError(detailed_error)

    async def _store_minimal_step_error(self, document_id: UUID, step_name: str, status: str, error: str) -> None:
        """Store minimal step error information when full step result storage fails."""
        try:
            # Try to store just the error in the error_message field
            minimal_update = {
                "error_message": f"{step_name} step {status}: {error[:500]}...",  # Truncate long errors
                "indexing_status": "failed"
            }
            
            self.supabase.table("documents").update(minimal_update).eq("id", str(document_id)).execute()
            logger.info(f"Stored minimal error info for document {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to store even minimal error info: {e}")

    async def get_document_step_result(self, document_id: UUID, step_name: str) -> StepResult | None:
        """Get a specific step result from a document's step_results field."""
        try:
            result = self.supabase.table("documents").select("step_results").eq("id", str(document_id)).execute()

            if not result.data:
                return None

            step_results = result.data[0].get("step_results", {})
            step_data = step_results.get(step_name)

            if not step_data:
                return None

            return StepResult(**step_data)

        except Exception as e:
            logger.error(f"Error getting document step result: {e}")
            raise DatabaseError(f"Failed to get document step result: {str(e)}")

    async def get_document_step_results(self, document_id: UUID) -> dict[str, StepResult]:
        """Get all step results for a document."""
        try:
            result = self.supabase.table("documents").select("step_results").eq("id", str(document_id)).execute()

            if not result.data:
                return {}

            step_results = result.data[0].get("step_results", {})

            return {step_name: StepResult(**step_data) for step_name, step_data in step_results.items()}

        except Exception as e:
            logger.error(f"Error getting document step results: {e}")
            raise DatabaseError(f"Failed to get document step results: {str(e)}")

    async def get_indexing_run(self, indexing_run_id: UUID) -> IndexingRun | None:
        """Get a complete indexing run with all step results."""
        try:
            result = self.supabase.table("indexing_runs").select("*").eq("id", str(indexing_run_id)).execute()

            if not result.data:
                print(f"❌ No indexing run found for ID: {indexing_run_id}")
                return None

            raw_data = result.data[0]
            indexing_run = IndexingRun(**raw_data)
            print(f"✅ Retrieved indexing run: {indexing_run.id}")
            return indexing_run

        except Exception as e:
            print(f"❌ Error getting indexing run: {e}")
            raise DatabaseError(f"Failed to get indexing run: {str(e)}")

    async def get_document_indexing_runs(self, document_id: UUID) -> list[IndexingRun]:
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

    async def get_latest_successful_indexing_run(self, document_id: UUID) -> IndexingRun | None:
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
            raise DatabaseError(f"Failed to get latest successful indexing run: {str(e)}")

    async def get_all_indexing_runs(self) -> list[IndexingRun]:
        """Get all indexing runs, sorted by latest first."""
        logger.info("🔍 Getting all indexing runs from database...")

        try:
            result = self.supabase.table("indexing_runs").select("*").order("started_at", desc=True).execute()

            logger.info(f"📊 Raw database result: {result.data}")
            logger.info(f"📊 Number of runs found: {len(result.data) if result.data else 0}")

            if result.data:
                for i, run in enumerate(result.data):
                    logger.info(
                        f"📊 Run {i + 1}: ID={run.get('id')}, upload_type={run.get('upload_type')}, status={run.get('status')}"
                    )

            indexing_runs = [IndexingRun(**run) for run in result.data]
            logger.info(f"✅ Successfully created {len(indexing_runs)} IndexingRun objects")

            return indexing_runs

        except Exception as e:
            logger.error(f"Error getting all indexing runs: {e}")
            raise DatabaseError(f"Failed to get all indexing runs: {str(e)}")
