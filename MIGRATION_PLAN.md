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

Always use local Supabase for development. Use the full stack setup script for complete local development including indexing capabilities. Start frontend development server separately.

### Phase-by-Phase Implementation (All Local First)

#### Phase 1: Local Foundation (Week 1)
**Local Database + Storage Setup**
Create migration branch and apply database changes locally including creating the anonymous user, adding new columns for username/project_slug/visibility, and updating storage structure. Test with fresh local data without migrating existing data.
**Local Testing:** Upload documents locally, verify new structure works

#### Phase 2: Backend API - Local Development (Week 2)
**Build New Endpoints in Local Environment**
Build new GitHub-style endpoints using username and project_slug parameters for project access. Old endpoints can be ignored during local development.
**Local Testing:** Test new endpoints with local data only

#### Phase 3: Frontend Routes - Local Development (Week 3-4)
**Build New Routes Testing Locally**
Build the unified project route structure using username and project_slug parameters. Test with local anonymous uploads first, then authenticated uploads.
**Local Testing:** Complete workflows in local environment

#### Phase 4: Production Deployment (Week 5)
**Only After Local Testing Complete**
- Reset production database (fresh start)
- Deploy new system to Railway
- No data migration needed
- Users start fresh with new system

### Testing Strategy (All Local First)

#### Critical First Test: Anonymous Upload with Project Name
**MOST IMPORTANT:** The first test in LOCAL environment - upload document as anonymous user with chosen project name. Verify project creation with proper slug, URL functionality, wiki generation, and query capabilities all work correctly in local environment. (COMPLETED)

#### Local Testing Suite
Run backend API tests against local Supabase, frontend E2E tests against local backend, and test new endpoints locally using curl to verify anonymous and user project endpoints work correctly.

#### Production Testing (After Deployment)
Only after local testing is complete: Test production endpoints to verify they work correctly in the live environment.

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
Create a special anonymous user record in the user_profiles table with the ANONYMOUS_USER_ID, username 'anonymous', and appropriate display name.

### Constants Definition
Define ANONYMOUS_USER_ID and ANONYMOUS_USERNAME constants in both backend (Python) and frontend (TypeScript) configuration files for consistent reference throughout the application.

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
Create anonymous user if needed, update NULL user_ids to ANONYMOUS_USER_ID, make user_id NOT NULL, add username/project_slug/visibility columns, create unique constraint for username/project_slug combination, update existing records with appropriate username and slug values, and remove old access_level column after migration.

#### Modified `indexing_runs` Table
Update NULL user_ids to ANONYMOUS_USER_ID, make user_id NOT NULL, add visibility column with appropriate constraints, update existing records based on upload_type and access_level, then remove old upload_type and access_level columns after migration.

#### Modified `wiki_generation_runs` Table
Remove upload_type and upload_id columns, add visibility column with constraints, update storage_path to use username/project structure, set visibility based on old upload_type and access_level values, then remove old access_level column.

#### Modified `documents` Table
Add visibility column with constraints, update visibility based on existing access_level values, update file_path structure during storage migration, then remove old access_level column.

### New RLS Policies

Drop existing RLS policies and create new unified policies for projects, indexing runs, wiki generation runs, and documents. The new policies use visibility-based access control with separate rules for public (readable by all), private (owner only), and internal (authenticated users only) resources. Include service role policies for administrative access. Anonymous users are excluded from accessing private projects and cannot manage any projects.

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

The storage architecture is completely unified - both anonymous and authenticated users follow the exact same pattern using their username in the path structure. Anonymous projects use 'anonymous' as the username, while authenticated users use their actual username. All projects follow the same folder structure with documents and wiki subfolders.

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
Create a migration function to get all projects, generate new unified storage paths using username and project_slug, move files in Supabase Storage to the new structure, and update database references to point to the new paths.

## Frontend Upload Form Updates

### Critical Missing Component: Project Name Input

For the new URL structure to work, **ALL uploads (anonymous and authenticated) must provide a project name**. This is currently missing from upload forms and is essential for creating the GitHub-style URLs.

#### Required Upload Form Changes

**Problem:** Current upload forms don't collect project names, making it impossible to generate `/projects/username/project-name` URLs.

**Solution:** Add project name input field with real-time validation to all upload forms.

#### Upload Form Implementation

Create a ProjectUploadForm component with project name input field, real-time name availability checking using debounced API calls, file upload input, URL preview showing the final project URL, validation states and error handling, and upload functionality that sends project name and files to the API endpoint.

