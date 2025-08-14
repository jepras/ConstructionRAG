from __future__ import annotations

from typing import Any

from src.config.database import get_supabase_client
from src.services.db_service import DbService
from src.utils.exceptions import DatabaseError
from src.utils.logging import get_logger
from supabase import Client


class PipelineReadService:
    """Read-side helpers for indexing runs with basic access checks.

    Phase 4 scope: filter by user's projects; exclude unrelated runs.
    """

    def __init__(self, client: Client | None = None) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.db = client or get_supabase_client()
        self.crud = DbService(client=self.db)

    def _get_user_project_ids(self, user_id: str) -> list[str]:
        try:
            res = self.db.table("projects").select("id").eq("user_id", user_id).execute()
            return [row["id"] for row in (res.data or [])]
        except Exception as exc:  # noqa: BLE001
            self.logger.error("list user projects failed", user_id=user_id, error=str(exc))
            raise DatabaseError("Failed to list user projects") from exc

    def list_recent_runs_for_user(self, user_id: str, limit: int = 5) -> list[dict[str, Any]]:
        project_ids = self._get_user_project_ids(user_id)
        if not project_ids:
            return []
        try:
            q = (
                self.db.table("indexing_runs")
                .select("id, upload_type, project_id, status, started_at, completed_at, error_message")
                .in_("project_id", project_ids)
                .order("started_at", desc=True)
                .limit(limit)
            )
            res = q.execute()
            return list(res.data or [])
        except Exception as exc:  # noqa: BLE001
            self.logger.error("list runs failed", user_id=user_id, error=str(exc))
            raise DatabaseError("Failed to get indexing runs") from exc

    def get_run_for_user(self, run_id: str, user_id: str) -> dict[str, Any] | None:
        try:
            self.logger.info(f"🔍 PipelineReadService.get_run_for_user called with run_id={run_id}, user_id={user_id}")
            self.logger.info(f"🔧 Database client type: {type(self.db).__name__}")
            
            # The critical RLS query - this will fail if JWT context is missing
            res = self.db.table("indexing_runs").select("*").eq("id", run_id).limit(1).execute()
            self.logger.info(f"📊 RLS query result: found {len(res.data) if res.data else 0} rows")
            
            if not res.data:
                self.logger.warning(f"⚠️ No data returned from indexing_runs query - likely RLS policy blocked access")
                return None
                
            run = dict(res.data[0])
            self.logger.info(f"✅ Found indexing run: {run.get('id')} with user_id={run.get('user_id')}")
            
            project_id = run.get("project_id")
            if project_id is None:
                # Email uploads: allow access if public/auth; default to public for email
                self.logger.info(f"📧 Email upload path - access_level: {run.get('access_level')}")
                if run.get("access_level") in {"public", "auth"}:
                    self.logger.info("✅ Email upload access granted")
                    return run
                self.logger.warning("❌ Email upload access denied - not public/auth")
                return None
                
            # Ensure user owns the project
            self.logger.info(f"🏗️ Project upload path - checking project ownership for project_id: {project_id}")
            proj = self.db.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).limit(1).execute()
            if not proj.data:
                self.logger.warning(f"❌ Project ownership check failed - no project found for user {user_id}")
                return None
                
            self.logger.info("✅ Project ownership verified - access granted")
            return run
        except Exception as exc:  # noqa: BLE001
            self.logger.error(f"❌ get_run_for_user failed: run_id={run_id}, user_id={user_id}, error={str(exc)}")
            raise DatabaseError("Failed to get indexing run") from exc
