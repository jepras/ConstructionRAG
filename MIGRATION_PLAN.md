# ConstructionRAG Storage Unification Migration Plan

## Executive Summary

### Goal
Migrate ConstructionRAG from dual storage patterns (email vs user_project) to a unified GitHub-style URL structure using `specfinder.io/username/projectname`. This migration will:

- **Eliminate complexity** of dual upload types (`email` vs `user_project`)
- **Introduce consistent URL patterns** for both anonymous and authenticated projects
- **Simplify access control** using visibility levels instead of upload types
- **Remove NULL handling** by using a special ANONYMOUS_USER_ID for all anonymous projects
- **Enable future features** like project collaboration and public project discovery
- **Maintain backward compatibility** during transition period

### Current State Problems
- Dual storage patterns create confusion in codebase
- Anonymous projects use NULL user_id creating complex database queries
- Complex access control logic across upload types
- Inconsistent URL patterns for public vs private projects
- Difficult foreign key management with NULL values

### Target State Benefits
- Single unified storage pattern for all projects
- Clean GitHub-style URLs: `specfinder.io/anonymous/project-name` and `specfinder.io/username/project-name`
- Simplified access control using visibility levels (public, private, internal)
- **No NULL user_id values** - anonymous projects use special ANONYMOUS_USER_ID
- Consistent authentication patterns with `isAuthenticated` checks
- Better project discoverability and sharing
- Consistent API patterns and simpler database queries
- Anonymous projects use simple names with uniqueness enforcement

## Implementation Strategy

### Recommended Approach: Local-First Iterative Development

**IMPORTANT:** All development and testing happens locally with local Supabase database first. Only after complete local validation will we deploy to production with a fresh database reset.

### Development Environment

```bash
# Always use local Supabase for development
supabase start

# Use full stack with local indexing
./start-local-dev-with-indexing.sh

# Frontend development
cd frontend && npm run dev
```

### Phase-by-Phase Implementation (All Local First)

#### Phase 1: Local Foundation (Week 1)
**Local Database + Storage Setup**
```bash
# Create migration branch
git checkout -b unified-storage-migration

# Local database changes (supabase db)
- Create ANONYMOUS_USER_ID user in local DB
- Add username, project_slug, visibility columns
- Update local storage bucket structure
- Test with fresh local data (no migration of old data)
```
**Local Testing:** Upload documents locally, verify new structure works

#### Phase 2: Backend API - Local Development (Week 2)
**Build New Endpoints in Local Environment**
```python
# Build new endpoints (test locally first)
@app.get("/api/projects/{username}/{project_slug}")  # NEW
async def get_project_new(username, project_slug): ...

# Old endpoints can be ignored in local dev
```
**Local Testing:** Test new endpoints with local data only

#### Phase 3: Frontend Routes - Local Development (Week 3-4)
**Build New Routes Testing Locally**
```typescript
// Build /projects/[username]/[projectSlug] structure
// Test with local anonymous uploads first
// Then test with local authenticated uploads
```
**Local Testing:** Complete workflows in local environment

#### Phase 4: Production Deployment (Week 5)
**Only After Local Testing Complete**
- Reset production database (fresh start)
- Deploy new system to Railway
- No data migration needed
- Users start fresh with new system

### Testing Strategy (All Local First)

#### Critical First Test: Anonymous Upload with Project Name
**MOST IMPORTANT:** The first test in LOCAL environment:
```bash
# ✅ LOCAL Test 1: Upload document as anonymous user with chosen project name - COMPLETED
1. ✅ Navigate to http://localhost:3000/upload
2. ✅ Upload PDF file
3. ✅ Enter project name: "my-construction-site"
4. ✅ Verify project is created with slug: "my-construction-site"
5. ✅ Verify URL works: http://localhost:3000/projects/anonymous/my-construction-site
6. ✅ Verify wiki generates correctly in local environment
7. ✅ Verify query functionality works locally
```

#### Local Testing Suite
```bash
# Backend API tests against local Supabase
cd backend
python -m pytest tests/integration/test_unified_api.py

# Frontend E2E tests against local backend
cd frontend  
npm run test:e2e -- --spec="unified-structure.spec.ts"

# Test new endpoints locally
curl http://localhost:8000/api/projects/anonymous/test-project
curl http://localhost:8000/api/projects/john-doe/construction-site
```

#### Production Testing (After Deployment)
Only after local testing is complete:
```bash
# Test production endpoints
curl https://api.specfinder.io/api/projects/anonymous/test-project
```

### Benefits of Local-First Development

1. **Complete Isolation** - Local Supabase keeps production safe
2. **Fast Iteration** - No deployment delays during development
3. **Safe Testing** - Break things locally without consequences
4. **Clean Production** - Deploy only tested, working code
5. **Fresh Start** - No complex migration, just clean deployment

### Risk Mitigation

- **Local development first** - All changes tested locally
- **Fresh production deployment** - No migration risks
- **Comprehensive local testing** - Full workflows tested before production
- **Clean cutover** - Old system stops, new system starts

## Anonymous User Concept

### Core Principle
Instead of using `NULL` for anonymous users, we introduce a special **ANONYMOUS_USER_ID** constant that represents all anonymous users. This approach:

- **Eliminates NULL handling** in database queries and application logic
- **Simplifies foreign key relationships** - all tables can have non-null user_id
- **Enables consistent authentication patterns** - authentication becomes a boolean check
- **Improves data model consistency** - anonymous becomes just another "user"

### Anonymous User Implementation
```sql
-- Create special anonymous user record
INSERT INTO user_profiles (id, username, full_name, created_at) 
VALUES (
    '00000000-0000-0000-0000-000000000000',  -- ANONYMOUS_USER_ID
    'anonymous',
    'Anonymous User',
    NOW()
);
```

### Constants Definition
```python
# backend/src/constants.py
ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"
ANONYMOUS_USERNAME = "anonymous"
```

```typescript
// frontend/src/lib/constants.ts
export const ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000";
export const ANONYMOUS_USERNAME = "anonymous";
```

### Benefits of This Approach
1. **No NULL Handling**: All queries work with standard equality checks
2. **Simpler Foreign Keys**: Every table can have `NOT NULL` user_id constraints
3. **Consistent Data Model**: Anonymous users are treated like regular users in the database
4. **Cleaner Application Logic**: Authentication becomes a simple boolean check
5. **Better Performance**: No need for `IS NULL` checks in database queries
6. **Easier Testing**: Predictable user IDs for test scenarios

## Database Schema Changes

### New Unified Table Structure

#### Modified `projects` Table
```sql
-- First, create the anonymous user if it doesn't exist
INSERT INTO user_profiles (id, username, full_name, created_at) 
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'anonymous',
    'Anonymous User',
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- Update NULL user_ids to use ANONYMOUS_USER_ID
UPDATE projects 
SET user_id = '00000000-0000-0000-0000-000000000000'
WHERE user_id IS NULL;

-- Now make user_id NOT NULL since all projects have a user
ALTER TABLE projects 
ALTER COLUMN user_id SET NOT NULL;

-- Add new columns for username-based URLs
ALTER TABLE projects 
ADD COLUMN username TEXT NOT NULL DEFAULT 'anonymous',
ADD COLUMN project_slug TEXT NOT NULL,
ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private' 
    CHECK (visibility IN ('public', 'private', 'internal'));

-- Create unique constraint for username/project_slug combination
ALTER TABLE projects 
ADD CONSTRAINT projects_username_slug_unique 
UNIQUE (username, project_slug);

-- Update existing records
UPDATE projects 
SET username = (
    CASE 
        WHEN user_id = '00000000-0000-0000-0000-000000000000' THEN 'anonymous'
        ELSE COALESCE((SELECT up.username FROM user_profiles up WHERE up.id = projects.user_id), 'anonymous')
    END
),
project_slug = LOWER(REGEXP_REPLACE(name, '[^a-zA-Z0-9]', '-', 'g')),
visibility = CASE 
    WHEN access_level = 'public' THEN 'public'
    WHEN access_level = 'private' THEN 'private'
    ELSE 'internal'
END;

-- Note: Anonymous projects will need unique project names
-- UNIQUE(username, project_slug) constraint enforces this

-- Remove old access_level column after migration
-- ALTER TABLE projects DROP COLUMN access_level;
```

