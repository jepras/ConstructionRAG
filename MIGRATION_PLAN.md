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

### Recommended Approach: Iterative Development

Instead of following the migration steps sequentially, use this iterative approach that allows testing at each stage while maintaining system stability.

### Phase-by-Phase Implementation

#### Phase 1: Foundation (Week 1)
**Database + Storage Migration**
```bash
# Create migration branch
git checkout -b unified-storage-migration

# Database changes
- Create ANONYMOUS_USER_ID user
- Add username, project_slug, visibility columns
- Migrate existing NULL user_ids to ANONYMOUS_USER_ID
- Update storage bucket structure
```
**Testing:** Verify data migration worked, existing functionality intact

#### Phase 2: Backend API (Week 2)
**Parallel Development - Keep Old Endpoints Working**
```python
# Add new endpoints alongside existing ones
@app.get("/api/projects/{username}/{project_slug}")  # NEW
async def get_project_new(username, project_slug): ...

@app.get("/api/indexing-runs/{run_id}")  # OLD (still works)
async def get_indexing_run_old(run_id): ...
```
**Testing:** Both old and new endpoints work, data consistency maintained

#### Phase 3: Frontend Routes (Week 3-4)
**Start with Anonymous Projects (Simpler to Test)**
```typescript
// Week 3: Build /projects/anonymous/[projectSlug] first
// Test with existing anonymous data
// Week 4: Build /projects/[username]/[projectSlug]
// Migrate authenticated routes last
```
**Testing:** New routes work, old routes still functional

#### Phase 4: Gradual Cutover (Week 5)
**Remove Old Endpoints Only After Frontend Fully Migrated**
- Update frontend to use only new API endpoints
- Remove old API endpoints
- Clean up old route files
- Final testing and deployment

### Testing Strategy

#### Pre-Migration Testing
Create comprehensive test suite before migration starts:
```bash
# Backend API tests
cd backend
python -m pytest tests/integration/test_pre_migration_api.py

# Frontend E2E tests
cd frontend  
npm run test:e2e -- --spec="pre-migration.spec.ts"
```

#### During Migration Testing
Test both old and new systems work in parallel:
```bash
# Test old endpoints still work
curl /api/indexing-runs/123
curl /api/documents/456

# Test new endpoints work
curl /api/projects/anonymous/test-project
curl /api/projects/john-doe/construction-site
```

#### Post-Migration Testing
Convert existing tests to use new API structure:
```bash
# Update test files to use new endpoints
# Re-run full test suite with new API patterns
python -m pytest tests/integration/test_post_migration_api.py
npm run test:e2e -- --spec="post-migration.spec.ts"
```

### Local Development Setup

**Important:** Use local Supabase database for complete isolation:
```bash
# 1. Start local Supabase
supabase start

# 2. Start backend with webhook support  
./start-local-dev.sh

# 3. Start frontend
cd frontend && npm run dev
```

**Local Testing URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Supabase Studio: http://127.0.0.1:54323

### Benefits of Iterative Approach

1. **Always Have Working System** - Old code continues functioning
2. **Test Incrementally** - Catch issues early in development
3. **Deploy Continuously** - Railway auto-deploys as you merge to main
4. **Rollback Easily** - Can revert specific changes without affecting whole system
5. **Production Safe** - Local Supabase prevents production data corruption

### Risk Mitigation

- **Database backups** before each migration phase
- **Feature flags** to control new endpoint rollout
- **Monitoring** to track both old and new API usage
- **Gradual migration** allows time to identify and fix issues

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

## Migration Steps

**Important:** Follow the **Implementation Strategy** above for the recommended iterative approach. The steps below provide technical details for each phase but should be executed using the parallel development pattern (keeping old and new systems working simultaneously).

### Phase 1: Database Schema Migration (Week 1)
**Foundation Phase - Follow Implementation Strategy Phase 1**

1. **Create anonymous user** record with ANONYMOUS_USER_ID in user_profiles table
   ```sql
   INSERT INTO user_profiles (id, username, full_name, created_at) 
   VALUES ('00000000-0000-0000-0000-000000000000', 'anonymous', 'Anonymous User', NOW());
   ```
   **Testing:** Verify anonymous user exists with correct ID

