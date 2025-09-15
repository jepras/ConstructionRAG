from __future__ import annotations

from typing import Any
from uuid import UUID

from src.config.database import get_supabase_admin_client, get_supabase_client
from src.pipeline.querying.models import QueryRequest
from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError, DatabaseError
from src.utils.logging import get_logger
from supabase import Client


class QueryService:
    """Create/query runs with access-aware scoping and SoT invariants.

    - Anonymous queries: scope to public content only and mark run as public
    - Authenticated queries: scope to public + auth + owned content; mark run as private
    """

    def __init__(self, client: Client | None = None) -> None:
        self.logger = get_logger(self.__class__.__name__)
        # Read-side queries should use normal client; orchestrator uses admin as needed
        self.db = client or get_supabase_client()
        self.admin = get_supabase_admin_client()

    def _resolve_accessible_document_ids(
        self, *, user: dict[str, Any] | None, indexing_run_id: str | None
    ) -> list[str] | None:
        """Resolve list of document IDs accessible to the caller.

        Returns None to indicate "no additional filter" when indexing_run_id is provided
        and access is verified via run-level checks.
        """
        try:
            # If specific run is targeted, rely on run-level scoping via join table
            if indexing_run_id:
                self.logger.info(f"🔍 Resolving access for indexing_run_id: {indexing_run_id}")
                self.logger.info(f"🔍 User context: {user['id'] if user else 'anonymous'}")

                # For anonymous: verify the run is public/auth and from email uploads
                # For authenticated: ensure ownership or public/auth
                run_res = (
                    self.db.table("indexing_runs")
                    .select("id, upload_type, project_id, user_id, access_level")
                    .eq("id", indexing_run_id)
                    .limit(1)
                    .execute()
                )

                self.logger.info(f"🔍 Database query result: {run_res.data}")
                self.logger.info(f"🔍 Query status: {getattr(run_res, 'status', 'unknown')}")

                if not run_res.data:
                    self.logger.error(f"❌ No indexing run found for ID: {indexing_run_id}")
                    raise AppError("Indexing run not found", error_code=ErrorCode.NOT_FOUND)

                run = run_res.data[0]
                self.logger.info(f"🔍 Run data: {run}")

                if user is None:
                    self.logger.info(
                        f"🔍 Anonymous user check - access_level: {run.get('access_level')}, upload_type: {run.get('upload_type')}"
                    )
                    if run.get("access_level") not in {"public", "auth"} or run.get("upload_type") != "email":
                        self.logger.error(
                            f"❌ Access denied for anonymous user - access_level: {run.get('access_level')}, upload_type: {run.get('upload_type')}"
                        )
                        raise AppError("Access denied", error_code=ErrorCode.AUTHORIZATION_FAILED)
                    self.logger.info("✅ Anonymous user access granted")
                else:
                    self.logger.info(f"🔍 Authenticated user check - user_id: {user['id']}")
                    # Owner check for project runs; allow public/auth for non-project runs
                    project_id = run.get("project_id")
                    if project_id:
                        self.logger.info(f"🔍 Checking project ownership for project_id: {project_id}")
                        proj = (
                            self.db.table("projects")
                            .select("id")
                            .eq("id", project_id)
                            .eq("user_id", user["id"])
                            .limit(1)
                            .execute()
                        )
                        if not proj.data:
                            self.logger.error(f"❌ Project ownership check failed for project_id: {project_id}")
                            raise AppError("Indexing run not found", error_code=ErrorCode.NOT_FOUND)
                        self.logger.info("✅ Project ownership verified")
                    else:
                        self.logger.info("✅ No project_id - allowing access")

                # We will filter by run via join table in retrieval; return None to skip document id filter
                self.logger.info("✅ Access control passed - returning None for document filtering")
                return None

            # No specific run provided → resolve accessible documents
            if user is None:
                # Anonymous → public only
                res = self.db.table("documents").select("id").eq("access_level", "public").execute()
                return [row["id"] for row in (res.data or [])]

            # Authenticated → public + auth + owned (private/owner)
            public_res = self.db.table("documents").select("id").in_("access_level", ["public", "auth"]).execute()
            owned_res = self.db.table("documents").select("id").eq("user_id", user["id"]).execute()
            ids: set[str] = set()
            ids.update([row["id"] for row in (public_res.data or [])])
            ids.update([row["id"] for row in (owned_res.data or [])])
            return list(ids)
        except AppError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.logger.error("resolve accessible documents failed", error=str(exc))
            raise DatabaseError("Failed to resolve accessible content") from exc

    async def create_query(
        self,
        *,
        user: dict[str, Any] | None,
        query_text: str,
        indexing_run_id: str | None = None,
        orchestrator: QueryPipelineOrchestrator | None = None,
    ) -> dict[str, Any]:
        """Create and execute a query with access-aware scoping."""

        if not query_text or not query_text.strip():
            raise AppError("Query text is required", error_code=ErrorCode.VALIDATION_ERROR)

        allowed_ids = self._resolve_accessible_document_ids(user=user, indexing_run_id=indexing_run_id)

        # 🆕 CRITICAL: Fetch language from stored config when indexing_run_id is provided
        language = "english"  # default fallback
        if indexing_run_id:
            try:
                self.logger.info(f"🔄 Query: Fetching stored config for indexing run {indexing_run_id}")
                result = self.db.table("indexing_runs").select("pipeline_config").eq("id", indexing_run_id).execute()
                
                if result.data and result.data[0].get("pipeline_config"):
                    pipeline_config = result.data[0]["pipeline_config"]
                    language = pipeline_config.get("defaults", {}).get("language", "english")
                    self.logger.info(f"✅ Query: Using language from stored config: {language}")
                else:
                    self.logger.warning(f"⚠️ Query: No stored config found for run {indexing_run_id}, using default: {language}")
            except Exception as e:
                self.logger.error(f"❌ Query: Failed to fetch stored config: {e}, using default: {language}")

        req = QueryRequest(
            query=query_text.strip(),
            user_id=(user["id"] if user else None),
            indexing_run_id=(UUID(indexing_run_id) if indexing_run_id else None),
            allowed_document_ids=allowed_ids,
        )

        orch = orchestrator or QueryPipelineOrchestrator()
        resp = await orch.process_query(req, language=language)  # 🆕 Pass language

        # Wrap response with minimal envelope. The orchestrator stores the run and sets access_level.
        return {
            "response": resp.response,
            "search_results": [r.model_dump(exclude_none=True) for r in resp.search_results],
            "performance_metrics": resp.performance_metrics,
            "quality_metrics": (resp.quality_metrics.model_dump(exclude_none=True) if resp.quality_metrics else None),
            "step_timings": resp.step_timings,
        }


