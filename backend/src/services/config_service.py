from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, ValidationError

from src.config.settings import get_settings


class ConfigServiceError(Exception):
    pass


class ConfigService:
    """Loads, merges, and validates pipeline configuration from a single SoT JSON file.

    - SoT path: repo_root/config/pipeline/pipeline_config.json
    - Secrets are never read from the file (handled via settings)
    - Enforces Phase 0 embedding invariants
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.settings = get_settings()

        if config_path is None:
            # backend/src/services/config_service.py → repo_root is parents[3]
            repo_root = Path(__file__).resolve().parents[3]
            config_path = repo_root / "config" / "pipeline" / "pipeline_config.json"

        self.config_path: Path = config_path
        self._raw_config: Optional[Dict[str, Any]] = None
        self._mtime: Optional[float] = None

    # ---------- Public API ----------
    def get_effective_config(
        self, pipeline: str, overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Return merged config dict for a pipeline: defaults → section → overrides.

        Raises ConfigServiceError on validation or invariant violations.
        """
        cfg = self._load_config()
        merged = self._merge_pipeline(cfg, pipeline, overrides or {})

        # Enforce Phase 0 invariants
        self._enforce_embedding_invariants(merged)

        # Validate against schema (best-effort; schema kept simple for Phase 0)
        self._validate_shape(merged)

        return merged

    def validate_startup(self) -> None:
        """Validate critical configuration and environment at app startup.

        - SoT file present and valid
        - Embedding invariants
        - Critical secrets present in non-development environments
        """
        # Load once to trigger file presence and JSON validity
        _ = self._load_config()
        _ = self.get_effective_config("indexing")
        _ = self.get_effective_config("query")
        _ = self.get_effective_config("wiki")

        # Secrets check (non-development only)
        if self.settings.environment != "development":
            missing: list[str] = []
            if not self.settings.supabase_url:
                missing.append("SUPABASE_URL")
            if not self.settings.supabase_anon_key:
                missing.append("SUPABASE_ANON_KEY")
            if not self.settings.voyage_api_key:
                missing.append("VOYAGE_API_KEY")
            if not self.settings.openrouter_api_key:
                missing.append("OPENROUTER_API_KEY")
            if missing:
                raise ConfigServiceError(
                    f"Missing required environment variables: {', '.join(missing)}"
                )

    # ---------- Internals ----------
    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise ConfigServiceError(
                f"Configuration file not found: {self.config_path}"
            )

        stat = self.config_path.stat()
        if self._raw_config is None or self._mtime != stat.st_mtime:
            try:
                with self.config_path.open("r", encoding="utf-8") as f:
                    self._raw_config = json.load(f)
                self._mtime = stat.st_mtime
            except json.JSONDecodeError as e:
                raise ConfigServiceError(
                    f"Invalid JSON in {self.config_path}: {e}"
                ) from e

        # mypy: _raw_config is set if we didn't raise
        return dict(self._raw_config)  # shallow copy

    @staticmethod
    def _deep_merge(base: Dict[str, Any], other: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(base)
        for k, v in other.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = ConfigService._deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    def _merge_pipeline(
        self, cfg: Dict[str, Any], pipeline: str, overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        defaults = cfg.get("defaults", {})
        section = cfg.get(pipeline, {})
        merged = self._deep_merge(defaults, section)
        if overrides:
            merged = self._deep_merge(merged, overrides)
        return merged

    @staticmethod
    def _enforce_embedding_invariants(effective: Dict[str, Any]) -> None:
        embedding = effective.get("embedding", {})
        model = embedding.get("model")
        dims = embedding.get("dimensions")
        if model != "voyage-multilingual-2" or dims != 1024:
            raise ConfigServiceError(
                "Embedding invariants violated: require voyage-multilingual-2 with 1024 dimensions"
            )

    @staticmethod
    def _validate_shape(effective: Dict[str, Any]) -> None:
        """Best-effort shape validation to catch obvious mistakes in Phase 0.

        Avoids tight coupling to step internals.
        """
        required_top = ["chunking", "embedding", "retrieval", "generation"]
        for k in required_top:
            if k not in effective:
                raise ConfigServiceError(
                    f"Missing required section in effective config: '{k}'"
                )
