"""Metadata collection step for wiki generation pipeline."""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from uuid import UUID

from ...shared.base_step import PipelineStep
from src.models import StepResult
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError
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
            raise AppError(
                "Metadata collection failed",
                error_code=ErrorCode.DATABASE_ERROR,
                details={"reason": str(e)},
            ) from e

    async def validate_prerequisites_async(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data meets step requirements."""
        required_fields = ["index_run_id"]
        return all(field in input_data for field in required_fields)

    def estimate_duration(self, input_data: Dict[str, Any]) -> int:
        """Estimate step duration in seconds."""
        return 30  # Metadata collection is typically fast

    async def _collect_metadata(self, index_run_id: str) -> Dict[str, Any]:
        """Collect comprehensive metadata about the project - matching original implementation."""
        print(f"Trin 1: Henter projektmetadata for indexing run: {index_run_id}")

        # Get indexing run with step results
        indexing_run_response = (
            self.supabase.table("indexing_runs")
            .select("*")
            .eq("id", index_run_id)
            .execute()
        )

        if not indexing_run_response.data:
            raise ValueError(f"Ingen indexing run fundet med ID: {index_run_id}")

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

        # Get chunks with embeddings (but don't store embeddings in output)
        chunks_response = (
            self.supabase.table("document_chunks")
            .select("id, document_id, content, metadata, embedding_1024")
            .in_("document_id", document_ids)
            .execute()
        )

        # Store chunks without embeddings for output, but keep embeddings for processing
        chunks = []
        chunks_with_embeddings = []
        for chunk_data in chunks_response.data:
            # Clean chunk for output (no embeddings)
            # Extract page_number from metadata if available
            metadata = chunk_data.get("metadata", {})
            page_number = metadata.get("page_number", "N/A")

            clean_chunk = {
                "id": chunk_data.get("id"),
                "document_id": chunk_data.get("document_id"),
                "content": chunk_data.get("content", ""),
                "page_number": page_number,
                "metadata": metadata,
            }
            chunks.append(clean_chunk)

            # Keep original with embeddings for processing
            chunks_with_embeddings.append(chunk_data)

        # Extract metadata from step results
        metadata = {
            "indexing_run_id": index_run_id,
            "total_documents": len(documents),
            "total_chunks": len(chunks),
            "documents": documents,
            "chunks": chunks,  # Clean chunks without embeddings for output
            "chunks_with_embeddings": chunks_with_embeddings,  # For processing only
        }

        # Extract pages analyzed (sum from all documents)
        total_pages = sum(
            doc.get("page_count", 0) for doc in documents if doc.get("page_count")
        )
        metadata["total_pages_analyzed"] = total_pages

        # Extract from chunking step
        chunking_data = step_results.get("chunking", {}).get("data", {})
        if chunking_data:
            summary_stats = chunking_data.get("summary_stats", {})
            metadata["section_headers_distribution"] = summary_stats.get(
                "section_headers_distribution", {}
            )
        else:
            metadata["section_headers_distribution"] = {}

        # Extract from enrichment step
        enrichment_data = step_results.get("enrichment", {}).get("data", {})
        if enrichment_data:
            enrich_summary = enrichment_data.get("summary_stats", {})
            metadata["images_processed"] = enrich_summary.get("images_captioned", 0)
            metadata["tables_processed"] = enrich_summary.get("tables_captioned", 0)
        else:
            metadata["images_processed"] = 0
            metadata["tables_processed"] = 0

        # Extract document filenames - exactly matching original
        metadata["document_filenames"] = [
            doc.get("filename", f"document_{doc.get('id', 'unknown')[:8]}")
            for doc in documents
        ]

        # Additional metadata for pipeline compatibility
        metadata["document_ids"] = document_ids
        metadata["upload_type"] = indexing_run.get("upload_type", "user_project")
        metadata["user_id"] = indexing_run.get("user_id")
        metadata["project_id"] = indexing_run.get("project_id")

        print(f"Projektmetadata hentet:")
        print(f"- Dokumenter: {metadata['total_documents']}")
        print(f"- Sider analyseret: {metadata['total_pages_analyzed']}")
        print(f"- Chunks oprettet: {metadata['total_chunks']}")
        print(f"- Billeder behandlet: {metadata['images_processed']}")
        print(f"- Tabeller behandlet: {metadata['tables_processed']}")
        print(f"- Sektioner fundet: {len(metadata['section_headers_distribution'])}")

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
