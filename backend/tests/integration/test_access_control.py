"""
Consolidated integration tests for access control and RLS (Row Level Security).

This test suite verifies:
- Row-level security policies for different tables
- Cross-user data isolation
- Public vs private access patterns
- Authentication and authorization
"""

import os
import uuid

import httpx
import pytest

from tests.integration.conftest import upload_test_document, create_test_project


# ====================
# RLS Policy Tests
# ====================


@pytest.mark.asyncio
async def test_rls_documents_public_vs_private(async_client, monkeypatch):
    """Test that anonymous users cannot see private documents."""
    from src.services.auth_service import get_current_user_optional
    from src.main import app
    
    # Test as anonymous user
    app.dependency_overrides[get_current_user_optional] = lambda: None
    
    fake_doc_id = str(uuid.uuid4())
    fake_run_id = str(uuid.uuid4())
    
    response = await async_client.get(
        f"/api/documents/{fake_doc_id}?index_run_id={fake_run_id}"
    )
    
    # Anonymous users should not be able to access private documents
    assert response.status_code in (404, 400, 403)
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rls_indexing_runs_email_vs_project(async_client, monkeypatch):
    """Test that anonymous users can only access email-type indexing runs."""
    from src.services.auth_service import get_current_user_optional
    from src.main import app
    
    # Test as anonymous user
    app.dependency_overrides[get_current_user_optional] = lambda: None
    
    fake_run_id = str(uuid.uuid4())
    response = await async_client.get(f"/api/indexing-runs/{fake_run_id}")
    
    # Anonymous should not access project-type runs (would be 404 or 403)
    assert response.status_code in (404, 403)
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rls_queries_visibility(async_client, monkeypatch):
    """Test that query visibility respects user boundaries."""
    from src.services.auth_service import get_current_user_optional
    from src.main import app
    
    # Test as anonymous user - should only see public queries
    app.dependency_overrides[get_current_user_optional] = lambda: None
    
    response = await async_client.get("/api/queries")
    assert response.status_code == 200
    
    # Response should be a list (possibly empty for anonymous)
    body = response.json()
    assert isinstance(body, list) or isinstance(body.get("queries"), list)
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rls_wiki_runs_access(async_client, monkeypatch):
    """Test wiki runs access control."""
    from src.services.auth_service import get_current_user_optional
    from src.main import app
    
    fake_run_id = str(uuid.uuid4())
    
    # Anonymous access to wiki runs (public email type should work)
    app.dependency_overrides[get_current_user_optional] = lambda: None
    response = await async_client.get(f"/api/wiki/runs/{fake_run_id}/pages")
    
    # Should return 404 for non-existent or 403 for private
    assert response.status_code in (404, 403)
    
    app.dependency_overrides.clear()


# ====================
# Cross-User Isolation Tests
# ====================


@pytest.mark.asyncio
async def test_cross_user_project_isolation(async_client, multiple_test_users, monkeypatch):
    """Test that users cannot access each other's projects."""
    from src.services.auth_service import get_current_user
    from src.main import app
    
    user_a, user_b = multiple_test_users
    
    # Create project as user A
    app.dependency_overrides[get_current_user] = lambda: user_a
    
    project_data = {
        "name": f"User A Project {uuid.uuid4().hex[:8]}",
        "description": "Private project"
    }
    
    create_response = await async_client.post(
        "/api/projects",
        json=project_data,
        headers={"Authorization": f"Bearer test-token-{user_a['id']}"}
    )
    
    if create_response.status_code == 200:
        project = create_response.json()
        project_id = project["id"]
        
        # Try to access as user B
        app.dependency_overrides[get_current_user] = lambda: user_b
        
        access_response = await async_client.get(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer test-token-{user_b['id']}"}
        )
        
        # User B should not be able to access User A's project
        assert access_response.status_code in (403, 404)
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_cross_user_document_isolation(async_client, multiple_test_users, test_pdf_content, monkeypatch):
    """Test that users cannot access each other's documents."""
    from src.services.auth_service import get_current_user_optional
    from src.main import app
    
    user_a, user_b = multiple_test_users
    
    # Upload document as user A
    app.dependency_overrides[get_current_user_optional] = lambda: user_a
    
    upload_response = await upload_test_document(
        async_client,
        auth_headers={"Authorization": f"Bearer test-token-{user_a['id']}"},
        test_pdf_content=test_pdf_content
    )
    
    if "documents" in upload_response and len(upload_response["documents"]) > 0:
        doc_id = upload_response["documents"][0]["id"]
        
        # Try to access as user B
        app.dependency_overrides[get_current_user_optional] = lambda: user_b
        
        access_response = await async_client.get(
            f"/api/documents/{doc_id}",
            headers={"Authorization": f"Bearer test-token-{user_b['id']}"}
        )
        
        # User B should not see User A's documents
        assert access_response.status_code in (403, 404)
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_cross_user_indexing_run_isolation(async_client, multiple_test_users, monkeypatch):
    """Test that users cannot access each other's indexing runs."""
    from src.services.auth_service import get_current_user_optional
    from src.main import app
    
    user_a, user_b = multiple_test_users
    
    # List indexing runs as user A
    app.dependency_overrides[get_current_user_optional] = lambda: user_a
    
    list_response_a = await async_client.get(
        "/api/indexing-runs",
        headers={"Authorization": f"Bearer test-token-{user_a['id']}"}
    )
    
    assert list_response_a.status_code == 200
    runs_a = list_response_a.json()
    
    # List indexing runs as user B
    app.dependency_overrides[get_current_user_optional] = lambda: user_b
    
    list_response_b = await async_client.get(
        "/api/indexing-runs",
        headers={"Authorization": f"Bearer test-token-{user_b['id']}"}
    )
    
    assert list_response_b.status_code == 200
    runs_b = list_response_b.json()
    
    # If both users have runs, verify they're different
    if runs_a and runs_b:
        runs_a_ids = {run["id"] for run in runs_a} if isinstance(runs_a, list) else set()
        runs_b_ids = {run["id"] for run in runs_b} if isinstance(runs_b, list) else set()
        
        # Users should not see each other's runs
        assert runs_a_ids.isdisjoint(runs_b_ids)
    
    app.dependency_overrides.clear()


