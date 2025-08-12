# ConstructionRAG API Redesign Plan

## Overview

This document outlines the migration from the current nested/mixed API structure to a **flat, resource-based design with optional authentication** that supports both anonymous and authenticated users seamlessly.

## Design Principles

### **1. Flat Resources with Optional Auth**
- All core endpoints work without authentication
- Authentication unlocks additional features and privacy controls
- Resources exist independently with flexible access control

### **2. Access Level System**
```python
class AccessLevel(str, Enum):
    PUBLIC = "public"           # Anyone can access
    AUTHENTICATED = "auth"      # Any authenticated user  
    OWNER = "owner"            # Only resource owner
    PRIVATE = "private"        # Only owner + explicit shares
```

### **3. Resource Independence**
- Documents, indexing runs, queries, and wikis are independent resources
- Relationships expressed through foreign keys, not URL nesting
- Projects become optional organizational containers

## Target API Structure

### **Core Anonymous-Friendly Endpoints**

```
# Document Upload & Management
POST /api/uploads                    # Anonymous/auth document upload
GET  /api/uploads/{upload_id}        # Get upload status

POST /api/documents                  # Create document (auth optional)
GET  /api/documents                  # List accessible documents
GET  /api/documents/{id}             # Get document details (if accessible)
PATCH /api/documents/{id}            # Update document (if owner)
DELETE /api/documents/{id}           # Delete document (if owner)

# Indexing Pipeline
POST /api/indexing-runs              # Start indexing (for accessible documents)
GET  /api/indexing-runs              # List accessible runs
GET  /api/indexing-runs/{id}         # Get run details (if accessible)
GET  /api/indexing-runs/{id}/progress # Real-time progress
DELETE /api/indexing-runs/{id}       # Cancel/delete run (if owner)

# Query & Search
POST /api/queries                    # Ask questions (scoped to accessible content)
GET  /api/queries                    # Query history (user's or public)
GET  /api/queries/{id}               # Get query details (if accessible)

# Wiki Generation
POST /api/wikis                      # Generate wiki (for accessible indexing runs)
GET  /api/wikis                      # List accessible wikis
GET  /api/wikis/{id}                 # Get wiki details (if accessible)
GET  /api/wikis/{id}/pages           # List wiki pages
GET  /api/wikis/{id}/pages/{page}    # Get specific page content
DELETE /api/wikis/{id}               # Delete wiki (if owner)
```

### **Project Organization (Auth Required)**

```
# Project Management
POST /api/projects                   # Create project (auth required)
GET  /api/projects                   # List user's projects
GET  /api/projects/{id}              # Get project details (if owned)
PATCH /api/projects/{id}             # Update project (if owned)
DELETE /api/projects/{id}            # Delete project (if owned)


```

### **Authentication & System**

```
# Authentication (unchanged)
POST /api/auth/signup
POST /api/auth/signin
POST /api/auth/signout
GET  /api/auth/me
POST /api/auth/refresh
POST /api/auth/reset-password

# Resource Management
POST /api/resource-claims            # Claim anonymous upload after signup

# System
GET  /api/health                     # System health
GET  /api/admin/metrics              # Admin dashboard (admin only)
```

## Database Schema Updates

### **1. Add Access Control Fields**

```sql
-- Add access control to existing tables
ALTER TABLE documents ADD COLUMN access_level VARCHAR(20) DEFAULT 'private';
ALTER TABLE indexing_runs ADD COLUMN access_level VARCHAR(20) DEFAULT 'private';
ALTER TABLE query_runs ADD COLUMN access_level VARCHAR(20) DEFAULT 'private';
ALTER TABLE wiki_generation_runs ADD COLUMN access_level VARCHAR(20) DEFAULT 'private';

-- Update existing records to maintain current behavior
UPDATE documents SET access_level = 'private' WHERE user_id IS NOT NULL;
UPDATE documents SET access_level = 'public' WHERE user_id IS NULL;

-- Add indexes for performance
CREATE INDEX idx_documents_access_level ON documents(access_level);
CREATE INDEX idx_documents_user_access ON documents(user_id, access_level);
```

### **2. Update Foreign Key Constraints**

```sql
-- Make user_id nullable where appropriate (allow anonymous resources)
ALTER TABLE documents ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE indexing_runs ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE query_runs ALTER COLUMN user_id DROP NOT NULL;

-- Add cascade deletes for cleanup
ALTER TABLE indexing_runs ADD CONSTRAINT fk_documents_cascade 
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE;
```

## Implementation Plan

### **Phase 1: Foundation & Data Model (Week 1-2)**

#### **Goals:**
- Establish access control foundation
- Update database schema
- Create core auth patterns

#### **Tasks:**

