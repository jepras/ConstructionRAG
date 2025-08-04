"""Storage service for handling Supabase Storage operations."""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Union
from uuid import UUID
import logging
from enum import Enum

from src.config.database import get_supabase_admin_client
from src.utils.exceptions import StorageError


class UploadType(str, Enum):
    """Type of upload - email-based or user project."""

    EMAIL = "email"
    USER_PROJECT = "user_project"


logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file storage operations in Supabase Storage."""

    def __init__(self, bucket_name: str = "pipeline-assets"):
        self.supabase = get_supabase_admin_client()
        self.bucket_name = bucket_name  # Allow custom bucket name

    @classmethod
    def create_test_storage(cls):
        """Create a storage service instance for testing."""
        return cls(bucket_name="pipeline-assets-test")

    async def ensure_bucket_exists(self) -> bool:
        """Ensure the storage bucket exists, create if it doesn't."""
        try:
            # Try to get bucket info
            result = self.supabase.storage.get_bucket(self.bucket_name)
            logger.info(f"Storage bucket '{self.bucket_name}' exists")
            return True
        except Exception:
            try:
                # Create bucket if it doesn't exist
                result = self.supabase.storage.create_bucket(
                    self.bucket_name,
                    options={
                        "public": False,  # Private bucket
                        "file_size_limit": 52428800,  # 50MB limit
                        "allowed_mime_types": [
                            "image/png",
                            "image/jpeg",
                            "image/jpg",
                            "application/pdf",
                            "text/html",
                            "text/plain",
                            "text/markdown",
                        ],
                    },
                )
                logger.info(f"Created storage bucket '{self.bucket_name}'")
                return True
            except Exception as e:
                logger.error(f"Failed to create storage bucket: {e}")
                raise StorageError(f"Failed to create storage bucket: {str(e)}")

    async def upload_file(
        self,
        file_path: Optional[str],
        storage_path: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload a file to Supabase Storage and return the public URL."""
        try:
            # Ensure bucket exists
            await self.ensure_bucket_exists()

            # Handle file content
            if file_path is None:
                # Create empty placeholder file
                file_content = b""
                if not content_type:
                    content_type = "text/plain"
            else:
                # Read file content
                with open(file_path, "rb") as f:
                    file_content = f.read()

                # Determine content type if not provided
                if not content_type:
                    content_type = self._get_content_type(file_path)

            # Upload file
            result = self.supabase.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": content_type},
            )

            # Get signed URL (since bucket is private)
            url = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                storage_path,
                expires_in=3600 * 24 * 7,  # 7 days
            )

            logger.info(f"Uploaded file to storage: {storage_path} -> {url}")
            return url

        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {e}")
            raise StorageError(f"Failed to upload file: {str(e)}")

    async def upload_extracted_page_image(
        self,
        image_path: str,
        document_id: UUID,
        page_num: int,
        complexity: str,
        upload_type: UploadType,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        index_run_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Upload an extracted page image and return metadata with URL."""
        try:
            filename = Path(image_path).name

            # Create storage path based on upload type
            if upload_type == UploadType.EMAIL:
                storage_path = f"email-uploads/index-runs/{index_run_id}/{document_id}/extracted-pages/{filename}"
            else:  # USER_PROJECT
                storage_path = f"users/{user_id}/projects/{project_id}/index-runs/{index_run_id}/{document_id}/extracted-pages/{filename}"

            # Upload file
            url = await self.upload_file(image_path, storage_path, "image/png")

            # Return metadata
            return {
                "url": url,
                "storage_path": storage_path,
                "filename": filename,
                "page_num": page_num,
                "complexity": complexity,
                "document_id": str(document_id),
                "upload_type": upload_type.value,
            }

        except Exception as e:
            logger.error(f"Failed to upload extracted page image: {e}")
            raise StorageError(f"Failed to upload extracted page image: {str(e)}")

    async def upload_table_image(
        self,
        image_path: str,
        document_id: UUID,
        table_id: str,
        upload_type: UploadType,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        index_run_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Upload a table image and return metadata with URL."""
        try:
            filename = Path(image_path).name

            # Create storage path based on upload type
            if upload_type == UploadType.EMAIL:
                storage_path = f"email-uploads/index-runs/{index_run_id}/{document_id}/table-images/{filename}"
            else:  # USER_PROJECT
                storage_path = f"users/{user_id}/projects/{project_id}/index-runs/{index_run_id}/{document_id}/table-images/{filename}"

            # Upload file
            url = await self.upload_file(image_path, storage_path, "image/png")

            # Return metadata
            return {
                "url": url,
                "storage_path": storage_path,
                "filename": filename,
                "table_id": table_id,
                "document_id": str(document_id),
                "upload_type": upload_type.value,
            }

        except Exception as e:
            logger.error(f"Failed to upload table image: {e}")
            raise StorageError(f"Failed to upload table image: {str(e)}")

    async def upload_generated_file(
        self,
        file_path: str,
        filename: str,
        upload_type: UploadType,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        index_run_id: Optional[UUID] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a generated file (markdown, etc.) to the generated folder."""
        try:
            # Create storage path based on upload type
            if upload_type == UploadType.EMAIL:
                storage_path = (
                    f"email-uploads/index-runs/{index_run_id}/generated/{filename}"
                )
            else:  # USER_PROJECT
                storage_path = f"users/{user_id}/projects/{project_id}/index-runs/{index_run_id}/generated/{filename}"

            # Upload file
            url = await self.upload_file(file_path, storage_path, content_type)

            # Return metadata
            return {
                "url": url,
                "storage_path": storage_path,
                "filename": filename,
                "upload_type": upload_type.value,
            }

        except Exception as e:
            logger.error(f"Failed to upload generated file: {e}")
            raise StorageError(f"Failed to upload generated file: {str(e)}")

    async def upload_original_pdf(
        self,
        file_path: str,
        filename: str,
        upload_type: UploadType,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        index_run_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Upload the original PDF file."""
        try:
            # Create storage path based on upload type
            if upload_type == UploadType.EMAIL:
                storage_path = (
                    f"email-uploads/index-runs/{index_run_id}/pdfs/{filename}"
                )
            else:  # USER_PROJECT
                storage_path = f"users/{user_id}/projects/{project_id}/index-runs/{index_run_id}/pdfs/{filename}"

            # Upload file
            url = await self.upload_file(file_path, storage_path, "application/pdf")

            # Return metadata
            return {
                "url": url,
                "storage_path": storage_path,
                "filename": filename,
                "upload_type": upload_type.value,
            }

        except Exception as e:
            logger.error(f"Failed to upload original PDF: {e}")
            raise StorageError(f"Failed to upload original PDF: {str(e)}")

    async def upload_temp_file(
        self,
        file_path: str,
        filename: str,
        step: str,
        upload_type: UploadType,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        index_run_id: Optional[UUID] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a temporary processing file."""
        try:
            # Create storage path based on upload type
            if upload_type == UploadType.EMAIL:
                storage_path = (
                    f"email-uploads/index-runs/{index_run_id}/temp/{step}/{filename}"
                )
            else:  # USER_PROJECT
                storage_path = f"users/{user_id}/projects/{project_id}/index-runs/{index_run_id}/temp/{step}/{filename}"

            # Upload file
            url = await self.upload_file(file_path, storage_path, content_type)

            # Return metadata
            return {
                "url": url,
                "storage_path": storage_path,
                "filename": filename,
                "step": step,
                "upload_type": upload_type.value,
            }

        except Exception as e:
            logger.error(f"Failed to upload temp file: {e}")
            raise StorageError(f"Failed to upload temp file: {str(e)}")

    async def create_storage_structure(
        self,
        upload_type: UploadType,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        index_run_id: Optional[UUID] = None,
    ) -> bool:
        """Create the storage folder structure for the upload type."""
        try:
            if upload_type == UploadType.EMAIL:
                # Create simplified email upload structure (no upload_id)
                base_path = f"email-uploads/index-runs/{index_run_id}"
                folders = [
                    f"{base_path}/pdfs",
                    f"{base_path}/generated",
                    f"{base_path}/generated/markdown",
                    f"{base_path}/generated/pages",
                    f"{base_path}/generated/assets",
                    f"{base_path}/generated/assets/images",
                    f"{base_path}/generated/assets/css",
                    f"{base_path}/generated/assets/js",
                    f"{base_path}/temp",
                    f"{base_path}/temp/partition",
                    f"{base_path}/temp/metadata",
                    f"{base_path}/temp/enrichment",
                    f"{base_path}/temp/chunking",
                    f"{base_path}/temp/embedding",
                ]
            else:  # USER_PROJECT
                # Create user project structure (unchanged)
                base_path = (
                    f"users/{user_id}/projects/{project_id}/index-runs/{index_run_id}"
                )
                folders = [
                    f"{base_path}/pdfs",
                    f"{base_path}/generated",
                    f"{base_path}/generated/markdown",
                    f"{base_path}/generated/pages",
                    f"{base_path}/generated/assets",
                    f"{base_path}/generated/assets/images",
                    f"{base_path}/generated/assets/css",
                    f"{base_path}/generated/assets/js",
                    f"{base_path}/temp",
                    f"{base_path}/temp/partition",
                    f"{base_path}/temp/metadata",
                    f"{base_path}/temp/enrichment",
                    f"{base_path}/temp/chunking",
                    f"{base_path}/temp/embedding",
                ]

            logger.info(f"Storage structure paths defined for {upload_type.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to create storage structure: {e}")
            return False

    def _get_content_type(self, file_path: str) -> str:
        """Get content type based on file extension."""
        ext = Path(file_path).suffix.lower()
        content_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".pdf": "application/pdf",
            ".html": "text/html",
            ".txt": "text/plain",
            ".md": "text/markdown",
        }
        return content_types.get(ext, "application/octet-stream")

    async def delete_file(self, storage_path: str) -> bool:
        """Delete a file from Supabase Storage."""
        try:
            result = self.supabase.storage.from_(self.bucket_name).remove(
                [storage_path]
            )
            logger.info(f"Deleted file from storage: {storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {storage_path}: {e}")
            return False

    async def delete_run_directory(self, run_id: UUID) -> bool:
        """Delete entire run directory and all its contents."""
        try:
            # List all files in the run directory
            run_path = str(run_id)
            files = await self.list_files(run_path)

            if not files:
                logger.info(f"No files found in run directory: {run_path}")
                return True

            # Extract file paths from the list
            file_paths = []
            for file_info in files:
                if isinstance(file_info, dict) and "name" in file_info:
                    file_paths.append(f"{run_path}/{file_info['name']}")
                elif isinstance(file_info, str):
                    file_paths.append(f"{run_path}/{file_info}")

            # Delete all files in the run directory
            if file_paths:
                result = self.supabase.storage.from_(self.bucket_name).remove(
                    file_paths
                )
                logger.info(
                    f"Deleted {len(file_paths)} files from run directory: {run_path}"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to delete run directory {run_id}: {e}")
            return False

    async def list_files(self, folder_path: str = "") -> list:
        """List files in a storage folder."""
        try:
            result = self.supabase.storage.from_(self.bucket_name).list(folder_path)
            return result
        except Exception as e:
            logger.error(f"Failed to list files in {folder_path}: {e}")
            return []

    async def get_run_storage_usage(self, run_id: UUID) -> Dict[str, Any]:
        """Get storage usage statistics for a specific run."""
        try:
            run_path = str(run_id)
            files = await self.list_files(run_path)

            total_files = 0
            total_size = 0

            for file_info in files:
                if isinstance(file_info, dict):
                    total_files += 1
                    total_size += file_info.get("metadata", {}).get("size", 0)

            return {
                "run_id": str(run_id),
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
            }

        except Exception as e:
            logger.error(f"Failed to get storage usage for run {run_id}: {e}")
            return {
                "run_id": str(run_id),
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "error": str(e),
            }
