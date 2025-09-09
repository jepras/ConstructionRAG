#!/usr/bin/env python3
"""
Admin Cleanup Script for ConstructionRAG (v2)
Bulk deletion of indexing runs and all associated data.

This script handles comprehensive cleanup including:
- Database direct deletion (not just orphaned documents)
- Projects deletion when no other indexing runs remain
- Supabase Storage cleanup (PDFs, generated files, temp files)
- Safety features (dry-run, confirmations, logging)
- Automatic oldest-X cleanup mode

Usage:
    python admin_cleanup_v2.py --dry-run  # Preview what would be deleted
    python admin_cleanup_v2.py --confirm   # Execute actual deletions
    python admin_cleanup_v2.py --oldest 50 --confirm  # Delete oldest 50 runs
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

try:
    from src.config.database import get_supabase_admin_client
    from src.services.storage_service import StorageService, UploadType
    from src.utils.exceptions import StorageError
except Exception as e:
    print(f"Import error: {e}")
    print(f"Error type: {type(e).__name__}")
    print(f"Backend path: {backend_path}")
    print(f"Path exists: {backend_path.exists()}")
    import traceback
    traceback.print_exc()
    print("Make sure you're running this script from the backend directory")
    sys.exit(1)


# Configuration - Add indexing run IDs here for manual deletion
INDEXING_RUNS_TO_DELETE = [
    # Add specific indexing run IDs here if needed
]

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class CleanupStats:
    """Track deletion statistics."""

    def __init__(self):
        self.indexing_runs_deleted = 0
        self.wiki_runs_deleted = 0
        self.documents_deleted = 0
        self.chunks_deleted = 0
        self.projects_deleted = 0
        self.indexing_run_documents_deleted = 0
        self.query_runs_deleted = 0
        self.storage_paths_deleted = []
        self.failed_operations = []
        self.start_time = datetime.now()

    def add_failure(self, operation: str, error: str):
        self.failed_operations.append(f"{operation}: {error}")

    def get_summary(self) -> str:
        duration = datetime.now() - self.start_time
        return f"""
Cleanup Summary:
================
Duration: {duration.total_seconds():.1f} seconds
Indexing runs deleted: {self.indexing_runs_deleted}
Wiki runs deleted: {self.wiki_runs_deleted}  
Documents deleted: {self.documents_deleted}
Document chunks deleted: {self.chunks_deleted} (via CASCADE)
Projects deleted: {self.projects_deleted}
Indexing-run-documents deleted: {self.indexing_run_documents_deleted}
Query runs deleted: {self.query_runs_deleted}
Storage paths deleted: {len(self.storage_paths_deleted)}
Failed operations: {len(self.failed_operations)}

Storage paths cleaned:
{chr(10).join(f"  - {path}" for path in self.storage_paths_deleted[:10])}
{"  ... and more" if len(self.storage_paths_deleted) > 10 else ""}

