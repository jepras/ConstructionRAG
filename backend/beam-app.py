"""
Beam v2 application for ConstructionRAG indexing pipeline.

This file defines the Beam task queue that will handle the document processing pipeline
on GPU-accelerated instances, while keeping the Railway backend responsive.
"""

from beam import Image, task_queue, env
import os


# Simple test version - no complex imports
def run_indexing_pipeline_on_beam(
    indexing_run_id: str, document_ids: list, user_id: str, project_id: str
):
    """Simple test version of the beam worker"""
    return {
        "status": "test_success",
        "message": "Beam worker is working!",
        "indexing_run_id": indexing_run_id,
        "document_count": len(document_ids),
        "user_id": user_id,
        "project_id": project_id,
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
    indexing_run_id: str, document_ids: list, user_id: str, project_id: str
):
    """
    Beam task queue entry point for document indexing pipeline.

    This function is triggered by Railway when documents are uploaded.
    It runs the complete 5-step indexing pipeline on Beam's GPU instances.

    Args:
        indexing_run_id: Unique identifier for this indexing run
        document_ids: List of document IDs to process
        user_id: User ID who uploaded the documents
        project_id: Project ID the documents belong to
    """
    if env.is_remote():
        return run_indexing_pipeline_on_beam(
            indexing_run_id, document_ids, user_id, project_id
        )
    else:
        # Local development - just return success
        print(f"Local development mode - would process {len(document_ids)} documents")
        return {"status": "local_dev_mode", "document_count": len(document_ids)}
