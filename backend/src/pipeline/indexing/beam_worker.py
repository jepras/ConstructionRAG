"""
Beam worker for ConstructionRAG indexing pipeline.

This module contains the actual pipeline logic that runs on Beam's GPU instances.
It handles document processing, progress tracking, and callbacks to Railway.
"""

import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
from uuid import UUID

# Import our existing pipeline components
from src.pipeline.indexing.orchestrator import IndexingOrchestrator
from src.pipeline.shared.models import DocumentInput, UploadType
from src.config.database import get_supabase_admin_client
from src.services.storage_service import StorageService

logger = logging.getLogger(__name__)


async def run_indexing_pipeline_on_beam(
    indexing_run_id: str,
    document_ids: List[str],
    user_id: str,
    project_id: str,
) -> Dict[str, Any]:
    """
    Main Beam worker function for document indexing pipeline.

    This function runs the complete 5-step indexing pipeline on Beam's GPU instances.
    It handles both single and batch document processing with unified embedding.

    Args:
        indexing_run_id: Unique identifier for this indexing run
        document_ids: List of document IDs to process
        user_id: User ID who uploaded the documents
        project_id: Project ID the documents belong to

    Returns:
        Dict containing processing results and statistics
    """
    try:
        logger.info(f"🚀 Starting Beam indexing pipeline for run: {indexing_run_id}")
        logger.info(f"📄 Processing {len(document_ids)} documents")

        # Initialize services
        db = get_supabase_admin_client()
        storage_service = StorageService()

        # Create document inputs for the pipeline
        document_inputs = []

        for doc_id in document_ids:
            # Fetch document info from database
            doc_result = db.table("documents").select("*").eq("id", doc_id).execute()

            if not doc_result.data:
                logger.error(f"Document {doc_id} not found in database")
                continue

            doc_data = doc_result.data[0]

            # Create document input for pipeline
            document_input = DocumentInput(
                document_id=UUID(doc_id),
                run_id=UUID(indexing_run_id),
                user_id=UUID(user_id),
                file_path=doc_data.get("file_path", ""),
                filename=doc_data.get("filename", ""),
                upload_type=UploadType.USER_PROJECT,
                project_id=UUID(project_id),
                index_run_id=UUID(indexing_run_id),
                metadata={"project_id": str(project_id)},
            )
            document_inputs.append(document_input)

        if not document_inputs:
            logger.error("No valid documents found for processing")
            return {
                "status": "failed",
                "error": "No valid documents found",
                "indexing_run_id": indexing_run_id,
            }

        # Initialize orchestrator
        orchestrator = IndexingOrchestrator(
            db=db,
            storage=storage_service,
            use_test_storage=False,
            upload_type=UploadType.USER_PROJECT,
        )

        # Process documents using the unified method
        logger.info(
            f"🔄 Starting unified document processing for {len(document_inputs)} documents"
        )
        success = await orchestrator.process_documents(
            document_inputs, existing_indexing_run_id=UUID(indexing_run_id)
        )

        if success:
            logger.info(
                f"✅ Indexing pipeline completed successfully for run: {indexing_run_id}"
            )

            # Update indexing run status
            db.table("indexing_runs").update(
                {"status": "completed", "completed_at": "now()"}
            ).eq("id", indexing_run_id).execute()

            return {
                "status": "completed",
                "indexing_run_id": indexing_run_id,
                "document_count": len(document_inputs),
                "message": "Indexing pipeline completed successfully",
            }
        else:
            logger.error(f"❌ Indexing pipeline failed for run: {indexing_run_id}")

            # Update indexing run status
            db.table("indexing_runs").update(
                {"status": "failed", "completed_at": "now()"}
            ).eq("id", indexing_run_id).execute()

            return {
                "status": "failed",
                "indexing_run_id": indexing_run_id,
                "document_count": len(document_inputs),
                "error": "Indexing pipeline failed during processing",
            }

    except Exception as e:
        logger.error(f"💥 Critical error in Beam indexing pipeline: {e}")

        # Update indexing run status
        try:
            db.table("indexing_runs").update(
                {"status": "failed", "error_message": str(e), "completed_at": "now()"}
            ).eq("id", indexing_run_id).execute()
        except:
            logger.error("Failed to update indexing run status")

        return {
            "status": "failed",
            "indexing_run_id": indexing_run_id,
            "error": str(e),
            "message": "Critical error during indexing pipeline execution",
        }


# For testing purposes
if __name__ == "__main__":
    # Test the worker locally
    async def test_worker():
        result = await run_indexing_pipeline_on_beam(
            indexing_run_id="test-run-123",
            document_ids=["test-doc-1"],
            user_id="test-user",
            project_id="test-project",
        )
        print(f"Test result: {result}")

    asyncio.run(test_worker())
