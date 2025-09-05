# ConstructionRAG Documentation

Welcome to the ConstructionRAG documentation. This AI-optimized structure helps both humans and AI assistants navigate the codebase effectively.

## Quick Navigation for AI Assistants

When working with this codebase, refer to these documents based on your task:

- **Building features?** → Start with `ARCHITECTURE.md` for system design
- **Indexing documents?** → See `features/indexing-pipeline.md`
- **Working with APIs?** → Check `api/endpoints.md`
- **Deployment issues?** → Read `implementation/deployment.md`
- **Database queries?** → Review `implementation/database.md`
- **Authentication?** → See `implementation/authentication.md`
- **Debugging problems?** → Check `troubleshooting/common-errors.md`

## System Overview

ConstructionRAG is a production-ready AI-powered construction document processing and Q&A system. It's a "DeepWiki for Construction Sites" that automatically processes construction documents and enables intelligent Q&A about project requirements, timelines, and specifications.

### Key Technologies
- **Backend**: FastAPI (Python) deployed on Railway
- **Frontend**: Next.js 15.3 with App Router deployed on Railway
- **Database**: Supabase (PostgreSQL with pgvector)
- **Processing**: Beam for compute-intensive tasks
- **AI Services**: Voyage AI (embeddings), OpenRouter (VLM)
- **Language**: Optimized for Danish construction documents

## Documentation Structure

### Core Documents

#### [ARCHITECTURE.md](./ARCHITECTURE.md)
System-wide design decisions, component relationships, and data flow patterns. Start here to understand how the system works at a high level.

#### [CONTRIBUTING.md](./CONTRIBUTING.md)
Development guidelines, code standards, and contribution workflow for developers working on the codebase.

### Feature Documentation

#### [features/indexing-pipeline.md](./features/indexing-pipeline.md)
Complete documentation of the 5-stage indexing pipeline that processes PDFs into searchable knowledge:
- Partition → Metadata → Enrichment → Chunking → Embedding
- Beam integration and webhook workflows
- Configuration and troubleshooting

#### [features/wiki-generation.md](./features/wiki-generation.md)
Wiki generation system that creates structured documentation from indexed content:
- Semantic clustering and page organization
- Markdown generation with navigation
- Webhook-triggered automation

#### [features/query-system.md](./features/query-system.md)
RAG (Retrieval-Augmented Generation) system for intelligent Q&A:
- Query processing and enhancement
- Vector similarity search
- Response generation with citations

#### [features/project-management.md](./features/project-management.md)
User projects and permission system:
- Multi-tenant architecture with RLS
- Public vs private access patterns
- Project lifecycle management

### API Documentation

#### [api/endpoints.md](./api/endpoints.md)
Complete REST API reference with all endpoints:
- Authentication endpoints
- Document management
- Indexing and query operations
- Wiki generation

#### [api/webhooks.md](./api/webhooks.md)
Webhook integration patterns:
- Beam completion webhooks
- Wiki generation triggers
- Event-driven architecture

#### [api/examples.md](./api/examples.md)
Request/response examples for common operations:
- File uploads
- Query execution
- Project creation

### Implementation Guides

#### [implementation/database.md](./implementation/database.md)
Database schema, queries, and patterns:
- Table structures with relationships
- pgvector configuration
- RLS policies and access control

#### [implementation/authentication.md](./implementation/authentication.md)
Authentication and authorization implementation:
- Supabase Auth integration
- JWT token management
- Access level enforcement

#### [implementation/deployment.md](./implementation/deployment.md)
Deployment processes and configuration:
- Railway deployment for backend/frontend
- Beam deployment for processing
- Environment variable management

#### [implementation/configuration.md](./implementation/configuration.md)
Configuration management strategy:
- pipeline_config.json structure
- Environment-specific settings
- Feature flags and overrides

### Troubleshooting Guides

#### [troubleshooting/common-errors.md](./troubleshooting/common-errors.md)
Solutions for frequently encountered errors:
- PDF processing failures
- API rate limits
- Database connection issues

#### [troubleshooting/debugging.md](./troubleshooting/debugging.md)
Debug strategies and tools:
- Logging configuration
- Performance profiling
- Local development setup

#### [troubleshooting/performance.md](./troubleshooting/performance.md)
Performance optimization tips:
- Query optimization
- Caching strategies
- Resource management

## Key File Locations

For AI assistants and developers, here are the critical file paths:

### Backend
- **Main API**: `/backend/src/main.py`
- **Pipeline Entry**: `/backend/src/pipeline/indexing/pipeline.py`
- **Configuration**: `/backend/src/config/pipeline/pipeline_config.json`
- **Database Models**: `/backend/src/models/`
- **API Endpoints**: `/backend/src/api/`

### Frontend
- **App Layout**: `/frontend/src/app/layout.tsx`
- **Home Page**: `/frontend/src/app/page.tsx`
- **Project Pages**: `/frontend/src/app/projects/[indexingRunId]/`
- **Dashboard**: `/frontend/src/app/(app)/dashboard/`
- **API Routes**: `/frontend/src/app/api/`

### Tests
- **Integration Tests**: `/backend/tests/integration/`
- **Unit Tests**: `/backend/tests/unit/v2/`

## Environment Setup

### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

# AI Services
VOYAGE_API_KEY=...
OPENROUTER_API_KEY=...

# Processing
BEAM_WEBHOOK_URL=...
BEAM_AUTH_TOKEN=...

# Backend
BACKEND_API_URL=http://localhost:8000
SECRET_KEY=...
```

### Local Development
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Quick Start Commands

### Running the System
```bash
# Start everything
docker-compose up

# Backend only
cd backend && uvicorn src.main:app --reload

# Frontend only
cd frontend && npm run dev
```

### Testing
```bash
# All tests
cd backend && pytest tests/

# Integration tests only
pytest tests/integration/

# Unit tests only
pytest tests/unit/v2/
```

### Deployment
```bash
# Deploy backend to Railway
git push origin main

# Deploy indexing to Beam
cd backend && beam deploy beam-app.py:process_documents
```

## Documentation Maintenance

When updating documentation:
1. Keep information in single files (avoid splitting topics)
2. Use consistent headers and structure
3. Include file paths and line numbers for code references
4. Update cross-references when moving content
5. Maintain the README navigation when adding new docs

## Support

For issues or questions:
- GitHub Issues: Report bugs or request features
- Documentation: Check relevant guides above
- Logs: Enable DEBUG logging for detailed information