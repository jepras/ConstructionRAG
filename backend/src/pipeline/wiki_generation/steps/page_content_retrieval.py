"""Page content retrieval step for wiki generation pipeline."""

import logging
from datetime import datetime
from typing import Any

from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings
from src.models import StepResult
from src.pipeline.indexing.steps.embedding import VoyageEmbeddingClient
from src.services.storage_service import StorageService
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError

from ...shared.base_step import PipelineStep

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
        self.similarity_threshold = config.get("similarity_threshold", 0.3)
        self.max_chunks_per_query = config.get("max_chunks_per_query", 10)

        # Initialize Voyage for query embeddings (match document embeddings)
        settings = get_settings()
        # Force same model/dims as query pipeline to match embedding_1024
        self.query_embedding_model = "voyage-multilingual-2"
        self.query_embedding_dims_expected = 1024
        try:
            self.voyage_client = VoyageEmbeddingClient(
                api_key=settings.voyage_api_key,
                model=self.query_embedding_model,
            )
            logger.info(
                f"[Wiki:Retrieval] Using query embedding model='{self.query_embedding_model}', expected_dims={self.query_embedding_dims_expected}"
            )
        except Exception as e:
            logger.warning(f"[Wiki:Retrieval] Failed to initialize VoyageEmbeddingClient: {e}")
            self.voyage_client = None

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

            # Diagnostics: detect sample chunk embedding length
            chunks_with_embeddings = metadata.get("chunks_with_embeddings", [])
            sample_len = 0
            for ch in chunks_with_embeddings:
                emb = ch.get("embedding_1024")
                if emb is not None:
                    if isinstance(emb, str):
                        try:
                            import ast

                            emb = ast.literal_eval(emb)
                        except Exception:
                            emb = None
                    if isinstance(emb, list):
                        sample_len = len(emb)
                        break
            if sample_len:
                logger.info(
                    f"[Wiki:Retrieval] Sample chunk embedding length detected: {sample_len}; similarity_threshold={self.similarity_threshold}"
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

        chunks_with_embeddings = metadata["chunks_with_embeddings"]

        for query in queries:
            logger.debug(f"Processing query: {query}")

            # Generate embedding for query
            query_embedding = await self._generate_query_embedding(query)

            # Find similar chunks
            similar_chunks = await self._find_similar_chunks(query_embedding, chunks_with_embeddings)

            logger.info(f"[Wiki:Retrieval] Query '{query[:40]}...' retrieved {len(similar_chunks)} chunks")

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
                            "filename": chunk.get("metadata", {}).get("source_filename", "Unknown"),
                            "chunk_count": 0,
                        }
                    source_documents[document_id]["chunk_count"] += 1

        # Remove duplicates and sort by similarity score
        unique_chunks = self._deduplicate_chunks(all_retrieved_chunks)
        unique_chunks.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)

        # Limit to top chunks
        top_chunks = unique_chunks[: self.max_chunks_per_query * 2]  # Allow more for deduplication

        return {
            "retrieved_chunks": top_chunks,
            "source_documents": source_documents,
            "total_queries": len(queries),
            "total_chunks_retrieved": len(top_chunks),
        }

    async def _generate_query_embedding(self, query_text: str) -> list[float]:
        if not self.voyage_client:
            raise ValueError("Voyage client not initialized for query embeddings")
        embeddings = await self.voyage_client.get_embeddings([query_text])
        vector = embeddings[0] if embeddings else []
        if len(vector) != self.query_embedding_dims_expected:
            logger.warning(
                f"[Wiki:Retrieval] Query embedding dims mismatch: got {len(vector)}, expected {self.query_embedding_dims_expected}"
            )
        logger.info(f"[Wiki:Retrieval] Generated query embedding len={len(vector)} for text='{query_text[:50]}...'")
        return vector

    async def _find_similar_chunks(
        self, query_embedding: list[float], chunks_with_embeddings: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
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
                except Exception:
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

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

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