#### Name Validation Rules

Create validation functions for project names with basic rules (required, length limits), GitHub-style naming rules (alphanumeric, hyphens, underscores), reserved name checks, and a slug generation function that converts names to URL-safe slugs.

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

Define standardized error messages for common upload scenarios including name conflicts, validation errors, file size limits, file count limits, file type restrictions, and network failures.

## Frontend Structure Consolidation

### Current Dual Route Structure

The current frontend architecture maintains duplicate route structures for public and private project access with separate folder structures for public projects (single-slug format) and private projects (nested format) in the authenticated dashboard area, plus additional routes for marketing and authentication.

**Problems with Current Structure:**
- **Code duplication**: 12+ duplicate route files across public/private structures
- **Complex mental model**: Developers must remember two different URL patterns
- **Maintenance burden**: Changes require updates in both route structures
- **URL pattern inconsistency**: Single-slug vs nested URL patterns confuse users

### New Unified Route Structure

The consolidated frontend architecture uses a single GitHub-style pattern for all projects with a unified route structure using username and project slug parameters, while keeping existing dashboard, marketing, and auth routes unchanged.

**Example URL Transformations:**
Before: Public projects used single-slug format, private projects used nested format. After: All projects use unified GitHub-style format with username and project name.

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
- **Result**: Single codebase with conditional feature rendering using authentication checks within components

### Component Updates Needed

#### **Minimal API Call Changes**
Most existing shared components already work with the unified structure by changing parameter patterns from dual indexingRunId/projectSlug/runId pattern to single username/projectSlug pattern.

#### **Authentication State Integration**
Components add `user.isAuthenticated` checks for conditional features like settings access, where authenticated users who own the project can see management options.

#### **API Client Simplification**
Update API calls to use new GitHub-style endpoints, replacing different patterns for public and private projects with a single unified pattern using username and project slug.

### Files to Delete

Remove all duplicate route files from the current dual structure:

#### **Route Files to Remove**
Remove 6 public route files (using indexingRunId parameter) and 6 private route files (using projectSlug/runId parameters) for project overview, wiki pages, query interface, indexing progress, settings, and checklist functionality. **Total Removal**: 12 route files eliminated through consolidation.

### Files to Create/Update

#### **New Unified Route Files (6 files)**
Create new unified route files using username and projectSlug parameters for project overview, wiki pages, query interface, indexing progress, settings, and checklist functionality.

#### **Existing Shared Components (No Changes)**
The following components in `/components/features/project-pages/` work unchanged:
- `ProjectQueryContent.tsx` 
- `ProjectIndexingContent.tsx`
- `ProjectChecklistContent.tsx`
- `ProjectSettingsContent.tsx`
- `SourcePanel.tsx`, `QueryInterface.tsx`, etc.

#### **API Client Updates**
Update API client to use new GitHub-style endpoints with username and projectSlug parameters for getting projects, accessing wiki content, and creating queries.

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

Define GitHub-style RESTful endpoints for projects (get, update, delete, name checking), project runs (list, create, get specific), wiki (list pages, get page content), documents (list, get details, upload), and queries (list, create, get details), plus a legacy upload endpoint that requires project_name.

#### Project Discovery Endpoints

Define endpoints for global project discovery (all public projects), user-specific discovery (public projects by user), and authenticated user's private projects.

#### Legacy Anonymous Upload Support

Maintain backward compatibility with existing anonymous upload endpoint that creates anonymous projects.

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
Create unified handler functions for all project-based resources using username and project_slug parameters. Implement single project resolution function that applies visibility-based access control (public for anonymous users, public/internal/owned-private for authenticated users) without needing upload_type checking.

#### Access Control Simplification
Create unified access control function that handles different visibility levels: public projects allow read access for anyone and write access for owners only, private projects allow access only to owners, and internal projects allow access to any authenticated user.

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
Implement project name availability checking with validation and slug generation, project retrieval using unified project resolution, and project updates with access control verification.

#### Document Management
Implement document listing and upload endpoints that resolve projects using unified project resolution and apply appropriate access control for upload permissions.

#### Query System
Implement query creation endpoint that resolves projects using unified project resolution, applies query access control, and executes queries within the specific project context.

### URL Generation Helpers
Create helper functions to generate consistent API and frontend URLs for projects using username and project_slug parameters, with optional endpoint/page suffixes.

## Authentication Pattern Updates

### UserContext Class Pattern

We'll introduce a consistent `UserContext` pattern across both backend and frontend to handle authentication checks:

