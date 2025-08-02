# Storage Architecture

## Overview
This document outlines the storage structure for the ConstructionRAG system, supporting both anonymous email-based uploads and authenticated user projects with versioned indexing runs.

## Storage Structure

```
pipeline-assets/
├── email-uploads/                    # Anonymous email-based uploads
│   ├── {upload-id}/
│   │   ├── index-runs/
│   │   │   ├── {index-run-id}/       # Single index run per email upload
│   │   │   │   ├── pdfs/             # Original PDFs for this run
│   │   │   │   │   ├── document-1.pdf
│   │   │   │   │   └── ...
│   │   │   │   ├── {document-id-1}/  # Processing outputs per document
│   │   │   │   │   ├── extracted-pages/
│   │   │   │   │   │   ├── page_1.png
│   │   │   │   │   │   └── ...
│   │   │   │   │   └── table-images/
│   │   │   │   │       ├── table_1.png
│   │   │   │   │       └── ...
│   │   │   │   ├── {document-id-2}/
│   │   │   │   │   └── ...
│   │   │   │   ├── generated/        # Generated content
│   │   │   │   │   ├── markdown/
│   │   │   │   │   │   ├── summary.md
│   │   │   │   │   │   └── ...
│   │   │   └── ...
│   │   └── ...
│   └── ...
├── users/
│   ├── {user-id}/
│   │   ├── projects/
│   │   │   ├── {project-id}/
│   │   │   │   ├── index-runs/
│   │   │   │   │   ├── {index-run-id-1}/          # Version 1
│   │   │   │   │   │   ├── pdfs/                  # All PDFs for this run
│   │   │   │   │   │   │   ├── document-1.pdf
│   │   │   │   │   │   │   ├── document-2.pdf
│   │   │   │   │   │   │   └── ...
│   │   │   │   │   │   ├── {document-id-1}/       # Processing outputs
│   │   │   │   │   │   │   ├── extracted-pages/
│   │   │   │   │   │   │   │   ├── page_1.png
│   │   │   │   │   │   │   │   └── ...
│   │   │   │   │   │   │   └── table-images/
│   │   │   │   │   │   │       ├── table_1.png
│   │   │   │   │   │   │       └── ...
│   │   │   │   │   │   ├── {document-id-2}/
│   │   │   │   │   │   │   └── ...
│   │   │   │   │   │   └── ...
│   │   │   │   │   ├── generated/                 # Markdown and generated content
│   │   │   │   │   │   ├── markdown/
│   │   │   │   │   │   │   ├── project-summary.md
│   │   │   │   │   │   │   ├── technical-specs.md
│   │   │   │   │   │   │   └── ...
│   │   │   │   │   │   ├── pages/                 # Generated HTML pages
│   │   │   │   │   │   │   ├── index.html
│   │   │   │   │   │   │   └── ...
│   │   │   │   │   │   └── assets/                # Page assets
│   │   │   │   │   │       ├── images/
│   │   │   │   │   │       ├── css/
│   │   │   │   │   │       └── js/
│   │   │   │   │   └── temp/                      # Temporary processing files
│   │   │   │   │       ├── partition/             # Temporary files from partition step
│   │   │   │   │       │   ├── raw_text_extraction.json
│   │   │   │   │       │   ├── page_boundaries.json
│   │   │   │   │       │   └── temp_images/
│   │   │   │   │       ├── metadata/              # Temporary metadata processing
│   │   │   │   │       │   ├── raw_metadata.json
│   │   │   │   │       │   └── image_processing_temp/
│   │   │   │   │       ├── enrichment/            # Temporary VLM processing
│   │   │   │   │       │   ├── vlm_requests.json
│   │   │   │   │       │   └── caption_cache.json
│   │   │   │   │       ├── chunking/              # Temporary chunking files
│   │   │   │   │       │   ├── pre_chunked_elements.json
│   │   │   │   │       │   └── chunk_analysis.json
│   │   │   │   │       └── embedding/             # Temporary embedding files
│   │   │   │   │           ├── embedding_batches.json
│   │   │   │   │           └── validation_samples.json
│   │   │   │   └── {index-run-id-2}/              # Version 2
│   │   │   │       └── ... (same structure)
│   │   │   │   └── ...
│   │   │   └── ...
│   │   └── ...
│   └── ...
└── organizations/                    # Future: Organization support
    ├── {org-id}/
    │   ├── projects/
    │   │   └── {project-id}/
    │   │       └── index-runs/
    │   │           └── {index-run-id}/
    │   │               └── ... (same structure)
    │   └── ...
    └── ...
```

