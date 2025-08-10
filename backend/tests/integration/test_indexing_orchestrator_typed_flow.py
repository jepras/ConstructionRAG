import types
import pytest
from uuid import uuid4

from src.pipeline.indexing.orchestrator import IndexingOrchestrator
from src.pipeline.shared.models import DocumentInput, UploadType
from src.models import StepResult


class _DummyStep:
    def __init__(self, name: str, data: dict):
        self._name = name
        self._data = data

    def get_step_name(self):
        return self._name

    async def execute(self, _input):
        return StepResult(
            step=self._name,
            status="completed",
            duration_seconds=0.01,
            data=self._data,
        )

    async def validate_prerequisites_async(self, _):
        return True

    def estimate_duration(self, _):
        return 1


@pytest.mark.asyncio
async def test_indexing_orchestrator_typed_flow(monkeypatch):
    # Minimal env for Supabase clients (avoid real connections)
    import os

    os.environ.setdefault("SUPABASE_URL", "http://localhost")
    os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
    orch = IndexingOrchestrator()

    # Monkeypatch dependencies that hit DB/storage
    async def _fake_store_doc_step_result(*args, **kwargs):
        return None

    async def _fake_update_status(*args, **kwargs):
        return None

    async def _fake_create_run(upload_type=None, project_id=None):
        return types.SimpleNamespace(id=str(uuid4()))

    async def _fake_link_doc_to_run(**kwargs):
        return None

    monkeypatch.setattr(
        orch,
        "pipeline_service",
        types.SimpleNamespace(
            store_document_step_result=_fake_store_doc_step_result,
            update_indexing_run_status=_fake_update_status,
            create_indexing_run=_fake_create_run,
            link_document_to_indexing_run=_fake_link_doc_to_run,
        ),
    )

    # Provide minimal storage service
    monkeypatch.setattr(
        orch,
        "storage_service",
        types.SimpleNamespace(create_storage_structure=lambda **kwargs: None),
    )

    # Bypass config loading
    async def _fake_init_steps(user_id=None):
        orch.steps = [
            _DummyStep(
                "PartitionStep",
                {
                    "text_elements": [],
                    "table_elements": [],
                    "extracted_pages": {},
                    "page_analysis": {},
                    "document_metadata": {},
                    "metadata": {},
                },
            ),
            _DummyStep(
                "MetadataStep",
                {
                    "text_elements": [],
                    "table_elements": [],
                    "extracted_pages": {},
                    "page_analysis": {},
                    "document_metadata": {},
                    "metadata": {},
                    "page_sections": {},
                },
            ),
            _DummyStep(
                "EnrichmentStep",
                {
                    "text_elements": [],
                    "table_elements": [],
                    "extracted_pages": {},
                    "page_analysis": {},
                    "document_metadata": {},
                    "metadata": {},
                    "page_sections": {},
                },
            ),
            _DummyStep(
                "ChunkingStep",
                {"chunks": [], "chunking_metadata": {"total_chunks": 0}},
            ),
        ]

    monkeypatch.setattr(orch, "initialize_steps", _fake_init_steps)

    doc_input = DocumentInput(
        document_id=uuid4(),
        run_id=uuid4(),
        file_path="/tmp/fake.pdf",
        filename="fake.pdf",
        upload_type=UploadType.USER_PROJECT,
        user_id=None,
        project_id=None,
    )

    # Run single-document flow up to before embedding (handled by _process_single_document_steps)
    ok = await orch._process_single_document_steps(
        doc_input, uuid4(), types.SimpleNamespace()
    )
    assert ok is True
