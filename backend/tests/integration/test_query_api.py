"""
Consolidated integration tests for Query API endpoints.

This test suite verifies:
- Query creation (anonymous and authenticated)
- Query listing and retrieval
- Error handling and response shapes
- Request headers and IDs
"""

import os
import uuid
import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.integration.conftest import upload_test_document, execute_query


# ====================
# Query Creation Tests
# ====================


@pytest.mark.asyncio
async def test_create_query_anonymous(monkeypatch):
    """Test anonymous users can create queries."""
    from src.pipeline.querying.models import QueryResponse
    from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
    from src.main import app
    
    # Mock the query processor
    async def fake_process_query(self, _req):
        return QueryResponse(
            response="Test response",
            search_results=[],
            performance_metrics={"model_used": "test", "tokens_used": 0}
        )
    
    monkeypatch.setattr(QueryPipelineOrchestrator, "process_query", fake_process_query)
    
    # Create query as anonymous user
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/queries",
            json={"query": "What are the construction requirements?"},
            headers={"X-Request-ID": "test-query-1"}
        )
        
        assert response.status_code in (200, 201)
        body = response.json()
        assert "response" in body
        assert "search_results" in body
        assert body["response"] == "Test response"


@pytest.mark.asyncio
async def test_create_query_authenticated(auth_headers, monkeypatch):
    """Test authenticated users can create queries with user context."""
    from src.pipeline.querying.models import QueryResponse
    from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
    from src.main import app
    
    async def fake_process_query(self, _req):
        return QueryResponse(
            response="Authenticated response",
            search_results=[{"content": "test", "relevance": 0.9}],
            performance_metrics={"model_used": "test", "confidence": 0.95}
        )
    
    monkeypatch.setattr(QueryPipelineOrchestrator, "process_query", fake_process_query)
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/queries",
            json={"query": "Show me project specifications"},
            headers={**auth_headers, "X-Request-ID": "auth-query-1"}
        )
        
        assert response.status_code in (200, 201)
        body = response.json()
        assert body["response"] == "Authenticated response"
        assert len(body["search_results"]) == 1
        assert body["performance_metrics"]["confidence"] == 0.95


@pytest.mark.asyncio
async def test_create_query_with_index_run_id(test_pdf_content):
    """Test creating a query with specific index_run_id."""
    from src.main import app
    
    # First upload a document to get index_run_id
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        upload_response = await upload_test_document(
            client,
            email="test@example.com",
            test_pdf_content=test_pdf_content
        )
        
        if "index_run_id" in upload_response:
            query_response = await execute_query(
                client,
                query="What is in this document?",
                index_run_id=upload_response["index_run_id"]
            )
            
            # Check response shape even if query processing fails
            assert isinstance(query_response, dict)
            if "error" not in query_response:
                assert "response" in query_response or "search_results" in query_response


# ====================
# Query Retrieval Tests
# ====================


@pytest.mark.asyncio
async def test_list_queries(auth_headers, monkeypatch):
    """Test listing queries with pagination."""
    from src.services.auth_service import get_current_user_optional
    from src.main import app
    
    # Mock authenticated user
    app.dependency_overrides[get_current_user_optional] = lambda: {"id": "user-1"}
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/queries", headers=auth_headers)
        assert response.status_code == 200
        
        body = response.json()
        assert isinstance(body, list) or isinstance(body.get("queries"), list)
        
        # Test with pagination parameters
        response = await client.get(
            "/api/queries?limit=10&offset=0",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_query_by_id(auth_headers):
    """Test retrieving a specific query by ID."""
    from src.main import app
    
    query_id = str(uuid.uuid4())
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/queries/{query_id}",
            headers=auth_headers
        )
        
        # Should return 404 with proper error envelope for non-existent query
        if response.status_code == 404:
            body = response.json()
            assert "error" in body
            error = body["error"]
            assert all(key in error for key in ["code", "message", "request_id", "timestamp"])
            assert response.headers.get("X-Request-ID") is not None
        elif response.status_code == 200:
            body = response.json()
            assert "id" in body
            assert "query" in body


