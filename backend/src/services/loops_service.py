"""
Loops service for sending transactional emails.
"""

import os
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class LoopsService:
    """Service for sending transactional emails via Loops.so API."""

    def __init__(self):
        self.api_key = os.getenv("LOOPS_API_KEY")
        self.transactional_id = os.getenv("LOOPS_TRANSACTIONAL_ID")
        self.api_url = "https://app.loops.so/api/v1/transactional"

        if not self.api_key:
            raise ValueError("LOOPS_API_KEY environment variable not set")
        if not self.transactional_id:
            raise ValueError("LOOPS_TRANSACTIONAL_ID environment variable not set")

    async def send_wiki_completion_email(
        self,
        email: str,
        wiki_url: str,
        project_name: str = "Your Project",
        add_to_audience: bool = True,
    ) -> Dict[str, Any]:
        """
        Send a wiki completion notification email.

        Args:
            email: Recipient email address
            wiki_url: URL to the completed wiki
            project_name: Name of the project/documents processed
            add_to_audience: Whether to add contact to audience (default: True)

        Returns:
            Dict containing success status and response details
        """
        try:
            payload = {
                "transactionalId": self.transactional_id,
                "email": email,
                "dataVariables": {
                    "wikiUrl": wiki_url,
                    "projectName": project_name,
                },
            }

            # Add to audience if requested
            if add_to_audience:
                payload["addToAudience"] = True

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url, 
                    json=payload, 
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    logger.info(f"Wiki completion email sent successfully to {email}")
                    return {
                        "success": True,
                        "message": "Email sent successfully",
                        "response": response.json(),
                    }
                else:
                    error_msg = f"Failed to send email to {email}. Status: {response.status_code}, Response: {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                    }

        except httpx.TimeoutException:
            error_msg = f"Timeout sending email to {email}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except httpx.RequestError as e:
            error_msg = f"Request error sending email to {email}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error sending email to {email}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def send_transactional_email(
        self,
        email: str,
        data_variables: Dict[str, Any],
        add_to_audience: bool = False,
    ) -> Dict[str, Any]:
        """
        Send a generic transactional email with custom data variables.

        Args:
            email: Recipient email address
            data_variables: Custom data variables for email template
            add_to_audience: Whether to add contact to audience (default: False)

        Returns:
            Dict containing success status and response details
        """
        try:
            payload = {
                "transactionalId": self.transactional_id,
                "email": email,
                "dataVariables": data_variables,
            }

            if add_to_audience:
                payload["addToAudience"] = True

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url, 
                    json=payload, 
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    logger.info(f"Transactional email sent successfully to {email}")
                    return {
                        "success": True,
                        "message": "Email sent successfully",
                        "response": response.json(),
                    }
                else:
                    error_msg = f"Failed to send email to {email}. Status: {response.status_code}, Response: {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                    }

        except Exception as e:
            error_msg = f"Error sending transactional email to {email}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}