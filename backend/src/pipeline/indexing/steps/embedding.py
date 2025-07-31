"""Production embedding step for document processing pipeline."""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID
import logging
import httpx
from supabase import Client

from ...shared.base_step import PipelineStep
from models import StepResult
from ...shared.models import PipelineError

logger = logging.getLogger(__name__)


class VoyageEmbeddingClient:
    """Client for Voyage AI embedding API"""

    def __init__(self, api_key: str, model: str = "voyage-multimodal-3"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.voyageai.com/v1/embeddings"
        self.dimensions = 1024  # voyage-multilingual-2 dimensions

    async def get_embeddings(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """Generate embeddings for a list of texts using Voyage AI"""
        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self.base_url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={"model": self.model, "input": batch_texts},
                    )

                    if response.status_code != 200:
                        raise Exception(
                            f"Voyage API error: {response.status_code} - {response.text}"
                        )

                    result = response.json()
                    batch_embeddings = [item["embedding"] for item in result["data"]]
                    all_embeddings.extend(batch_embeddings)

                    logger.info(
                        f"Generated embeddings for batch {i//batch_size + 1}: {len(batch_texts)} texts"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to generate embeddings for batch {i//batch_size + 1}: {e}"
                )
                raise

        return all_embeddings


class EmbeddingStep(PipelineStep):
    """Production embedding step that generates embeddings for document chunks"""

    def __init__(
        self,
        config: Dict[str, Any],
        storage_client=None,
        progress_tracker=None,
        db: Client = None,
        pipeline_service=None,
    ):
        print(f"🔧 EmbeddingStep.__init__ called with config: {config}")
        print(f"   storage_client: {storage_client}")
        print(f"   progress_tracker: {progress_tracker}")
        print(f"   db: {db}")
        print(f"   pipeline_service: {pipeline_service}")

        super().__init__(config, progress_tracker)
        self.storage_client = storage_client
        self.db = db
        self.pipeline_service = pipeline_service

        # Initialize Voyage client
        print(f"🔧 Looking for API key in config: {config.get('api_key', 'NOT_FOUND')}")
        api_key = config.get("api_key")
        if not api_key:
            # Try to get from environment variable
            import os

            api_key = os.getenv("VOYAGE_API_KEY")
            print(
                f"🔧 API key from environment: {api_key[:10] + '...' if api_key else 'NOT_FOUND'}"
            )
            if not api_key:
                raise ValueError("Voyage API key not provided in config or environment")

        self.voyage_client = VoyageEmbeddingClient(
            api_key=api_key, model=config.get("model", "voyage-multimodal-3")
        )

        # Configuration
        self.batch_size = config.get("batch_size", 100)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 1.0)
        self.timeout_seconds = config.get("timeout_seconds", 30)
        self.resume_capability = config.get("resume_capability", True)

    async def execute(
        self, input_data: Any, indexing_run_id: UUID = None, document_id: UUID = None
    ) -> StepResult:
        """Execute the embedding step with chunking data from previous step"""
        start_time = datetime.now()

        try:
            logger.info("Starting embedding step execution")

            if not indexing_run_id or not document_id:
                raise ValueError(
                    "indexing_run_id and document_id are required for embedding step"
                )

            # Get chunks that need embedding from database
            chunks_to_embed = await self.get_chunks_for_embedding(
                indexing_run_id, document_id
            )

            if not chunks_to_embed:
                logger.info("No chunks found that need embedding")
                return StepResult(
                    step="embedding",
                    status="completed",
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                    data={"chunks_processed": 0, "embeddings_generated": 0},
                    summary_stats={"total_chunks": 0, "embeddings_generated": 0},
                )

            logger.info(f"Found {len(chunks_to_embed)} chunks that need embedding")

            # Generate embeddings
            embeddings = await self.generate_embeddings(chunks_to_embed)

            # Store embeddings back to database
            await self.store_embeddings(chunks_to_embed, embeddings, indexing_run_id)

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()

            # Create summary statistics
            summary_stats = {
                "total_chunks": len(chunks_to_embed),
                "embeddings_generated": len(embeddings),
                "embedding_model": self.voyage_client.model,
                "embedding_dimensions": self.voyage_client.dimensions,
                "batch_size_used": self.batch_size,
                "average_embedding_time": (
                    duration / len(chunks_to_embed) if chunks_to_embed else 0
                ),
            }

            # Create sample outputs
            sample_outputs = {
                "sample_embeddings": [
                    {
                        "chunk_id": chunk["chunk_id"],
                        "embedding_preview": f"Vector[{len(embedding)} dimensions]",
                        "content_preview": (
                            chunk["content"][:100] + "..."
                            if len(chunk["content"]) > 100
                            else chunk["content"]
                        ),
                    }
                    for chunk, embedding in zip(chunks_to_embed[:3], embeddings[:3])
                ]
            }

            logger.info(f"Embedding completed: {len(embeddings)} embeddings generated")

            return StepResult(
                step="embedding",
                status="completed",
                duration_seconds=duration,
                data={
                    "chunks_processed": len(chunks_to_embed),
                    "embeddings_generated": len(embeddings),
                    "embedding_model": self.voyage_client.model,
                },
                summary_stats=summary_stats,
                sample_outputs=sample_outputs,
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Embedding step failed: {str(e)}")

            return StepResult(
                step="embedding",
                status="failed",
                duration_seconds=duration,
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
            )

    async def get_chunks_for_embedding(
        self, indexing_run_id: UUID, document_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get chunks from database that need embedding"""
        try:
            # Query chunks that don't have embeddings yet
            query = (
                self.db.table("document_chunks")
                .select("*")
                .eq("indexing_run_id", str(indexing_run_id))
            )

            if self.resume_capability:
                # Only get chunks without embeddings for resume capability
                query = query.is_("embedding_1024", "null")

            result = query.execute()

            if not result.data:
                return []

            return result.data

        except Exception as e:
            logger.error(f"Failed to get chunks for embedding: {e}")
            raise

    async def generate_embeddings(
        self, chunks: List[Dict[str, Any]]
    ) -> List[List[float]]:
        """Generate embeddings for chunks with retry logic"""
        texts = [chunk["content"] for chunk in chunks]

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Generating embeddings (attempt {attempt + 1}/{self.max_retries})"
                )
                embeddings = await self.voyage_client.get_embeddings(
                    texts, self.batch_size
                )
                return embeddings

            except Exception as e:
                logger.warning(
                    f"Embedding generation failed (attempt {attempt + 1}): {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(
                        self.retry_delay * (2**attempt)
                    )  # Exponential backoff
                else:
                    raise

    async def store_embeddings(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        indexing_run_id: UUID,
    ):
        """Store embeddings back to database"""
        try:
            logger.info(f"Storing {len(embeddings)} embeddings in database")

            # Update each chunk with its embedding
            for chunk, embedding in zip(chunks, embeddings):
                self.db.table("document_chunks").update(
                    {
                        "embedding_1024": embedding,
                        "embedding_model": self.voyage_client.model,
                        "embedding_provider": "voyage",
                        "embedding_metadata": {
                            "dimensions": len(embedding),
                            "model": self.voyage_client.model,
                            "generated_at": datetime.now().isoformat(),
                        },
                        "embedding_created_at": datetime.now().isoformat(),
                    }
                ).eq("id", chunk["id"]).execute()

            logger.info(f"Successfully stored {len(embeddings)} embeddings in database")

        except Exception as e:
            logger.error(f"Failed to store embeddings in database: {e}")
            raise

    async def validate_prerequisites_async(self, input_data: Any) -> bool:
        """Validate that input data contains chunking results"""
        try:
            # Check if we have chunking results
            if hasattr(input_data, "data") and input_data.data:
                chunks = input_data.data.get("chunks", [])
                if len(chunks) > 0:
                    logger.info(f"Prerequisites validated: {len(chunks)} chunks found")
                    return True

            logger.warning("No chunks found in input data")
            return False

        except Exception as e:
            logger.error(f"Prerequisites validation failed: {str(e)}")
            return False

    def estimate_duration(self, input_data: Any) -> int:
        """Estimate embedding duration based on input size"""
        try:
            # Estimate based on number of chunks
            chunks = []
            if hasattr(input_data, "data") and input_data.data:
                chunks = input_data.data.get("chunks", [])

            # Rough estimate: 0.1 seconds per chunk + 2 seconds overhead
            estimated_seconds = len(chunks) * 0.1 + 2
            return max(1, int(estimated_seconds))

        except Exception as e:
            logger.error(f"Duration estimation failed: {str(e)}")
            return 30  # Default fallback