**1.1 Database Schema Updates**
```bash
# Create migration
supabase migration new add_access_control_fields

# Apply schema changes
- Add access_level columns to all resource tables
- Update existing data with appropriate access levels
- Add performance indexes
- Update foreign key constraints
```

**1.2 Core Auth Infrastructure**
```python
# File: src/auth/access_control.py
class AccessLevel(str, Enum): ...
class RequestContext: ...
async def get_current_user_optional(): ...
async def check_resource_access(): ...

# File: src/models/base.py  
class AccessControlledResource(BaseModel): ...

# Update existing models to inherit from AccessControlledResource
```

**1.3 Service Layer Foundation**
```python
# File: src/services/base_service.py
class BaseService:
    async def list_resources(self, ctx: RequestContext, filters: Dict): ...
    async def get_resource(self, resource_id: UUID, ctx: RequestContext): ...
    async def create_resource(self, data: Dict, ctx: RequestContext): ...
```

**Testing:**
- Unit tests for access control functions
- Integration tests for auth context passing
- Database migration verification

---

### **Phase 2: New Upload & Document Endpoints (Week 3-4)**

#### **Goals:**
- Implement new flat document endpoints
- Support both anonymous and authenticated uploads
- Maintain backward compatibility

#### **Tasks:**

**2.1 New Document API**
```python
# File: src/api/v2/documents.py
@router.post("/uploads")
async def create_upload(): ...

@router.get("/documents")  
async def list_documents(): ...

@router.get("/documents/{document_id}")
async def get_document(): ...
```

**2.2 Enhanced Document Service**
```python
# File: src/services/document_service.py
class DocumentService(BaseService):
    async def create_upload(self, files: List[UploadFile], ctx: RequestContext): ...
    async def list_documents(self, ctx: RequestContext, filters: Dict): ...
    async def get_document(self, document_id: UUID, ctx: RequestContext): ...
```

**2.3 Access Control Implementation**
```python
# Implement permission checking in all document operations
# Add query filtering based on access levels
# Support project_id filtering as query parameter
```

**Testing:**
- Anonymous upload flows
- Authenticated upload flows  
- Access control enforcement
- Cross-user access prevention

**Backward Compatibility:**
- Keep existing `/api/email-uploads` and `/api/projects/{id}/documents` 
- Add deprecation warnings
- Internal routing to new service layer

---

### **Phase 3: Indexing Runs & Pipeline (Week 5-6)**

#### **Goals:**
- Migrate indexing run management to flat structure
- Support anonymous indexing runs
- Consolidate pipeline status endpoints

#### **Tasks:**

**3.1 New Indexing API**
```python
# File: src/api/v2/indexing_runs.py
@router.post("/indexing-runs")
async def create_indexing_run(): ...

@router.get("/indexing-runs")
async def list_indexing_runs(): ...

@router.get("/indexing-runs/{run_id}")
async def get_indexing_run(): ...

@router.get("/indexing-runs/{run_id}/progress")
async def get_indexing_progress(): ...
```

**3.2 Enhanced Pipeline Service**
```python
# File: src/services/indexing_service.py
class IndexingService(BaseService):
    async def create_run(self, document_ids: List[UUID], ctx: RequestContext): ...
    async def list_runs(self, ctx: RequestContext, filters: Dict): ...
    async def get_run_details(self, run_id: UUID, ctx: RequestContext): ...
```

**3.3 Anonymous Indexing Support**
```python
# Update Beam worker to handle anonymous indexing runs
# Modify orchestrator to support user_id = null
# Update progress tracking for anonymous runs
```

**Testing:**
- Anonymous indexing flows
- Authenticated indexing flows
- Cross-user access prevention
- Progress tracking accuracy

**Backward Compatibility:**
- Map old pipeline endpoints to new service layer
- Maintain existing response formats

---

### **Phase 4: Query System & Content Access (Week 7-8)**

#### **Goals:**
- Enable anonymous querying of public content
- Implement content scoping based on access levels
- Support flexible query filtering

#### **Tasks:**

**4.1 New Query API**
```python
# File: src/api/v2/queries.py
@router.post("/queries")
async def create_query(): ...

@router.get("/queries")
async def list_queries(): ...

@router.get("/queries/{query_id}")
async def get_query(): ...
```

**4.2 Content Scoping Service**
```python
# File: src/services/query_service.py
class QueryService(BaseService):
    async def create_query(self, query_data: Dict, ctx: RequestContext): ...
    async def get_accessible_content(self, ctx: RequestContext): ...
    async def filter_search_results(self, results: List, ctx: RequestContext): ...
```

**4.3 Retrieval Pipeline Updates**
```python
# Update retrieval step to filter by accessible documents
# Modify vector search to include access_level filtering
# Update result ranking to consider user context
```

**Testing:**
- Anonymous query capabilities
- Content access filtering  
- Search result accuracy
- Privacy enforcement

---

### **Phase 5: Wiki Generation & Projects (Week 9-10)**

