import logging
import sys

import structlog

from src.config.settings import get_settings


def setup_logging(log_level: str | None = None) -> None:
    """Setup structured logging for the application"""

    if log_level is None:
        settings = get_settings()
        log_level = settings.log_level

    # Configure structlog with contextvars merging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to use ProcessorFormatter
    # so stdlib logging is rendered as structured JSON
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Quiet noisy third-party loggers (HTTP/2 debug, client libraries)
    noisy_loggers: dict[str, str] = {
        "httpx": "WARNING",
        "httpcore": "WARNING",
        "hpack": "WARNING",
        "uvicorn": "INFO",
        "uvicorn.error": "INFO",
        "uvicorn.access": "WARNING",
    }
    for logger_name, level in noisy_loggers.items():
        lib_logger = logging.getLogger(logger_name)
        lib_logger.setLevel(getattr(logging, level, logging.WARNING))
        # Prevent double logging via root
        lib_logger.propagate = False


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


# Global logger instance
logger = get_logger(__name__)
