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
    
    # Hardcoded template IDs (these are not secrets, just template references)
    WIKI_COMPLETION_TEMPLATE_ID = "cmfb0g26t89llxf0i592li27q"
    NEWSLETTER_CONFIRMATION_TEMPLATE_ID = "cmfb5sk790boz4o0igafcmfm4"

    def __init__(self):
        self.api_key = os.getenv("LOOPS_API_KEY")
        self.api_url = "https://app.loops.so/api/v1/transactional"

        if not self.api_key:
            raise ValueError("LOOPS_API_KEY environment variable not set")
        
        # Log configuration (truncated for security)
        api_key_preview = self.api_key[:4] + "..." if self.api_key else "None"
        logger.info(f"LoopsService initialized - API Key: {api_key_preview}, Templates: Wiki({self.WIKI_COMPLETION_TEMPLATE_ID[:4]}...), Newsletter({self.NEWSLETTER_CONFIRMATION_TEMPLATE_ID[:4]}...)")

    async def send_wiki_completion_email(
        self,
        email: str,
        wiki_url: str,
        project_name: str = "Your Project",
        add_to_audience: bool = True,
        user_group: str = None,
    ) -> Dict[str, Any]:
        """
        Send a wiki completion notification email.

        Args:
            email: Recipient email address
            wiki_url: URL to the completed wiki
            project_name: Name of the project/documents processed
            add_to_audience: Whether to add contact to audience (default: True)
            user_group: Optional user group to assign (e.g., "Public uploaders")

        Returns:
            Dict containing success status and response details
        """
        try:
            payload = {
                "transactionalId": self.WIKI_COMPLETION_TEMPLATE_ID,
                "email": email,
                "dataVariables": {
                    "wikiUrl": wiki_url,
                    "projectName": project_name,
                },
            }

            # Add to audience if requested
            if add_to_audience:
                payload["addToAudience"] = True
                
            # Add user group if specified
            if user_group:
                payload["userGroup"] = user_group

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Log the request details (without sensitive info)
            logger.info(f"Sending email to {email} with transactional ID: {self.WIKI_COMPLETION_TEMPLATE_ID[:4]}...")
            logger.info(f"Payload: email={email}, wikiUrl={wiki_url}, projectName={project_name}, addToAudience={add_to_audience}, userGroup={user_group}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url, 
                    json=payload, 
                    headers=headers,
                    timeout=30.0
                )

                response_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                
                if response.status_code == 200:
                    logger.info(f"✅ Loops API responded successfully (200) - Response: {response_data}")
                    logger.info(f"Wiki completion email sent successfully to {email}")
                    return {
                        "success": True,
                        "message": "Email sent successfully",
                        "response": response_data,
                    }
                else:
                    error_msg = f"❌ Loops API failed - Status: {response.status_code}, Response: {response_data}"
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

    async def send_newsletter_confirmation_email(
        self,
        email: str,
        add_to_audience: bool = True,
    ) -> Dict[str, Any]:
        """
        Send a newsletter signup confirmation email.

        Args:
            email: Recipient email address
            add_to_audience: Whether to add contact to audience (default: True)

        Returns:
            Dict containing success status and response details
        """
        try:
            payload = {
                "transactionalId": self.NEWSLETTER_CONFIRMATION_TEMPLATE_ID,
                "email": email,
                "dataVariables": {
                    "email": email,
                },
            }

            # Add to audience if requested
            if add_to_audience:
                payload["addToAudience"] = True
                payload["userGroup"] = "Newsletter Subscribers"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Log the request details (without sensitive info)
            logger.info(f"Sending newsletter confirmation to {email} with ID: {self.NEWSLETTER_CONFIRMATION_TEMPLATE_ID[:4]}...")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url, 
                    json=payload, 
                    headers=headers,
                    timeout=30.0
                )

                response_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                
                if response.status_code == 200:
                    logger.info(f"✅ Newsletter confirmation sent successfully to {email}")
                    return {
                        "success": True,
                        "message": "Newsletter confirmation email sent successfully",
                        "response": response_data,
                    }
                else:
                    error_msg = f"❌ Newsletter confirmation failed - Status: {response.status_code}, Response: {response_data}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                    }

        except httpx.TimeoutException:
            error_msg = f"Timeout sending newsletter confirmation to {email}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except httpx.RequestError as e:
            error_msg = f"Request error sending newsletter confirmation to {email}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error sending newsletter confirmation to {email}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}