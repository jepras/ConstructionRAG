"""Storage service for handling Supabase Storage operations."""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import UUID
import logging

from config.database import get_supabase_admin_client
from utils.exceptions import StorageError

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file storage operations in Supabase Storage."""

    def __init__(self):
        self.supabase = get_supabase_admin_client()
        self.bucket_name = "pipeline-assets"  # Main bucket for pipeline files

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
                        ],
                    },
                )
                logger.info(f"Created storage bucket '{self.bucket_name}'")
                return True
            except Exception as e:
                logger.error(f"Failed to create storage bucket: {e}")
                raise StorageError(f"Failed to create storage bucket: {str(e)}")

    async def upload_file(
        self, file_path: str, storage_path: str, content_type: Optional[str] = None
    ) -> str:
        """Upload a file to Supabase Storage and return the public URL."""
        try:
            # Ensure bucket exists
            await self.ensure_bucket_exists()

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

            # Get public URL
            url = self.supabase.storage.from_(self.bucket_name).get_public_url(
                storage_path
            )

            logger.info(f"Uploaded file to storage: {storage_path} -> {url}")
            return url

        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {e}")
            raise StorageError(f"Failed to upload file: {str(e)}")

    async def upload_extracted_page_image(
        self, image_path: str, document_id: UUID, page_num: int, complexity: str
    ) -> Dict[str, Any]:
        """Upload an extracted page image and return metadata with URL."""
        try:
            # Create storage path
            filename = Path(image_path).name
            storage_path = f"extracted-pages/{document_id}/{filename}"

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
            }

        except Exception as e:
            logger.error(f"Failed to upload extracted page image: {e}")
            raise StorageError(f"Failed to upload extracted page image: {str(e)}")

    async def upload_table_image(
        self, image_path: str, document_id: UUID, table_id: str
    ) -> Dict[str, Any]:
        """Upload a table image and return metadata with URL."""
        try:
            # Create storage path
            filename = Path(image_path).name
            storage_path = f"table-images/{document_id}/{filename}"

            # Upload file
            url = await self.upload_file(image_path, storage_path, "image/png")

            # Return metadata
            return {
                "url": url,
                "storage_path": storage_path,
                "filename": filename,
                "table_id": table_id,
                "document_id": str(document_id),
            }

        except Exception as e:
            logger.error(f"Failed to upload table image: {e}")
            raise StorageError(f"Failed to upload table image: {str(e)}")

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

    async def list_files(self, folder_path: str = "") -> list:
        """List files in a storage folder."""
        try:
            result = self.supabase.storage.from_(self.bucket_name).list(folder_path)
            return result
        except Exception as e:
            logger.error(f"Failed to list files in {folder_path}: {e}")
            return []
