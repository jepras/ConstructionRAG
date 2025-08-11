import os
from io import BytesIO

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY") or not os.getenv("SUPABASE_ANON_KEY"),
    reason="Supabase env not configured",
)
def test_wiki_endpoints_anonymous_email_flow(flat_app_fixture):
    app = flat_app_fixture
    client = TestClient(app)

    # 1) Anonymous email upload via unified endpoint
    files = [("files", ("small.pdf", BytesIO(b"%PDF-1.4\n..."), "application/pdf"))]
    resp = client.post("/api/uploads", files=files, data={"email": "anon@example.com"})
    assert resp.status_code == 200
    run_id = resp.json()["index_run_id"]

    # 2) Create wiki run anonymously for email indexing run
    r = client.post("/api/wiki/runs", params={"index_run_id": run_id})
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "started"
    assert body.get("index_run_id") == run_id

    # 3) List wiki runs for this index run (anon allowed for email)
    r = client.get(f"/api/wiki/runs/{run_id}")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # Note: Further page/content checks require a completed wiki run; out of scope for contract test
