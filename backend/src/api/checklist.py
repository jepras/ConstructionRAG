"""API endpoints for checklist analysis feature."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.models.checklist import (
    ChecklistAnalysisRequest,
    ChecklistAnalysisResponse,
    ChecklistAnalysisRun,
)
from src.pipeline.checklist import ChecklistAnalysisOrchestrator
from src.services.auth_service import get_current_user_optional
from src.services.checklist_service import ChecklistService
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/checklist", tags=["Checklist"])


@router.post("/analyze", response_model=ChecklistAnalysisResponse)
async def analyze_checklist(
    background_tasks: BackgroundTasks,
    request: ChecklistAnalysisRequest,
    user=Depends(get_current_user_optional),
):
    """
    Start checklist analysis.
    Supports both authenticated and unauthenticated users.
    """
    try:
        checklist_service = ChecklistService()
        
        # Validate access to indexing_run
        await checklist_service.validate_indexing_run_access(
            request.indexing_run_id, user
        )
        
        # Create analysis run
        analysis_run = await checklist_service.create_analysis_run(
            indexing_run_id=request.indexing_run_id,
            checklist_content=request.checklist_content,
            checklist_name=request.checklist_name,
            model_name=request.model_name,
            user_id=str(user.id) if user else None,
        )
        
        # Start background processing
        orchestrator = ChecklistAnalysisOrchestrator()
        background_tasks.add_task(
            orchestrator.process_checklist_analysis,
            str(analysis_run.id)
        )
        
        return ChecklistAnalysisResponse(
            analysis_run_id=analysis_run.id,
            status="running",
            message="Analysis started successfully",
        )
        
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error starting checklist analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs/{run_id}", response_model=ChecklistAnalysisRun)
async def get_analysis_run(
    run_id: str,
    user=Depends(get_current_user_optional),
):
    """
    Get analysis run status and results.
    RLS policies handle access control.
    """
    try:
        checklist_service = ChecklistService()
        analysis_run = await checklist_service.get_analysis_run_with_results(run_id)
        
        if not analysis_run:
            raise HTTPException(status_code=404, detail="Analysis run not found")
        
        return analysis_run
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching analysis run: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs")
async def list_analysis_runs(
    indexing_run_id: Optional[str] = None,
    user=Depends(get_current_user_optional),
):
    """
    List analysis runs for a project.
    RLS policies automatically filter based on user access.
    """
    try:
        checklist_service = ChecklistService()
        runs = await checklist_service.list_analysis_runs_for_user(
            user_id=str(user.id) if user else None,
            indexing_run_id=indexing_run_id,
        )
        return {"runs": runs}
        
    except Exception as e:
        logger.error(f"Error listing analysis runs: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/runs/{run_id}")
async def delete_analysis_run(
    run_id: str,
    user=Depends(get_current_user_optional),
):
    """
    Delete analysis run (authenticated users only).
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        checklist_service = ChecklistService()
        await checklist_service.delete_analysis_run_by_id(run_id, str(user.id))
        return {"message": "Analysis run deleted successfully"}
        
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error deleting analysis run: {e}")
        raise HTTPException(status_code=400, detail=str(e))