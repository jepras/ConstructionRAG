from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

# Skip entire module if Supabase env is not configured to avoid import-time client initialization
if not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY")):
    pytest.skip("Supabase env not configured; skipping contract tests that import app", allow_module_level=True)

from src.main import app

client = TestClient(app)


def test_documents_list_requires_auth():
    project_id = uuid.uuid4()
    r = client.get(f"/api/projects/{project_id}/documents")
    assert r.status_code in (401, 403)


def test_documents_get_requires_auth():
    project_id = uuid.uuid4()
    document_id = uuid.uuid4()
    r = client.get(f"/api/projects/{project_id}/documents/{document_id}")
    assert r.status_code in (401, 403)


def test_pipeline_runs_requires_auth():
    r = client.get("/pipeline/indexing/runs")
    assert r.status_code in (401, 403)


def test_pipeline_run_status_requires_auth():
    run_id = uuid.uuid4()
    r = client.get(f"/pipeline/indexing/runs/{run_id}/status")
    assert r.status_code in (401, 403)


def test_pipeline_run_progress_requires_auth():
    run_id = uuid.uuid4()
    r = client.get(f"/pipeline/indexing/runs/{run_id}/progress")
    assert r.status_code in (401, 403)
