"""Wiki generation API endpoints."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ..pipeline.wiki_generation.orchestrator import WikiGenerationOrchestrator
from ..services.auth_service import get_current_user_optional
from ..services.pipeline_read_service import PipelineReadService
from ..services.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wiki", tags=["wiki"])


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
        # Get orchestrator
        orchestrator = WikiGenerationOrchestrator()

        # Access and metadata for indexing run
        reader = PipelineReadService()
        upload_type = None
        project_id = None
        user_id = None

        if current_user:
            allowed = reader.get_run_for_user(str(index_run_id), current_user["id"])
            if not allowed:
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

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
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

                raise AppError("Indexing run not found", error_code=ErrorCode.NOT_FOUND)
            upload_type = getattr(indexing_run, "upload_type", "user_project")
            project_id = getattr(indexing_run, "project_id", None)
            if upload_type != "email":
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

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
    except Exception as e:
        logger.error(f"Failed to start wiki generation: {e}")
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
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

                raise AppError("Indexing run not found or access denied", error_code=ErrorCode.NOT_FOUND)
            upload_type = allowed.get("upload_type", "user_project")
        else:
            from ..services.pipeline_service import PipelineService

            pipeline_service = PipelineService(use_admin_client=True)
            indexing_run = await pipeline_service.get_indexing_run(str(index_run_id))
            if not indexing_run:
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

                raise AppError("Indexing run not found", error_code=ErrorCode.NOT_FOUND)
            upload_type = getattr(indexing_run, "upload_type", "user_project")
            if upload_type != "email":
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

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
        status = getattr(exc, "status_code", 500)
        code = (
            ErrorCode.NOT_FOUND
            if status == 404
            else ErrorCode.ACCESS_DENIED
            if status == 403
            else ErrorCode.INTERNAL_ERROR
        )
        raise AppError(str(getattr(exc, "detail", "Failed to list wiki runs")), error_code=code) from exc
    except Exception as e:
        logger.error(f"Failed to list wiki runs: {e}")
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
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Wiki run not found", error_code=ErrorCode.NOT_FOUND)

        # For authenticated users, validate ownership
        if current_user:
            if wiki_run.user_id and str(current_user.get("id")) != str(wiki_run.user_id):
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

                raise AppError(
                    "Access denied: This wiki run does not belong to you", error_code=ErrorCode.ACCESS_DENIED
                )

        # For unauthenticated users, only allow access to email uploads
        if not current_user:
            if wiki_run.upload_type != "email":
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

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
    except Exception as e:
        logger.error(f"Failed to get wiki pages: {e}")
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
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Wiki run not found", error_code=ErrorCode.NOT_FOUND)

        # For authenticated users, validate ownership
        if current_user:
            if wiki_run.user_id and str(current_user.get("id")) != str(wiki_run.user_id):
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

                raise AppError(
                    "Access denied: This wiki run does not belong to you", error_code=ErrorCode.ACCESS_DENIED
                )

        # For unauthenticated users, only allow access to email uploads
        if not current_user:
            if wiki_run.upload_type != "email":
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

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
        status = getattr(exc, "status_code", 500)
        code = (
            ErrorCode.NOT_FOUND
            if status == 404
            else ErrorCode.ACCESS_DENIED
            if status == 403
            else ErrorCode.INTERNAL_ERROR
        )
        raise AppError(str(getattr(exc, "detail", "Failed to get wiki page content")), error_code=code) from exc
    except Exception as e:
        logger.error(f"Failed to get wiki page content: {e}")
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
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Wiki run not found", error_code=ErrorCode.NOT_FOUND)

        # For authenticated users, validate ownership
        if current_user:
            if wiki_run.user_id and str(current_user.get("id")) != str(wiki_run.user_id):
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

                raise AppError(
                    "Access denied: This wiki run does not belong to you", error_code=ErrorCode.ACCESS_DENIED
                )

        # For unauthenticated users, only allow access to email uploads
        if not current_user:
            if wiki_run.upload_type != "email":
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

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
    except Exception as e:
        logger.error(f"Failed to get wiki metadata: {e}")
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
            raise HTTPException(status_code=404, detail="Wiki run not found")

        # For authenticated users, validate ownership
        if current_user:
            if wiki_run.user_id and str(current_user.get("id")) != str(wiki_run.user_id):
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: This wiki run does not belong to you",
                )

        # For unauthenticated users, only allow access to email uploads
        if not current_user:
            if wiki_run.upload_type != "email":
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: Authentication required for user project wikis",
                )

        # Delete wiki run
        success = await orchestrator.delete_wiki_run(str(wiki_run_id))

        if not success:
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

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
    except Exception as e:
        logger.error(f"Failed to delete wiki run: {e}")
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
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Wiki run not found", error_code=ErrorCode.NOT_FOUND)

        # For authenticated users, validate ownership
        if current_user:
            if wiki_run.user_id and str(current_user.get("id")) != str(wiki_run.user_id):
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

                raise AppError(
                    "Access denied: This wiki run does not belong to you", error_code=ErrorCode.ACCESS_DENIED
                )

        # For unauthenticated users, only allow access to email uploads
        if not current_user:
            if wiki_run.upload_type != "email":
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

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
    except Exception as e:
        logger.error(f"Failed to get wiki run status: {e}")
        raise AppError("Failed to get wiki run status", error_code=ErrorCode.INTERNAL_ERROR) from e
