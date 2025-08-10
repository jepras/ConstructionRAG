from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    # 4xx
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    ACCESS_DENIED = "ACCESS_DENIED"
    NOT_FOUND = "NOT_FOUND"

    # 5xx - external/service/system
    DATABASE_ERROR = "DATABASE_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


ERROR_STATUS: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.AUTHENTICATION_REQUIRED: 401,
    ErrorCode.ACCESS_DENIED: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.DATABASE_ERROR: 502,
    ErrorCode.STORAGE_ERROR: 502,
    ErrorCode.EXTERNAL_API_ERROR: 502,
    ErrorCode.CONFIGURATION_ERROR: 500,
    ErrorCode.INTERNAL_ERROR: 500,
}


def status_for_error_code(code: ErrorCode) -> int:
    return ERROR_STATUS.get(code, 500)
