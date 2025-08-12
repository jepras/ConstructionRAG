import os

import httpx
import pytest


@pytest.mark.asyncio
async def test_live_query_on_indexing_run():
    """Live integration: exercise POST /api/queries against a known indexing_run.

    Requires valid Supabase and model provider env in backend/.env and existing data for the run.
    Set INDEXING_RUN_ID in environment to override the default run id.
    """

    run_id = os.getenv(
        "INDEXING_RUN_ID",
        "0f1069d6-bca5-4f62-97e9-2f624cd07cfd",  # previous verified email/public run
    )

    assert run_id, "INDEXING_RUN_ID must be provided or default must be valid for the environment"

    # Import app after env is loaded
    from src.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/queries",
            json={"query": "hvad hedder projektet?", "indexing_run_id": run_id},
            headers={"X-Request-ID": "live-query-test"},
            timeout=60.0,
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Basic shape assertions
        assert "response" in body
        assert "search_results" in body
        assert isinstance(body["search_results"], list)
        # For this public/email run we expect zero or more results, but not an error envelope
        assert "error" not in body
