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
    index_run_id: str
    document_count: int
    document_ids: List[str]
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


class MultiDocumentUploadResponse(BaseModel):
    """Response for multi-document project upload"""

    project_id: str
    index_run_id: str
    document_count: int
    document_ids: List[str]
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
    files: List[UploadFile] = File(...),
    email: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Upload one or more PDFs for anonymous email-based processing"""

    # Validate files
    if not files:
        raise HTTPException(400, "At least one PDF file is required")

    if len(files) > 10:  # Limit to 10 files per upload
        raise HTTPException(400, "Maximum 10 PDF files allowed per upload")

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                400, f"Only PDF files are supported. Found: {file.filename}"
            )

        if file.size and file.size > 50 * 1024 * 1024:  # 50MB limit per file
            raise HTTPException(400, f"File {file.filename} must be less than 50MB")

    upload_id = str(uuid4())
    index_run_id = str(uuid4())

    try:
        # Initialize services
        db = get_supabase_admin_client()
        storage_service = StorageService()

        # Create storage structure for the new index run
        await storage_service.create_storage_structure(
            upload_type=UploadType.EMAIL,
            upload_id=upload_id,
            index_run_id=UUID(index_run_id),
        )

        # Create index run record first
        index_run_data = {
            "id": index_run_id,
            "upload_type": "email",
            "upload_id": upload_id,
            "status": "pending",
            "created_at": "now()",
        }

        db.table("indexing_runs").insert(index_run_data).execute()

        # Process each file
        document_ids = []
        total_file_size = 0
        filenames = []
        document_data = []  # Collect document data for unified processing

        for file in files:
            # Get file content
            content = await file.read()
            total_file_size += len(content)
            filenames.append(file.filename)

            # Create document record
            document_id = str(uuid4())
            document_ids.append(document_id)

            # Upload to Supabase Storage using new structure
            storage_path = f"email-uploads/{upload_id}/index-runs/{index_run_id}/pdfs/{file.filename}"

            # Create a temporary file just for upload (will be cleaned up immediately)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

            try:
                upload_result = await storage_service.upload_file(
                    file_path=temp_file_path, storage_path=storage_path
                )
                # Extract the signed URL from the response
                if isinstance(upload_result, dict) and "signedURL" in upload_result:
                    public_url = upload_result["signedURL"]
                elif isinstance(upload_result, dict) and "signedUrl" in upload_result:
                    public_url = upload_result["signedUrl"]
                else:
                    public_url = str(upload_result)
            finally:
                # Clean up temp file immediately after upload
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

            # Store in documents table (required for foreign key constraints)
            document_data_for_db = {
                "id": document_id,  # Use the generated document_id
                "user_id": None,  # No user for email uploads
                "filename": file.filename,
                "file_size": len(content),
                "file_path": public_url,
                "status": "processing",
                "upload_type": "email",  # Set correct upload type for email uploads
                "index_run_id": index_run_id,  # Link to indexing run
                "upload_id": upload_id,  # Link to upload
                "metadata": {"email": email, "upload_id": upload_id},
            }

            doc_result = db.table("documents").insert(document_data_for_db).execute()

            if not doc_result.data:
                raise HTTPException(
                    500, f"Failed to store document record for {file.filename}"
                )

            # Store in email_uploads table (one record per file)
            email_upload_data = {
                "id": f"{upload_id}_{document_id}",  # Unique ID for each file
                "email": email,
                "filename": file.filename,
                "file_size": len(content),
                "status": "processing",
                "public_url": public_url,
                "index_run_id": index_run_id,
            }

            result = db.table("email_uploads").insert(email_upload_data).execute()

            if not result.data:
                raise HTTPException(
                    500, f"Failed to store email upload record for {file.filename}"
                )

            # Collect document data for unified processing
            document_data.append(
                {
                    "document_id": document_id,
                    "filename": file.filename,
                    "storage_url": public_url,
                }
            )

        # Start unified processing pipeline in background
        background_tasks.add_task(
            process_multi_document_email_upload_async,
            upload_id=upload_id,
            index_run_id=index_run_id,
            email=email,
            document_data=document_data,
        )

        # Return response with multi-file information
        return EmailUploadResponse(
            upload_id=upload_id,
            index_run_id=index_run_id,
            document_count=len(files),
            document_ids=document_ids,
            public_url=f"/email-uploads/{upload_id}",
            status="processing",
            message=f"{len(files)} PDF(s) uploaded successfully. Processing started.",
            expires_at=result.data[0]["expires_at"],
        )

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

        # First, try to find a single email upload record
        result = db.table("email_uploads").select("*").eq("id", upload_id).execute()

        if result.data:
            # Single file upload (legacy)
            upload_data = result.data[0]
            return {
                "upload_id": upload_id,
                "index_run_id": upload_data.get("index_run_id"),
                "email": upload_data["email"],
                "filename": upload_data["filename"],
                "status": upload_data["status"],
                "public_url": upload_data["public_url"],
                "created_at": upload_data["created_at"],
                "completed_at": upload_data["completed_at"],
                "expires_at": upload_data["expires_at"],
                "processing_results": upload_data.get("processing_results", {}),
            }

        # If not found, check if it's a multi-document upload (upload_id without suffix)
        # Look for records that start with the upload_id
        result = (
            db.table("email_uploads").select("*").like("id", f"{upload_id}_%").execute()
        )

        if result.data:
            # Multi-document upload
            uploads = result.data

            # Get the index run status
            index_run_id = uploads[0].get("index_run_id")
            index_run_status = "unknown"

            if index_run_id:
                index_run_result = (
                    db.table("indexing_runs")
                    .select("*")
                    .eq("id", index_run_id)
                    .execute()
                )
                if index_run_result.data:
                    index_run_status = index_run_result.data[0]["status"]

            # Aggregate status from all uploads
            all_completed = all(upload["status"] == "completed" for upload in uploads)
            any_failed = any(upload["status"] == "failed" for upload in uploads)

            if all_completed:
                overall_status = "completed"
            elif any_failed:
                overall_status = "completed_with_errors"
            else:
                overall_status = "processing"

            return {
                "upload_id": upload_id,
                "index_run_id": index_run_id,
                "email": uploads[0]["email"],
                "document_count": len(uploads),
                "filenames": [upload["filename"] for upload in uploads],
                "status": overall_status,
                "index_run_status": index_run_status,
                "created_at": uploads[0]["created_at"],
                "expires_at": uploads[0]["expires_at"],
                "individual_uploads": [
                    {
                        "filename": upload["filename"],
                        "status": upload["status"],
                        "public_url": upload["public_url"],
                    }
                    for upload in uploads
                ],
            }

        # Not found
        raise HTTPException(404, "Email upload not found")

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
    """Upload single PDF to user's project (legacy endpoint)"""

    # Validate file
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    if file.size and file.size > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(400, "File size must be less than 50MB")

    try:
        # Initialize services - use regular client for user project operations
        from src.config.database import get_supabase_client

        db = get_supabase_client()
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
            "upload_id": str(
                uuid4()
            ),  # Generate unique upload ID for project documents
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


