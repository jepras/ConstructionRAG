import os
import uuid
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pytest

# Load backend/.env so os.getenv-based skips and clients see Supabase env
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except Exception:
    # If python-dotenv is not installed, proceed; tests that require env will skip
    pass


# ====================
# Environment Checking
# ====================


@pytest.fixture(scope="session", autouse=True)
def check_required_env_vars():
    """Check for required environment variables at session start."""
    required_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        pytest.skip(f"Missing required env vars: {', '.join(missing)}", allow_module_level=True)


@pytest.fixture(scope="session")
def flat_app_fixture():
    # Importing main creates the FastAPI app with routers
    # Skip if env is not configured to avoid startup failures
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"):
        pytest.skip("Supabase env not configured")
    from src.main import app

    return app


# ====================
# Client Fixtures
# ====================


@pytest.fixture
async def async_client(flat_app_fixture):
    """Get async test client for the FastAPI app."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=flat_app_fixture),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def sync_client(flat_app_fixture):
    """Get sync test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    return TestClient(flat_app_fixture)


# ====================
# Authentication Fixtures
# ====================


@pytest.fixture
def test_user():
    """Create a test user object."""
    return {
        "id": str(uuid.uuid4()),
        "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def auth_headers(test_user):
    """Get auth headers for authenticated requests."""
    # In real tests, this would generate a proper JWT token
    # For now, return a mock token that tests can use
    token = f"test-jwt-token-{test_user['id']}"
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def multiple_test_users():
    """Create multiple test users for cross-user testing."""
    return [
        {
            "id": str(uuid.uuid4()),
            "email": f"user1-{uuid.uuid4().hex[:8]}@example.com",
            "created_at": "2024-01-01T00:00:00Z"
        },
        {
            "id": str(uuid.uuid4()),
            "email": f"user2-{uuid.uuid4().hex[:8]}@example.com",
            "created_at": "2024-01-01T00:00:00Z"
        }
    ]


# ====================
# File Upload Fixtures
# ====================


@pytest.fixture
def test_pdf_content():
    """Get minimal valid PDF content for testing."""
    # Minimal valid PDF structure
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
365
%%EOF"""


@pytest.fixture
def test_upload_files(test_pdf_content):
    """Create test PDF files for upload."""
    return [
        ("files", ("test.pdf", BytesIO(test_pdf_content), "application/pdf"))
    ]


@pytest.fixture
def multiple_test_files(test_pdf_content):
    """Create multiple test PDF files for upload."""
    return [
        ("files", (f"test{i}.pdf", BytesIO(test_pdf_content), "application/pdf"))
        for i in range(3)
    ]


# ====================
# Database Mock Fixtures
# ====================


@pytest.fixture
def mock_supabase_client():
    """Provide a properly mocked Supabase client."""
    
    class MockTable:
        def __init__(self, table_name: str, data: Optional[List[Dict]] = None):
            self.table_name = table_name
            self.data = data or []
            self.filters = {}
            self._limit = None
            self._order = None
            
        def select(self, columns: str = "*"):
            return self
            
        def insert(self, data: Dict) -> "MockTable":
            if isinstance(data, list):
                self.data.extend(data)
            else:
                self.data.append(data)
            return self
            
        def update(self, data: Dict) -> "MockTable":
            for item in self.data:
                if all(item.get(k) == v for k, v in self.filters.items()):
                    item.update(data)
            return self
            
        def delete(self) -> "MockTable":
            self.data = [
                item for item in self.data
                if not all(item.get(k) == v for k, v in self.filters.items())
            ]
            return self
            
        def eq(self, column: str, value: Any) -> "MockTable":
            self.filters[column] = value
            return self
            
        def limit(self, count: int) -> "MockTable":
            self._limit = count
            return self
            
        def order(self, column: str, desc: bool = False) -> "MockTable":
            self._order = (column, desc)
            return self
            
        def execute(self) -> SimpleNamespace:
            result = list(self.data)
            
            # Apply filters
            for key, value in self.filters.items():
                result = [r for r in result if r.get(key) == value]
            
            # Apply ordering
            if self._order:
                column, desc = self._order
                result.sort(key=lambda x: x.get(column), reverse=desc)
            
            # Apply limit
            if self._limit:
                result = result[:self._limit]
            
            return SimpleNamespace(data=result)
    
    class MockStorage:
        def __init__(self):
            self.files = {}
            
        def from_(self, bucket: str):
            self.bucket = bucket
            return self
            
        def upload(self, path: str, file_data: bytes, file_options: Optional[Dict] = None):
            self.files[f"{self.bucket}/{path}"] = file_data
            return SimpleNamespace(data={"path": path})
            
        def download(self, path: str):
            return self.files.get(f"{self.bucket}/{path}", b"")
    
    class MockAuth:
        def __init__(self):
            self.user = None
            
        def sign_in_with_password(self, credentials: Dict):
            return SimpleNamespace(user={"id": str(uuid.uuid4()), "email": credentials.get("email")})
            
        def sign_out(self):
            self.user = None
            return SimpleNamespace(data=None)
            
        def get_user(self, token: Optional[str] = None):
            if token and token.startswith("test-jwt-token"):
                return SimpleNamespace(user={"id": token.split("-")[-1]})
            return None
    
    class MockClient:
        def __init__(self):
            self.storage = MockStorage()
            self.auth = MockAuth()
            self._tables = {}
            
        def table(self, name: str) -> MockTable:
            if name not in self._tables:
                self._tables[name] = MockTable(name)
            return self._tables[name]
    
    return MockClient()


# ====================
# Helper Functions
# ====================


async def upload_test_document(
    client: httpx.AsyncClient,
    email: Optional[str] = None,
    auth_headers: Optional[Dict] = None,
    files: Optional[List[Tuple]] = None,
    test_pdf_content: Optional[bytes] = None
) -> Dict:
    """Helper to upload a test document and return the response data."""
    if not files:
        if not test_pdf_content:
            test_pdf_content = b"%PDF-1.4\n..."  # Minimal PDF
        files = [("files", ("test.pdf", BytesIO(test_pdf_content), "application/pdf"))]
    
    data = {"email": email} if email else {}
    headers = auth_headers or {}
    
    resp = await client.post("/api/uploads", files=files, data=data, headers=headers)
    return resp.json() if resp.status_code == 200 else {"error": resp.text, "status": resp.status_code}


async def create_test_project(
    client: httpx.AsyncClient,
    auth_headers: Dict,
    name: Optional[str] = None
) -> Dict:
    """Helper to create a test project."""
    project_data = {
        "name": name or f"Test Project {uuid.uuid4().hex[:8]}",
        "description": "Test project created by test suite"
    }
    
    resp = await client.post("/api/projects", json=project_data, headers=auth_headers)
    return resp.json() if resp.status_code == 200 else {"error": resp.text, "status": resp.status_code}


async def create_indexing_run(
    client: httpx.AsyncClient,
    project_id: str,
    document_ids: List[str],
    auth_headers: Dict
) -> Dict:
    """Helper to create an indexing run."""
    run_data = {
        "project_id": project_id,
        "document_ids": document_ids
    }
    
    resp = await client.post("/api/indexing-runs", json=run_data, headers=auth_headers)
    return resp.json() if resp.status_code == 200 else {"error": resp.text, "status": resp.status_code}


async def execute_query(
    client: httpx.AsyncClient,
    query: str,
    index_run_id: str,
    auth_headers: Optional[Dict] = None
) -> Dict:
    """Helper to execute a query."""
    query_data = {
        "query": query,
        "index_run_id": index_run_id
    }
    
    headers = auth_headers or {}
    resp = await client.post("/api/queries", json=query_data, headers=headers)
    return resp.json() if resp.status_code == 200 else {"error": resp.text, "status": resp.status_code}


# ====================
# Cleanup Fixtures
# ====================


@pytest.fixture
def cleanup_tracker():
    """Track resources for cleanup after tests."""
    resources = {
        "projects": [],
        "indexing_runs": [],
        "documents": [],
        "queries": []
    }
    
    yield resources
    
    # Cleanup would happen here if we had admin access
    # For now, just log what would be cleaned
    if any(resources.values()):
        print(f"Test resources created: {resources}")
