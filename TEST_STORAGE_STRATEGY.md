# Test Storage Strategy

## Overview
This document outlines how to handle storage during local testing and integration tests for the ConstructionRAG system.

## 🎯 **Test Storage Approach**

### **Separate Test Bucket**
- **Bucket Name**: `pipeline-assets-test`
- **Isolation**: Complete separation from production data
- **Admin Access**: Uses `get_supabase_admin_client()` to bypass auth requirements
- **Auto Cleanup**: Automatic cleanup after tests complete

### **Test Storage Structure**
```
pipeline-assets-test/
├── email-uploads/
│   ├── test-upload-789/
│   │   ├── original.pdf
│   │   ├── generated-page.html
│   │   └── processing/
│   └── ...
├── users/
│   ├── test-user-123/
│   │   ├── projects/
│   │   │   ├── test-project-456/
│   │   │   │   └── index-runs/
│   │   │   │       ├── test-index-run-123/
│   │   │   │       │   ├── pdfs/
│   │   │   │       │   ├── test-document-456/
│   │   │   │       │   └── generated/
│   │   │   │       └── ...
│   │   │   └── ...
│   │   └── ...
│   └── ...
└── ...
```

## 🧪 **Test Storage Service**

### **Key Features**
- **Admin Client**: Bypasses authentication requirements
- **Predefined IDs**: Consistent test user/project/upload IDs
- **Temp File Management**: Automatic cleanup of local temporary files
- **Error Handling**: Comprehensive error handling and logging
- **Storage Analytics**: Usage tracking and statistics

### **Core Methods**
```python
# Email upload testing
await storage.upload_test_email_pdf(pdf_path, upload_id="test-upload-789")

# User project testing
await storage.upload_test_user_pdf(
    pdf_path, 
    user_id="test-user-123",
    project_id="test-project-456",
    index_run_id="test-index-run-123",
    document_id="test-document-456"
)

# Processing output testing
await storage.upload_test_processing_output(data, upload_type="email")

# Markdown generation testing
await storage.create_test_markdown_file(content, "test-summary.md")

# Cleanup
await storage.cleanup_test_data()
```

## 📋 **Test Configuration Class**

### **TestStorageConfig Features**
- **Setup/Teardown**: Automatic setup and cleanup
- **Temp File Tracking**: Tracks all temporary files for cleanup
- **Test Data Tracking**: Keeps track of uploaded test data
- **Convenience Methods**: Simplified methods for common test operations

### **Usage Pattern**
```python
# In test files
config = TestStorageConfig()
await config.setup()

try:
    # Create test PDF
    pdf_path = await config.create_test_pdf("Test content")
    
    # Upload test files
    email_result = await config.upload_test_email_pdf(pdf_path, "test-001")
    user_result = await config.upload_test_user_pdf(pdf_path)
    
    # Create processing outputs
    await config.create_test_processing_output({"test": "data"})
    
    # Create markdown
    await config.create_test_markdown("# Test\n\nContent", "test.md")
    
    # Run your actual tests here...
    
finally:
    await config.teardown()  # Cleanup everything
```

## 🚀 **Running Tests**

### **Test Storage Service**
```bash
# Run the storage service test
cd backend
python test_storage_service.py
```

### **Integration Tests**
```bash
# Run integration tests that use storage
cd backend
python -m pytest tests/integration/ -v
```

### **Individual Test Files**
```python
# In your test files
from src.services.test_storage_service import get_test_storage_service
from tests.test_storage_config import TestStorageConfig

async def test_upload_functionality():
    config = TestStorageConfig()
    await config.setup()
    
    try:
        # Your test logic here
        pdf_path = await config.create_test_pdf("Test content")
        result = await config.upload_test_email_pdf(pdf_path)
        
        # Assertions
        assert result['upload_id'] is not None
        assert result['url'] is not None
        
    finally:
        await config.teardown()
```

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Test storage uses the same Supabase credentials as production
# but creates a separate bucket for isolation
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### **Test IDs**
```python
# Predefined test IDs for consistency
TEST_USER_ID = "test-user-123"
TEST_PROJECT_ID = "test-project-456"
TEST_UPLOAD_ID = "test-upload-789"
TEST_INDEX_RUN_ID = "test-index-run-123"
TEST_DOCUMENT_ID = "test-document-456"
```

## 🧹 **Cleanup Strategy**

### **Automatic Cleanup**
- **Test Data**: All test files deleted after tests complete
- **Temp Files**: Local temporary files cleaned up automatically
- **Storage Usage**: Regular cleanup of old test data

### **Manual Cleanup**
```python
# Clean specific patterns
await storage.cleanup_test_data("email-uploads/test-upload-789")

# Clean all test data
await storage.cleanup_test_data()

# Get storage usage before cleanup
usage = await storage.get_test_storage_usage()
print(f"Files: {usage['total_files']}, Size: {usage['total_size_mb']} MB")
```

## 📊 **Monitoring**

### **Storage Usage**
```python
# Get current usage
usage = await storage.get_test_storage_usage()
print(f"Test bucket: {usage['bucket_name']}")
print(f"Total files: {usage['total_files']}")
print(f"Total size: {usage['total_size_mb']} MB")
```

### **File Listing**
```python
# List all test files
all_files = await storage.list_test_files()

# List specific folders
email_files = await storage.list_test_files("email-uploads")
user_files = await storage.list_test_files("users")
```

## 🎯 **Benefits**

1. **Isolation**: Complete separation from production data
2. **No Auth Issues**: Admin client bypasses authentication
3. **Consistent**: Predefined test IDs ensure consistency
4. **Clean**: Automatic cleanup prevents test data accumulation
5. **Scalable**: Can handle multiple test scenarios
6. **Debuggable**: Clear logging and error handling
7. **Efficient**: Temporary files managed automatically

## 🔄 **Integration with Existing Tests**

### **Pipeline Tests**
```python
# Use in pipeline integration tests
async def test_pipeline_with_storage():
    config = TestStorageConfig()
    await config.setup()
    
    try:
        # Upload test PDF
        pdf_path = await config.create_test_pdf("Pipeline test content")
        upload_result = await config.upload_test_email_pdf(pdf_path)
        
        # Run pipeline
        pipeline_result = await run_indexing_pipeline(upload_result['upload_id'])
        
        # Verify results
        assert pipeline_result['status'] == 'completed'
        
    finally:
        await config.teardown()
```

### **API Tests**
```python
# Use in API endpoint tests
async def test_upload_endpoint():
    config = TestStorageConfig()
    await config.setup()
    
    try:
        # Create test file
        pdf_path = await config.create_test_pdf("API test content")
        
        # Test API endpoint
        with open(pdf_path, 'rb') as f:
            response = await client.post("/api/upload", files={"file": f})
        
        assert response.status_code == 200
        
    finally:
        await config.teardown()
```

This test storage strategy ensures that your tests can run independently, safely, and efficiently without affecting production data or requiring complex authentication setup. 