@router.post(
    "/projects/{project_id}/documents/multi", response_model=MultiDocumentUploadResponse
)
async def upload_project_documents(
    project_id: UUID,
    files: List[UploadFile] = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Upload multiple PDFs to user's project"""

    # Validate file count
    if len(files) < 1:
        raise HTTPException(400, "At least one file must be uploaded")
    if len(files) > 10:
        raise HTTPException(400, "Maximum 10 files can be uploaded at once")

    # Validate all files
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                400, f"Only PDF files are supported. Invalid file: {file.filename}"
            )
        if file.size and file.size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(
                400, f"File size must be less than 50MB. Invalid file: {file.filename}"
            )

    try:
        # Initialize services
        from src.config.database import get_supabase_client

        db = get_supabase_client()
        storage_service = StorageService()

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

        # Create new index run for multi-document upload
        index_run_result = (
            db.table("indexing_runs")
            .select("*")
            .eq("project_id", str(project_id))
            .order("version", desc=True)
            .limit(1)
            .execute()
        )

        new_version = (
            (index_run_result.data[0]["version"] + 1) if index_run_result.data else 1
        )

        index_run_data = {
            "project_id": str(project_id),
            "version": new_version,
            "status": "pending",
            "upload_type": "user_project",
        }

        index_run_result = db.table("indexing_runs").insert(index_run_data).execute()
        index_run_id = index_run_result.data[0]["id"]

        # Process each file
        document_ids = []
        document_data = []  # Collect document data for unified processing

        for file in files:
            # Create document record
            document_id = str(uuid4())
            document_ids.append(document_id)

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

                # Store in documents table
                document_data_for_db = {
                    "id": document_id,
                    "user_id": current_user["id"],
                    "filename": file.filename,
                    "file_size": len(content),
                    "file_path": public_url,
                    "status": "processing",
                    "upload_type": "user_project",
                    "project_id": str(project_id),
                    "index_run_id": index_run_id,
                    "upload_id": str(
                        uuid4()
                    ),  # Generate unique upload ID for each document
                }

                doc_result = (
                    db.table("documents").insert(document_data_for_db).execute()
                )

                if not doc_result.data:
                    raise HTTPException(
                        500, f"Failed to store document record for {file.filename}"
                    )

                # Collect document data for unified processing
                document_data.append(
                    {
                        "document_id": document_id,
                        "filename": file.filename,
                        "storage_url": public_url,
                    }
                )

            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        # Start unified processing pipeline in background
        background_tasks.add_task(
            process_multi_document_project_upload_async,
            project_id=project_id,
            index_run_id=index_run_id,
            user_id=current_user["id"],
            document_data=document_data,
        )

        # Return response with multi-file information
        return MultiDocumentUploadResponse(
            project_id=str(project_id),
            index_run_id=index_run_id,
            document_count=len(files),
            document_ids=document_ids,
            status="processing",
            message=f"{len(files)} PDF(s) uploaded successfully. Processing started.",
        )

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
        from src.config.database import get_supabase_client

        db = get_supabase_client()

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
        from src.config.database import get_supabase_client

        db = get_supabase_client()

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
        from src.config.database import get_supabase_client

        db = get_supabase_client()

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


