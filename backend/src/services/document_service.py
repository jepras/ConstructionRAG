from __future__ import annotations

import os
import tempfile
import time
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from src.services.db_service import DbService
from src.services.storage_service import StorageService
from src.utils.exceptions import DatabaseError, StorageError
from src.utils.filename_utils import sanitize_filename
from src.utils.logging import get_logger
from supabase import Client


class DocumentService:
    """Minimal document operations built on CRUD + Storage for Phase 4.

    Keeps behavior equivalent to existing endpoints while centralizing logic.
    """

    def __init__(self, db: Client, storage: StorageService | None = None) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.db = db
        self.crud = DbService(client=db)
        self.storage = storage or StorageService()

    async def create_email_document(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        index_run_id: str,
        email: str,
    ) -> dict[str, Any]:
        """Create a document for email upload: upload file and insert DB rows.

        Returns a dict with document_id and storage_url.
        """
        document_id = str(uuid4())
        # Sanitize filename for storage compatibility
        sanitized_filename = sanitize_filename(filename)
        self.logger.info(f"Sanitized filename: '{filename}' -> '{sanitized_filename}'")
        
        # Create temp file for upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            temp_path = tmp.name
        try:
            storage_path = f"email-uploads/index-runs/{index_run_id}/pdfs/{sanitized_filename}"
            storage_url = await self.storage.upload_file(file_path=temp_path, storage_path=storage_path)
        except StorageError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.logger.error("storage upload failed", error=str(exc))
            raise StorageError(f"Failed to upload file: {exc}") from exc
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        # Insert document row
        doc_row = {
            "id": document_id,
            "user_id": None,
            "filename": sanitized_filename,
            "file_size": len(file_bytes),
            "file_path": storage_url,
            "status": "processing",
            "upload_type": "email",
            "index_run_id": index_run_id,
            "metadata": {"email": email},
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "access_level": "public",
        }
        try:
            self.crud.create("documents", doc_row)
        except DatabaseError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.logger.error("create document failed", error=str(exc))
            raise DatabaseError(f"Failed to store document record for {sanitized_filename}") from exc

        # Create junction link
        try:
            self.db.table("indexing_run_documents").insert(
                {"indexing_run_id": index_run_id, "document_id": document_id}
            ).execute()
        except Exception as exc:  # noqa: BLE001
            # Non-fatal; log only to match current behavior
            self.logger.warning("failed to link document to indexing run", document_id=document_id, error=str(exc))

        return {"document_id": document_id, "storage_url": storage_url}

    async def create_project_document(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        project_id: UUID,
        user_id: str,
        index_run_id: str,
        file_size: int | None,
    ) -> dict[str, Any]:
        """Create a document for a user project: insert row, upload, and update path."""
        document_id = str(uuid4())
        
        # Sanitize filename for storage compatibility
        sanitized_filename = sanitize_filename(filename)
        self.logger.info(f"Sanitized filename: '{filename}' -> '{sanitized_filename}'")

        # Insert initial row
        doc_row = {
            "id": document_id,
            "user_id": user_id,
            "filename": sanitized_filename,
            "file_size": file_size,
            "status": "pending",
            "upload_type": "user_project",
            "project_id": str(project_id),
            "index_run_id": index_run_id,
            "access_level": "private",
        }
        try:
            self.crud.create("documents", doc_row)
        except DatabaseError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.logger.error("create document failed", error=str(exc))
            raise DatabaseError("Failed to create document record") from exc

        # Create temp file for upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            temp_path = tmp.name
        try:
            storage_path = f"users/{user_id}/projects/{project_id}/index-runs/{index_run_id}/pdfs/{sanitized_filename}"
            storage_url = await self.storage.upload_file(file_path=temp_path, storage_path=storage_path)
        except StorageError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.logger.error("storage upload failed", error=str(exc))
            raise StorageError(f"Failed to upload file: {exc}") from exc

        # Update row with file_path
        try:
            self.db.table("documents").update({"file_path": storage_url}).eq("id", document_id).execute()
        except Exception as exc:  # noqa: BLE001
            self.logger.error("update file_path failed", error=str(exc))
            raise DatabaseError("Failed to update document with file path") from exc

        # Do not delete temp file here; caller schedules background work then cleans up
        return {
            "document_id": document_id,
            "storage_url": storage_url,
            "index_run_id": index_run_id,
            "temp_path": temp_path,
        }

    async def create_email_documents_batch(
        self,
        *,
        file_data: list[tuple[bytes, str]],  # List of (file_bytes, filename) tuples
        index_run_id: str,
        email: str,
    ) -> list[dict[str, Any]]:
        """Create multiple documents for email upload in parallel.
        
        Args:
            file_data: List of (file_bytes, filename) tuples
            index_run_id: The indexing run ID
            email: User's email
            
        Returns:
            List of dicts with document_id and storage_url
        """
        import asyncio
        
        batch_start = time.time()
        self.logger.info(f"Starting batch creation of {len(file_data)} email documents")
        
        # Create tasks for parallel processing
        tasks = [
            self._create_single_email_document(file_bytes, filename, index_run_id, email)
            for file_bytes, filename in file_data
        ]
        
        # Run all document creations in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle any errors
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                filename = file_data[i][1]
                self.logger.error(f"Failed to create document for {filename}: {result}")
                # Re-raise the first error to maintain existing behavior
                if isinstance(result, (StorageError, DatabaseError)):
                    raise result
                else:
                    raise DatabaseError(f"Failed to create document for {filename}") from result
            else:
                successful_results.append(result)
        
        batch_time = time.time() - batch_start
        self.logger.info(f"Batch document creation completed in {batch_time:.2f}s for {len(file_data)} files")
        
        return successful_results
    
    async def _create_single_email_document(
        self,
        file_bytes: bytes,
        filename: str,
        index_run_id: str,
        email: str,
    ) -> dict[str, Any]:
        """Helper method to create a single email document (for parallel processing)."""
        document_id = str(uuid4())
        # Sanitize filename for storage compatibility
        sanitized_filename = sanitize_filename(filename)
        self.logger.debug(f"Creating document: '{filename}' -> '{sanitized_filename}' (ID: {document_id})")
        
        # Create temp file for upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            temp_path = tmp.name
        try:
            storage_path = f"email-uploads/index-runs/{index_run_id}/pdfs/{sanitized_filename}"
            storage_url = await self.storage.upload_file(file_path=temp_path, storage_path=storage_path)
        except StorageError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.logger.error("storage upload failed", error=str(exc))
            raise StorageError(f"Failed to upload file: {exc}") from exc
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        # Insert document row
        doc_row = {
            "id": document_id,
            "user_id": None,
            "filename": sanitized_filename,
            "file_size": len(file_bytes),
            "file_path": storage_url,
            "status": "processing",
            "upload_type": "email",
            "index_run_id": index_run_id,
            "metadata": {"email": email},
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "access_level": "public",
        }
        try:
            self.crud.create("documents", doc_row)
        except DatabaseError:
            raise
        except Exception as exc:  # noqa: BLE001
            self.logger.error("create document failed", error=str(exc))
            raise DatabaseError(f"Failed to store document record for {sanitized_filename}") from exc

        # Create junction link
        try:
            self.db.table("indexing_run_documents").insert(
                {"indexing_run_id": index_run_id, "document_id": document_id}
            ).execute()
        except Exception as exc:  # noqa: BLE001
            # Non-fatal; log only to match current behavior
            self.logger.warning("failed to link document to indexing run", document_id=document_id, error=str(exc))

        return {"document_id": document_id, "storage_url": storage_url}
