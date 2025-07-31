from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import os
import sys

print("DEBUG: Starting main.py import process")

# Import configuration
try:
    print("DEBUG: Importing src.config.settings")
    from src.config.settings import get_settings

    print("DEBUG: Successfully imported src.config.settings")
except Exception as e:
    print(f"DEBUG: Failed to import src.config.settings: {e}")
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


# Include API routers
try:
    print("DEBUG: Importing src.api.auth_router")
    from src.api import auth_router

    print("DEBUG: Successfully imported src.api.auth_router")
except Exception as e:
    print(f"DEBUG: Failed to import src.api.auth_router: {e}")
    raise

try:
    print("DEBUG: Importing src.api.pipeline")
    from src.api import pipeline

    print("DEBUG: Successfully imported src.api.pipeline")
except Exception as e:
    print(f"DEBUG: Failed to import src.api.pipeline: {e}")
    raise

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(pipeline.router, prefix="/api", tags=["Pipeline"])

# Additional routers (will be added later)
# from api import documents, queries
# app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
# app.include_router(queries.router, prefix="/api/queries", tags=["Queries"])

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=settings.environment == "development",
    )
