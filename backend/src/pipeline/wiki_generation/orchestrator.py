"""Wiki generation pipeline orchestrator."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from src.models import (
    WikiGenerationRun,
    WikiGenerationRunCreate,
    WikiGenerationStatus,
    StepResult,
)
from src.services.storage_service import StorageService
from src.config.database import get_supabase_admin_client
from src.services.config_service import ConfigService
from .steps import (
    MetadataCollectionStep,
    OverviewGenerationStep,
    SemanticClusteringStep,
    StructureGenerationStep,
    PageContentRetrievalStep,
    MarkdownGenerationStep,
)

logger = logging.getLogger(__name__)


class WikiGenerationOrchestrator:
    """Orchestrator for wiki generation pipeline."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Load wiki config from SoT if not provided
        self.config: Dict[str, Any] = config or ConfigService().get_effective_config(
            "wiki"
        )
        self.storage_service = StorageService()
        self.supabase = get_supabase_admin_client()
        self.steps = self._initialize_steps()

    def _initialize_steps(self) -> Dict[str, Any]:
        """Initialize pipeline steps."""
        config_dict = self.config

        return {
            "metadata_collection": MetadataCollectionStep(
                config=config_dict,
                storage_service=self.storage_service,
            ),
            "overview_generation": OverviewGenerationStep(
                config=config_dict,
                storage_service=self.storage_service,
            ),
            "semantic_clustering": SemanticClusteringStep(
                config=config_dict,
                storage_service=self.storage_service,
            ),
            "structure_generation": StructureGenerationStep(
                config=config_dict,
                storage_service=self.storage_service,
            ),
            "page_content_retrieval": PageContentRetrievalStep(
                config=config_dict,
                storage_service=self.storage_service,
            ),
            "markdown_generation": MarkdownGenerationStep(
                config=config_dict,
                storage_service=self.storage_service,
            ),
        }

    async def run_pipeline(
        self,
        index_run_id: str,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        upload_type: str = "user_project",
    ) -> WikiGenerationRun:
        """Run the complete wiki generation pipeline."""
        start_time = datetime.utcnow()

        try:
            print(
                f"🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Starting pipeline for index run: {index_run_id}"
            )
            logger.info(
                f"Starting wiki generation pipeline for index run: {index_run_id}"
            )

            # Create wiki generation run record
            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Creating wiki generation run record"
            )
            wiki_run = await self._create_wiki_run(
                index_run_id, user_id, project_id, upload_type
            )
            print(
                f"🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Created wiki run: {wiki_run.id}"
            )

            # Step 1: Metadata Collection
            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Starting Step 1: Metadata Collection"
            )
            logger.info("Step 1: Metadata Collection")
            metadata_result = await self.steps["metadata_collection"].execute(
                {
                    "index_run_id": index_run_id,
                }
            )

            if metadata_result.status == "failed":
                print(
                    f"❌ [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Step 1 failed: {metadata_result.error_message}"
                )
                await self._update_wiki_run_status(
                    wiki_run.id, "failed", metadata_result.error_message
                )
                return wiki_run

            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Step 1 completed successfully"
            )
            metadata = metadata_result.data

            # Step 2: Overview Generation
            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Starting Step 2: Overview Generation"
            )
            logger.info("Step 2: Overview Generation")
            overview_result = await self.steps["overview_generation"].execute(
                {
                    "metadata": metadata,
                }
            )

            if overview_result.status == "failed":
                print(
                    f"❌ [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Step 2 failed: {overview_result.error_message}"
                )
                await self._update_wiki_run_status(
                    wiki_run.id, "failed", overview_result.error_message
                )
                return wiki_run

            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Step 2 completed successfully"
            )
            project_overview = overview_result.data["project_overview"]

            # Step 3: Semantic Clustering
            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Starting Step 3: Semantic Clustering"
            )
            logger.info("Step 3: Semantic Clustering")
            clustering_result = await self.steps["semantic_clustering"].execute(
                {
                    "metadata": metadata,
                }
            )

            if clustering_result.status == "failed":
                print(
                    f"❌ [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Step 3 failed: {clustering_result.error_message}"
                )
                await self._update_wiki_run_status(
                    wiki_run.id, "failed", clustering_result.error_message
                )
                return wiki_run

            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Step 3 completed successfully"
            )
            semantic_analysis = clustering_result.data

            # Step 4: Structure Generation
            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Starting Step 4: Structure Generation"
            )
            logger.info("Step 4: Structure Generation")
            structure_result = await self.steps["structure_generation"].execute(
                {
                    "metadata": metadata,
                    "project_overview": project_overview,
                    "semantic_analysis": semantic_analysis,
                }
            )

            if structure_result.status == "failed":
                print(
                    f"❌ [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Step 4 failed: {structure_result.error_message}"
                )
                await self._update_wiki_run_status(
                    wiki_run.id, "failed", structure_result.error_message
                )
                return wiki_run

            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Step 4 completed successfully"
            )
            wiki_structure = structure_result.data

            # Step 5: Page Content Retrieval
            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Starting Step 5: Page Content Retrieval"
            )
            logger.info("Step 5: Page Content Retrieval")
            content_result = await self.steps["page_content_retrieval"].execute(
                {
                    "metadata": metadata,
                    "wiki_structure": wiki_structure,
                }
            )

            if content_result.status == "failed":
                print(
                    f"❌ [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Step 5 failed: {content_result.error_message}"
                )
                await self._update_wiki_run_status(
                    wiki_run.id, "failed", content_result.error_message
                )
                return wiki_run

            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Step 5 completed successfully"
            )
            page_contents = content_result.data

            # Step 6: Markdown Generation
            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Starting Step 6: Markdown Generation"
            )
            logger.info("Step 6: Markdown Generation")
            markdown_result = await self.steps["markdown_generation"].execute(
                {
                    "metadata": metadata,
                    "wiki_structure": wiki_structure,
                    "page_contents": page_contents,
                }
            )

            if markdown_result.status == "failed":
                print(
                    f"❌ [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Step 6 failed: {markdown_result.error_message}"
                )
                await self._update_wiki_run_status(
                    wiki_run.id, "failed", markdown_result.error_message
                )
                return wiki_run

            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Step 6 completed successfully"
            )
            generated_pages = markdown_result.data

            # Step 7: Save to Storage
            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Starting Step 7: Saving to Storage"
            )
            logger.info("Step 7: Saving to Storage")
            await self._save_wiki_to_storage(
                wiki_run.id,
                wiki_structure,
                generated_pages,
                metadata,
                upload_type,
                user_id,
                project_id,
                index_run_id,
            )

            # Update wiki run status to completed
            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Updating wiki run status to completed"
            )
            await self._update_wiki_run_status(
                wiki_run.id,
                "completed",
                f"Successfully generated {len(generated_pages)} wiki pages",
            )

            # Update wiki run with final data
            print(
                "🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Getting final wiki run data"
            )
            final_wiki_run = await self._get_wiki_run(wiki_run.id)
            print(
                f"🔍 [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Final wiki run: {final_wiki_run.id}"
            )

            logger.info(
                f"Wiki generation pipeline completed successfully: {final_wiki_run.id}"
            )
            return final_wiki_run

        except Exception as e:
            print(
                f"❌ [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Pipeline failed: {e}"
            )
            logger.error(f"Wiki generation pipeline failed: {e}")

            # Update wiki run status to failed
            if "wiki_run" in locals():
                print(
                    f"❌ [DEBUG] WikiGenerationOrchestrator.run_pipeline() - Updating wiki run status to failed for run: {wiki_run.id}"
                )
                await self._update_wiki_run_status(wiki_run.id, "failed", str(e))

            raise

    async def _create_wiki_run(
        self,
        index_run_id: str,
        user_id: Optional[UUID],
        project_id: Optional[UUID],
        upload_type: str,
    ) -> WikiGenerationRun:
        """Create a new wiki generation run record."""
        wiki_run_data = WikiGenerationRunCreate(
            indexing_run_id=index_run_id,
            upload_type=upload_type,
            user_id=user_id,
            project_id=project_id,
            status=WikiGenerationStatus.PENDING,
        )

        # Convert UUIDs to strings for JSON serialization
        data_dict = wiki_run_data.model_dump(exclude_none=True)
        if data_dict.get("user_id"):
            data_dict["user_id"] = str(data_dict["user_id"])
        if data_dict.get("project_id"):
            data_dict["project_id"] = str(data_dict["project_id"])
        if data_dict.get("indexing_run_id"):
            data_dict["indexing_run_id"] = str(data_dict["indexing_run_id"])

        response = (
            self.supabase.table("wiki_generation_runs").insert(data_dict).execute()
        )

        if not response.data:
            raise Exception("Failed to create wiki generation run")

        # Convert pages_metadata from dict to list if needed
        run_data = response.data[0].copy()
        if "pages_metadata" in run_data and isinstance(
            run_data["pages_metadata"], dict
        ):
            run_data["pages_metadata"] = []

        return WikiGenerationRun(**run_data)

    async def _update_wiki_run_status(
        self, wiki_run_id: str, status: str, message: str = ""
    ) -> None:
        """Update wiki generation run status."""
        update_data = {
            "status": status,
            "completed_at": (
                datetime.utcnow().isoformat()
                if status in ["completed", "failed"]
                else None
            ),
        }

        if message:
            update_data["error_message"] = message if status == "failed" else None

        response = (
            self.supabase.table("wiki_generation_runs")
            .update(update_data)
            .eq("id", wiki_run_id)
            .execute()
        )

        if not response.data:
            logger.warning(f"Failed to update wiki run status: {wiki_run_id}")

    async def _get_wiki_run(self, wiki_run_id: str) -> WikiGenerationRun:
        """Get wiki generation run by ID."""
        response = (
            self.supabase.table("wiki_generation_runs")
            .select("*")
            .eq("id", wiki_run_id)
            .execute()
        )

        if not response.data:
            raise Exception(f"Wiki generation run not found: {wiki_run_id}")

        # Convert pages_metadata from dict to list if needed
        run_data = response.data[0].copy()
        if "pages_metadata" in run_data and isinstance(
            run_data["pages_metadata"], dict
        ):
            run_data["pages_metadata"] = []

        return WikiGenerationRun(**run_data)

    async def _save_wiki_to_storage(
        self,
        wiki_run_id: str,
        wiki_structure: Dict[str, Any],
        generated_pages: Dict[str, Any],
        metadata: Dict[str, Any],
        upload_type: str,
        user_id: Optional[UUID],
        project_id: Optional[UUID],
        index_run_id: str,
    ) -> None:
        """Save wiki content to storage and database."""
        try:
            # Create storage structure
            await self.storage_service.create_wiki_storage_structure(
                wiki_run_id=wiki_run_id,
                upload_type=upload_type,
                user_id=user_id,
                project_id=project_id,
                index_run_id=index_run_id,
            )

            # Prepare pages metadata for database storage
            pages_metadata_list = []
            storage_path = None

            # Save individual pages and collect metadata
            for i, (page_id, page_data) in enumerate(generated_pages.items(), 1):
                page_title = page_data["title"]
                markdown_content = page_data["markdown_content"]

                # Use simple numbered filename instead of sanitizing title
                filename = f"page-{i}.md"

                # Upload markdown file to storage
                upload_result = await self.storage_service.upload_wiki_page(
                    file_path=None,  # We'll pass content directly
                    filename=filename,
                    wiki_run_id=wiki_run_id,
                    upload_type=upload_type,
                    user_id=user_id,
                    project_id=project_id,
                    index_run_id=index_run_id,
                    content=markdown_content,
                )

                # Store the storage path for the first page (base path)
                if storage_path is None:
                    storage_path = upload_result["storage_path"].rsplit("/", 1)[0]

                # Create page metadata for database
                storage_url = upload_result["url"]
                # Ensure storage_url is a string (handle case where it might be a dict)
                if isinstance(storage_url, dict):
                    if "signedURL" in storage_url:
                        storage_url = storage_url["signedURL"]
                    elif "signedUrl" in storage_url:
                        storage_url = storage_url["signedUrl"]
                    else:
                        storage_url = str(storage_url)

                page_metadata = {
                    "title": page_title,
                    "filename": filename,
                    "storage_path": upload_result["storage_path"],
                    "storage_url": storage_url,
                    "file_size": len(markdown_content.encode("utf-8")),
                    "order": i,
                }
                pages_metadata_list.append(page_metadata)

                logger.info(f"Saved wiki page: {filename} (title: {page_title})")

            # Update database with metadata
            update_data = {
                "wiki_structure": wiki_structure,
                "pages_metadata": pages_metadata_list,
                "storage_path": storage_path,
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
            }

            # Update the wiki generation run record
            response = (
                self.supabase.table("wiki_generation_runs")
                .update(update_data)
                .eq("id", wiki_run_id)
                .execute()
            )

            if not response.data:
                raise Exception("Failed to update wiki generation run with metadata")

            logger.info(
                f"Successfully saved {len(generated_pages)} wiki pages to storage and metadata to database"
            )

        except Exception as e:
            logger.error(f"Failed to save wiki to storage and database: {e}")
            raise

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize title for use as filename."""
        import re

        # Remove special characters and replace spaces with underscores
        sanitized = re.sub(r"[^\w\s-]", "", title)
        sanitized = re.sub(r"[-\s]+", "_", sanitized)
        sanitized = sanitized.strip("_")

        return sanitized

    async def get_wiki_run(self, wiki_run_id: str) -> Optional[WikiGenerationRun]:
        """Get wiki generation run by ID."""
        try:
            return await self._get_wiki_run(wiki_run_id)
        except Exception as e:
            logger.error(f"Failed to get wiki run: {e}")
            return None

    async def list_wiki_runs(self, index_run_id: str) -> List[WikiGenerationRun]:
        """List all wiki generation runs for an indexing run."""
        response = (
            self.supabase.table("wiki_generation_runs")
            .select("*")
            .eq("indexing_run_id", index_run_id)
            .order("created_at", desc=True)
            .execute()
        )

        wiki_runs = []
        for run_data in response.data:
            # Create a copy to avoid modifying the original data
            run_data_copy = run_data.copy()
            # Convert pages_metadata from dict to list if needed
            if "pages_metadata" in run_data_copy and isinstance(
                run_data_copy["pages_metadata"], dict
            ):
                run_data_copy["pages_metadata"] = []
            wiki_runs.append(WikiGenerationRun(**run_data_copy))

        return wiki_runs

    async def delete_wiki_run(self, wiki_run_id: str) -> bool:
        """Delete a wiki generation run and its associated files."""
        try:
            # Get wiki run details
            wiki_run = await self._get_wiki_run(wiki_run_id)

            # Delete from storage
            await self.storage_service.delete_wiki_run(
                wiki_run_id=wiki_run_id,
                upload_type=wiki_run.upload_type,
                user_id=wiki_run.user_id,
                project_id=wiki_run.project_id,
                index_run_id=wiki_run.indexing_run_id,
            )

            # Delete from database
            response = (
                self.supabase.table("wiki_generation_runs")
                .delete()
                .eq("id", wiki_run_id)
                .execute()
            )

            return bool(response.data)

        except Exception as e:
            logger.error(f"Failed to delete wiki run: {e}")
            return False
