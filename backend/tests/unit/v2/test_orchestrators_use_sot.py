import pytest

import os
from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
from src.services.config_service import ConfigService
import src.config.settings as settings_mod


def test_query_orchestrator_uses_sot_generation_and_retrieval(monkeypatch):
    # Prevent Supabase admin client requirement by setting minimal env (if code checks env during imports)
    monkeypatch.setenv("SUPABASE_URL", "http://localhost")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    # Reset settings singleton so env vars are picked up in this test
    monkeypatch.setattr(settings_mod, "_settings", None, raising=False)
    eff = ConfigService().get_effective_config("query")
    qp = QueryPipelineOrchestrator()

    # Asserts on internal resolved config
    assert qp.config["generation"]["model"] == eff["generation"]["model"]
    assert qp.config["retrieval"]["dimensions"] == eff["embedding"]["dimensions"]
    assert qp.config["retrieval"].get("embedding_model") == eff.get(
        "retrieval", {}
    ).get("embedding_model", eff["embedding"]["model"])
