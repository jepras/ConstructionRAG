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
    UploadType,
    Project,
    EmailUpload,
)
from src.utils.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class PipelineService:
    """Service for managing pipeline operations in the database."""

    def __init__(self, use_admin_client=False):
        if use_admin_client:
            from src.config.database import get_supabase_admin_client

            self.supabase = get_supabase_admin_client()
        else:
            self.supabase = get_supabase_client()

    async def create_indexing_run(
        self,
        upload_type: UploadType = UploadType.USER_PROJECT,
        upload_id: Optional[str] = None,
        project_id: Optional[UUID] = None,
    ) -> IndexingRun:
        """Create a new indexing run."""
        try:
            indexing_run_data = IndexingRunCreate(
                upload_type=upload_type,
                upload_id=upload_id,
                project_id=project_id,
                status="pending",
            )

            # Convert UUIDs to strings for JSON serialization
            data_dict = indexing_run_data.model_dump()
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

            result = (
                self.supabase.table("indexing_run_documents")
                .insert(data_dict)
                .execute()
            )

            if not result.data:
                raise DatabaseError("Failed to link document to indexing run")

            return True

        except Exception as e:
            logger.error(f"Error linking document to indexing run: {e}")
            raise DatabaseError(f"Failed to link document to indexing run: {str(e)}")

    async def create_project(
        self, user_id: UUID, name: str, description: Optional[str] = None
    ) -> Project:
        """Create a new project for a user."""
        try:
            from src.models.pipeline import Project, ProjectCreate

            project_data = ProjectCreate(
                user_id=user_id, name=name, description=description
            )

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
        self, upload_id: str, email: str, filename: str, file_size: Optional[int] = None
    ) -> EmailUpload:
        """Create a new email upload record."""
        try:
            from src.models.pipeline import EmailUpload, EmailUploadCreate

            email_upload_data = EmailUploadCreate(
                id=upload_id, email=email, filename=filename, file_size=file_size
            )

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
        public_url: Optional[str] = None,
        processing_results: Optional[Dict[str, Any]] = None,
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
                completed_at=(
                    datetime.utcnow().isoformat()
                    if status in ["completed", "failed"]
                    else None
                ),
            )

            data_dict = update_data.model_dump(exclude_unset=True)

            result = (
                self.supabase.table("email_uploads")
                .update(data_dict)
                .eq("id", upload_id)
                .execute()
            )

            if not result.data:
                raise DatabaseError("Failed to update email upload")

            return EmailUpload(**result.data[0])

        except Exception as e:
            logger.error(f"Error updating email upload status: {e}")
            raise DatabaseError(f"Failed to update email upload status: {str(e)}")

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
            data_dict = update_data.model_dump(exclude_unset=True, mode="json")

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

    def _serialize_step_result(self, step_result: StepResult) -> dict:
        """Serialize step result with proper datetime handling"""
        try:
            # Convert to dict and handle datetime serialization
            result_dict = step_result.model_dump()

            # Convert datetime objects to ISO format strings
            if isinstance(result_dict.get("started_at"), datetime):
                result_dict["started_at"] = result_dict["started_at"].isoformat()
            if isinstance(result_dict.get("completed_at"), datetime):
                result_dict["completed_at"] = result_dict["completed_at"].isoformat()

            return result_dict
        except Exception as e:
            logger.error(f"Error serializing step result: {e}")
            # Fallback: convert to string representation
            return {"error": f"Serialization failed: {str(e)}"}

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

    async def store_document_step_result(
        self, document_id: UUID, step_name: str, step_result: StepResult
    ) -> bool:
        """Store a step result in the document's step_results JSONB field."""
        try:
            # First, get the current step_results
            result = (
                self.supabase.table("documents")
                .select("step_results")
                .eq("id", str(document_id))
                .execute()
            )

            if not result.data:
                raise DatabaseError("Document not found")

            current_step_results = result.data[0].get("step_results", {})

            # Add the new step result with custom serialization
            current_step_results[step_name] = self._serialize_step_result(step_result)

            # Determine indexing status based on step result
            indexing_status = "running"
            if step_result.status == "failed":
                indexing_status = "failed"
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

            # Update the step_results field and indexing_status
            update_result = (
                self.supabase.table("documents")
                .update(
                    {
                        "step_results": current_step_results,
                        "indexing_status": indexing_status,
                    }
                )
                .eq("id", str(document_id))
                .execute()
            )

            if not update_result.data:
                raise DatabaseError("Failed to store document step result")

            logger.info(f"Stored step result for {step_name} in document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing document step result: {e}")
            raise DatabaseError(f"Failed to store document step result: {str(e)}")

    async def get_document_step_result(
        self, document_id: UUID, step_name: str
    ) -> Optional[StepResult]:
        """Get a specific step result from a document's step_results field."""
        try:
            result = (
                self.supabase.table("documents")
                .select("step_results")
                .eq("id", str(document_id))
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
            logger.error(f"Error getting document step result: {e}")
            raise DatabaseError(f"Failed to get document step result: {str(e)}")

    async def get_document_step_results(
        self, document_id: UUID
    ) -> Dict[str, StepResult]:
        """Get all step results for a document."""
        try:
            result = (
                self.supabase.table("documents")
                .select("step_results")
                .eq("id", str(document_id))
                .execute()
            )

            if not result.data:
                return {}

            step_results = result.data[0].get("step_results", {})

            return {
                step_name: StepResult(**step_data)
                for step_name, step_data in step_results.items()
            }

        except Exception as e:
            logger.error(f"Error getting document step results: {e}")
            raise DatabaseError(f"Failed to get document step results: {str(e)}")

    async def get_indexing_run(self, indexing_run_id: UUID) -> Optional[IndexingRun]:
        """Get a complete indexing run with all step results."""
        logger.info(
            f"🔍 PipelineService.get_indexing_run called with: {indexing_run_id}"
        )
        logger.info(f"🔍 Indexing run ID type: {type(indexing_run_id)}")

        try:
            # First, let's see what indexing runs exist in the database
            logger.info("🔍 Checking what indexing runs exist in database...")
            all_runs_result = (
                self.supabase.table("indexing_runs")
                .select("id, status, started_at")
                .execute()
            )
            logger.info(f"📊 All indexing runs in database: {all_runs_result.data}")
            logger.info(
                f"📊 Total indexing runs found: {len(all_runs_result.data) if all_runs_result.data else 0}"
            )

            # Check if our specific run ID exists
            if all_runs_result.data:
                existing_ids = [run.get("id") for run in all_runs_result.data]
                logger.info(f"📊 Existing run IDs: {existing_ids}")
                if str(indexing_run_id) in existing_ids:
                    logger.info(f"✅ Run ID {indexing_run_id} found in existing runs")
                else:
                    logger.warning(
                        f"❌ Run ID {indexing_run_id} NOT found in existing runs"
                    )
                    logger.warning(f"❌ Looking for: {str(indexing_run_id)}")
                    logger.warning(f"❌ Available: {existing_ids}")

            logger.info(
                f"📡 Executing database query for indexing run: {indexing_run_id}"
            )
            result = (
                self.supabase.table("indexing_runs")
                .select("*")
                .eq("id", str(indexing_run_id))
                .execute()
            )

            logger.info(f"📊 Database query result: {result}")
            logger.info(
                f"📊 Result data length: {len(result.data) if result.data else 0}"
            )

            if not result.data:
                logger.warning(f"❌ No indexing run found for ID: {indexing_run_id}")
                return None

            raw_data = result.data[0]
            logger.info(f"📊 Raw database data: {raw_data}")
            logger.info(f"📊 Raw data keys: {list(raw_data.keys())}")
            logger.info(
                f"📊 Raw data types: {[(k, type(v)) for k, v in raw_data.items()]}"
            )

            # Check for pipeline_config field specifically
            if "pipeline_config" in raw_data:
                logger.info(
                    f"✅ pipeline_config found in database: {raw_data['pipeline_config']}"
                )
                logger.info(
                    f"✅ pipeline_config type: {type(raw_data['pipeline_config'])}"
                )
            else:
                logger.warning(f"⚠️ pipeline_config NOT found in database data")

            logger.info(f"🔧 Creating IndexingRun object from raw data...")
            indexing_run = IndexingRun(**raw_data)
            logger.info(
                f"✅ Successfully created IndexingRun object: {indexing_run.id}"
            )
            logger.info(
                f"✅ IndexingRun pipeline_config: {indexing_run.pipeline_config}"
            )

            return indexing_run

        except Exception as e:
            logger.error(f"❌ Error getting indexing run: {e}")
            logger.error(f"❌ Error type: {type(e)}")
            logger.error(f"❌ Error details: {str(e)}")
            import traceback

            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
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

    async def get_all_indexing_runs(self) -> List[IndexingRun]:
        """Get all indexing runs, sorted by latest first."""
        logger.info("🔍 Getting all indexing runs from database...")

        try:
            result = (
                self.supabase.table("indexing_runs")
                .select("*")
                .order("started_at", desc=True)
                .execute()
            )

            logger.info(f"📊 Raw database result: {result.data}")
            logger.info(
                f"📊 Number of runs found: {len(result.data) if result.data else 0}"
            )

            if result.data:
                for i, run in enumerate(result.data):
                    logger.info(
                        f"📊 Run {i+1}: ID={run.get('id')}, upload_type={run.get('upload_type')}, status={run.get('status')}"
                    )

            indexing_runs = [IndexingRun(**run) for run in result.data]
            logger.info(
                f"✅ Successfully created {len(indexing_runs)} IndexingRun objects"
            )

            return indexing_runs

        except Exception as e:
            logger.error(f"Error getting all indexing runs: {e}")
            raise DatabaseError(f"Failed to get all indexing runs: {str(e)}")