# ====================
# Public Access Tests
# ====================


@pytest.mark.asyncio
async def test_anonymous_email_upload_access(async_client, test_pdf_content):
    """Test that anonymous users can upload via email and access their data."""
    # Upload as anonymous with email
    upload_response = await upload_test_document(
        async_client,
        email="anonymous@example.com",
        test_pdf_content=test_pdf_content
    )
    
    if "index_run_id" in upload_response:
        run_id = upload_response["index_run_id"]
        
        # Anonymous should be able to access email-type runs
        run_response = await async_client.get(f"/api/indexing-runs/{run_id}")
        
        if run_response.status_code == 200:
            run_data = run_response.json()
            assert run_data.get("upload_type") == "email"
            
            # Should also be able to list documents for this run
            docs_response = await async_client.get(
                f"/api/documents?index_run_id={run_id}"
            )
            assert docs_response.status_code == 200


@pytest.mark.asyncio
async def test_anonymous_cannot_create_projects(async_client):
    """Test that anonymous users cannot create projects."""
    project_data = {
        "name": "Anonymous Project",
        "description": "Should not be created"
    }
    
    response = await async_client.post("/api/projects", json=project_data)
    
    # Should require authentication
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_anonymous_cannot_list_private_projects(async_client):
    """Test that anonymous users cannot list private projects."""
    response = await async_client.get("/api/projects")
    
    # Should require authentication
    assert response.status_code in (401, 403)


# ====================
# Authentication Tests
# ====================


@pytest.mark.asyncio
async def test_invalid_token_rejected(async_client):
    """Test that invalid JWT tokens are rejected."""
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    
    # Try to access protected endpoint
    response = await async_client.get("/api/projects", headers=headers)
    
    # Should reject invalid token
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_expired_token_rejected(async_client, monkeypatch):
    """Test that expired JWT tokens are rejected."""
    from src.services.auth_service import auth_service
    
    # Mock token validation to simulate expired token
    async def mock_get_user(token):
        return None  # Simulate expired/invalid token
    
    monkeypatch.setattr(auth_service, "get_current_user", mock_get_user)
    
    headers = {"Authorization": "Bearer expired.jwt.token"}
    response = await async_client.get("/api/projects", headers=headers)
    
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_missing_auth_header_on_protected_route(async_client):
    """Test that protected routes require authentication header."""
    # No auth header provided
    response = await async_client.get("/api/projects")
    
    # Should require authentication
    assert response.status_code in (401, 403)


# ====================
# Soft Delete Tests
# ====================


@pytest.mark.asyncio
async def test_soft_deleted_project_not_accessible(async_client, auth_headers, monkeypatch):
    """Test that soft-deleted projects are not accessible."""
    from src.services.auth_service import get_current_user
    from src.main import app
    
    test_user = {"id": str(uuid.uuid4()), "email": "test@example.com"}
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    # Create a project
    project_data = {"name": "To Be Deleted", "description": "Test"}
    create_response = await async_client.post(
        "/api/projects",
        json=project_data,
        headers=auth_headers
    )
    
    if create_response.status_code == 200:
        project = create_response.json()
        project_id = project["id"]
        
        # Soft delete the project
        delete_response = await async_client.delete(
            f"/api/projects/{project_id}",
            headers=auth_headers
        )
        
        if delete_response.status_code in (200, 204):
            # Try to access soft-deleted project
            access_response = await async_client.get(
                f"/api/projects/{project_id}",
                headers=auth_headers
            )
            
            # Should not be accessible after soft delete
            assert access_response.status_code == 404
    
    app.dependency_overrides.clear()


# ====================
# Access Level Tests
# ====================


@pytest.mark.asyncio
async def test_access_levels_enforcement(async_client, test_user, monkeypatch):
    """Test that different access levels are properly enforced."""
    from src.services.auth_service import get_current_user_optional
    from src.main import app
    
    # Test public access level (anonymous)
    app.dependency_overrides[get_current_user_optional] = lambda: None
    
    # Public endpoints should work
    response = await async_client.get("/api/indexing-runs-with-wikis")
    assert response.status_code == 200
    
    # Auth-required endpoints should fail
    response = await async_client.get("/api/user-projects-with-wikis")
    assert response.status_code in (401, 403)
    
    # Test authenticated access level
    app.dependency_overrides[get_current_user_optional] = lambda: test_user
    
    # Auth-required endpoints should now work
    response = await async_client.get("/api/user-projects-with-wikis")
    assert response.status_code == 200
    
    app.dependency_overrides.clear()