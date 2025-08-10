from typing import Optional, Any, Dict
from datetime import datetime

from src.shared.errors import ErrorCode, status_for_error_code


class AppError(Exception):
    """Base application exception with minimal consistent fields"""

    def __init__(
        self,
        message: str,
        *,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.request_id = request_id
        self.status_code = status_code or status_for_error_code(error_code)
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)

    def to_response(self) -> Dict[str, Any]:
        return {
            "code": self.error_code.value,
            "message": self.message,
            "details": self.details or None,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
        }


class ConfigurationError(AppError):
    pass


class DatabaseError(AppError):
    pass


class FileProcessingError(AppError):
    pass


class PipelineError(AppError):
    pass


class APIError(AppError):
    pass


class ValidationError(AppError):
    pass


class AuthenticationError(AppError):
    pass


class StorageError(AppError):
    pass