2. **Update all NULL user_ids** across all tables to use ANONYMOUS_USER_ID
   ```sql
   -- Test query first to see affected rows
   SELECT COUNT(*) FROM projects WHERE user_id IS NULL;
   -- Then update
   UPDATE projects SET user_id = '00000000-0000-0000-0000-000000000000' WHERE user_id IS NULL;
   ```
   **Testing:** Confirm no NULL user_ids remain anywhere

3. **Make user_id columns NOT NULL** to enforce referential integrity
   **Testing:** Verify foreign key constraints work correctly

4. **Add new columns** to projects, indexing_runs, wiki_generation_runs tables
   **Testing:** Check column defaults and constraints

5. **Populate username and project_slug** fields from existing data
   **Testing:** Verify all projects have valid slugs and usernames

6. **Create unique constraints** on username/project_slug combinations
   **Testing:** Test uniqueness enforcement with sample data

7. **Implement uniqueness enforcement** for anonymous project names
   **Testing:** Try creating duplicate anonymous project names (should fail)

8. **Update RLS policies** to use visibility and handle ANONYMOUS_USER_ID correctly
   **Testing:** Test access control with anonymous and authenticated users

9. **Verify data integrity** and foreign key relationships
   **Testing:** Run comprehensive data validation queries

### Phase 2: Storage Migration (Part of Week 1)
**Storage Unification - Follow Implementation Strategy Phase 1**

10. **Create storage migration script** to move files to new unified folder structure (username/project-name for all projects)
    ```python
    # Test script first with a few files
    migrate_storage_sample_files()
    ```
    **Testing:** Verify sample files moved correctly before full migration

11. **Update file_path references** in documents table to use unified username/project-name paths
    **Testing:** Check file accessibility via new paths

12. **Verify file accessibility** after migration for both anonymous and authenticated projects
    **Testing:** Download files through API to confirm paths work

13. **Update storage_path in wiki_generation_runs** table to use unified path structure
    **Testing:** Verify wiki pages load with new storage paths

### Phase 3: Backend API Migration (Week 2)
**Parallel Development - Follow Implementation Strategy Phase 2**

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

### Phase 4: Frontend Structure Consolidation (Week 3-4)
**Follow Implementation Strategy Phase 3 - Parallel Route Development**

26. **Create unified route structure** - Create `/app/projects/[username]/[projectSlug]/` folder structure
    **Testing:** Verify folder structure created correctly

27. **Migrate route files** - Copy private route implementations (more feature-complete) to unified structure
    **Testing:** Test new routes render correctly with sample data

28. **Update parameter extraction** - Change from `projectSlug`/`runId` to `username`/`projectSlug` parameters
    ```typescript
    // Test parameter extraction
    const { username, projectSlug } = params;
    console.log('Extracted params:', { username, projectSlug });
    ```
    **Testing:** Verify route parameters extracted correctly

29. **Implement component-level access control** - Add `user.isAuthenticated` checks to shared components
    **Testing:** Test access control with authenticated and anonymous users

30. **Update API calls in components** - Migrate existing shared components to use new GitHub-style endpoints
    **Testing:** Test components work with both old and new API endpoints

31. **Test shared component compatibility** - Verify `/components/features/project-pages/` components work with new parameters
    **Testing:** Test all shared components render correctly

32. **Update internal navigation** - Change all `Link` components to use unified URL patterns (ONLY in new routes)
    **Testing:** Test navigation works between new route pages

33. **Keep old routes working** during development phase
    **Testing:** Ensure old routes still functional while new ones developed

### Phase 5: Frontend API Integration (Week 4-5)
**Complete Frontend Migration - Follow Implementation Strategy Phase 4**

34. **Implement UserContext interface** and authentication helpers
    ```typescript
    const user = useAuth(); // Should return UserContext
    console.log('User authenticated:', user.isAuthenticated);
    ```
    **Testing:** Test UserContext helper methods

35. **Replace all user?.id checks** with user.isAuthenticated pattern
    **Testing:** Search for remaining `user?.id` checks in codebase

36. **Update authentication context** to return UserContext objects
    **Testing:** Test auth context provides correct user information

