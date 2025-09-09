"""Document upload and management API endpoints (v2 flat only)."""

import logging
from typing import Any
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    UploadFile,
)
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel

from src.config.database import get_db_client_for_request, get_supabase_admin_client
from src.middleware.request_id import get_request_id
from src.models.pipeline import UploadType
from src.services.auth_service import get_current_user_optional, optional_security
from src.services.document_read_service import DocumentReadService
from src.services.storage_service import StorageService
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError, StorageError, ValidationError

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Documents"])

# Linter-friendly dependency placeholder
DB_CLIENT_DEP = Depends(get_db_client_for_request)
CURRENT_USER_OPT_DEP = Depends(get_current_user_optional)


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


class FileValidationResult(BaseModel):
    """Result for a single file validation."""
    
    filename: str
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    metadata: dict[str, Any]
    page_analysis: dict[str, Any]
    security: dict[str, Any]
    processing_estimate: dict[str, Any]


class ValidationResponse(BaseModel):
    """Response for batch file validation."""
    
    files: list[FileValidationResult]
    is_valid: bool
    total_pages: int
    total_processing_time_estimate: int
    total_processing_time_minutes: float
    errors: list[str]
    warnings: list[str]


## Legacy /api/email-uploads removed in v2


## Legacy project-scoped single-upload removed in v2


# Validation endpoint for pre-upload checks


@router.post("/uploads/validate", response_model=ValidationResponse)
async def validate_uploads(
    files: list[UploadFile] = File(...),  # noqa: B008
    current_user: dict[str, Any] | None = CURRENT_USER_OPT_DEP,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
):
    """Validate PDF files before upload.
    
    This endpoint performs security, integrity, and processing time estimation
    without storing the files. It helps prevent malicious content and provides
    upfront feedback about processing requirements.
    
    Rate limits:
    - Anonymous: 50 PDFs per hour
    - Authenticated: Unlimited
    """
    from src.middleware.rate_limiter import rate_limit_middleware
    from src.services.pdf_validation_service import PDFValidationService
    from fastapi import Request
    from starlette.datastructures import State
    
    # Create a mock request for rate limiting
    # In production, this would be handled by middleware
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "url": "/api/uploads/validate",
            "headers": [],
            "query_string": b"",
        }
    )
    request._state = State()
    
    # Apply rate limiting
    is_authenticated = current_user is not None
    await rate_limit_middleware(
        request=request,
        file_count=len(files),
        is_authenticated=is_authenticated,
    )
    
    # Initialize validation service
    validator = PDFValidationService()
    
    # Prepare files for validation
    files_to_validate = []
    for file in files:
        if not file.filename:
            raise ValidationError(
                "File must have a filename",
                details={"field_errors": [{"field": "files", "message": "Filename required"}]},
                request_id=get_request_id(),
            )
        
        # Read file content
        content = await file.read()
        files_to_validate.append((file.filename, content))
        
        # Reset file position for potential future reads
        await file.seek(0)
    
    # Validate all files
    try:
        validation_result = await validator.validate_batch(
            files=files_to_validate,
            is_authenticated=is_authenticated,
        )
        
        # Convert to response model
        return ValidationResponse(
            files=[
                FileValidationResult(
                    filename=f["filename"],
                    is_valid=f["is_valid"],
                    errors=f.get("errors", []),
                    warnings=f.get("warnings", []),
                    metadata=f.get("metadata", {}),
                    page_analysis=f.get("page_analysis", {}),
                    security=f.get("security", {}),
                    processing_estimate=f.get("processing_estimate", {}),
                )
                for f in validation_result["files"]
            ],
            is_valid=validation_result["is_valid"],
            total_pages=validation_result.get("total_pages", 0),
            total_processing_time_estimate=validation_result.get("total_processing_time_estimate", 0),
            total_processing_time_minutes=validation_result.get("total_processing_time_minutes", 0.0),
            errors=validation_result.get("errors", []),
            warnings=validation_result.get("warnings", []),
        )
        
    except Exception as e:  # noqa: BLE001
        logger.error(f"Validation error: {e}")
        raise AppError(
            "Failed to validate files",
            error_code=ErrorCode.INTERNAL_ERROR,
            details={"reason": str(e)},
            request_id=get_request_id(),
        ) from e