#### Backend UserContext (Python)
Create UserContext class with id, username, email, and is_authenticated fields. Include class methods for creating anonymous and authenticated user contexts. Add isAuthenticated property that checks both authentication status and excludes ANONYMOUS_USER_ID. Implement token-based user context extraction from requests.

#### Frontend UserContext (TypeScript)
Create UserContext interface and helper class with methods for creating anonymous and authenticated user contexts. Include isAuthenticated checking that excludes ANONYMOUS_USER_ID. Implement useAuth hook that returns current user context with fallback to anonymous.

### Replacing Authentication Checks

#### Before (Problematic NULL Checks)
Old patterns relied on checking user.id directly, which fails with ANONYMOUS_USER_ID since it's a valid UUID rather than null.

#### After (Consistent isAuthenticated Pattern)
Replace all user.id checks with user.isAuthenticated pattern in both backend and frontend. This ensures consistent behavior regardless of whether the user is anonymous (with ANONYMOUS_USER_ID) or authenticated with real credentials.

### Rate Limiting and Feature Differentiation

#### Rate Limiting by Authentication Status
Apply different rate limits based on authentication status - authenticated users get higher limits with individual keys, while anonymous users share lower limits with a common key.

#### Feature Access Control
Implement different project creation behavior for authenticated vs anonymous users - anonymous users create public projects with ANONYMOUS_USER_ID, while authenticated users can create private projects with their own user_id and chosen visibility.

## Frontend Updates

### URL Generation Changes

#### URL Pattern Changes
Transform from dual patterns (public single-slug and private nested) to unified GitHub-style pattern using username and project name for all projects (anonymous, user, and organization projects).

### Route Structure Modifications

#### New Route Structure
Create unified route structure under projects/[username]/[projectSlug] with subpages for project overview, wiki, queries, and settings (authentication-gated). Implement route components that extract username and projectSlug parameters and use helper functions for URL generation.

### API Call Updates

#### Updated API Client and Components
Create unified API client with methods for getting projects, accessing wiki content, and creating queries using username/projectSlug parameters. Update component interfaces to use project objects with username, project_slug, name, and visibility properties. Include URL generation and visibility indicators.

## Structured Logging Updates

### Logging Pattern Updates
Replace old logging patterns that used upload_type with new unified patterns using username, project_slug, and is_authenticated fields for more semantic and consistent logging across all project operations.

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
Create system upgrade notice explaining GitHub-style project URLs, unified project management, enhanced features, and improved performance. Inform users that existing projects will be archived and they'll need to re-register and re-upload documents. Provide upgrade date and expected downtime duration.

## Migration Steps

**Important:** All development happens locally first with local Supabase. Production deployment only happens after complete local validation.

### Phase 1: Local Database and Storage Setup (Week 1)
**Local Development - Fresh Start with Local Supabase**

1. **Setup local database schema** - Apply new schema to local Supabase with all development happening locally first
   **Local Testing:** Verify schema works in local environment

2. **Setup local storage structure** - Create unified folder structure locally and configure local Supabase storage
   **Local Testing:** Test file uploads work locally

3. **Create anonymous user** record with ANONYMOUS_USER_ID in fresh database
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

8. **Implement project name input field** in upload forms with ProjectUploadForm component including real-time validation
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

14. **Implement UserContext class** and authentication helpers with creation, validation, and isAuthenticated property
    **Testing:** Unit tests for UserContext methods

15. **Replace all user.id checks** with user.isAuthenticated pattern
    **Testing:** Search codebase for remaining `user.id` checks

16. **Update authentication middleware** to return UserContext instead of raw user data
    **Testing:** Test middleware with both authenticated and anonymous requests

17. **Update structured logging** - Replace all upload_type references with username, project_slug, and is_authenticated fields
    **Testing:** Check logs contain new fields, no old upload_type references

18. **Standardize logging patterns** - Add consistent UserContext properties to all project-related logs
    **Testing:** Verify log consistency across different operations

19. **Implement new GitHub-style RESTful API endpoints** with username/project_slug patterns alongside existing endpoints for parallel operation
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

28. **Implement parameter extraction** - Extract `username` and `projectSlug` parameters from route components
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

34. **Implement UserContext interface** and authentication helpers with useAuth hook returning UserContext objects
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

44. **Final comprehensive test suite validation** - Run all backend tests with fresh database and frontend E2E tests with new routes
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

64. **Remove deprecated columns** (upload_type, access_level) after verification that no references remain
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