"""Indexing pipeline orchestrator with explicit dependency injection."""

import asyncio
import time
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging
from fastapi import BackgroundTasks

from ..shared.base_step import PipelineStep, StepExecutor
from ..shared.progress_tracker import ProgressTracker
from ..shared.config_manager import ConfigManager
from ..shared.models import DocumentInput, PipelineError
from models import StepResult
from services.pipeline_service import PipelineService
from .steps.partition import PartitionStep
from .steps.metadata import MetadataStep
from .steps.enrichment import EnrichmentStep
from .steps.chunking import ChunkingStep

logger = logging.getLogger(__name__)


class IndexingOrchestrator:
    """Orchestrator with explicit dependency injection for indexing pipeline"""

    def __init__(
        self,
        db=None,
        storage=None,
        config_manager: ConfigManager = None,
        progress_tracker: ProgressTracker = None,
        pipeline_service: PipelineService = None,
    ):
        self.db = db
        self.storage = storage
        self.config_manager = config_manager or ConfigManager(db)
        self.progress_tracker = progress_tracker
        self.pipeline_service = pipeline_service or PipelineService()

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
            # Load configuration
            config = await self.config_manager.get_indexing_config(user_id)

            # Initialize real partition step
            partition_config = config.steps.get("partition", {})
            self.partition_step = PartitionStep(
                config=partition_config,
                storage_client=self.storage,
                progress_tracker=self.progress_tracker,
            )

            # Initialize real metadata step
            metadata_config = config.steps.get("metadata", {})
            self.metadata_step = MetadataStep(
                config=metadata_config,
                storage_client=self.storage,
                progress_tracker=self.progress_tracker,
            )

            # Initialize real enrichment step
            enrichment_config = config.steps.get("enrichment", {})
            self.enrichment_step = EnrichmentStep(
                config=enrichment_config,
                storage_client=self.storage,
                progress_tracker=self.progress_tracker,
            )

            # Initialize real chunking step
            chunking_config = config.steps.get("chunking", {})
            self.chunking_step = ChunkingStep(
                config=chunking_config,
                storage_client=self.storage,
                progress_tracker=self.progress_tracker,
            )
            self.embedding_step = self._create_placeholder_step(
                "embedding", config.steps.get("embedding", {})
            )
            self.storage_step = self._create_placeholder_step(
                "storage", config.steps.get("storage", {})
            )

            self.steps = [
                self.partition_step,
                self.metadata_step,
                self.enrichment_step,
                self.chunking_step,
                self.embedding_step,
                self.storage_step,
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
                start_time = time.time()

                # Simulate processing time
                await asyncio.sleep(1)

                duration = time.time() - start_time

                return StepResult(
                    step=self.name,
                    status="completed",
                    duration_seconds=duration,
                    summary_stats={"processed": True, "step_name": self.name},
                    sample_outputs={
                        "placeholder": f"Placeholder output for {self.name}"
                    },
                )

            async def validate_prerequisites_async(self, input_data: Any) -> bool:
                """Placeholder validation"""
                return True

            def estimate_duration(self, input_data: Any) -> int:
                """Placeholder duration estimation"""
                return 60  # 1 minute

        return PlaceholderStep(step_name, config)

    async def process_document_async(self, document_input: DocumentInput) -> bool:
        """Process a single document through all indexing steps sequentially"""
        indexing_run = None
        try:
            # Initialize steps if not already done
            if not self.steps:
                await self.initialize_steps(document_input.user_id)

            # Create indexing run in database
            indexing_run = await self.pipeline_service.create_indexing_run(
                document_id=document_input.document_id, user_id=document_input.user_id
            )

            # Update DocumentInput with run_id for storage operations
            document_input.run_id = indexing_run.id

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
                result = await step_executor.execute_with_tracking(current_data)

                # Store step result in database
                await self.pipeline_service.store_step_result(
                    indexing_run_id=indexing_run.id,
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

                # Update current data for next step
                current_data = result
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
    return IndexingOrchestrator(db, storage, config_manager, progress_tracker)
