# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Claude rules
- Make a plan before coding. Do not code until I have confirmed the plan looks good.
- Do not use git commands unless explicitly told to 
- Before implementing new use of frontend API calls, then make the API calls as curl commands to test they return what you expect them to return before implementing it in the code.

## Authentication & RLS (Row Level Security) Best Practices

### Critical: Backend Authenticated Requests
When creating backend API endpoints that need to access user-specific data with RLS policies:

**✅ CORRECT Pattern:**
```python
@router.get("/user-data")
async def get_user_data(
    current_user: dict[str, Any] = Depends(get_current_user),
    db_client = Depends(get_db_client_for_request),  # ← Use authenticated client
):
    db = db_client  # This client includes the user's JWT for RLS
    result = db.table("user_specific_table").select("*").execute()
```

**❌ WRONG Pattern:**
```python
@router.get("/user-data") 
async def get_user_data(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    db = get_supabase_client()  # ← This is the anon client - RLS will block queries!
    result = db.table("user_specific_table").select("*").execute()  # Returns 0 rows
```

**Why this matters:** Supabase RLS policies require the authenticated user's JWT token to determine data access. The anon client (`get_supabase_client()`) doesn't have this context, so RLS policies will block all queries even if the user is authenticated at the API level. 


## Core development philosophy
KISS (Keep It Simple, Stupid)
Simplicity should be a key goal in design. Choose straightforward solutions over complex ones whenever possible. Simple solutions are easier to understand, maintain, and debug.

