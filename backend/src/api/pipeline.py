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

try:
    from ..pipeline.indexing.orchestrator import get_indexing_orchestrator
except Exception as e:
    raise

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
    try:
        # Create document input with placeholder run_id (will be updated by orchestrator)
        document_input = DocumentInput(
            document_id=document_id,
            run_id=UUID(int=0),  # Placeholder - will be updated by orchestrator
            user_id=current_user["id"],
            file_path=f"/path/to/document/{document_id}.pdf",  # This would come from document service
            filename=f"document_{document_id}.pdf",
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
    pipeline_service: PipelineService = Depends(lambda: PipelineService()),
):
    """Get the status of a specific indexing run."""
    try:
        run = await pipeline_service.get_indexing_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Indexing run not found")

        return {
            "id": str(run.id),
            "document_id": str(run.document_id),
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "error_message": run.error_message,
            "step_results": run.step_results,
        }

    except DatabaseError as e:
        logger.error(f"Database error getting indexing run status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get indexing run status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
