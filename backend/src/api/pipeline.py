"""Pipeline API endpoints for managing indexing and query pipelines."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

try:
    pass
except Exception:
    raise

from ..config.database import get_supabase_client
from ..services.auth_service import get_current_user_optional
from ..services.pipeline_read_service import PipelineReadService
from ..services.pipeline_service import PipelineService

# Indexing orchestrator only available on Beam, not FastAPI
try:
    from ..pipeline.indexing.orchestrator import get_indexing_orchestrator

    INDEXING_AVAILABLE = True
except ImportError:
    INDEXING_AVAILABLE = False
    get_indexing_orchestrator = None
    logging.warning("Indexing orchestrator not available - indexing runs on Beam only")

try:
    pass
except Exception:
    raise

try:
    from .auth import get_current_user
except Exception:
    raise

try:
    from ..shared.errors import ErrorCode
    from ..utils.exceptions import AppError, DatabaseError
except Exception:
    raise

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])
flat_router = APIRouter(prefix="/api", tags=["IndexingRuns"])


@router.post("/indexing/start", response_model=dict[str, Any])
async def start_indexing_pipeline(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Indexing is Beam-only; legacy local start is disabled."""
    from ..shared.errors import ErrorCode
    from ..utils.exceptions import AppError

    raise AppError(
        "Indexing runs on Beam only. Use /api/uploads to create runs.",
        error_code=ErrorCode.CONFIGURATION_ERROR,
        status_code=501,
    )


