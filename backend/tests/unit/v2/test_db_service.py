from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.services.db_service import DbService
from src.utils.exceptions import DatabaseError


class StubClient:
    def __init__(self, rows: list[dict] | None = None):
        self._rows = rows or []

    def table(self, name: str):  # noqa: D401
        client = self

        class InsertBuilder:
            def __init__(self, table_name: str):
                self.table_name = table_name
                self._data = None

            def insert(self, data):
                self._data = data
                return self

            def execute(self):
                # Simulate DB returning inserted row
                return SimpleNamespace(data=[self._data])

        class SelectBuilder:
            def __init__(self, table_name: str):
                self.table_name = table_name
                self._eq = None
                self._limit = None

            def select(self, _columns: str):  # noqa: ARG002
                return self

            def eq(self, field: str, value: str):  # noqa: ARG002
                self._eq = (field, value)
                return self

            def limit(self, n: int):
                self._limit = n
                return self

            def execute(self):
                return SimpleNamespace(data=list(client._rows))

        return SimpleNamespace(
            insert=lambda data: InsertBuilder(name).insert(data),
            select=lambda cols: SelectBuilder(name).select(cols),
        )


def test_create_happy_path():
    svc = DbService(client=StubClient())
    row = svc.create("documents", {"id": "1", "name": "doc"})
    assert row["id"] == "1"


def test_create_returns_empty_raises_database_error():
    class EmptyInsertClient(StubClient):
        def table(self, name: str):
            class InsertBuilder:
                def insert(self, data):  # noqa: ARG002
                    return SimpleNamespace(data=[])

            return SimpleNamespace(insert=lambda data: InsertBuilder().insert(data))

    svc = DbService(client=EmptyInsertClient())
    with pytest.raises(DatabaseError):
        svc.create("documents", {"id": "1"})


def test_get_by_id_happy_path():
    svc = DbService(client=StubClient(rows=[{"id": "42", "name": "x"}]))
    row = svc.get_by_id("documents", "42")
    assert row["name"] == "x"


def test_get_by_id_not_found_raises_database_error():
    svc = DbService(client=StubClient(rows=[]))
    with pytest.raises(DatabaseError):
        svc.get_by_id("documents", "404")
