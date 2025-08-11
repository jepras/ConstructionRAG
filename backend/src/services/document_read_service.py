from __future__ import annotations

from typing import Any

from src.config.database import get_supabase_client
from src.services.db_service import DbService
from src.utils.exceptions import DatabaseError
from src.utils.logging import get_logger
from supabase import Client


class DocumentReadService:
    """Read-side helpers for documents with basic access checks."""

    def __init__(self, client: Client | None = None) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.db = client or get_supabase_client()
        self.crud = DbService(client=self.db)

    def _ensure_project_owned(self, user_id: str, project_id: str) -> None:
        try:
            res = self.db.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).limit(1).execute()
            if not res.data:
                raise DatabaseError("Project not found or access denied")
        except DatabaseError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.logger.error("project ownership check failed", user_id=user_id, project_id=project_id, error=str(exc))
            raise DatabaseError("Failed to verify project ownership") from exc

    def list_project_documents(
        self, user_id: str, project_id: str, *, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        self._ensure_project_owned(user_id, project_id)
        try:
            res = (
                self.db.table("documents")
                .select("*")
                .eq("project_id", project_id)
                .in_("access_level", ["private", "owner", "auth", "public"])  # project owner can see all
                .range(offset, offset + limit - 1)
                .execute()
            )
            return list(res.data or [])
        except Exception as exc:  # noqa: BLE001
            self.logger.error("list documents failed", user_id=user_id, project_id=project_id, error=str(exc))
            raise DatabaseError("Failed to get documents") from exc

    def get_project_document(self, user_id: str, project_id: str, document_id: str) -> dict[str, Any] | None:
        self._ensure_project_owned(user_id, project_id)
        try:
            res = (
                self.db.table("documents")
                .select("*")
                .eq("id", document_id)
                .eq("project_id", project_id)
                .eq("user_id", user_id)
                .in_("access_level", ["private", "owner", "auth", "public"])  # owner has full access
                .limit(1)
                .execute()
            )
            if not res.data:
                return None
            return dict(res.data[0])
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "get document failed", user_id=user_id, project_id=project_id, document_id=document_id, error=str(exc)
            )
            raise DatabaseError("Failed to get document") from exc
