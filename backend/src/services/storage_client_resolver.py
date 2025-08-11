from __future__ import annotations

from src.config.database import get_supabase_admin_client, get_supabase_client
from supabase import Client


class StorageClientResolver:
    """Dynamic resolver that selects anon vs admin based on context.

    Defaults to anon client for user-scoped operations (RLS). Use admin for
    trusted server-to-server operations where writes need elevated privileges.
    """

    def __init__(self) -> None:
        self._admin = get_supabase_admin_client()
        self._anon = get_supabase_client()

    def get_client(
        self,
        *,
        user_id: str | None = None,
        operation: str | None = None,
        access_level: str | None = None,
        trusted: bool | None = None,
    ) -> Client:
        """Return a Supabase client for storage.

        Selection rules:
        - If trusted is True → admin
        - Else if operation in {"ensure_bucket", "delete"} → admin
        - Else if access_level in {"public"} → anon
        - Else if user_id is provided → anon
        - Fallback → anon
        """
        if trusted:
            return self._admin
        if operation in {"ensure_bucket", "delete"}:
            return self._admin
        if access_level == "public":
            return self._anon
        if user_id:
            return self._anon
        return self._anon
