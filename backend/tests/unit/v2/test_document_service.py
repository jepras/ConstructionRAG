from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.services.document_service import DocumentService


class StubStorage:
    async def upload_file(self, file_path: str, storage_path: str) -> str:  # noqa: ARG002
        return "https://example.com/signed"


class StubDB:
    def __init__(self):
        self.inserted = []
        self.updated = []

    def table(self, name: str):  # noqa: D401
        # Return a stub chain supporting insert/update/eq/execute
        db = self

        class InsertBuilder:
            def __init__(self, db_ref, table_name):
                self.db_ref = db_ref
                self.table_name = table_name
                self._data = None

            def insert(self, data):
                self._data = data
                self.db_ref.inserted.append((self.table_name, data))
                return self

            def execute(self):
                return SimpleNamespace(data=[self._data])

        class UpdateBuilder:
            def __init__(self, db_ref, table_name):
                self.db_ref = db_ref
                self.table_name = table_name
                self._data = None
                self._eq = None

            def update(self, data):
                self._data = data
                return self

            def eq(self, field, value):  # noqa: ARG002
                self._eq = (field, value)
                return self

            def execute(self):
                self.db_ref.updated.append((self.table_name, self._data, self._eq))
                return SimpleNamespace(data=[self._data])

        return SimpleNamespace(
            insert=lambda data: InsertBuilder(self, name).insert(data),
            update=lambda data: UpdateBuilder(self, name).update(data),
        )


@pytest.mark.asyncio
async def test_create_email_document_happy_path(tmp_path):
    db = StubDB()
    storage = StubStorage()
    svc = DocumentService(db=db, storage=storage)

    file_bytes = b"%PDF-1.4 test"
    result = await svc.create_email_document(
        file_bytes=file_bytes,
        filename="doc.pdf",
        index_run_id="run-1",
        email="test@example.com",
    )

    assert "document_id" in result
    assert result["storage_url"] == "https://example.com/signed"
    # One insert into documents
    assert any(t == "documents" for t, _ in ((t, d) for t, d in db.inserted))


@pytest.mark.asyncio
async def test_create_project_document_happy_path(tmp_path):
    db = StubDB()
    storage = StubStorage()
    svc = DocumentService(db=db, storage=storage)

    file_bytes = b"%PDF-1.4 test"
    result = await svc.create_project_document(
        file_bytes=file_bytes,
        filename="doc.pdf",
        project_id="11111111-1111-1111-1111-111111111111",
        user_id="user-1",
        index_run_id="run-1",
        file_size=len(file_bytes),
    )

    assert "document_id" in result
    assert result["storage_url"] == "https://example.com/signed"
    assert result["temp_path"]
