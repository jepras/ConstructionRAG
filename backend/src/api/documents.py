"""Document upload and management API endpoints."""

import logging
import os
import tempfile
from typing import Any
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from pydantic import BaseModel

from src.config.database import get_supabase_admin_client
from src.middleware.request_id import get_request_id
from src.models.pipeline import UploadType
from src.pipeline.indexing.orchestrator import get_indexing_orchestrator
from src.pipeline.shared.models import DocumentInput
from src.services.auth_service import get_current_user, get_current_user_optional
from src.services.document_read_service import DocumentReadService
from src.services.storage_service import StorageService
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError, StorageError, ValidationError

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


# Pydantic models for API responses
class EmailUploadResponse(BaseModel):
    """Response for email upload"""

    index_run_id: str
    document_count: int
    document_ids: list[str]
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
    document_ids: list[str]
    status: str
    message: str


class DocumentListResponse(BaseModel):
    """Response for document listing"""

    documents: list[dict[str, Any]]
    total_count: int
    has_more: bool


class UploadCreateResponse(BaseModel):
    """Unified response for uploads (email or project)."""

    index_run_id: str
    document_count: int
    document_ids: list[str]
    status: str
    message: str


# Email Upload Endpoints (Anonymous)


@router.post("/email-uploads", response_model=EmailUploadResponse, include_in_schema=False)
async def upload_email_pdf(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    email: str = Form(...),
):
    """Deprecated: use POST /api/uploads instead.

    For unit tests, still validate inputs and raise AppError-based validation errors.
    """
    # Basic validations preserved for unit tests
    if not files or len(files) < 1:
        raise ValidationError("At least one file must be uploaded")
    if len(files) > 10:
        raise ValidationError("Maximum 10 files can be uploaded at once")
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise ValidationError("Only PDF files are supported")
        if getattr(file, "size", None) and file.size > 50 * 1024 * 1024:
            raise ValidationError("File size must be less than 50MB")

    # Still deprecated for actual flow
    from src.shared.errors import ErrorCode
    from src.utils.exceptions import AppError

    raise AppError(
        "/api/email-uploads is deprecated. Use /api/uploads instead.",
        error_code=ErrorCode.CONFIGURATION_ERROR,
        status_code=410,
    )


# User Project Upload Endpoints (Authenticated)