# Flat unified upload endpoint (anonymous or authenticated)


@router.post("/uploads", response_model=UploadCreateResponse)
async def create_upload(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),  # noqa: B008
    email: str | None = Form(None),  # noqa: B008
    project_id: UUID | None = Form(None),  # noqa: B008
    email_notifications_enabled: bool = Form(True),  # noqa: B008
    current_user: dict[str, Any] | None = CURRENT_USER_OPT_DEP,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
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

    # Different limits for anonymous vs authenticated uploads
    max_files_limit = 5 if project_id is None else 20  # 5 for email uploads, 20 for project uploads
    if len(files) > max_files_limit:
        upload_type = "anonymous" if project_id is None else "authenticated"
        raise ValidationError(
            f"Maximum {max_files_limit} PDF files allowed per {upload_type} upload",
            details={"field_errors": [{"field": "files", "message": f"At most {max_files_limit} files per {upload_type} upload"}]},
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
        from src.services.document_service import DocumentService

        # Anonymous email upload (no project_id)
        if project_id is None:
            # Use admin for anonymous/email flow
            db = get_supabase_admin_client()
            doc_service = DocumentService(db)
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
                    "email": email,
                    "email_notifications_enabled": email_notifications_enabled,
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
                process_upload_async,
                index_run_id=index_run_id,
                email=email,
                document_data=document_data,
                user_id=None,
                project_id=None,
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

        # Use anon client for user-scoped project flow
        from src.config.database import get_supabase_client

        db = get_supabase_client()

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
                "user_id": current_user["id"],
                "project_id": str(project_id),
                "access_level": "private",
                "email_notifications_enabled": email_notifications_enabled,
            }
        ).execute()

        document_ids: list[str] = []
        for file in files:
            content = await file.read()
            # Reuse project-scoped doc service with anon client
            created = await DocumentService(db).create_project_document(
                file_bytes=content,
                filename=file.filename,
                project_id=project_id,  # type: ignore[arg-type]
                user_id=current_user["id"],
                index_run_id=index_run_id,
                file_size=file.size,
            )
            document_ids.append(created["document_id"])

        # Trigger background processing for project uploads
        background_tasks.add_task(
            process_upload_async,
            index_run_id=index_run_id,
            email=None,
            document_data=document_ids,  # Pass the document IDs directly
            user_id=current_user["id"],
            project_id=str(project_id),
        )

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


## Legacy project-scoped multi-upload removed in v2


## Legacy project-scoped list removed in v2


## Legacy project-scoped get removed in v2


# Flat resource endpoints


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    project_id: UUID | None = None,
    index_run_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
    current_user: dict[str, Any] | None = CURRENT_USER_OPT_DEP,
    db_client=DB_CLIENT_DEP,
):
    """Flat list endpoint for documents.

    For now, requires `project_id` to scope results. Pagination via limit/offset.
    """
    try:
        reader = DocumentReadService(client=db_client)

        # Anonymous listing by index_run_id (email uploads only)
        if not current_user and index_run_id is not None:
            from src.config.database import get_supabase_admin_client

            db = get_supabase_admin_client()
            run_res = db.table("indexing_runs").select("upload_type").eq("id", str(index_run_id)).limit(1).execute()
            if not run_res.data or run_res.data[0].get("upload_type") != "email":
                raise AppError(
                    "Access denied: Authentication required",
                    error_code=ErrorCode.ACCESS_DENIED,
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
    current_user: dict[str, Any] | None = CURRENT_USER_OPT_DEP,
    db_client=DB_CLIENT_DEP,
):
    """Flat get endpoint for a single document.

    Modes:
    - Auth + project_id: enforce ownership and return document.
    - Anonymous + index_run_id (email uploads): allow access if the document belongs to the given email-indexing run.
    """
    try:
        reader = DocumentReadService(client=db_client)

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
                    error_code=ErrorCode.ACCESS_DENIED,
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


