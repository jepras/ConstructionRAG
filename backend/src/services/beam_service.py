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
        self.beam_url = os.getenv("BEAM_WEBHOOK_URL")
        self.beam_token = os.getenv("BEAM_AUTH_TOKEN")

        if not self.beam_url:
            raise ValueError("BEAM_WEBHOOK_URL environment variable not set")
        if not self.beam_token:
            raise ValueError("BEAM_AUTH_TOKEN environment variable not set")

    async def trigger_indexing_pipeline(
        self,
        indexing_run_id: str,
        document_ids: List[str],
        user_id: str = None,
        project_id: str = None,
        auth_token: str = None,
    ) -> Dict[str, Any]:
        """
        Trigger the indexing pipeline on Beam.

        Args:
            indexing_run_id: Unique identifier for this indexing run
            document_ids: List of document IDs to process
            user_id: User ID (optional for email uploads)
            project_id: Project ID (optional for email uploads)
            auth_token: JWT token for authenticated wiki generation (optional)

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
            
            # Add backend URL for wiki generation webhook
            backend_url = os.getenv("BACKEND_API_URL")
            logger.info(f"🔍 DEBUG: BACKEND_API_URL from environment: {backend_url}")
            if backend_url:
                payload["backend_url"] = backend_url
                logger.info(f"✅ Added backend_url to payload: {backend_url}")
            else:
                logger.warning("⚠️ BACKEND_API_URL not set in local environment - wiki generation will be skipped")
            
            # Add auth token for authenticated wiki generation
            if auth_token:
                payload["auth_token"] = auth_token
                logger.info(f"✅ Added auth_token to payload for authenticated wiki generation")
            else:
                logger.info("ℹ️ No auth_token provided - wiki generation will be anonymous")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.beam_token}",
            }

            logger.info(f"Triggering Beam task for indexing run: {indexing_run_id}")
            logger.info(f"Document IDs: {document_ids}")
            logger.info(f"🔍 DEBUG: Complete payload being sent to Beam: {payload}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.beam_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    task_id = result.get("task_id")
                    logger.info(f"Beam task triggered successfully: {task_id}")
                    return {
                        "status": "triggered",
                        "task_id": task_id,
                        "beam_url": self.beam_url,
                    }
                else:
                    logger.error(
                        f"Beam API error: {response.status_code} - {response.text}"
                    )
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
