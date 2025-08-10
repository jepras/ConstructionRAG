import os

import pytest
import httpx


# Ensure minimal env so settings don't fail
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")


@pytest.mark.asyncio
async def test_main_app_health_and_request_id(monkeypatch):
    # Monkeypatch startup validation to avoid environment coupling
    from src.services import config_service

    monkeypatch.setattr(
        config_service.ConfigService, "validate_startup", lambda self: None
    )

    # Import the real app after monkeypatching
    from src.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/health", headers={"X-Request-ID": "it-works"})
        assert r.status_code == 200
        # Request ID header should be echoed by middleware
        assert r.headers.get("X-Request-ID") == "it-works"


@pytest.mark.asyncio
async def test_main_app_app_error_handling(monkeypatch):
    from src.services import config_service

    monkeypatch.setattr(
        config_service.ConfigService, "validate_startup", lambda self: None
    )

    from src.main import app
    from src.utils.exceptions import AppError
    from src.shared.errors import ErrorCode

    # Add a temporary route that raises AppError
    @app.get("/_boom_test")
    async def _boom_test():  # noqa: F811 - test-only route definition
        raise AppError("boom", error_code=ErrorCode.INTERNAL_ERROR)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/_boom_test")
        assert r.status_code == 500
        assert r.headers.get("X-Request-ID")
        body = r.json()
        assert body["error"]["code"] == ErrorCode.INTERNAL_ERROR.value
