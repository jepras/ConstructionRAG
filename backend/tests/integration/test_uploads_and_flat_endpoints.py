import os
from io import BytesIO

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="Supabase env not configured",
)
def test_anonymous_email_upload_and_access(flat_app_fixture):
    app = flat_app_fixture
    client = TestClient(app)

    # Upload via unified endpoint
    files = [("files", ("small.pdf", BytesIO(b"%PDF-1.4\n..."), "application/pdf"))]
    resp = client.post("/api/uploads", files=files, data={"email": "anon@example.com"})
    assert resp.status_code == 200
    data = resp.json()
    run_id = data["index_run_id"]
    assert run_id
    assert data["document_count"] >= 1

    # Anonymous can read run details for email type
    r = client.get(f"/api/indexing-runs/{run_id}")
    assert r.status_code == 200
    run = r.json()
    assert run["upload_type"] == "email"

    # Anonymous can list documents for this run
    r = client.get(f"/api/documents?index_run_id={run_id}")
    assert r.status_code == 200
    docs_list = r.json()
    assert isinstance(docs_list.get("documents"), list)
    if docs_list["documents"]:
        doc_id = docs_list["documents"][0]["id"]
        r = client.get(f"/api/documents/{doc_id}?index_run_id={run_id}")
        assert r.status_code == 200


@pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY") or not os.getenv("SUPABASE_ANON_KEY"),
    reason="Supabase env not configured",
)
def test_flat_progress_endpoint_for_email_run(flat_app_fixture):
    app = flat_app_fixture
    client = TestClient(app)

    # Setup: create a minimal email upload
    files = [("files", ("small.pdf", BytesIO(b"%PDF-1.4\n..."), "application/pdf"))]
    resp = client.post("/api/uploads", files=files, data={"email": "anon@example.com"})
    assert resp.status_code == 200
    run_id = resp.json()["index_run_id"]

    # Anonymous progress for email runs is allowed
    r = client.get(f"/api/indexing-runs/{run_id}/progress")
    assert r.status_code in {200, 404}  # May be 404 early before any progress is recorded
