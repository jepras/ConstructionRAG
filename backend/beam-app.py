"""
Beam v2 application for Specfinder indexing pipeline.

This file defines the Beam task queue that will handle the document processing pipeline
on GPU-accelerated instances, while keeping the Railway backend responsive.
"""

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
from beam import Image, env, task_queue

# Structured logging
from src.utils.logging import get_logger

# Version tracking for debugging deployments
BEAM_VERSION = "2.2.0"  # Update this when making changes
DEPLOYMENT_DATE = "2025-09-01"
CHANGES = "Added resource monitoring and removed GPU to optimize costs"

# Initialize logger
logger = get_logger(__name__)

# Resource monitoring
from src.config.database import get_supabase_admin_client
from src.models.pipeline import UploadType

# Import our existing pipeline components
from src.pipeline.indexing.orchestrator import IndexingOrchestrator
from src.pipeline.shared.models import DocumentInput
from src.services.storage_service import StorageService
from src.utils.resource_monitor import get_monitor, log_resources


async def trigger_wiki_generation(indexing_run_id: str, webhook_url: str, webhook_api_key: str):
    """
    Trigger wiki generation for a completed indexing run via webhook.

    Args:
        indexing_run_id: The completed indexing run ID
        webhook_url: The webhook URL to call for wiki generation
        webhook_api_key: API key for webhook authentication
    """
    try:
        if not webhook_url:
            logger.warning("wiki_webhook_url_missing", extra={
                "run_id": indexing_run_id
            })
            return

        if not webhook_api_key:
            logger.warning("wiki_webhook_api_key_missing", extra={
                "run_id": indexing_run_id
            })
            return

        payload = {"indexing_run_id": indexing_run_id}

        logger.info("wiki_webhook_triggered", extra={
            "run_id": indexing_run_id,
            "webhook_url": webhook_url
        })

        # Set up headers with API key authentication
        headers = {"Content-Type": "application/json", "X-API-Key": webhook_api_key}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(webhook_url, json=payload, headers=headers)

                if response.status_code == 200:
                    logger.info("wiki_webhook_success", extra={
                        "run_id": indexing_run_id,
                        "status_code": response.status_code
                    })
                else:
                    logger.warning("wiki_webhook_failed", extra={
                        "run_id": indexing_run_id,
                        "status_code": response.status_code
                    })

            except httpx.TimeoutException as timeout_error:
                logger.error("wiki_webhook_timeout", extra={
                    "run_id": indexing_run_id,
                    "error": str(timeout_error)
                })
            except httpx.RequestError as req_error:
                logger.error("wiki_webhook_request_error", extra={
                    "run_id": indexing_run_id,
                    "error": str(req_error)
                })
            except Exception as http_error:
                logger.error("wiki_webhook_unexpected_error", extra={
                    "run_id": indexing_run_id,
                    "error": str(http_error)
                })

    except Exception as e:
        logger.error("wiki_generation_error", extra={
            "run_id": indexing_run_id,
            "error_type": type(e).__name__,
            "error": str(e)
        })
        # Don't fail the indexing pipeline if wiki generation fails


async def trigger_error_webhook(indexing_run_id: str, error_message: str, webhook_url: str = None, webhook_api_key: str = None):
    """
    Trigger error notification webhook for a failed indexing run.

    Args:
        indexing_run_id: The failed indexing run ID
        error_message: The error message to report
        webhook_url: The base webhook URL (will be modified to error-webhook endpoint)
        webhook_api_key: API key for webhook authentication
    """
    try:
        if not webhook_url or not webhook_api_key:
            logger.warning("error_webhook_not_configured", extra={
                "run_id": indexing_run_id,
                "webhook_url_provided": bool(webhook_url),
                "webhook_api_key_provided": bool(webhook_api_key)
            })
            return

        # Convert from success webhook URL to error webhook URL
        error_webhook_url = webhook_url.replace("/internal/webhook", "/internal/error-webhook")
        
        payload = {
            "indexing_run_id": indexing_run_id,
            "error_message": error_message,
            "error_stage": "beam_processing"
        }

        logger.error("error_webhook_triggered", extra={
            "run_id": indexing_run_id,
            "error_message": error_message,
            "error_webhook_url": error_webhook_url
        })

        # Set up headers with API key authentication
        headers = {"Content-Type": "application/json", "X-API-Key": webhook_api_key}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(error_webhook_url, json=payload, headers=headers)

                if response.status_code == 200:
                    logger.info("error_webhook_success", extra={
                        "run_id": indexing_run_id,
                        "status_code": response.status_code
                    })
                else:
                    logger.warning("error_webhook_failed", extra={
                        "run_id": indexing_run_id,
                        "status_code": response.status_code,
                        "response_text": response.text
                    })

            except httpx.TimeoutException as timeout_error:
                logger.error("error_webhook_timeout", extra={
                    "run_id": indexing_run_id,
                    "error": str(timeout_error)
                })
            except httpx.RequestError as req_error:
                logger.error("error_webhook_request_error", extra={
                    "run_id": indexing_run_id,
                    "error": str(req_error)
                })
            except Exception as http_error:
                logger.error("error_webhook_unexpected_error", extra={
                    "run_id": indexing_run_id,
                    "error": str(http_error)
                })

    except Exception as e:
        logger.error("error_webhook_trigger_failed", extra={
            "run_id": indexing_run_id,
            "error_type": type(e).__name__,
            "error": str(e)
        })
        # Don't fail further if error notification fails


