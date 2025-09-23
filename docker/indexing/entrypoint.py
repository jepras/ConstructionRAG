"""
Local indexing container entrypoint.
Provides HTTP API interface that calls the EXACT same process_documents function from beam-app.py.
No code duplication - uses the actual deployment code.
"""
import asyncio
import logging
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import sys
import os

# Mock the beam module since we're not using Beam infrastructure locally
class MockEnv:
    def is_remote(self):
        return True  # Return True so beam-app.py runs the actual indexing pipeline

class MockBeam:
    def __init__(self):
        self.env = MockEnv()
    
    def Image(self, **kwargs):
        return None
    
    def task_queue(self, **kwargs):
        # Return a decorator that just returns the function unchanged
        def decorator(func):
            return func
        return decorator

sys.modules['beam'] = MockBeam()

# Now import the ACTUAL function from beam-app.py
sys.path.append('/app')
from beam_app import process_documents

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app for internal API
app = FastAPI(title="Local Indexing Service", version="1.0.0")

class IndexingRequest(BaseModel):
    """Request model matching beam-app.py process_documents parameters exactly."""
    indexing_run_id: str
    document_ids: List[str]
    user_id: str = None
    project_id: str = None
    webhook_url: str = None
    webhook_api_key: str = None

class IndexingResponse(BaseModel):
    """Response model."""
    status: str
    message: str
    indexing_run_id: str

@app.post("/process", response_model=IndexingResponse)
async def process_documents_endpoint(request: IndexingRequest):
    """
    HTTP endpoint that calls the EXACT same process_documents function from beam-app.py.
    This ensures 100% code consistency between local and production.
    """
    try:
        logger.info(f"🚀 [INDEXING] Starting local indexing for run: {request.indexing_run_id}")
        logger.info(f"🚀 [INDEXING] Document IDs: {request.document_ids}")
        logger.info(f"🚀 [INDEXING] Webhook URL: {request.webhook_url}")
        
        # Add task with exception handling
        async def run_with_error_handling():
            try:
                logger.info(f"🔄 [INDEXING] Calling process_documents function...")
                result = await asyncio.to_thread(
                    process_documents,
                    indexing_run_id=request.indexing_run_id,
                    document_ids=request.document_ids,
                    user_id=request.user_id,
                    project_id=request.project_id,
                    webhook_url=request.webhook_url,
                    webhook_api_key=request.webhook_api_key,
                )
                logger.info(f"✅ [INDEXING] Process completed successfully: {result}")
            except Exception as e:
                logger.error(f"❌ [INDEXING] Process failed with error: {e}")
                logger.error(f"❌ [INDEXING] Error type: {type(e).__name__}")
                import traceback
                logger.error(f"❌ [INDEXING] Full traceback: {traceback.format_exc()}")
                raise
        
        # Start the task
        task = asyncio.create_task(run_with_error_handling())
        logger.info(f"🎯 [INDEXING] Background task created: {task}")
        
        return IndexingResponse(
            status="triggered",
            message="Indexing started successfully (using actual beam-app.py code)",
            indexing_run_id=request.indexing_run_id
        )
        
    except Exception as e:
        logger.error(f"❌ [INDEXING] Failed to start indexing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "local-indexing", "code_source": "beam-app.py"}

if __name__ == "__main__":
    # Run the local indexing service
    logger.info("Starting local indexing service using actual beam-app.py code...")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        log_level="info"
    )