#### **Goals:**
- Support anonymous wiki generation
- Implement project organization layer
- Add resource claiming functionality

#### **Tasks:**

**5.1 New Wiki API**
```python
# File: src/api/v2/wikis.py
@router.post("/wikis")
async def create_wiki(): ...

@router.get("/wikis")
async def list_wikis(): ...

@router.get("/wikis/{wiki_id}/pages")
async def get_wiki_pages(): ...
```

**5.2 Project Organization**
```python
# File: src/api/v2/projects.py
@router.post("/projects")
async def create_project(): ...

# Note: Project organization uses query parameters on core endpoints
# Example: GET /api/documents?project_id={id} instead of nested routes
```

**5.3 Resource Claiming**
```python
# File: src/api/v2/resource_claims.py
@router.post("/resource-claims")
async def create_resource_claim(): ...

# File: src/services/resource_claim_service.py
async def create_claim(self, resource_type: str, resource_id: UUID, user_id: UUID): ...
```

**Testing:**
- Anonymous wiki generation
- Project organization workflows
- Resource claiming functionality
- Permission inheritance

---

### **Phase 6: Migration & Cleanup (Week 11-12)**

#### **Goals:**
- Complete migration of frontend to new endpoints
- Remove deprecated endpoints
- Performance optimization

#### **Tasks:**

**6.1 Frontend Migration**
```typescript
// Update API client to use new endpoints
// Implement anonymous user flows
// Add access level management UI
// Test all user journeys
```

**6.2 Performance Optimization**
```python
# Add database indexes for new query patterns
# Optimize access control queries
# Implement caching for public content
# Add API response pagination
```

**6.3 Cleanup & Documentation**
```python
# Remove deprecated endpoints
# Update API documentation
# Add migration guides
# Create usage examples
```

**Testing:**
- Full end-to-end testing
- Performance benchmarking
- Security audit
- User acceptance testing

## Testing Strategy

### **Per-Phase Testing**

**Unit Tests:**
- Access control functions
- Service layer methods
- Database query builders
- Permission checking logic

**Integration Tests:**
- API endpoint functionality
- Cross-service interactions
- Database consistency
- Auth flow completeness

**End-to-End Tests:**
- Anonymous user journeys
- Authenticated user journeys
- Resource claiming flows
- Permission enforcement

### **Test Scenarios**

**Anonymous User:**
1. Upload documents via `/api/uploads`
2. Start indexing run for uploaded documents  
3. Query public content across all documents
4. Generate wiki from public indexing runs
5. View public wikis and pages

**Authenticated User:**
1. Sign up and claim previous anonymous uploads
2. Create private projects and upload documents
3. Control access levels on resources
4. Query across personal + public content
5. Organize resources into projects

**Security Testing:**
1. Attempt cross-user resource access
2. Verify anonymous users can't access private content
3. Test permission inheritance and updates
4. Validate resource ownership changes

## Migration Considerations

### **Backward Compatibility**

**Phase 1-5**: All existing endpoints remain functional
- Old endpoints internally route to new service layer
- Response formats maintained for compatibility
- Deprecation warnings added to headers

**Phase 6**: Gradual deprecation
- 30-day notice for endpoint removal
- Migration guides provided
- Automated endpoint mapping where possible

### **Data Migration**

**Existing Data:**
- All current documents/runs remain private to current owners
- Email uploads get `access_level = "public"`
- User uploads get `access_level = "private"`
- No data loss during migration

**User Communication:**
- In-app notifications about new features
- Documentation updates
- Migration guides for API consumers

### **Rollback Plan**

Each phase includes:
- Database migration rollback scripts
- Feature flags for new endpoint activation
- Monitoring for performance/error regressions
- Quick rollback to previous API version if needed

## Success Metrics

### **Technical Metrics**
- API response time maintained < 500ms
- Database query performance unchanged
- Error rate < 1% during migration
- 100% backward compatibility maintained

### **User Experience Metrics**
- Anonymous user conversion rate
- Feature adoption for access controls
- User retention through migration
- Support ticket volume

### **Business Metrics**
- Increased anonymous user engagement
- Reduced friction in user onboarding
- Improved API developer experience
- Enhanced content discoverability

---

## Conclusion

This phased approach provides a clear path from the current nested API structure to a flexible, flat design that supports both anonymous and authenticated users. Each phase builds upon the previous one while maintaining full backward compatibility until the final migration phase.

The key benefits of this design:
- **Reduced friction**: Core functionality works without signup
- **Flexible access control**: Users control privacy per resource
- **Scalable architecture**: Clean separation of concerns
- **Developer-friendly**: Predictable, RESTful patterns
- **Future-proof**: Easy to extend with new features

The migration can be completed over 12 weeks with continuous testing and validation, ensuring a smooth transition for both users and API consumers.