async def run_indexing_pipeline_with_timeout_buffer(
    indexing_run_id: str,
    document_ids: list[str],
    user_id: str = None,
    project_id: str = None,
    webhook_url: str = None,
    webhook_api_key: str = None,
) -> dict[str, Any]:
    """
    Wrapper for pipeline execution with internal timeout buffer.
    
    Uses 3.5 hour internal timeout to ensure webhook is sent before Beam's 4h hard timeout.
    """
    # Set internal timeout to 3.5 hours (leaving 30min buffer before Beam's 4h limit)
    internal_timeout = 3.5 * 3600  # 3.5 hours in seconds
    
    try:
        return await asyncio.wait_for(
            run_indexing_pipeline_on_beam(
                indexing_run_id, document_ids, user_id, project_id, webhook_url, webhook_api_key
            ),
            timeout=internal_timeout
        )
    except asyncio.TimeoutError:
        timeout_error_message = f"Processing timeout: Task exceeded 3.5 hour limit (Beam has 4h hard timeout)"
        
        logger.error("internal_timeout_reached", extra={
            "run_id": indexing_run_id,
            "timeout_hours": 3.5,
            "beam_timeout_hours": 4.0
        })
        
        # Send error webhook before Beam kills the task
        await trigger_error_webhook(
            indexing_run_id, 
            timeout_error_message,
            webhook_url, 
            webhook_api_key
        )
        
        # Re-raise to let Beam know it failed
        raise Exception(timeout_error_message)


