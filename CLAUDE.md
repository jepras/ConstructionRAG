# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ConstructionRAG is a production-ready AI-powered construction document processing and Q&A system. It's a "DeepWiki for Construction Sites" that automatically processes construction documents and enables intelligent Q&A about project requirements, timelines, and specifications.

### Key Technologies
- **Backend**: FastAPI (Python) - deployed on Railway
- **Frontend**: Streamlit - deployed on Streamlit Cloud
- **Database**: Supabase (PostgreSQL with pgvector)
- **AI Services**: Voyage AI (embeddings), OpenRouter (generation), Anthropic (VLM)
- **Language**: Optimized for Danish construction documents

## Development Commands

### Local Development
```bash
# Start full stack
docker-compose up --build

# Backend only (from backend/ directory)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend only (from frontend/ directory)
streamlit run streamlit_app/main.py --server.port 8501

# Run tests (from backend/ directory)
python run_tests.py
pytest tests/integration/
pytest tests/unit/

# Code quality (from backend/ directory)
black .
isort .
flake8 .
mypy .
```

### URLs
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

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
│   │   │   └── config/      # Pipeline configuration (YAML)
│   │   └── querying/        # Query processing pipeline
│   │       ├── steps/       # Query Processing → Retrieval → Generation
│   │       └── config/      # Query configuration (YAML)
│   ├── services/            # Business logic
│   ├── models/              # Pydantic data models
│   └── config/              # App configuration

frontend/streamlit_app/
├── main.py                  # Main Streamlit app
├── pages/                   # Multi-page app structure
├── components/              # Reusable UI components
└── utils/                   # Frontend utilities
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

### Configuration Management
- Pipeline settings in YAML files: `backend/src/pipeline/*/config/*.yaml`
- Environment variables in `.env` files (never commit these)
- Hot reloading: configuration changes take effect immediately

## Key Development Practices

### Database Operations
- Uses **production Supabase database** (not local)
- All database operations via Supabase client
- Vector operations use pgvector extension
- Migrations applied directly to production - push after writing

### Code Style (from .cursor/rules)
- Use async/await for I/O operations
- Type hints required for all functions
- Pydantic models for validation
- Early returns for error conditions
- Functional programming preferred over classes
- Snake_case for files/directories

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

### Test Structure
```bash
backend/tests/
├── integration/             # Full pipeline tests
│   ├── test_*_step_orchestrator.py
│   ├── test_pipeline_integration.py
│   └── test_query_api_endpoints.py
└── unit/                   # Unit tests (TODO)
```

### Running Tests
- Integration tests: `python run_tests.py` (custom runner)
- Specific tests: `pytest tests/integration/test_*.py`
- All tests use production database with proper isolation

## Configuration Files

### Pipeline Configuration
- `indexing_config.yaml`: Document processing parameters
- `query_config.yaml`: Query processing parameters
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

## Important Notes

- Never use `rm` command without approval
- Clean up test files after use (propose, don't auto-delete)
- Construction-specific optimizations for Danish language
- Pipeline processing can take up to 30 minutes for large documents
- All AI service calls include retry logic and error handling