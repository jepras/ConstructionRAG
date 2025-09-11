"""
Loops service for sending transactional emails.
"""

import json
import os
import logging
from typing import Dict, Any, Optional
import httpx
from src.config.database import get_supabase_admin_client

logger = logging.getLogger(__name__)


class LoopsService:
    """Service for sending transactional emails via Loops.so API."""

    # Hardcoded template IDs (these are not secrets, just template references)
    WIKI_COMPLETION_TEMPLATE_ID = "cmfb0g26t89llxf0i592li27q"
    NEWSLETTER_CONFIRMATION_TEMPLATE_ID = "cmfb5sk790boz4o0igafcmfm4"
    AUTHENTICATED_WIKI_COMPLETION_TEMPLATE_ID = "cmfc9jow3ajs80f0is1ebv0c6"
    ERROR_NOTIFICATION_TEMPLATE_ID = "cmfe2w96f00c6vs0if2nvyuha"  # Admin error notifications
    USER_ERROR_NOTIFICATION_TEMPLATE_ID = "cmfe3lbsp0vew120inwjgly3h"  # User error notifications

    def __init__(self):
        self.api_key = os.getenv("LOOPS_API_KEY")
        self.api_url = "https://app.loops.so/api/v1/transactional"

        if not self.api_key:
            raise ValueError("LOOPS_API_KEY environment variable not set")

        # Log configuration (truncated for security)
        api_key_preview = self.api_key[:4] + "..." if self.api_key else "None"
        logger.info(
            f"LoopsService initialized - API Key: {api_key_preview}, Templates: Wiki({self.WIKI_COMPLETION_TEMPLATE_ID[:4]}...), Newsletter({self.NEWSLETTER_CONFIRMATION_TEMPLATE_ID[:4]}...), Authenticated({self.AUTHENTICATED_WIKI_COMPLETION_TEMPLATE_ID[:4]}...)"
        )

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
            logger.info(
                f"Payload: email={email}, wikiUrl={wiki_url}, projectName={project_name}, addToAudience={add_to_audience}, userGroup={user_group}"
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=payload, headers=headers, timeout=30.0)

                response_data = (
                    response.json()
                    if response.headers.get("content-type", "").startswith("application/json")
                    else response.text
                )

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

    async def send_authenticated_wiki_completion_email(
        self,
        email: str,
        wiki_url: str,
        project_name: str = "Your Project",
        user_name: str = None,
        add_to_audience: bool = True,
        user_group: str = "Authenticated Users",
    ) -> Dict[str, Any]:
        """
        Send a wiki completion notification email for authenticated users.

        Args:
            email: Recipient email address
            wiki_url: URL to the completed wiki (private dashboard URL)
            project_name: Name of the project/documents processed
            user_name: Optional user name for personalization
            add_to_audience: Whether to add contact to audience (default: True)
            user_group: User group to assign (default: "Authenticated Users")

        Returns:
            Dict containing success status and response details
        """
        try:
            payload = {
                "transactionalId": self.AUTHENTICATED_WIKI_COMPLETION_TEMPLATE_ID,
                "email": email,
                "dataVariables": {
                    "wikiUrl": wiki_url,
                    "projectName": project_name,
                    "userName": user_name or "there",  # Friendly fallback
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
            logger.info(
                f"Sending authenticated wiki completion email to {email} with template ID: {self.AUTHENTICATED_WIKI_COMPLETION_TEMPLATE_ID[:4]}..."
            )
            logger.info(
                f"Payload: email={email}, wikiUrl={wiki_url}, projectName={project_name}, userName={user_name}, addToAudience={add_to_audience}, userGroup={user_group}"
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=payload, headers=headers, timeout=30.0)

                response_data = (
                    response.json()
                    if response.headers.get("content-type", "").startswith("application/json")
                    else response.text
                )

                if response.status_code == 200:
                    logger.info(f"✅ Authenticated wiki completion email sent successfully to {email}")
                    return {
                        "success": True,
                        "message": "Authenticated wiki completion email sent successfully",
                        "response": response_data,
                    }
                else:
                    error_msg = f"❌ Authenticated wiki completion email failed - Status: {response.status_code}, Response: {response_data}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                    }

        except httpx.TimeoutException:
            error_msg = f"Timeout sending authenticated wiki completion email to {email}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except httpx.RequestError as e:
            error_msg = f"Request error sending authenticated wiki completion email to {email}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error sending authenticated wiki completion email to {email}: {str(e)}"
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
                response = await client.post(self.api_url, json=payload, headers=headers, timeout=30.0)

                if response.status_code == 200:
                    logger.info(f"Transactional email sent successfully to {email}")
                    return {
                        "success": True,
                        "message": "Email sent successfully",
                        "response": response.json(),
                    }
                else:
                    error_msg = (
                        f"Failed to send email to {email}. Status: {response.status_code}, Response: {response.text}"
                    )
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
            logger.info(
                f"Sending newsletter confirmation to {email} with ID: {self.NEWSLETTER_CONFIRMATION_TEMPLATE_ID[:4]}..."
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=payload, headers=headers, timeout=30.0)

                response_data = (
                    response.json()
                    if response.headers.get("content-type", "").startswith("application/json")
                    else response.text
                )

                if response.status_code == 200:
                    logger.info(f"✅ Newsletter confirmation sent successfully to {email}")
                    return {
                        "success": True,
                        "message": "Newsletter confirmation email sent successfully",
                        "response": response_data,
                    }
                else:
                    error_msg = (
                        f"❌ Newsletter confirmation failed - Status: {response.status_code}, Response: {response_data}"
                    )
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

    async def send_error_notification(
        self,
        error_stage: str,
        error_message: str,
        indexing_run_id: str,
        user_email: str = None,
        project_name: str = "Unknown Project",
        debug_info: str = None,
    ) -> Dict[str, Any]:
        """
        Send an error notification email to the admin when upload processing fails.

        Args:
            error_stage: Stage where error occurred (upload/beam_processing/wiki_generation)
            error_message: Technical error details
            indexing_run_id: Correlation ID for debugging
            user_email: Email of user who uploaded (optional)
            project_name: Name of the project/documents processed
            debug_info: Additional debugging context (logs URL, etc.)

        Returns:
            Dict containing success status and response details
        """
        try:
            admin_email = "jeprasher@gmail.com"

            payload = {
                "transactionalId": self.ERROR_NOTIFICATION_TEMPLATE_ID,
                "email": admin_email,
                "dataVariables": {
                    "errorStage": error_stage,
                    "errorMessage": error_message,
                    "indexingRunId": indexing_run_id,
                    "userEmail": user_email or "Anonymous",
                    "projectName": project_name,
                    "debugInfo": debug_info or f"Check Railway logs for: {indexing_run_id}",
                },
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            logger.info(f"Sending error notification for {error_stage} failure in run {indexing_run_id}")
            logger.info(f"Error: {error_message}")

            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=payload, headers=headers, timeout=30.0)

                response_data = (
                    response.json()
                    if response.headers.get("content-type", "").startswith("application/json")
                    else response.text
                )

                if response.status_code == 200:
                    logger.info(f"✅ Error notification sent successfully for run {indexing_run_id}")
                    return {
                        "success": True,
                        "message": "Error notification sent successfully",
                        "response": response_data,
                    }
                else:
                    error_msg = (
                        f"❌ Error notification failed - Status: {response.status_code}, Response: {response_data}"
                    )
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                    }

        except httpx.TimeoutException:
            error_msg = f"Timeout sending error notification for run {indexing_run_id}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except httpx.RequestError as e:
            error_msg = f"Request error sending error notification for run {indexing_run_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error sending error notification for run {indexing_run_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def send_user_error_notification(self, user_email: str) -> Dict[str, Any]:
        """
        Send a simple error notification email to the user when their upload fails.
        
        Args:
            user_email: User's email address
            
        Returns:
            Dict containing success status and response details
        """
        try:
            payload = {
                "transactionalId": self.USER_ERROR_NOTIFICATION_TEMPLATE_ID,
                "email": user_email,
                "dataVariables": {}  # No template variables needed
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            logger.info(f"Sending user error notification to {user_email}")

            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=payload, headers=headers, timeout=30.0)

                response_data = (
                    response.json()
                    if response.headers.get("content-type", "").startswith("application/json")
                    else response.text
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ User error notification sent successfully to {user_email}")
                    return {
                        "success": True,
                        "message": "User error notification sent successfully",
                        "response": response_data,
                    }
                else:
                    error_msg = f"❌ User error notification failed - Status: {response.status_code}, Response: {response_data}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "status_code": response.status_code,
                    }

        except httpx.TimeoutException:
            error_msg = f"Timeout sending user error notification to {user_email}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except httpx.RequestError as e:
            error_msg = f"Request error sending user error notification to {user_email}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error sending user error notification to {user_email}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    @staticmethod
    def extract_project_name_from_documents(indexing_run_id: str) -> str:
        """
        Extract project name from document filenames or metadata.

        Args:
            indexing_run_id: The indexing run ID to extract project name for

        Returns:
            Extracted project name or "Unknown Project" as fallback
        """
        try:
            admin_db = get_supabase_admin_client()

            # Get documents for this indexing run
            run_docs = (
                admin_db.table("indexing_run_documents")
                .select("document_id")
                .eq("indexing_run_id", indexing_run_id)
                .execute()
            )
            docs_result = None
            if run_docs.data:
                doc_ids = [row["document_id"] for row in run_docs.data]
                docs_result = admin_db.table("documents").select("filename").in_("id", doc_ids).limit(5).execute()

            if docs_result and docs_result.data:
                # Extract common project name from filenames
                filenames = [doc.get("filename", "") for doc in docs_result.data]
                if filenames:
                    # Simple heuristic: use first part of filename before common separators
                    first_filename = filenames[0]
                    for separator in [" - ", "_", "-", ".", " "]:
                        if separator in first_filename:
                            project_part = first_filename.split(separator)[0].strip()
                            if len(project_part) > 3:  # Reasonable project name length
                                return project_part.title()

                    # If no separators, use first 30 chars of filename
                    if len(first_filename) > 30:
                        return first_filename[:30].strip() + "..."

                    return first_filename.replace(".pdf", "").replace(".PDF", "").strip()

        except Exception as e:
            logger.warning(f"Failed to extract project name for run {indexing_run_id}: {e}")

        return "Unknown Project"

    @staticmethod
    def format_error_context(stage: str, step: str, error: str, context: Dict[str, Any]) -> str:
        """
        Format error context as readable JSON for email notifications.

        Args:
            stage: The stage where error occurred
            step: The specific step that failed
            error: The error message
            context: Additional context dictionary

        Returns:
            Formatted JSON string
        """
        error_obj = {"stage": stage, "step": step, "error": error, "context": context}

        try:
            return json.dumps(error_obj, indent=2, default=str)
        except Exception:
            # Fallback to string representation
            return str(error_obj)