async def run_indexing_pipeline_on_beam(
    indexing_run_id: str,
    document_ids: list[str],
    user_id: str = None,
    project_id: str = None,
    webhook_url: str = None,
    webhook_api_key: str = None,
) -> dict[str, Any]:
    """
    Main Beam worker function for document indexing pipeline.

    This function runs the complete 5-step indexing pipeline on Beam's GPU instances.
    It handles both single and batch document processing with unified embedding.

    Args:
        indexing_run_id: Unique identifier for this indexing run
        document_ids: List of document IDs to process
        user_id: User ID who uploaded the documents (optional for email uploads)
        project_id: Project ID the documents belong to (optional for email uploads)
        webhook_url: URL to call for wiki generation after indexing completion
        webhook_api_key: API key for webhook authentication

    Returns:
        Dict containing processing results and statistics
    """
    try:
        logger.info("pipeline_started", extra={
            "run_id": indexing_run_id,
            "document_count": len(document_ids),
            "beam_version": BEAM_VERSION,
            "deployment_date": DEPLOYMENT_DATE,
            "changes": CHANGES,
            "user_id": user_id,
            "project_id": project_id
        })

        # Log initial resources
        log_resources("Pipeline Start")

        # Initialize services
        logger.info("services_initializing", extra={
            "run_id": indexing_run_id,
            "step": "initialization"
        })
        db = get_supabase_admin_client()
        storage_service = StorageService()
        logger.info("services_initialized", extra={
            "run_id": indexing_run_id,
            "step": "initialization"
        })

        # Quick database connectivity test
        try:
            test_run = db.table("indexing_runs").select("id").eq("id", str(indexing_run_id)).execute()
            if not test_run.data:
                logger.error("indexing_run_not_found", extra={
                    "run_id": indexing_run_id,
                    "error_type": "database_validation"
                })
                return {
                    "status": "failed",
                    "indexing_run_id": indexing_run_id,
                    "error": f"Indexing run {indexing_run_id} not found",
                }
            logger.info("indexing_run_validated", extra={
                "run_id": indexing_run_id,
                "step": "initialization"
            })
        except Exception as db_error:
            logger.error("database_connection_failed", extra={
                "run_id": indexing_run_id,
                "error_type": "database_connectivity",
                "error": str(db_error)
            }, exc_info=True)
            return {
                "status": "failed",
                "indexing_run_id": indexing_run_id,
                "error": f"Database connection failed: {str(db_error)}",
            }

        # Create document inputs for the pipeline
        document_inputs = []
        logger.info("document_preparation_started", extra={
            "run_id": indexing_run_id,
            "document_count": len(document_ids)
        })

        for i, doc_id in enumerate(document_ids):
            try:
                doc_result = db.table("documents").select("*").eq("id", doc_id).execute()
                if not doc_result.data:
                    logger.warning("document_not_found", extra={
                        "run_id": indexing_run_id,
                        "document_id": doc_id,
                        "document_index": i + 1,
                        "total_documents": len(document_ids)
                    })
                    continue

                doc_data = doc_result.data[0]
                document_input = DocumentInput(
                    document_id=UUID(doc_id),
                    run_id=UUID(indexing_run_id),
                    user_id=UUID(user_id) if user_id else None,
                    file_path=doc_data.get("file_path", ""),
                    filename=doc_data.get("filename", ""),
                    upload_type=(UploadType.EMAIL if not user_id else UploadType.USER_PROJECT),
                    project_id=UUID(project_id) if project_id else None,
                    index_run_id=UUID(indexing_run_id),
                    metadata={"project_id": str(project_id)} if project_id else {},
                )
                document_inputs.append(document_input)

            except Exception as doc_error:
                logger.error("document_preparation_error", extra={
                    "run_id": indexing_run_id,
                    "document_id": doc_id,
                    "error": str(doc_error)
                }, exc_info=True)
                continue

        if not document_inputs:
            logger.error("no_valid_documents", extra={
                "run_id": indexing_run_id,
                "requested_document_count": len(document_ids),
                "valid_document_count": 0
            })
            return {
                "status": "failed",
                "error": "No valid documents found",
                "indexing_run_id": indexing_run_id,
            }

        logger.info("document_preparation_completed", extra={
            "run_id": indexing_run_id,
            "requested_document_count": len(document_ids),
            "prepared_document_count": len(document_inputs)
        })

        # Initialize orchestrator
        logger.info("orchestrator_initializing", extra={
            "run_id": indexing_run_id,
            "upload_type": "email" if not user_id else "user_project",
            "use_test_storage": False
        })
        orchestrator = IndexingOrchestrator(
            db=db,
            storage=storage_service,
            use_test_storage=False,
            upload_type=(UploadType.EMAIL if not user_id else UploadType.USER_PROJECT),
        )
        logger.info("orchestrator_ready", extra={
            "run_id": indexing_run_id,
            "step": "initialization"
        })

        # Process documents using the unified method
        logger.info("document_processing_started", extra={
            "run_id": indexing_run_id,
            "document_count": len(document_inputs)
        })
        log_resources("Before Document Processing")

        try:
            success = await orchestrator.process_documents(
                document_inputs, existing_indexing_run_id=UUID(indexing_run_id)
            )
            logger.info("document_processing_completed", extra={
                "run_id": indexing_run_id,
                "status": "success" if success else "failed",
                "document_count": len(document_inputs)
            })
            log_resources("After Document Processing")
        except Exception as orchestrator_error:
            error_message = f"Orchestrator error: {str(orchestrator_error)}"
            logger.error("orchestrator_processing_error", extra={
                "run_id": indexing_run_id,
                "error_type": "orchestrator_failure",
                "error": error_message
            }, exc_info=True)
            
            # Trigger error webhook
            await trigger_error_webhook(indexing_run_id, error_message, webhook_url, webhook_api_key)
            
            return {
                "status": "failed",
                "indexing_run_id": indexing_run_id,
                "error": error_message,
            }

        if success:
            logger.info("pipeline_completed_successfully", extra={
                "run_id": indexing_run_id,
                "document_count": len(document_inputs),
                "status": "success"
            })

            # Log final resource usage
            monitor = get_monitor()
            summary = monitor.get_summary()
            logger.info("pipeline_resource_summary", extra={
                "run_id": indexing_run_id,
                "resource_usage": {
                    "peak_cpu_percent": summary["peak_cpu_percent"],
                    "peak_ram_percent": summary["peak_ram_percent"]
                }
            })

            # Trigger wiki generation via webhook
            if webhook_url and webhook_api_key:
                await trigger_wiki_generation(indexing_run_id, webhook_url, webhook_api_key)
            else:
                logger.warning("webhook_not_configured", extra={
                    "run_id": indexing_run_id,
                    "webhook_url_provided": bool(webhook_url),
                    "webhook_api_key_provided": bool(webhook_api_key)
                })

            return {
                "status": "completed",
                "indexing_run_id": indexing_run_id,
                "document_count": len(document_inputs),
                "message": "Indexing pipeline completed successfully",
                "resource_usage": {
                    "peak_cpu_percent": summary["peak_cpu_percent"],
                    "peak_ram_percent": summary["peak_ram_percent"],
                },
            }
        else:
            error_message = "Indexing pipeline failed during processing"
            logger.error("pipeline_processing_failed", extra={
                "run_id": indexing_run_id,
                "document_count": len(document_inputs),
                "error_type": "processing_failure",
                "error": error_message
            })
            
            # Trigger error webhook
            await trigger_error_webhook(indexing_run_id, error_message, webhook_url, webhook_api_key)
            
            return {
                "status": "failed",
                "indexing_run_id": indexing_run_id,
                "document_count": len(document_inputs),
                "error": error_message,
            }

    except Exception as e:
        error_message = f"Critical error during indexing pipeline execution: {str(e)}"
        logger.error("pipeline_critical_error", extra={
            "run_id": indexing_run_id,
            "error_type": "critical_failure",
            "error": error_message
        }, exc_info=True)
        
        # Trigger error webhook for critical failures
        await trigger_error_webhook(indexing_run_id, error_message, webhook_url, webhook_api_key)
        
        return {
            "status": "failed",
            "error": str(e),
            "message": "Critical error during indexing pipeline execution",
        }


