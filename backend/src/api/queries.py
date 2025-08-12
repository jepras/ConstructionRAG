"""Flat Query API with optional auth and access-aware scoping."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.config.database import (
    get_db_client_for_request,
    get_supabase_admin_client,
    get_supabase_client,
)
from src.pipeline.querying.models import QueryRequest
from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
from src.services.auth_service import get_current_user_optional
from src.services.query_service import QueryReadService, QueryService
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError
from src.utils.logging import get_logger

logger = get_logger(__name__)

flat_router = APIRouter(prefix="/api", tags=["Queries"])  # v2 flat routes


# Module-level FastAPI dependency placeholders to satisfy linter
DB_CLIENT_DEP = Depends(get_db_client_for_request)
CURRENT_USER_DEP = Depends(get_current_user_optional)


async def get_query_orchestrator(
    db_client=DB_CLIENT_DEP,
) -> QueryPipelineOrchestrator:
    """Provide orchestrator bound to request-scoped client for RLS-aware retrieval."""
    return QueryPipelineOrchestrator(db_client=db_client)


## Legacy endpoint cluster removed in v2


# ---------------- Flat resource endpoints (Phase 8) ----------------


class CreateQueryRequest(BaseModel):
    query: str
    indexing_run_id: str | None = None


ORCH_DEP = Depends(get_query_orchestrator)


@flat_router.post("/queries", response_model=dict)
async def create_query(
    payload: CreateQueryRequest,
    current_user: dict[str, Any] | None = CURRENT_USER_DEP,
    orchestrator: QueryPipelineOrchestrator = ORCH_DEP,
):
    svc = QueryService()
    result = await svc.create_query(
        user=current_user,
        query_text=payload.query,
        indexing_run_id=payload.indexing_run_id,
        orchestrator=orchestrator,
    )
    return result


@flat_router.get("/queries", response_model=list[dict])
async def list_queries(
    limit: int = 20,
    offset: int = 0,
    current_user: dict[str, Any] | None = CURRENT_USER_DEP,
    db_client=DB_CLIENT_DEP,
):
    reader = QueryReadService(client=db_client)
    return reader.list_queries(user=current_user, limit=min(limit, 100), offset=max(offset, 0))


@flat_router.get("/queries/{query_id}", response_model=dict)
async def get_query(
    query_id: str,
    current_user: dict[str, Any] | None = CURRENT_USER_DEP,
    db_client=DB_CLIENT_DEP,
):
    reader = QueryReadService(client=db_client)
    row = reader.get_query(query_id=query_id, user=current_user)
    if not row:
        raise AppError("Query not found", error_code=ErrorCode.NOT_FOUND)
    return row


## Legacy history endpoint removed in v2


## Legacy feedback endpoint removed in v2


## Legacy quality dashboard removed in v2


async def store_error_query(request: QueryRequest, error_message: str):
    """Store failed query in database for analytics"""
    try:
        # Use anon when possible; fall back to admin if user_id is absent (anonymous error)
        db = get_supabase_client() if getattr(request, "user_id", None) else get_supabase_admin_client()

        await (
            db.table("query_runs")
            .insert(
                {
                    "user_id": request.user_id,
                    "original_query": request.query,
                    "error_message": error_message,
                    "response_time_ms": 0,
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
            .execute()
        )

    except Exception as e:
        logger.error(f"Failed to store error query: {e}")