## File Lifecycle

### Email Upload Lifecycle
```
1. Upload: original.pdf → email-uploads/{upload-id}/index-runs/{index-run-id}/pdfs/{filename}
2. Processing: Document outputs → email-uploads/{upload-id}/index-runs/{index-run-id}/{document-id}/
3. Generation: Generated content → email-uploads/{upload-id}/index-runs/{index-run-id}/generated/
4. Cleanup: After 30 days → Delete entire {upload-id} folder
```

### User Project Lifecycle
```
1. Upload: PDFs → users/{user-id}/projects/{project-id}/index-runs/{index-run-id}/pdfs/
2. Processing: Document outputs → users/{user-id}/projects/{project-id}/index-runs/{index-run-id}/{document-id}/
3. Generation: Project content → users/{user-id}/projects/{project-id}/index-runs/{index-run-id}/generated/
4. Cleanup: Temp files deleted after processing, versions kept indefinitely
```

## Database Schema

### Email Uploads
```sql
CREATE TABLE email_uploads (
    id TEXT PRIMARY KEY, -- upload_id from storage path
    email TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_size INTEGER,
    status TEXT DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
    public_url TEXT,  -- Generated page URL
    processing_results JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '30 days'),
    index_run_id TEXT  -- References indexing_runs table
);
```

### User Projects
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE index_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,  -- Auto-increment per project
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    document_count INTEGER DEFAULT 0,
    processing_results JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(project_id, version)
);