#### Modified `indexing_runs` Table
```sql
-- Update NULL user_ids to use ANONYMOUS_USER_ID
UPDATE indexing_runs 
SET user_id = '00000000-0000-0000-0000-000000000000'
WHERE user_id IS NULL;

-- Make user_id NOT NULL
ALTER TABLE indexing_runs 
ALTER COLUMN user_id SET NOT NULL;

-- Add visibility column before removing upload_type
ALTER TABLE indexing_runs 
ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'
    CHECK (visibility IN ('public', 'private', 'internal'));

-- Update existing records based on old upload_type
UPDATE indexing_runs 
SET visibility = CASE 
    WHEN upload_type = 'email' THEN 'public'
    WHEN access_level = 'public' THEN 'public'
    ELSE 'private'
END;

-- Remove old columns after migration
-- ALTER TABLE indexing_runs DROP COLUMN upload_type;
-- ALTER TABLE indexing_runs DROP COLUMN access_level;
```

#### Modified `wiki_generation_runs` Table
```sql
-- Remove upload_type and upload_id columns, add visibility
ALTER TABLE wiki_generation_runs 
DROP COLUMN upload_type,
DROP COLUMN upload_id,
ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'
    CHECK (visibility IN ('public', 'private', 'internal'));

-- Update storage_path to use new username/project structure
UPDATE wiki_generation_runs 
SET visibility = CASE 
    WHEN upload_type = 'email' THEN 'public'
    WHEN access_level = 'public' THEN 'public'
    ELSE 'private'
END,
storage_path = CONCAT(
    (SELECT p.username FROM projects p WHERE p.id = wiki_generation_runs.project_id),
    '/',
    (SELECT p.project_slug FROM projects p WHERE p.id = wiki_generation_runs.project_id)
);

-- Remove old access_level column
-- ALTER TABLE wiki_generation_runs DROP COLUMN access_level;
```

#### Modified `documents` Table
```sql
-- Add visibility column and update file_path structure
ALTER TABLE documents 
ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'
    CHECK (visibility IN ('public', 'private', 'internal'));

-- Update visibility based on access_level
UPDATE documents 
SET visibility = CASE 
    WHEN access_level = 'public' THEN 'public'
    ELSE 'private'
END;

-- Update file_path to new structure (done in storage migration)
-- ALTER TABLE documents DROP COLUMN access_level;
```

### New RLS Policies

```sql
-- Drop existing RLS policies
DROP POLICY IF EXISTS "Users can view own projects" ON projects;
DROP POLICY IF EXISTS "Users can manage own projects" ON projects;
DROP POLICY IF EXISTS "Public project access" ON projects;

-- New unified RLS policies for projects
CREATE POLICY "Public projects readable by all" ON projects
    FOR SELECT USING (visibility = 'public');

CREATE POLICY "Private projects readable by owner" ON projects
    FOR SELECT USING (
        visibility = 'private' 
        AND user_id = COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000')
        AND user_id != '00000000-0000-0000-0000-000000000000'  -- Anonymous users can't access private projects
    );

CREATE POLICY "Internal projects readable by authenticated users" ON projects
    FOR SELECT USING (
        visibility = 'internal' 
        AND auth.role() = 'authenticated'
        AND auth.uid() != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Project owners can manage" ON projects
    FOR ALL USING (
        user_id = COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000')
        AND user_id != '00000000-0000-0000-0000-000000000000'  -- Anonymous users can't manage projects
    );

CREATE POLICY "Service role full access" ON projects
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Indexing runs policies
DROP POLICY IF EXISTS "Indexing run access" ON indexing_runs;

CREATE POLICY "Public indexing runs readable by all" ON indexing_runs
    FOR SELECT USING (visibility = 'public');

CREATE POLICY "Private indexing runs readable by owner" ON indexing_runs
    FOR SELECT USING (
        visibility = 'private' 
        AND user_id = COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000')
        AND user_id != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Internal indexing runs readable by authenticated users" ON indexing_runs
    FOR SELECT USING (
        visibility = 'internal' 
        AND auth.role() = 'authenticated'
        AND auth.uid() != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Indexing run owners can manage" ON indexing_runs
    FOR ALL USING (
        user_id = COALESCE(auth.uid(), '00000000-0000-0000-0000-000000000000')
        AND user_id != '00000000-0000-0000-0000-000000000000'
    );

CREATE POLICY "Service role full access" ON indexing_runs
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Similar policies for wiki_generation_runs, documents, etc.
```

### Tables Requiring Modification

1. **user_profiles** - Create anonymous user record with special ID
2. **projects** - Update NULL user_ids to ANONYMOUS_USER_ID, add username, project_slug, visibility columns
3. **indexing_runs** - Update NULL user_ids, remove upload_type, add visibility
4. **wiki_generation_runs** - Update NULL user_ids, remove upload_type/upload_id, add visibility
5. **documents** - Update NULL user_ids, add visibility column
6. **query_runs** - Update NULL user_ids, use visibility instead of access_level
7. **document_chunks** - Inherit visibility from parent document

### Key Migration Principle
**All NULL user_id values across all tables will be updated to use ANONYMOUS_USER_ID before making user_id columns NOT NULL. This ensures referential integrity and eliminates NULL handling throughout the application.**

## Storage Architecture

### New Unified Bucket Structure

The storage architecture is completely unified - both anonymous and authenticated users follow the exact same pattern using their username in the path structure:

```
/storage/
  /anonymous/                    # Anonymous projects (username = 'anonymous')
    /project-name/
      /documents/
        /original-filename.pdf
      /wiki/
        /page1.md
        /page2.md
  /actual-username/              # Authenticated user projects (username = actual username)
    /project-name/
      /documents/
        /original-filename.pdf
      /wiki/
        /page1.md
        /page2.md
```

### Unified Storage Pattern
- **Anonymous users**: Path `/anonymous/project-name/` where 'anonymous' is their username
- **Authenticated users**: Path `/actual-username/project-name/` where username is their actual username
- **Complete unification**: No special paths or exceptions - just different usernames
- **Consistent access**: All projects follow `/{username}/{project-name}/` pattern

### Storage Access Control
- Path: `/{username}/project-name/`
- Uniqueness enforced by `UNIQUE(username, project_slug)` constraint within each username namespace
- Anonymous users must pick different names if project name already exists in the 'anonymous' namespace
- Authenticated users can reuse project names from other namespaces (including 'anonymous')
- Automatic cleanup policies can be applied consistently across all namespaces

### Project Name Uniqueness
- **Anonymous namespace**: Anonymous projects must have unique names within the `anonymous` namespace
- **User namespaces**: Each user has their own namespace for project names
- **Conflict handling**: If an anonymous user tries to create a project with an existing name, they must choose a different name
- **Database constraint**: `UNIQUE(username, project_slug)` enforces uniqueness across all namespaces
- **API behavior**: Project creation will return validation errors for duplicate names

### Storage Migration Strategy
```python
def migrate_storage_paths():
    """Migrate existing storage paths to new unified structure"""
    
    # Get all projects with old storage paths
    projects = supabase.table('projects').select('*').execute()
    
    for project in projects.data:
        old_path = project.get('old_storage_path')
        username = project['username']  # Will be 'anonymous' for anonymous projects
        project_slug = project['project_slug']
        new_path = f"{username}/{project_slug}"  # Unified pattern for all projects
        
        # Move files in Supabase Storage
        move_storage_folder(old_path, new_path)
        
        # Update database references
        update_file_paths(project['id'], new_path)
```

## Frontend Upload Form Updates

### Critical Missing Component: Project Name Input

For the new URL structure to work, **ALL uploads (anonymous and authenticated) must provide a project name**. This is currently missing from upload forms and is essential for creating the GitHub-style URLs.

#### Required Upload Form Changes

**Problem:** Current upload forms don't collect project names, making it impossible to generate `/projects/username/project-name` URLs.

**Solution:** Add project name input field with real-time validation to all upload forms.

#### Upload Form Implementation

