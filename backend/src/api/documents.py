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


## Legacy /api/email-uploads removed in v2


## Legacy project-scoped single-upload removed in v2


# Flat unified upload endpoint (anonymous or authenticated)


@router.post("/uploads", response_model=UploadCreateResponse)
async def create_upload(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),  # noqa: B008
    email: str | None = Form(None),  # noqa: B008
    project_id: UUID | None = Form(None),  # noqa: B008
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
                auth_token=None,  # Email uploads are anonymous
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
                "project_id": str(project_id),
                "access_level": "private",
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

        # Extract JWT token for authenticated API calls
        auth_token = credentials.credentials if credentials else None
        
        # Trigger background processing for project uploads
        background_tasks.add_task(
            process_upload_async,
            index_run_id=index_run_id,
            email=None,
            document_data=document_ids,  # Pass the document IDs directly
            user_id=current_user["id"],
            project_id=str(project_id),
            auth_token=auth_token,
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


## Legacy project-scoped delete removed in v2


## Background processing helpers for project uploads removed in v2


async def process_upload_async(
    index_run_id: str,
    email: str | None = None,
    document_data: list[dict[str, Any]] | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
    auth_token: str | None = None,
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
                auth_token=auth_token,
            )

            if beam_result["status"] == "triggered":
                logger.info(f"Beam task triggered successfully: {beam_result['task_id']}")
            else:
                logger.error(f"Failed to trigger Beam task: {beam_result}")

        except Exception as e:
            logger.error(f"Error triggering Beam task: {e}")

    except Exception as e:
        logger.error(f"Error in {upload_type} upload processing for {identifier}: {e}")
