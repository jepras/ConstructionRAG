"""API module initialization."""

from .auth import router as auth_router
from . import pipeline
from . import queries
from . import documents
from . import wiki

__all__ = ["auth_router"]