class QueryReadService:
    """Read-side helpers for query runs with access checks."""

    def __init__(self, client: Client | None = None) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.db = client or get_supabase_client()

    def list_queries(self, *, user: dict[str, Any] | None, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        try:
            if user is None:
                res = (
                    self.db.table("query_runs")
                    .select("id, original_query, final_response, created_at, access_level")
                    .eq("access_level", "public")
                    .order("created_at", desc=True)
                    .range(offset, offset + limit - 1)
                    .execute()
                )
                return list(res.data or [])
            # Authenticated: own private + public + auth
            own = (
                self.db.table("query_runs")
                .select("id, original_query, final_response, created_at, access_level")
                .eq("user_id", user["id"])
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            public_auth = (
                self.db.table("query_runs")
                .select("id, original_query, final_response, created_at, access_level")
                .in_("access_level", ["public", "auth"])
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            merged: dict[str, dict[str, Any]] = {}
            for row in public_auth.data or []:
                merged[row["id"]] = row
            for row in own.data or []:
                merged[row["id"]] = row
            # Return most recent first
            return sorted(merged.values(), key=lambda r: r["created_at"], reverse=True)[:limit]
        except Exception as exc:  # noqa: BLE001
            self.logger.error("list queries failed", error=str(exc))
            raise DatabaseError("Failed to list queries") from exc

    def get_query(self, *, query_id: str, user: dict[str, Any] | None) -> dict[str, Any] | None:
        try:
            res = self.db.table("query_runs").select("*").eq("id", query_id).limit(1).execute()
            if not res.data:
                return None
            row = dict(res.data[0])
            access = row.get("access_level", "private")
            if access == "public":
                return row
            if access == "auth":
                if user is None:
                    return None
                return row
            # private/owner → must be owner
            if user and row.get("user_id") == user["id"]:
                return row
            return None
        except Exception as exc:  # noqa: BLE001
            self.logger.error("get query failed", query_id=query_id, error=str(exc))
            raise DatabaseError("Failed to get query") from exc
