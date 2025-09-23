"""Service for CRUD operations on projects (RLS-aware)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Dict
from fastapi import HTTPException
from uuid import UUID

from src.models.pipeline import Project, ProjectCreate, ProjectUpdate
from src.models.user import UserContext
from src.constants import ANONYMOUS_USER_ID, ANONYMOUS_USERNAME
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

    async def get_project_by_slug(
        self,
        username: str,
        project_slug: str,
        user: Optional[UserContext] = None
    ) -> Dict[str, Any]:
        """Single project resolution function for all endpoints."""
        try:
            query = self.db.table('projects').select('*')
            query = query.eq('username', username).eq('project_slug', project_slug)

            # Unified access control - no upload_type checking needed
            if user and user.isAuthenticated:
                # Authenticated users can see public, internal, and their own private projects
                query = query.or_(
                    f"visibility.eq.public,"
                    f"visibility.eq.internal,"
                    f"and(visibility.eq.private,user_id.eq.{user.id})"
                )
            else:
                # Anonymous users can only see public projects
                query = query.eq('visibility', 'public')

            result = query.execute()
            if not result.data:
                raise HTTPException(404, "Project not found")

            project = result.data[0]

            logger.info(
                "Project resolved successfully",
                username=username,
                project_slug=project_slug,
                project_id=project['id'],
                visibility=project['visibility'],
                is_authenticated=user.isAuthenticated if user else False
            )

            return project

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Failed to resolve project",
                username=username,
                project_slug=project_slug,
                error=str(e),
                error_type=type(e).__name__
            )
            raise HTTPException(500, "Failed to resolve project")

    def can_access_resource(
        self,
        project: Dict[str, Any],
        resource_type: str,
        user: Optional[UserContext]
    ) -> bool:
        """Unified access control for all project resources."""
        visibility = project.get('visibility', 'private')

        # Public projects - anyone can read
        if visibility == 'public':
            if resource_type in ['read', 'query', 'wiki']:
                return True
            # Write operations require authentication
            if resource_type in ['write', 'upload', 'settings']:
                return user and user.isAuthenticated and project['user_id'] == user.id

        # Private projects - owner only
        if visibility == 'private':
            return user and user.isAuthenticated and project['user_id'] == user.id

        # Internal projects - any authenticated user
        if visibility == 'internal':
            return user and user.isAuthenticated

        return False

    def generate_project_slug(self, name: str) -> str:
        """Generate project slug from project name."""
        import re
        # Convert to lowercase and replace non-alphanumeric with hyphens
        slug = re.sub(r'[^a-zA-Z0-9]', '-', name.lower())
        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        return slug or 'untitled-project'

    async def check_project_name_availability(
        self,
        username: str,
        project_name: str
    ) -> Dict[str, Any]:
        """Check if project name is available in the given username namespace."""
        try:
            project_slug = self.generate_project_slug(project_name)

            # Check if name already exists in namespace
            existing = self.db.table('projects').select('id').eq(
                'username', username
            ).eq('project_slug', project_slug).execute()

            available = len(existing.data) == 0

            return {
                "available": available,
                "project_slug": project_slug,
                "username": username,
                "error": "Project name already taken" if not available else None
            }
        except Exception as e:
            logger.error(
                "Failed to check project name availability",
                username=username,
                project_name=project_name,
                error=str(e)
            )
            return {
                "available": False,
                "project_slug": "",
                "username": username,
                "error": "Error checking name availability"
            }
