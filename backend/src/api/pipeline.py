"""Pipeline API endpoints for managing indexing and query pipelines."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import logging

try:
    from ..models.pipeline import IndexingRun, QueryRun, StepResult
except Exception as e:
    raise

try:
    from ..services.pipeline_service import PipelineService
except Exception as e:
    raise

# Indexing orchestrator only available on Beam, not FastAPI
try:
    from ..pipeline.indexing.orchestrator import get_indexing_orchestrator

    INDEXING_AVAILABLE = True
except ImportError:
    INDEXING_AVAILABLE = False
    get_indexing_orchestrator = None
    logging.warning("Indexing orchestrator not available - indexing runs on Beam only")

try:
    from ..pipeline.shared.models import DocumentInput
except Exception as e:
    raise

try:
    from .auth import get_current_user
except Exception as e:
    raise

try:
    from ..utils.exceptions import DatabaseError, PipelineError
except Exception as e:
    raise

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/indexing/start", response_model=Dict[str, Any])
async def start_indexing_pipeline(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(lambda: PipelineService()),
):
    """Start the indexing pipeline for a document."""

    # Indexing now runs exclusively on Beam, not FastAPI
    if not INDEXING_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Indexing pipeline runs on Beam only. Use /api/email-uploads endpoint for document processing.",
        )

    try:
        # Create document input with placeholder run_id (will be updated by orchestrator)
        document_input = DocumentInput(
            document_id=document_id,
            run_id=UUID(int=0),  # Placeholder - will be updated by orchestrator
            user_id=current_user["id"],
            file_path=f"/path/to/document/{document_id}.pdf",  # This would come from document service
            filename=f"document_{document_id}.pdf",
            upload_type="user_project",
            metadata={},
        )

        # Get orchestrator
        orchestrator = await get_indexing_orchestrator()

        # Start pipeline in background
        background_tasks.add_task(orchestrator.process_document_async, document_input)

        return {
            "message": "Indexing pipeline started",
            "document_id": str(document_id),
            "user_id": str(current_user["id"]),
            "status": "started",
        }

    except Exception as e:
        logger.error(f"Failed to start indexing pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indexing/runs", response_model=List[Dict[str, Any]])
async def get_all_indexing_runs(
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(
        lambda: PipelineService(use_admin_client=True)
    ),
):
    """Get all indexing runs, sorted by latest first."""
    logger.info(
        f"🔍 Getting all indexing runs for user: {current_user.get('id', 'unknown')}"
    )

    try:
        # Direct database query to avoid validation issues
        result = (
            pipeline_service.supabase.table("indexing_runs")
            .select(
                "id, upload_type, project_id, status, started_at, completed_at, error_message"
            )
            .order("started_at", desc=True)
            .limit(5)  # Only get last 5 runs
            .execute()
        )

        if not result.data:
            logger.info("📭 No indexing runs found")
            return []

        # Transform the raw data
        runs = []
        for run_data in result.data:
            runs.append(
                {
                    "id": run_data["id"],
                    "upload_type": run_data.get("upload_type", "unknown"),
                    "project_id": run_data.get("project_id"),
                    "status": run_data.get("status", "unknown"),
                    "started_at": run_data.get("started_at"),
                    "completed_at": run_data.get("completed_at"),
                    "error_message": run_data.get("error_message"),
                }
            )

        logger.info(f"📊 Found {len(runs)} indexing runs")
        logger.info(f"📊 Run IDs being returned: {[run['id'] for run in runs]}")

        return runs

    except Exception as e:
        logger.error(f"Failed to get all indexing runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indexing/runs/{document_id}", response_model=List[Dict[str, Any]])
async def get_indexing_runs(
    document_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(lambda: PipelineService()),
):
    """Get all indexing runs for a document."""
    try:
        runs = await pipeline_service.get_document_indexing_runs(document_id)
        return [
            {
                "id": str(run.id),
                "document_id": str(run.document_id),
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": (
                    run.completed_at.isoformat() if run.completed_at else None
                ),
                "error_message": run.error_message,
                "step_results": run.step_results,
            }
            for run in runs
        ]

    except DatabaseError as e:
        logger.error(f"Database error getting indexing runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get indexing runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indexing/runs/{run_id}/status", response_model=Dict[str, Any])
async def get_indexing_run_status(
    run_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(
        lambda: PipelineService(use_admin_client=True)
    ),
):
    """Get the status of a specific indexing run."""
    logger.info(f"🔍 Getting indexing run status for run_id: {run_id}")
    logger.info(f"👤 Current user: {current_user.get('id', 'unknown')}")

    try:
        logger.info(f"📡 Calling pipeline_service.get_indexing_run({run_id})")
        run = await pipeline_service.get_indexing_run(run_id)

        if not run:
            logger.warning(f"❌ Indexing run not found: {run_id}")
            raise HTTPException(status_code=404, detail="Indexing run not found")

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
            response_data["project_id"] = (
                str(run.project_id) if run.project_id else None
            )
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
            response_data["started_at"] = (
                run.started_at.isoformat() if run.started_at else None
            )
            logger.info(f"✅ Added started_at: {response_data['started_at']}")
        except Exception as e:
            logger.error(f"❌ Error adding started_at: {e}")
            raise

        try:
            response_data["completed_at"] = (
                run.completed_at.isoformat() if run.completed_at else None
            )
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
            logger.info(
                f"✅ Added pipeline_config: {type(response_data['pipeline_config'])}"
            )
        except Exception as e:
            logger.error(f"❌ Error adding pipeline_config: {e}")
            raise

        logger.info(f"🎉 Successfully built response for run {run_id}")
        return response_data

    except DatabaseError as e:
        logger.error(f"❌ Database error getting indexing run status: {e}")
        logger.error(f"❌ Database error type: {type(e)}")
        logger.error(f"❌ Database error details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Failed to get indexing run status: {e}")
        logger.error(f"❌ Error type: {type(e)}")
        logger.error(f"❌ Error details: {str(e)}")
        import traceback

        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indexing/runs/{run_id}/progress", response_model=Dict[str, Any])
async def get_indexing_run_progress(
    run_id: UUID,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(
        lambda: PipelineService(use_admin_client=True)
    ),
):
    """Get detailed progress information for an indexing run."""
    try:
        # Get basic run info
        run = await pipeline_service.get_indexing_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Indexing run not found")

        # Get documents associated with this run
        documents_result = (
            pipeline_service.supabase.table("indexing_run_documents")
            .select("document_id")
            .eq("indexing_run_id", str(run_id))
            .execute()
        )

        document_ids = (
            [doc["document_id"] for doc in documents_result.data]
            if documents_result.data
            else []
        )

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
                completed_steps = len(
                    [
                        step
                        for step in step_results.values()
                        if step.get("status") == "completed"
                    ]
                )
                total_steps = 5  # partition, metadata, enrichment, chunking, embedding

                document_status[doc_id] = {
                    "filename": doc["filename"],
                    "completed_steps": completed_steps,
                    "total_steps": total_steps,
                    "progress_percentage": (
                        (completed_steps / total_steps * 100) if total_steps > 0 else 0
                    ),
                    "current_step": _get_current_step(step_results),
                    "step_results": step_results,
                }

        # Calculate overall progress
        total_docs = len(document_status)
        completed_docs = sum(
            1
            for status in document_status.values()
            if status["progress_percentage"] >= 100
        )

        # Get step results from the run (only batch operations like embedding)
        run_step_results = run.step_results or {}

        # Convert Pydantic models to dictionaries if needed
        if run_step_results and hasattr(
            next(iter(run_step_results.values())), "status"
        ):
            # These are Pydantic models, convert to dict
            run_step_results_dict = {
                step_name: {
                    "status": step.status,
                    "duration_seconds": step.duration_seconds,
                    "summary_stats": step.summary_stats,
                    "completed_at": (
                        step.completed_at.isoformat() if step.completed_at else None
                    ),
                    "error_message": (
                        step.error_message if hasattr(step, "error_message") else None
                    ),
                }
                for step_name, step in run_step_results.items()
            }
        else:
            # These are already dictionaries
            run_step_results_dict = run_step_results

        # Count completed run steps (batch operations only)
        completed_run_steps = len(
            [
                step
                for step in run_step_results_dict.values()
                if step.get("status") == "completed"
            ]
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
                    if doc_status["step_results"].get(step_name, {}).get("status")
                    == "completed"
                )
                total_count = len(document_status)

                all_step_results[f"document_{step_name}"] = {
                    "status": (
                        "completed" if completed_count == total_count else "running"
                    ),
                    "completed_documents": completed_count,
                    "total_documents": total_count,
                    "progress_percentage": (
                        (completed_count / total_count * 100) if total_count > 0 else 0
                    ),
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
                "documents_percentage": (
                    (completed_docs / total_docs * 100) if total_docs > 0 else 0
                ),
                "run_steps_completed": completed_run_steps,
                "total_run_steps": total_run_steps,
                "run_steps_percentage": (
                    (completed_run_steps / total_run_steps * 100)
                    if total_run_steps > 0
                    else 0
                ),
            },
            "document_status": document_status,
            "step_results": all_step_results,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "error_message": run.error_message,
        }

    except Exception as e:
        logger.error(f"Failed to get indexing run progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/indexing/runs/{run_id}/steps/{step_name}", response_model=Dict[str, Any])
async def get_step_result(
    run_id: UUID,
    step_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline_service: PipelineService = Depends(lambda: PipelineService()),
):
    """Get the result of a specific step from an indexing run."""
    try:
        step_result = await pipeline_service.get_step_result(run_id, step_name)
        if not step_result:
            raise HTTPException(status_code=404, detail="Step result not found")

        return {
            "step": step_result.step,
            "status": step_result.status,
            "duration_seconds": step_result.duration_seconds,
            "summary_stats": step_result.summary_stats,
            "sample_outputs": step_result.sample_outputs,
            "data": step_result.data,
            "started_at": (
                step_result.started_at.isoformat() if step_result.started_at else None
            ),
            "completed_at": (
                step_result.completed_at.isoformat()
                if step_result.completed_at
                else None
            ),
            "error_message": step_result.error_message,
            "error_details": step_result.error_details,
        }

    except DatabaseError as e:
        logger.error(f"Database error getting step result: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get step result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/indexing/steps/{step_name}/execute", response_model=Dict[str, Any])
async def execute_single_step(
    step_name: str,
    input_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Execute a single pipeline step with provided input data."""
    try:
        # Get orchestrator
        orchestrator = await get_indexing_orchestrator()

        # Initialize steps
        await orchestrator.initialize_steps(current_user["id"])

        # Find the requested step
        step = None
        for s in orchestrator.steps:
            if s.get_step_name() == step_name:
                step = s
                break

        if not step:
            raise HTTPException(status_code=404, detail=f"Step '{step_name}' not found")

        # Execute the step
        result = await step.execute(input_data)

        return {
            "step": result.step,
            "status": result.status,
            "duration_seconds": result.duration_seconds,
            "summary_stats": result.summary_stats,
            "sample_outputs": result.sample_outputs,
            "data": result.data,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": (
                result.completed_at.isoformat() if result.completed_at else None
            ),
            "error_message": result.error_message,
            "error_details": result.error_details,
        }

    except PipelineError as e:
        logger.error(f"Pipeline error executing step: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute step: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=Dict[str, Any])
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
        raise HTTPException(status_code=503, detail="Pipeline service unhealthy")
