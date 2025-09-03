"""
Integration tests for upload and flat API endpoints.

This test suite uses the new test helpers from conftest.py.
"""

import pytest

from tests.integration.conftest import upload_test_document


def test_anonymous_email_upload_and_access(sync_client, test_upload_files):
    """Test anonymous email upload and subsequent data access."""
    # Upload via unified endpoint using helper
    resp = sync_client.post(
        "/api/uploads", 
        files=test_upload_files, 
        data={"email": "anon@example.com"}
    )
    assert resp.status_code == 200
    
    data = resp.json()
    run_id = data["index_run_id"]
    assert run_id
    assert data["document_count"] >= 1

    # Anonymous can read run details for email type
    r = sync_client.get(f"/api/indexing-runs/{run_id}")
    assert r.status_code == 200
    run = r.json()
    assert run["upload_type"] == "email"

    # Anonymous can list documents for this run
    r = sync_client.get(f"/api/documents?index_run_id={run_id}")
    assert r.status_code == 200
    docs_list = r.json()
    assert isinstance(docs_list.get("documents"), list)
    
    if docs_list["documents"]:
        doc_id = docs_list["documents"][0]["id"]
        r = sync_client.get(f"/api/documents/{doc_id}?index_run_id={run_id}")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_flat_progress_endpoint_for_email_run(async_client, test_pdf_content):
    """Test progress endpoint for email-based uploads."""
    # Setup: create a minimal email upload using helper
    upload_response = await upload_test_document(
        async_client,
        email="anon@example.com",
        test_pdf_content=test_pdf_content
    )
    
    if "index_run_id" in upload_response:
        run_id = upload_response["index_run_id"]
        
        # Anonymous progress for email runs is allowed
        r = await async_client.get(f"/api/indexing-runs/{run_id}/progress")
        assert r.status_code in {200, 404}  # May be 404 early before any progress is recorded
