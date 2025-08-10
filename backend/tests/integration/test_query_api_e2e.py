import pytest
import httpx


@pytest.mark.asyncio
async def test_api_query_e2e_headers_and_shape(monkeypatch):
    # Avoid startup validation coupling
    from src.services import config_service

    monkeypatch.setattr(
        config_service.ConfigService, "validate_startup", lambda self: None
    )

    # Set minimal env for Supabase clients used during import
    import os

    os.environ.setdefault("SUPABASE_URL", "http://localhost")
    os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")

    from src.main import app
    from src.pipeline.querying.models import QueryResponse
    from src.api.queries import get_query_orchestrator, get_current_user

    class FakeOrchestrator:
        async def process_query(self, request):
            return QueryResponse(
                response="ok",
                search_results=[],
                performance_metrics={
                    "model_used": "test",
                    "tokens_used": 0,
                    "confidence": 1.0,
                },
            )

    # Override dependencies for auth and orchestrator
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}
    app.dependency_overrides[get_query_orchestrator] = lambda: FakeOrchestrator()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        req_id = "it-works"
        r = await client.post(
            "/api/query/",
            headers={"X-Request-ID": req_id},
            json={"query": "hej"},
        )

        assert r.status_code == 200
        # Header echoed by middleware/handlers
        assert r.headers.get("X-Request-ID") == req_id

        body = r.json()
        # Shape (subset) as defined by QueryResponse
        assert set(["response", "search_results", "performance_metrics"]).issubset(
            body.keys()
        )

    # Cleanup overrides
    app.dependency_overrides.clear()
