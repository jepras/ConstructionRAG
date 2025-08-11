import os

import httpx
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


def _env_missing() -> bool:
    return not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_ANON_KEY"))


@pytest.mark.skipif(_env_missing(), reason="Supabase env not configured")
@pytest.mark.asyncio
async def test_create_query_anonymous_smoke(monkeypatch):
    from src.services import config_service

    # Avoid startup validation coupling
    monkeypatch.setattr(config_service.ConfigService, "validate_startup", lambda self: None)

    # Minimal env defaults for clients used during import
    os.environ.setdefault("SUPABASE_URL", "http://localhost")
    os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")

    from src.main import app
    from src.pipeline.querying.models import QueryResponse
    from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator

    async def fake_process_query(self, _req):
        return QueryResponse(response="ok", search_results=[], performance_metrics={})

    monkeypatch.setattr(QueryPipelineOrchestrator, "process_query", fake_process_query)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/queries", json={"query": "hello"}, headers={"X-Request-ID": "q1"})
        # Anonymous is allowed; may return 200 with empty results depending on data
        assert r.status_code in (200, 201)
        body = r.json()
        assert "response" in body
        assert "search_results" in body


@pytest.mark.skipif(_env_missing(), reason="Supabase env not configured")
@pytest.mark.asyncio
async def test_get_and_list_queries_access(monkeypatch):
    from src.services import config_service

    monkeypatch.setattr(config_service.ConfigService, "validate_startup", lambda self: None)

    os.environ.setdefault("SUPABASE_URL", "http://localhost")
    os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")

    from src.main import app
    from src.services.auth_service import get_current_user_optional

    # Override auth to simulate authenticated user
    app.dependency_overrides[get_current_user_optional] = lambda: {"id": "user-1"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # List queries should not fail
        lr = await client.get("/api/queries")
        assert lr.status_code == 200

        # GET by id returns standardized error envelope
        gr = await client.get("/api/queries/00000000-0000-0000-0000-000000000000")
        # Either 404 with error envelope, or 200 if preloaded data exists
        if gr.status_code == 404:
            body = gr.json()
            assert "error" in body
            assert set(["code", "message", "request_id", "timestamp"]).issubset(body["error"].keys())
            assert gr.headers.get("X-Request-ID")

    app.dependency_overrides.clear()


@pytest.mark.skipif(_env_missing(), reason="Supabase env not configured")
@pytest.mark.asyncio
async def test_error_envelope_and_request_id(monkeypatch):
    from src.services import config_service

    monkeypatch.setattr(config_service.ConfigService, "validate_startup", lambda self: None)

    os.environ.setdefault("SUPABASE_URL", "http://localhost")
    os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")

    from src.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Force validation error by sending wrong shape
        r = await client.post("/api/queries", json={}, headers={"X-Request-ID": "err-1"})
        assert r.status_code in (400, 422)
        data = r.json()
        assert "error" in data
        assert set(["code", "message", "request_id", "timestamp"]).issubset(data["error"].keys())
        assert r.headers.get("X-Request-ID") == "err-1"
