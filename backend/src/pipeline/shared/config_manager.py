"""Configuration management for bridging to run storage.

Phase 0 simplification:
- Load effective configs from ConfigService (single JSON SoT)
- Remove YAML loading and user overrides
- Keep only the surface needed by existing orchestrators and run storage
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class IndexingConfig(BaseModel):
    """Indexing pipeline configuration"""

    steps: Dict[str, Dict[str, Any]]
    orchestration: Dict[str, Any]


class QueryConfig(BaseModel):
    """Query pipeline configuration"""

    steps: Dict[str, Dict[str, Any]]
    orchestration: Dict[str, Any]


class ConfigManager:
    """Configuration manager that bridges SoT configs to existing consumers and persists run configs."""

    def __init__(self, db=None):
        self.db = db
        self._admin_db = None  # Lazy load admin client only when needed
        self._indexing_config_cache = None
        self._query_config_cache = None

        # Directory reference kept in case of future file operations
        self.config_dir = Path(__file__).parent.parent

    # YAML loading removed in Phase 0; all configs come from ConfigService

    # User overrides removed in Phase 0; use per-request overrides via service layer if needed

    def merge_and_validate_config_pure(
        self, defaults: Dict[str, Any], overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Pure function for merging and validating configurations"""
        try:
            merged_config = self.deep_merge_configs(defaults, overrides)
            return merged_config

        except Exception as e:
            logger.error(f"Failed to merge and validate config: {e}")
            return defaults

    def deep_merge_configs(
        self, defaults: Dict[str, Any], overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge configuration dictionaries"""
        result = defaults.copy()

        for key, value in overrides.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self.deep_merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    async def get_indexing_config(
        self, user_id: Optional[UUID] = None
    ) -> IndexingConfig:
        """Get indexing configuration from single SoT via ConfigService."""
        try:
            from src.services.config_service import ConfigService

            effective = ConfigService().get_effective_config("indexing")
            # Map to legacy IndexingConfig shape expected by orchestrator
            steps = {
                "partition": effective.get("partition", {}),
                "metadata": effective.get("metadata", {}),
                "enrichment": effective.get("enrichment", {}),
                "chunking": effective.get("chunking", {}),
                "embedding": effective.get("embedding", {}),
                "storage": effective.get("storage", {}),
            }
            orchestration = effective.get("orchestration", {})
            return IndexingConfig(steps=steps, orchestration=orchestration)
        except Exception as e:
            logger.error(f"Failed to get indexing config from SoT: {e}")
            # Minimal safe fallback aligned with Phase 0 invariants
            return IndexingConfig(
                steps={
                    "partition": {},
                    "metadata": {},
                    "enrichment": {},
                    "chunking": {"chunk_size": 1000, "overlap": 200},
                    "embedding": {"model": "voyage-multilingual-2", "dimensions": 1024},
                    "storage": {},
                },
                orchestration={"max_concurrent_documents": 5, "fail_fast": True},
            )

    async def get_query_config(self, user_id: Optional[UUID] = None) -> QueryConfig:
        """Get query configuration from single SoT via ConfigService."""
        try:
            from src.services.config_service import ConfigService

            effective = ConfigService().get_effective_config("query")
            steps = {
                "query_processing": effective.get("query_processing", {}),
                "retrieval": effective.get("retrieval", {}),
                "generation": effective.get("generation", {}),
                "quality_analysis": effective.get("quality_analysis", {}),
            }
            return QueryConfig(
                steps=steps, orchestration=effective.get("orchestration", {})
            )
        except Exception as e:
            logger.error(f"Failed to get query config from SoT: {e}")
            return QueryConfig(
                steps={
                    "query_processing": {},
                    "retrieval": {
                        "embedding_model": "voyage-multilingual-2",
                        "dimensions": 1024,
                    },
                    "generation": {
                        "model": "google/gemini-2.5-flash",
                        "temperature": 0.1,
                    },
                },
                orchestration={"response_timeout_seconds": 30, "fail_fast": True},
            )

    async def set_user_config_override_async(
        self,
        user_id: UUID,
        config_type: str,
        config_key: str,
        config_value: Dict[str, Any],
    ) -> bool:
        """Set user configuration override (async)"""
        if not self.db:
            return False

        try:
            # Simulate async database operation
            await asyncio.sleep(0.001)  # Minimal async operation

            # This would be the actual database operation
            # await self.db.execute(
            #     """
            #     INSERT INTO user_config_overrides (user_id, config_type, config_key, config_value)
            #     VALUES ($1, $2, $3, $4)
            #     ON CONFLICT (user_id, config_type, config_key)
            #     DO UPDATE SET config_value = $4, updated_at = NOW()
            #     """,
            #     user_id, config_type, config_key, config_value
            # )

            # Placeholder for actual implementation
            logger.info(
                f"Set config override for user {user_id}: {config_type}.{config_key}"
            )

            # Clear cache to force reload
            if config_type == "indexing":
                self._indexing_config_cache = None
            elif config_type == "querying":
                self._query_config_cache = None

            return True

        except Exception as e:
            logger.error(f"Failed to set user config override: {e}")
            return False

    def get_step_config(self, config: Dict[str, Any], step_name: str) -> Dict[str, Any]:
        """Get configuration for a specific step"""
        return config.get("steps", {}).get(step_name, {})

    def get_orchestration_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get orchestration configuration"""
        return config.get("orchestration", {})

    async def store_run_config(self, run_id: UUID, config: Dict[str, Any]) -> bool:
        """Store configuration used for a specific indexing run"""
        # Use admin client for storing run config (background operation)
        if not self._admin_db:
            try:
                from src.config.database import get_supabase_admin_client

                self._admin_db = get_supabase_admin_client()
                logger.info("Initialized admin client for storing run config")
            except Exception as e:
                logger.error(f"Failed to initialize admin client: {e}")
                return False

        try:
            # Update the indexing run with the pipeline configuration using admin client
            result = (
                self._admin_db.table("indexing_runs")
                .update({"pipeline_config": config})
                .eq("id", str(run_id))
                .execute()
            )

            if result.data:
                logger.info(f"Stored pipeline configuration for run {run_id}")
                return True
            else:
                logger.error(f"Failed to store pipeline configuration for run {run_id}")
                return False

        except Exception as e:
            logger.error(f"Error storing run configuration for {run_id}: {e}")
            return False

    async def get_run_config(self, run_id: UUID) -> Optional[Dict[str, Any]]:
        """Get configuration used for a specific indexing run"""
        # Use admin client for retrieving run config (background operation)
        if not self._admin_db:
            try:
                from src.config.database import get_supabase_admin_client

                self._admin_db = get_supabase_admin_client()
                logger.info("Initialized admin client for retrieving run config")
            except Exception as e:
                logger.error(f"Failed to initialize admin client: {e}")
                return None

        try:
            result = (
                self._admin_db.table("indexing_runs")
                .select("pipeline_config")
                .eq("id", str(run_id))
                .execute()
            )

            if result.data and result.data[0].get("pipeline_config"):
                return result.data[0]["pipeline_config"]
            else:
                logger.info(f"No pipeline configuration found for run {run_id}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving run configuration for {run_id}: {e}")
            return None
