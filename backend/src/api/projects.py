"""Projects API (v2 flat, owner-only)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.config.database import get_db_client_for_request, get_supabase_client
from src.models.base import AccessLevel
from src.models.pipeline import ProjectCreate, ProjectUpdate
from src.services.auth_service import get_current_user
from src.services.project_service import ProjectService

router = APIRouter(prefix="/api", tags=["Projects"])

DB_CLIENT_DEP = Depends(get_db_client_for_request)
CURRENT_USER_DEP = Depends(get_current_user)


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    access_level: AccessLevel

    class Config:
        from_attributes = True


class ProjectWithIndexingRunResponse(BaseModel):
    """Enhanced project response that includes latest indexing run ID for frontend compatibility."""
    id: UUID  # This will be the indexing run ID for frontend compatibility
    name: str
    description: str | None = None
    access_level: AccessLevel
    project_id: UUID | None = None  # The actual project ID
    upload_type: str | None = None
    status: str | None = None

    class Config:
        from_attributes = True


class ProjectCreateRequest(BaseModel):
    name: str
    description: str | None = None
    access_level: AccessLevel = AccessLevel.OWNER


class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    access_level: AccessLevel | None = None


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    payload: ProjectCreateRequest,
    current_user: dict[str, Any] = CURRENT_USER_DEP,
    db_client=DB_CLIENT_DEP,
):
    svc = ProjectService(db_client)
    data = ProjectCreate(
        user_id=UUID(current_user["id"]),
        name=payload.name,
        description=payload.description,
        access_level=payload.access_level,
    )
    created = svc.create(user_id=current_user["id"], data=data)
    return ProjectResponse.model_validate(created)


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    limit: int = 20,
    offset: int = 0,
    current_user: dict[str, Any] = CURRENT_USER_DEP,
    db_client=DB_CLIENT_DEP,
):
    svc = ProjectService(db_client)
    items = svc.list(user_id=current_user["id"], limit=min(limit, 50), offset=offset)
    return [ProjectResponse.model_validate(p) for p in items]


@router.get("/projects/{project_id}", response_model=ProjectWithIndexingRunResponse)
async def get_project(
    project_id: UUID,
    current_user: dict[str, Any] = CURRENT_USER_DEP,
    db_client=DB_CLIENT_DEP,
):
    """Get a project with its latest indexing run information for frontend compatibility."""
    svc = ProjectService(db_client)
    proj = svc.get(project_id, user_id=current_user["id"])
    if not proj:
        from src.shared.errors import ErrorCode
        from src.utils.exceptions import AppError

        raise AppError("Project not found", error_code=ErrorCode.NOT_FOUND)
    
    # Get the latest completed indexing run for this project from project_wikis table
    db = get_supabase_client()
    try:
        latest_run_query = (
            db.table("project_wikis")
            .select("indexing_run_id, upload_type, wiki_status")
            .eq("project_id", str(project_id))
            .eq("user_id", current_user["id"])
            .eq("wiki_status", "completed")
            .order("created_at", desc=True)
            .limit(1)
        )
        
        latest_run_res = latest_run_query.execute()
        
        if latest_run_res.data:
            # Return indexing run ID as the main ID for frontend compatibility
            latest_run = latest_run_res.data[0]
            return ProjectWithIndexingRunResponse(
                id=UUID(latest_run["indexing_run_id"]),  # Frontend expects this as the main ID
                name=proj.name,
                description=proj.description,
                access_level=proj.access_level,
                project_id=proj.id,  # Store actual project ID separately
                upload_type=latest_run.get("upload_type"),
                status=latest_run.get("wiki_status")
            )
        else:
            # No completed wikis found, fall back to project info
            raise AppError("No completed wikis found for this project", error_code=ErrorCode.NOT_FOUND)
            
    except Exception as e:
        # If project_wikis lookup fails, return basic project info
        import logging
        logging.warning(f"Failed to get latest indexing run for project {project_id}: {e}")
        raise AppError("No completed wikis found for this project", error_code=ErrorCode.NOT_FOUND)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdateRequest,
    current_user: dict[str, Any] = CURRENT_USER_DEP,
    db_client=DB_CLIENT_DEP,
):
    svc = ProjectService(db_client)
    updated = svc.update(
        project_id, user_id=current_user["id"], data=ProjectUpdate(**payload.model_dump(exclude_unset=True))
    )
    if not updated:
        from src.shared.errors import ErrorCode
        from src.utils.exceptions import AppError

        raise AppError("Project not found or not modified", error_code=ErrorCode.NOT_FOUND)
    return ProjectResponse.model_validate(updated)


@router.delete("/projects/{project_id}", response_model=dict[str, Any])
async def delete_project(
    project_id: UUID,
    current_user: dict[str, Any] = CURRENT_USER_DEP,
    db_client=DB_CLIENT_DEP,
):
    svc = ProjectService(db_client)
    ok = svc.delete(project_id, user_id=current_user["id"])
    if not ok:
        from src.shared.errors import ErrorCode
        from src.utils.exceptions import AppError

        raise AppError("Project not found", error_code=ErrorCode.NOT_FOUND)
    return {"status": "deleted"}