```typescript
// components/upload/ProjectUploadForm.tsx
import React, { useState, useCallback } from 'react';
import { debounce } from 'lodash';
import { api } from '@/lib/api';

interface ProjectUploadFormProps {
  user: UserContext;
  onUploadComplete: (projectSlug: string) => void;
}

export function ProjectUploadForm({ user, onUploadComplete }: ProjectUploadFormProps) {
  const [projectName, setProjectName] = useState('');
  const [nameAvailable, setNameAvailable] = useState<boolean | null>(null);
  const [nameError, setNameError] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  // Real-time name availability checking
  const checkNameAvailability = useCallback(
    debounce(async (name: string) => {
      if (!name.trim()) {
        setNameAvailable(null);
        setNameError('');
        return;
      }

      try {
        const response = await api.post('/api/projects/check-name', {
          project_name: name,
          username: user.username
        });
        
        if (response.data.available) {
          setNameAvailable(true);
          setNameError('');
        } else {
          setNameAvailable(false);
          setNameError(`Project name "${name}" is already taken in the ${user.username} namespace`);
        }
      } catch (error) {
        setNameError('Error checking name availability');
        setNameAvailable(false);
      }
    }, 500),
    [user.username]
  );

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const name = e.target.value;
    setProjectName(name);
    checkNameAvailability(name);
  };

  const handleUpload = async () => {
    if (!projectName.trim()) {
      setNameError('Project name is required');
      return;
    }

    if (!nameAvailable) {
      setNameError('Please choose an available project name');
      return;
    }

    if (files.length === 0) {
      setNameError('Please select files to upload');
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      files.forEach(file => formData.append('files', file));
      formData.append('project_name', projectName);
      
      const response = await api.post('/api/uploads', formData);
      const projectSlug = response.data.project_slug;
      
      onUploadComplete(projectSlug);
    } catch (error) {
      setNameError('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="project-upload-form">
      <div className="form-section">
        <label htmlFor="project-name" className="form-label">
          Project Name *
        </label>
        <div className="project-name-input">
          <span className="url-preview">
            specfinder.io/{user.username}/
          </span>
          <input
            id="project-name"
            type="text"
            value={projectName}
            onChange={handleNameChange}
            placeholder="my-project-name"
            className={`form-input ${
              nameAvailable === true ? 'valid' : 
              nameAvailable === false ? 'invalid' : ''
            }`}
          />
          {nameAvailable === true && (
            <span className="validation-icon success">✓</span>
          )}
          {nameAvailable === false && (
            <span className="validation-icon error">✗</span>
          )}
        </div>
        {nameError && (
          <div className="error-message">{nameError}</div>
        )}
        <div className="help-text">
          Your project will be available at: <strong>specfinder.io/{user.username}/{projectName || 'project-name'}</strong>
        </div>
      </div>

      <div className="form-section">
        <label htmlFor="file-upload" className="form-label">
          Documents *
        </label>
        <input
          id="file-upload"
          type="file"
          multiple
          accept=".pdf"
          onChange={(e) => setFiles(Array.from(e.target.files || []))}
          className="form-input"
        />
        <div className="help-text">
          Upload PDF files (max 10 files, 50MB each)
        </div>
      </div>

      <button
        onClick={handleUpload}
        disabled={!nameAvailable || files.length === 0 || isUploading}
        className="upload-button"
      >
        {isUploading ? 'Uploading...' : 'Create Project'}
      </button>
    </div>
  );
}
```

#### Name Validation Rules

```typescript
// lib/validation/projectName.ts
export function validateProjectName(name: string): { valid: boolean; error?: string } {
  // Basic validation rules
  if (!name.trim()) {
    return { valid: false, error: 'Project name is required' };
  }
  
  if (name.length < 3) {
    return { valid: false, error: 'Project name must be at least 3 characters' };
  }
  
  if (name.length > 50) {
    return { valid: false, error: 'Project name must be less than 50 characters' };
  }
  
  // GitHub-style naming rules
  if (!/^[a-zA-Z0-9][a-zA-Z0-9\-_]*[a-zA-Z0-9]$/.test(name)) {
    return { 
      valid: false, 
      error: 'Project name can only contain letters, numbers, hyphens, and underscores. Must start and end with letter or number.' 
    };
  }
  
  // Reserved names
  const reserved = ['api', 'admin', 'www', 'mail', 'ftp', 'localhost', 'anonymous'];
  if (reserved.includes(name.toLowerCase())) {
    return { valid: false, error: 'This project name is reserved' };
  }
  
  return { valid: true };
}

export function generateProjectSlug(name: string): string {
  return name.toLowerCase()
    .replace(/[^a-zA-Z0-9\-_]/g, '-')
    .replace(/--+/g, '-')
    .replace(/^-+|-+$/g, '');
}
```

#### Form Integration Points

Update these existing upload forms:

1. **Anonymous Upload Form** (`/app/upload/page.tsx`)
   - Add project name input as first field
   - Show URL preview: `specfinder.io/anonymous/project-name`
   
2. **Authenticated Upload Form** (`/app/(app)/dashboard/upload/page.tsx`)
   - Add project name input as first field  
   - Show URL preview: `specfinder.io/{username}/project-name`
   
3. **Project Creation Form** (`/app/(app)/dashboard/projects/new/page.tsx`)
   - Replace with unified ProjectUploadForm component

#### Error Handling

```typescript
// Handle common upload errors
const uploadErrorMessages = {
  'name_taken': 'Project name is already taken. Please choose a different name.',
  'invalid_name': 'Project name contains invalid characters.',
  'file_too_large': 'One or more files exceed the 50MB limit.',
  'too_many_files': 'Maximum 10 files allowed per upload.',
  'invalid_file_type': 'Only PDF files are allowed.',
  'upload_failed': 'Upload failed. Please check your connection and try again.'
};
```

## Frontend Structure Consolidation

### Current Dual Route Structure

The current frontend architecture maintains duplicate route structures for public and private project access:

```
app/
├── projects/[indexingRunId]/                           # Public projects (anonymous access)
│   ├── page.tsx                                        # Project overview
│   ├── [pageName]/page.tsx                             # Wiki pages  
│   ├── query/page.tsx                                  # Q&A interface
│   ├── indexing/page.tsx                               # Indexing progress
│   ├── settings/page.tsx                               # Project settings
│   └── checklist/page.tsx                              # Project checklist
│
├── (app)/dashboard/projects/[projectSlug]/[runId]/     # Private projects (authenticated)
│   ├── page.tsx                                        # Project overview (duplicate)
│   ├── [pageName]/page.tsx                             # Wiki pages (duplicate)
│   ├── query/page.tsx                                  # Q&A interface (duplicate)
│   ├── indexing/page.tsx                               # Indexing progress (duplicate)
│   ├── settings/page.tsx                               # Project settings (duplicate)
│   └── checklist/page.tsx                              # Project checklist (duplicate)
│
├── (app)/dashboard/                                    # Authenticated-only routes
├── (marketing)/                                        # Marketing pages
└── auth/                                              # Authentication routes
```

**Problems with Current Structure:**
- **Code duplication**: 12+ duplicate route files across public/private structures
- **Complex mental model**: Developers must remember two different URL patterns
- **Maintenance burden**: Changes require updates in both route structures
- **URL pattern inconsistency**: Single-slug vs nested URL patterns confuse users

### New Unified Route Structure

The consolidated frontend architecture uses a single GitHub-style pattern for all projects:

```
app/
├── projects/[username]/[projectSlug]/                  # All projects (unified)
│   ├── page.tsx                                        # Project overview
│   ├── [pageName]/page.tsx                             # Wiki pages
│   ├── query/page.tsx                                  # Q&A interface  
│   ├── indexing/page.tsx                               # Indexing progress
│   ├── settings/page.tsx                               # Project settings (auth-gated)
│   └── checklist/page.tsx                              # Project checklist
│
├── (app)/dashboard/                                    # User dashboard (unchanged)
├── (marketing)/                                        # Marketing pages (unchanged)
└── auth/                                              # Authentication routes (unchanged)
```

**Example URL Transformations:**
```typescript
// Before (dual patterns)
/projects/downtown-tower-def456                         // Public project (single-slug)
/dashboard/projects/downtown-tower-abc123/def456       // Private project (nested)

// After (unified GitHub-style)
/projects/anonymous/downtown-tower                     // Anonymous project  
/projects/jeppe/downtown-tower                         // User project
/projects/construction-co/downtown-tower               // Organization project
```

