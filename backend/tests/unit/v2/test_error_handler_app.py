import os

import pytest
import httpx
from fastapi import FastAPI, HTTPException

from src.middleware.request_id import RequestIdMiddleware
from src.middleware.error_handler import (
    app_error_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError


# Ensure minimal env to avoid startup issues for any imported settings
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")


def build_app() -> FastAPI:
    app = FastAPI()

    # Register middleware and handlers
    app.add_middleware(RequestIdMiddleware)
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    @app.get("/boom-app")
    async def boom_app():
        raise AppError("boom", error_code=ErrorCode.INTERNAL_ERROR)

    @app.get("/boom-http")
    async def boom_http():
        raise HTTPException(status_code=404, detail="missing")

    @app.get("/validate")
    async def validate(count: int):  # noqa: ARG001 - used for validation only
        return {"ok": True}

    return app


@pytest.mark.asyncio
async def test_app_error_response_and_header():
    app = build_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/boom-app", headers={"X-Request-ID": "test-rid"})
        assert r.status_code == 500
        assert r.headers.get("X-Request-ID") == "test-rid"
        body = r.json()
        assert body["error"]["code"] == ErrorCode.INTERNAL_ERROR.value
        assert body["error"]["request_id"] == "test-rid"


@pytest.mark.asyncio
async def test_http_exception_normalized_and_header():
    app = build_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/boom-http")
        assert r.status_code == 404
        assert r.headers.get("X-Request-ID")
        body = r.json()
        assert body["error"]["code"] == "HTTP_EXCEPTION"


@pytest.mark.asyncio
async def test_validation_exception_envelope_and_header():
    app = build_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/validate", params={"count": "abc"})
        assert r.status_code == 422
        assert r.headers.get("X-Request-ID")
        body = r.json()
        assert body["error"]["code"] == ErrorCode.VALIDATION_ERROR.value
