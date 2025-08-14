"""Wiki generation pipeline orchestrator."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from src.config.database import get_supabase_admin_client
from src.models import (
    WikiGenerationRun,
    WikiGenerationRunCreate,
    WikiGenerationStatus,
)
from src.models.pipeline import UploadType
from src.services.config_service import ConfigService
from src.services.storage_service import StorageService

from .models import (
    to_markdown_output,
    to_metadata_output,
    to_overview_output,
    to_page_contents_output,
    to_semantic_output,
    to_structure_output,
)
from .steps import (
    MarkdownGenerationStep,
    MetadataCollectionStep,
    OverviewGenerationStep,
    PageContentRetrievalStep,
    SemanticClusteringStep,
    StructureGenerationStep,
)

logger = logging.getLogger(__name__)


class WikiGenerationOrchestrator:
    """Orchestrator for wiki generation pipeline."""

    def __init__(self, config: dict[str, Any] | None = None, *, db_client=None):
        # Load wiki config from SoT if not provided
        self.config: dict[str, Any] = config or ConfigService().get_effective_config("wiki")
        self.storage_service = StorageService()
        self.supabase = db_client or get_supabase_admin_client()
        self.steps = self._initialize_steps(db_client=db_client)

    def _initialize_steps(self, *, db_client=None) -> dict[str, Any]:
        """Initialize pipeline steps."""
        config_dict = self.config

        return {
            "metadata_collection": MetadataCollectionStep(
                config=config_dict,
                storage_service=self.storage_service,
                db_client=db_client,
            ),
            "overview_generation": OverviewGenerationStep(
                config=config_dict,
                storage_service=self.storage_service,
                db_client=db_client,
            ),
            "semantic_clustering": SemanticClusteringStep(
                config=config_dict,
                storage_service=self.storage_service,
                db_client=db_client,
            ),
            "structure_generation": StructureGenerationStep(
                config=config_dict,
                storage_service=self.storage_service,
                db_client=db_client,
            ),
            "page_content_retrieval": PageContentRetrievalStep(
                config=config_dict,
                storage_service=self.storage_service,
                db_client=db_client,
            ),
            "markdown_generation": MarkdownGenerationStep(
                config=config_dict,
                storage_service=self.storage_service,
                db_client=db_client,
            ),
        }

    async def run_pipeline(
        self,
        index_run_id: str,
        user_id: UUID | None = None,
        project_id: UUID | None = None,
        upload_type: UploadType | str = "user_project",
    ) -> WikiGenerationRun:
        """Run the complete wiki generation pipeline."""
        start_time = datetime.utcnow()

        try:
            logger.info(f"Starting wiki generation pipeline for index run: {index_run_id}")

            # Convert string to enum if needed
            if isinstance(upload_type, str):
                upload_type_enum = UploadType.EMAIL if upload_type == "email" else UploadType.USER_PROJECT
            else:
                upload_type_enum = upload_type

            # Create wiki generation run record
            wiki_run = await self._create_wiki_run(index_run_id, user_id, project_id, upload_type_enum)

            # Step 1: Metadata Collection
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
                await self._update_wiki_run_status(wiki_run.id, "failed", metadata_result.error_message)
                return wiki_run

            metadata = to_metadata_output(metadata_result.data).model_dump(exclude_none=True)

            # Step 2: Overview Generation
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
                await self._update_wiki_run_status(wiki_run.id, "failed", overview_result.error_message)
                return wiki_run

            project_overview = to_overview_output(overview_result.data).project_overview

            # Step 3: Semantic Clustering
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
                await self._update_wiki_run_status(wiki_run.id, "failed", clustering_result.error_message)
                return wiki_run

            semantic_analysis = to_semantic_output(clustering_result.data).model_dump(exclude_none=True)

            # Step 4: Structure Generation
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
                await self._update_wiki_run_status(wiki_run.id, "failed", structure_result.error_message)
                return wiki_run

            wiki_structure = to_structure_output(structure_result.data).wiki_structure

            # Step 5: Page Content Retrieval
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
                await self._update_wiki_run_status(wiki_run.id, "failed", content_result.error_message)
                return wiki_run

            page_contents = to_page_contents_output(content_result.data).page_contents

            # Step 6: Markdown Generation
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
                await self._update_wiki_run_status(wiki_run.id, "failed", markdown_result.error_message)
                return wiki_run

            generated_pages = to_markdown_output(markdown_result.data).generated_pages

            # Step 7: Save to Storage
            logger.info("Step 7: Saving to Storage")
            await self._save_wiki_to_storage(
                wiki_run.id,
                wiki_structure,
                generated_pages,
                metadata,
                upload_type_enum,
                user_id,
                project_id,
                index_run_id,
            )

            # Update wiki run status to completed
            await self._update_wiki_run_status(
                wiki_run.id,
                "completed",
                f"Successfully generated {len(generated_pages)} wiki pages",
            )

            # Update wiki run with final data
            final_wiki_run = await self._get_wiki_run(wiki_run.id)

            logger.info(f"Wiki generation pipeline completed successfully: {final_wiki_run.id}")
            return final_wiki_run

        except Exception as e:
            logger.error(f"Wiki generation pipeline failed: {e}")
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
        user_id: UUID | None,
        project_id: UUID | None,
        upload_type: UploadType,
    ) -> WikiGenerationRun:
        """Create a new wiki generation run record."""
        
        # Get the access_level from the parent indexing run
        indexing_run_response = (
            self.supabase.table("indexing_runs")
            .select("access_level")
            .eq("id", index_run_id)
            .limit(1)
            .execute()
        )
        
        # Default to 'private' if we can't find the indexing run
        access_level = "private"
        if indexing_run_response.data:
            access_level = indexing_run_response.data[0].get("access_level", "private")
        
        logger.info(f"Creating wiki run for indexing run {index_run_id} with access_level: {access_level}")
        
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
        
        # Set the inherited access_level
        data_dict["access_level"] = access_level

        response = self.supabase.table("wiki_generation_runs").insert(data_dict).execute()

        if not response.data:
            raise Exception("Failed to create wiki generation run")

        # Convert pages_metadata from dict to list if needed
        run_data = response.data[0].copy()
        if "pages_metadata" in run_data and isinstance(run_data["pages_metadata"], dict):
            run_data["pages_metadata"] = []

        return WikiGenerationRun(**run_data)

    async def _update_wiki_run_status(self, wiki_run_id: str, status: str, message: str = "") -> None:
        """Update wiki generation run status."""
        update_data = {
            "status": status,
            "completed_at": (datetime.utcnow().isoformat() if status in ["completed", "failed"] else None),
        }

        if message:
            update_data["error_message"] = message if status == "failed" else None

        response = self.supabase.table("wiki_generation_runs").update(update_data).eq("id", wiki_run_id).execute()

        if not response.data:
            logger.warning(f"Failed to update wiki run status: {wiki_run_id}")

    async def _get_wiki_run(self, wiki_run_id: str) -> WikiGenerationRun:
        """Get wiki generation run by ID."""
        response = self.supabase.table("wiki_generation_runs").select("*").eq("id", wiki_run_id).execute()

        if not response.data:
            raise Exception(f"Wiki generation run not found: {wiki_run_id}")

        # Convert pages_metadata from dict to list if needed
        run_data = response.data[0].copy()
        if "pages_metadata" in run_data and isinstance(run_data["pages_metadata"], dict):
            run_data["pages_metadata"] = []

        return WikiGenerationRun(**run_data)

    async def _save_wiki_to_storage(
        self,
        wiki_run_id: str,
        wiki_structure: dict[str, Any],
        generated_pages: dict[str, Any],
        metadata: dict[str, Any],
        upload_type: UploadType,
        user_id: UUID | None,
        project_id: UUID | None,
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
            response = self.supabase.table("wiki_generation_runs").update(update_data).eq("id", wiki_run_id).execute()

            if not response.data:
                raise Exception("Failed to update wiki generation run with metadata")

            logger.info(f"Successfully saved {len(generated_pages)} wiki pages to storage and metadata to database")

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

    async def get_wiki_run(self, wiki_run_id: str) -> WikiGenerationRun | None:
        """Get wiki generation run by ID."""
        try:
            return await self._get_wiki_run(wiki_run_id)
        except Exception as e:
            logger.error(f"Failed to get wiki run: {e}")
            return None

    async def list_wiki_runs(self, index_run_id: str) -> list[WikiGenerationRun]:
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
            if "pages_metadata" in run_data_copy and isinstance(run_data_copy["pages_metadata"], dict):
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
            response = self.supabase.table("wiki_generation_runs").delete().eq("id", wiki_run_id).execute()

            return bool(response.data)

        except Exception as e:
            logger.error(f"Failed to delete wiki run: {e}")
            return False
