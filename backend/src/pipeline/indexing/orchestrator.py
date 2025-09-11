"""Indexing pipeline orchestrator with explicit dependency injection."""

import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging
from fastapi import BackgroundTasks

try:
    from ..shared.base_step import PipelineStep, StepExecutor
except Exception as e:
    raise

try:
    from ..shared.progress_tracker import ProgressTracker
except Exception as e:
    raise

try:
    from ..shared.config_manager import ConfigManager
except Exception as e:
    raise
from src.services.config_service import ConfigService

try:
    from ..shared.models import DocumentInput, PipelineError
    from src.models.pipeline import UploadType
except Exception as e:
    raise

try:
    from src.models import StepResult
except Exception as e:
    raise

try:
    from src.services.pipeline_service import PipelineService
except Exception as e:
    raise

try:
    from .steps.partition import PartitionStep
except Exception as e:
    raise

try:
    from .steps.metadata import MetadataStep
except Exception as e:
    raise

try:
    from .steps.enrichment import EnrichmentStep
except Exception as e:
    raise

try:
    from .steps.chunking import ChunkingStep
except Exception as e:
    raise

try:
    from .steps.embedding import EmbeddingStep
except Exception as e:
    raise

logger = logging.getLogger(__name__)
from .models import (
    to_partition_output,
    to_metadata_output,
    to_enrichment_output,
    to_chunking_output,
)


