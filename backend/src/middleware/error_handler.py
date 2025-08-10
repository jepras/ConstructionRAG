from datetime import datetime

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.middleware.request_id import get_request_id
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def app_error_handler(request: Request, exc: AppError):
    request_id = exc.request_id or get_request_id()
    payload = exc.to_response()
    payload["request_id"] = request_id
    logger.error(
        "Application error",
        error_code=exc.error_code.value,
        message=exc.message,
        details=exc.details,
        request_id=request_id,
        path=str(request.url.path),
        method=request.method,
        status_code=exc.status_code,
    )
    return JSONResponse(status_code=exc.status_code, content={"error": payload})


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = get_request_id()
    logger.warning(
        "HTTP exception",
        error_code="HTTP_EXCEPTION",
        status_code=exc.status_code,
        detail=exc.detail,
        request_id=request_id,
        path=str(request.url.path),
        method=request.method,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_EXCEPTION",
                "message": exc.detail,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = get_request_id()
    field_errors = []
    for error in exc.errors():
        field_errors.append(
            {
                "field": ".".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )
    logger.warning(
        "Validation error",
        error_code=ErrorCode.VALIDATION_ERROR.value,
        field_errors=field_errors,
        request_id=request_id,
        path=str(request.url.path),
        method=request.method,
        status_code=422,
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": ErrorCode.VALIDATION_ERROR.value,
                "message": "Request validation failed",
                "details": {"field_errors": field_errors},
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    request_id = get_request_id()
    logger.error(
        "Internal error",
        error_code=ErrorCode.INTERNAL_ERROR.value,
        exception_type=type(exc).__name__,
        message=str(exc),
        request_id=request_id,
        path=str(request.url.path),
        method=request.method,
        status_code=500,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": ErrorCode.INTERNAL_ERROR.value,
                "message": "An unexpected error occurred",
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
    )
