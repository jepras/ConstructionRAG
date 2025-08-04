"""
Beam v2 application for ConstructionRAG indexing pipeline.

This file defines the Beam task queue that will handle the document processing pipeline
on GPU-accelerated instances, while keeping the Railway backend responsive.
"""

import asyncio
import os
from typing import List, Dict, Any, Optional
from uuid import UUID

from beam import Image, task_queue, env

# Import our existing pipeline components
from src.pipeline.indexing.orchestrator import IndexingOrchestrator
from src.pipeline.shared.models import DocumentInput
from src.models.pipeline import UploadType
from src.config.database import get_supabase_admin_client
from src.services.storage_service import StorageService


async def run_indexing_pipeline_on_beam(
    indexing_run_id: str,
    document_ids: List[str],
    user_id: str = None,
    project_id: str = None,
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
        print(f"🔍 Input parameters - user_id: {user_id}, project_id: {project_id}")
        print(f"🔍 Document IDs: {document_ids}")

        # Initialize services
        print("🔧 Initializing Supabase connection...")
        db = get_supabase_admin_client()
        print("✅ Supabase admin client initialized")

        # Test database connection
        try:
            print("🔍 Testing database connection...")
            test_result = db.table("documents").select("id").limit(1).execute()
            print(
                f"✅ Database connection successful, test query returned {len(test_result.data)} rows"
            )
        except Exception as db_error:
            print(f"❌ Database connection failed: {db_error}")
            return {
                "status": "failed",
                "indexing_run_id": indexing_run_id,
                "error": f"Database connection failed: {str(db_error)}",
            }

        print("🔧 Initializing storage service...")
        storage_service = StorageService()
        print("✅ Storage service initialized")

        # Create document inputs for the pipeline
        document_inputs = []
        print(f"🔍 Fetching document data for {len(document_ids)} documents...")

        for i, doc_id in enumerate(document_ids):
            print(f"📄 Processing document {i+1}/{len(document_ids)}: {doc_id}")

            # Fetch document info from database
            try:
                print(f"🔍 Fetching document data for ID: {doc_id}")
                doc_result = (
                    db.table("documents").select("*").eq("id", doc_id).execute()
                )
                print(f"📊 Document query result: {len(doc_result.data)} rows returned")

                if not doc_result.data:
                    print(f"❌ Document {doc_id} not found in database")
                    continue

                doc_data = doc_result.data[0]
                print(f"📋 Document data keys: {list(doc_data.keys())}")
                print(f"📋 Document filename: {doc_data.get('filename', 'N/A')}")
                print(f"📋 Document file_path: {doc_data.get('file_path', 'N/A')}")

                # Validate UUIDs before creating DocumentInput
                print(f"🔍 Validating UUIDs...")
                print(f"  - doc_id: {doc_id} (type: {type(doc_id)})")
                print(f"  - indexing_run_id: {indexing_run_id} (type: {type(indexing_run_id)})")
                print(f"  - user_id: {user_id} (type: {type(user_id)})")
                print(f"  - project_id: {project_id} (type: {type(project_id)})")

                # Create document input for pipeline - let the orchestrator handle validation
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
                print(f"✅ Successfully created DocumentInput for document {doc_id}")

            except Exception as doc_error:
                print(f"❌ Error processing document {doc_id}: {doc_error}")
                print(f"❌ Error type: {type(doc_error)}")
                continue

        if not document_inputs:
            print("❌ No valid documents found for processing")
            return {
                "status": "failed",
                "error": "No valid documents found",
                "indexing_run_id": indexing_run_id,
            }

        print(f"✅ Successfully created {len(document_inputs)} DocumentInput objects")

        # Initialize orchestrator
        print("🔧 Initializing IndexingOrchestrator...")
        orchestrator = IndexingOrchestrator(
            db=db,
            storage=storage_service,
            use_test_storage=False,
            upload_type=(UploadType.EMAIL if not user_id else UploadType.USER_PROJECT),
        )
        print("✅ IndexingOrchestrator initialized")

        # Process documents using the unified method - use existing indexing run
        print(
            f"🔄 Starting unified document processing for {len(document_inputs)} documents"
        )
        print(f"🔄 Calling orchestrator.process_documents with existing_indexing_run_id: {indexing_run_id}")

        try:
            success = await orchestrator.process_documents(
                document_inputs, existing_indexing_run_id=UUID(indexing_run_id)
            )
            print(
                f"🔄 Orchestrator.process_documents completed with success: {success}"
            )
        except Exception as orchestrator_error:
            print(f"❌ Error in orchestrator.process_documents: {orchestrator_error}")
            print(f"❌ Error type: {type(orchestrator_error)}")
            return {
                "status": "failed",
                "indexing_run_id": indexing_run_id,
                "error": f"Orchestrator error: {str(orchestrator_error)}",
            }

        if success:
            print(f"✅ Indexing pipeline completed successfully for run: {indexing_run_id}")
            return {
                "status": "completed",
                "indexing_run_id": indexing_run_id,
                "document_count": len(document_inputs),
                "message": "Indexing pipeline completed successfully",
            }
        else:
            print(f"❌ Indexing pipeline failed for run: {indexing_run_id}")
            return {
                "status": "failed",
                "indexing_run_id": indexing_run_id,
                "document_count": len(document_inputs),
                "error": "Indexing pipeline failed during processing",
            }

    except Exception as e:
        print(f"💥 Critical error in Beam indexing pipeline: {e}")
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
        python_version="python3.12",
        python_packages="beam_requirements.txt",
    ),
    # Timeout set to 30 minutes to match current pipeline expectations
    timeout=1800,
)
def process_documents(
    indexing_run_id: str,
    document_ids: list,
    user_id: str = None,
    project_id: str = None,
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
        # Run the async function in an event loop
        return asyncio.run(
            run_indexing_pipeline_on_beam(indexing_run_id, document_ids, user_id, project_id)
        )
    else:
        # Local development - just return success
        print(f"Local development mode - would process {len(document_ids)} documents")
        return {"status": "local_dev_mode", "document_count": len(document_ids)}
