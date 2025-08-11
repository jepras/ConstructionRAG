from datetime import datetime
from typing import Any

from src.shared.errors import ErrorCode, status_for_error_code


class AppError(Exception):
    """Base application exception with minimal consistent fields"""

    def __init__(
        self,
        message: str,
        *,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.request_id = request_id
        self.status_code = status_code or status_for_error_code(error_code)
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)

    def to_response(self) -> dict[str, Any]:
        return {
            "code": self.error_code.value,
            "message": self.message,
            "details": self.details or None,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
        }


class ConfigurationError(AppError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=ErrorCode.CONFIGURATION_ERROR,
            details=details,
            request_id=request_id,
            status_code=status_code,
        )


class DatabaseError(AppError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=ErrorCode.DATABASE_ERROR,
            details=details,
            request_id=request_id,
            status_code=status_code,
        )


class FileProcessingError(AppError): ...


class PipelineError(AppError): ...


class APIError(AppError): ...


class ValidationError(AppError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=ErrorCode.VALIDATION_ERROR,
            details=details,
            request_id=request_id,
            status_code=status_code,
        )


class AuthenticationError(AppError):
    def __init__(
        self,
        message: str = "Authentication required",
        *,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=ErrorCode.AUTHENTICATION_REQUIRED,
            details=details,
            request_id=request_id,
            status_code=status_code,
        )


class StorageError(AppError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=ErrorCode.STORAGE_ERROR,
            details=details,
            request_id=request_id,
            status_code=status_code,
        )
