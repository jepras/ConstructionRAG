"""Metadata collection step for wiki generation pipeline."""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from uuid import UUID

from ...shared.base_step import PipelineStep
from src.models import StepResult
from src.services.storage_service import StorageService
from src.config.database import get_supabase_admin_client

logger = logging.getLogger(__name__)


class MetadataCollectionStep(PipelineStep):
    """Step 1: Collect metadata about the project from the database."""

    def __init__(
        self,
        config: Dict[str, Any],
        storage_service: Optional[StorageService] = None,
        progress_tracker=None,
    ):
        super().__init__(config, progress_tracker)
        self.storage_service = storage_service or StorageService()
        self.supabase = get_supabase_admin_client()

    async def execute(self, input_data: Dict[str, Any]) -> StepResult:
        """Execute metadata collection step."""
        start_time = datetime.utcnow()

        try:
            index_run_id = input_data["index_run_id"]
            logger.info(
                f"Starting metadata collection for indexing run: {index_run_id}"
            )

            # Collect metadata
            metadata = await self._collect_metadata(index_run_id)

            # Create step result
            result = StepResult(
                step="metadata_collection",
                status="completed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                summary_stats={
                    "total_documents": metadata["total_documents"],
                    "total_chunks": metadata["total_chunks"],
                    "total_pages_analyzed": metadata["total_pages_analyzed"],
                    "images_processed": metadata["images_processed"],
                    "tables_processed": metadata["tables_processed"],
                },
                sample_outputs={
                    "document_filenames": metadata["document_filenames"][:3],
                    "section_headers": list(
                        metadata["section_headers_distribution"].keys()
                    )[:5],
                },
                data=metadata,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

            logger.info(
                f"Metadata collection completed: {metadata['total_documents']} documents, {metadata['total_chunks']} chunks"
            )
            return result

        except Exception as e:
            logger.error(f"Metadata collection failed: {e}")
            return StepResult(
                step="metadata_collection",
                status="failed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

    async def validate_prerequisites_async(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data meets step requirements."""
        required_fields = ["index_run_id"]
        return all(field in input_data for field in required_fields)

    def estimate_duration(self, input_data: Dict[str, Any]) -> int:
        """Estimate step duration in seconds."""
        return 30  # Metadata collection is typically fast

    async def _collect_metadata(self, index_run_id: str) -> Dict[str, Any]:
        """Collect comprehensive metadata about the project."""

        # Get indexing run with step results
        indexing_run_response = (
            self.supabase.table("indexing_runs")
            .select("*")
            .eq("id", index_run_id)
            .execute()
        )

        if not indexing_run_response.data:
            raise ValueError(f"No indexing run found with ID: {index_run_id}")

        indexing_run = indexing_run_response.data[0]
        step_results = indexing_run.get("step_results", {})

        # Get documents
        documents_response = (
            self.supabase.table("indexing_run_documents")
            .select("document_id, documents(*)")
            .eq("indexing_run_id", index_run_id)
            .execute()
        )

        documents = [
            item["documents"] for item in documents_response.data if item["documents"]
        ]
        document_ids = [doc["id"] for doc in documents]

        # Get chunks with embeddings
        chunks_response = (
            self.supabase.table("document_chunks")
            .select("id, document_id, content, metadata, embedding_1024")
            .in_("document_id", document_ids)
            .execute()
        )

        # Process chunks
        chunks = []
        chunks_with_embeddings = []
        section_headers_distribution = {}
        total_pages_analyzed = 0
        images_processed = 0
        tables_processed = 0

        for chunk in chunks_response.data:
            # Store chunk without embeddings for output
            chunk_without_embedding = {
                k: v for k, v in chunk.items() if k != "embedding_1024"
            }
            chunks.append(chunk_without_embedding)

            # Store chunk with embeddings for processing
            chunks_with_embeddings.append(chunk)

            # Extract metadata
            metadata = chunk.get("metadata", {})

            # Count pages
            page_number = metadata.get("page_number")
            if page_number:
                total_pages_analyzed = max(total_pages_analyzed, page_number)

            # Count images and tables
            if metadata.get("image_type"):
                images_processed += 1
            if metadata.get("table_id"):
                tables_processed += 1

            # Extract section headers
            section_title = metadata.get("section_title")
            if section_title:
                section_headers_distribution[section_title] = (
                    section_headers_distribution.get(section_title, 0) + 1
                )

        # Extract processing statistics from step results
        processing_stats = self._extract_processing_stats(step_results)

        # Compile metadata
        metadata = {
            "index_run_id": index_run_id,
            "total_documents": len(documents),
            "total_chunks": len(chunks),
            "total_pages_analyzed": total_pages_analyzed,
            "images_processed": images_processed,
            "tables_processed": tables_processed,
            "document_filenames": [doc.get("filename", "Unknown") for doc in documents],
            "document_ids": document_ids,
            "section_headers_distribution": section_headers_distribution,
            "processing_stats": processing_stats,
            "chunks": chunks,  # Without embeddings
            "chunks_with_embeddings": chunks_with_embeddings,  # With embeddings for processing
            "upload_type": indexing_run.get("upload_type", "user_project"),
            "user_id": indexing_run.get("user_id"),
            "project_id": indexing_run.get("project_id"),
        }

        return metadata

    def _extract_processing_stats(self, step_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract processing statistics from step results."""
        stats = {
            "partition": {},
            "metadata": {},
            "enrichment": {},
            "chunking": {},
            "embedding": {},
        }

        for step_name, step_result in step_results.items():
            if isinstance(step_result, dict):
                summary_stats = step_result.get("summary_stats", {})
                stats[step_name] = summary_stats

        return stats