class IndexingOrchestrator:
    """Orchestrator with explicit dependency injection for indexing pipeline"""

    def __init__(
        self,
        db=None,
        storage=None,
        config_manager: ConfigManager = None,
        progress_tracker: ProgressTracker = None,
        pipeline_service: PipelineService = None,
        use_test_storage: bool = False,
        upload_type: UploadType = UploadType.USER_PROJECT,
    ):
        self.db = db
        self.storage = storage
        self.config_manager = config_manager or ConfigManager(db)
        self.progress_tracker = progress_tracker
        # Use provided pipeline service or create one with admin client if db is available
        if pipeline_service:
            self.pipeline_service = pipeline_service
        elif db:
            # Create pipeline service with admin client using the existing db connection
            self.pipeline_service = PipelineService(use_admin_client=True)
        else:
            # Fallback to regular pipeline service
            self.pipeline_service = PipelineService()
        self.upload_type = upload_type

        # Initialize storage service based on test flag
        if use_test_storage:
            from src.services.storage_service import StorageService

            self.storage_service = StorageService.create_test_storage()
            logger.info("Using test storage service")
        else:
            from src.services.storage_service import StorageService

            self.storage_service = StorageService()
            logger.info("Using production storage service")

        # Initialize steps with injected dependencies
        # These will be properly initialized when config is loaded
        self.partition_step = None
        self.metadata_step = None
        self.enrichment_step = None
        self.chunking_step = None
        self.embedding_step = None
        self.storage_step = None

        self.steps = []

    async def initialize_steps(self, user_id: Optional[UUID] = None):
        """Initialize pipeline steps with configuration"""
        try:
            # Load configuration (SoT overrides enforced in ConfigManager)
            if not self.config_manager:
                raise ValueError("Config manager is None - cannot initialize steps")

            config = await self.config_manager.get_indexing_config(user_id)

            # Initialize real partition step
            partition_config = config.steps.get("partition", {})
            self.partition_step = PartitionStep(
                config=partition_config,
                storage_client=self.storage,
                progress_tracker=self.progress_tracker,
                storage_service=self.storage_service,
            )

            # Initialize real metadata step
            metadata_config = config.steps.get("metadata", {})
            self.metadata_step = MetadataStep(
                config=metadata_config,
                storage_client=self.storage,
                progress_tracker=self.progress_tracker,
                storage_service=self.storage_service,
            )

            # Initialize real enrichment step
            enrichment_config = config.steps.get("enrichment", {})
            self.enrichment_step = EnrichmentStep(
                config=enrichment_config,
                storage_client=self.storage,
                progress_tracker=self.progress_tracker,
                storage_service=self.storage_service,
            )

            # Initialize real chunking step
            chunking_config = config.steps.get("chunking", {})
            self.chunking_step = ChunkingStep(
                config=chunking_config,
                storage_client=self.storage,
                progress_tracker=self.progress_tracker,
                db=self.db,
                pipeline_service=self.pipeline_service,
                storage_service=self.storage_service,
            )
            # Initialize embedding & storage step (combined)
            embedding_config = config.steps.get("embedding", {})
            self.embedding_step = EmbeddingStep(
                config=embedding_config,
                progress_tracker=self.progress_tracker,
                db=self.db,
                pipeline_service=self.pipeline_service,
                storage_service=self.storage_service,
            )

            self.steps = [
                self.partition_step,
                self.metadata_step,
                self.enrichment_step,
                self.chunking_step,
                self.embedding_step,
            ]

            logger.info("Indexing pipeline steps initialized")

        except Exception as e:
            logger.error(f"Failed to initialize indexing steps: {e}")
            raise

    def _create_placeholder_step(
        self, step_name: str, config: Dict[str, Any]
    ) -> PipelineStep:
        """Create a placeholder step for now (will be replaced with actual implementations)"""

        class PlaceholderStep(PipelineStep):
            def __init__(self, name: str, step_config: Dict[str, Any]):
                super().__init__(step_config)
                self.name = name

            async def execute(self, input_data: Any) -> StepResult:
                """Placeholder execution"""
                start_time = datetime.utcnow()

                # Simulate processing time
                await asyncio.sleep(1)

                duration = (datetime.utcnow() - start_time).total_seconds()

                return StepResult(
                    step=self.name,
                    status="completed",
                    duration_seconds=duration,
                    summary_stats={"processed": True, "step_name": self.name},
                    sample_outputs={
                        "placeholder": f"Placeholder output for {self.name}"
                    },
                    started_at=start_time,
                    completed_at=datetime.utcnow(),
                )

            async def validate_prerequisites_async(self, input_data: Any) -> bool:
                """Placeholder validation"""
                return True

            def estimate_duration(self, input_data: Any) -> int:
                """Placeholder duration estimation"""
                return 60  # 1 minute

        return PlaceholderStep(step_name, config)

    async def process_document_async(
        self,
        document_input: DocumentInput,
        existing_indexing_run_id: Optional[UUID] = None,
    ) -> bool:
        """Process a single document through all indexing steps sequentially"""
        indexing_run = None
        try:
            # Initialize steps if not already done
            if not self.steps:
                await self.initialize_steps(document_input.user_id)

            # Create or get indexing run in database
            if existing_indexing_run_id:
                indexing_run = await self.pipeline_service.get_indexing_run(
                    existing_indexing_run_id
                )
                if not indexing_run:
                    raise ValueError(
                        f"Indexing run {existing_indexing_run_id} not found"
                    )
                logger.info(f"Using existing indexing run: {existing_indexing_run_id}")
            else:
                indexing_run = await self.pipeline_service.create_indexing_run(
                    upload_type=document_input.upload_type,
                    user_id=document_input.user_id,
                    project_id=document_input.project_id,
                )

            # Link document to indexing run
            if document_input.document_id:
                await self.pipeline_service.link_document_to_indexing_run(
                    indexing_run_id=indexing_run.id,
                    document_id=document_input.document_id,
                )

            # Update DocumentInput with run_id for storage operations
            document_input.run_id = indexing_run.id

            # Create storage structure for the upload type
            await self.storage_service.create_storage_structure(
                upload_type=document_input.upload_type,
                user_id=document_input.user_id,
                project_id=document_input.project_id,
                index_run_id=indexing_run.id,
            )

            # Store the configuration used for this run (effective indexing config)
            effective = ConfigService().get_effective_config("indexing")
            await self.config_manager.store_run_config(indexing_run.id, effective)

            # Update status to running
            await self.pipeline_service.update_indexing_run_status(
                indexing_run_id=indexing_run.id, status="running"
            )

            # Create progress tracker for this run
            progress_tracker = ProgressTracker(indexing_run.id, self.db)

            logger.info(
                f"Starting indexing pipeline for document {document_input.document_id} (run: {indexing_run.id})"
            )

            # Sequential step execution for single document
            current_data = document_input

            for step in self.steps:
                step_executor = StepExecutor(step, progress_tracker)

                # Debug logging to see what we're passing to each step
                logger.info(
                    f"🔍 Orchestrator passing to {step.get_step_name()}: type={type(current_data)}"
                )
                logger.info(
                    f"🔍 Orchestrator passing to {step.get_step_name()}: {current_data}"
                )

                # Special handling for steps that need run information
                if isinstance(step, ChunkingStep):
                    result = await step.execute(
                        current_data, indexing_run.id, document_input.document_id
                    )
                elif isinstance(step, EmbeddingStep):
                    result = await step.execute(
                        current_data, indexing_run.id, document_input.document_id
                    )
                else:
                    result = await step_executor.execute_with_tracking(current_data)

                # Store step result in document's step_results field
                await self.pipeline_service.store_document_step_result(
                    document_id=document_input.document_id,
                    step_name=step.get_step_name(),
                    step_result=result,
                )

                if result.status == "failed":
                    logger.error(
                        f"Step {step.get_step_name()} failed: {result.error_message}"
                    )
                    await self.pipeline_service.update_indexing_run_status(
                        indexing_run_id=indexing_run.id,
                        status="failed",
                        error_message=result.error_message,
                    )
                    return False

                # Update current data for next step using typed adapters
                if hasattr(result, "data") and result.data is not None:
                    if isinstance(step, PartitionStep):
                        current_data = to_partition_output(result.data).model_dump(
                            exclude_none=True
                        )
                    elif isinstance(step, MetadataStep):
                        current_data = to_metadata_output(result.data).model_dump(
                            exclude_none=True
                        )
                    elif isinstance(step, EnrichmentStep):
                        current_data = to_enrichment_output(result.data).model_dump(
                            exclude_none=True
                        )
                    elif isinstance(step, ChunkingStep):
                        current_data = to_chunking_output(result.data).model_dump(
                            exclude_none=True
                        )
                    else:
                        current_data = result.data
                    logger.info(
                        f"🔍 Orchestrator passing typed data to next step: type={type(current_data)}"
                    )
                else:
                    current_data = result
                    logger.info(
                        f"🔍 Orchestrator passing entire result to next step (no data field): type={type(result)}"
                    )

                logger.info(
                    f"🔍 Orchestrator step {step.get_step_name()} returned: type={type(result)}"
                )
                logger.info(
                    f"🔍 Orchestrator step {step.get_step_name()} returned: {result}"
                )
                logger.info(f"Completed step {step.get_step_name()}")

            # Mark indexing run as completed
            await self.pipeline_service.update_indexing_run_status(
                indexing_run_id=indexing_run.id, status="completed"
            )

            logger.info(
                f"Successfully completed indexing pipeline for document {document_input.document_id} (run: {indexing_run.id})"
            )
            return True

        except Exception as e:
            logger.error(
                f"Indexing pipeline failed for document {document_input.document_id}: {e}"
            )
            if indexing_run:
                await self.pipeline_service.update_indexing_run_status(
                    indexing_run_id=indexing_run.id,
                    status="failed",
                    error_message=str(e),
                )
            return False

    async def process_documents(
        self,
        document_inputs: List[DocumentInput],
        existing_indexing_run_id: Optional[UUID] = None,
    ) -> bool:
        """
        Process multiple documents in a single index run with intelligent batching.

        This method provides a unified interface for processing 1→N documents,
        with optimized parallel processing for individual steps and batch embedding.
        """
        if not document_inputs:
            logger.warning("No documents provided for processing")
            return False

        indexing_run = None
        try:
            # Initialize steps if not already done
            if not self.steps:
                await self.initialize_steps(document_inputs[0].user_id)

            # Create or get indexing run in database
            if existing_indexing_run_id:
                indexing_run = await self.pipeline_service.get_indexing_run(
                    existing_indexing_run_id
                )
                if not indexing_run:
                    raise ValueError(
                        f"Indexing run {existing_indexing_run_id} not found"
                    )
                logger.info(f"Using existing indexing run: {existing_indexing_run_id}")
            else:
                indexing_run = await self.pipeline_service.create_indexing_run(
                    upload_type=document_inputs[0].upload_type,
                    user_id=document_inputs[0].user_id,
                    project_id=document_inputs[0].project_id,
                )

            # Link all documents to indexing run
            for doc_input in document_inputs:
                if doc_input.document_id:
                    await self.pipeline_service.link_document_to_indexing_run(
                        indexing_run_id=indexing_run.id,
                        document_id=doc_input.document_id,
                    )
                # Update DocumentInput with run_id for storage operations
                doc_input.run_id = indexing_run.id

            # Create storage structure for the upload type
            await self.storage_service.create_storage_structure(
                upload_type=document_inputs[0].upload_type,
                user_id=document_inputs[0].user_id,
                project_id=document_inputs[0].project_id,
                index_run_id=indexing_run.id,
            )

            # Store the configuration used for this run (effective indexing config)
            effective = ConfigService().get_effective_config("indexing")
            await self.config_manager.store_run_config(indexing_run.id, effective)

            # Update status to running
            await self.pipeline_service.update_indexing_run_status(
                indexing_run_id=indexing_run.id, status="running"
            )

            # Create progress tracker for this run
            progress_tracker = ProgressTracker(indexing_run.id, self.db)

            logger.info(
                f"Starting unified indexing pipeline for {len(document_inputs)} documents (run: {indexing_run.id})"
            )

            # Phase 1: Process each document through individual steps (partition → metadata → enrichment → chunking)
            document_results = await self._process_documents_individual_steps(
                document_inputs, indexing_run.id, progress_tracker
            )

            # Check if any documents failed
            failed_document_ids = [
                doc_id for doc_id, result in document_results.items() if not result
            ]
            successful_document_ids = [
                doc_id for doc_id, result in document_results.items() if result
            ]

            if not successful_document_ids:
                logger.error("All documents failed processing")
                await self.pipeline_service.update_indexing_run_status(
                    indexing_run_id=indexing_run.id,
                    status="failed",
                    error_message="All documents failed during individual step processing",
                )
                return False

            # Phase 2: Embedding now handled per-document above (no batch embedding needed)
            # Batch embedding has been moved to per-document processing for better parallelization

            # Generate embedding summary
            total_documents = len(document_inputs)
            successful_embeddings = len(successful_document_ids)  # Assumes embeddings succeeded if document succeeded
            failed_embeddings = len(failed_document_ids)
            
            print(f"📊 EMBEDDING SUMMARY:")
            print(f"  ✅ Successful: {successful_embeddings}")
            print(f"  ❌ Failed: {failed_embeddings}")
            print(f"  📄 Total documents: {total_documents}")

            # Update final status
            if failed_document_ids:
                logger.warning(
                    f"{len(failed_document_ids)} documents failed, but {len(successful_document_ids)} succeeded"
                )
                await self.pipeline_service.update_indexing_run_status(
                    indexing_run_id=indexing_run.id,
                    status="failed",
                    error_message=f"Completed with {len(failed_document_ids)} failed documents",
                )
            else:
                logger.info(
                    f"Successfully completed processing all {len(document_inputs)} documents"
                )
                await self.pipeline_service.update_indexing_run_status(
                    indexing_run_id=indexing_run.id, status="completed"
                )

            return True

        except Exception as e:
            logger.error(f"Unified indexing pipeline failed: {e}")
            if indexing_run:
                await self.pipeline_service.update_indexing_run_status(
                    indexing_run_id=indexing_run.id,
                    status="failed",
                    error_message=str(e),
                )
            return False

    async def _process_documents_individual_steps(
        self,
        document_inputs: List[DocumentInput],
        indexing_run_id: UUID,
        progress_tracker: ProgressTracker,
    ) -> Dict[UUID, bool]:
        """
        Process each document through individual pipeline steps using continuous queue processing.
        Uses semaphore-based concurrency control for optimal resource utilization.
        """
        results = {}

        # Continuous processing with semaphore (no batch boundaries)
        max_concurrent = 5  # Process up to 5 concurrent documents
        semaphore = asyncio.Semaphore(max_concurrent)
        
        print(f"🔄 Starting continuous processing of {len(document_inputs)} documents with max {max_concurrent} concurrent")

        async def process_with_semaphore(doc_input: DocumentInput) -> tuple[UUID, bool]:
            """Process a single document with semaphore control"""
            async with semaphore:
                try:
                    print(f"📄 Starting document {doc_input.document_id}")
                    result = await self._process_single_document_steps(
                        doc_input, indexing_run_id, progress_tracker
                    )
                    print(f"✅ Completed document {doc_input.document_id}: {'Success' if result else 'Failed'}")
                    return doc_input.document_id, result
                except Exception as e:
                    logger.error(f"Document {doc_input.document_id} failed: {e}")
                    print(f"❌ Failed document {doc_input.document_id}: {e}")
                    return doc_input.document_id, False

        # Create all tasks at once (continuous queue)
        tasks = [
            asyncio.create_task(process_with_semaphore(doc_input))
            for doc_input in document_inputs
        ]

        # Process results as they complete (no waiting for batches)
        completed_count = 0
        for coro in asyncio.as_completed(tasks):
            doc_id, result = await coro
            results[doc_id] = result
            completed_count += 1
            print(f"🏁 Progress: {completed_count}/{len(document_inputs)} documents completed")

        return results

    async def _process_single_document_steps(
        self,
        document_input: DocumentInput,
        indexing_run_id: UUID,
        progress_tracker: ProgressTracker,
    ) -> bool:
        """
        Process a single document through individual pipeline steps.
        Stops before embedding step - that's handled separately in batch.
        """
        try:
            current_data = document_input

            # Process through all individual steps (partition → metadata → enrichment → chunking → embedding)
            for step in self.steps:  # Include ALL steps including embedding
                step_executor = StepExecutor(step, progress_tracker)

                print(
                    f"📄 Processing {step.get_step_name()} for document {document_input.document_id}"
                )

                # Special handling for steps that need run information
                if isinstance(step, ChunkingStep):
                    result = await step.execute(
                        current_data, indexing_run_id, document_input.document_id
                    )
                elif isinstance(step, EmbeddingStep):
                    # Enhanced logging for embedding step
                    print(f"🔗 Starting embedding for document {document_input.document_id}")
                    result = await step.execute(
                        current_data, 
                        indexing_run_id=indexing_run_id, 
                        document_id=document_input.document_id
                    )
                    if result.status == "completed":
                        embeddings_count = result.summary_stats.get("embeddings_generated", 0)
                        print(f"✅ Embedding completed for document {document_input.document_id}: {embeddings_count} embeddings")
                    else:
                        print(f"❌ Embedding failed for document {document_input.document_id}: {result.error_message}")
                else:
                    result = await step_executor.execute_with_tracking(current_data)

                # Store step result in document's metadata (for individual document processing)
                await self.pipeline_service.store_document_step_result(
                    document_id=document_input.document_id,
                    step_name=step.get_step_name(),
                    step_result=result,
                )

                if result.status == "failed":
                    logger.error(
                        f"Step {step.get_step_name()} failed for document {document_input.document_id}: {result.error_message}"
                    )
                    return False

                # Prepare typed data for next step
                if hasattr(result, "data") and result.data is not None:
                    if isinstance(step, PartitionStep):
                        current_data = to_partition_output(result.data).model_dump(
                            exclude_none=True
                        )
                    elif isinstance(step, MetadataStep):
                        current_data = to_metadata_output(result.data).model_dump(
                            exclude_none=True
                        )
                    elif isinstance(step, EnrichmentStep):
                        current_data = to_enrichment_output(result.data).model_dump(
                            exclude_none=True
                        )
                    elif isinstance(step, ChunkingStep):
                        current_data = to_chunking_output(result.data).model_dump(
                            exclude_none=True
                        )
                    else:
                        current_data = result.data
                else:
                    current_data = result

            print(
                f"✅ Completed individual steps for document {document_input.document_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Individual step processing failed for document {document_input.document_id}: {e}"
            )
            return False

    async def _batch_embed_all_chunks(
        self,
        indexing_run_id: UUID,
        progress_tracker: ProgressTracker,
    ) -> bool:
        """
        Batch embed all chunks from all documents in the index run.
        This is the optimization that reduces API calls and improves efficiency.
        """
        try:
            logger.info(f"Starting batch embedding for index run {indexing_run_id}")

            # Get the embedding step
            embedding_step = None
            for step in self.steps:
                if isinstance(step, EmbeddingStep):
                    embedding_step = step
                    break

            if not embedding_step:
                logger.error("Embedding step not found")
                return False

            # Execute batch embedding
            result = await embedding_step.execute(
                None,  # No input data needed for batch embedding
                indexing_run_id=indexing_run_id,
                document_id=None,  # Process all documents
            )

            # Store embedding step result in indexing run (batch operation affects all documents)
            await self.pipeline_service.store_step_result(
                indexing_run_id=indexing_run_id,
                step_name="embedding",
                step_result=result,
            )

            if result.status == "failed":
                logger.error(f"Batch embedding failed: {result.error_message}")
                return False

            logger.info(
                f"Successfully completed batch embedding for index run {indexing_run_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            return False

    async def process_multiple_documents_async(
        self, document_inputs: List[DocumentInput]
    ) -> Dict[UUID, bool]:
        """Process multiple documents in parallel"""
        try:
            logger.info(
                f"Starting parallel processing of {len(document_inputs)} documents"
            )

            # Create tasks for parallel processing
            tasks = []
            for doc_input in document_inputs:
                task = asyncio.create_task(self.process_document_async(doc_input))
                tasks.append((doc_input.document_id, task))

            # Wait for all tasks to complete
            results = {}
            for doc_id, task in tasks:
                try:
                    result = await task
                    results[doc_id] = result
                except Exception as e:
                    logger.error(f"Task failed for document {doc_id}: {e}")
                    results[doc_id] = False

            logger.info(f"Completed parallel processing. Results: {results}")
            return results

        except Exception as e:
            logger.error(f"Parallel processing failed: {e}")
            return {doc_input.document_id: False for doc_input in document_inputs}

    async def get_pipeline_status(self, document_id: UUID) -> Dict[str, Any]:
        """Get current status of indexing pipeline for a document"""
        try:
            # This would query the database for actual status
            # For now, return placeholder status
            return {
                "document_id": str(document_id),
                "status": "running",
                "completed_steps": 0,
                "total_steps": 6,
                "progress_percentage": 0.0,
            }
        except Exception as e:
            logger.error(f"Failed to get pipeline status: {e}")
            return {"error": str(e)}


# FastAPI dependency injection helper
async def get_indexing_orchestrator(
    db=None,
    storage=None,
    config_manager: ConfigManager = None,
    progress_tracker: ProgressTracker = None,
) -> IndexingOrchestrator:
    """Get indexing orchestrator with all dependencies injected"""
    # Create pipeline service if not provided - use admin client for background operations
    pipeline_service = PipelineService(use_admin_client=True) if db is None else None

    return IndexingOrchestrator(
        db, storage, config_manager, progress_tracker, pipeline_service
    )