37. **Complete API client migration** to new GitHub-style endpoints
    **Testing:** Test all API clients use new endpoint patterns

38. **Update all remaining API calls** to use username/project_slug parameters
    **Testing:** Verify all API calls use correct parameters

39. **Update feature access controls** to use isAuthenticated checks throughout components
    **Testing:** Test feature access with different user types

40. **Update form handling** to work with new project-centric endpoints
    **Testing:** Test form submissions use correct endpoints

41. **Delete duplicate route files** - Remove all 12 duplicate files from old public/private structures (ONLY after new routes tested):
    - Delete `/app/projects/[indexingRunId]/` (6 files)  
    - Delete `/app/(app)/dashboard/projects/[projectSlug]/[runId]/` (6 files)
    **Testing:** Verify old route deletion doesn't break anything

42. **Update URL generation helpers** - Ensure all link generation uses `/projects/{username}/{project_slug}` pattern
    **Testing:** Test URL generation produces correct paths

### Phase 6: Testing and Validation (Week 5)
**Comprehensive Testing - Follow Implementation Strategy Phase 4**

43. **Run comprehensive test suite** on new GitHub-style endpoints and unified frontend structure
    ```bash
    # Backend tests
    python -m pytest tests/ -v --tb=short
    # Frontend tests  
    npm run test:e2e
    ```
    **Testing:** All tests pass with new architecture

44. **Verify access control** works correctly for all visibility levels across both backend and frontend
    **Testing:** Test public, private, internal visibility with different user types

45. **Test anonymous vs authenticated** project access with new UserContext pattern
    **Testing:** Verify anonymous users can't access private projects

46. **Test ANONYMOUS_USER_ID handling** across all database operations
    **Testing:** Verify no NULL user_id values anywhere in database

47. **Test anonymous project name uniqueness** enforcement
    **Testing:** Try creating duplicate anonymous project names (should fail)

48. **Test isAuthenticated pattern** replaces all old authentication checks
    **Testing:** Search codebase for any remaining `user.id` or `user?.id` checks

49. **Test unified route structure** with component-level access control
    **Testing:** Test all route components with different user contexts

50. **Test new API endpoint patterns** with all HTTP methods (GET, POST, PATCH, DELETE)
    **Testing:** Verify all CRUD operations work through new endpoints

51. **Validate storage file** access and serving with new URL structure
    **Testing:** Download files, view images through new paths

52. **Performance test** new database queries and indexes
    **Testing:** Check query performance with EXPLAIN ANALYZE

53. **Test URL generation helpers** for consistency across frontend and API
    **Testing:** Verify URL helpers generate same patterns across application

54. **Remove old endpoints** (Follow Implementation Strategy Phase 4)
    ```python
    # Remove old endpoints after frontend fully migrated
    # @app.get("/api/indexing-runs/{run_id}")  # DELETE THIS
    ```
    **Testing:** Ensure frontend doesn't use any old endpoints

55. **Validate structured logging updates** work correctly across all components
    **Testing:** Check logs contain correct new fields, no old upload_type

### Phase 7: Production Deployment (Week 5-6)
**Gradual Cutover - Follow Implementation Strategy**

56. **Deploy to production** with both old and new endpoints initially
    **Testing:** Monitor both endpoint types in production

57. **Verify all NULL user_ids** have been migrated to ANONYMOUS_USER_ID in production
    **Testing:** Query production database for any remaining NULL values

58. **Monitor error rates** and performance metrics during transition
    **Testing:** Set up alerts for increased error rates

59. **Validate UserContext authentication** pattern works in production
    **Testing:** Test authentication flows work correctly

60. **Monitor GitHub-style URL** patterns and API usage
    **Testing:** Check analytics for URL pattern usage

61. **Verify unified frontend structure** serves both anonymous and authenticated users correctly
    **Testing:** Test production frontend with different user types

62. **Monitor new structured logging** patterns and ensure proper log aggregation
    **Testing:** Verify logs appear correctly in monitoring systems

63. **Complete old endpoint removal** after monitoring confirms new endpoints stable
    **Testing:** Remove old endpoints and verify no errors

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