from __future__ import annotations

from typing import Any

from src.config.database import get_supabase_admin_client, get_supabase_client
from src.utils.exceptions import DatabaseError
from src.utils.logging import get_logger
from supabase import Client


class DbService:
    """Minimal shared CRUD helpers with optional admin client (Phase 4).

    Scope kept intentionally small to avoid overengineering.
    """

    def __init__(self, *, use_admin_client: bool = False, client: Client | None = None) -> None:
        self.logger = get_logger(self.__class__.__name__)
        if client is not None:
            self.db = client
        else:
            self.db = get_supabase_admin_client() if use_admin_client else get_supabase_client()

    def get_by_id(self, table: str, resource_id: str) -> dict[str, Any]:
        try:
            result = self.db.table(table).select("*").eq("id", resource_id).limit(1).execute()
            if not result.data:
                raise DatabaseError(f"{table} not found: {resource_id}")
            return dict(result.data[0])
        except DatabaseError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.logger.error("get_by_id failed", table=table, id=resource_id, error=str(exc))
            raise DatabaseError(f"Failed to fetch from {table}: {exc}") from exc

    def create(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.db.table(table).insert(data).execute()
            if not result.data:
                raise DatabaseError(f"Failed to create in {table}")
            return dict(result.data[0])
        except DatabaseError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.logger.error("create failed", table=table, error=str(exc))
            raise DatabaseError(f"Failed to create in {table}: {exc}") from exc