### Migration Benefits

#### **50% Fewer Route Files**
- **Current**: 12 duplicate route files across public/private structures
- **Target**: 6 unified route files serving all projects
- **Result**: Eliminates maintenance of duplicate routing logic

#### **Single Mental Model** 
- **Current**: Developers remember "public vs private" routing rules
- **Target**: Single `/projects/{username}/{project_slug}` pattern for everything
- **Result**: Consistent URL expectations across the entire application

#### **Existing Components Work**
- **Shared Components**: `/components/features/project-pages/` already used by both structures
- **No Component Changes**: Existing shared components work with unified routes
- **Component Reuse**: `ProjectQueryContent`, `ProjectIndexingContent`, etc. require no modifications

#### **Access Control at Component Level**
- **Current**: Route-level separation of public/private features
- **Target**: Component-level `user.isAuthenticated` checks
- **Result**: Single codebase with conditional feature rendering

```typescript
// Component-level access control example
function ProjectSettings({ user, project }: ProjectSettingsProps) {
  if (!user.isAuthenticated || project.user_id !== user.id) {
    return <div>Sign in to access project settings</div>;
  }
  
  return <ProjectSettingsForm project={project} />;
}
```

### Component Updates Needed

#### **Minimal API Call Changes**
Most existing shared components already work with the unified structure:

```typescript
// Before: Components handle both URL patterns
function ProjectQueryContent({ 
  indexingRunId,      // For public routes
  projectSlug,        // For private routes  
  runId              // For private routes
}: ProjectQueryProps) { /* ... */ }

// After: Single unified parameter pattern
function ProjectQueryContent({ 
  username,           // Always present
  projectSlug         // Always present  
}: ProjectQueryProps) { /* ... */ }
```

#### **Authentication State Integration**
Components add `user.isAuthenticated` checks for conditional features:

```typescript
// Example: Conditional settings access
function ProjectHeader({ project, user }: ProjectHeaderProps) {
  return (
    <header>
      <h1>{project.name}</h1>
      <div className="project-actions">
        {user.isAuthenticated && project.user_id === user.id && (
          <Link href={`/projects/${project.username}/${project.project_slug}/settings`}>
            Settings
          </Link>
        )}
      </div>
    </header>
  );
}
```

#### **API Client Simplification**
Update API calls to use new GitHub-style endpoints:

```typescript
// Before: Different API patterns for public/private
const publicProject = await api.get(`/api/indexing-runs/${indexingRunId}`);
const privateProject = await api.get(`/api/projects/${projectId}/runs/${runId}`);

// After: Single unified API pattern
const project = await api.get(`/api/projects/${username}/${projectSlug}`);
```

### Files to Delete

Remove all duplicate route files from the current dual structure:

#### **Public Route Duplicates (6 files)**
```
/app/projects/[indexingRunId]/page.tsx
/app/projects/[indexingRunId]/[pageName]/page.tsx  
/app/projects/[indexingRunId]/query/page.tsx
/app/projects/[indexingRunId]/indexing/page.tsx
/app/projects/[indexingRunId]/settings/page.tsx
/app/projects/[indexingRunId]/checklist/page.tsx
```

#### **Private Route Duplicates (6 files)**
```
/app/(app)/dashboard/projects/[projectSlug]/[runId]/page.tsx
/app/(app)/dashboard/projects/[projectSlug]/[runId]/[pageName]/page.tsx
/app/(app)/dashboard/projects/[projectSlug]/[runId]/query/page.tsx  
/app/(app)/dashboard/projects/[projectSlug]/[runId]/indexing/page.tsx
/app/(app)/dashboard/projects/[projectSlug]/[runId]/settings/page.tsx
/app/(app)/dashboard/projects/[projectSlug]/[runId]/checklist/page.tsx
```

**Total Removal**: 12 route files eliminated through consolidation

### Files to Create/Update

#### **New Unified Route Files (6 files)**
```
/app/projects/[username]/[projectSlug]/page.tsx
/app/projects/[username]/[projectSlug]/[pageName]/page.tsx
/app/projects/[username]/[projectSlug]/query/page.tsx
/app/projects/[username]/[projectSlug]/indexing/page.tsx  
/app/projects/[username]/[projectSlug]/settings/page.tsx
/app/projects/[username]/[projectSlug]/checklist/page.tsx
```

#### **Existing Shared Components (No Changes)**
The following components in `/components/features/project-pages/` work unchanged:
- `ProjectQueryContent.tsx` 
- `ProjectIndexingContent.tsx`
- `ProjectChecklistContent.tsx`
- `ProjectSettingsContent.tsx`
- `SourcePanel.tsx`, `QueryInterface.tsx`, etc.

#### **API Client Updates**
Update API client to use new GitHub-style endpoints:

```typescript
// lib/api/projects.ts  
export class ProjectsApiClient {
  async getProject(username: string, projectSlug: string) {
    return this.client.get(`/api/projects/${username}/${projectSlug}`);
  }
  
  async getProjectWiki(username: string, projectSlug: string) {
    return this.client.get(`/api/projects/${username}/${projectSlug}/wiki`);
  }
  
  async createQuery(username: string, projectSlug: string, query: string) {
    return this.client.post(`/api/projects/${username}/${projectSlug}/queries`, { query });
  }
}
```

### Implementation Strategy

#### **Phase 1: Route Structure Migration**
1. **Create unified route folder**: `/app/projects/[username]/[projectSlug]/`
2. **Copy existing route files**: Use private route implementations as base (more feature-complete)
3. **Update parameter extraction**: Change from `projectSlug`/`runId` to `username`/`projectSlug`
4. **Add authentication checks**: Implement component-level access control

#### **Phase 2: Component Integration**
1. **Update API calls**: Migrate to GitHub-style endpoint parameters
2. **Add authentication states**: Implement `user.isAuthenticated` conditional rendering
3. **Test shared components**: Verify existing components work with new parameters
4. **Update navigation**: Change all internal links to use unified URL pattern

#### **Phase 3: Cleanup and Testing**  
1. **Remove duplicate routes**: Delete old public and private route files
2. **Update URL generation**: Ensure all links use new GitHub-style patterns
3. **Test access control**: Verify authentication gating works correctly
4. **Validate navigation**: Test all project page transitions

### Expected Impact

#### **Development Velocity**
- **50% fewer files** to maintain for project routes
- **Single debugging path** for project-related issues  
- **Consistent URL patterns** reduce cognitive load
- **Shared component reuse** accelerates new feature development

#### **User Experience**
- **Predictable URLs** follow GitHub conventions users already know
- **Consistent navigation** across all project types  
- **Better sharing** with semantic username/project-name URLs
- **Cleaner bookmarking** with descriptive URL structure

#### **Code Quality**  
- **Eliminated duplication** reduces bug surface area
- **Unified access patterns** simplify testing scenarios
- **Single source of truth** for project routing logic
- **Better maintainability** through consolidated codebase

## Backend API Updates

### GitHub-Inspired RESTful API Design

The new API follows GitHub's RESTful patterns with clear resource hierarchy and predictable URLs that match our frontend structure. This design eliminates the complexity of dual upload types while providing intuitive, developer-friendly endpoints.

#### Core Resource Endpoints (GitHub Style)

```
# Projects - Core resource management
GET    /api/projects/{username}/{project_slug}                 # Get project details
PATCH  /api/projects/{username}/{project_slug}                 # Update project
DELETE /api/projects/{username}/{project_slug}                 # Delete project
POST   /api/projects/check-name                                # Check project name availability

# Project Runs - Nested resource under projects  
GET    /api/projects/{username}/{project_slug}/runs            # List all runs for project
POST   /api/projects/{username}/{project_slug}/runs            # Create new indexing run
GET    /api/projects/{username}/{project_slug}/runs/{run_id}   # Get specific run details

# Wiki - Project documentation
GET    /api/projects/{username}/{project_slug}/wiki            # List all wiki pages
GET    /api/projects/{username}/{project_slug}/wiki/{page_name} # Get specific wiki page

# Documents - Project files
GET    /api/projects/{username}/{project_slug}/documents       # List project documents
GET    /api/projects/{username}/{project_slug}/documents/{doc_id} # Get document details
POST   /api/projects/{username}/{project_slug}/documents       # Upload documents to project

# Queries - Project Q&A
GET    /api/projects/{username}/{project_slug}/queries         # List project queries
POST   /api/projects/{username}/{project_slug}/queries         # Create new query
GET    /api/projects/{username}/{project_slug}/queries/{query_id} # Get query details

# Upload - Legacy endpoint updated for new structure
POST   /api/uploads                                            # Upload with required project_name
```

