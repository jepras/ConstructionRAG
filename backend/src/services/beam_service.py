"""
Beam service for Railway to trigger document processing tasks on Beam.
"""

import os
import logging
from typing import List, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class BeamService:
    """Service for communicating with Beam task queue."""

    def __init__(self):
        # Check if we're in local development mode
        self.use_local_indexing = os.getenv("USE_LOCAL_INDEXING", "false").lower() == "true"
        
        if self.use_local_indexing:
            # Use local indexing container
            self.beam_url = "http://indexing:8001/process"
            self.beam_token = "local-development"  # Not used for local
            logger.info("[DEBUG] Using local indexing container at http://indexing:8001")
        else:
            # Use external Beam
            self.beam_url = os.getenv("BEAM_WEBHOOK_URL")
            self.beam_token = os.getenv("BEAM_AUTH_TOKEN")

            if not self.beam_url:
                raise ValueError("BEAM_WEBHOOK_URL environment variable not set")
            if not self.beam_token:
                raise ValueError("BEAM_AUTH_TOKEN environment variable not set")
            logger.info(f"[DEBUG] Using external Beam at {self.beam_url}")

    async def trigger_indexing_pipeline(
        self,
        indexing_run_id: str,
        document_ids: List[str],
        user_id: str = None,
        project_id: str = None,
        username: str = None,
        project_slug: str = None,
    ) -> Dict[str, Any]:
        """
        Trigger the indexing pipeline on Beam.

        Args:
            indexing_run_id: Unique identifier for this indexing run
            document_ids: List of document IDs to process
            user_id: User ID (optional for email uploads)
            project_id: Project ID (optional for email uploads)
            username: Username for unified GitHub-style storage paths (optional)
            project_slug: Project slug for unified GitHub-style storage paths (optional)

        Returns:
            Dict containing the task_id and status
        """
        try:
            payload = {
                "indexing_run_id": indexing_run_id,
                "document_ids": document_ids,
            }

            # Add optional fields if provided
            if user_id:
                payload["user_id"] = user_id
            if project_id:
                payload["project_id"] = project_id
            if username:
                payload["username"] = username
            if project_slug:
                payload["project_slug"] = project_slug

            # Add webhook URL and API key for wiki generation
            backend_url = os.getenv("BACKEND_API_URL")
            webhook_api_key = os.getenv("BEAM_WEBHOOK_API_KEY")
            
            # DEBUG: Log what we're getting from environment
            logger.info(f"[DEBUG] BACKEND_API_URL from env: {backend_url}")
            logger.info(f"[DEBUG] BEAM_WEBHOOK_API_KEY present: {'Yes' if webhook_api_key else 'No'}")

            if backend_url and webhook_api_key:
                webhook_url = f"{backend_url}/api/wiki/internal/webhook"
                payload["webhook_url"] = webhook_url
                payload["webhook_api_key"] = webhook_api_key
                logger.info(f"[DEBUG] Added webhook configuration: {webhook_url}")
            else:
                logger.warning(f"[DEBUG] Missing env vars - BACKEND_API_URL: {backend_url}, BEAM_WEBHOOK_API_KEY: {'present' if webhook_api_key else 'missing'} - wiki generation will be skipped")

            # Prepare headers based on local vs external Beam
            if self.use_local_indexing:
                headers = {
                    "Content-Type": "application/json",
                }
                timeout = 3600.0  # Longer timeout for local processing
            else:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.beam_token}",
                }
                timeout = 30.0

            logger.info(f"Triggering {'local indexing' if self.use_local_indexing else 'Beam'} task for indexing run: {indexing_run_id}")
            logger.info(f"Document IDs: {document_ids}")
            logger.info(f"[DEBUG] Full payload: {payload}")
            logger.info(f"[DEBUG] Target URL: {self.beam_url}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.beam_url,
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                )

                if response.status_code == 200:
                    result = response.json()
                    
                    if self.use_local_indexing:
                        # Local indexing response format
                        logger.info(f"(beam service) - Local indexing triggered successfully: {result.get('indexing_run_id')}")
                        return {
                            "status": "triggered",
                            "task_id": result.get("indexing_run_id"),  # Use run_id as task_id
                            "beam_url": self.beam_url,
                            "local": True
                        }
                    else:
                        # External Beam response format
                        task_id = result.get("task_id")
                        logger.info(f"(beam service) - Beam task triggered successfully: {task_id}")
                        return {
                            "status": "triggered",
                            "task_id": task_id,
                            "beam_url": self.beam_url,
                        }
                else:
                    logger.error(f"Beam API error: {response.status_code} - {response.text}")
                    return {
                        "status": "error",
                        "error": f"Beam API error: {response.status_code}",
                        "response": response.text,
                    }

        except Exception as e:
            logger.error(f"Error triggering Beam task: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    def get_beam_status_url(self, task_id: str) -> str:
        """Get the URL to check Beam task status."""
        return f"{self.beam_url}/status/{task_id}"
