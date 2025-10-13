"""Pipeline API endpoints for managing indexing and query pipelines."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

try:
    pass
except Exception:
    raise

from ..config.database import get_db_client_for_request, get_supabase_client
from ..services.auth_service import get_current_user_optional
from ..services.pipeline_read_service import PipelineReadService
from ..services.pipeline_service import PipelineService
from ..shared.errors import ErrorCode
from ..utils.exceptions import AppError

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

logger = logging.getLogger(__name__)

flat_router = APIRouter(prefix="/api", tags=["IndexingRuns"])


## Legacy /pipeline endpoints removed in v2


## Legacy /pipeline endpoints removed in v2


## Legacy /pipeline endpoints removed in v2


## Legacy /pipeline endpoints removed in v2


## Legacy /pipeline endpoints removed in v2


## Legacy helper removed with legacy endpoints


## Legacy /pipeline endpoints removed in v2


## Legacy /pipeline endpoints removed in v2


## Legacy /pipeline endpoints removed in v2


# Flat resource endpoints for indexing runs


@flat_router.get("/indexing-runs-with-wikis", response_model=list[dict[str, Any]])
async def list_indexing_runs_with_wikis(
    limit: int = 20,
    offset: int = 0,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
):
    """List public projects that have completed wikis using the project_wikis junction table.

    Returns only public projects with completed wikis, regardless of authentication status.
    This endpoint is used on the /projects page for anonymous and authenticated users.
    Authenticated users should use /api/user-projects-with-wikis for their private projects.
    """
    try:
        db = get_supabase_client()
        
        # Check if project_wikis table exists, fallback to old method if not
        try:
            test_query = db.table("project_wikis").select("id").limit(1)
            test_res = test_query.execute()
            logger.info("Using project_wikis junction table")
            use_junction_table = True
        except Exception as test_e:
            logger.warning(f"project_wikis table not available, using fallback: {test_e}")
            use_junction_table = False
        
        if use_junction_table:
            # Use efficient junction table query with wiki data join
            query = (
                db.table("project_wikis")
                .select("""
                    *,
                    wiki_generation_runs!project_wikis_wiki_run_id_fkey(
                        wiki_structure,
                        pages_metadata,
                        language
                    ),
                    projects!inner(
                        visibility,
                        username,
                        project_slug
                    )
                """)
                .eq("wiki_status", "completed")
                .eq("access_level", "public")
                .eq("projects.visibility", "public")
                .gt("pages_count", 0)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
            )
            
            res = query.execute()
            
            # Transform the response to flatten the wiki data
            result_data = []
            for row in res.data or []:
                wiki_data = row.get("wiki_generation_runs")
                if wiki_data:
                    # Flatten the wiki data into the main response
                    flattened_row = {**row}
                    flattened_row["wiki_structure"] = wiki_data.get("wiki_structure", {})
                    flattened_row["pages_metadata"] = wiki_data.get("pages_metadata", [])
                    flattened_row["language"] = wiki_data.get("language")
                    # Remove the nested object
                    flattened_row.pop("wiki_generation_runs", None)
                    result_data.append(flattened_row)
                else:
                    # Fallback if no wiki data found
                    row["wiki_structure"] = {}
                    row["pages_metadata"] = []
                    row["language"] = None
                    result_data.append(row)
            
            return result_data
        
        else:
            # Fallback to old cross-table query method (simplified for now)
            return []
        
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to list indexing runs with wikis: {e}")
        from ..shared.errors import ErrorCode
        from ..utils.exceptions import AppError
        raise AppError("Failed to list indexing runs with wikis", error_code=ErrorCode.INTERNAL_ERROR) from e


@flat_router.get("/user-projects-with-wikis", response_model=list[dict[str, Any]])
async def list_user_projects_with_wikis(
    limit: int = 50,
    offset: int = 0,
    current_user: dict[str, Any] = Depends(get_current_user),
    db_client=Depends(get_db_client_for_request),
):
    """List user's projects that have completed wikis using the project_wikis junction table.
    
    Returns project data grouped by project_id with latest completed wiki for each project.
    Requires authentication.
    """
    try:
        logger.info(f"🔍 list_user_projects_with_wikis called - user_id: {current_user.get('id', 'NONE')}")
        db = db_client  # Use authenticated client for RLS
        
        # Check if project_wikis table exists
        try:
            test_query = db.table("project_wikis").select("id").limit(1)
            test_res = test_query.execute()
            logger.info("✅ Using project_wikis junction table for user projects")
        except Exception as test_e:
            logger.warning(f"❌ project_wikis table not available: {test_e}")
            # Fallback: return empty for now - could implement legacy logic if needed
            return []
        
        # Start with a basic query to see what exists
        basic_query = (
            db.table("project_wikis")
            .select("*, projects!inner(visibility)")
            .eq("user_id", current_user["id"])
            .neq("projects.visibility", "public")  # Get user's private/internal projects
            .limit(10)
        )

        logger.info(f"🔍 First checking basic query: user_id={current_user['id']}, non-public projects")
        basic_res = basic_query.execute()
        logger.info(f"🔢 Basic query returned {len(basic_res.data or [])} rows")
        
        for row in basic_res.data or []:
            logger.info(f"🐛 Found: project_id={row.get('project_id')}, wiki_status={row.get('wiki_status')}, pages_count={row.get('pages_count')}")
        
        # Now apply the full query with joins and proper filters
        query = (
            db.table("project_wikis")
            .select("""
                *,
                wiki_generation_runs!project_wikis_wiki_run_id_fkey(
                    wiki_structure,
                    pages_metadata,
                    language
                )
            """)
            .eq("user_id", current_user["id"])
            .neq("projects.visibility", "public")  # Get user's private/internal projects
            .eq("wiki_status", "completed")
            .gt("pages_count", 0)
            .order("project_id, created_at", desc=True)
        )

        logger.info(f"🔍 Full query filters: user_id={current_user['id']}, non-public projects, wiki_status=completed, pages_count>0")
        
        logger.info(f"📊 Executing query for user {current_user['id']}")
        res = query.execute()
        logger.info(f"🔢 Query returned {len(res.data or [])} rows")
        
        # Group by project_id and take the latest wiki for each project
        projects_dict = {}
        project_ids = set()
        
        # First pass: collect data and project IDs
        for row in res.data or []:
            project_id = row.get("project_id")
            if not project_id:
                logger.warning(f"⚠️ Row missing project_id: {row}")
                continue
                
            project_ids.add(project_id)
            
            # Skip if we already have this project (since we ordered by created_at desc, first is latest)
            if project_id in projects_dict:
                continue
                
            wiki_data = row.get("wiki_generation_runs")
            
            # Store project_wikis data with wiki info
            projects_dict[project_id] = {
                "project_id": project_id,
                "indexing_run_id": row.get("indexing_run_id"),
                "wiki_run_id": row.get("wiki_run_id"),
                "project_name": row.get("project_name"),  # From project_wikis table
                "visibility": row.get("projects", {}).get("visibility", "private"),
                "access_level": row.get("access_level"),
                "user_id": row.get("user_id"),
                "pages_count": row.get("pages_count", 0),
                "total_word_count": row.get("total_word_count", 0),
                "wiki_status": row.get("wiki_status"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "wiki_structure": wiki_data.get("wiki_structure", {}) if wiki_data else {},
                "pages_metadata": wiki_data.get("pages_metadata", []) if wiki_data else [],
                "language": wiki_data.get("language", "danish") if wiki_data else "danish",
            }
        
        # Second pass: enrich with project data from projects table
        if project_ids:
            projects_query = (
                db.table("projects")
                .select("id, name, description, created_at, updated_at")
                .in_("id", list(project_ids))
                .is_("deleted_at", "null")
            )
            projects_res = projects_query.execute()
            
            # Update project names and descriptions
            for project_row in projects_res.data or []:
                project_id = project_row.get("id")
                if project_id in projects_dict:
                    projects_dict[project_id]["project_name"] = project_row.get("name") or projects_dict[project_id]["project_name"]
                    projects_dict[project_id]["project_description"] = project_row.get("description")
                    projects_dict[project_id]["project_created_at"] = project_row.get("created_at")
                    projects_dict[project_id]["project_updated_at"] = project_row.get("updated_at")
        
        # Convert to list and apply pagination
        result_data = list(projects_dict.values())
        
        # Sort by updated_at desc (most recently updated first)
        result_data.sort(key=lambda x: x.get("project_updated_at") or x.get("updated_at", ""), reverse=True)
        
        # Apply pagination
        start_idx = offset
        end_idx = offset + limit
        paginated_data = result_data[start_idx:end_idx]
        
        logger.info(f"✅ Returning {len(paginated_data)} projects for user {current_user['id']}")
        return paginated_data
        
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to list user projects with wikis: {e}")
        from ..shared.errors import ErrorCode
        from ..utils.exceptions import AppError
        raise AppError("Failed to list user projects with wikis", error_code=ErrorCode.INTERNAL_ERROR) from e



@flat_router.get("/indexing-runs", response_model=list[dict[str, Any]])
async def list_indexing_runs(
    project_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
    db_client=Depends(get_db_client_for_request),
):
    """Flat list endpoint for indexing runs.
    
    - If authenticated: scoped to user's projects
    - If anonymous: only shows email upload types (public access)
    """
    try:
        db = get_supabase_client()
        
        if current_user is None:
            # Anonymous access: only show public projects
            res = (
                db.table("indexing_runs")
                .select("indexing_runs.id, indexing_runs.project_id, indexing_runs.status, indexing_runs.started_at, indexing_runs.completed_at, indexing_runs.error_message, projects.visibility")
                .join("projects", "indexing_runs.project_id = projects.id")
                .eq("projects.visibility", "public")
                .order("started_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return list(res.data or [])
        
        # Authenticated user logic
        reader = PipelineReadService(client=db_client)
        if project_id is None:
            # Fallback to recent runs across all user's projects
            runs = reader.list_recent_runs_for_user(current_user["id"], limit=min(limit, 50))
            return runs
        # Filter by specific project
        # Simple select with ownership check similar to get_run_for_user
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
            .select("id, project_id, status, started_at, completed_at, error_message, projects!inner(visibility)")
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
):
    """Flat get endpoint for a single indexing run.

    - If authenticated: ensure access via PipelineReadService.
    - If anonymous: allow only when run is from email uploads.
    """
    reader = PipelineReadService()
    # Use anon for authenticated users; admin for anonymous lookup
    svc = PipelineService(use_admin_client=not bool(current_user))
    run = await svc.get_indexing_run(run_id)
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
        # Anonymous users can only access public projects
        # Get project visibility for this indexing run
        project_result = (
            svc.supabase.table("projects")
            .select("visibility")
            .eq("id", str(run.project_id))
            .execute()
        )
        if not project_result.data or project_result.data[0].get("visibility") != "public":
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Access denied: Authentication required", error_code=ErrorCode.ACCESS_DENIED)

    # Get project visibility for response
    project_result = (
        svc.supabase.table("projects")
        .select("visibility")
        .eq("id", str(run.project_id))
        .execute()
    )
    visibility = project_result.data[0].get("visibility", "private") if project_result.data else "private"

    return {
        "id": str(run.id),
        "visibility": visibility,
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
):
    """Flat progress endpoint mirroring the pipeline progress, with optional auth."""
    reader = PipelineReadService()
    svc = PipelineService(use_admin_client=not bool(current_user))
    run = await svc.get_indexing_run(run_id)
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
        # Anonymous users can only access public projects
        # Get project visibility for this indexing run
        project_result = (
            svc.supabase.table("projects")
            .select("visibility")
            .eq("id", str(run.project_id))
            .execute()
        )
        if not project_result.data or project_result.data[0].get("visibility") != "public":
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Access denied: Authentication required", error_code=ErrorCode.ACCESS_DENIED)

    documents_result = (
        svc.supabase.table("indexing_run_documents").select("document_id").eq("indexing_run_id", str(run_id)).execute()
    )
    document_ids = [doc["document_id"] for doc in (documents_result.data or [])]

    document_status: dict[str, Any] = {}
    if document_ids:
        documents_result = (
            svc.supabase.table("documents").select("id, filename, step_results").in_("id", document_ids).execute()
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
                "current_step": _infer_current_step(step_results),
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

    # Get project visibility for response
    project_result = (
        svc.supabase.table("projects")
        .select("visibility")
        .eq("id", str(run.project_id))
        .execute()
    )
    visibility = project_result.data[0].get("visibility", "private") if project_result.data else "private"

    return {
        "run_id": str(run_id),
        "status": run.status,
        "visibility": visibility,
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


def _infer_current_step(step_results: dict) -> str:
    if not step_results:
        return "waiting"
    steps = ["partition", "metadata", "enrichment", "chunking", "embedding"]
    for step in steps:
        if step not in step_results:
            return step
        if step_results[step].get("status") != "completed":
            return step
    return "completed"


@flat_router.get("/indexing-runs/{run_id}/summary", response_model=dict[str, Any])
async def get_flat_indexing_run_summary(
    run_id: UUID,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
):
    """Lightweight summary endpoint for indexing run statistics.
    
    Returns only essential data for summary bars: PDF count, names, page count,
    image count, table count, chunk count, and last updated timestamp.
    """
    try:
        reader = PipelineReadService()
        svc = PipelineService(use_admin_client=not bool(current_user))
        run = await svc.get_indexing_run(run_id)
        if not run:
            from ..shared.errors import ErrorCode
            from ..utils.exceptions import AppError

            raise AppError("Indexing run not found", error_code=ErrorCode.NOT_FOUND)
        
        # Access control (same logic as progress endpoint)
        if current_user:
            allowed = reader.get_run_for_user(str(run_id), current_user["id"])
            if not allowed:
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

                raise AppError("Indexing run not found or access denied", error_code=ErrorCode.NOT_FOUND)
        else:
            # Anonymous users can only access public projects
            # Get project visibility for this indexing run
            project_result = (
                svc.supabase.table("projects")
                .select("visibility")
                .eq("id", str(run.project_id))
                .execute()
            )
            if not project_result.data or project_result.data[0].get("visibility") != "public":
                from ..shared.errors import ErrorCode
                from ..utils.exceptions import AppError

                raise AppError("Access denied: Authentication required", error_code=ErrorCode.ACCESS_DENIED)

        # Get documents linked to this indexing run
        documents_result = (
            svc.supabase.table("indexing_run_documents").select("document_id").eq("indexing_run_id", str(run_id)).execute()
        )
        document_ids = [doc["document_id"] for doc in (documents_result.data or [])]

        # Initialize counters
        pdf_names = []
        total_pages = 0
        total_images = 0
        total_tables = 0
        total_chunks = 0

        if document_ids:
            documents_result = (
                svc.supabase.table("documents").select("id, filename, step_results").in_("id", document_ids).execute()
            )
            
            for doc in documents_result.data or []:
                pdf_names.append(doc["filename"])
                step_results = doc.get("step_results", {})
                
                # Extract page count from PartitionStep
                partition_step = step_results.get("PartitionStep", {})
                if partition_step.get("summary_stats", {}).get("document_metadata", {}).get("total_pages"):
                    total_pages += partition_step["summary_stats"]["document_metadata"]["total_pages"]
                
                # Extract image and table counts from EnrichmentStep
                enrichment_step = step_results.get("EnrichmentStep", {})
                if enrichment_step.get("summary_stats"):
                    total_images += enrichment_step["summary_stats"].get("images_processed", 0)
                    total_tables += enrichment_step["summary_stats"].get("tables_processed", 0)
                
                # Extract chunk count from ChunkingStep
                chunking_step = step_results.get("ChunkingStep", {})
                if chunking_step.get("summary_stats", {}).get("total_chunks_created"):
                    total_chunks += chunking_step["summary_stats"]["total_chunks_created"]

        return {
            "run_id": str(run_id),
            "pdf_count": len(pdf_names),
            "pdf_names": pdf_names,
            "total_pages": total_pages,
            "total_images": total_images,
            "total_tables": total_tables,
            "total_chunks": total_chunks,
            "last_updated": run.completed_at.isoformat() if run.completed_at else (run.started_at.isoformat() if run.started_at else None),
            "status": run.status,
        }
    
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Failed to get indexing run summary for {run_id}: {e}")
        from ..shared.errors import ErrorCode
        from ..utils.exceptions import AppError
        raise AppError("Failed to get indexing run summary", error_code=ErrorCode.INTERNAL_ERROR) from e


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
            user_id=UUID(current_user["id"]),
            project_id=project_id,
        )
        # Get project visibility for response
        project_result = (
            pipeline_service.supabase.table("projects")
            .select("visibility")
            .eq("id", str(run.project_id))
            .execute()
        )
        visibility = project_result.data[0].get("visibility", "private") if project_result.data else "private"

        return {
            "id": str(run.id),
            "visibility": visibility,
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
