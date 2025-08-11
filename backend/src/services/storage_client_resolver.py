from __future__ import annotations

from src.config.database import get_supabase_admin_client
from supabase import Client


class StorageClientResolver:
    """Phase 4 resolver that always returns the admin client.

    In Phase 5, this will select anon vs admin based on context/access level.
    """

    def __init__(self) -> None:
        self._admin = get_supabase_admin_client()

    def get_client(self, *, user_id: str | None = None) -> Client:  # noqa: ARG002
        return self._admin
