"""Page content retrieval step for wiki generation pipeline."""

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


class PageContentRetrievalStep(PipelineStep):
    """Step 4: Retrieve content for each wiki page using vector search."""

    def __init__(
        self,
        config: Dict[str, Any],
        storage_service: Optional[StorageService] = None,
        progress_tracker=None,
    ):
        super().__init__(config, progress_tracker)
        self.storage_service = storage_service or StorageService()
        self.supabase = get_supabase_admin_client()
        self.similarity_threshold = config.get("similarity_threshold", 0.3)
        self.max_chunks_per_query = config.get("max_chunks_per_query", 10)

    async def execute(self, input_data: Dict[str, Any]) -> StepResult:
        """Execute page content retrieval step."""
        start_time = datetime.utcnow()

        try:
            metadata = input_data["metadata"]
            wiki_structure = input_data["wiki_structure"]
            logger.info(
                f"Starting page content retrieval for {len(wiki_structure['pages'])} pages"
            )

            # Retrieve content for each page
            page_contents = {}
            total_chunks_retrieved = 0

            for page in wiki_structure["pages"]:
                page_id = page["id"]
                page_title = page["title"]
                queries = page.get("queries", [])

                logger.info(f"Retrieving content for page: {page_title}")

                # Retrieve content for this page
                page_content = await self._retrieve_page_content(queries, metadata)
                page_contents[page_id] = page_content
                total_chunks_retrieved += len(page_content.get("retrieved_chunks", []))

            # Create step result
            result = StepResult(
                step="page_content_retrieval",
                status="completed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                summary_stats={
                    "total_pages": len(wiki_structure["pages"]),
                    "total_chunks_retrieved": total_chunks_retrieved,
                    "average_chunks_per_page": (
                        total_chunks_retrieved // len(wiki_structure["pages"])
                        if wiki_structure["pages"]
                        else 0
                    ),
                },
                sample_outputs={
                    "page_examples": [
                        page["title"] for page in wiki_structure["pages"][:3]
                    ],
                    "chunks_per_page": {
                        page_id: len(content.get("retrieved_chunks", []))
                        for page_id, content in list(page_contents.items())[:3]
                    },
                },
                data=page_contents,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

            logger.info(
                f"Page content retrieval completed: {total_chunks_retrieved} chunks retrieved"
            )
            return result

        except Exception as e:
            logger.error(f"Page content retrieval failed: {e}")
            return StepResult(
                step="page_content_retrieval",
                status="failed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

    async def validate_prerequisites_async(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data meets step requirements."""
        required_fields = ["metadata", "wiki_structure"]
        if not all(field in input_data for field in required_fields):
            return False

        wiki_structure = input_data["wiki_structure"]
        if "pages" not in wiki_structure or not isinstance(
            wiki_structure["pages"], list
        ):
            return False

        return True

    def estimate_duration(self, input_data: Dict[str, Any]) -> int:
        """Estimate step duration in seconds."""
        wiki_structure = input_data.get("wiki_structure", {})
        num_pages = len(wiki_structure.get("pages", []))
        return num_pages * 30  # 30 seconds per page

    async def _retrieve_page_content(
        self, queries: List[str], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Retrieve content for a specific page using its queries."""
        all_retrieved_chunks = []
        source_documents = {}

        chunks_with_embeddings = metadata["chunks_with_embeddings"]

        for query in queries:
            logger.debug(f"Processing query: {query}")

            # Generate embedding for query
            query_embedding = await self._generate_query_embedding(query)

            # Find similar chunks
            similar_chunks = await self._find_similar_chunks(
                query_embedding, chunks_with_embeddings
            )

            # Add query information to chunks
            for chunk in similar_chunks:
                chunk["query"] = query
                all_retrieved_chunks.append(chunk)

                # Track source documents
                document_id = chunk.get("document_id")
                if document_id:
                    if document_id not in source_documents:
                        source_documents[document_id] = {
                            "document_id": document_id,
                            "filename": chunk.get("metadata", {}).get(
                                "source_filename", "Unknown"
                            ),
                            "chunk_count": 0,
                        }
                    source_documents[document_id]["chunk_count"] += 1

        # Remove duplicates and sort by similarity score
        unique_chunks = self._deduplicate_chunks(all_retrieved_chunks)
        unique_chunks.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)

        # Limit to top chunks
        top_chunks = unique_chunks[
            : self.max_chunks_per_query * 2
        ]  # Allow more for deduplication

        return {
            "retrieved_chunks": top_chunks,
            "source_documents": source_documents,
            "total_queries": len(queries),
            "total_chunks_retrieved": len(top_chunks),
        }

    async def _generate_query_embedding(self, query_text: str) -> List[float]:
        """Generate embedding for query text."""
        # This is a simplified implementation
        # In production, you'd use Voyage AI or similar service
        import hashlib
        import random

        # Create a deterministic "embedding" based on query text
        # This is just for demonstration - replace with actual embedding service
        hash_obj = hashlib.md5(query_text.encode())
        hash_hex = hash_obj.hexdigest()

        # Convert hash to list of floats (1024 dimensions)
        random.seed(int(hash_hex[:8], 16))
        embedding = [random.uniform(-1, 1) for _ in range(1024)]

        return embedding

    async def _find_similar_chunks(
        self, query_embedding: List[float], chunks_with_embeddings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find similar chunks using cosine similarity."""
        similar_chunks = []

        for chunk in chunks_with_embeddings:
            chunk_embedding = chunk.get("embedding_1024")
            if not chunk_embedding:
                continue

            # Parse embedding if it's a string
            if isinstance(chunk_embedding, str):
                try:
                    import ast

                    chunk_embedding = ast.literal_eval(chunk_embedding)
                except:
                    continue

            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_embedding, chunk_embedding)

            if similarity >= self.similarity_threshold:
                chunk_with_similarity = {
                    **chunk,
                    "similarity_score": similarity,
                }
                similar_chunks.append(chunk_with_similarity)

        # Sort by similarity score and limit results
        similar_chunks.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar_chunks[: self.max_chunks_per_query]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
