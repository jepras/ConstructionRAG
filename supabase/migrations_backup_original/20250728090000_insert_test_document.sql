-- Insert test document for pipeline testing
-- This document will be owned by the test user

INSERT INTO documents (
    id,
    user_id,
    filename,
    file_path,
    file_size,
    page_count,
    status,
    metadata,
    created_at,
    updated_at
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000', -- Fixed UUID for testing
    'a4be935d-dd17-4db2-aa4e-b4989277bb1a', -- Your user ID
    'test-with-little-variety.pdf',
    '/path/to/test-with-little-variety.pdf',
    4370000, -- 4.37 MB in bytes
    10, -- Approximate page count
    'pending',
    '{"content_type": "application/pdf", "test_document": true}'::jsonb,
    NOW(),
    NOW()
) ON CONFLICT (id) DO NOTHING; 