# Project URL Architecture

## Overview
Dual URL pattern for public email uploads vs authenticated user projects.

## URL Patterns

### Public Projects (Anonymous Email Uploads)
- **URL**: `/projects/project-name-{indexing_run_id}`
- **Example**: `/projects/untitled-project-abc123-def4-5678-9abc-def123456789`
- **Data Source**: Email upload → indexing run → wiki generation
- **Access**: Public (no authentication required)

### Private Projects (Authenticated Users)
- **URL**: `/projects/project-name-{project_id}/indexing-run-{indexing_run_id}`
- **Example**: `/projects/my-building-project-123abc-def4-5678-9abc-def987654321/indexing-run-456def-abc1-2345-6def-abc789012345`
- **Data Source**: Project → indexing runs → wiki generations
- **Access**: Owner only (RLS enforced)
- **Multiple Wikis**: Shows latest wiki by default, can navigate to specific runs

## Data Architecture

### Junction Table: `project_wikis`
```sql
-- Public email uploads
project_id = NULL
indexing_run_id = "abc-123-email-run"
access_level = 'public'

-- Private user projects  
project_id = "def-456-project"
indexing_run_id = "ghi-789-run-1"
access_level = 'private'
```

## API Implementation

### Frontend Slug Resolution
1. Extract UUID from URL
2. Determine if it's project_id or indexing_run_id based on URL pattern
3. Call appropriate backend endpoint

### Backend Endpoints
- `/api/indexing-runs-with-wikis` - Public browsing (junction table)
- `/api/projects/{project_id}` - Get project + latest wiki
- `/api/projects/{project_id}/indexing-runs/{run_id}` - Specific wiki

### Access Control
- **Public**: `access_level = 'public' AND upload_type = 'email'`
- **Private**: RLS policies based on `user_id`
- **Junction table**: Single source for both patterns

## Key Benefits
1. **SEO Friendly**: Project-based URLs for authenticated users
2. **Performance**: Junction table eliminates complex queries
3. **Scalability**: Handles 1:many project:wiki relationship
4. **Security**: RLS policies prevent unauthorized access
5. **Backward Compatible**: Public email uploads continue working