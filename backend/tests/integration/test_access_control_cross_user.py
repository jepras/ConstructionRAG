import os
import uuid

import httpx
import pytest


def _env_missing() -> bool:
    return not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_ANON_KEY"))


@pytest.mark.skipif(_env_missing(), reason="Supabase env not configured")
@pytest.mark.asyncio
async def test_indexing_run_cross_user_denied(monkeypatch):
    # Avoid startup validation coupling
    from src.services import config_service

    monkeypatch.setattr(config_service.ConfigService, "validate_startup", lambda self: None)

    from src.main import app
    from src.services.auth_service import get_current_user_optional

    # Simulate authenticated user
    app.dependency_overrides[get_current_user_optional] = lambda: {"id": "user-1"}

    fake_run_id = str(uuid.uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/api/indexing-runs/{fake_run_id}")
        # For non-owned or non-existent runs, API responds with not found to avoid leaking existence
        assert r.status_code in (404,)

    app.dependency_overrides.clear()


@pytest.mark.skipif(_env_missing(), reason="Supabase env not configured")
@pytest.mark.asyncio
async def test_documents_cross_user_denied(monkeypatch):
    # Avoid startup validation coupling
    from src.services import config_service

    monkeypatch.setattr(config_service.ConfigService, "validate_startup", lambda self: None)

    from src.main import app
    from src.services.auth_service import get_current_user_optional

    # Simulate authenticated user
    app.dependency_overrides[get_current_user_optional] = lambda: {"id": "user-1"}

    fake_project_id = str(uuid.uuid4())
    fake_doc_id = str(uuid.uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r_list = await client.get(f"/api/documents?project_id={fake_project_id}")
        assert r_list.status_code in (200, 404)
        r_get = await client.get(f"/api/documents/{fake_doc_id}?project_id={fake_project_id}")
        assert r_get.status_code in (404,)

    app.dependency_overrides.clear()


@pytest.mark.skipif(_env_missing(), reason="Supabase env not configured")
@pytest.mark.asyncio
async def test_wiki_cross_user_denied(monkeypatch):
    from src.services import config_service

    monkeypatch.setattr(config_service.ConfigService, "validate_startup", lambda self: None)

    from src.main import app
    from src.services.auth_service import get_current_user_optional

    app.dependency_overrides[get_current_user_optional] = lambda: {"id": "user-1"}

    fake_id = str(uuid.uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Run details should 404 for non-owned
        r = await client.get(f"/api/wiki/runs/{fake_id}")
        assert r.status_code in (404,)
        # Status should also 404 for non-owned
        s = await client.get(f"/api/wiki/runs/{fake_id}/status")
        assert s.status_code in (404,)

    app.dependency_overrides.clear()


@pytest.mark.skipif(_env_missing(), reason="Supabase env not configured")
@pytest.mark.asyncio
async def test_query_cross_user_denied(monkeypatch):
    from src.services import config_service

    monkeypatch.setattr(config_service.ConfigService, "validate_startup", lambda self: None)

    from src.main import app
    from src.services.auth_service import get_current_user_optional

    app.dependency_overrides[get_current_user_optional] = lambda: {"id": "user-1"}

    fake_id = str(uuid.uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Flat get query should not leak others; expect 404 for random id
        r = await client.get(f"/api/queries/{fake_id}")
        assert r.status_code in (404,)

    app.dependency_overrides.clear()