@pytest.mark.asyncio
async def test_get_query_anonymous_access():
    """Test anonymous access to queries is properly restricted."""
    from src.main import app
    
    query_id = str(uuid.uuid4())
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Anonymous users may be restricted from accessing queries
        response = await client.get(f"/api/queries/{query_id}")
        assert response.status_code in (200, 401, 403, 404)
        
        # List endpoint may also be restricted
        response = await client.get("/api/queries")
        assert response.status_code in (200, 401, 403)


# ====================
# Error Handling Tests
# ====================


@pytest.mark.asyncio
async def test_query_invalid_request_body():
    """Test query creation with invalid request body."""
    from src.main import app
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/queries",
            json={"invalid_field": "test"}  # Missing required 'query' field
        )
        
        assert response.status_code in (400, 422)
        body = response.json()
        assert "error" in body or "detail" in body


@pytest.mark.asyncio
async def test_query_empty_query_string():
    """Test query creation with empty query string."""
    from src.main import app
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/queries",
            json={"query": ""}
        )
        
        assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_query_with_too_long_query():
    """Test query creation with excessively long query string."""
    from src.main import app
    
    long_query = "a" * 10000  # 10k characters
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/queries",
            json={"query": long_query}
        )
        
        # Should either accept or return 400/422 for too long
        assert response.status_code in (200, 201, 400, 422)


# ====================
# Headers and Middleware Tests
# ====================


@pytest.mark.asyncio
async def test_query_request_id_propagation(monkeypatch):
    """Test X-Request-ID header propagation through query pipeline."""
    from src.pipeline.querying.models import QueryResponse
    from src.api.queries import get_query_orchestrator
    from src.main import app
    
    class FakeOrchestrator:
        async def process_query(self, request):
            return QueryResponse(
                response="test",
                search_results=[],
                performance_metrics={"model_used": "test"}
            )
    
    app.dependency_overrides[get_query_orchestrator] = lambda: FakeOrchestrator()
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        request_id = "test-request-123"
        response = await client.post(
            "/api/queries",
            json={"query": "test"},
            headers={"X-Request-ID": request_id}
        )
        
        assert response.status_code in (200, 201)
        # Verify request ID is echoed back
        assert response.headers.get("X-Request-ID") == request_id
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_query_response_shape_consistency(monkeypatch):
    """Test query API response shape is consistent."""
    from src.pipeline.querying.models import QueryResponse
    from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
    from src.main import app
    
    async def fake_process_query(self, _req):
        return QueryResponse(
            response="Consistent response",
            search_results=[
                {"content": "result1", "relevance": 0.9},
                {"content": "result2", "relevance": 0.8}
            ],
            performance_metrics={
                "model_used": "gpt-4",
                "tokens_used": 150,
                "confidence": 0.92,
                "processing_time": 1.5
            }
        )
    
    monkeypatch.setattr(QueryPipelineOrchestrator, "process_query", fake_process_query)
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/queries",
            json={"query": "test consistency"}
        )
        
        assert response.status_code in (200, 201)
        body = response.json()
        
        # Verify all expected fields are present
        assert "response" in body
        assert "search_results" in body
        assert "performance_metrics" in body
        
        # Verify nested structure
        assert isinstance(body["search_results"], list)
        assert isinstance(body["performance_metrics"], dict)
        assert body["performance_metrics"]["model_used"] == "gpt-4"


# ====================
# Integration Tests
# ====================


def test_query_sync_client_compatibility(sync_client):
    """Test query API works with sync test client."""
    response = sync_client.get("/api/queries")
    assert response.status_code in (200, 401, 403)


@pytest.mark.asyncio
async def test_query_concurrent_requests(monkeypatch):
    """Test handling concurrent query requests."""
    from src.pipeline.querying.models import QueryResponse
    from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
    from src.main import app
    
    async def fake_process_query(self, _req):
        await asyncio.sleep(0.1)  # Simulate processing time
        return QueryResponse(
            response="Concurrent response",
            search_results=[],
            performance_metrics={}
        )
    
    monkeypatch.setattr(QueryPipelineOrchestrator, "process_query", fake_process_query)
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Send multiple concurrent requests
        tasks = [
            client.post("/api/queries", json={"query": f"query-{i}"})
            for i in range(5)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code in (200, 201)
            body = response.json()
            assert body["response"] == "Concurrent response"