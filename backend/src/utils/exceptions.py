from typing import Optional, Any, Dict


class ConstructionRAGException(Exception):
    """Base exception for ConstructionRAG application"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(ConstructionRAGException):
    """Raised when there's a configuration error"""

    pass


class DatabaseError(ConstructionRAGException):
    """Raised when there's a database error"""

    pass


class FileProcessingError(ConstructionRAGException):
    """Raised when there's an error processing files"""

    pass


class PipelineError(ConstructionRAGException):
    """Raised when there's an error in the pipeline"""

    pass


class APIError(ConstructionRAGException):
    """Raised when there's an external API error"""

    pass


class ValidationError(ConstructionRAGException):
    """Raised when there's a validation error"""

    pass


class AuthenticationError(ConstructionRAGException):
    """Raised when there's an authentication error"""

    pass