@task_queue(
    name="construction-rag-indexing",
    cpu=10,  # Optimized: 10 cores for 5 workers (2 cores each)
    memory="20Gi",  # Optimized: 20GB for 5 workers (4GB each)
    # gpu="T4",  # REMOVED: Not used, saves $0.54/hour
    workers=5,  # Increased to 5 for better throughput
    image=Image(
        python_version="python3.11",  # Changed from 3.12 for Unstructured compatibility
        python_packages="beam_requirements.txt",
        # Add system dependencies for Unstructured hi_res strategy
        commands=[
            # Update package lists
            "apt-get update",
            # Install core system dependencies
            "apt-get install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libxrender1 libgomp1",
            # Install additional runtime libraries 
            "apt-get install -y libgcc-s1 libstdc++6 fonts-liberation",
            # Install OCR and PDF processing tools
            "apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-dan tesseract-ocr-eng",
            # Install additional image processing dependencies
            "apt-get install -y libjpeg-dev libpng-dev libtiff-dev libwebp-dev",
            # Verify installations
            "tesseract --version && pdfinfo -v || echo 'Warning: Some dependencies may not be properly installed'"
        ],
    ),
    # Remove environment variable dependency - pass URL as parameter instead
    # Timeout set to 4 hours for large PDF processing jobs
    timeout=14400,
)
def process_documents(
    indexing_run_id: str,
    document_ids: list,
    user_id: str = None,
    project_id: str = None,
    webhook_url: str = None,
    webhook_api_key: str = None,
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
    # Log version information at the start of every run
    logger.info("beam_task_started", extra={
        "beam_version": BEAM_VERSION,
        "deployment_date": DEPLOYMENT_DATE,
        "changes": CHANGES,
        "run_id": indexing_run_id,
        "document_count": len(document_ids),
        "start_time": datetime.now().isoformat(),
        "environment": "remote_beam"
    })

    if env.is_remote():
        try:
            # Run the async function with timeout buffer in an event loop
            return asyncio.run(
                run_indexing_pipeline_with_timeout_buffer(
                    indexing_run_id, document_ids, user_id, project_id, webhook_url, webhook_api_key
                )
            )
        except Exception as e:
            # Check if it's a timeout/cancellation/expiration
            error_str = str(e).lower()
            if "timeout" in error_str:
                error_type = "timeout"
            elif "cancelled" in error_str:
                error_type = "cancelled"  
            elif "expired" in error_str:
                error_type = "expired"
            else:
                error_type = "failure"
            
            logger.error("beam_task_failed", extra={
                "run_id": indexing_run_id,
                "error_type": error_type,
                "error": str(e)
            }, exc_info=True)
            
            # Call error webhook for timeout/cancellation/expiration
            if webhook_url and webhook_api_key:
                try:
                    asyncio.run(trigger_error_webhook(
                        indexing_run_id, 
                        f"Beam task {error_type}: {str(e)}",
                        webhook_url,
                        webhook_api_key
                    ))
                except Exception as webhook_error:
                    logger.error("webhook_trigger_failed", extra={
                        "run_id": indexing_run_id,
                        "webhook_error": str(webhook_error)
                    })
            else:
                logger.warning("webhook_not_configured_for_error", extra={
                    "run_id": indexing_run_id,
                    "webhook_url_provided": bool(webhook_url),
                    "webhook_api_key_provided": bool(webhook_api_key)
                })
            
            # Re-raise to let Beam know it failed
            raise
    else:
        # Local development - just return success
        logger.info("local_development_mode", extra={
            "run_id": indexing_run_id,
            "document_count": len(document_ids)
        })
        return {"status": "local_dev_mode", "document_count": len(document_ids)}
