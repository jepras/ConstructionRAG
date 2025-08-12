import uuid
from copy import deepcopy

import httpx
import pytest


@pytest.mark.asyncio
async def test_projects_crud_owner_only(monkeypatch):
    # Avoid startup validation coupling
    from src.services import config_service

    monkeypatch.setattr(config_service.ConfigService, "validate_startup", lambda self: None)

    # Minimal env for clients used during import
    import os

    os.environ.setdefault("SUPABASE_URL", "http://localhost")
    os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")

    from src.api.auth import get_current_user
    from src.api.projects import router as projects_router
    from src.config.database import get_db_client_for_request
    from src.main import app

    # Mount only for test scope (already included in app, but kept explicit)
    app.include_router(projects_router)

    # Auth overrides for two users
    user_a = {"id": "00000000-0000-0000-0000-00000000000a"}
    user_b = {"id": "00000000-0000-0000-0000-00000000000b"}

    # Provide a minimal fake Supabase client for the projects table
    class ExecResult:
        def __init__(self, data):
            self.data = data

    class FakeQuery:
        def __init__(self, store, op):
            self.store = store
            self.op = op
            self.filters = {}
            self._order = None
            self._desc = False
            self._limit = None
            self._range = None

        def eq(self, col, val):
            self.filters[col] = val
            return self

        def limit(self, n):
            self._limit = n
            return self

        def order(self, col, desc=False):
            self._order = col
            self._desc = desc
            return self

        def range(self, start, end):
            self._range = (start, end)
            return self

        def select(self, *_):
            self.op = "select"
            return self

        def update(self, payload):
            self.op = ("update", payload)
            return self

        def delete(self):
            self.op = ("delete", None)
            return self

        def execute(self):
            # Basic select/update/delete for projects only
            items = list(self.store.values())
            # Apply filters
            for k, v in self.filters.items():
                items = [it for it in items if str(it.get(k)) == str(v)]
            if isinstance(self.op, tuple) and self.op[0] == "update":
                payload = self.op[1]
                for it in items:
                    it.update(payload)
                return ExecResult([deepcopy(it) for it in items])
            if isinstance(self.op, tuple) and self.op[0] == "delete":
                deleted = []
                for it in list(items):
                    removed = self.store.pop(str(it["id"]), None)
                    if removed:
                        deleted.append(removed)
                return ExecResult(deleted)
            # Order and slice
            if self._order:
                items.sort(key=lambda x: x.get(self._order), reverse=self._desc)
            if self._range:
                start, end = self._range
                items = items[start : end + 1]
            if self._limit is not None:
                items = items[: self._limit]
            return ExecResult([deepcopy(it) for it in items])

    class FakeTable:
        def __init__(self, name, store):
            self.name = name
            self.store = store

        def insert(self, payload):
            data = deepcopy(payload)
            pid = str(uuid.uuid4())
            data.setdefault("id", pid)
            data.setdefault("access_level", "owner")

            table_store = self.store

            class _Insert:
                def __init__(self, d):
                    self._d = d

                def execute(self_inner):
                    table_store[self_inner._d["id"]] = self_inner._d
                    return ExecResult([deepcopy(self_inner._d)])

            return _Insert(data)

        def select(self, *cols, **kwargs):
            return FakeQuery(self.store, "select")

        def update(self, payload):
            return FakeQuery(self.store, ("update", payload))

        def delete(self):
            return FakeQuery(self.store, ("delete", None))

    class FakeClient:
        def __init__(self):
            self._projects: dict[str, dict] = {}

        def table(self, name):
            if name != "projects":
                raise AssertionError("Only projects table is supported in fake client")
            return FakeTable(name, self._projects)

    fake_client = FakeClient()

    async def _fake_db_client_for_request():
        return fake_client

    app.dependency_overrides[get_db_client_for_request] = _fake_db_client_for_request

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        app.dependency_overrides[get_current_user] = lambda: user_a

        # Create project
        r = await client.post("/api/projects", json={"name": "My Project", "description": "desc"})
        assert r.status_code in (200, 201)
        project = r.json()
        pid = project["id"]

        # List projects shows the new project
        r = await client.get("/api/projects")
        assert r.status_code == 200
        assert any(p["id"] == pid for p in r.json())

        # Get returns the project
        r = await client.get(f"/api/projects/{pid}")
        assert r.status_code == 200
        assert r.json()["name"] == "My Project"

        # Update name
        r = await client.patch(f"/api/projects/{pid}", json={"name": "Renamed"})
        assert r.status_code == 200
        assert r.json()["name"] == "Renamed"

        # Switch to user B: access should be denied (404 by contract)
        app.dependency_overrides[get_current_user] = lambda: user_b
        r = await client.get(f"/api/projects/{pid}")
        assert r.status_code in (403, 404)

        r = await client.patch(f"/api/projects/{pid}", json={"name": "X"})
        assert r.status_code in (403, 404)

        r = await client.delete(f"/api/projects/{pid}")
        assert r.status_code in (403, 404)

        # Back to owner: delete succeeds
        app.dependency_overrides[get_current_user] = lambda: user_a
        r = await client.delete(f"/api/projects/{pid}")
        assert r.status_code == 200

    app.dependency_overrides.clear()