YAGNI (You Aren't Gonna Need It)
Avoid building functionality on speculation. Implement features only when they are needed, not when you anticipate they might be useful in the future.

Design Principles
   Single Responsibility: Each function, class, and module should have one clear purpose.
   Fail Fast: Check for potential errors early and raise exceptions immediately when issues occur.

File and Function Limits
   Never create a file longer than 500 lines of code. If approaching this limit, refactor by splitting into modules.
   Functions should be under 50 lines with a single, clear responsibility.
   Classes should be under 100 lines and represent a single concept or entity.
   Organize code into clearly separated modules, grouped by feature or responsibility.

Python style guide
- Format with ruff format (faster alternative to Black)
- Use async/await for I/O operations
- Type hints required for all functions
- Pydantic models for validation and settings management
- Early returns for error conditions. Consistent error handling from middleware. 
- Functional programming preferred over classes

## Project Overview

ConstructionRAG is a production-ready AI-powered construction document processing and Q&A system. It's a "DeepWiki for Construction Sites" that automatically processes construction documents and enables intelligent Q&A about project requirements, timelines, and specifications.

### Key Technologies
- **Backend**: FastAPI (Python) - deployed on Railway
- **Production React Frontend**: Not developed yet - also to be deployed on Railway
- **Development Frontend**: Streamlit - deployed on Streamlit Cloud
- **Database**: Supabase (PostgreSQL with pgvector)
- **AI Services**: Voyage AI (embeddings), OpenRouter (generation & VLM)
- **Language**: Optimized for Danish construction documents currently. To be made multilingual. 

## Development Commands

### Local Development
```bash
# Start full stack
docker-compose up --build

# Backend only (from backend/ directory)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend only (from frontend/ directory)
npm run dev

# Legacy frontend
streamlit run streamlit_app/main.py --server.port 8501

# Run tests (from backend/ directory)
python run_tests.py
pytest tests/integration/
pytest tests/unit/

# Code quality (from backend/ directory)
Code style: ruff format .
Lint: ruff check .
Types: mypy .
```

### Prod development
Railway automatically updates on git pushes. Uses Dockerfile from /backend repository.
Updates to indexing run requires cd backend && beam deploy beam-app.py:process_documents
Streamlit updates automatically on git pushes.

Backend to Railway
Indexing run on Beam
Development Frontend on Streamlit
Production React Frontend on Railway (future) 

### URLs
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
│   │   └── api/             # API routes
│   ├── components/          # Reusable UI components
│   └── lib/                 # Utilities and helpers
├── package.json             # Node.js dependencies
├── Dockerfile               # Production build
└── railway.toml             # Railway deployment config

```

### Pipeline Processing Flow

1. **Indexing Pipeline** (Document → Knowledge Base):
   - **Partition**: Extract text, tables, images from PDFs (supports PyMuPDF)
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
- Hot reloading: configuration changes take effect immediately
- YAML-based config deprecated in favor of single source of truth approach

## Key Development Practices

### Database Operations
- Uses **production Supabase database** (not local)
- All database operations via Supabase client
- Vector operations use pgvector extension
- Migrations applied directly to production - push after writing

### Access Control & Security
- **Access Levels**: `public` (anonymous), `auth` (any authenticated user), `owner` (policies), `private` (resource owner only)
- **Upload Types**: `email` (public access), `user_project` (authenticated access with RLS)
- **RLS Policies**: Row-level security enforces user-specific data access in Supabase
- All endpoints validate ownership via access levels and database policies
- Anonymous users can only access `email` upload type resources


### Pipeline Development
- Embedding model consistency: voyage-multilingual-2 (1024 dims) throughout
- Test basic implementation before full features
- Configuration-driven design for easy tuning
- Progress tracking for all long-running operations

### Environment Management
- Always activate venv when running tests
- Never update requirements.txt without verification
- Never commit to git without explicit instruction
- Never echo/update .env files

## Testing
```bash
backend/tests/
├── integration/             # Full pipeline tests
│   ├── test_*_step_orchestrator.py
│   ├── test_pipeline_integration.py
│   └── test_query_api_endpoints.py
└── unit/                   # Unit tests (TODO)
```

### Running Tests
- All tests: `pytest tests/` (standard pytest runner)
- Integration tests: `pytest tests/integration/`
- Unit tests: `pytest tests/unit/v2/`
- All tests use production database with proper isolation
- Tests are organized by type: integration (full pipelines), unit (service/component tests)

## Configuration Files

### Pipeline Configuration
- Environment variable substitution supported
- Validation and optimization guides included

### Key Settings
- Chunk size: 1000 chars, overlap: 200
- Embedding: voyage-multilingual-2 (1024 dims)
- Timeout: 30 minutes per pipeline step
- Max concurrent documents: 5

## Production Deployment

- **Backend**: Railway (automatic from GitHub)
- **Frontend**: Streamlit Cloud (automatic from GitHub)
- **Database**: Supabase (managed PostgreSQL)
- Health checks and monitoring configured
- SSL/TLS enabled for all endpoints

## API Endpoints

### Authentication (`/api/auth`)
- **POST** `/api/auth/signup` - Sign up new user
- **POST** `/api/auth/signin` - Sign in existing user  
- **POST** `/api/auth/signout` - Sign out current user
- **POST** `/api/auth/reset-password` - Send password reset email
- **GET** `/api/auth/me` - Get current user info (requires auth)
- **POST** `/api/auth/refresh` - Refresh access token

### Document Management (`/api`)
- **POST** `/api/uploads` - Upload PDFs (max 10 files, 50MB each) - supports anonymous (email) or authenticated (project)
- **GET** `/api/documents` - List documents with pagination and filtering
- **GET** `/api/documents/{document_id}` - Get single document details

### Indexing Pipeline (`/api`)
- **GET** `/api/indexing-runs` - List indexing runs (paginated) - optional auth
- **GET** `/api/indexing-runs/{run_id}` - Get single indexing run - optional auth
- **GET** `/api/indexing-runs/{run_id}/progress` - Get detailed progress - optional auth
- **POST** `/api/indexing-runs` - Create project-based indexing run (requires auth) - use `/api/uploads` for email uploads

### Query System (`/api`)
- **POST** `/api/queries` - Create and execute query (optional auth)
- **GET** `/api/queries` - List previous queries (paginated)
- **GET** `/api/queries/{query_id}` - Get specific query results

### Project Management (`/api`)
- **POST** `/api/projects` - Create project (requires auth)
- **GET** `/api/projects` - List user projects (requires auth)
- **GET** `/api/projects/{project_id}` - Get specific project
- **PATCH** `/api/projects/{project_id}` - Update project
- **DELETE** `/api/projects/{project_id}` - Delete project

### Wiki Generation (`/api/wiki`)
- **POST** `/api/wiki/runs` - Create wiki generation run
- **GET** `/api/wiki/runs/{index_run_id}` - List wiki runs for indexing run
- **GET** `/api/wiki/runs/{wiki_run_id}/pages` - Get wiki pages metadata
- **GET** `/api/wiki/runs/{wiki_run_id}/pages/{page_name}` - Get wiki page content
- **GET** `/api/wiki/runs/{wiki_run_id}/metadata` - Get wiki metadata
- **DELETE** `/api/wiki/runs/{wiki_run_id}` - Delete wiki run
- **GET** `/api/wiki/runs/{wiki_run_id}/status` - Get wiki run status

### System Endpoints
- **GET** `/` - API status message
- **GET** `/health` - Health check for monitoring
- **GET** `/api/health` - API-specific health check
- **GET** `/api/debug/env` - Environment debug (development only)

## Important Notes

- Never use `rm` command without approval
- Clean up test files after use (propose, don't auto-delete)
- Construction-specific optimizations for Danish language
- Pipeline processing can take up to 30 minutes for large documents
- All AI service calls include retry logic and error handling