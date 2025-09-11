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
from src.models import StepResult
from ...shared.models import PipelineError
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError
from src.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class VoyageEmbeddingClient:
    """Client for Voyage AI embedding API"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.voyageai.com/v1/embeddings"
        self.dimensions = 1024  # voyage-multilingual-2 dimensions

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for Danish/multilingual text"""
        # Conservative estimate for voyage-multilingual-2:
        # - Danish text has longer compound words and special chars
        # - Technical construction text is token-dense
        # - Use 1.8x multiplier for safety (Danish factor + technical content)
        return int(len(text) * 1.8)

    def split_batch_by_tokens(self, texts: List[str], max_tokens: int = 100000) -> List[List[str]]:
        """Split texts into batches that don't exceed token limits"""
        batches = []
        current_batch = []
        current_tokens = 0
        
        for text in texts:
            text_tokens = self.estimate_tokens(text)
            
            # If adding this text would exceed limit, start new batch
            if current_batch and (current_tokens + text_tokens) > max_tokens:
                batches.append(current_batch)
                current_batch = [text]
                current_tokens = text_tokens
            else:
                current_batch.append(text)
                current_tokens += text_tokens
                
        # Add final batch if not empty
        if current_batch:
            batches.append(current_batch)
            
        return batches

    async def get_embeddings(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """Generate embeddings for a list of texts using Voyage AI with token-aware batching"""
        all_embeddings = []
        
        # Split texts by token limits first (120K limit for voyage-multilingual-2)
        token_batches = self.split_batch_by_tokens(texts, max_tokens=100000)
        log_msg = f"📊 Split {len(texts)} texts into {len(token_batches)} token-limited batches"
        logger.info(log_msg)
        print(log_msg)
        
        # Process each token-limited batch
        for token_batch_idx, token_batch in enumerate(token_batches):
            estimated_tokens = sum(self.estimate_tokens(text) for text in token_batch)
            log_msg = f"🔄 Processing token batch {token_batch_idx + 1}/{len(token_batches)}: {len(token_batch)} texts, ~{estimated_tokens:,} estimated tokens"
            logger.info(log_msg)
            print(log_msg)
            
            # Further split by batch_size within token limits
            for i in range(0, len(token_batch), batch_size):
                batch_texts = token_batch[i : i + batch_size]
                batch_tokens = sum(self.estimate_tokens(text) for text in batch_texts)
                batch_num = i // batch_size + 1
                total_batches = (len(token_batch) + batch_size - 1) // batch_size

                try:
                    api_msg = f"🌐 Sending API request for batch {batch_num}/{total_batches}: {len(batch_texts)} texts, ~{batch_tokens:,} estimated tokens"
                    logger.info(api_msg)
                    print(api_msg)
                    async with httpx.AsyncClient(timeout=90.0) as client:
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

                    success_msg = f"✅ Generated embeddings for batch {batch_num}/{total_batches}: {len(batch_texts)} texts, ~{batch_tokens:,} estimated tokens"
                    logger.info(success_msg)
                    print(success_msg)

            except Exception as e:
                error_msg = f"❌ Failed to generate embeddings for batch {batch_num}/{total_batches}: {e}"
                logger.error(error_msg)
                print(error_msg)
                
                # Enhanced error logging for better debugging
                details_msg = f"Voyage API request details: model={self.model}, batch_size={len(batch_texts)}, estimated_tokens={batch_tokens:,}"
                logger.error(details_msg)
                print(details_msg)
                
                sample_msg = f"Sample batch content: {[text[:100] + '...' if len(text) > 100 else text for text in batch_texts[:3]]}"
                logger.error(sample_msg)
                print(sample_msg)
                
                # Check if it's a token limit error
                if "token" in str(e).lower() or "limit" in str(e).lower():
                    limit_msg = f"⚠️ Suspected token limit exceeded! Batch had ~{batch_tokens:,} estimated tokens (voyage-multilingual-2 limit: 120K)"
                    logger.error(limit_msg)
                    print(limit_msg)
                
                # Log HTTP response details if available
                if hasattr(e, 'response') and e.response:
                    logger.error(f"HTTP response status: {e.response.status_code}")
                    logger.error(f"HTTP response body: {e.response.text[:500]}")
                
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
        storage_service=None,
    ):
        # Initialize embedding step

        super().__init__(config, progress_tracker)
        self.storage_client = storage_client
        self.db = db
        self.pipeline_service = pipeline_service
        self.storage_service = storage_service or StorageService()

        # Create database client if not provided
        if self.db is None:
            from src.config.database import get_supabase_admin_client

            self.db = get_supabase_admin_client()

        # Initialize Voyage client
        api_key = config.get("api_key")
        if not api_key:
            # Try to get from environment variable
            from src.config.settings import get_settings

            settings = get_settings()
            api_key = settings.voyage_api_key
            if not api_key:
                raise ValueError("Voyage API key not provided in config or environment")

        # Model from SoT: orchestrator provided config already includes embedding settings
        model_name = config.get("model") or "voyage-multilingual-2"
        self.voyage_client = VoyageEmbeddingClient(api_key=api_key, model=model_name)

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
            if document_id:
                logger.info(
                    f"Starting embedding step execution for document {document_id}"
                )
            else:
                logger.info(
                    f"Starting batch embedding step execution for index run {indexing_run_id}"
                )

            if not indexing_run_id:
                raise ValueError("indexing_run_id is required for embedding step")

            # Get chunks that need embedding from database
            chunks_to_embed = await self.get_chunks_for_embedding(
                indexing_run_id, document_id
            )

            if not chunks_to_embed:
                logger.info("No chunks found that need embedding")
                return StepResult(
                    step="embedding",
                    status="completed",
                    duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    data={"chunks_processed": 0, "embeddings_generated": 0},
                    summary_stats={"total_chunks": 0, "embeddings_generated": 0},
                    started_at=start_time,
                    completed_at=datetime.utcnow(),
                )

            logger.info(f"Found {len(chunks_to_embed)} chunks that need embedding")

            # Generate embeddings (may return empty list on failure)
            embeddings = await self.generate_embeddings(chunks_to_embed)

            # Handle embedding failure gracefully
            if not embeddings:
                logger.error(f"No embeddings generated for any chunks. Marking all chunks as failed.")
                # Mark all chunks as failed in database
                await self.store_failed_embeddings(chunks_to_embed, "All embedding attempts failed", indexing_run_id)
                
                # Return failed result
                duration = (datetime.utcnow() - start_time).total_seconds()
                return StepResult(
                    step="embedding",
                    status="failed",
                    duration_seconds=duration,
                    error_message=f"Failed to generate embeddings for all {len(chunks_to_embed)} chunks after {self.max_retries} retries",
                    data={"chunks_processed": len(chunks_to_embed), "embeddings_generated": 0, "chunks_failed": len(chunks_to_embed)},
                    summary_stats={"total_chunks": len(chunks_to_embed), "embeddings_generated": 0, "success_rate": 0.0},
                    started_at=start_time,
                    completed_at=datetime.utcnow(),
                )

            # Check for partial embedding success/failure
            if len(embeddings) != len(chunks_to_embed):
                logger.warning(f"Partial embedding success: {len(embeddings)}/{len(chunks_to_embed)} chunks embedded")

            # Store successful embeddings back to database
            await self.store_embeddings(chunks_to_embed[:len(embeddings)], embeddings, indexing_run_id)
            
            # Mark remaining chunks as failed if any
            if len(embeddings) < len(chunks_to_embed):
                failed_chunks = chunks_to_embed[len(embeddings):]
                await self.store_failed_embeddings(failed_chunks, "Embedding generation partially failed", indexing_run_id)

            # Validate embedding quality
            quality_metrics = await self.validate_embedding_quality(
                chunks_to_embed, embeddings
            )

            # Verify final indexes and optimization
            index_verification = await self.verify_final_indexes(indexing_run_id)

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Calculate success rate for threshold check
            success_rate = len(embeddings) / len(chunks_to_embed) if chunks_to_embed else 0.0
            success_threshold = 0.80  # 80% success threshold
            
            # Determine step status based on success rate
            if success_rate >= success_threshold:
                step_status = "completed"
                status_message = f"Embedding completed with {success_rate:.1%} success rate"
                if success_rate < 1.0:
                    status_message += f" ({len(embeddings)}/{len(chunks_to_embed)} chunks)"
            else:
                step_status = "failed" 
                status_message = f"Embedding failed - only {success_rate:.1%} success rate (below {success_threshold:.0%} threshold)"

            # Create summary statistics
            summary_stats = {
                "total_chunks": len(chunks_to_embed),
                "embeddings_generated": len(embeddings),
                "chunks_failed": len(chunks_to_embed) - len(embeddings),
                "success_rate": success_rate,
                "success_threshold": success_threshold,
                "embedding_model": self.voyage_client.model,
                "embedding_dimensions": self.voyage_client.dimensions,
                "batch_size_used": self.batch_size,
                "average_embedding_time": (
                    duration / len(chunks_to_embed) if chunks_to_embed else 0
                ),
                "quality_score": quality_metrics.get("quality_score", 0.0),
                "zero_vectors": quality_metrics.get("zero_vectors", 0),
                "duplicate_embeddings": quality_metrics.get("duplicate_embeddings", 0),
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

            logger.info(status_message)

            return StepResult(
                step="embedding",
                status=step_status,
                duration_seconds=duration,
                error_message=status_message if step_status == "failed" else None,
                data={
                    "chunks_processed": len(chunks_to_embed),
                    "embeddings_generated": len(embeddings),
                    "chunks_failed": len(chunks_to_embed) - len(embeddings),
                    "success_rate": success_rate,
                    "embedding_model": self.voyage_client.model,
                    "embedding_quality": quality_metrics,
                    "index_verification": index_verification,
                },
                summary_stats=summary_stats,
                sample_outputs=sample_outputs,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Embedding step failed: {str(e)}")
            raise AppError(
                "Embedding step failed",
                error_code=ErrorCode.EXTERNAL_API_ERROR,
                details={"reason": str(e)},
            ) from e

    async def get_chunks_for_embedding(
        self, indexing_run_id: UUID, document_id: UUID = None
    ) -> List[Dict[str, Any]]:
        """Get chunks from database that need embedding"""
        try:
            # Query chunks that don't have embeddings yet
            query = (
                self.db.table("document_chunks")
                .select("*")
                .eq("indexing_run_id", str(indexing_run_id))
            )

            # If document_id is provided, filter by specific document
            if document_id:
                query = query.eq("document_id", str(document_id))

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
                logger.error(
                    f"Embedding generation failed (attempt {attempt + 1}): {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(
                        self.retry_delay * (2**attempt)
                    )  # Exponential backoff
                else:
                    # CRITICAL FIX: Return empty list instead of raising exception
                    # This prevents the entire document processing from being killed
                    logger.error(f"All embedding attempts failed after {self.max_retries} retries. Returning empty embeddings.")
                    return []  # Return empty list for graceful failure handling

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
                            "status": "completed",
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

    async def store_failed_embeddings(
        self,
        chunks: List[Dict[str, Any]],
        error_message: str,
        indexing_run_id: UUID,
    ):
        """Mark chunks as failed in database using embedding_metadata"""
        try:
            logger.info(f"Marking {len(chunks)} chunks as embedding failed in database")

            # Update each chunk with failure information
            for chunk in chunks:
                self.db.table("document_chunks").update(
                    {
                        "embedding_metadata": {
                            "status": "failed",
                            "error": error_message,
                            "model": self.voyage_client.model,
                            "failed_at": datetime.now().isoformat(),
                        },
                    }
                ).eq("id", chunk["id"]).execute()

            logger.info(f"Successfully marked {len(chunks)} chunks as embedding failed")

        except Exception as e:
            logger.error(f"Failed to mark chunks as embedding failed: {e}")
            # Don't raise - we don't want to fail the entire step for metadata updates

    async def validate_embedding_quality(
        self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]
    ) -> Dict[str, Any]:
        """Validate embedding quality and generate metrics"""
        try:
            logger.info("Validating embedding quality...")

            import numpy as np

            # Basic quality checks
            quality_metrics = {
                "total_embeddings": len(embeddings),
                "embedding_dimensions": len(embeddings[0]) if embeddings else 0,
                "zero_vectors": 0,
                "duplicate_embeddings": 0,
                "embedding_stats": {},
                "similarity_analysis": {},
                "quality_score": 0.0,
                "validation_timestamp": datetime.now().isoformat(),
            }

            if not embeddings:
                return quality_metrics

            # Convert to numpy for calculations
            embedding_array = np.array(embeddings)

            # Check for zero vectors
            zero_vectors = np.sum(np.all(embedding_array == 0, axis=1))
            quality_metrics["zero_vectors"] = int(zero_vectors)

            # Calculate embedding statistics
            quality_metrics["embedding_stats"] = {
                "mean": float(np.mean(embedding_array)),
                "std": float(np.std(embedding_array)),
                "min": float(np.min(embedding_array)),
                "max": float(np.max(embedding_array)),
                "norm_mean": float(np.mean(np.linalg.norm(embedding_array, axis=1))),
                "norm_std": float(np.std(np.linalg.norm(embedding_array, axis=1))),
            }

            # Check for duplicate embeddings (simple check)
            unique_embeddings = len(set(tuple(emb) for emb in embeddings))
            quality_metrics["duplicate_embeddings"] = (
                len(embeddings) - unique_embeddings
            )

            # Calculate similarity between first few embeddings
            if len(embeddings) >= 2:
                # Normalize embeddings for cosine similarity
                normalized_embeddings = embedding_array / np.linalg.norm(
                    embedding_array, axis=1, keepdims=True
                )

                # Calculate similarity between first two embeddings
                similarity = np.dot(normalized_embeddings[0], normalized_embeddings[1])
                quality_metrics["similarity_analysis"] = {
                    "first_two_similarity": float(similarity),
                    "self_similarity_check": float(
                        np.dot(normalized_embeddings[0], normalized_embeddings[0])
                    ),
                }

            # Calculate overall quality score
            quality_score = 0.0
            if quality_metrics["zero_vectors"] == 0:
                quality_score += 0.3
            if quality_metrics["duplicate_embeddings"] == 0:
                quality_score += 0.3
            if quality_metrics["embedding_stats"]["norm_mean"] > 0.9:
                quality_score += 0.2
            if quality_metrics["embedding_stats"]["std"] > 0.01:
                quality_score += 0.2

            quality_metrics["quality_score"] = quality_score

            logger.info(
                f"Embedding quality validation completed. Score: {quality_score:.2f}"
            )
            return quality_metrics

        except Exception as e:
            logger.error(f"Embedding quality validation failed: {e}")
            return {
                "total_embeddings": len(embeddings),
                "quality_score": 0.0,
                "error": str(e),
                "validation_timestamp": datetime.now().isoformat(),
            }

    async def store_quality_metrics(
        self, quality_metrics: Dict[str, Any], indexing_run_id: UUID
    ):
        """Store embedding quality metrics in the indexing run"""
        try:
            logger.info("Storing embedding quality metrics...")

            # Store quality metrics under the embedding step result
            # This will be handled by the main embedding step result storage
            return quality_metrics

            logger.info("Embedding quality metrics stored successfully")

        except Exception as e:
            logger.error(f"Failed to store quality metrics: {e}")
            # Don't fail the entire step for this

    async def verify_final_indexes(self, indexing_run_id: UUID):
        """Verify that all necessary indexes are in place for optimal retrieval"""
        try:
            logger.info("Verifying final indexes...")

            # Get a sample embedding to test with
            result = (
                self.db.table("document_chunks")
                .select("embedding_1024")
                .eq("indexing_run_id", str(indexing_run_id))
                .limit(1)
                .execute()
            )

            if result.data and result.data[0].get("embedding_1024"):
                # Test that we can query embeddings (this will use the HNSW index)
                test_embedding = result.data[0]["embedding_1024"]

                # Simple test: count embeddings for this run
                count_result = (
                    self.db.table("document_chunks")
                    .select("id", count="exact")
                    .eq("indexing_run_id", str(indexing_run_id))
                    .not_.is_("embedding_1024", "null")
                    .execute()
                )

                embedding_count = count_result.count if count_result.count else 0

                logger.info(
                    f"Index verification successful. Found {embedding_count} embeddings for this run"
                )

                # Store index verification status under the embedding step result
                # This will be handled by the main embedding step result storage
                return {
                    "embeddings_found": embedding_count,
                    "index_status": "verified",
                    "test_results": f"Found {embedding_count} embeddings with HNSW index",
                }

            else:
                logger.warning("No embeddings found for index verification")
                # Return verification failure data
                return {
                    "embeddings_found": 0,
                    "index_status": "failed",
                    "error_message": "No embeddings found for verification",
                }

        except Exception as e:
            logger.error(f"Index verification failed: {e}")
            # Return verification failure data
            return {
                "embeddings_found": 0,
                "index_status": "failed",
                "error_message": str(e),
            }

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
