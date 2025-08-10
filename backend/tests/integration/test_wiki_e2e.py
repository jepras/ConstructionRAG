import types
import pytest
from datetime import datetime

from src.pipeline.wiki_generation.orchestrator import WikiGenerationOrchestrator
from src.models import StepResult


class _DummyStep:
    def __init__(self, data):
        self._data = data

    async def execute(self, _input):
        return StepResult(
            step="dummy",
            status="completed",
            duration_seconds=0.01,
            data=self._data,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )


@pytest.mark.asyncio
async def test_wiki_pipeline_e2e_smoke(monkeypatch):
    # Minimal env for Supabase clients
    import os

    os.environ.setdefault("SUPABASE_URL", "http://localhost")
    os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
    orch = WikiGenerationOrchestrator(config={})

    # Monkeypatch internal IO-heavy methods
    async def _fake_create_wiki_run(index_run_id, user_id, project_id, upload_type):
        return types.SimpleNamespace(id="test-wiki-run")

    async def _fake_update_status(_id, _status, _msg=""):
        return None

    async def _fake_get_wiki_run(_id):
        # Return a simple object; the test only asserts the object is returned
        return types.SimpleNamespace(id=_id, status="completed")

    async def _fake_save(*args, **kwargs):
        return None

    monkeypatch.setattr(orch, "_create_wiki_run", _fake_create_wiki_run)
    monkeypatch.setattr(orch, "_update_wiki_run_status", _fake_update_status)
    monkeypatch.setattr(orch, "_get_wiki_run", _fake_get_wiki_run)
    monkeypatch.setattr(orch, "_save_wiki_to_storage", _fake_save)

    # Dummy step outputs to satisfy adapters
    orch.steps = {
        "metadata_collection": _DummyStep(
            {
                "indexing_run_id": "idx",
                "total_documents": 1,
                "total_chunks": 1,
                "total_pages_analyzed": 1,
                "documents": [{"id": "doc1", "filename": "a.pdf"}],
                "chunks": [
                    {
                        "id": "c1",
                        "document_id": "doc1",
                        "content": "x",
                        "metadata": {"page_number": 1},
                    }
                ],
                "chunks_with_embeddings": [],
                "section_headers_distribution": {},
                "images_processed": 0,
                "tables_processed": 0,
                "document_filenames": ["a.pdf"],
                "document_ids": ["doc1"],
            }
        ),
        "overview_generation": _DummyStep({"project_overview": "Short overview"}),
        "semantic_clustering": _DummyStep({}),
        "structure_generation": _DummyStep({"wiki_structure": {}}),
        "page_content_retrieval": _DummyStep({"page_contents": {}}),
        "markdown_generation": _DummyStep({"generated_pages": {}}),
    }

    result = await orch.run_pipeline(index_run_id="idx")
    assert getattr(result, "id", None) == "test-wiki-run"