{"Failures:" if self.failed_operations else ""}
{chr(10).join(f"  - {failure}" for failure in self.failed_operations[:5])}
{"  ... and more" if len(self.failed_operations) > 5 else ""}
"""


class AdminCleanup:
    """Admin cleanup service for bulk deletion operations."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.stats = CleanupStats()

        # Initialize clients - use service role for admin operations
        self.supabase = get_supabase_admin_client()
        self.storage_service = StorageService()

        logger.info(f"Initialized AdminCleanup (dry_run={dry_run})")

    async def get_oldest_indexing_runs(self, limit: int) -> list[dict[str, Any]]:
        """Get the oldest indexing runs."""
        try:
            result = (
                self.supabase.table("indexing_runs")
                .select("id, upload_type, user_id, project_id, started_at")
                .order("started_at", desc=False)
                .limit(limit)
                .execute()
            )

            return result.data
        except Exception as e:
            logger.error(f"Failed to get oldest indexing runs: {e}")
            return []

    async def get_indexing_run_details(self, run_id: UUID) -> dict[str, Any] | None:
        """Get detailed information about an indexing run."""
        try:
            result = self.supabase.table("indexing_runs").select("*").eq("id", str(run_id)).single().execute()

            return result.data
        except Exception as e:
            logger.warning(f"Could not get details for indexing run {run_id}: {e}")
            return None

    async def get_associated_wiki_runs(self, run_id: UUID) -> list[dict[str, Any]]:
        """Get wiki generation runs associated with an indexing run."""
        try:
            result = (
                self.supabase.table("wiki_generation_runs")
                .select("id, storage_path, upload_type, user_id, project_id")
                .eq("indexing_run_id", str(run_id))
                .execute()
            )

            return result.data
        except Exception as e:
            logger.warning(f"Could not get wiki runs for {run_id}: {e}")
            return []

    async def get_associated_documents(self, run_id: UUID) -> list[dict[str, Any]]:
        """Get documents associated with an indexing run."""
        try:
            result = (
                self.supabase.table("indexing_run_documents")
                .select("document_id, documents(id, file_path, user_id, filename)")
                .eq("indexing_run_id", str(run_id))
                .execute()
            )

            documents = []
            for item in result.data:
                if item.get("documents"):
                    documents.append(item["documents"])

            return documents
        except Exception as e:
            logger.warning(f"Could not get documents for {run_id}: {e}")
            return []

    async def delete_indexing_run_documents(self, run_id: UUID) -> int:
        """Delete all indexing_run_documents entries for a run and return count."""
        try:
            if not self.dry_run:
                result = (
                    self.supabase.table("indexing_run_documents").delete().eq("indexing_run_id", str(run_id)).execute()
                )
                count = len(result.data) if result.data else 0
            else:
                # Count entries that would be deleted in dry run
                result = (
                    self.supabase.table("indexing_run_documents")
                    .select("id")
                    .eq("indexing_run_id", str(run_id))
                    .execute()
                )
                count = len(result.data)

            logger.info(
                f"{'[DRY RUN] Would delete' if self.dry_run else 'Deleted'} {count} indexing_run_documents entries"
            )
            return count
        except Exception as e:
            logger.warning(f"Could not delete indexing_run_documents for {run_id}: {e}")
            self.stats.add_failure(f"indexing_run_documents deletion {run_id}", str(e))
            return 0

    async def get_document_chunks_count(self, document_id: str) -> int:
        """Get count of chunks for a document."""
        try:
            result = self.supabase.table("document_chunks").select("id").eq("document_id", document_id).execute()
            return len(result.data)
        except Exception as e:
            logger.warning(f"Could not count chunks for document {document_id}: {e}")
            return 0

    async def delete_documents_and_chunks(self, documents: list[dict[str, Any]]) -> int:
        """Delete documents and their chunks (CASCADE). Returns count deleted."""
        deleted_count = 0
        total_chunks = 0

        for doc in documents:
            doc_id = doc.get("id")
            filename = doc.get("filename", "unknown")

            try:
                # Count chunks before deletion for reporting
                chunk_count = await self.get_document_chunks_count(doc_id)
                total_chunks += chunk_count

                if not self.dry_run:
                    # Delete document (chunks will be deleted via CASCADE)
                    result = self.supabase.table("documents").delete().eq("id", doc_id).execute()

                    if result.data:
                        deleted_count += 1
                        logger.info(f"Deleted document {doc_id} ({filename}) with {chunk_count} chunks")
                else:
                    deleted_count += 1
                    logger.info(f"[DRY RUN] Would delete document {doc_id} ({filename}) with {chunk_count} chunks")

            except Exception as e:
                logger.warning(f"Failed to delete document {doc_id}: {e}")
                self.stats.add_failure(f"Document deletion {doc_id}", str(e))

        # Update chunks deleted count in stats
        self.stats.chunks_deleted += total_chunks
        logger.info(
            f"{'[DRY RUN] Would delete' if self.dry_run else 'Deleted'} {total_chunks} total document chunks via CASCADE"
        )

        return deleted_count

    async def delete_query_runs(self, run_id: UUID) -> int:
        """Delete all query_runs associated with this indexing run."""
        try:
            if not self.dry_run:
                result = self.supabase.table("query_runs").delete().eq("indexing_run_id", str(run_id)).execute()
                count = len(result.data) if result.data else 0
            else:
                # Count entries that would be deleted in dry run
                result = self.supabase.table("query_runs").select("id").eq("indexing_run_id", str(run_id)).execute()
                count = len(result.data)

            if count > 0:
                logger.info(f"{'[DRY RUN] Would delete' if self.dry_run else 'Deleted'} {count} query_runs")
            else:
                logger.info(f"No query runs found for indexing run {run_id}")
            return count
        except Exception as e:
            logger.warning(f"Could not delete query_runs for {run_id}: {e}")
            self.stats.add_failure(f"query_runs deletion {run_id}", str(e))
            return 0

    async def check_and_delete_project(self, project_id: UUID | None, user_id: UUID | None) -> bool:
        """Check if project should be deleted and delete it if so, including its storage folder."""
        if not project_id:
            return False

        try:
            # Check if project has any other indexing runs
            result = self.supabase.table("indexing_runs").select("id").eq("project_id", str(project_id)).execute()

            remaining_runs = len(result.data)

            # Only delete project if this was its last indexing run
            if remaining_runs <= 1:  # <= 1 because current run might still exist during deletion
                # Delete project storage folder first (but only if it exists and has remaining content)
                if user_id:
                    project_folder = f"users/{user_id}/projects/{project_id}"
                    if not self.dry_run:
                        # Delete entire project folder
                        success = await self.delete_storage_folder_completely(project_folder)
                        if success:
                            self.stats.storage_paths_deleted.append(project_folder)
                            logger.info(f"Deleted project storage folder: {project_folder}")
                        else:
                            logger.warning(f"Failed to delete project storage folder: {project_folder}")
                    else:
                        logger.info(f"[DRY RUN] Would delete project storage folder: {project_folder}")
                        self.stats.storage_paths_deleted.append(f"[DRY RUN] Would delete folder: {project_folder}")

                # Delete project from database
                if not self.dry_run:
                    project_result = self.supabase.table("projects").delete().eq("id", str(project_id)).execute()

                    if project_result.data:
                        logger.info(f"Deleted project {project_id} (no remaining indexing runs)")
                        self.stats.projects_deleted += 1
                        return True
                else:
                    logger.info(f"[DRY RUN] Would delete project {project_id} (no remaining indexing runs)")
                    self.stats.projects_deleted += 1
                    return True
            else:
                logger.info(f"Project {project_id} has {remaining_runs} remaining runs, keeping it")

        except Exception as e:
            logger.warning(f"Failed to check/delete project {project_id}: {e}")
            self.stats.add_failure(f"Project deletion {project_id}", str(e))

        return False

    async def delete_storage_folder_recursive(self, folder_path: str) -> list[str]:
        """Recursively delete all files and folders within a storage path."""
        deleted_paths = []

        def list_all_files_recursive(path: str, all_files: list):
            """Recursively list all files in subdirectories."""
            try:
                # List contents of current path
                result = self.supabase.storage.from_("pipeline-assets").list(path)

                if result:
                    for item in result:
                        item_path = f"{path.rstrip('/')}/{item['name']}"

                        # Check if it's a file (has size metadata) or folder
                        if "metadata" in item and item["metadata"] and "size" in item["metadata"]:
                            # It's a file
                            all_files.append(item_path)
                        else:
                            # It's likely a folder, recurse into it
                            list_all_files_recursive(item_path, all_files)
            except Exception as e:
                logger.warning(f"Failed to list contents of {path}: {e}")

        try:
            # Get all files recursively
            all_files = []
            list_all_files_recursive(folder_path, all_files)

            if all_files:
                # Delete all files in batches (Supabase has limits)
                batch_size = 100
                for i in range(0, len(all_files), batch_size):
                    batch = all_files[i : i + batch_size]
                    try:
                        delete_result = self.supabase.storage.from_("pipeline-assets").remove(batch)
                        deleted_paths.extend(batch)
                        logger.info(f"Deleted batch of {len(batch)} files from {folder_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete batch: {e}")
                        self.stats.add_failure(f"Batch deletion {folder_path}", str(e))

                logger.info(f"Total deleted {len(deleted_paths)} files from {folder_path}")
            else:
                logger.info(f"No files found in {folder_path}")

        except Exception as e:
            logger.warning(f"Failed to delete folder contents {folder_path}: {e}")
            self.stats.add_failure(f"Folder deletion {folder_path}", str(e))

        return deleted_paths

    async def delete_storage_folder_completely(self, folder_path: str) -> bool:
        """Delete all files in a folder using direct database approach (recommended by Supabase community)."""
        try:
            logger.info(f"Attempting complete deletion of storage folder: {folder_path}")

            # First, try the direct database approach recommended by Supabase community
            # This deletes all objects where the name starts with our folder path
            try:
                # Use the storage schema to directly delete objects
                # This is more reliable than the recursive API approach
                delete_result = (
                    self.supabase.schema("storage")
                    .from_("objects")
                    .delete()
                    .eq("bucket_id", "pipeline-assets")
                    .like("name", f"{folder_path}%")
                    .execute()
                )

                deleted_count = len(delete_result.data) if delete_result.data else 0
                logger.info(f"Database approach: deleted {deleted_count} objects from {folder_path}")

                if deleted_count > 0:
                    return True

            except Exception as e:
                logger.warning(f"Direct database deletion failed: {e}")
                # Fall back to API approach

            # Fallback: Use the API approach with improved recursion
            def collect_all_files_recursive(path: str, all_files: list, visited: set):
                """Recursively collect all file paths for deletion."""
                if path in visited:
                    return
                visited.add(path)

                try:
                    items = self.supabase.storage.from_("pipeline-assets").list(path)
                    if items:
                        for item in items:
                            item_path = f"{path.rstrip('/')}/{item['name']}"

                            # Check if it's a file by looking for size metadata or id (files have these)
                            is_file = (
                                item.get("id") is not None  # Files have IDs
                                or (item.get("metadata") and item["metadata"].get("size") is not None)
                            )

                            if is_file:
                                all_files.append(item_path)
                                logger.debug(f"Found file: {item_path}")
                            else:
                                # It's a folder, recurse into it
                                logger.debug(f"Found folder: {item_path}")
                                collect_all_files_recursive(item_path, all_files, visited)
                except Exception as e:
                    logger.warning(f"Failed to list contents of {path}: {e}")

            all_files = []
            visited = set()
            collect_all_files_recursive(folder_path, all_files, visited)

            logger.info(f"Found {len(all_files)} files to delete in {folder_path}")

            if all_files:
                # Delete all files in smaller batches (Supabase has URL length limits)
                batch_size = 25  # Reduced batch size for better reliability
                deleted_files = []

                for i in range(0, len(all_files), batch_size):
                    batch = all_files[i : i + batch_size]
                    try:
                        result = self.supabase.storage.from_("pipeline-assets").remove(batch)
                        deleted_files.extend(batch)
                        logger.info(f"Deleted batch {i // batch_size + 1}: {len(batch)} files")
                    except Exception as e:
                        logger.warning(f"Batch deletion failed: {e}")
                        # Try individual deletions for this batch
                        for file_path in batch:
                            try:
                                result = self.supabase.storage.from_("pipeline-assets").remove([file_path])
                                deleted_files.append(file_path)
                                logger.debug(f"Individually deleted: {file_path}")
                            except Exception as individual_error:
                                logger.warning(f"Failed to delete {file_path}: {individual_error}")

                logger.info(
                    f"Successfully deleted {len(deleted_files)} out of {len(all_files)} files from {folder_path}"
                )
                return len(deleted_files) > 0
            else:
                logger.info(f"No files found in {folder_path} - folder may already be empty")
                return True

        except Exception as e:
            logger.error(f"Failed to delete folder {folder_path}: {e}")
            self.stats.add_failure(f"Folder deletion {folder_path}", str(e))
            return False

    async def delete_storage_paths(
        self, run_id: UUID, upload_type: str, user_id: UUID | None, project_id: UUID | None
    ) -> list[str]:
        """Delete entire folder structure for an indexing run."""
        deleted_paths = []

        try:
            # Determine the root folder path based on upload type
            if upload_type == UploadType.EMAIL.value:
                root_folder = f"email-uploads/index-runs/{run_id}"
            else:  # USER_PROJECT
                root_folder = f"users/{user_id}/projects/{project_id}/index-runs/{run_id}"

            if not self.dry_run:
                # Delete the entire folder in one operation
                success = await self.delete_storage_folder_completely(root_folder)
                if success:
                    deleted_paths.append(root_folder)
                    logger.info(f"Successfully deleted folder structure: {root_folder}")
                else:
                    logger.warning(f"Failed to delete folder structure: {root_folder}")
            else:
                deleted_paths.append(f"[DRY RUN] Would delete entire folder: {root_folder}")
                logger.info(f"[DRY RUN] Would delete entire folder: {root_folder}")

        except Exception as e:
            logger.error(f"Failed to delete storage for run {run_id}: {e}")
            self.stats.add_failure(f"Storage deletion for run {run_id}", str(e))

        return deleted_paths

    async def delete_indexing_run(self, run_id: UUID) -> bool:
        """Delete a single indexing run and all associated data."""
        logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}Processing indexing run: {run_id}")

        try:
            # Get run details
            run_details = await self.get_indexing_run_details(run_id)
            if not run_details:
                logger.warning(f"Indexing run {run_id} not found")
                return False

            upload_type = run_details.get("upload_type")
            user_id = run_details.get("user_id")
            project_id = run_details.get("project_id")

            logger.info(f"Run details: upload_type={upload_type}, user_id={user_id}, project_id={project_id}")

            # Get associated data for reporting
            wiki_runs = await self.get_associated_wiki_runs(run_id)
            documents = await self.get_associated_documents(run_id)

            logger.info(f"Found {len(wiki_runs)} wiki runs, {len(documents)} documents")
            logger.info(f"Will delete all {len(documents)} documents associated with this indexing run")

            # Delete storage paths
            deleted_paths = await self.delete_storage_paths(
                run_id, upload_type, UUID(user_id) if user_id else None, UUID(project_id) if project_id else None
            )
            self.stats.storage_paths_deleted.extend(deleted_paths)

            # Delete wiki storage paths
            for wiki_run in wiki_runs:
                wiki_id = wiki_run.get("id")
                wiki_storage_path = wiki_run.get("storage_path")
                if wiki_storage_path and not self.dry_run:
                    try:
                        deleted = await self.storage_service.delete_wiki_run(
                            UUID(wiki_id),
                            UploadType(upload_type),
                            UUID(user_id) if user_id else None,
                            UUID(project_id) if project_id else None,
                            run_id,
                        )
                        if deleted:
                            self.stats.storage_paths_deleted.append(f"Wiki: {wiki_storage_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete wiki storage {wiki_storage_path}: {e}")

            # Database deletions
            try:
                # 1. Delete query runs associated with this indexing run
                query_runs_deleted = await self.delete_query_runs(run_id)
                self.stats.query_runs_deleted += query_runs_deleted

                # 2. Delete indexing_run_documents entries
                run_docs_deleted = await self.delete_indexing_run_documents(run_id)
                self.stats.indexing_run_documents_deleted += run_docs_deleted

                # 3. Delete all associated documents and their chunks
                docs_deleted = await self.delete_documents_and_chunks(documents)
                self.stats.documents_deleted += docs_deleted

                # 4. Check and delete project if this was its last indexing run (only for user_project uploads)
                if upload_type == UploadType.USER_PROJECT.value and project_id:
                    project_deleted = await self.check_and_delete_project(
                        UUID(project_id), UUID(user_id) if user_id else None
                    )
                else:
                    logger.info(f"Skipping project deletion for upload_type={upload_type}")

                # 5. Delete the indexing run (this will CASCADE to wiki_generation_runs)
                if not self.dry_run:
                    # First check if the indexing run still exists
                    check_result = self.supabase.table("indexing_runs").select("id").eq("id", str(run_id)).execute()

                    if check_result.data:
                        # Run exists, try to delete it
                        result = self.supabase.table("indexing_runs").delete().eq("id", str(run_id)).execute()
                        self.stats.indexing_runs_deleted += 1
                        logger.info(f"Deleted indexing run {run_id}")
                    else:
                        # Run was already deleted by CASCADE or doesn't exist
                        self.stats.indexing_runs_deleted += 1
                        logger.info(f"Indexing run {run_id} was already deleted (likely by CASCADE)")
                else:
                    self.stats.indexing_runs_deleted += 1
                    logger.info(f"[DRY RUN] Would delete indexing run {run_id}")

                # Count wiki runs that were deleted via CASCADE
                self.stats.wiki_runs_deleted += len(wiki_runs)

                logger.info(f"Successfully processed indexing run {run_id} and associated data")
                return True

            except Exception as e:
                logger.error(f"Failed to delete indexing run {run_id} from database: {e}")
                self.stats.add_failure(f"Database deletion {run_id}", str(e))
                return False

        except Exception as e:
            logger.error(f"Failed to process indexing run {run_id}: {e}")
            self.stats.add_failure(f"Processing run {run_id}", str(e))
            return False

    async def cleanup_manual_list(self) -> bool:
        """Clean up manually specified indexing runs."""
        if not INDEXING_RUNS_TO_DELETE:
            logger.info("No manual indexing runs specified for deletion")
            return True

        logger.info(f"Processing {len(INDEXING_RUNS_TO_DELETE)} manually specified runs")

        success_count = 0
        for run_id_str in INDEXING_RUNS_TO_DELETE:
            try:
                run_id = UUID(run_id_str)
                success = await self.delete_indexing_run(run_id)
                if success:
                    success_count += 1
            except ValueError:
                logger.error(f"Invalid UUID format: {run_id_str}")
                self.stats.add_failure(f"Invalid UUID {run_id_str}", "Invalid format")

        logger.info(f"Processed {success_count}/{len(INDEXING_RUNS_TO_DELETE)} runs successfully")
        return success_count == len(INDEXING_RUNS_TO_DELETE)

    async def cleanup_oldest_runs(self, count: int) -> bool:
        """Clean up the oldest N indexing runs."""
        logger.info(f"Getting oldest {count} indexing runs")

        oldest_runs = await self.get_oldest_indexing_runs(count)
        if not oldest_runs:
            logger.info("No indexing runs found")
            return True

        logger.info(f"Found {len(oldest_runs)} runs to process")

        # Show preview
        logger.info("Runs to be deleted:")
        for i, run in enumerate(oldest_runs):
            logger.info(f"  {i + 1}. {run['id']} (started: {run['started_at']}, type: {run['upload_type']})")

        success_count = 0
        for run in oldest_runs:
            try:
                run_id = UUID(run["id"])
                success = await self.delete_indexing_run(run_id)
                if success:
                    success_count += 1
            except Exception as e:
                logger.error(f"Failed to process run {run['id']}: {e}")
                self.stats.add_failure(f"Processing run {run['id']}", str(e))

        logger.info(f"Processed {success_count}/{len(oldest_runs)} runs successfully")
        return success_count == len(oldest_runs)


