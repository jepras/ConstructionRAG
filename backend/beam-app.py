"""
Beam v2 application for ConstructionRAG indexing pipeline.

This file defines the Beam task queue that will handle the document processing pipeline
on GPU-accelerated instances, while keeping the Railway backend responsive.
"""

import asyncio
import os
from typing import List, Dict, Any, Optional
from uuid import UUID

import httpx
from beam import Image, task_queue, env

# Import our existing pipeline components
from src.pipeline.indexing.orchestrator import IndexingOrchestrator
from src.pipeline.shared.models import DocumentInput
from src.models.pipeline import UploadType
from src.config.database import get_supabase_admin_client
from src.services.storage_service import StorageService


async def trigger_wiki_generation(indexing_run_id: str, backend_url: str, auth_token: str = None, user_id: str = None, project_id: str = None):
    """
    Trigger wiki generation for a completed indexing run.
    
    Args:
        indexing_run_id: The completed indexing run ID
        backend_url: The backend URL to call for wiki generation
        auth_token: JWT token for authenticated requests (optional)
        user_id: User ID (optional for email uploads)
        project_id: Project ID (optional for email uploads)
    """
    try:
        if not backend_url:
            print("⚠️ Backend URL not provided, skipping wiki generation")
            return
        
        wiki_url = f"{backend_url}/api/wiki/runs?index_run_id={indexing_run_id}"
        payload = {}  # Empty payload since index_run_id is now a query parameter
        
        print(f"🔄 Triggering wiki generation for run: {indexing_run_id}")
        print(f"🔍 DEBUG: Wiki URL: {wiki_url}")
        print(f"🔍 DEBUG: Payload: {payload}")
        print(f"🔍 DEBUG: Auth token provided: {bool(auth_token)}")
        print(f"🔍 DEBUG: User ID: {user_id}")
        print(f"🔍 DEBUG: Project ID: {project_id}")
        
        # Set up headers for authentication if token is provided
        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
            print(f"🔐 Using JWT token for authenticated wiki generation")
            print(f"🔍 DEBUG: Auth header set: Bearer {auth_token[:20]}...{auth_token[-10:] if len(auth_token) > 30 else auth_token}")
        else:
            print(f"🔓 Making anonymous wiki generation request")
        
        print(f"🌐 Making HTTP POST request to: {wiki_url}")
        print(f"📤 Headers: {list(headers.keys())}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(wiki_url, json=payload, headers=headers)
                
                print(f"📥 Response status: {response.status_code}")
                print(f"📥 Response headers: {dict(response.headers)}")
                print(f"📥 Response text: {response.text}")
                
                if response.status_code == 200:
                    print(f"✅ Wiki generation triggered successfully")
                    try:
                        response_json = response.json()
                        print(f"📄 Response JSON: {response_json}")
                    except Exception as json_error:
                        print(f"⚠️ Could not parse response as JSON: {json_error}")
                else:
                    print(f"⚠️ Wiki generation trigger failed: {response.status_code} - {response.text}")
                    print(f"🔍 DEBUG: Response reason: {response.reason_phrase}")
                    
            except httpx.TimeoutException as timeout_error:
                print(f"⏰ Request timed out: {timeout_error}")
            except httpx.RequestError as req_error:
                print(f"🌐 Request error: {req_error}")
            except Exception as http_error:
                print(f"💥 Unexpected HTTP error: {http_error}")
                
    except Exception as e:
        print(f"⚠️ Error triggering wiki generation: {type(e).__name__}: {e}")
        import traceback
        print(f"📍 Full traceback: {traceback.format_exc()}")
        # Don't fail the indexing pipeline if wiki generation fails


async def run_indexing_pipeline_on_beam(
    indexing_run_id: str,
    document_ids: List[str],
    user_id: str = None,
    project_id: str = None,
    backend_url: str = None,
    auth_token: str = None,
) -> Dict[str, Any]:
    """
    Main Beam worker function for document indexing pipeline.

    This function runs the complete 5-step indexing pipeline on Beam's GPU instances.
    It handles both single and batch document processing with unified embedding.

    Args:
        indexing_run_id: Unique identifier for this indexing run
        document_ids: List of document IDs to process
        user_id: User ID who uploaded the documents (optional for email uploads)
        project_id: Project ID the documents belong to (optional for email uploads)

    Returns:
        Dict containing processing results and statistics
    """
    try:
        print(f"🚀 Starting Beam indexing pipeline for run: {indexing_run_id}")
        print(f"📄 Processing {len(document_ids)} documents")

        # Initialize services
        print("🔧 Initializing services...")
        db = get_supabase_admin_client()
        storage_service = StorageService()
        print("✅ Services initialized")

        # Quick database connectivity test
        try:
            test_run = (
                db.table("indexing_runs")
                .select("id")
                .eq("id", str(indexing_run_id))
                .execute()
            )
            if not test_run.data:
                print(f"❌ Indexing run {indexing_run_id} not found in database")
                return {
                    "status": "failed",
                    "indexing_run_id": indexing_run_id,
                    "error": f"Indexing run {indexing_run_id} not found",
                }
            print(f"✅ Found indexing run: {indexing_run_id}")
        except Exception as db_error:
            print(f"❌ Database connection failed: {db_error}")
            return {
                "status": "failed",
                "indexing_run_id": indexing_run_id,
                "error": f"Database connection failed: {str(db_error)}",
            }

        # Create document inputs for the pipeline
        document_inputs = []
        print(f"📋 Preparing {len(document_ids)} documents...")

        for i, doc_id in enumerate(document_ids):
            try:
                doc_result = (
                    db.table("documents").select("*").eq("id", doc_id).execute()
                )
                if not doc_result.data:
                    print(f"❌ Document {doc_id} not found")
                    continue

                doc_data = doc_result.data[0]
                document_input = DocumentInput(
                    document_id=UUID(doc_id),
                    run_id=UUID(indexing_run_id),
                    user_id=UUID(user_id) if user_id else None,
                    file_path=doc_data.get("file_path", ""),
                    filename=doc_data.get("filename", ""),
                    upload_type=(
                        UploadType.EMAIL if not user_id else UploadType.USER_PROJECT
                    ),
                    project_id=UUID(project_id) if project_id else None,
                    index_run_id=UUID(indexing_run_id),
                    metadata={"project_id": str(project_id)} if project_id else {},
                )
                document_inputs.append(document_input)

            except Exception as doc_error:
                print(f"❌ Error processing document {doc_id}: {doc_error}")
                continue

        if not document_inputs:
            print("❌ No valid documents found for processing")
            return {
                "status": "failed",
                "error": "No valid documents found",
                "indexing_run_id": indexing_run_id,
            }

        print(f"✅ Prepared {len(document_inputs)} documents")

        # Initialize orchestrator
        print("🔧 Initializing orchestrator...")
        orchestrator = IndexingOrchestrator(
            db=db,
            storage=storage_service,
            use_test_storage=False,
            upload_type=(UploadType.EMAIL if not user_id else UploadType.USER_PROJECT),
        )
        print("✅ Orchestrator ready")

        # Process documents using the unified method
        print(f"🔄 Starting document processing...")
        try:
            success = await orchestrator.process_documents(
                document_inputs, existing_indexing_run_id=UUID(indexing_run_id)
            )
            print(
                f"🔄 Processing completed: {'✅ Success' if success else '❌ Failed'}"
            )
        except Exception as orchestrator_error:
            print(f"❌ Orchestrator error: {orchestrator_error}")
            return {
                "status": "failed",
                "indexing_run_id": indexing_run_id,
                "error": f"Orchestrator error: {str(orchestrator_error)}",
            }

        if success:
            print(f"✅ Indexing pipeline completed successfully")
            
            # Trigger wiki generation
            if backend_url:
                await trigger_wiki_generation(indexing_run_id, backend_url, auth_token, user_id, project_id)
            else:
                print("⚠️ Backend URL not provided, skipping wiki generation")
            
            return {
                "status": "completed",
                "indexing_run_id": indexing_run_id,
                "document_count": len(document_inputs),
                "message": "Indexing pipeline completed successfully",
            }
        else:
            print(f"❌ Indexing pipeline failed")
            return {
                "status": "failed",
                "indexing_run_id": indexing_run_id,
                "document_count": len(document_inputs),
                "error": "Indexing pipeline failed during processing",
            }

    except Exception as e:
        print(f"💥 Critical error: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "message": "Critical error during indexing pipeline execution",
        }


@task_queue(
    name="construction-rag-indexing",
    cpu=4,
    memory="8Gi",
    gpu="T4",
    image=Image(
        python_version="python3.11",  # Changed from 3.12 for Unstructured compatibility
        python_packages="beam_requirements.txt",
        # Add system dependencies for Unstructured hi_res strategy
        commands=[
            "apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libxrender1 libgomp1 libgcc-s1 libstdc++6 fonts-liberation poppler-utils tesseract-ocr tesseract-ocr-dan"
        ],
    ),
    # Remove environment variable dependency - pass URL as parameter instead
    # Timeout set to 30 minutes to match current pipeline expectations
    timeout=1800,
)
def process_documents(
    indexing_run_id: str,
    document_ids: list,
    user_id: str = None,
    project_id: str = None,
    backend_url: str = None,
    auth_token: str = None,
):
    """
    Beam task queue entry point for document indexing pipeline.

    This function is triggered by Railway when documents are uploaded.
    It runs the complete 5-step indexing pipeline on Beam's GPU instances.

    Args:
        indexing_run_id: Unique identifier for this indexing run
        document_ids: List of document IDs to process
        user_id: User ID who uploaded the documents (optional for email uploads)
        project_id: Project ID the documents belong to (optional for email uploads)
    """
    if env.is_remote():
        # Debug: Log all parameters received
        print(f"🔍 DEBUG: Received parameters:")
        print(f"  - indexing_run_id: {indexing_run_id}")
        print(f"  - document_ids: {document_ids}")
        print(f"  - user_id: {user_id}")
        print(f"  - project_id: {project_id}")
        print(f"  - backend_url: {backend_url}")
        print(f"  - auth_token: {bool(auth_token)}")
        
        # Run the async function in an event loop
        return asyncio.run(
            run_indexing_pipeline_on_beam(
                indexing_run_id, document_ids, user_id, project_id, backend_url, auth_token
            )
        )
    else:
        # Local development - just return success
        print(f"Local development mode - would process {len(document_ids)} documents")
        return {"status": "local_dev_mode", "document_count": len(document_ids)}
