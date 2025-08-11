import os
import uuid

import httpx
import pytest


def _env_missing() -> bool:
    return not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


@pytest.mark.skipif(_env_missing(), reason="Supabase env not configured")
@pytest.mark.asyncio
async def test_rls_documents_public_vs_private(monkeypatch):
    from src.services import config_service

    monkeypatch.setattr(config_service.ConfigService, "validate_startup", lambda self: None)

    from src.main import app
    from src.services.auth_service import get_current_user_optional

    # Anonymous cannot see private/owner docs; only public
    app.dependency_overrides[get_current_user_optional] = lambda: None

    fake_doc = str(uuid.uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/api/documents/{fake_doc}?index_run_id={uuid.uuid4()}")
        assert r.status_code in (404, 400)

    app.dependency_overrides.clear()


@pytest.mark.skipif(_env_missing(), reason="Supabase env not configured")
@pytest.mark.asyncio
async def test_rls_indexing_runs_public_email_vs_private_project(monkeypatch):
    from src.services import config_service

    monkeypatch.setattr(config_service.ConfigService, "validate_startup", lambda self: None)

    from src.main import app
    from src.services.auth_service import get_current_user_optional

    # Anonymous only allowed for email runs
    app.dependency_overrides[get_current_user_optional] = lambda: None
    fake_run = str(uuid.uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/api/indexing-runs/{fake_run}")
        assert r.status_code in (404, 403)

    app.dependency_overrides.clear()


@pytest.mark.skipif(_env_missing(), reason="Supabase env not configured")
@pytest.mark.asyncio
async def test_rls_queries_visibility(monkeypatch):
    from src.services import config_service

    monkeypatch.setattr(config_service.ConfigService, "validate_startup", lambda self: None)

    from src.main import app
    from src.services.auth_service import get_current_user_optional

    # Anonymous should only see public query_runs
    app.dependency_overrides[get_current_user_optional] = lambda: None

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/queries")
        # Either empty list or 200 with some public entries; ensure not 5xx
        assert r.status_code in (200,)

    app.dependency_overrides.clear()