CREATE TABLE index_run_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    index_run_id UUID REFERENCES index_runs(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_size INTEGER,
    status TEXT DEFAULT 'pending',
    processing_results JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Security & Access Control

### Email Upload Access
- Public pages accessible via unique URL
- Not indexed by search engines
- Auto-expire after 30 days
- Rate limited to prevent abuse

### User Project Access
- Requires authentication
- Row Level Security (RLS) ensures users can only access their own projects
- Project-level permissions for future collaboration

## Storage Service Methods

### Email Upload Methods
```python
async def upload_original_pdf(self, file_path: str, filename: str, upload_type: UploadType.EMAIL, upload_id: str, index_run_id: UUID) -> Dict[str, Any]
async def upload_extracted_page_image(self, image_path: str, document_id: UUID, page_num: int, complexity: str, upload_type: UploadType.EMAIL, upload_id: str, index_run_id: UUID) -> Dict[str, Any]
async def upload_table_image(self, image_path: str, document_id: UUID, table_id: str, upload_type: UploadType.EMAIL, upload_id: str, index_run_id: UUID) -> Dict[str, Any]
async def upload_generated_file(self, file_path: str, filename: str, upload_type: UploadType.EMAIL, upload_id: str, index_run_id: UUID) -> Dict[str, Any]
async def upload_temp_file(self, file_path: str, filename: str, step: str, upload_type: UploadType.EMAIL, upload_id: str, index_run_id: UUID) -> Dict[str, Any]
```

### User Project Methods
```python
async def upload_original_pdf(self, file_path: str, filename: str, upload_type: UploadType.USER_PROJECT, user_id: UUID, project_id: UUID, index_run_id: UUID) -> Dict[str, Any]
async def upload_extracted_page_image(self, image_path: str, document_id: UUID, page_num: int, complexity: str, upload_type: UploadType.USER_PROJECT, user_id: UUID, project_id: UUID, index_run_id: UUID) -> Dict[str, Any]
async def upload_table_image(self, image_path: str, document_id: UUID, table_id: str, upload_type: UploadType.USER_PROJECT, user_id: UUID, project_id: UUID, index_run_id: UUID) -> Dict[str, Any]
async def upload_generated_file(self, file_path: str, filename: str, upload_type: UploadType.USER_PROJECT, user_id: UUID, project_id: UUID, index_run_id: UUID) -> Dict[str, Any]
async def upload_temp_file(self, file_path: str, filename: str, step: str, upload_type: UploadType.USER_PROJECT, user_id: UUID, project_id: UUID, index_run_id: UUID) -> Dict[str, Any]
```

### Cleanup Methods
```python
async def cleanup_expired_email_uploads(self) -> int
async def cleanup_temp_files(self, max_age_days: int = 1) -> int
async def delete_index_run(self, index_run_id: UUID) -> bool
```

## Benefits

1. **Unified Structure**: Email uploads and user projects use identical storage organization
2. **Version Control**: Each index run is a complete snapshot
3. **Project Organization**: Clear project boundaries
4. **Scalability**: Easy to add new versions without affecting old ones
5. **Cleanup**: Can delete old versions while keeping current
6. **Collaboration**: Future organization support built-in
7. **Debugging**: Temp files available for troubleshooting
8. **Generated Content**: Markdown and pages organized by run
9. **Simple Anonymous Uploads**: Email-based system for quick trials with same structure as projects
10. **Security**: Proper access controls for each type
11. **Efficiency**: Temporary files cleaned up automatically
12. **Consistency**: Same storage service methods work for both upload types

## Test Storage Strategy

### Test Storage Structure
```
pipeline-assets-test/                    # Separate test bucket
├── email-uploads/
│   ├── test-upload-789/
│   │   └── index-runs/
│   │       ├── test-index-run-123/
│   │       │   ├── pdfs/
│   │       │   │   └── test-document.pdf
│   │       │   ├── test-document-456/
│   │       │   │   ├── extracted-pages/
│   │       │   │   └── table-images/
│   │       │   ├── generated/
│   │       │   └── temp/
│   │       └── ...
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

### Test Storage Service
- **Admin Client**: Uses `get_supabase_admin_client()` to bypass auth requirements
- **Separate Bucket**: `pipeline-assets-test` bucket for complete isolation
- **Test IDs**: Predefined test user/project/upload IDs for consistency
- **Auto Cleanup**: Automatic cleanup of test data after tests complete
- **Temp Files**: Local temporary files for testing, cleaned up automatically

### Test Storage Methods
```python
# Email upload testing
await test_storage.upload_original_pdf(
    pdf_path, 
    filename="test-document.pdf",
    upload_type=UploadType.EMAIL,
    upload_id="test-upload-789",
    index_run_id=UUID("test-index-run-123")
)

# User project testing
await test_storage.upload_original_pdf(
    pdf_path, 
    filename="test-document.pdf",
    upload_type=UploadType.USER_PROJECT,
    user_id=UUID("test-user-123"),
    project_id=UUID("test-project-456"),
    index_run_id=UUID("test-index-run-123")
)

# Processing output testing
await test_storage.upload_temp_file(
    temp_file_path,
    filename="test-output.json",
    step="partition",
    upload_type=UploadType.EMAIL,
    upload_id="test-upload-789",
    index_run_id=UUID("test-index-run-123")
)

# Cleanup
await test_storage.cleanup_test_data()
```

### Test Configuration
```python
# In test files
config = TestStorageConfig()
await config.setup()

try:
    # Run tests
    pdf_path = await config.create_test_pdf("Test content")
    result = await config.upload_test_email_pdf(pdf_path)
    # ... more tests
finally:
    await config.teardown()  # Cleanup everything
```

## Future Considerations

- Organization-level storage for team collaboration
- Advanced versioning with branching and merging
- Automated backup and disaster recovery
- Storage analytics and usage monitoring
- Integration with external storage providers 