## Legacy project-scoped delete removed in v2


## Background processing helpers for project uploads removed in v2


@router.get("/documents/{document_id}/pdf")
async def get_document_pdf(
    document_id: UUID,
    index_run_id: UUID | None = None,
    current_user: dict[str, Any] | None = CURRENT_USER_OPT_DEP,
    db_client=DB_CLIENT_DEP,
):
    """Get signed URL for document PDF.
    
    Returns a signed URL to access the PDF file directly from Supabase storage.
    Access control follows the same rules as get_document endpoint.
    """
    try:
        from src.config.database import get_supabase_admin_client, get_supabase_client
        
        # First, verify access to the document using same logic as get_document
        if current_user:
            # Authenticated user - check project ownership
            db = get_supabase_client()
            doc_result = (
                db.table("documents")
                .select("file_path, filename, project_id, index_run_id")
                .eq("id", str(document_id))
                .limit(1)
                .execute()
            )
            
            if not doc_result.data:
                raise AppError(
                    "Document not found",
                    error_code=ErrorCode.NOT_FOUND,
                    request_id=get_request_id(),
                )
            
            doc = doc_result.data[0]
            
            # Verify project ownership if document has project_id
            if doc.get("project_id"):
                proj = (
                    db.table("projects")
                    .select("id")
                    .eq("id", doc["project_id"])
                    .eq("user_id", current_user["id"])
                    .limit(1)
                    .execute()
                )
                if not proj.data:
                    raise AppError(
                        "Access denied",
                        error_code=ErrorCode.ACCESS_DENIED,
                        request_id=get_request_id(),
                    )
        
        elif index_run_id:
            # Anonymous access - verify document belongs to email indexing run
            db = get_supabase_admin_client()
            
            # Check that run is email type
            run_res = db.table("indexing_runs").select("upload_type").eq("id", str(index_run_id)).limit(1).execute()
            if not run_res.data or run_res.data[0].get("upload_type") != "email":
                raise AppError(
                    "Access denied: Authentication required",
                    error_code=ErrorCode.ACCESS_DENIED,
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
                raise AppError(
                    "Document not found or access denied",
                    error_code=ErrorCode.NOT_FOUND,
                    request_id=get_request_id(),
                )
            
            # Get document details
            doc_result = (
                db.table("documents")
                .select("file_path, filename, index_run_id")
                .eq("id", str(document_id))
                .limit(1)
                .execute()
            )
            
            if not doc_result.data:
                raise AppError(
                    "Document not found",
                    error_code=ErrorCode.NOT_FOUND,
                    request_id=get_request_id(),
                )
            
            doc = doc_result.data[0]
        
        else:
            raise ValidationError(
                "Invalid parameters",
                details={
                    "field_errors": [
                        {
                            "field": "index_run_id",
                            "message": "Either authentication or index_run_id required",
                        }
                    ]
                },
                request_id=get_request_id(),
            )
        
        # Generate storage path based on document type and location
        # For email uploads: email-uploads/index-runs/{index_run_id}/pdfs/{filename}
        # For project uploads: users/{user_id}/projects/{project_id}/index-runs/{index_run_id}/pdfs/{filename}
        
        filename = doc.get("filename")
        doc_index_run_id = doc.get("index_run_id")
        
        if not filename:
            logger.error(f"No filename found for document {document_id}")
            raise AppError(
                "Document PDF not found",
                error_code=ErrorCode.NOT_FOUND,
                details={"reason": "No filename for document", "document_id": str(document_id)},
                request_id=get_request_id(),
            )
            
        # Construct storage path based on document type
        if current_user and doc.get("project_id"):
            # Authenticated user project upload
            storage_path = f"users/{current_user['id']}/projects/{doc['project_id']}/index-runs/{doc_index_run_id}/pdfs/{filename}"
        else:
            # Anonymous email upload - use the index_run_id from parameter or document
            run_id = index_run_id if index_run_id else doc_index_run_id
            storage_path = f"email-uploads/index-runs/{run_id}/pdfs/{filename}"
        
        logger.info(f"Generating signed URL for document {document_id} with path: {storage_path}")
        
        # Use admin client to create signed URL
        admin_db = get_supabase_admin_client()
        
        # Generate a signed URL valid for 1 hour
        try:
            response = admin_db.storage.from_("pipeline-assets").create_signed_url(
                path=storage_path,
                expires_in=3600  # 1 hour
            )
            
            logger.info(f"Supabase storage response: {response}")
            
            if not response or "signedURL" not in response:
                logger.error(f"Invalid response from Supabase storage: {response}")
                raise AppError(
                    "Failed to generate PDF URL",
                    error_code=ErrorCode.INTERNAL_ERROR,
                    details={"reason": "Could not create signed URL", "storage_path": storage_path},
                    request_id=get_request_id(),
                )
            
            return {
                "url": response["signedURL"],
                "filename": doc.get("filename", "document.pdf"),
                "expires_in": 3600
            }
        except Exception as storage_error:
            logger.error(f"Storage error for document {document_id}: {storage_error}")
            raise AppError(
                "Failed to generate PDF URL",
                error_code=ErrorCode.INTERNAL_ERROR,
                details={"reason": str(storage_error), "storage_path": storage_path},
                request_id=get_request_id(),
            ) from storage_error
        
    except (AppError, ValidationError):
        raise
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error getting document PDF: {e}")
        raise AppError(
            "Failed to get document PDF",
            error_code=ErrorCode.INTERNAL_ERROR,
            details={"reason": str(e)},
            request_id=get_request_id(),
        ) from e


async def process_upload_async(
    index_run_id: str,
    email: str | None = None,
    document_data: list[dict[str, Any]] | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
):
    """Background processing for uploads (email and project) using Beam"""

    try:
        upload_type = "email" if email else "project"
        identifier = email if email else f"project:{project_id}"
        logger.info(f"Starting {upload_type} upload processing for {identifier} (index run: {index_run_id})")

        # Extract document IDs for Beam
        if document_data and len(document_data) > 0:
            # Check if document_data is list of IDs (project uploads) or list of dicts (email uploads)
            if isinstance(document_data[0], str):
                # Project uploads: document_data is list of document IDs
                document_ids = document_data
            else:
                # Email uploads: document_data is list of document metadata dicts
                document_ids = [doc_data["document_id"] for doc_data in document_data]
        else:
            # Fallback: get document IDs from indexing run
            from src.config.database import get_supabase_admin_client
            db = get_supabase_admin_client()
            docs_result = (
                db.table("indexing_run_documents")
                .select("document_id")
                .eq("indexing_run_id", index_run_id)
                .execute()
            )
            document_ids = [doc["document_id"] for doc in (docs_result.data or [])]

        # Trigger Beam task for document processing
        try:
            from src.services.beam_service import BeamService

            beam_service = BeamService()
            beam_result = await beam_service.trigger_indexing_pipeline(
                indexing_run_id=index_run_id,
                document_ids=document_ids,
                user_id=user_id,
                project_id=project_id,
            )

            if beam_result["status"] == "triggered":
                logger.info(f"Beam task triggered successfully: {beam_result['task_id']}")
            else:
                logger.error(f"Failed to trigger Beam task: {beam_result}")

        except Exception as e:
            logger.error(f"Error triggering Beam task: {e}")

    except Exception as e:
        logger.error(f"Error in {upload_type} upload processing for {identifier}: {e}")