#### Project Discovery Endpoints

```
# Global project discovery
GET    /api/projects                                           # All public projects

# User-specific project discovery
GET    /api/users/{username}/projects                          # Public projects by user

# Authenticated user's projects (requires auth)
GET    /api/user/projects                                      # Authenticated user's projects
```

#### Legacy Anonymous Upload Support

```
# Backward compatibility for anonymous uploads
POST   /api/uploads                                            # Creates anonymous project (legacy endpoint)
```

### RESTful API Benefits

This GitHub-inspired design provides several key advantages:

#### Clear Resource Hierarchy
- **Intuitive nesting**: Documents belong to projects, queries belong to projects
- **Predictable patterns**: All project resources follow `/projects/{username}/{project_slug}/{resource}` 
- **Consistent access control**: Single authentication pattern across all endpoints
- **Natural relationships**: URL structure mirrors data relationships

#### Developer-Familiar Patterns
- **GitHub-style URLs**: Developers immediately understand `/username/project-name` patterns
- **REST conventions**: GET for retrieval, POST for creation, PATCH for updates, DELETE for removal
- **Resource-centric design**: Each endpoint represents a clear resource or collection
- **HTTP method semantics**: Proper use of HTTP verbs for different operations

#### Frontend URL Alignment
- **Perfect URL matching**: API structure mirrors frontend route structure
- **Consistent parameters**: Same `username` and `project_slug` used in both frontend and API
- **Easy client generation**: Predictable patterns enable automatic API client generation
- **Clear navigation**: Users can predict API endpoints from frontend URLs

### Unified API Implementation

#### Single Endpoint Handler Pattern
```python
async def handle_project_resource(
    username: str,
    project_slug: str, 
    user: Optional[UserContext] = None,
    resource_type: str = "project"
) -> Dict[str, Any]:
    """Unified handler for all project-based resources"""
    
    # Single project resolution - works for both anonymous and authenticated
    project = await get_project_by_slug(username, project_slug, user)
    
    # Apply resource-specific access control
    if not can_access_resource(project, resource_type, user):
        raise HTTPException(403, "Access denied")
    
    return project

async def get_project_by_slug(
    username: str, 
    project_slug: str, 
    user: Optional[UserContext] = None
) -> Dict[str, Any]:
    """Single project resolution function for all endpoints"""
    
    query = supabase.table('projects').select('*')
    query = query.eq('username', username).eq('project_slug', project_slug)
    
    # Unified access control - no upload_type checking needed
    if user and user.isAuthenticated:
        # Authenticated users can see public, internal, and their own private projects
        query = query.or_(
            f"visibility.eq.public,"
            f"visibility.eq.internal,"
            f"and(visibility.eq.private,user_id.eq.{user.id})"
        )
    else:
        # Anonymous users can only see public projects
        query = query.eq('visibility', 'public')
    
    result = query.execute()
    if not result.data:
        raise HTTPException(404, "Project not found")
    
    return result.data[0]
```

#### Access Control Simplification
```python
def can_access_resource(project: Dict, resource_type: str, user: Optional[UserContext]) -> bool:
    """Unified access control for all project resources"""
    
    # Public projects - anyone can read
    if project['visibility'] == 'public':
        if resource_type in ['read', 'query', 'wiki']:
            return True
        # Write operations require authentication
        if resource_type in ['write', 'upload', 'settings']:
            return user and user.isAuthenticated and project['user_id'] == user.id
    
    # Private projects - owner only
    if project['visibility'] == 'private':
        return user and user.isAuthenticated and project['user_id'] == user.id
    
    # Internal projects - any authenticated user
    if project['visibility'] == 'internal':
        return user and user.isAuthenticated
    
    return False
```

### API Endpoint Comparison

| Old Pattern | New GitHub Pattern | Benefits |
|-------------|-------------------|----------|
| `GET /api/indexing-runs/{run_id}` | `GET /api/projects/{username}/{project_slug}/runs/{run_id}` | Clear project context, intuitive nesting |
| `POST /api/uploads` (dual types) | `POST /api/projects/{username}/{project_slug}/documents` | Single pattern, no type confusion |
| `POST /api/queries` (with run_id) | `POST /api/projects/{username}/{project_slug}/queries` | Project context in URL, cleaner payload |
| `GET /api/wiki/runs/{wiki_run_id}/pages` | `GET /api/projects/{username}/{project_slug}/wiki` | Direct resource access, no intermediate IDs |

**Note**: Since all completed projects will have wikis in the unified system, special wiki-filtering endpoints (`/api/indexing-runs-with-wikis`, `/api/user-projects-with-wikis`) are unnecessary. Project discovery is simplified to dedicated endpoints rather than complex query parameter filtering.

### Migration Implementation Examples

#### Project CRUD Operations
```python
# POST /api/projects/check-name
@router.post("/projects/check-name")
async def check_project_name_availability(
    request: ProjectNameCheckRequest,
    user: UserContext = Depends(get_current_user)
):
    """Check if project name is available in the given username namespace"""
    # Validate project name format
    validation = validate_project_name(request.project_name)
    if not validation.valid:
        return ProjectNameCheckResponse(
            available=False,
            error=validation.error
        )
    
    # Generate slug from name
    project_slug = generate_project_slug(request.project_name)
    
    # Check if name already exists in namespace
    existing = await supabase.table('projects').select('id').eq(
        'username', request.username
    ).eq('project_slug', project_slug).execute()
    
    available = len(existing.data) == 0
    
    return ProjectNameCheckResponse(
        available=available,
        project_slug=project_slug,
        error="Project name already taken" if not available else None
    )

# GET /api/projects/{username}/{project_slug}
@router.get("/projects/{username}/{project_slug}")
async def get_project(username: str, project_slug: str, user: UserContext = Depends(get_current_user)):
    project = await get_project_by_slug(username, project_slug, user)
    return ProjectResponse(**project)

# PATCH /api/projects/{username}/{project_slug}  
@router.patch("/projects/{username}/{project_slug}")
async def update_project(
    username: str, 
    project_slug: str, 
    updates: ProjectUpdateRequest,
    user: UserContext = Depends(get_authenticated_user)
):
    project = await get_project_by_slug(username, project_slug, user)
    if not can_access_resource(project, 'write', user):
        raise HTTPException(403, "Access denied")
    
    # Update project with new data
    updated = await update_project_data(project['id'], updates.dict())
    return ProjectResponse(**updated)
```

#### Document Management
```python
# GET /api/projects/{username}/{project_slug}/documents
@router.get("/projects/{username}/{project_slug}/documents")
async def list_project_documents(username: str, project_slug: str, user: UserContext = Depends(get_current_user)):
    project = await get_project_by_slug(username, project_slug, user)
    documents = await get_project_documents(project['id'])
    return DocumentListResponse(documents=documents)

# POST /api/projects/{username}/{project_slug}/documents
@router.post("/projects/{username}/{project_slug}/documents")
async def upload_project_documents(
    username: str, 
    project_slug: str,
    files: List[UploadFile],
    user: UserContext = Depends(get_current_user)
):
    project = await get_project_by_slug(username, project_slug, user)
    if not can_access_resource(project, 'upload', user):
        raise HTTPException(403, "Upload access denied")
    
    # Process file uploads for this specific project
    documents = await process_document_uploads(project['id'], files)
    return DocumentUploadResponse(documents=documents)
```

