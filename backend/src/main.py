import os
from datetime import datetime

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api import auth_router, documents, pipeline, queries, wiki
from src.config.settings import get_settings
from src.middleware.error_handler import (
    app_error_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from src.middleware.request_id import RequestIdMiddleware
from src.utils.exceptions import AppError
from src.utils.logging import setup_logging

# Create FastAPI app
app = FastAPI(
    title="ConstructionRAG API",
    description="AI-powered construction document processing and Q&A system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging and request ID middleware
setup_logging()
app.add_middleware(RequestIdMiddleware)

# Register exception handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.on_event("startup")
async def validate_startup_config() -> None:
    """Fail-fast validation for config and critical environment."""
    from src.services.config_service import ConfigService

    cfg = ConfigService()
    cfg.validate_startup()


# Health check endpoint
@app.get("/")
async def root():
    return {"message": "ConstructionRAG API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


@app.get("/api/health")
async def api_health():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "service": "ConstructionRAG API",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/debug/env")
async def debug_env():
    """Debug endpoint to check environment variables"""
    return {
        "beam_webhook_url": os.getenv("BEAM_WEBHOOK_URL", "NOT_SET"),
        "beam_auth_token": (
            os.getenv("BEAM_AUTH_TOKEN", "NOT_SET")[:10] + "..."
            if os.getenv("BEAM_AUTH_TOKEN")
            else "NOT_SET"
        ),
        "environment": os.getenv("ENVIRONMENT", "NOT_SET"),
        "supabase_url": (
            os.getenv("SUPABASE_URL", "NOT_SET")[:20] + "..."
            if os.getenv("SUPABASE_URL")
            else "NOT_SET"
        ),
    }


app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(pipeline.router, prefix="/api", tags=["Pipeline"])
app.include_router(queries.router, prefix="/api", tags=["Queries"])
app.include_router(documents.router, tags=["Documents"])
app.include_router(wiki.router, prefix="/api", tags=["Wiki"])

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=settings.environment == "development",
    )
