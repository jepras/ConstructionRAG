# backend/src/api/unified_projects.py
"""GitHub-style RESTful API endpoints for unified project management."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Form
from pydantic import BaseModel

from src.services.auth_service import get_user_context_optional, get_user_context
from src.services.project_service import ProjectService
from src.config.database import get_supabase_client
from src.models.user import UserContext
from src.models.pipeline import UploadType
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ProjectNameCheckRequest(BaseModel):
    project_name: str
    username: str


class ProjectNameCheckResponse(BaseModel):
    available: bool
    project_slug: str
    username: str
    error: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    username: str
    project_slug: str
    visibility: str
    description: str | None = None
    created_at: str
    updated_at: str


# POST /api/projects/check-name
@router.post("/projects/check-name", response_model=ProjectNameCheckResponse)
async def check_project_name_availability(
    request: ProjectNameCheckRequest,
    user: UserContext = Depends(get_user_context_optional)
):
    """Check if project name is available in the given username namespace"""
    project_service = ProjectService(get_supabase_client())

    # Validate project name format
    from src.utils.validation import validate_project_name
    validation = validate_project_name(request.project_name)
    if not validation["valid"]:
        return ProjectNameCheckResponse(
            available=False,
            project_slug="",
            username=request.username,
            error=validation["error"]
        )

    # Generate slug from name
    project_slug = project_service.generate_project_slug(request.project_name)

    # Check availability
    result = await project_service.check_project_name_availability(
        request.username, request.project_name
    )

    return ProjectNameCheckResponse(**result)


# GET /api/projects/{username}/{project_slug}
@router.get("/projects/{username}/{project_slug}", response_model=ProjectResponse)
async def get_project(
    username: str,
    project_slug: str,
    user: UserContext = Depends(get_user_context_optional)
):
    """Get project details by username and project slug"""
    project_service = ProjectService(get_supabase_client())
    project = await project_service.get_project_by_slug(username, project_slug, user)

    return ProjectResponse(
        id=project['id'],
        name=project['name'],
        username=project['username'],
        project_slug=project['project_slug'],
        visibility=project['visibility'],
        description=project.get('description'),
        created_at=project['created_at'],
        updated_at=project['updated_at']
    )


# PATCH /api/projects/{username}/{project_slug}
@router.patch("/projects/{username}/{project_slug}", response_model=ProjectResponse)
async def update_project(
    username: str,
    project_slug: str,
    updates: Dict[str, Any],
    user: UserContext = Depends(get_user_context)
):
    """Update project (requires authentication)"""
    project_service = ProjectService(get_supabase_client())
    project = await project_service.get_project_by_slug(username, project_slug, user)

    if not project_service.can_access_resource(project, 'write', user):
        raise HTTPException(403, "Access denied")

    # Update project with new data
    # Implementation would go here
    raise HTTPException(501, "Update functionality not yet implemented")


# DELETE /api/projects/{username}/{project_slug}
@router.delete("/projects/{username}/{project_slug}")
async def delete_project(
    username: str,
    project_slug: str,
    user: UserContext = Depends(get_user_context)
):
    """Delete project (requires authentication)"""
    project_service = ProjectService(get_supabase_client())
    project = await project_service.get_project_by_slug(username, project_slug, user)

    if not project_service.can_access_resource(project, 'write', user):
        raise HTTPException(403, "Access denied")

    # Delete project
    # Implementation would go here
    raise HTTPException(501, "Delete functionality not yet implemented")


# GET /api/projects/{username}/{project_slug}/documents
@router.get("/projects/{username}/{project_slug}/documents")
async def list_project_documents(
    username: str,
    project_slug: str,
    user: UserContext = Depends(get_user_context_optional)
):
    """List documents for a project"""
    project_service = ProjectService(get_supabase_client())
    project = await project_service.get_project_by_slug(username, project_slug, user)

    if not project_service.can_access_resource(project, 'read', user):
        raise HTTPException(403, "Access denied")

    # Get project documents
    try:
        db = get_supabase_client()
        documents_result = (
            db.table("documents")
            .select("*")
            .eq("project_id", project["id"])
            .order("created_at", desc=True)
            .execute()
        )

        documents = documents_result.data or []

        logger.info(
            "Listed project documents",
            username=username,
            project_slug=project_slug,
            project_id=project["id"],
            document_count=len(documents),
            is_authenticated=user.isAuthenticated if user else False
        )

        return {
            "documents": documents,
            "total_count": len(documents),
            "project": {
                "id": project["id"],
                "name": project["name"],
                "username": project["username"],
                "project_slug": project["project_slug"]
            }
        }

    except Exception as e:
        logger.error(
            "Failed to list project documents",
            username=username,
            project_slug=project_slug,
            error=str(e)
        )
        raise HTTPException(500, "Failed to list documents")


# POST /api/projects/{username}/{project_slug}/documents
@router.post("/projects/{username}/{project_slug}/documents")
async def upload_project_documents(
    username: str,
    project_slug: str,
    user: UserContext = Depends(get_user_context)
):
    """Upload documents to a project (requires authentication)"""
    project_service = ProjectService(get_supabase_client())
    project = await project_service.get_project_by_slug(username, project_slug, user)

    if not project_service.can_access_resource(project, 'upload', user):
        raise HTTPException(403, "Upload access denied")

    # Process file uploads for this specific project
    # Implementation would go here
    raise HTTPException(501, "Document upload not yet implemented")


# GET /api/projects/{username}/{project_slug}/wiki
@router.get("/projects/{username}/{project_slug}/wiki")
async def get_project_wiki(
    username: str,
    project_slug: str,
    user: UserContext = Depends(get_user_context_optional)
):
    """Get project wiki pages"""
    project_service = ProjectService(get_supabase_client())
    project = await project_service.get_project_by_slug(username, project_slug, user)

    if not project_service.can_access_resource(project, 'read', user):
        raise HTTPException(403, "Access denied")

    # Get project wiki
    try:
        db = get_supabase_client()

        # Find the latest indexing run for this project
        indexing_runs_result = (
            db.table("indexing_runs")
            .select("id, status, created_at")
            .eq("project_id", project["id"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not indexing_runs_result.data:
            return {
                "wiki_pages": [],
                "status": "no_indexing_run",
                "message": "No indexing run found for this project"
            }

        indexing_run = indexing_runs_result.data[0]

        # Get wiki generation runs for this indexing run
        wiki_runs_result = (
            db.table("wiki_generation_runs")
            .select("*")
            .eq("indexing_run_id", indexing_run["id"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not wiki_runs_result.data:
            return {
                "wiki_pages": [],
                "status": "no_wiki",
                "indexing_run_id": indexing_run["id"],
                "message": "No wiki generated for this project yet"
            }

        wiki_run = wiki_runs_result.data[0]

        # Get wiki pages directly from database/storage using unified parameters
        try:
            from src.services.storage_service import StorageService

            storage_service = StorageService()

            # Determine upload type based on project properties
            upload_type = UploadType.EMAIL if project.get("user_id") == "00000000-0000-0000-0000-000000000000" else UploadType.USER_PROJECT

            logger.info(f"[DEBUG] Calling storage service with parameters - FRESH:")
            logger.info(f"  wiki_run_id: {wiki_run['id']}")
            logger.info(f"  upload_type: {upload_type}")
            logger.info(f"  username: {username}")
            logger.info(f"  project_slug: {project_slug}")
            logger.info(f"  index_run_id: {indexing_run['id']}")
            logger.info(f"  user_id: {project.get('user_id')}")
            logger.info(f"  project_id: {project['id']}")

            # Use unified storage parameters to get pages with correct paths
            wiki_pages_response = await storage_service.list_wiki_pages(
                wiki_run_id=str(wiki_run["id"]),
                upload_type=upload_type,
                username=username,
                project_slug=project_slug,
                index_run_id=indexing_run["id"],
                user_id=project.get("user_id"),
                project_id=project["id"]
            )

            logger.info(f"[DEBUG] Storage service returned: {wiki_pages_response}")
            wiki_pages = wiki_pages_response.get("pages", [])

            # Get metadata from database
            metadata = {}
        except Exception as e:
            logger.warning(f"Could not retrieve wiki pages from storage: {e}")
            logger.exception("Full traceback:")
            wiki_pages = []
            metadata = {}

        logger.info(
            "Retrieved project wiki",
            username=username,
            project_slug=project_slug,
            project_id=project["id"],
            wiki_run_id=wiki_run["id"],
            page_count=len(wiki_pages),
            is_authenticated=user.isAuthenticated if user else False
        )

        return {
            "wiki_pages": wiki_pages,
            "wiki_run": {
                "id": wiki_run["id"],
                "status": wiki_run["status"],
                "created_at": wiki_run["created_at"]
            },
            "indexing_run_id": indexing_run["id"],
            "metadata": metadata,
            "status": "success"
        }

    except Exception as e:
        logger.error(
            "Failed to retrieve project wiki",
            username=username,
            project_slug=project_slug,
            error=str(e)
        )
        raise HTTPException(500, "Failed to retrieve wiki")


# POST /api/projects/{username}/{project_slug}/queries
@router.post("/projects/{username}/{project_slug}/queries")
async def create_project_query(
    username: str,
    project_slug: str,
    question: str = Form(...),
    user: UserContext = Depends(get_user_context_optional)
):
    """Create and execute query within project context"""
    project_service = ProjectService(get_supabase_client())
    project = await project_service.get_project_by_slug(username, project_slug, user)

    if not project_service.can_access_resource(project, 'query', user):
        raise HTTPException(403, "Query access denied")

    # Execute query within project context
    try:
        from src.services.query_service import QueryService

        db = get_supabase_client()

        # Find the latest indexing run for this project
        indexing_runs_result = (
            db.table("indexing_runs")
            .select("id, status")
            .eq("project_id", project["id"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not indexing_runs_result.data:
            raise HTTPException(404, "No indexing run found for this project")

        indexing_run = indexing_runs_result.data[0]

        if indexing_run["status"] != "completed":
            return {
                "status": "indexing_not_complete",
                "message": f"Indexing is still {indexing_run['status']}. Please wait for indexing to complete before querying.",
                "indexing_run_id": indexing_run["id"]
            }

        # Create query using existing query service
        query_service = QueryService(db)

        # Create query with project context
        query_result = await query_service.create_query(
            question=question,
            user_id=user.id if user and user.isAuthenticated else None,
            index_run_id=indexing_run["id"],
            project_id=project["id"]
        )

        logger.info(
            "Created project query",
            username=username,
            project_slug=project_slug,
            project_id=project["id"],
            indexing_run_id=indexing_run["id"],
            query_id=query_result.get("id"),
            question_length=len(question),
            is_authenticated=user.isAuthenticated if user else False
        )

        return {
            "query": query_result,
            "project": {
                "id": project["id"],
                "name": project["name"],
                "username": project["username"],
                "project_slug": project["project_slug"]
            },
            "indexing_run_id": indexing_run["id"],
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create project query",
            username=username,
            project_slug=project_slug,
            question=question[:100],  # Truncate for logging
            error=str(e)
        )
        raise HTTPException(500, "Failed to execute query")


# GET /api/projects/{username}/{project_slug}/queries
@router.get("/projects/{username}/{project_slug}/queries")
async def list_project_queries(
    username: str,
    project_slug: str,
    limit: int = 20,
    offset: int = 0,
    user: UserContext = Depends(get_user_context_optional)
):
    """List queries for a project"""
    project_service = ProjectService(get_supabase_client())
    project = await project_service.get_project_by_slug(username, project_slug, user)

    if not project_service.can_access_resource(project, 'read', user):
        raise HTTPException(403, "Access denied")

    # Get project queries
    try:
        db = get_supabase_client()

        # Get queries for this project
        queries_result = (
            db.table("query_runs")
            .select("*")
            .eq("project_id", project["id"])
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        queries = queries_result.data or []

        # Get total count
        count_result = (
            db.table("query_runs")
            .select("id", count="exact")
            .eq("project_id", project["id"])
            .execute()
        )

        total_count = count_result.count or 0

        logger.info(
            "Listed project queries",
            username=username,
            project_slug=project_slug,
            project_id=project["id"],
            query_count=len(queries),
            total_count=total_count,
            is_authenticated=user.isAuthenticated if user else False
        )

        return {
            "queries": queries,
            "total_count": total_count,
            "has_more": (offset + limit) < total_count,
            "project": {
                "id": project["id"],
                "name": project["name"],
                "username": project["username"],
                "project_slug": project["project_slug"]
            }
        }

    except Exception as e:
        logger.error(
            "Failed to list project queries",
            username=username,
            project_slug=project_slug,
            error=str(e)
        )
        raise HTTPException(500, "Failed to list queries")


# GET /api/projects/{username}/{project_slug}/runs
@router.get("/projects/{username}/{project_slug}/runs")
async def list_project_runs(
    username: str,
    project_slug: str,
    user: UserContext = Depends(get_user_context_optional)
):
    """List all runs for a project"""
    project_service = ProjectService(get_supabase_client())
    project = await project_service.get_project_by_slug(username, project_slug, user)

    if not project_service.can_access_resource(project, 'read', user):
        raise HTTPException(403, "Access denied")

    # Get project indexing runs
    try:
        db = get_supabase_client()

        # Get indexing runs for this project
        indexing_runs_result = (
            db.table("indexing_runs")
            .select("*")
            .eq("project_id", project["id"])
            .order("created_at", desc=True)
            .execute()
        )

        indexing_runs = indexing_runs_result.data or []

        logger.info(
            "Listed project indexing runs",
            username=username,
            project_slug=project_slug,
            project_id=project["id"],
            runs_count=len(indexing_runs),
            is_authenticated=user.isAuthenticated if user else False
        )

        return {
            "runs": indexing_runs,
            "total_count": len(indexing_runs),
            "project": {
                "id": project["id"],
                "name": project["name"],
                "username": project["username"],
                "project_slug": project["project_slug"]
            }
        }

    except Exception as e:
        logger.error(
            "Failed to list project indexing runs",
            username=username,
            project_slug=project_slug,
            error=str(e)
        )
        raise HTTPException(500, "Failed to list indexing runs")


# GET /api/projects/{username}/{project_slug}/runs/{run_id}
@router.get("/projects/{username}/{project_slug}/runs/{run_id}")
async def get_project_run(
    username: str,
    project_slug: str,
    run_id: str,
    user: UserContext = Depends(get_user_context_optional)
):
    """Get specific run details"""
    project_service = ProjectService(get_supabase_client())
    project = await project_service.get_project_by_slug(username, project_slug, user)

    if not project_service.can_access_resource(project, 'read', user):
        raise HTTPException(403, "Access denied")

    # Get specific indexing run
    try:
        db = get_supabase_client()

        # Get the specific indexing run for this project
        indexing_run_result = (
            db.table("indexing_runs")
            .select("*")
            .eq("id", run_id)
            .eq("project_id", project["id"])
            .execute()
        )

        if not indexing_run_result.data:
            raise HTTPException(404, "Run not found")

        indexing_run = indexing_run_result.data[0]

        logger.info(
            "Retrieved project run details",
            username=username,
            project_slug=project_slug,
            project_id=project["id"],
            run_id=run_id,
            run_status=indexing_run.get("status"),
            is_authenticated=user.isAuthenticated if user else False
        )

        return {
            "run": indexing_run,
            "project": {
                "id": project["id"],
                "name": project["name"],
                "username": project["username"],
                "project_slug": project["project_slug"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get project run details",
            username=username,
            project_slug=project_slug,
            run_id=run_id,
            error=str(e)
        )
        raise HTTPException(500, "Failed to get run details")