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
    ) -> Dict[str, Any]:
        """
        Trigger the indexing pipeline on Beam.

        Args:
            indexing_run_id: Unique identifier for this indexing run
            document_ids: List of document IDs to process
            user_id: User ID (optional for email uploads)
            project_id: Project ID (optional for email uploads)

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
            
            # Add webhook URL and API key for wiki generation
            backend_url = os.getenv("BACKEND_API_URL")
            webhook_api_key = os.getenv("BEAM_WEBHOOK_API_KEY")
            logger.info(f"🔍 DEBUG: BACKEND_API_URL from environment: {backend_url}")
            logger.info(f"🔍 DEBUG: BEAM_WEBHOOK_API_KEY configured: {bool(webhook_api_key)}")
            
            if backend_url and webhook_api_key:
                payload["webhook_url"] = f"{backend_url}/api/wiki/internal/webhook"
                payload["webhook_api_key"] = webhook_api_key
                logger.info(f"✅ Added webhook configuration to payload")
                logger.info(f"📡 Webhook URL: {payload['webhook_url']}")
            else:
                logger.warning("⚠️ BACKEND_API_URL or BEAM_WEBHOOK_API_KEY not set - wiki generation will be skipped")

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
