"""API module initialization."""

from .auth import router as auth_router
from . import pipeline
from . import queries
from . import documents

__all__ = ["auth_router"]