@router.get(
    "/documents/by-index-run/{index_run_id}", response_model=List[Dict[str, Any]]
)
async def get_documents_by_index_run(
    index_run_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get all documents for a specific indexing run using the junction table"""
    logger.info(f"🔍 Getting documents for indexing run: {index_run_id}")

    try:
        db = get_supabase_admin_client()
        logger.info(f"✅ Using admin client")

        # First, get document IDs from the junction table
        logger.info(f"🔗 Querying junction table for indexing_run_id: {index_run_id}")
        junction_result = (
            db.table("indexing_run_documents")
            .select("document_id")
            .eq("indexing_run_id", str(index_run_id))
            .execute()
        )

        logger.info(f"📊 Junction query result: {junction_result}")
        logger.info(
            f"📊 Junction data length: {len(junction_result.data) if junction_result.data else 0}"
        )

        if not junction_result.data:
            logger.warning(
                f"❌ No junction records found for indexing run {index_run_id}"
            )
            return []

        # Extract document IDs
        document_ids = [row["document_id"] for row in junction_result.data]
        logger.info(f"📄 Document IDs found: {document_ids}")

        # Get the actual documents
        logger.info(f"📄 Querying documents table for IDs: {document_ids}")
        documents_result = (
            db.table("documents").select("*").in_("id", document_ids).execute()
        )

        logger.info(f"📊 Documents query result: {documents_result}")
        logger.info(
            f"📊 Documents data length: {len(documents_result.data) if documents_result.data else 0}"
        )

        if not documents_result.data:
            logger.warning(f"❌ No documents found for IDs: {document_ids}")
            return []

        # Log details about each document
        for i, doc in enumerate(documents_result.data):
            logger.info(
                f"📄 Document {i+1}: ID={doc.get('id')}, filename={doc.get('filename')}"
            )
            step_results = doc.get("step_results", {})
            logger.info(f"  Step results keys: {list(step_results.keys())}")
            logger.info(f"  Step results count: {len(step_results)}")

            # Log specific step data
            for step_name, step_data in step_results.items():
                if isinstance(step_data, dict):
                    logger.info(
                        f"    {step_name}: status={step_data.get('status')}, keys={list(step_data.keys())}"
                    )
                else:
                    logger.info(f"    {step_name}: {type(step_data)}")

        logger.info(f"✅ Returning {len(documents_result.data)} documents")
        return documents_result.data

    except Exception as e:
        logger.error(f"❌ Error getting documents for indexing run {index_run_id}: {e}")
        logger.error(f"❌ Error type: {type(e)}")
        import traceback

        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_email_upload_async(
    upload_id: str, index_run_id: str, email: str, storage_url: str, filename: str
):
    """Background processing for email uploads"""

    try:
        logger.info(
            f"Starting email upload processing for {upload_id} (index run: {index_run_id})"
        )

        # Initialize services
        storage_service = StorageService()
        db = get_supabase_admin_client()

        # Create document record for email upload
        document_id = str(uuid4())
        document_data = {
            "id": document_id,
            "user_id": None,  # No user for email uploads
            "filename": filename,
            "file_size": 0,  # We don't have file size from URL, set to 0
            "status": "processing",
            "upload_type": "email",
            "upload_id": upload_id,
            "index_run_id": index_run_id,
        }

        db.table("documents").insert(document_data).execute()

        # Create document input for pipeline
        document_input = DocumentInput(
            document_id=UUID(document_id),  # Use the created document ID
            run_id=UUID(index_run_id),  # Use the actual index run ID
            user_id=None,  # No user for email uploads
            file_path=storage_url,  # Use storage URL as file path
            filename=filename,
            upload_type=UploadType.EMAIL,
            upload_id=upload_id,
            index_run_id=UUID(index_run_id),
            metadata={"email": email},
        )

        # Get orchestrator and process
        orchestrator = await get_indexing_orchestrator()
        success = await orchestrator.process_document_async(
            document_input, existing_indexing_run_id=UUID(index_run_id)
        )

        if success:
            # Update email_uploads table
            db.table("email_uploads").update(
                {"status": "completed", "completed_at": "now()"}
            ).eq("id", upload_id).execute()

            # Note: Indexing run status is updated by the orchestrator, no need to update here

            logger.info(f"Email upload processing completed for {upload_id}")
        else:
            # Update email_uploads table with error
            db.table("email_uploads").update(
                {"status": "failed", "completed_at": "now()"}
            ).eq("id", upload_id).execute()

            # Note: Indexing run status is updated by the orchestrator, no need to update here

            logger.error(f"Email upload processing failed for {upload_id}")

    except Exception as e:
        logger.error(f"Error in email upload processing for {upload_id}: {e}")

        # Update email_uploads table with error
        try:
            db = get_supabase_admin_client()
            db.table("email_uploads").update(
                {"status": "failed", "completed_at": "now()"}
            ).eq("id", upload_id).execute()

            # Note: Indexing run status is updated by the orchestrator, no need to update here
        except:
            pass
    # No file cleanup needed since we're using storage URLs


async def process_multi_document_email_upload_async(
    upload_id: str, index_run_id: str, email: str, document_data: List[Dict[str, Any]]
):
    """Background processing for multi-document email uploads using unified processing"""

    try:
        logger.info(
            f"Starting multi-document email upload processing for {upload_id} (index run: {index_run_id})"
        )

        # Initialize services
        storage_service = StorageService()
        db = get_supabase_admin_client()

        # Create document inputs for pipeline
        document_inputs = []

        for doc_data in document_data:
            document_id = doc_data["document_id"]
            filename = doc_data["filename"]
            storage_url = doc_data["storage_url"]

            # Create document input for pipeline
            document_input = DocumentInput(
                document_id=UUID(document_id),
                run_id=UUID(index_run_id),
                user_id=None,  # No user for email uploads
                file_path=storage_url,
                filename=filename,
                upload_type=UploadType.EMAIL,
                upload_id=upload_id,
                index_run_id=UUID(index_run_id),
                metadata={"email": email},
            )
            document_inputs.append(document_input)

        # Get orchestrator and process using unified method
        orchestrator = await get_indexing_orchestrator()
        success = await orchestrator.process_documents(
            document_inputs, existing_indexing_run_id=UUID(index_run_id)
        )

        if success:
            # Update all email_uploads records for this upload_id
            db.table("email_uploads").update(
                {"status": "completed", "completed_at": "now()"}
            ).like("id", f"{upload_id}_%").execute()

            logger.info(
                f"Multi-document email upload processing completed for {upload_id}"
            )
        else:
            # Update all email_uploads records for this upload_id with error
            db.table("email_uploads").update(
                {"status": "failed", "completed_at": "now()"}
            ).like("id", f"{upload_id}_%").execute()

            logger.error(
                f"Multi-document email upload processing failed for {upload_id}"
            )

    except Exception as e:
        logger.error(
            f"Error in multi-document email upload processing for {upload_id}: {e}"
        )

        # Update all email_uploads records for this upload_id with error
        try:
            db = get_supabase_admin_client()
            db.table("email_uploads").update(
                {"status": "failed", "completed_at": "now()"}
            ).like("id", f"{upload_id}_%").execute()
        except:
            pass


async def process_multi_document_project_upload_async(
    project_id: UUID,
    index_run_id: str,
    user_id: str,
    document_data: List[Dict[str, Any]],
):
    """Background processing for multi-document project uploads using unified processing"""

    try:
        logger.info(
            f"Starting multi-document project upload processing for project {project_id} (index run: {index_run_id})"
        )

        # Initialize services
        storage_service = StorageService()
        db = get_supabase_admin_client()

        # Create document inputs for pipeline
        document_inputs = []

        for doc_data in document_data:
            document_id = doc_data["document_id"]
            filename = doc_data["filename"]
            storage_url = doc_data["storage_url"]

            # Create document input for pipeline
            document_input = DocumentInput(
                document_id=UUID(document_id),
                run_id=UUID(index_run_id),
                user_id=UUID(user_id),
                file_path=storage_url,
                filename=filename,
                upload_type=UploadType.USER_PROJECT,
                project_id=UUID(project_id),
                index_run_id=UUID(index_run_id),
                metadata={"project_id": str(project_id)},
            )
            document_inputs.append(document_input)

        # Get orchestrator and process using unified method
        orchestrator = await get_indexing_orchestrator()
        success = await orchestrator.process_documents(
            document_inputs, existing_indexing_run_id=UUID(index_run_id)
        )

        if success:
            logger.info(
                f"Multi-document project upload processing completed for project {project_id}"
            )
        else:
            logger.error(
                f"Multi-document project upload processing failed for project {project_id}"
            )

    except Exception as e:
        logger.error(
            f"Error in multi-document project upload processing for project {project_id}: {e}"
        )


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