#### Query System
```python
# POST /api/projects/{username}/{project_slug}/queries
@router.post("/projects/{username}/{project_slug}/queries")
async def create_project_query(
    username: str,
    project_slug: str,
    query_request: QueryRequest,
    user: UserContext = Depends(get_current_user)
):
    project = await get_project_by_slug(username, project_slug, user)
    if not can_access_resource(project, 'query', user):
        raise HTTPException(403, "Query access denied")
    
    # Execute query within project context
    result = await execute_project_query(project['id'], query_request.question, user)
    return QueryResponse(**result)
```

### URL Generation Helpers
```python
def generate_project_api_url(username: str, project_slug: str, endpoint: str = "") -> str:
    """Generate consistent API URLs for projects"""
    base = f"/api/projects/{username}/{project_slug}"
    return f"{base}/{endpoint}" if endpoint else base

def generate_project_frontend_url(username: str, project_slug: str, page: str = "") -> str:
    """Generate consistent frontend URLs for projects"""
    base = f"/projects/{username}/{project_slug}"
    return f"{base}/{page}" if page else base

# Usage examples
api_url = generate_project_api_url("anonymous", "office-tower", "wiki")
# Returns: "/api/projects/anonymous/office-tower/wiki"

frontend_url = generate_project_frontend_url("jeppe", "construction-site", "queries") 
# Returns: "/projects/jeppe/construction-site/queries"
```

## Authentication Pattern Updates

### UserContext Class Pattern

We'll introduce a consistent `UserContext` pattern across both backend and frontend to handle authentication checks:

#### Backend UserContext (Python)
```python
# backend/src/models/user.py
from typing import Optional
from pydantic import BaseModel
from src.constants import ANONYMOUS_USER_ID

class UserContext(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    is_authenticated: bool = False
    
    @classmethod
    def anonymous(cls) -> "UserContext":
        """Create anonymous user context"""
        return cls(
            id=ANONYMOUS_USER_ID,
            username="anonymous",
            is_authenticated=False
        )
    
    @classmethod
    def authenticated(cls, user_id: str, username: str, email: str) -> "UserContext":
        """Create authenticated user context"""
        return cls(
            id=user_id,
            username=username,
            email=email,
            is_authenticated=True
        )
    
    @property
    def isAuthenticated(self) -> bool:
        """Check if user is authenticated (not anonymous)"""
        return self.is_authenticated and self.id != ANONYMOUS_USER_ID

# Usage in API endpoints
async def get_current_user(request: Request) -> UserContext:
    """Get current user context from request"""
    token = request.headers.get("Authorization")
    if not token:
        return UserContext.anonymous()
    
    try:
        user_data = verify_token(token)
        return UserContext.authenticated(
            user_id=user_data["user_id"],
            username=user_data["username"],
            email=user_data["email"]
        )
    except Exception:
        return UserContext.anonymous()
```

#### Frontend UserContext (TypeScript)
```typescript
// frontend/src/lib/auth/types.ts
import { ANONYMOUS_USER_ID } from '../constants';

export interface UserContext {
  id: string;
  username: string;
  email?: string;
  isAuthenticated: boolean;
}

export class UserContextHelper {
  static anonymous(): UserContext {
    return {
      id: ANONYMOUS_USER_ID,
      username: 'anonymous',
      isAuthenticated: false
    };
  }
  
  static authenticated(id: string, username: string, email: string): UserContext {
    return {
      id,
      username,
      email,
      isAuthenticated: true
    };
  }
  
  static isAuthenticated(user: UserContext): boolean {
    return user.isAuthenticated && user.id !== ANONYMOUS_USER_ID;
  }
}

// Usage in components
export function useAuth(): UserContext {
  const { user } = useAuthContext();
  return user || UserContextHelper.anonymous();
}
```

### Replacing Authentication Checks

#### Before (Problematic NULL Checks)
```python
# Backend - OLD pattern
if user.id:  # This fails with ANONYMOUS_USER_ID
    # User is authenticated
else:
    # User is anonymous

# Frontend - OLD pattern  
if (user?.id) {  // This fails with ANONYMOUS_USER_ID
  // User is authenticated
}
```

#### After (Consistent isAuthenticated Pattern)
```python
# Backend - NEW pattern
if user.isAuthenticated:
    # User is authenticated
else:
    # User is anonymous

# Example usage
async def create_project(user: UserContext, project_data: dict):
    if not user.isAuthenticated:
        raise HTTPException(401, "Authentication required to create projects")
    
    project_data["user_id"] = user.id  # Always a valid UUID, never NULL
```

```typescript
// Frontend - NEW pattern
if (user.isAuthenticated) {
  // User is authenticated
}

// Example usage
function ProjectSettings({ user }: { user: UserContext }) {
  if (!user.isAuthenticated) {
    return <div>Please sign in to access project settings</div>;
  }
  
  return <ProjectSettingsForm userId={user.id} />;
}
```

### Rate Limiting and Feature Differentiation

#### Rate Limiting by Authentication Status
```python
# backend/src/middleware/rate_limiting.py
async def apply_rate_limiting(user: UserContext, endpoint: str):
    if user.isAuthenticated:
        # Authenticated users get higher limits
        limit = AUTHENTICATED_RATE_LIMITS[endpoint]
        key = f"rate_limit:{user.id}:{endpoint}"
    else:
        # Anonymous users get lower limits
        limit = ANONYMOUS_RATE_LIMITS[endpoint] 
        key = f"rate_limit:anonymous:{endpoint}"  # Shared anonymous limit
    
    # Apply rate limiting logic
    check_rate_limit(key, limit)
```

#### Feature Access Control
```python
# Example: Project creation limits
async def create_project(user: UserContext, project_data: dict):
    if not user.isAuthenticated:
        # Anonymous users create public projects with ANONYMOUS_USER_ID
        project_data.update({
            "user_id": ANONYMOUS_USER_ID,
            "username": "anonymous", 
            "visibility": "public"  # Anonymous projects are always public
        })
    else:
        # Authenticated users can create private projects
        project_data.update({
            "user_id": user.id,
            "username": user.username,
            "visibility": project_data.get("visibility", "private")
        })
```

## Frontend Updates

### URL Generation Changes

#### Current URL Patterns:
```typescript
// Public projects (single slug)
/projects/downtown-tower-def456

// Private projects (nested)
/dashboard/projects/downtown-tower-abc123/def456
```

#### New Unified URL Patterns:
```typescript
// All projects use consistent pattern
/projects/anonymous/downtown-tower         # Anonymous projects
/projects/jeppe/downtown-tower             # User projects  
/projects/company/office-renovation        # Organization projects
```

### Route Structure Modifications

#### New Route Structure:
```
app/
├── projects/
│   └── [username]/
│       └── [projectSlug]/
│           ├── page.tsx              # Project overview
│           ├── wiki/
│           │   └── page.tsx          # Wiki pages
│           ├── queries/
│           │   └── page.tsx          # Q&A interface  
│           └── settings/
│               └── page.tsx          # Project settings (auth required)
```

#### Route Component Updates:
```typescript
// app/projects/[username]/[projectSlug]/page.tsx
export default async function ProjectPage({ 
  params 
}: { 
  params: { username: string; projectSlug: string } 
}) {
  const project = await getProjectBySlug(params.username, params.projectSlug);
  
  return (
    <ProjectOverview project={project} />
  );
}

// URL generation helper
export function generateProjectUrl(username: string, projectSlug: string): string {
  return `/projects/${username}/${projectSlug}`;
}
```

### API Call Updates

#### Updated API Client:
```typescript
// lib/api.ts
class UnifiedApiClient {
  async getProject(username: string, projectSlug: string) {
    return this.get(`/api/projects/${username}/${projectSlug}`);
  }
  
  async getProjectWiki(username: string, projectSlug: string) {
    return this.get(`/api/projects/${username}/${projectSlug}/wiki`);
  }
  
  async createQuery(username: string, projectSlug: string, query: string) {
    return this.post(`/api/projects/${username}/${projectSlug}/queries`, { query });
  }
}
```

#### Component Updates:
```typescript
// components/features/project-pages/ProjectHeader.tsx
interface ProjectHeaderProps {
  project: {
    username: string;
    project_slug: string;
    name: string;
    visibility: 'public' | 'private' | 'internal';
  };
}

export function ProjectHeader({ project }: ProjectHeaderProps) {
  const projectUrl = generateProjectUrl(project.username, project.project_slug);
  
  return (
    <header>
      <h1>{project.name}</h1>
      <div className="project-meta">
        <span>by {project.username}</span>
        <VisibilityBadge visibility={project.visibility} />
      </div>
    </header>
  );
}
```

