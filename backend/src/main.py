from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import os
import sys

# Import configuration
try:
    from src.config.settings import get_settings
except Exception as e:
    raise

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


# Include API routers
try:
    from src.api import auth_router
except Exception as e:
    raise

try:
    from src.api import pipeline
except Exception as e:
    raise

try:
    from src.api import queries
except Exception as e:
    raise

try:
    from src.api import documents
except Exception as e:
    raise

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(pipeline.router, prefix="/api", tags=["Pipeline"])
app.include_router(queries.router, prefix="/api", tags=["Queries"])
app.include_router(documents.router, tags=["Documents"])

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=settings.environment == "development",
    )
