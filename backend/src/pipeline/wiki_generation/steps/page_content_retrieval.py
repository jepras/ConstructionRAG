"""Page content retrieval step for wiki generation pipeline."""

import logging
from datetime import datetime
from typing import Any

from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings
from src.models import StepResult
from src.services.config_service import ConfigService
from src.services.storage_service import StorageService
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError

from ...shared.base_step import PipelineStep
from ...shared import SharedRetrievalConfig, RetrievalCore

logger = logging.getLogger(__name__)


class PageContentRetrievalStep(PipelineStep):
    """Step 4: Retrieve content for each wiki page using vector search."""

    def __init__(
        self,
        config: dict[str, Any],
        storage_service: StorageService | None = None,
        progress_tracker=None,
        db_client=None,
    ):
        super().__init__(config, progress_tracker)
        self.storage_service = storage_service or StorageService()
        # Allow DI of db client; default to admin for pipeline safety
        self.supabase = db_client or get_supabase_admin_client()
        
        # Load wiki retrieval config from SoT
        wiki_cfg = ConfigService().get_effective_config("wiki")
        retrieval_cfg = wiki_cfg.get("retrieval", {})
        
        # Configure retrieval settings
        self.max_chunks_per_query = retrieval_cfg.get("top_k", 10)
        self.max_chunks_per_page = retrieval_cfg.get("max_chunks_per_page", 20)
        self.similarity_threshold = retrieval_cfg.get("similarity_threshold", 0.15)
        
        # Create shared retrieval configuration
        shared_config = SharedRetrievalConfig(
            embedding_model=retrieval_cfg.get("embedding_model", "voyage-multilingual-2"),
            dimensions=retrieval_cfg.get("dimensions", 1024),
            top_k=self.max_chunks_per_query,
            similarity_thresholds={"minimum": self.similarity_threshold},
            danish_thresholds={"minimum": self.similarity_threshold}
        )
        
        # Initialize shared retrieval core
        self.retrieval_core = RetrievalCore(
            config=shared_config,
            db_client=self.supabase
        )
        
        logger.info(
            f"[Wiki:Retrieval] Using shared retrieval with model='{shared_config.embedding_model}', "
            f"top_k={self.max_chunks_per_query}, threshold={self.similarity_threshold}"
        )

    async def execute(self, input_data: dict[str, Any]) -> StepResult:
        """Execute page content retrieval step."""
        start_time = datetime.utcnow()

        try:
            metadata = input_data["metadata"]
            wiki_structure = input_data["wiki_structure"]
            logger.info(f"Starting page content retrieval for {len(wiki_structure['pages'])} pages")

            # Retrieve content for each page
            page_contents = {}
            total_chunks_retrieved = 0
            
            logger.info(
                f"[Wiki:Retrieval] Starting retrieval with threshold={self.similarity_threshold}, "
                f"max_chunks_per_query={self.max_chunks_per_query}, max_chunks_per_page={self.max_chunks_per_page}"
            )

            for page in wiki_structure["pages"]:
                page_id = page["id"]
                page_title = page["title"]
                queries = page.get("queries", [])

                logger.info(f"Retrieving content for page: {page_title}")
                print(
                    f"🔍 [DEBUG] PageContentRetrievalStep.execute() - Retrieving page '{page_title}' with {len(queries)} queries"
                )

                # Retrieve content for this page
                page_content = await self._retrieve_page_content(queries, metadata)
                page_contents[page_id] = page_content
                total_chunks_retrieved += len(page_content.get("retrieved_chunks", []))
                logger.info(
                    f"[Wiki:Retrieval] Page '{page_title}' retrieved {len(page_content.get('retrieved_chunks', []))} chunks from {len(queries)} queries"
                )
                print(
                    f"🔍 [DEBUG] PageContentRetrievalStep.execute() - Page '{page_title}' retrieved {len(page_content.get('retrieved_chunks', []))} chunks"
                )

            # Create step result
            result = StepResult(
                step="page_content_retrieval",
                status="completed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                summary_stats={
                    "total_pages": len(wiki_structure["pages"]),
                    "total_chunks_retrieved": total_chunks_retrieved,
                    "average_chunks_per_page": (
                        total_chunks_retrieved // len(wiki_structure["pages"]) if wiki_structure["pages"] else 0
                    ),
                },
                sample_outputs={
                    "page_examples": [page["title"] for page in wiki_structure["pages"][:3]],
                    "chunks_per_page": {
                        page_id: len(content.get("retrieved_chunks", []))
                        for page_id, content in list(page_contents.items())[:3]
                    },
                },
                data=page_contents,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

            logger.info(f"Page content retrieval completed: {total_chunks_retrieved} chunks retrieved")
            print(
                f"✅ [DEBUG] PageContentRetrievalStep.execute() - Completed retrieval, total_chunks_retrieved={total_chunks_retrieved}"
            )
            return result

        except Exception as e:
            logger.error(f"Page content retrieval failed: {e}")
            raise AppError(
                "Page content retrieval failed",
                error_code=ErrorCode.DATABASE_ERROR,
                details={"reason": str(e)},
            ) from e

    async def validate_prerequisites_async(self, input_data: dict[str, Any]) -> bool:
        """Validate that input data meets step requirements."""
        required_fields = ["metadata", "wiki_structure"]
        if not all(field in input_data for field in required_fields):
            return False

        wiki_structure = input_data["wiki_structure"]
        if "pages" not in wiki_structure or not isinstance(wiki_structure["pages"], list):
            return False

        return True

    def estimate_duration(self, input_data: dict[str, Any]) -> int:
        """Estimate step duration in seconds."""
        wiki_structure = input_data.get("wiki_structure", {})
        num_pages = len(wiki_structure.get("pages", []))
        return num_pages * 30  # 30 seconds per page

    async def _retrieve_page_content(self, queries: list[str], metadata: dict[str, Any]) -> dict[str, Any]:
        """Retrieve content for a specific page using its queries."""
        all_retrieved_chunks = []
        source_documents = {}
        indexing_run_id = metadata.get("indexing_run_id")

        for query in queries:
            logger.info(f"🔍 [Wiki:Retrieval] Processing query: '{query[:80]}...'")

            # Generate embedding using shared service
            query_embedding = await self.retrieval_core.generate_query_embedding(query)

            # Search using shared retrieval core with HNSW optimization
            similar_chunks = await self.retrieval_core.search_with_fallback(
                query_embedding,
                indexing_run_id=indexing_run_id,
                language="danish"
            )

            logger.info(f"📊 [Wiki:Retrieval] Query retrieved {len(similar_chunks)} chunks")
            
            # Log details about top chunks for debugging
            if similar_chunks:
                for i, chunk in enumerate(similar_chunks[:3]):
                    content_preview = chunk["content"][:200].replace("\n", " ")
                    logger.info(
                        f"   Top {i+1} (sim={chunk.get('similarity_score', 0):.3f}): "
                        f"{content_preview}..."
                    )
            else:
                logger.warning(f"   ⚠️ No results for query: '{query}'")

            # Add query information to chunks and filter metadata to essentials
            for chunk in similar_chunks:
                chunk["query"] = query
                # Filter metadata to only essential fields for wiki generation
                chunk["metadata"] = self._filter_essential_metadata(chunk.get("metadata", {}))
                all_retrieved_chunks.append(chunk)

                # Track source documents
                document_id = chunk.get("document_id")
                if document_id:
                    if document_id not in source_documents:
                        source_documents[document_id] = {
                            "document_id": document_id,
                            "filename": chunk.get("metadata", {}).get("source_filename", chunk.get("source_filename", "Unknown")),
                            "chunk_count": 0,
                        }
                    source_documents[document_id]["chunk_count"] += 1

        # Remove duplicates and sort by similarity score
        unique_chunks = self._deduplicate_chunks(all_retrieved_chunks)
        unique_chunks.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)

        # Limit to configured max chunks per page
        top_chunks = unique_chunks[: self.max_chunks_per_page]
        
        logger.info(
            f"✅ [Wiki:Retrieval] Page aggregation complete: "
            f"{len(top_chunks)} unique chunks from {len(queries)} queries"
        )

        return {
            "retrieved_chunks": top_chunks,
            "source_documents": source_documents,
            "total_queries": len(queries),
            "total_chunks_retrieved": len(top_chunks),
        }

    # Note: The following methods have been removed as they are now handled by RetrievalCore:
    # - _generate_query_embedding (replaced by retrieval_core.generate_query_embedding)
    # - _find_similar_chunks (replaced by retrieval_core.search_with_fallback)
    # - _cosine_similarity (replaced by shared similarity service)

    def _deduplicate_chunks(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate chunks based on content similarity."""
        unique_chunks = []
        seen_contents = set()

        for chunk in chunks:
            content = chunk.get("content", "")
            content_hash = hash(content[:100])  # Use first 100 chars as hash

            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_chunks.append(chunk)

        return unique_chunks

    def _filter_essential_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Filter metadata to only essential fields for wiki generation.
        
        Essential fields:
        - page_number: For source citations
        - source_filename: For document identification 
        - bbox: For PDF highlighting
        - document_id: For document grouping
        """
        essential_fields = ["page_number", "source_filename", "bbox", "document_id"]
        return {
            field: metadata.get(field)
            for field in essential_fields
            if metadata.get(field) is not None
        }
