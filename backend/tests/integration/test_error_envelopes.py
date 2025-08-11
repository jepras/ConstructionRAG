import os

import httpx
import pytest


def _env_missing() -> bool:
    return not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


@pytest.mark.skipif(_env_missing(), reason="Supabase env not configured")
@pytest.mark.asyncio
async def test_error_envelope_and_request_id(monkeypatch):
    from src.services import config_service

    monkeypatch.setattr(config_service.ConfigService, "validate_startup", lambda self: None)

    from src.main import app

    # Call deprecated endpoint to trigger 410 with AppError
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/api/email-uploads",
            headers={"X-Request-ID": "envelope-test-1"},
            files={"files": ("test.pdf", b"%PDF-1.4", "application/pdf")},
            data={"email": "test@example.com"},
        )
        assert r.status_code == 410
        assert r.headers.get("X-Request-ID") == "envelope-test-1"
        body = r.json()
        assert "error" in body
        err = body["error"]
        assert set(["code", "message", "request_id", "timestamp"]).issubset(err.keys())

