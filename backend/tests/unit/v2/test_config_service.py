from pathlib import Path
import json
import pytest

from src.services.config_service import ConfigService, ConfigServiceError


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