def confirm_operation(operation_desc: str) -> bool:
    """Get user confirmation for destructive operations."""
    print(f"\nWARNING: {operation_desc}")
    print("This operation is PERMANENT and cannot be undone!")

    response = input("Type 'DELETE' to confirm, or anything else to cancel: ").strip()
    return response == "DELETE"


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Admin cleanup for ConstructionRAG indexing runs")
    parser.add_argument(
        "--dry-run", action="store_true", default=True, help="Show what would be deleted without executing (default)"
    )
    parser.add_argument("--confirm", action="store_true", help="Actually execute deletions (overrides --dry-run)")
    parser.add_argument("--oldest", type=int, help="Delete the oldest N indexing runs")

    args = parser.parse_args()

    # Determine if this is a dry run
    dry_run = not args.confirm

    if dry_run:
        print("=== DRY RUN MODE ===")
        print("This will show what would be deleted without actually deleting anything.")
        print("Use --confirm to execute actual deletions.")
        print()

    # Initialize cleanup service
    cleanup = AdminCleanup(dry_run=dry_run)

    # Determine operation mode
    if args.oldest:
        operation_desc = f"delete the oldest {args.oldest} indexing runs and all associated data"
        if not dry_run and not confirm_operation(operation_desc):
            print("Operation cancelled.")
            return

        success = await cleanup.cleanup_oldest_runs(args.oldest)
    else:
        operation_desc = f"delete {len(INDEXING_RUNS_TO_DELETE)} manually specified indexing runs"
        if not dry_run and INDEXING_RUNS_TO_DELETE and not confirm_operation(operation_desc):
            print("Operation cancelled.")
            return

        success = await cleanup.cleanup_manual_list()

    # Print summary
    print(cleanup.stats.get_summary())

    if success:
        print("✅ Cleanup completed successfully!")
    else:
        print("❌ Cleanup completed with errors. Check the log for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