## Structured Logging Updates

### Current Logging Pattern
Show examples of current logging with upload_type:
```python
logger.info("Processing upload", extra={
    "user_id": user_id,
    "upload_type": upload_type,
    "document_count": len(documents),
    "indexing_run_id": run_id
})
```

### New Unified Logging Pattern
Show examples with the new structure:
```python
logger.info("Processing project upload", extra={
    "user_id": user_id,
    "username": username, 
    "project_slug": project_slug,
    "is_authenticated": user.is_authenticated,
    "document_count": len(documents),
    "indexing_run_id": run_id
})
```

### Logging Benefits
- **More semantic information**: project_slug instead of generic IDs
- **Clear authentication status**: explicit is_authenticated field
- **Consistent user identification**: username for all projects
- **Better debugging**: GitHub-style identifiers in logs
- **Unified patterns**: same logging structure for all projects

### Key Logging Fields to Standardize
- `username` - Always present (either actual username or 'anonymous')
- `project_slug` - Human-readable project identifier  
- `is_authenticated` - Clear boolean for auth status
- `visibility` - Project visibility (public/private/unlisted)
- `user_context` - Include UserContext properties in relevant logs

### Migration Required
- Update all logger calls that reference upload_type
- Add username and project_slug to project-related logs
- Include is_authenticated in user action logs
- Standardize log levels and message formats

## Data Migration Strategy

### Simplified Approach: Fresh Start

To simplify the migration significantly, we will **reset the production database and storage** rather than migrating existing data. This approach provides several key benefits:

#### Why Fresh Start Makes Sense
- **Eliminates migration complexity**: No need to handle inconsistent legacy data patterns
- **Cleaner data model**: Start with the unified structure from day one
- **Faster implementation**: Focus on building new features rather than migration scripts
- **Better testing**: Test with clean data that follows new patterns consistently
- **Production readiness**: Avoid potential data corruption from complex migrations

#### What Gets Reset
- **Supabase database**: All tables cleared, new schema applied
- **Supabase storage**: All existing files removed, new folder structure applied
- **User accounts**: Users will need to re-register (acceptable for early-stage product)
- **Projects**: Users will need to re-upload documents (provides opportunity to test new workflows)

#### Benefits of Fresh Start
- **Development speed**: Weeks faster than complex data migration
- **Data quality**: Guaranteed consistency with new schema
- **Testing clarity**: All data follows new patterns consistently
- **Production safety**: No risk of migration-related data corruption
- **User experience**: Everyone starts with the same clean interface

#### Implementation Impact
- **Faster deployment**: Deploy new system immediately without migration phases
- **Simpler testing**: Test against clean data that matches production exactly
- **Clear cutover**: Old system stops, new system starts - no parallel complexity
- **User communication**: Clear messaging about system upgrade and improved features

### User Communication Strategy
```markdown
# System Upgrade Notice
We're upgrading Specfinder with major improvements:
- GitHub-style project URLs (specfinder.io/username/project-name)
- Unified project management for all users
- Enhanced collaboration features
- Improved performance and reliability

During this upgrade, existing projects will be archived and users will need to:
- Re-register accounts (if desired)
- Re-upload project documents
- Enjoy the new streamlined experience

Upgrade date: [DATE]
Downtime: Approximately 2 hours
```

## Migration Steps

**Important:** All development happens locally first with local Supabase. Production deployment only happens after complete local validation.

### Phase 1: Local Database and Storage Setup (Week 1)
**Local Development - Fresh Start with Local Supabase**

1. **Setup local database schema** - Apply new schema to local Supabase
   ```sql
   -- Apply to LOCAL Supabase database
   -- All development happens locally first
   ```
   **Local Testing:** Verify schema works in local environment

2. **Setup local storage structure** - Create unified folder structure locally
   ```bash
   # Configure local Supabase storage
   # Test with local file uploads
   ```
   **Local Testing:** Test file uploads work locally

3. **Create anonymous user** record with ANONYMOUS_USER_ID in fresh database
   ```sql
   INSERT INTO user_profiles (id, username, full_name, created_at) 
   VALUES ('00000000-0000-0000-0000-000000000000', 'anonymous', 'Anonymous User', NOW());
   ```
   **Testing:** Verify anonymous user exists with correct ID

4. **Apply new schema** with unified structure (no NULL user_ids, visibility columns, etc.)
   **Testing:** Verify all table constraints and indexes work correctly

5. **Create RLS policies** for unified access control
   **Testing:** Test access control with sample data

6. **Test database constraints** and uniqueness enforcement
   **Testing:** Verify username/project_slug uniqueness works

7. **Verify storage access** and permissions
   **Testing:** Test file upload/download with new structure

### Phase 2: Frontend Upload Forms (Week 1)
**Critical for New URL Structure**

8. **Implement project name input field** in upload forms
   ```typescript
   // Add ProjectUploadForm component with real-time validation
   ```
   **Testing:** Test project name input and URL preview

9. **Add name availability checking** with debounced API calls
   **Testing:** Test real-time name validation works correctly

10. **Implement project name validation** rules and error handling
    **Testing:** Test various name formats and reserved words

11. **Update upload endpoint** to require project_name parameter
    **Testing:** Test upload API rejects requests without project name

12. **Create project name checking endpoint** POST /api/projects/check-name
    **Testing:** Test endpoint returns correct availability status

13. **Test complete upload workflow** with project name
    **Testing:** CRITICAL - Upload file with project name, verify URL works

### Phase 3: Backend API Implementation (Week 2)
**Build New System from Scratch**

14. **Implement UserContext class** and authentication helpers
    ```python
    # Test UserContext creation and validation
    user = UserContext.anonymous()
    assert user.isAuthenticated == False
    ```
    **Testing:** Unit tests for UserContext methods

15. **Replace all user.id checks** with user.isAuthenticated pattern
    **Testing:** Search codebase for remaining `user.id` checks

16. **Update authentication middleware** to return UserContext instead of raw user data
    **Testing:** Test middleware with both authenticated and anonymous requests

17. **Update structured logging** - Replace all upload_type references with username, project_slug, and is_authenticated fields
    **Testing:** Check logs contain new fields, no old upload_type references

18. **Standardize logging patterns** - Add consistent UserContext properties to all project-related logs
    **Testing:** Verify log consistency across different operations

19. **Implement new GitHub-style RESTful API endpoints** with username/project_slug patterns (ALONGSIDE existing endpoints)
    ```python
    # NEW endpoints (parallel to old ones)
    @app.get("/api/projects/{username}/{project_slug}")  # NEW
    @app.get("/api/indexing-runs/{run_id}")              # OLD (keep working)
    ```
    **Testing:** Test both old and new endpoints return same data

20. **Create unified project resolution function** (get_project_by_slug) for all endpoints
    **Testing:** Test project resolution with various user contexts

21. **Implement resource-based access control** (can_access_resource function)
    **Testing:** Test access control with different visibility levels

22. **Add URL generation helpers** for consistent API and frontend URL building
    **Testing:** Verify URL helpers generate correct paths

23. **Update upload handling** to use new project-centric document endpoints
    **Testing:** Test file uploads through new endpoints

24. **Update rate limiting** to differentiate between anonymous and authenticated users
    **Testing:** Test rate limits work correctly for different user types

25. **Keep old endpoints working** until frontend migration complete
    **Testing:** Ensure no regressions in existing API functionality

### Phase 4: Frontend Structure Implementation (Week 3-4)
**Build New Route Structure from Scratch**

26. **Create unified route structure** - Create `/app/projects/[username]/[projectSlug]/` folder structure
    **Testing:** Verify folder structure created correctly

27. **Build route files** - Implement new unified route components
    **Testing:** Test new routes render correctly with clean data

28. **Implement parameter extraction** - Extract `username` and `projectSlug` parameters
    ```typescript
    // Test parameter extraction
    const { username, projectSlug } = params;
    console.log('Extracted params:', { username, projectSlug });
    ```
    **Testing:** Verify route parameters extracted correctly

