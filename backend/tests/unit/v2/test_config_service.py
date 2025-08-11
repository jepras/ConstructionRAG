from __future__ import annotations

import os

import pytest

from src.services.config_service import ConfigService, ConfigServiceError


def test_config_service_loads_effective_indexing_config(monkeypatch):
    svc = ConfigService()
    cfg = svc.get_effective_config("indexing")
    assert cfg["embedding"]["model"] == "voyage-multilingual-2"
    assert cfg["embedding"]["dimensions"] == 1024


def test_config_service_enforces_embedding_invariants(monkeypatch, tmp_path):
    bad = tmp_path / "pipeline_config.json"
    bad.write_text(
        '{"defaults": {"embedding": {"model": "X", "dimensions": 1536}}, "indexing": {}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("PIPELINE_CONFIG_PATH", str(bad))
    try:
        with pytest.raises(ConfigServiceError):
            ConfigService().get_effective_config("indexing")
    finally:
        os.environ.pop("PIPELINE_CONFIG_PATH", None)


import json
from pathlib import Path


def test_effective_configs_and_invariants_from_sot():
    svc = ConfigService()

    idx = svc.get_effective_config("indexing")
    qry = svc.get_effective_config("query")
    wiki = svc.get_effective_config("wiki")

    # Embedding invariants enforced
    assert idx["embedding"]["model"] == "voyage-multilingual-2"
    assert idx["embedding"]["dimensions"] == 1024

    # Retrieval should align to embedding dims/model
    assert qry["retrieval"]["dimensions"] == 1024
    assert (
        qry["retrieval"].get("embedding_model") == "voyage-multilingual-2"
        or qry["embedding"]["model"] == "voyage-multilingual-2"
    )

    # Minimal shape presence
    for section in ("chunking", "embedding", "retrieval", "generation"):
        assert section in idx
        assert section in qry
    assert "generation" in wiki


def test_startup_validation_requires_generation_settings(tmp_path: Path):
    # Create a minimal invalid SoT missing query.generation.model
    bad = {
        "defaults": {
            "chunking": {"chunk_size": 1000, "overlap": 200},
            "embedding": {"model": "voyage-multilingual-2", "dimensions": 1024},
            "retrieval": {"top_k": 5},
            "generation": {"model": "x", "temperature": 0.1},
        },
        "indexing": {},
        "query": {
            # missing generation.model and fallback_models
            "retrieval": {
                "embedding_model": "voyage-multilingual-2",
                "dimensions": 1024,
            }
        },
        "wiki": {"generation": {"model": "some-model", "temperature": 0.2}},
    }
    cfg_path = tmp_path / "pipeline_config.json"
    cfg_path.write_text(json.dumps(bad), encoding="utf-8")

    svc = ConfigService(config_path=cfg_path)

    with pytest.raises(ConfigServiceError):
        svc.validate_startup()
