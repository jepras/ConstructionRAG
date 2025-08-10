"""Configuration management system with async YAML loading and user overrides."""

import yaml
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from uuid import UUID
import logging
from pydantic import BaseModel, ValidationError

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
    """Configuration manager with async operations and user overrides"""

    def __init__(self, db=None):
        self.db = db
        self._admin_db = None  # Lazy load admin client only when needed
        self._indexing_config_cache = None
        self._query_config_cache = None

        # Get the directory where this config manager is located
        self.config_dir = Path(__file__).parent.parent

    async def load_yaml_async(self, config_path: str) -> Dict[str, Any]:
        """Async YAML file loading"""
        try:
            # Simulate async file reading
            await asyncio.sleep(0.001)  # Minimal async operation

            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")

            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            return config_data

        except Exception as e:
            logger.error(f"Failed to load YAML config from {config_path}: {e}")
            raise

    async def get_user_config_overrides_async(
        self, user_id: UUID, config_type: str, db=None
    ) -> Dict[str, Any]:
        """Get user configuration overrides from database (async)"""
        if not db:
            return {}

        try:
            # Simulate async database query
            await asyncio.sleep(0.001)  # Minimal async operation

            # This would be the actual database query
            # result = await db.execute(
            #     "SELECT config_key, config_value FROM user_config_overrides WHERE user_id = $1 AND config_type = $2",
            #     user_id, config_type
            # )

            # Placeholder for actual implementation
            overrides = {}
            logger.info(
                f"Retrieved config overrides for user {user_id}, type {config_type}"
            )

            return overrides

        except Exception as e:
            logger.error(f"Failed to get user config overrides: {e}")
            return {}

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
        """Get indexing configuration with user overrides using async operations"""
        try:
            # 1. Load YAML defaults (async file reading) - use relative path
            config_path = (
                self.config_dir / "indexing" / "config" / "indexing_config.yaml"
            )
            defaults = await self.load_yaml_async(str(config_path))

            # 2. Apply user overrides from database (async database query)
            user_overrides = {}
            if user_id:
                user_overrides = await self.get_user_config_overrides_async(
                    user_id, "indexing", self.db
                )

            # 3. Merge and validate (pure function)
            merged_config = self.merge_and_validate_config_pure(
                defaults, user_overrides
            )

            # 3b. Override embedding settings from central SoT via ConfigService (Phase 0 invariant)
            try:
                from src.services.config_service import ConfigService

                effective = ConfigService().get_effective_config("indexing")
                embedding_from_sot = effective.get("embedding", {})
                merged_config.setdefault("steps", {})
                merged_config["steps"]["embedding"] = {
                    **merged_config["steps"].get("embedding", {}),
                    **embedding_from_sot,
                }
            except Exception:
                # If ConfigService fails here, startup would already fail; keep merged_config as-is
                pass

            # 4. Validate with Pydantic
            return IndexingConfig(**merged_config)

        except Exception as e:
            logger.error(f"Failed to get indexing config: {e}")
            # Return default config on error
            return IndexingConfig(
                steps={
                    "partition": {"ocr_strategy": "auto", "extract_tables": True},
                    "metadata": {"extract_page_structure": True},
                    "enrichment": {"add_context_headers": True},
                    "chunking": {"chunk_size": 1000, "overlap": 200},
                    # Phase 0 invariant fallback
                    "embedding": {"model": "voyage-multilingual-2", "dimensions": 1024},
                    "storage": {"collection_prefix": "construction_docs"},
                },
                orchestration={"max_concurrent_documents": 5, "fail_fast": True},
            )

    async def get_query_config(self, user_id: Optional[UUID] = None) -> QueryConfig:
        """Get query configuration with user overrides using async operations"""
        try:
            # 1. Load YAML defaults (async file reading) - use relative path
            config_path = self.config_dir / "querying" / "config" / "query_config.yaml"
            defaults = await self.load_yaml_async(str(config_path))

            # 2. Apply user overrides from database (async database query)
            user_overrides = {}
            if user_id:
                user_overrides = await self.get_user_config_overrides_async(
                    user_id, "querying", self.db
                )

            # 3. Merge and validate (pure function)
            merged_config = self.merge_and_validate_config_pure(
                defaults, user_overrides
            )

            # 3b. Override retrieval embedding model/dimensions from SoT
            try:
                from src.services.config_service import ConfigService

                effective = ConfigService().get_effective_config("query")
                embedding = effective.get("embedding", {})
                steps = merged_config.setdefault("query_pipeline", {})
                retrieval = steps.setdefault("retrieval", {})
                # Normalize keys
                if embedding.get("model"):
                    retrieval["embedding_model"] = embedding["model"]
                if embedding.get("dimensions"):
                    retrieval["dimensions"] = embedding["dimensions"]
            except Exception:
                pass

            # 4. Validate with Pydantic
            return QueryConfig(**merged_config)

        except Exception as e:
            logger.error(f"Failed to get query config: {e}")
            # Return default config on error
            return QueryConfig(
                steps={
                    "query_processing": {"semantic_expansion_count": 3},
                    # Phase 0 invariant fallback
                    "retrieval": {
                        "embedding_model": "voyage-multilingual-2",
                        "dimensions": 1024,
                        "top_k": 5,
                        "similarity_threshold": 0.7,
                    },
                    "generation": {"model": "gpt-4", "temperature": 0.1},
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