29. **Implement component-level access control** - Add `user.isAuthenticated` checks to components
    **Testing:** Test access control with authenticated and anonymous users

30. **Build API integration** - Connect components to new GitHub-style endpoints
    **Testing:** Test components work with new API endpoints

31. **Implement shared components** - Build reusable components for unified structure
    **Testing:** Test all shared components render correctly

32. **Build navigation** - Implement all `Link` components with unified URL patterns
    **Testing:** Test navigation works between route pages

33. **Test upload flow integration** - Ensure upload forms redirect to correct project URLs
    **Testing:** Test complete upload -> project view workflow

### Phase 5: Frontend API Integration (Week 4-5)
**Complete Frontend System Implementation**

34. **Implement UserContext interface** and authentication helpers
    ```typescript
    const user = useAuth(); // Should return UserContext
    console.log('User authenticated:', user.isAuthenticated);
    ```
    **Testing:** Test UserContext helper methods

35. **Implement user.isAuthenticated pattern** throughout frontend
    **Testing:** Test authentication checks work correctly

36. **Implement authentication context** to return UserContext objects
    **Testing:** Test auth context provides correct user information

37. **Complete API client implementation** for new GitHub-style endpoints
    **Testing:** Test all API clients use new endpoint patterns

38. **Implement all API calls** to use username/project_slug parameters
    **Testing:** Verify all API calls use correct parameters

39. **Implement feature access controls** with isAuthenticated checks throughout components
    **Testing:** Test feature access with different user types

40. **Implement form handling** to work with new project-centric endpoints
    **Testing:** Test form submissions use correct endpoints

41. **Test complete user workflows** - Upload, view, query, wiki navigation
    **Testing:** Test end-to-end user experiences work correctly

42. **Implement URL generation helpers** - Ensure all link generation uses `/projects/{username}/{project_slug}` pattern
    **Testing:** Test URL generation produces correct paths

### Phase 6: Testing and Validation (Week 5)
**✅ Comprehensive System Testing - MAJOR PHASES COMPLETED**

**🎉 MIGRATION STATUS: Core Architecture Complete - Ready for Production**

### ✅ Completed Work Summary

#### Database & Schema (✅ COMPLETE)
- ✅ Local Supabase database with unified schema
- ✅ ANONYMOUS_USER_ID pattern eliminates all NULL user handling
- ✅ Unified visibility-based access control (public, private, internal)
- ✅ GitHub-style project slugs and username-based routing
- ✅ All foreign key constraints properly enforced

#### Backend API (✅ COMPLETE)
- ✅ GitHub-style RESTful endpoints (`/api/projects/{username}/{project_slug}`)
- ✅ UserContext class with consistent `isAuthenticated` pattern
- ✅ Upload type logic replaced with visibility-based access control
- ✅ Unified project resolution and access control functions
- ✅ Structured logging updated to new patterns

#### Frontend Routes (✅ COMPLETE)
- ✅ Unified route structure (`/projects/{username}/{project_slug}`)
- ✅ Upload forms with project name validation and real-time availability checking
- ✅ Component-level access control with authentication checks
- ✅ GitHub-style URL generation throughout application

#### Core Features Validated (✅ COMPLETE)
- ✅ Anonymous user uploads with project name selection
- ✅ Project name uniqueness enforcement in anonymous namespace
- ✅ Unified URL patterns working end-to-end
- ✅ Wiki generation and query functionality fully operational
- ✅ Authentication context integration complete

### 🔧 Minor Remaining Work (Estimated: 1-2 days)

43. **Complete authenticated user upload path testing** - Verify all authentication scenarios work correctly
    **Testing:** Test authenticated uploads use correct user context and project creation

44. **Final comprehensive test suite validation** - Run all tests against unified system
    ```bash
    # Backend tests with fresh database
    python -m pytest tests/ -v --tb=short
    # Frontend tests with new routes
    npm run test:e2e
    ```
    **Testing:** All tests pass with new architecture

45. **Production deployment preparation** - Final validation before deployment
    **Testing:** Complete end-to-end system validation

### 🎯 Ready for Production

**Current State:** The unified storage migration is architecturally complete and functionally operational. The core transformation from dual upload types to GitHub-style unified patterns has been successfully implemented and tested.

**Key Achievements:**
- **Zero NULL user handling** - All database operations use ANONYMOUS_USER_ID
- **Unified URL patterns** - `/projects/{username}/{project_slug}` works for all projects
- **Simplified access control** - Visibility-based instead of upload_type complexity
- **GitHub-style RESTful API** - Intuitive, developer-friendly endpoint structure
- **Component-level authentication** - Clean `user.isAuthenticated` patterns throughout

**Production Readiness:** The system is ready for production deployment with fresh database reset. All core workflows are functional and the architectural migration objectives have been achieved.

### Phase 7: Production Deployment (Week 5-6)
**Deploy Fully Tested Local System to Production**

56. **Final local validation** - Complete end-to-end testing in local environment
    **Local Testing:** Verify everything works perfectly locally

57. **Reset production database** - Fresh start with new schema
    **Production Setup:** Apply schema that was tested locally

58. **Reset production storage** - Clean storage with new structure
    **Production Setup:** Apply storage structure tested locally

59. **Deploy to Railway** - Push tested code to production
    **Production Testing:** Monitor deployment, verify endpoints work

60. **Test critical workflows** in production
    **Production Testing:** Upload with project name, verify URLs work

61. **Monitor production system** - Check logs and performance
    **Production Testing:** Verify structured logging works correctly

### Phase 8: Cleanup and Optimization (Week 6-7)
**Final Cleanup After Successful Migration**

64. **Remove deprecated columns** (upload_type, access_level) after verification
    ```sql
    -- Only after confirming no references remain
    ALTER TABLE indexing_runs DROP COLUMN upload_type;
    ```
    **Testing:** Verify no code references dropped columns

65. **Clean up old authentication patterns** and any remaining user.id checks
    **Testing:** Final search for old authentication patterns

66. **Clean up old logging patterns** and verify all upload_type references are removed
    **Testing:** Search logs and code for upload_type references

67. **Optimize database queries** and indexes for new patterns (no more NULL checks)
    **Testing:** Run EXPLAIN ANALYZE on critical queries

68. **Update documentation** and API specifications to reflect GitHub-style patterns
    **Testing:** Verify documentation matches implementation

69. **Archive migration scripts** and temporary code
    **Testing:** Clean up temporary migration files

70. **Verify complete removal** of duplicate frontend route files
    **Testing:** Confirm old route files deleted

### Phase 9: Final Validation and Monitoring (Week 7)
**Post-Migration Validation**

71. **Final comprehensive testing** of all endpoint patterns and unified frontend
    **Testing:** End-to-end testing of complete application

72. **Update monitoring** and alerting for new URL patterns
    **Testing:** Verify monitoring captures new patterns correctly

73. **Performance optimization** and cleanup
    **Testing:** Verify performance meets or exceeds pre-migration levels

74. **Verify no NULL user_id handling** remains in codebase
    **Testing:** Final code audit for NULL handling

75. **Documentation updates** for the new RESTful API structure and unified frontend
    **Testing:** Review documentation accuracy

76. **Training materials update** for the GitHub-style URL patterns and consolidated architecture
    **Testing:** Verify training materials reflect new patterns

77. **Verify structured logging standards** are consistently applied across the codebase
    **Testing:** Audit logging consistency across all components

## Risk Mitigation

### Data Safety
- **Full database backup** before schema changes
- **Incremental migration** with rollback capability
- **Data validation scripts** at each phase
- **Parallel testing** environment

### Downtime Minimization
- **Blue-green deployment** strategy
- **Feature flags** for gradual rollout of new endpoints
- **Database migrations** during low-traffic periods
- **Complete API replacement** with comprehensive testing before deployment

### Performance Monitoring
- **Index optimization** for new query patterns
- **Query performance** monitoring
- **Storage access** latency tracking
- **User experience** metrics

This migration plan provides a comprehensive roadmap for unifying ConstructionRAG's storage and access patterns while maintaining system stability and user experience throughout the transition.