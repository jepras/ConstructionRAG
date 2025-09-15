# CLAUDE.md
This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Claude rules
- Make a plan before coding. Do not code until I have confirmed the plan looks good.
- Do not use git commands unless explicitly told to.
- Before implementing new use of frontend API calls, then make the API calls as curl commands to test they return what you expect them to return before implementing it in the code.
- When creating tests to verify new features, look to the existing test functions and the test helper functions to see if any code can be reused to check your code and implementation. I want you to be a contributor to my codebase, not a generator of standalone scripts.
- Never use `rm` command without approval

## Core development philosophy
KISS (Keep It Simple, Stupid)
Simplicity should be a key goal in design. Choose straightforward solutions over complex ones whenever possible. Simple solutions are easier to understand, maintain, and debug.

YAGNI (You Aren't Gonna Need It)
Avoid building functionality on speculation. Implement features only when they are needed, not when you anticipate they might be useful in the future.

Design Principles
- Single Responsibility: Each function, class, and module should have one clear purpose.
- Fail Fast: Check for potential errors early and raise exceptions immediately when issues occur.

File and Function Limits
- Never create a file longer than 500 lines of code. If approaching this limit, refactor by splitting into modules.
- Functions should be under 50 lines with a single, clear responsibility.
- Classes should be under 100 lines and represent a single concept or entity.
- Organize code into clearly separated modules, grouped by feature or responsibility.

Python style guide
- Format with ruff format (faster alternative to Black)
- Use async/await for I/O operations
- Type hints required for all functions
- Pydantic models for validation and settings management
- Early returns for error conditions. Consistent error handling from middleware. 
- Functional programming preferred over classes

## Project Overview
Specfinder is a production-ready AI-powered construction document processing and Q&A system. It's a "DeepWiki for Construction Sites" that automatically processes construction documents and enables intelligent Q&A about project requirements, timelines, and specifications.

### Key Technologies
- **Backend**: FastAPI (Python) - deployed on Railway
- **Production React Frontend**: Next.js 15.3 with App Router - deployed on Railway
- **Development Frontend**: Streamlit - deployed on Streamlit Cloud (legacy)
- **Database**: Supabase (PostgreSQL with pgvector)
- **AI Services**: Voyage AI (embeddings), OpenRouter (generation & VLM)
- **Language**: Optimized for Danish construction documents currently. To be made multilingual. 

### Prod development
Railway automatically updates on git pushes. Uses Dockerfile from /backend repository.
Updates to indexing run requires cd backend && beam deploy beam-app.py:process_documents
Streamlit updates automatically on git pushes.

Backend to Railway
Indexing run on Beam
Development Frontend on Streamlit
Production React Frontend on Railway 

### URLs

#### Production
- **Frontend**: https://specfinder.io
- **Backend API**: https://api.specfinder.io
- **API Documentation**: https://api.specfinder.io/docs
- **Important**: Frontend production environment variables are correctly configured to point to production API URLs. Do not suggest env var configuration issues for production.

#### Local Development
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Legacy Streamlit Frontend: http://localhost:8501 (if running)

## Architecture

### High-Level Structure
```
backend/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── api/                 # REST endpoints
│   ├── pipeline/            # Core RAG pipeline
│   │   ├── indexing/        # Document processing (5 steps)
│   │   │   ├── steps/       # Partition → Metadata → Enrichment → Chunking → Embedding
│   │   ├── querying/        # Query processing pipeline
│   │   │   ├── steps/       # Query Processing → Retrieval → Generation
│   │   └─── wiki_generation/
│   ├── services/            # Business logic
│   ├── models/              # Pydantic data models
│   └── config/              # App configuration

frontend/
├── src/
│   ├── app/                 # Next.js App Router
│   │   ├── layout.tsx       # Root layout
│   │   ├── page.tsx         # Home page
│   │   ├── projects/        # Public projects (anonymous access)
│   │   │   └── [indexingRunId]/  # Single-slug format
│   │   ├── (app)/          # Authenticated app routes
│   │   │   └── dashboard/   # Private projects and user management
│   │   │       └── projects/[projectSlug]/[runId]/  # Nested format
│   │   └── api/             # API routes
│   ├── components/          # Reusable UI components
│   │   └── features/
│   │       └── project-pages/  # Shared components for public/private
│   └── lib/                 # Utilities and helpers
├── package.json             # Node.js dependencies
├── Dockerfile               # Production build
└── railway.toml             # Railway deployment config

```

### Pipeline Processing Flow

1. **Indexing Pipeline** (Document → Knowledge Base):
   - **Partition**: Extract text, tables, images from PDFs (supports PyMuPDF & Unstructured)
   - **Metadata**: Extract document structure and metadata
   - **Enrichment**: Generate VLM captions for tables/images using Anthropic
   - **Chunking**: Semantic chunking with 1000 chars, 200 overlap
   - **Embedding**: Voyage-multilingual-2 (1024 dimensions)

2. **Query Pipeline** (Question → Answer):
   - **Query Processing**: Generate semantic variations and HyDE queries
   - **Retrieval**: Vector similarity search using pgvector
   - **Generation**: OpenRouter models for response generation

3. **Wiki Generation Pipeline** (Indexed Documents → Structured Wiki):
   - **Metadata Collection**: Extract document metadata and structure
   - **Overview Generation**: Create project overview from collected data
   - **Semantic Clustering**: Group related content by semantic similarity
   - **Structure Generation**: Define wiki page hierarchy and navigation
   - **Page Content Retrieval**: Gather relevant content for each wiki page
   - **Markdown Generation**: Generate final markdown pages with proper formatting

### Webhook Integration Flow

The current working webhook path for automatic wiki generation after indexing:

1. **Upload triggers indexing** → BeamService sends request to Beam with `webhook_url` and `webhook_api_key`
2. **Beam runs indexing** → When complete, calls webhook at `{BACKEND_API_URL}/api/wiki/internal/webhook`
3. **Webhook endpoint** → Verifies API key and triggers wiki generation in background

### Configuration Management
- Pipeline settings in single JSON SoT: `config/pipeline/pipeline_config.json`
- ConfigService loads from JSON with environment variable substitution
- Environment variables in `.env` files (never commit these)

## Key Development Practices

### Database Operations
- Uses **production Supabase database** (not local)
- All database operations via Supabase client
- Vector operations use pgvector extension
- Migrations needs to be applied with supabase db push - ask for permission before doing that. 

### Access Control & Security
- **Access Levels**: `public` (anonymous), `auth` (any authenticated user), `owner` (policies), `private` (resource owner only)
- **Upload Types**: `email` (public access), `user_project` (authenticated access with RLS)
- **RLS Policies**: Row-level security enforces user-specific data access in Supabase
- All endpoints validate ownership via access levels and database policies
- Anonymous users can only access `email` upload type resources

### Environment Management
- Always activate venv when running tests
- Never update requirements.txt without verification
- Never commit to git without explicit instruction
- Never echo/update .env files

### Running Tests
- All tests: `pytest tests/` (standard pytest runner)
- Integration tests: `pytest tests/integration/`
- Unit tests: `pytest tests/unit/v2/`
- All tests use production database with proper isolation
- Tests are organized by type: integration (full pipelines), unit (service/component tests)

## Project URL Structure

Specfinder uses **dual URL patterns** to support both public and private project access:

### Public Projects (Anonymous Access)
**URL Format:** `/projects/{indexingRunId}` (single-slug)
- `indexingRunId`: `project-name-{uuid}` (e.g., `downtown-tower-def456`)
- **Full URL**: `/projects/downtown-tower-def456`
- **Access**: Server-side rendered, no authentication required
- **Features**: Basic wiki, query, and indexing progress viewing

### Private Projects (Authenticated Access)
**URL Format:** `/dashboard/projects/{projectSlug}/{runId}` (nested)
- `projectSlug`: `project-name-{project_id}` (e.g., `downtown-tower-abc123`)
- `runId`: `{indexing_run_id}` (e.g., `def456`)
- **Full URL**: `/dashboard/projects/downtown-tower-abc123/def456`
- **Access**: Authentication required, full feature access
- **Features**: Advanced project management, settings, collaboration

This dual structure enables:
- **Public sharing**: Anonymous users can view projects without accounts
- **Authentication separation**: Clear boundaries between public and private access
- **Feature differentiation**: Public users see read-only content, authenticated users get full control
- **Backward compatibility**: Existing public URLs continue to work
- **Multi-version support**: Private projects support multiple indexing runs per project

## API Endpoints

### Authentication (`/api/auth`)
- **POST** `/api/auth/signup` - Sign up new user
- **POST** `/api/auth/signin` - Sign in existing user  
- **POST** `/api/auth/signout` - Sign out current user (requires auth)
- **POST** `/api/auth/reset-password` - Send password reset email
- **GET** `/api/auth/me` - Get current user info (requires auth)
- **POST** `/api/auth/refresh` - Refresh access token

### Document Management (`/api`)
- **POST** `/api/uploads/validate` - Validate PDFs before upload (checks file types, sizes)
- **POST** `/api/uploads` - Upload PDFs (max 10 files, 50MB each) - supports anonymous (email) or authenticated (project)
- **GET** `/api/documents` - List documents with pagination and filtering (optional auth)
- **GET** `/api/documents/{document_id}` - Get single document details (optional auth)
- **GET** `/api/documents/{document_id}/pdf` - Download PDF file (optional auth, streaming response)

### Indexing Pipeline (`/api`)
- **GET** `/api/indexing-runs` - List indexing runs (paginated) - optional auth
- **GET** `/api/indexing-runs/{run_id}` - Get single indexing run - optional auth
- **GET** `/api/indexing-runs/{run_id}/progress` - Get detailed progress - optional auth
- **POST** `/api/indexing-runs` - Create project-based indexing run (requires auth) - use `/api/uploads` for email uploads
- **GET** `/api/indexing-runs-with-wikis` - List indexing runs that have completed wikis (public email uploads only)
- **GET** `/api/user-projects-with-wikis` - List user's projects with completed wikis (requires auth)

### Query System (`/api`)
- **POST** `/api/queries` - Create and execute query (optional auth)
- **GET** `/api/queries` - List previous queries (paginated)
- **GET** `/api/queries/{query_id}` - Get specific query results

### Project Management (`/api`)
- **POST** `/api/projects` - Create project (requires auth)
- **GET** `/api/projects` - List user projects (requires auth)
- **GET** `/api/projects/{project_id}` - Get specific project with latest indexing run (requires auth)
- **PATCH** `/api/projects/{project_id}` - Update project (requires auth)
- **DELETE** `/api/projects/{project_id}` - Soft delete project (requires auth)
- **GET** `/api/projects/{project_id}/runs/{indexing_run_id}` - Get project with specific indexing run (requires auth)
- **GET** `/api/projects/{project_id}/runs` - List all indexing runs for a project (requires auth)

### Wiki Generation (`/api/wiki`)
- **POST** `/api/wiki/internal/webhook` - Internal webhook endpoint for Beam integration (requires API key)
- **POST** `/api/wiki/runs` - Create wiki generation run (optional auth)
- **GET** `/api/wiki/runs/{index_run_id}` - List wiki runs for indexing run (optional auth)
- **GET** `/api/wiki/runs/{wiki_run_id}/pages` - Get wiki pages metadata (optional auth)
- **GET** `/api/wiki/runs/{wiki_run_id}/pages/{page_name}` - Get wiki page content (optional auth)
- **GET** `/api/wiki/runs/{wiki_run_id}/metadata` - Get wiki metadata (optional auth)
- **DELETE** `/api/wiki/runs/{wiki_run_id}` - Delete wiki run (requires auth)
- **GET** `/api/wiki/runs/{wiki_run_id}/status` - Get wiki run status (optional auth)

### System Endpoints
- **GET** `/` - API status message
- **GET** `/health` - Health check for monitoring
- **GET** `/api/health` - API-specific health check
- **GET** `/api/debug/env` - Environment debug (development only)

