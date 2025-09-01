"""Service for CRUD operations on projects (RLS-aware)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from src.models.pipeline import Project, ProjectCreate, ProjectUpdate
from src.utils.logging import get_logger

logger = get_logger(__name__)

try:  # pragma: no cover - optional for type hints
    from supabase import Client as SupabaseClient  # type: ignore
except Exception:  # pragma: no cover

    class SupabaseClient:  # type: ignore
        ...


class ProjectService:
    """RLS-aware service using the anon client; user context enforced by policies and filters."""

    def __init__(self, client: SupabaseClient):
        self.db = client

    def create(self, user_id: str, data: ProjectCreate) -> Project:
        payload: dict[str, Any] = data.model_dump()
        payload["user_id"] = user_id
        res = self.db.table("projects").insert(payload).execute()
        if not res.data:
            from src.utils.exceptions import DatabaseError

            raise DatabaseError("Failed to create project")
        return Project(**res.data[0])

    def list(self, user_id: str, limit: int = 20, offset: int = 0) -> list[Project]:
        # RLS restricts to owner; explicit filter for clarity and exclude soft-deleted
        res = (
            self.db.table("projects")
            .select("*")
            .eq("user_id", user_id)
            .is_("deleted_at", "null")  # Exclude soft-deleted projects
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return [Project(**row) for row in (res.data or [])]

    def get(self, project_id: UUID, user_id: str) -> Project | None:
        res = (
            self.db.table("projects")
            .select("*")
            .eq("id", str(project_id))
            .eq("user_id", user_id)
            .is_("deleted_at", "null")  # Exclude soft-deleted projects
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        return Project(**res.data[0])

    def update(self, project_id: UUID, user_id: str, data: ProjectUpdate) -> Project | None:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self.get(project_id, user_id)
        res = self.db.table("projects").update(update_data).eq("id", str(project_id)).eq("user_id", user_id).execute()
        if not res.data:
            return None
        return Project(**res.data[0])

    def delete(self, project_id: UUID, user_id: str) -> bool:
        """Hard delete a project (use soft_delete for normal deletion)."""
        res = self.db.table("projects").delete().eq("id", str(project_id)).eq("user_id", user_id).execute()
        # Consider success only if a row was actually deleted
        return bool(res.data)

    def soft_delete(self, project_id: UUID, user_id: str) -> bool:
        """Soft delete a project by setting deleted_at and deleted_by."""
        update_data = {
            "deleted_at": datetime.utcnow().isoformat(),
            "deleted_by": user_id,
        }
        res = (
            self.db.table("projects")
            .update(update_data)
            .eq("id", str(project_id))
            .eq("user_id", user_id)
            .is_("deleted_at", "null")  # Only delete if not already deleted
            .execute()
        )
        # Consider success only if a row was actually updated
        return bool(res.data)
