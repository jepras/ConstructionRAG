# Test Suite Guide

## Quick Start

### Running Tests

```bash
# Run all tests
cd backend && pytest tests/

# Run specific test categories
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only

# Run specific test file
pytest tests/integration/test_query_api.py

# Run specific test function
pytest tests/integration/test_query_api.py::test_create_query_anonymous

# Run with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src
```

## Test Organization

```
tests/
├── conftest.py              # Root test configuration
├── integration/
│   ├── conftest.py         # Shared fixtures and helpers
│   ├── test_query_api.py  # Consolidated query endpoint tests
│   ├── test_access_control.py  # Access control & RLS tests
│   └── test_*.py           # Other integration tests
└── unit/
    └── v2/
        └── test_*.py       # Service and component unit tests
```

## Using Test Helpers

### Available Fixtures

Our `tests/integration/conftest.py` provides reusable fixtures:

#### Client Fixtures
```python
def test_with_sync_client(sync_client):
    """sync_client provides a FastAPI TestClient"""
    response = sync_client.get("/api/health")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_with_async_client():
    """Use httpx.AsyncClient directly for async tests"""
    from src.main import app
    import httpx
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
```

#### Authentication Fixtures
```python
def test_authenticated_request(sync_client, auth_headers):
    """auth_headers provides mock authentication headers"""
    response = sync_client.get("/api/projects", headers=auth_headers)
    assert response.status_code == 200

def test_multiple_users(multiple_test_users):
    """multiple_test_users provides two test user objects"""
    user_a, user_b = multiple_test_users
    # Test cross-user isolation
```

#### File Upload Fixtures
```python
def test_document_upload(sync_client, test_upload_files):
    """test_upload_files provides valid PDF files for testing"""
    response = sync_client.post(
        "/api/uploads",
        files=test_upload_files,
        data={"email": "test@example.com"}
    )
    assert response.status_code == 200

def test_with_custom_pdf(test_pdf_content):
    """test_pdf_content provides raw PDF bytes"""
    # Use test_pdf_content for custom PDF operations
```

#### Mock Database Fixture
```python
def test_with_mock_db(mock_supabase_client):
    """mock_supabase_client provides a fake Supabase client"""
    # Useful for unit tests that need database isolation
    mock_supabase_client.table("projects").insert({"name": "Test"}).execute()
```

### Helper Functions

Import helper functions for common operations:

```python
from tests.integration.conftest import (
    upload_test_document,
    create_test_project,
    create_indexing_run,
    execute_query
)

@pytest.mark.asyncio
async def test_full_flow():
    from src.main import app
    import httpx
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Upload a document
        upload_response = await upload_test_document(
            client,
            email="test@example.com"
        )
        
        # Execute a query on the uploaded document
        query_response = await execute_query(
            client,
            query="What is in this document?",
            index_run_id=upload_response["index_run_id"]
        )
```

## Writing New Tests

### For Claude/AI Assistants

When writing tests for new features:

1. **Check existing test patterns first**:
   ```bash
   # Find similar tests to use as templates
   grep -r "test_.*upload" tests/
   grep -r "test_.*query" tests/
   ```

2. **Use the established fixtures**:
   ```python
   @pytest.mark.asyncio
   async def test_new_feature():
       """Always prefer existing fixtures over creating new ones"""
       from src.main import app
       import httpx
       
       # Use the standard client pattern
       async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
           # Your test logic here
           pass
   ```

3. **Follow naming conventions**:
   - Integration tests: `test_integration/test_{feature}_{aspect}.py`
   - Unit tests: `test_unit/v2/test_{service_name}.py`
   - Test functions: `test_{action}_{condition}_{expected_result}`

4. **Mock external services**:
   ```python
   def test_with_mocked_service(monkeypatch):
       """Mock external API calls to avoid dependencies"""
       async def mock_api_call(*args, **kwargs):
           return {"status": "success"}
       
       monkeypatch.setattr("src.services.external_service.api_call", mock_api_call)
   ```

### Test Categories

#### Unit Tests
- Test individual services/components in isolation
- Mock all dependencies
- Fast execution (<0.1s per test)
- Example: `tests/unit/v2/test_db_service.py`

#### Integration Tests
- Test API endpoints end-to-end
- Test component interactions
- May use real database (with cleanup)
- Example: `tests/integration/test_query_api.py`

## Best Practices

### DO:
- ✅ Use existing fixtures and helpers
- ✅ Test both success and error cases
- ✅ Use descriptive test names
- ✅ Clean up test data after tests
- ✅ Mock external API calls
- ✅ Test edge cases and boundaries

### DON'T:
- ❌ Create duplicate test helpers
- ❌ Use hardcoded UUIDs or IDs
- ❌ Leave test data in the database
- ❌ Test implementation details
- ❌ Make real API calls to external services
- ❌ Write tests longer than 50 lines

## Common Test Patterns

### Testing API Endpoints
```python
@pytest.mark.asyncio
async def test_api_endpoint():
    from src.main import app
    import httpx
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Arrange
        test_data = {"field": "value"}
        
        # Act
        response = await client.post("/api/endpoint", json=test_data)
        
        # Assert
        assert response.status_code == 200
        body = response.json()
        assert "expected_field" in body
```

### Testing with Authentication
```python
def test_protected_endpoint(sync_client, auth_headers):
    response = sync_client.get("/api/protected", headers=auth_headers)
    assert response.status_code == 200
```

### Testing Error Cases
```python
@pytest.mark.asyncio
async def test_invalid_request():
    from src.main import app
    import httpx
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/endpoint", json={"invalid": "data"})
        assert response.status_code in (400, 422)
        assert "error" in response.json()
```

## Environment Variables

Tests require these environment variables (set in `.env`):
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (for some tests)

Tests will skip automatically if required env vars are missing.

## Troubleshooting

### Tests failing with "Supabase env not configured"
Ensure your `.env` file exists and contains the required variables.

### Import errors
Always run tests from the backend directory:
```bash
cd backend && pytest tests/
```

### Async test issues
Ensure async tests are marked with `@pytest.mark.asyncio`

### Database conflicts
Tests use the production database. If tests fail due to conflicts, check for:
- Existing test data not cleaned up
- Concurrent test runs
- RLS policies blocking test operations