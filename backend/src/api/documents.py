"""Document upload and management API endpoints."""

import os
import tempfile
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.services.auth_service import get_current_user, get_current_user_optional
from src.models.document import Document, DocumentStatus
from src.models.pipeline import UploadType, PipelineStatus
from src.pipeline.shared.models import DocumentInput
from src.services.storage_service import StorageService
from src.services.pipeline_service import PipelineService
from src.pipeline.indexing.orchestrator import get_indexing_orchestrator
from src.config.database import get_supabase_admin_client
from src.utils.exceptions import StorageError

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


# Pydantic models for API responses
class EmailUploadResponse(BaseModel):
    """Response for email upload"""

    upload_id: str
    public_url: str
    status: str
    message: str
    expires_at: str


class DocumentUploadResponse(BaseModel):
    """Response for user project document upload"""

    document_id: str
    project_id: str
    index_run_id: str
    status: str
    message: str


class DocumentListResponse(BaseModel):
    """Response for document listing"""

    documents: List[Dict[str, Any]]
    total_count: int
    has_more: bool


# Email Upload Endpoints (Anonymous)


@router.post("/email-uploads", response_model=EmailUploadResponse)
async def upload_email_pdf(
    file: UploadFile = File(...),
    email: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Upload PDF for anonymous email-based processing"""

    # Validate file
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    if file.size and file.size > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(400, "File size must be less than 50MB")

    upload_id = str(uuid4())

    try:
        # Initialize services
        db = get_supabase_admin_client()
        storage_service = StorageService()

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Upload to Supabase Storage
            storage_path = f"email-uploads/{upload_id}/original.pdf"
            public_url = await storage_service.upload_file(
                file_path=temp_file_path, storage_path=storage_path
            )

            # Store in email_uploads table
            email_upload_data = {
                "id": upload_id,
                "email": email,
                "filename": file.filename,
                "file_size": len(content),
                "status": "processing",
                "public_url": public_url,
            }

            result = db.table("email_uploads").insert(email_upload_data).execute()

            if not result.data:
                raise HTTPException(500, "Failed to store email upload record")

            # Start processing pipeline in background
            background_tasks.add_task(
                process_email_upload_async,
                upload_id=upload_id,
                email=email,
                file_path=temp_file_path,
                filename=file.filename,
            )

            return EmailUploadResponse(
                upload_id=upload_id,
                public_url=f"/email-uploads/{upload_id}",
                status="processing",
                message="PDF uploaded successfully. Processing started.",
                expires_at=result.data[0]["expires_at"],
            )

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except StorageError as e:
        logger.error(f"Storage error during email upload: {e}")
        raise HTTPException(500, f"Storage error: {str(e)}")
    except Exception as e:
        logger.error(f"Error during email upload: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")


@router.get("/email-uploads/{upload_id}", response_model=Dict[str, Any])
async def get_email_upload_status(upload_id: str):
    """Get status of email upload processing"""

    try:
        db = get_supabase_admin_client()

        result = db.table("email_uploads").select("*").eq("id", upload_id).execute()

        if not result.data:
            raise HTTPException(404, "Email upload not found")

        upload_data = result.data[0]

        return {
            "upload_id": upload_id,
            "email": upload_data["email"],
            "filename": upload_data["filename"],
            "status": upload_data["status"],
            "public_url": upload_data["public_url"],
            "created_at": upload_data["created_at"],
            "completed_at": upload_data["completed_at"],
            "expires_at": upload_data["expires_at"],
            "processing_results": upload_data.get("processing_results", {}),
        }

    except Exception as e:
        logger.error(f"Error getting email upload status: {e}")
        raise HTTPException(500, f"Failed to get upload status: {str(e)}")


# User Project Upload Endpoints (Authenticated)


@router.post("/projects/{project_id}/documents", response_model=DocumentUploadResponse)
async def upload_project_document(
    project_id: UUID,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Upload PDF to user's project"""

    # Validate file
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    if file.size and file.size > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(400, "File size must be less than 50MB")

    try:
        # Initialize services
        db = get_supabase_admin_client()
        storage_service = StorageService()
        pipeline_service = PipelineService()

        # Verify user owns project
        project_result = (
            db.table("projects")
            .select("*")
            .eq("id", str(project_id))
            .eq("user_id", current_user["id"])
            .execute()
        )

        if not project_result.data:
            raise HTTPException(404, "Project not found or access denied")

        project = project_result.data[0]

        # Get or create index run
        index_run_result = (
            db.table("indexing_runs")
            .select("*")
            .eq("project_id", str(project_id))
            .order("version", desc=True)
            .limit(1)
            .execute()
        )

        if index_run_result.data and index_run_result.data[0]["status"] in [
            "pending",
            "running",
        ]:
            # Use existing index run
            index_run = index_run_result.data[0]
            index_run_id = index_run["id"]
        else:
            # Create new index run
            new_version = (
                (index_run_result.data[0]["version"] + 1)
                if index_run_result.data
                else 1
            )

            index_run_data = {
                "project_id": str(project_id),
                "version": new_version,
                "status": "pending",
                "upload_type": "user_project",
            }

            index_run_result = (
                db.table("indexing_runs").insert(index_run_data).execute()
            )
            index_run_id = index_run_result.data[0]["id"]

        # Create document record
        document_id = str(uuid4())
        document_data = {
            "id": document_id,
            "user_id": current_user["id"],
            "filename": file.filename,
            "file_size": file.size,
            "status": "pending",
            "upload_type": "user_project",
            "project_id": str(project_id),
            "index_run_id": index_run_id,
        }

        document_result = db.table("documents").insert(document_data).execute()

        if not document_result.data:
            raise HTTPException(500, "Failed to create document record")

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Upload to Supabase Storage
            storage_path = f"users/{current_user['id']}/projects/{project_id}/index-runs/{index_run_id}/pdfs/{file.filename}"
            public_url = await storage_service.upload_file(
                file_path=temp_file_path, storage_path=storage_path
            )

            # Update document with file path
            db.table("documents").update({"file_path": public_url}).eq(
                "id", document_id
            ).execute()

            # Start processing pipeline in background
            background_tasks.add_task(
                process_project_document_async,
                document_id=document_id,
                project_id=project_id,
                index_run_id=index_run_id,
                user_id=current_user["id"],
                file_path=temp_file_path,
                filename=file.filename,
            )

            return DocumentUploadResponse(
                document_id=document_id,
                project_id=str(project_id),
                index_run_id=index_run_id,
                status="processing",
                message="Document uploaded successfully. Processing started.",
            )

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except StorageError as e:
        logger.error(f"Storage error during project upload: {e}")
        raise HTTPException(500, f"Storage error: {str(e)}")
    except Exception as e:
        logger.error(f"Error during project upload: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")


@router.get("/projects/{project_id}/documents", response_model=DocumentListResponse)
async def get_project_documents(
    project_id: UUID,
    limit: int = 20,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get list of documents in a project"""

    try:
        db = get_supabase_admin_client()

        # Verify user owns project
        project_result = (
            db.table("projects")
            .select("*")
            .eq("id", str(project_id))
            .eq("user_id", current_user["id"])
            .execute()
        )

        if not project_result.data:
            raise HTTPException(404, "Project not found or access denied")

        # Get documents with pagination
        documents_result = (
            db.table("documents")
            .select("*")
            .eq("project_id", str(project_id))
            .range(offset, offset + limit - 1)
            .execute()
        )

        # Get total count
        count_result = (
            db.table("documents")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
        total_count = count_result.count or 0

        return DocumentListResponse(
            documents=documents_result.data,
            total_count=total_count,
            has_more=(offset + limit) < total_count,
        )

    except Exception as e:
        logger.error(f"Error getting project documents: {e}")
        raise HTTPException(500, f"Failed to get documents: {str(e)}")


@router.get(
    "/projects/{project_id}/documents/{document_id}", response_model=Dict[str, Any]
)
async def get_project_document(
    project_id: UUID,
    document_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get specific document details"""

    try:
        db = get_supabase_admin_client()

        # Verify user owns project and document
        document_result = (
            db.table("documents")
            .select("*")
            .eq("id", str(document_id))
            .eq("project_id", str(project_id))
            .eq("user_id", current_user["id"])
            .execute()
        )

        if not document_result.data:
            raise HTTPException(404, "Document not found or access denied")

        document = document_result.data[0]

        # Get processing status from indexing_runs
        if document.get("index_run_id"):
            index_run_result = (
                db.table("indexing_runs")
                .select("*")
                .eq("id", document["index_run_id"])
                .execute()
            )
            if index_run_result.data:
                document["index_run_status"] = index_run_result.data[0]["status"]

        return document

    except Exception as e:
        logger.error(f"Error getting project document: {e}")
        raise HTTPException(500, f"Failed to get document: {str(e)}")


@router.delete("/projects/{project_id}/documents/{document_id}")
async def delete_project_document(
    project_id: UUID,
    document_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a document from a project"""

    try:
        db = get_supabase_admin_client()

        # Verify user owns project and document
        document_result = (
            db.table("documents")
            .select("*")
            .eq("id", str(document_id))
            .eq("project_id", str(project_id))
            .eq("user_id", current_user["id"])
            .execute()
        )

        if not document_result.data:
            raise HTTPException(404, "Document not found or access denied")

        document = document_result.data[0]

        # Delete from database (cascade will handle related records)
        db.table("documents").delete().eq("id", str(document_id)).execute()

        # TODO: Clean up storage files (implement storage cleanup)

        return {"message": "Document deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting project document: {e}")
        raise HTTPException(500, f"Failed to delete document: {str(e)}")


# Background processing functions


async def process_email_upload_async(
    upload_id: str, email: str, file_path: str, filename: str
):
    """Background processing for email uploads"""

    try:
        logger.info(f"Starting email upload processing for {upload_id}")

        # Initialize services
        storage_service = StorageService()
        db = get_supabase_admin_client()

        # Create document input for pipeline
        document_input = DocumentInput(
            document_id=UUID(
                upload_id
            ),  # Use upload_id as document_id for email uploads
            run_id=UUID(int=0),  # Placeholder - will be updated by orchestrator
            user_id=None,  # No user for email uploads
            file_path=file_path,
            filename=filename,
            upload_type=UploadType.EMAIL,
            upload_id=upload_id,
            metadata={"email": email},
        )

        # Get orchestrator and process
        orchestrator = await get_indexing_orchestrator()
        success = await orchestrator.process_document_async(document_input)

        if success:
            # Update email_uploads table
            db.table("email_uploads").update(
                {"status": "completed", "completed_at": "now()"}
            ).eq("id", upload_id).execute()

            logger.info(f"Email upload processing completed for {upload_id}")
        else:
            # Update email_uploads table with error
            db.table("email_uploads").update(
                {"status": "failed", "completed_at": "now()"}
            ).eq("id", upload_id).execute()

            logger.error(f"Email upload processing failed for {upload_id}")

    except Exception as e:
        logger.error(f"Error in email upload processing for {upload_id}: {e}")

        # Update email_uploads table with error
        try:
            db = get_supabase_admin_client()
            db.table("email_uploads").update(
                {"status": "failed", "completed_at": "now()"}
            ).eq("id", upload_id).execute()
        except:
            pass


async def process_project_document_async(
    document_id: str,
    project_id: UUID,
    index_run_id: str,
    user_id: str,
    file_path: str,
    filename: str,
):
    """Background processing for project documents"""

    try:
        logger.info(f"Starting project document processing for {document_id}")

        # Initialize services
        storage_service = StorageService()
        db = get_supabase_admin_client()

        # Create document input for pipeline
        document_input = DocumentInput(
            document_id=UUID(document_id),
            run_id=UUID(int=0),  # Placeholder - will be updated by orchestrator
            user_id=UUID(user_id),
            file_path=file_path,
            filename=filename,
            upload_type=UploadType.USER_PROJECT,
            project_id=project_id,
            index_run_id=UUID(index_run_id),
            metadata={},
        )

        # Get orchestrator and process
        orchestrator = await get_indexing_orchestrator()
        success = await orchestrator.process_document_async(document_input)

        if success:
            # Update document status
            db.table("documents").update({"status": "completed"}).eq(
                "id", document_id
            ).execute()

            logger.info(f"Project document processing completed for {document_id}")
        else:
            # Update document status with error
            db.table("documents").update({"status": "failed"}).eq(
                "id", document_id
            ).execute()

            logger.error(f"Project document processing failed for {document_id}")

    except Exception as e:
        logger.error(f"Error in project document processing for {document_id}: {e}")

        # Update document status with error
        try:
            db = get_supabase_admin_client()
            db.table("documents").update({"status": "failed"}).eq(
                "id", document_id
            ).execute()
        except:
            pass
