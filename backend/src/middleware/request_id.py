import uuid

from contextvars import ContextVar
from fastapi import Request

from starlette.middleware.base import BaseHTTPMiddleware

try:
    import structlog
    import structlog.contextvars as slcv
except Exception:  # pragma: no cover - optional import
    structlog = None
    slcv = None


request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_ctx.set(request_id)
        if slcv is not None:
            slcv.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def get_request_id() -> str:
    rid = request_id_ctx.get()
    return rid or str(uuid.uuid4())