@router.post("/projects/{project_id}/documents", response_model=DocumentUploadResponse)
async def upload_project_document(
    background_tasks: BackgroundTasks,
    project_id: UUID,
    file: UploadFile = File(...),
    current_user: dict[str, Any] = Depends(get_current_user),
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
        from src.services.document_service import DocumentService

        db = get_supabase_client()
        storage_service = StorageService()
        doc_service = DocumentService(db, storage_service)

        # Verify user owns project
        project_result = (
            db.table("projects").select("*").eq("id", str(project_id)).eq("user_id", current_user["id"]).execute()
        )

        if not project_result.data:
            raise AppError(
                "Project not found or access denied",
                error_code=ErrorCode.NOT_FOUND,
                request_id=get_request_id(),
            )

        # project verified by ownership check above

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
            new_version = (index_run_result.data[0]["version"] + 1) if index_run_result.data else 1

            index_run_data = {
                "project_id": str(project_id),
                "version": new_version,
                "status": "pending",
                "upload_type": "user_project",
                "access_level": "private",
            }

            index_run_result = db.table("indexing_runs").insert(index_run_data).execute()
            index_run_id = index_run_result.data[0]["id"]

        # Create document via service (handles DB insert, storage upload, and update)
        content = await file.read()
        created = await doc_service.create_project_document(
            file_bytes=content,
            filename=file.filename,
            project_id=project_id,
            user_id=current_user["id"],
            index_run_id=index_run_id,
            file_size=file.size,
        )
        document_id = created["document_id"]
        temp_file_path = created["temp_path"]

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

    except StorageError:
        raise
    except AppError:
        raise
    except Exception as e:
        raise AppError(
            "Upload failed",
            error_code=ErrorCode.INTERNAL_ERROR,
            details={"reason": str(e)},
            request_id=get_request_id(),
        )


# Flat unified upload endpoint (anonymous or authenticated)


@router.post("/uploads", response_model=UploadCreateResponse)
async def create_upload(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    email: str | None = Form(None),
    project_id: UUID | None = Form(None),
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
):
    """Create an upload for email (anonymous) or project (authenticated).

    - If project_id provided: requires authentication; creates project-scoped upload with private access.
    - Else: email upload allowed anonymously; creates public resources tied to an indexing run.
    """
    if not files:
        raise ValidationError(
            "At least one PDF file is required",
            details={"field_errors": [{"field": "files", "message": "Required"}]},
            request_id=get_request_id(),
        )

    if len(files) > 10:
        raise ValidationError(
            "Maximum 10 PDF files allowed per upload",
            details={"field_errors": [{"field": "files", "message": "At most 10 files per upload"}]},
            request_id=get_request_id(),
        )

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise ValidationError(
                f"Only PDF files are supported. Found: {file.filename}",
                details={"field_errors": [{"field": "file", "message": "Only PDF files are supported"}]},
                request_id=get_request_id(),
            )
        if file.size and file.size > 50 * 1024 * 1024:
            raise ValidationError(
                f"File {file.filename} must be less than 50MB",
                details={"field_errors": [{"field": "file", "message": "Must be less than 50MB"}]},
                request_id=get_request_id(),
            )

    index_run_id = str(uuid4())

    try:
        db = get_supabase_admin_client()
        from src.services.document_service import DocumentService

        doc_service = DocumentService(db)

        # Anonymous email upload (no project_id)
        if project_id is None:
            if not email:
                raise ValidationError(
                    "email is required for anonymous upload",
                    details={"field_errors": [{"field": "email", "message": "Required for anonymous"}]},
                    request_id=get_request_id(),
                )

            await StorageService().create_storage_structure(
                upload_type=UploadType.EMAIL,
                index_run_id=UUID(index_run_id),
            )

            db.table("indexing_runs").insert(
                {
                    "id": index_run_id,
                    "upload_type": "email",
                    "status": "pending",
                    "created_at": "now()",
                    "access_level": "public",
                }
            ).execute()

            document_ids: list[str] = []
            document_data: list[dict[str, Any]] = []
            for file in files:
                content = await file.read()
                created = await doc_service.create_email_document(
                    file_bytes=content,
                    filename=file.filename,
                    index_run_id=index_run_id,
                    email=email,
                )
                document_ids.append(created["document_id"])
                document_data.append(
                    {
                        "document_id": created["document_id"],
                        "filename": file.filename,
                        "storage_url": created["storage_url"],
                    }
                )

            background_tasks.add_task(
                process_email_upload_async,
                index_run_id=index_run_id,
                email=email,
                document_data=document_data,
            )

            return UploadCreateResponse(
                index_run_id=index_run_id,
                document_count=len(document_ids),
                document_ids=document_ids,
                status="accepted",
                message="Email upload accepted. Processing will start shortly.",
            )

        # Project upload (requires auth)
        if not current_user:
            raise AppError(
                "Authentication required",
                error_code=ErrorCode.AUTHENTICATION_REQUIRED,
                request_id=get_request_id(),
            )

        proj = (
            db.table("projects")
            .select("id")
            .eq("id", str(project_id))
            .eq("user_id", current_user["id"])
            .limit(1)
            .execute()
        )
        if not proj.data:
            raise AppError(
                "Project not found or access denied",
                error_code=ErrorCode.NOT_FOUND,
                request_id=get_request_id(),
            )

        db.table("indexing_runs").insert(
            {
                "id": index_run_id,
                "upload_type": "user_project",
                "status": "pending",
                "project_id": str(project_id),
                "access_level": "private",
            }
        ).execute()

        document_ids: list[str] = []
        for file in files:
            content = await file.read()
            created = await doc_service.create_project_document(
                file_bytes=content,
                filename=file.filename,
                project_id=project_id,  # type: ignore[arg-type]
                user_id=current_user["id"],
                index_run_id=index_run_id,
                file_size=file.size,
            )
            document_ids.append(created["document_id"])

        return UploadCreateResponse(
            index_run_id=index_run_id,
            document_count=len(document_ids),
            document_ids=document_ids,
            status="accepted",
            message="Project upload accepted. Processing will start shortly.",
        )

    except (AppError, StorageError):
        raise
    except Exception as e:  # noqa: BLE001
        raise AppError(
            "Failed to create upload",
            error_code=ErrorCode.INTERNAL_ERROR,
            details={"reason": str(e)},
            request_id=get_request_id(),
        ) from e


@router.post("/projects/{project_id}/documents/multi", response_model=MultiDocumentUploadResponse)
async def upload_project_documents(
    background_tasks: BackgroundTasks,
    project_id: UUID,
    files: list[UploadFile] = File(...),
    current_user: dict[str, Any] = Depends(get_current_user),
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
            raise HTTPException(400, f"Only PDF files are supported. Invalid file: {file.filename}")
        if file.size and file.size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(400, f"File size must be less than 50MB. Invalid file: {file.filename}")

    try:
        # Initialize services
        from src.config.database import get_supabase_client

        db = get_supabase_client()
        storage_service = StorageService()

        # Verify user owns project
        project_result = (
            db.table("projects").select("*").eq("id", str(project_id)).eq("user_id", current_user["id"]).execute()
        )

        if not project_result.data:
            raise AppError(
                "Project not found or access denied",
                error_code=ErrorCode.NOT_FOUND,
                request_id=get_request_id(),
            )

        # project verified by ownership check above

        # Create new index run for multi-document upload
        index_run_result = (
            db.table("indexing_runs")
            .select("*")
            .eq("project_id", str(project_id))
            .order("version", desc=True)
            .limit(1)
            .execute()
        )

        new_version = (index_run_result.data[0]["version"] + 1) if index_run_result.data else 1

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
                storage_path = (
                    f"users/{current_user['id']}/projects/{project_id}/index-runs/{index_run_id}/pdfs/{file.filename}"
                )
                public_url = await storage_service.upload_file(file_path=temp_file_path, storage_path=storage_path)

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
                    "upload_id": str(uuid4()),  # Generate unique upload ID for each document
                }

                doc_result = db.table("documents").insert(document_data_for_db).execute()

                if not doc_result.data:
                    raise AppError(
                        f"Failed to store document record for {file.filename}",
                        error_code=ErrorCode.INTERNAL_ERROR,
                        request_id=get_request_id(),
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

    except StorageError:
        raise
    except AppError:
        raise
    except Exception as e:
        raise AppError(
            "Upload failed",
            error_code=ErrorCode.INTERNAL_ERROR,
            details={"reason": str(e)},
            request_id=get_request_id(),
        )


@router.get("/projects/{project_id}/documents", response_model=DocumentListResponse)
async def get_project_documents(
    project_id: UUID,
    limit: int = 20,
    offset: int = 0,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Get list of documents in a project"""

    try:
        reader = DocumentReadService()
        docs = reader.list_project_documents(current_user["id"], str(project_id), limit=limit, offset=offset)

        # Total count (best-effort)
        from src.config.database import get_supabase_client

        count_result = (
            get_supabase_client()
            .table("documents")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
        total_count = count_result.count or 0

        return DocumentListResponse(documents=docs, total_count=total_count, has_more=(offset + limit) < total_count)

    except AppError:
        raise
    except Exception as e:
        raise AppError(
            "Failed to get documents",
            error_code=ErrorCode.INTERNAL_ERROR,
            details={"reason": str(e)},
            request_id=get_request_id(),
        )


@router.get("/projects/{project_id}/documents/{document_id}", response_model=dict[str, Any])
async def get_project_document(
    project_id: UUID,
    document_id: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Get specific document details"""

    try:
        reader = DocumentReadService()
        document = reader.get_project_document(current_user["id"], str(project_id), str(document_id))

        if not document:
            raise AppError(
                "Document not found or access denied",
                error_code=ErrorCode.NOT_FOUND,
                request_id=get_request_id(),
            )

        # Augment with indexing run status
        from src.config.database import get_supabase_client

        if document.get("index_run_id"):
            idx = (
                get_supabase_client()
                .table("indexing_runs")
                .select("status")
                .eq("id", document["index_run_id"])
                .limit(1)
                .execute()
            )
            if idx.data:
                document["index_run_status"] = idx.data[0]["status"]

        return document

    except AppError:
        raise
    except Exception as e:
        raise AppError(
            "Failed to get document",
            error_code=ErrorCode.INTERNAL_ERROR,
            details={"reason": str(e)},
            request_id=get_request_id(),
        )


# Flat resource endpoints


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    project_id: UUID | None = None,
    index_run_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
):
    """Flat list endpoint for documents.

    For now, requires `project_id` to scope results. Pagination via limit/offset.
    """
    try:
        reader = DocumentReadService()

        # Anonymous listing by index_run_id (email uploads only)
        if not current_user and index_run_id is not None:
            from src.config.database import get_supabase_admin_client

            db = get_supabase_admin_client()
            run_res = db.table("indexing_runs").select("upload_type").eq("id", str(index_run_id)).limit(1).execute()
            if not run_res.data or run_res.data[0].get("upload_type") != "email":
                raise AppError(
                    "Access denied: Authentication required",
                    error_code=ErrorCode.UNAUTHORIZED,
                    request_id=get_request_id(),
                )
            j = (
                db.table("indexing_run_documents")
                .select("document_id")
                .eq("indexing_run_id", str(index_run_id))
                .range(offset, offset + limit - 1)
                .execute()
            )
            document_ids = [row["document_id"] for row in (j.data or [])]
            if not document_ids:
                return DocumentListResponse(documents=[], total_count=0, has_more=False)
            docs_res = db.table("documents").select("*").in_("id", document_ids).execute()
            # Total count
            total_res = (
                db.table("indexing_run_documents")
                .select("document_id", count="exact")
                .eq("indexing_run_id", str(index_run_id))
                .execute()
            )
            total_count = total_res.count or 0
            return DocumentListResponse(
                documents=list(docs_res.data or []), has_more=(offset + limit) < total_count, total_count=total_count
            )

        # project-scoped listing requires authentication and ownership
        if not current_user:
            raise ValidationError(
                "Authentication required",
                details={"reason": "project-scoped listing requires authentication"},
                request_id=get_request_id(),
            )
        docs = reader.list_project_documents(current_user["id"], str(project_id), limit=limit, offset=offset)

        # Total count (best-effort)
        from src.config.database import get_supabase_client

        count_result = (
            get_supabase_client()
            .table("documents")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
        total_count = count_result.count or 0

        return DocumentListResponse(documents=docs, total_count=total_count, has_more=(offset + limit) < total_count)
    except AppError:
        raise
    except Exception as e:  # noqa: BLE001
        raise AppError(
            "Failed to list documents",
            error_code=ErrorCode.INTERNAL_ERROR,
            details={"reason": str(e)},
            request_id=get_request_id(),
        ) from e


@router.get("/documents/{document_id}", response_model=dict[str, Any])
async def get_document(
    document_id: UUID,
    project_id: UUID | None = None,
    index_run_id: UUID | None = None,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
):
    """Flat get endpoint for a single document.

    Modes:
    - Auth + project_id: enforce ownership and return document.
    - Anonymous + index_run_id (email uploads): allow access if the document belongs to the given email-indexing run.
    """
    try:
        reader = DocumentReadService()

        if current_user and project_id is not None:
            document = reader.get_project_document(current_user["id"], str(project_id), str(document_id))
        elif not current_user and index_run_id is not None:
            # Anonymous email-flow: verify document belongs to the email indexing run via junction table
            from src.config.database import get_supabase_admin_client

            db = get_supabase_admin_client()
            # Check that run is email type
            run_res = db.table("indexing_runs").select("upload_type").eq("id", str(index_run_id)).limit(1).execute()
            if not run_res.data or run_res.data[0].get("upload_type") != "email":
                raise AppError(
                    "Access denied: Authentication required",
                    error_code=ErrorCode.UNAUTHORIZED,
                    request_id=get_request_id(),
                )
            # Verify document is linked to the run
            j = (
                db.table("indexing_run_documents")
                .select("document_id")
                .eq("indexing_run_id", str(index_run_id))
                .eq("document_id", str(document_id))
                .limit(1)
                .execute()
            )
            if not j.data:
                document = None
            else:
                d = db.table("documents").select("*").eq("id", str(document_id)).limit(1).execute()
                document = dict(d.data[0]) if d.data else None
        else:
            raise ValidationError(
                "Invalid parameters",
                details={
                    "field_errors": [
                        {
                            "field": "project_id|index_run_id",
                            "message": "Provide project_id (auth) or index_run_id (anon)",
                        }
                    ]
                },
                request_id=get_request_id(),
            )

        if not document:
            raise AppError(
                "Document not found or access denied",
                error_code=ErrorCode.NOT_FOUND,
                request_id=get_request_id(),
            )

        # Augment with indexing run status
        from src.config.database import get_supabase_client

        if document.get("index_run_id"):
            idx = (
                get_supabase_client()
                .table("indexing_runs")
                .select("status")
                .eq("id", document["index_run_id"])
                .limit(1)
                .execute()
            )
            if idx.data:
                document["index_run_status"] = idx.data[0]["status"]

        return document
    except AppError:
        raise
    except Exception as e:  # noqa: BLE001
        raise AppError(
            "Failed to get document",
            error_code=ErrorCode.INTERNAL_ERROR,
            details={"reason": str(e)},
            request_id=get_request_id(),
        ) from e


@router.delete("/projects/{project_id}/documents/{document_id}")
async def delete_project_document(
    project_id: UUID,
    document_id: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
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
            raise AppError(
                "Document not found or access denied",
                error_code=ErrorCode.NOT_FOUND,
                request_id=get_request_id(),
            )

        document = document_result.data[0]

        # Delete from database (cascade will handle related records)
        db.table("documents").delete().eq("id", str(document_id)).execute()

        # TODO: Clean up storage files (implement storage cleanup)

        return {"message": "Document deleted successfully"}

    except AppError:
        raise
    except Exception as e:
        raise AppError(
            "Failed to delete document",
            error_code=ErrorCode.INTERNAL_ERROR,
            details={"reason": str(e)},
            request_id=get_request_id(),
        )


# Background processing functions


@router.get("/documents/by-index-run/{index_run_id}", response_model=list[dict[str, Any]])
async def get_documents_by_index_run(
    index_run_id: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Get all documents for a specific indexing run using the junction table"""
    logger.info(f"🔍 Getting documents for indexing run: {index_run_id}")

    try:
        db = get_supabase_admin_client()
        logger.info("✅ Using admin client")

        # First, get document IDs from the junction table
        logger.info(f"🔗 Querying junction table for indexing_run_id: {index_run_id}")
        junction_result = (
            db.table("indexing_run_documents").select("document_id").eq("indexing_run_id", str(index_run_id)).execute()
        )

        logger.info(f"📊 Junction query result: {junction_result}")
        logger.info(f"📊 Junction data length: {len(junction_result.data) if junction_result.data else 0}")

        if not junction_result.data:
            logger.warning(f"❌ No junction records found for indexing run {index_run_id}")
            return []

        # Extract document IDs
        document_ids = [row["document_id"] for row in junction_result.data]
        logger.info(f"📄 Document IDs found: {document_ids}")

        # Get the actual documents
        logger.info(f"📄 Querying documents table for IDs: {document_ids}")
        documents_result = db.table("documents").select("*").in_("id", document_ids).execute()

        if not documents_result.data:
            logger.warning(f"❌ No documents found for IDs: {document_ids}")
            return []

        # Convert to Document models to trigger computed properties
        logger.info("🔄 Converting raw documents to Document models...")
        from src.models import Document

        document_models = []
        for i, doc_data in enumerate(documents_result.data):
            try:
                logger.info(f"🔄 Creating Document model for document {i + 1}: {doc_data.get('filename')}")
                doc_model = Document(**doc_data)
                logger.info("✅ Document model created successfully")

                # Trigger computed properties
                logger.info(f"🔍 Accessing computed properties for {doc_model.filename}...")
                step_timings = doc_model.step_timings
                total_time = doc_model.total_processing_time
                current_step = doc_model.current_step

                logger.info(f"📊 Computed step_timings: {step_timings}")
                logger.info(f"📊 Computed total_processing_time: {total_time}")
                logger.info(f"📊 Computed current_step: {current_step}")

                # Convert back to dict with computed properties
                doc_dict = doc_data.copy()
                doc_dict["step_timings"] = step_timings
                doc_dict["total_processing_time"] = total_time
                doc_dict["current_step"] = current_step

                document_models.append(doc_dict)
                logger.info(f"✅ Document {i + 1} processed with computed properties")

            except Exception as e:
                logger.error(f"❌ Error creating Document model for document {i + 1}: {e}")
                logger.error(f"❌ Document data: {doc_data}")
                # Fall back to raw data
                document_models.append(doc_data)

        logger.info(f"✅ Returning {len(document_models)} documents with computed properties")
        return document_models

    except Exception as e:
        logger.error(f"❌ Error getting documents for indexing run {index_run_id}: {e}")
        logger.error(f"❌ Error type: {type(e)}")
        import traceback

        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_multi_document_project_upload_async(
    project_id: UUID,
    index_run_id: str,
    user_id: str,
    document_data: list[dict[str, Any]],
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
        success = await orchestrator.process_documents(document_inputs, existing_indexing_run_id=UUID(index_run_id))

        if success:
            logger.info(f"Multi-document project upload processing completed for project {project_id}")
        else:
            logger.error(f"Multi-document project upload processing failed for project {project_id}")

    except Exception as e:
        logger.error(f"Error in multi-document project upload processing for project {project_id}: {e}")


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
            db.table("documents").update({"status": "completed"}).eq("id", document_id).execute()

            logger.info(f"Project document processing completed for {document_id}")
        else:
            # Update document status with error
            db.table("documents").update({"status": "failed"}).eq("id", document_id).execute()

            logger.error(f"Project document processing failed for {document_id}")

    except Exception as e:
        logger.error(f"Error in project document processing for {document_id}: {e}")

        # Update document status with error
        try:
            db = get_supabase_admin_client()
            db.table("documents").update({"status": "failed"}).eq("id", document_id).execute()
        except:
            pass


async def process_email_upload_async(
    index_run_id: str,
    email: str,
    document_data: list[dict[str, Any]],
):
    """Background processing for email uploads using Beam"""

    try:
        logger.info(f"Starting email upload processing for {email} (index run: {index_run_id})")

        # Extract document IDs for Beam
        document_ids = [doc_data["document_id"] for doc_data in document_data]

        # Trigger Beam task for document processing
        try:
            from src.services.beam_service import BeamService

            beam_service = BeamService()
            beam_result = await beam_service.trigger_indexing_pipeline(
                indexing_run_id=index_run_id,
                document_ids=document_ids,
                # No user_id or project_id for email uploads
            )

            if beam_result["status"] == "triggered":
                logger.info(f"Beam task triggered successfully: {beam_result['task_id']}")
            else:
                logger.error(f"Failed to trigger Beam task: {beam_result}")

        except Exception as e:
            logger.error(f"Error triggering Beam task: {e}")

    except Exception as e:
        logger.error(f"Error in email upload processing for {email}: {e}")
