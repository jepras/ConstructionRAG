"""Wiki generation API endpoints."""

import logging
import os
import traceback
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from pydantic import BaseModel

from ..config.database import get_supabase_client, get_supabase_admin_client
from ..models.pipeline import UploadType
from ..pipeline.wiki_generation.orchestrator import WikiGenerationOrchestrator
from ..services.auth_service import get_current_user_optional
from ..services.pipeline_read_service import PipelineReadService
from ..services.pipeline_service import PipelineService
from ..services.storage_service import StorageService
from ..shared.errors import ErrorCode
from ..utils.exceptions import AppError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wiki", tags=["Wiki"])


class WebhookRequest(BaseModel):
    indexing_run_id: str

@router.post("/internal/webhook", response_model=dict[str, Any])
async def trigger_wiki_from_beam(
    request: WebhookRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """Internal webhook endpoint for Beam to trigger wiki generation after indexing completion.
    
    This endpoint is called by Beam after indexing runs complete, eliminating the need
    to pass JWT tokens to external services. The endpoint fetches the indexing run
    details and initiates wiki generation with proper authentication context.
    """
    try:
        # Verify API key
        expected_api_key = os.getenv("BEAM_WEBHOOK_API_KEY")
        if not expected_api_key:
            logger.error("BEAM_WEBHOOK_API_KEY environment variable not configured")
            raise AppError("Webhook authentication not configured", error_code=ErrorCode.INTERNAL_ERROR)
        
        if x_api_key != expected_api_key:
            logger.warning(f"Invalid API key provided for webhook: {x_api_key[:10]}...")
            raise AppError("Invalid API key", error_code=ErrorCode.UNAUTHORIZED)
        
        indexing_run_id = request.indexing_run_id
        
        # Fetch indexing run details using admin client
        admin_db = get_supabase_admin_client()
        run_result = admin_db.table("indexing_runs").select("*").eq("id", str(indexing_run_id)).execute()
        
        if not run_result.data:
            logger.error(f"Indexing run {indexing_run_id} not found")
            raise AppError("Indexing run not found", error_code=ErrorCode.NOT_FOUND)
        
        run_data = run_result.data[0]
        upload_type = run_data.get("upload_type")
        user_id = run_data.get("user_id")
        project_id = run_data.get("project_id")
        
        # Initialize orchestrator based on upload type
        if upload_type == "email":
            # Email uploads: Use admin client (no user context needed)
            orchestrator = WikiGenerationOrchestrator(db_client=None)
        else:
            # User project uploads: Use admin client but pass user context
            orchestrator = WikiGenerationOrchestrator(db_client=None)
        
        # Start wiki generation in background
        background_tasks.add_task(
            orchestrator.run_pipeline,
            str(indexing_run_id),
            user_id,
            project_id,
            upload_type,
        )
        
        return {
            "message": "Wiki generation started via webhook",
            "indexing_run_id": str(indexing_run_id),
            "upload_type": upload_type,
            "status": "started",
        }
        
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {type(e).__name__}: {e}")
        raise AppError("Failed to process webhook", error_code=ErrorCode.INTERNAL_ERROR) from e


async def get_optional_user(
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> dict[str, Any] | None:
    """Optional authentication for wiki endpoints"""
    return current_user


@router.post("/runs", response_model=dict[str, Any])
async def create_wiki_generation_run(
    index_run_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: dict[str, Any] | None = Depends(get_optional_user),
):
    """Create and start a new wiki generation run for an indexing run."""
    try:
        logger.info(f"Starting wiki generation for index_run_id: {index_run_id}")
        
        # Get orchestrator (always use admin client for pipeline execution)
        orchestrator = WikiGenerationOrchestrator()

        # Access and metadata for indexing run
        # CRITICAL: Use authenticated client for PipelineReadService to pass JWT context for RLS
        db_client = get_supabase_client() if current_user else None
        reader = PipelineReadService(client=db_client)
        
        upload_type = None
        project_id = None
        user_id = None

        if current_user:
            # Authenticated flow - check access
            allowed = reader.get_run_for_user(str(index_run_id), current_user["id"])
                
            if not allowed:
                raise AppError("Indexing run not found or access denied", error_code=ErrorCode.NOT_FOUND)
            upload_type = allowed.get("upload_type", "user_project")
            project_id = allowed.get("project_id")
            user_id = current_user["id"]
        else:
            # Anonymous: fetch minimal run info via orchestrator/pipeline (email-only allowed)
            from ..services.pipeline_service import PipelineService

            pipeline_service = PipelineService(use_admin_client=True)
            indexing_run = await pipeline_service.get_indexing_run(str(index_run_id))
                
            if not indexing_run:
                raise AppError("Indexing run not found", error_code=ErrorCode.NOT_FOUND)
            upload_type = getattr(indexing_run, "upload_type", "user_project")
            project_id = getattr(indexing_run, "project_id", None)
            
            if upload_type != "email":
                raise AppError(
                    "Access denied: Authentication required for user project wikis",
                    error_code=ErrorCode.ACCESS_DENIED,
                )

        # Start wiki generation in background
        background_tasks.add_task(
            orchestrator.run_pipeline,
            str(index_run_id),
            user_id,
            project_id,
            upload_type,
        )
        return {
            "message": "Wiki generation started",
            "index_run_id": str(index_run_id),
            "status": "started",
        }

    except HTTPException as exc:
        status = getattr(exc, "status_code", 500)
        code = (
            ErrorCode.NOT_FOUND
            if status == 404
            else ErrorCode.ACCESS_DENIED
            if status == 403
            else ErrorCode.INTERNAL_ERROR
        )
        raise AppError(str(getattr(exc, "detail", "Failed to start wiki generation")), error_code=code) from exc
    except AppError:
        # Re-raise AppError as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in wiki generation: {type(e).__name__}: {e}")
        raise AppError("Failed to start wiki generation", error_code=ErrorCode.INTERNAL_ERROR) from e


@router.get("/runs/{index_run_id}", response_model=list[dict[str, Any]])
async def list_wiki_runs(
    index_run_id: UUID,
    current_user: dict[str, Any] | None = Depends(get_optional_user),
):
    """List all wiki generation runs for an indexing run."""
    try:
        orchestrator = WikiGenerationOrchestrator()

        # Access and upload type
        reader = PipelineReadService()
        upload_type = None

        if current_user:
            allowed = reader.get_run_for_user(str(index_run_id), current_user["id"])
            if not allowed:
                raise AppError("Indexing run not found or access denied", error_code=ErrorCode.NOT_FOUND)
            upload_type = allowed.get("upload_type", "user_project")
        else:
            from ..services.pipeline_service import PipelineService

            pipeline_service = PipelineService(use_admin_client=True)
            indexing_run = await pipeline_service.get_indexing_run(str(index_run_id))
            if not indexing_run:
                raise AppError("Indexing run not found", error_code=ErrorCode.NOT_FOUND)
            upload_type = getattr(indexing_run, "upload_type", "user_project")
            if upload_type != "email":
                raise AppError(
                    "Access denied: Authentication required for user project wikis",
                    error_code=ErrorCode.ACCESS_DENIED,
                )

        wiki_runs = await orchestrator.list_wiki_runs(str(index_run_id))

        return [
            {
                "id": str(wiki_run.id),
                "indexing_run_id": str(wiki_run.indexing_run_id),
                "upload_type": wiki_run.upload_type,
                "user_id": str(wiki_run.user_id) if wiki_run.user_id else None,
                "project_id": str(wiki_run.project_id) if wiki_run.project_id else None,
                "status": wiki_run.status,
                "created_at": (wiki_run.created_at.isoformat() if wiki_run.created_at else None),
                "completed_at": (wiki_run.completed_at.isoformat() if wiki_run.completed_at else None),
                "error_message": wiki_run.error_message,
            }
            for wiki_run in wiki_runs
        ]

    except HTTPException as exc:
        logger.error(f"HTTPException in list_wiki_runs: {exc}")
        status = getattr(exc, "status_code", 500)
        code = (
            ErrorCode.NOT_FOUND
            if status == 404
            else ErrorCode.ACCESS_DENIED
            if status == 403
            else ErrorCode.INTERNAL_ERROR
        )
        raise AppError(str(getattr(exc, "detail", "Failed to list wiki runs")), error_code=code) from exc
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in list_wiki_runs: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise AppError("Failed to list wiki runs", error_code=ErrorCode.INTERNAL_ERROR) from e


@router.get("/runs/{wiki_run_id}/pages", response_model=dict[str, Any])
async def get_wiki_pages(
    wiki_run_id: UUID,
    current_user: dict[str, Any] | None = Depends(get_optional_user),
):
    """Get list of pages and metadata for a specific wiki run."""
    try:
        orchestrator = WikiGenerationOrchestrator()

        # Get wiki run details
        wiki_run = await orchestrator.get_wiki_run(str(wiki_run_id))
        if not wiki_run:
            raise AppError("Wiki run not found", error_code=ErrorCode.NOT_FOUND)

        # For authenticated users, validate ownership
        if current_user:
            if wiki_run.user_id and str(current_user.get("id")) != str(wiki_run.user_id):
                raise AppError(
                    "Access denied: This wiki run does not belong to you", error_code=ErrorCode.ACCESS_DENIED
                )

        # For unauthenticated users, only allow access to email uploads
        if not current_user:
            if wiki_run.upload_type != "email":
                raise AppError(
                    "Access denied: Authentication required for user project wikis",
                    error_code=ErrorCode.ACCESS_DENIED,
                )

        # Get pages from database (pages_metadata column)
        pages = []
        if wiki_run.pages_metadata:
            for page_meta in wiki_run.pages_metadata:
                pages.append(
                    {
                        "filename": page_meta.filename,
                        "title": page_meta.title,
                        "size": page_meta.file_size,
                        "storage_path": page_meta.storage_path,
                        "storage_url": page_meta.storage_url,
                        "order": page_meta.order,
                    }
                )

        return {
            "wiki_run_id": str(wiki_run_id),
            "status": wiki_run.status,
            "pages": pages,
            "total_pages": len(pages),
        }

    except HTTPException as exc:
        status = getattr(exc, "status_code", 500)
        code = (
            ErrorCode.NOT_FOUND
            if status == 404
            else ErrorCode.ACCESS_DENIED
            if status == 403
            else ErrorCode.INTERNAL_ERROR
        )
        raise AppError(str(getattr(exc, "detail", "Failed to get wiki pages")), error_code=code) from exc
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_wiki_pages: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise AppError("Failed to get wiki pages", error_code=ErrorCode.INTERNAL_ERROR) from e


@router.get("/runs/{wiki_run_id}/pages/{page_name}", response_model=dict[str, Any])
async def get_wiki_page_content(
    wiki_run_id: UUID,
    page_name: str,
    current_user: dict[str, Any] | None = Depends(get_optional_user),
):
    """Get the content of a specific wiki page."""
    try:
        orchestrator = WikiGenerationOrchestrator()
        storage_service = StorageService()

        # Get wiki run details
        wiki_run = await orchestrator.get_wiki_run(str(wiki_run_id))
        if not wiki_run:
            raise AppError("Wiki run not found", error_code=ErrorCode.NOT_FOUND)

        # For authenticated users, validate ownership
        if current_user:
            if wiki_run.user_id and str(current_user.get("id")) != str(wiki_run.user_id):
                raise AppError(
                    "Access denied: This wiki run does not belong to you", error_code=ErrorCode.ACCESS_DENIED
                )

        # For unauthenticated users, only allow access to email uploads
        if not current_user:
            if wiki_run.upload_type != "email":
                raise AppError(
                    "Access denied: Authentication required for user project wikis",
                    error_code=ErrorCode.ACCESS_DENIED,
                )

        # Ensure page_name ends with .md
        if not page_name.endswith(".md"):
            page_name += ".md"

        # Get page content from storage
        content = await storage_service.get_wiki_page_content(
            wiki_run_id=str(wiki_run_id),
            filename=page_name,
            upload_type=wiki_run.upload_type,
            user_id=wiki_run.user_id,
            project_id=wiki_run.project_id,
            index_run_id=wiki_run.indexing_run_id,
        )

        return {
            "wiki_run_id": str(wiki_run_id),
            "page_name": page_name,
            "content": content,
            "content_length": len(content),
        }

    except HTTPException as exc:
        from ..shared.errors import ErrorCode
        from ..utils.exceptions import AppError
        
        status = getattr(exc, "status_code", 500)
        code = (
            ErrorCode.NOT_FOUND
            if status == 404
            else ErrorCode.ACCESS_DENIED
            if status == 403
            else ErrorCode.INTERNAL_ERROR
        )
        raise AppError(str(getattr(exc, "detail", "Failed to get wiki page content")), error_code=code) from exc
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_wiki_page_content: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise AppError("Failed to get wiki page content", error_code=ErrorCode.INTERNAL_ERROR) from e


@router.get("/runs/{wiki_run_id}/metadata", response_model=dict[str, Any])
async def get_wiki_metadata(
    wiki_run_id: UUID,
    current_user: dict[str, Any] | None = Depends(get_optional_user),
):
    """Get metadata for a specific wiki run."""
    try:
        orchestrator = WikiGenerationOrchestrator()

        # Get wiki run details
        wiki_run = await orchestrator.get_wiki_run(str(wiki_run_id))
        if not wiki_run:
            raise AppError("Wiki run not found", error_code=ErrorCode.NOT_FOUND)

        # For authenticated users, validate ownership
        if current_user:
            if wiki_run.user_id and str(current_user.get("id")) != str(wiki_run.user_id):
                raise AppError(
                    "Access denied: This wiki run does not belong to you", error_code=ErrorCode.ACCESS_DENIED
                )

        # For unauthenticated users, only allow access to email uploads
        if not current_user:
            if wiki_run.upload_type != "email":
                raise AppError(
                    "Access denied: Authentication required for user project wikis",
                    error_code=ErrorCode.ACCESS_DENIED,
                )

        # Get metadata from database (wiki_structure and pages_metadata columns)
        metadata = {
            "wiki_structure": wiki_run.wiki_structure,
            "pages_metadata": wiki_run.pages_metadata,
            "generated_at": (wiki_run.completed_at.isoformat() if wiki_run.completed_at else None),
        }

        return {
            "wiki_run_id": str(wiki_run_id),
            "metadata": metadata,
        }

    except HTTPException as exc:
        status = getattr(exc, "status_code", 500)
        code = (
            ErrorCode.NOT_FOUND
            if status == 404
            else ErrorCode.ACCESS_DENIED
            if status == 403
            else ErrorCode.INTERNAL_ERROR
        )
        raise AppError(str(getattr(exc, "detail", "Failed to get wiki metadata")), error_code=code) from exc
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_wiki_metadata: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise AppError("Failed to get wiki metadata", error_code=ErrorCode.INTERNAL_ERROR) from e


@router.delete("/runs/{wiki_run_id}", response_model=dict[str, Any])
async def delete_wiki_run(
    wiki_run_id: UUID,
    current_user: dict[str, Any] | None = Depends(get_optional_user),
):
    """Delete a wiki generation run and its associated files."""
    try:
        orchestrator = WikiGenerationOrchestrator()

        # Get wiki run details
        wiki_run = await orchestrator.get_wiki_run(str(wiki_run_id))
        if not wiki_run:
            raise AppError("Wiki run not found", error_code=ErrorCode.NOT_FOUND)

        # For authenticated users, validate ownership
        if current_user:
            if wiki_run.user_id and str(current_user.get("id")) != str(wiki_run.user_id):
                raise AppError(
                    "Access denied: This wiki run does not belong to you",
                    error_code=ErrorCode.ACCESS_DENIED,
                )

        # For unauthenticated users, only allow access to email uploads
        if not current_user:
            if wiki_run.upload_type != "email":
                raise AppError(
                    "Access denied: Authentication required for user project wikis",
                    error_code=ErrorCode.ACCESS_DENIED,
                )

        # Delete wiki run
        success = await orchestrator.delete_wiki_run(str(wiki_run_id))

        if not success:
            raise AppError("Wiki run not found", error_code=ErrorCode.NOT_FOUND)

        return {
            "message": "Wiki run deleted successfully",
            "wiki_run_id": str(wiki_run_id),
        }

    except HTTPException as exc:
        status = getattr(exc, "status_code", 500)
        code = (
            ErrorCode.NOT_FOUND
            if status == 404
            else ErrorCode.ACCESS_DENIED
            if status == 403
            else ErrorCode.INTERNAL_ERROR
        )
        raise AppError(str(getattr(exc, "detail", "Failed to delete wiki run")), error_code=code) from exc
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in delete_wiki_run: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise AppError("Failed to delete wiki run", error_code=ErrorCode.INTERNAL_ERROR) from e


@router.get("/runs/{wiki_run_id}/status", response_model=dict[str, Any])
async def get_wiki_run_status(
    wiki_run_id: UUID,
    current_user: dict[str, Any] | None = Depends(get_optional_user),
):
    """Get the status of a wiki generation run."""
    try:
        orchestrator = WikiGenerationOrchestrator()

        wiki_run = await orchestrator.get_wiki_run(str(wiki_run_id))
        if not wiki_run:
            raise AppError("Wiki run not found", error_code=ErrorCode.NOT_FOUND)

        # For authenticated users, validate ownership
        if current_user:
            if wiki_run.user_id and str(current_user.get("id")) != str(wiki_run.user_id):
                raise AppError(
                    "Access denied: This wiki run does not belong to you", error_code=ErrorCode.ACCESS_DENIED
                )

        # For unauthenticated users, only allow access to email uploads
        if not current_user:
            if wiki_run.upload_type != "email":
                raise AppError(
                    "Access denied: Authentication required for user project wikis",
                    error_code=ErrorCode.ACCESS_DENIED,
                )

        return {
            "id": str(wiki_run.id),
            "indexing_run_id": str(wiki_run.indexing_run_id),
            "status": wiki_run.status,
            "created_at": (wiki_run.created_at.isoformat() if wiki_run.created_at else None),
            "completed_at": (wiki_run.completed_at.isoformat() if wiki_run.completed_at else None),
            "error_message": wiki_run.error_message,
        }

    except HTTPException as exc:
        status = getattr(exc, "status_code", 500)
        code = (
            ErrorCode.NOT_FOUND
            if status == 404
            else ErrorCode.ACCESS_DENIED
            if status == 403
            else ErrorCode.INTERNAL_ERROR
        )
        raise AppError(str(getattr(exc, "detail", "Failed to get wiki run status")), error_code=code) from exc
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_wiki_run_status: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise AppError("Failed to get wiki run status", error_code=ErrorCode.INTERNAL_ERROR) from e