@router.get("/indexing/runs", response_model=list[dict[str, Any]])
async def get_all_indexing_runs(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Get recent indexing runs for the current user's projects."""
    try:
        reader = PipelineReadService()
        runs = reader.list_recent_runs_for_user(current_user["id"], limit=5)
        return runs
    except HTTPException as exc:
        code = ErrorCode.NOT_FOUND if getattr(exc, "status_code", 500) == 404 else ErrorCode.INTERNAL_ERROR
        raise AppError(str(getattr(exc, "detail", "Failed to get indexing runs")), error_code=code) from exc
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to get all indexing runs: {e}")
        raise AppError("Failed to get indexing runs", error_code=ErrorCode.INTERNAL_ERROR) from e


@router.get("/indexing/runs/{document_id}", response_model=list[dict[str, Any]])
async def get_indexing_runs(
    document_id: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(lambda: PipelineService()),
):
    """Get all indexing runs for a document."""
    try:
        # Access check: ensure document belongs to current user
        db = get_supabase_client()
        doc_res = (
            db.table("documents")
            .select("id")
            .eq("id", str(document_id))
            .eq("user_id", current_user["id"])
            .limit(1)
            .execute()
        )
        if not doc_res.data:
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Document not found or access denied", error_code=ErrorCode.NOT_FOUND)

        runs = await pipeline_service.get_document_indexing_runs(document_id)
        return [
            {
                "id": str(run.id),
                "document_id": str(run.document_id),
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": (run.completed_at.isoformat() if run.completed_at else None),
                "error_message": run.error_message,
                "step_results": run.step_results,
            }
            for run in runs
        ]

    except HTTPException as exc:
        code = ErrorCode.NOT_FOUND if getattr(exc, "status_code", 500) == 404 else ErrorCode.INTERNAL_ERROR
        raise AppError(str(getattr(exc, "detail", "Failed to get indexing runs")), error_code=code) from exc
    except DatabaseError as e:
        logger.error(f"Database error getting indexing runs: {e}")
        raise AppError(str(e), error_code=ErrorCode.DATABASE_ERROR) from e
    except Exception as e:
        logger.error(f"Failed to get indexing runs: {e}")
        raise AppError("Failed to get indexing runs", error_code=ErrorCode.INTERNAL_ERROR) from e


@router.get("/indexing/runs/{run_id}/status", response_model=dict[str, Any])
async def get_indexing_run_status(
    run_id: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(lambda: PipelineService()),
):
    """Get the status of a specific indexing run."""
    logger.info(f"🔍 Getting indexing run status for run_id: {run_id}")
    logger.info(f"👤 Current user: {current_user.get('id', 'unknown')}")

    try:
        # Access check first
        reader = PipelineReadService()
        allowed = reader.get_run_for_user(str(run_id), current_user["id"])
        if not allowed:
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Indexing run not found or access denied", error_code=ErrorCode.NOT_FOUND)

        logger.info(f"📡 Calling pipeline_service.get_indexing_run({run_id})")
        run = await pipeline_service.get_indexing_run(run_id)

        if not run:
            logger.warning(f"❌ Indexing run not found: {run_id}")
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Indexing run not found", error_code=ErrorCode.NOT_FOUND)

        logger.info(f"✅ Indexing run found: {run.id}")
        logger.info(f"📊 Run status: {run.status}")
        logger.info(f"📊 Run upload_type: {run.upload_type}")

        logger.info(f"📊 Run project_id: {run.project_id}")
        logger.info(f"📊 Run pipeline_config type: {type(run.pipeline_config)}")
        logger.info(f"📊 Run pipeline_config: {run.pipeline_config}")

        # Build response step by step to catch any issues
        response_data = {}

        try:
            response_data["id"] = str(run.id)
            logger.info(f"✅ Added id: {response_data['id']}")
        except Exception as e:
            logger.error(f"❌ Error adding id: {e}")
            raise

        # Note: document_id was removed from indexing_runs table in favor of junction table
        # We'll get document information through the junction table if needed

        try:
            response_data["upload_type"] = run.upload_type
            logger.info(f"✅ Added upload_type: {response_data['upload_type']}")
        except Exception as e:
            logger.error(f"❌ Error adding upload_type: {e}")
            raise

            raise

        try:
            response_data["project_id"] = str(run.project_id) if run.project_id else None
            logger.info(f"✅ Added project_id: {response_data['project_id']}")
        except Exception as e:
            logger.error(f"❌ Error adding project_id: {e}")
            raise

        try:
            response_data["status"] = run.status
            logger.info(f"✅ Added status: {response_data['status']}")
        except Exception as e:
            logger.error(f"❌ Error adding status: {e}")
            raise

        try:
            response_data["started_at"] = run.started_at.isoformat() if run.started_at else None
            logger.info(f"✅ Added started_at: {response_data['started_at']}")
        except Exception as e:
            logger.error(f"❌ Error adding started_at: {e}")
            raise

        try:
            response_data["completed_at"] = run.completed_at.isoformat() if run.completed_at else None
            logger.info(f"✅ Added completed_at: {response_data['completed_at']}")
        except Exception as e:
            logger.error(f"❌ Error adding completed_at: {e}")
            raise

        try:
            response_data["error_message"] = run.error_message
            logger.info(f"✅ Added error_message: {response_data['error_message']}")
        except Exception as e:
            logger.error(f"❌ Error adding error_message: {e}")
            raise

        try:
            response_data["step_results"] = run.step_results
            logger.info(f"✅ Added step_results: {type(response_data['step_results'])}")
        except Exception as e:
            logger.error(f"❌ Error adding step_results: {e}")
            raise

        try:
            response_data["pipeline_config"] = run.pipeline_config
            logger.info(f"✅ Added pipeline_config: {type(response_data['pipeline_config'])}")
        except Exception as e:
            logger.error(f"❌ Error adding pipeline_config: {e}")
            raise

        logger.info(f"🎉 Successfully built response for run {run_id}")
        return response_data

    except HTTPException as exc:
        status = getattr(exc, "status_code", 500)
        code = (
            ErrorCode.NOT_FOUND
            if status == 404
            else ErrorCode.ACCESS_DENIED
            if status == 403
            else ErrorCode.INTERNAL_ERROR
        )
        raise AppError(str(getattr(exc, "detail", "Failed to get indexing run status")), error_code=code) from exc
    except DatabaseError as e:
        logger.error(f"❌ Database error getting indexing run status: {e}")
        raise AppError(str(e), error_code=ErrorCode.DATABASE_ERROR) from e
    except Exception as e:
        logger.error(f"❌ Failed to get indexing run status: {e}")
        raise AppError("Failed to get indexing run status", error_code=ErrorCode.INTERNAL_ERROR) from e


@router.get("/indexing/runs/{run_id}/progress", response_model=dict[str, Any])
async def get_indexing_run_progress(
    run_id: UUID,
    current_user: dict[str, Any] = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(lambda: PipelineService()),
):
    """Get detailed progress information for an indexing run."""
    try:
        # Access check first
        reader = PipelineReadService()
        allowed = reader.get_run_for_user(str(run_id), current_user["id"])
        if not allowed:
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Indexing run not found or access denied", error_code=ErrorCode.NOT_FOUND)

        # Get basic run info
        run = await pipeline_service.get_indexing_run(run_id)
        if not run:
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Indexing run not found", error_code=ErrorCode.NOT_FOUND)

        # Get documents associated with this run
        documents_result = (
            pipeline_service.supabase.table("indexing_run_documents")
            .select("document_id")
            .eq("indexing_run_id", str(run_id))
            .execute()
        )

        document_ids = [doc["document_id"] for doc in documents_result.data] if documents_result.data else []

        # Get document details
        document_status = {}
        if document_ids:
            documents_result = (
                pipeline_service.supabase.table("documents")
                .select("id, filename, step_results")
                .in_("id", document_ids)
                .execute()
            )

            for doc in documents_result.data:
                doc_id = doc["id"]
                step_results = doc.get("step_results", {})

                # Determine document status based on step results
                completed_steps = len([step for step in step_results.values() if step.get("status") == "completed"])
                total_steps = 5  # partition, metadata, enrichment, chunking, embedding

                document_status[doc_id] = {
                    "filename": doc["filename"],
                    "completed_steps": completed_steps,
                    "total_steps": total_steps,
                    "progress_percentage": ((completed_steps / total_steps * 100) if total_steps > 0 else 0),
                    "current_step": _get_current_step(step_results),
                    "step_results": step_results,
                }

        # Calculate overall progress
        total_docs = len(document_status)
        completed_docs = sum(1 for status in document_status.values() if status["progress_percentage"] >= 100)

        # Get step results from the run (only batch operations like embedding)
        run_step_results = run.step_results or {}

        # Convert Pydantic models to dictionaries if needed
        if run_step_results and hasattr(next(iter(run_step_results.values())), "status"):
            # These are Pydantic models, convert to dict
            run_step_results_dict = {
                step_name: {
                    "status": step.status,
                    "duration_seconds": step.duration_seconds,
                    "summary_stats": step.summary_stats,
                    "completed_at": (step.completed_at.isoformat() if step.completed_at else None),
                    "error_message": (step.error_message if hasattr(step, "error_message") else None),
                }
                for step_name, step in run_step_results.items()
            }
        else:
            # These are already dictionaries
            run_step_results_dict = run_step_results

        # Count completed run steps (batch operations only)
        completed_run_steps = len(
            [step for step in run_step_results_dict.values() if step.get("status") == "completed"]
        )

        # Total run steps includes batch operations (typically just embedding)
        total_run_steps = 1  # Only batch embedding step is stored at run level

        # Aggregate all step results for display (document + run level)
        all_step_results = {}

        # Add document-level step results (aggregated across all documents)
        if document_status:
            # Get unique step names from all documents
            all_document_steps = set()
            for doc_status in document_status.values():
                all_document_steps.update(doc_status["step_results"].keys())

            # Aggregate document step results (show completion across all documents)
            for step_name in all_document_steps:
                completed_count = sum(
                    1
                    for doc_status in document_status.values()
                    if doc_status["step_results"].get(step_name, {}).get("status") == "completed"
                )
                total_count = len(document_status)

                all_step_results[f"document_{step_name}"] = {
                    "status": ("completed" if completed_count == total_count else "running"),
                    "completed_documents": completed_count,
                    "total_documents": total_count,
                    "progress_percentage": ((completed_count / total_count * 100) if total_count > 0 else 0),
                    "step_type": "document_level",
                }

        # Add run-level step results (batch operations)
        for step_name, step_data in run_step_results_dict.items():
            all_step_results[f"run_{step_name}"] = {
                **step_data,
                "step_type": "batch_level",
            }

        return {
            "run_id": str(run_id),
            "status": run.status,
            "upload_type": run.upload_type,
            "progress": {
                "documents_processed": completed_docs,
                "total_documents": total_docs,
                "documents_percentage": ((completed_docs / total_docs * 100) if total_docs > 0 else 0),
                "run_steps_completed": completed_run_steps,
                "total_run_steps": total_run_steps,
                "run_steps_percentage": ((completed_run_steps / total_run_steps * 100) if total_run_steps > 0 else 0),
            },
            "document_status": document_status,
            "step_results": all_step_results,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "error_message": run.error_message,
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
        raise AppError(str(getattr(exc, "detail", "Failed to get indexing run progress")), error_code=code) from exc
    except Exception as e:
        logger.error(f"Failed to get indexing run progress: {e}")
        raise AppError("Failed to get indexing run progress", error_code=ErrorCode.INTERNAL_ERROR) from e


def _get_current_step(step_results: dict) -> str:
    """Helper function to determine the current step for a document"""
    if not step_results:
        return "waiting"

    # Check steps in order
    steps = ["partition", "metadata", "enrichment", "chunking", "embedding"]
    for step in steps:
        if step not in step_results:
            return step
        if step_results[step].get("status") != "completed":
            return step

    return "completed"


@router.get("/indexing/runs/{run_id}/steps/{step_name}", response_model=dict[str, Any])
async def get_step_result(
    run_id: UUID,
    step_name: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(lambda: PipelineService()),
):
    """Get the result of a specific step from an indexing run."""
    try:
        step_result = await pipeline_service.get_step_result(run_id, step_name)
        if not step_result:
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Step result not found", error_code=ErrorCode.NOT_FOUND)

        return {
            "step": step_result.step,
            "status": step_result.status,
            "duration_seconds": step_result.duration_seconds,
            "summary_stats": step_result.summary_stats,
            "sample_outputs": step_result.sample_outputs,
            "data": step_result.data,
            "started_at": (step_result.started_at.isoformat() if step_result.started_at else None),
            "completed_at": (step_result.completed_at.isoformat() if step_result.completed_at else None),
            "error_message": step_result.error_message,
            "error_details": step_result.error_details,
        }
    except HTTPException as exc:
        status = getattr(exc, "status_code", 500)
        code = ErrorCode.NOT_FOUND if status == 404 else ErrorCode.INTERNAL_ERROR
        raise AppError(str(getattr(exc, "detail", "Failed to get step result")), error_code=code) from exc
    except DatabaseError as e:
        logger.error(f"Database error getting step result: {e}")
        raise AppError(str(e), error_code=ErrorCode.DATABASE_ERROR) from e
    except Exception as e:
        logger.error(f"Failed to get step result: {e}")
        raise AppError("Failed to get step result", error_code=ErrorCode.INTERNAL_ERROR) from e


@router.post("/indexing/steps/{step_name}/execute", response_model=dict[str, Any])
async def execute_single_step(
    step_name: str,
    input_data: dict[str, Any],
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Local step execution is disabled; indexing executes on Beam only."""
    from ..shared.errors import ErrorCode
    from ..utils.exceptions import AppError

    raise AppError(
        "Local step execution is disabled; use Beam.", error_code=ErrorCode.CONFIGURATION_ERROR, status_code=501
    )


@router.get("/health", response_model=dict[str, Any])
async def pipeline_health_check():
    """Health check endpoint for the pipeline service."""
    try:
        # Test database connection
        pipeline_service = PipelineService()
        # This would test the database connection
        # For now, just return success

        return {
            "status": "healthy",
            "service": "pipeline",
            "database": "connected",
            "timestamp": "2025-01-28T12:00:00Z",
        }

    except Exception as e:
        logger.error(f"Pipeline health check failed: {e}")
        from ..shared.errors import ErrorCode
        from ..utils.exceptions import AppError

        raise AppError("Pipeline service unhealthy", error_code=ErrorCode.INTERNAL_ERROR, status_code=503) from e


# Flat resource endpoints for indexing runs


@flat_router.get("/indexing-runs", response_model=list[dict[str, Any]])
async def list_indexing_runs(
    project_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Flat list endpoint for indexing runs, scoped to user's projects.

    For now requires `project_id` to scope; later we can support multi-project list.
    """
    try:
        reader = PipelineReadService()
        if project_id is None:
            # Fallback to recent runs across all user's projects
            runs = reader.list_recent_runs_for_user(current_user["id"], limit=min(limit, 50))
            return runs
        # Filter by specific project
        # Simple select with ownership check similar to get_run_for_user
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
            return []
        res = (
            db.table("indexing_runs")
            .select("id, upload_type, project_id, status, started_at, completed_at, error_message")
            .eq("project_id", str(project_id))
            .order("started_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return list(res.data or [])
    except HTTPException as exc:
        code = ErrorCode.NOT_FOUND if getattr(exc, "status_code", 500) == 404 else ErrorCode.INTERNAL_ERROR
        raise AppError(str(getattr(exc, "detail", "Failed to list indexing runs")), error_code=code) from exc
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to list indexing runs: {e}")
        raise AppError("Failed to list indexing runs", error_code=ErrorCode.INTERNAL_ERROR) from e


@flat_router.get("/indexing-runs/{run_id}", response_model=dict[str, Any])
async def get_indexing_run(
    run_id: UUID,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
    pipeline_service: PipelineService = Depends(lambda: PipelineService(use_admin_client=True)),
):
    """Flat get endpoint for a single indexing run.

    - If authenticated: ensure access via PipelineReadService.
    - If anonymous: allow only when run is from email uploads.
    """
    reader = PipelineReadService()
    # Fetch run using admin client to check upload_type and existence
    run = await pipeline_service.get_indexing_run(run_id)
    if not run:
        from ..shared.errors import ErrorCode
        from ..utils.exceptions import AppError

        raise AppError("Indexing run not found", error_code=ErrorCode.NOT_FOUND)

    if current_user:
        allowed = reader.get_run_for_user(str(run_id), current_user["id"])
        if not allowed:
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Indexing run not found or access denied", error_code=ErrorCode.NOT_FOUND)
    else:
        # Anonymous only permitted for email uploads
        if getattr(run, "upload_type", None) != "email":
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Access denied: Authentication required", error_code=ErrorCode.ACCESS_DENIED)

    return {
        "id": str(run.id),
        "upload_type": run.upload_type,
        "project_id": (str(run.project_id) if run.project_id else None),
        "status": run.status,
        "started_at": (run.started_at.isoformat() if run.started_at else None),
        "completed_at": (run.completed_at.isoformat() if run.completed_at else None),
        "error_message": run.error_message,
        "step_results": run.step_results,
        "pipeline_config": run.pipeline_config,
    }


@flat_router.get("/indexing-runs/{run_id}/progress", response_model=dict[str, Any])
async def get_flat_indexing_run_progress(
    run_id: UUID,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
    pipeline_service: PipelineService = Depends(lambda: PipelineService(use_admin_client=True)),
):
    """Flat progress endpoint mirroring the pipeline progress, with optional auth."""
    reader = PipelineReadService()
    run = await pipeline_service.get_indexing_run(run_id)
    if not run:
        from ..shared.errors import ErrorCode
        from ..utils.exceptions import AppError

        raise AppError("Indexing run not found", error_code=ErrorCode.NOT_FOUND)
    if current_user:
        allowed = reader.get_run_for_user(str(run_id), current_user["id"])
        if not allowed:
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Indexing run not found or access denied", error_code=ErrorCode.NOT_FOUND)
    else:
        if getattr(run, "upload_type", None) != "email":
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Access denied: Authentication required", error_code=ErrorCode.ACCESS_DENIED)

    documents_result = (
        pipeline_service.supabase.table("indexing_run_documents")
        .select("document_id")
        .eq("indexing_run_id", str(run_id))
        .execute()
    )
    document_ids = [doc["document_id"] for doc in (documents_result.data or [])]

    document_status: dict[str, Any] = {}
    if document_ids:
        documents_result = (
            pipeline_service.supabase.table("documents")
            .select("id, filename, step_results")
            .in_("id", document_ids)
            .execute()
        )
        for doc in documents_result.data or []:
            doc_id = doc["id"]
            step_results = doc.get("step_results", {})
            completed_steps = len([s for s in step_results.values() if s.get("status") == "completed"])
            total_steps = 5
            document_status[doc_id] = {
                "filename": doc["filename"],
                "completed_steps": completed_steps,
                "total_steps": total_steps,
                "progress_percentage": ((completed_steps / total_steps * 100) if total_steps > 0 else 0),
                "current_step": _get_current_step(step_results),
                "step_results": step_results,
            }

    total_docs = len(document_status)
    completed_docs = sum(1 for status in document_status.values() if status["progress_percentage"] >= 100)

    run_step_results = run.step_results or {}
    if run_step_results and hasattr(next(iter(run_step_results.values()), {}), "status"):
        run_step_results_dict = {
            step_name: {
                "status": step.status,
                "duration_seconds": step.duration_seconds,
                "summary_stats": step.summary_stats,
                "completed_at": (step.completed_at.isoformat() if step.completed_at else None),
                "error_message": (step.error_message if hasattr(step, "error_message") else None),
            }
            for step_name, step in run_step_results.items()
        }
    else:
        run_step_results_dict = run_step_results

    completed_run_steps = len([s for s in run_step_results_dict.values() if s.get("status") == "completed"])
    total_run_steps = 1

    all_step_results: dict[str, Any] = {}
    if document_status:
        all_document_steps = set()
        for ds in document_status.values():
            all_document_steps.update(ds["step_results"].keys())
        for step_name in all_document_steps:
            completed_count = sum(
                1
                for ds in document_status.values()
                if ds["step_results"].get(step_name, {}).get("status") == "completed"
            )
            total_count = len(document_status)
            all_step_results[f"document_{step_name}"] = {
                "status": ("completed" if completed_count == total_count else "running"),
                "completed_documents": completed_count,
                "total_documents": total_count,
                "progress_percentage": ((completed_count / total_count * 100) if total_count > 0 else 0),
                "step_type": "document_level",
            }

    for step_name, step_data in run_step_results_dict.items():
        all_step_results[f"run_{step_name}"] = {**step_data, "step_type": "batch_level"}

    return {
        "run_id": str(run_id),
        "status": run.status,
        "upload_type": run.upload_type,
        "progress": {
            "documents_processed": completed_docs,
            "total_documents": total_docs,
            "documents_percentage": ((completed_docs / total_docs * 100) if total_docs > 0 else 0),
            "run_steps_completed": completed_run_steps,
            "total_run_steps": total_run_steps,
            "run_steps_percentage": ((completed_run_steps / total_run_steps * 100) if total_run_steps > 0 else 0),
        },
        "document_status": document_status,
        "step_results": all_step_results,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error_message": run.error_message,
    }


# Optional: Explicit creation of indexing runs (separate from uploads)
@flat_router.post("/indexing-runs", response_model=dict[str, Any])
async def create_indexing_run(
    project_id: UUID | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(lambda: PipelineService()),
):
    """Create an indexing run explicitly. Use for project-based runs.

    Note: Email/public runs should be created via /api/uploads.
    """
    try:
        # Basic ownership check if project specified
        if project_id is not None:
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
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

                raise AppError("Project not found or access denied", error_code=ErrorCode.NOT_FOUND)
        run = await pipeline_service.create_indexing_run(
            upload_type="user_project",
            project_id=project_id,
        )
        return {
            "id": str(run.id),
            "upload_type": run.upload_type,
            "project_id": (str(run.project_id) if run.project_id else None),
            "status": run.status,
            "started_at": (run.started_at.isoformat() if run.started_at else None),
            "completed_at": (run.completed_at.isoformat() if run.completed_at else None),
            "error_message": run.error_message,
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
        raise AppError(str(getattr(exc, "detail", "Failed to create indexing run")), error_code=code) from exc
    except Exception as e:
        logger.error(f"Failed to create indexing run: {e}")
        raise AppError("Failed to create indexing run", error_code=ErrorCode.INTERNAL_ERROR) from e
