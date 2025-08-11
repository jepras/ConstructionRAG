import httpx
import pytest


@pytest.mark.asyncio
async def test_debug_endpoint_guarded(monkeypatch):
    # Force non-dev environment
    monkeypatch.setenv("ENVIRONMENT", "production")
    # Provide dummy Supabase env to satisfy imports
    monkeypatch.setenv("SUPABASE_URL", "http://local-supabase")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    from importlib import reload

    from src.config import settings as settings_module

    reload(settings_module)
    from src import main as main_module

    reload(main_module)
    app = main_module.app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/debug/env")
        assert r.status_code in (404,)  # guarded in non-dev


@pytest.mark.asyncio
async def test_cors_allows_configured_origin(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    # Provide dummy Supabase env to satisfy imports
    monkeypatch.setenv("SUPABASE_URL", "http://local-supabase")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    from importlib import reload

    from src.config import settings as settings_module

    reload(settings_module)
    from src import main as main_module

    reload(main_module)
    app = main_module.app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Starlette CORS responds 200 for preflight with allowed origin
        assert r.status_code in (200, 204)
