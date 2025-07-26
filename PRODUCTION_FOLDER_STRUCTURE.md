# Production Folder Structure & Deployment Strategy

## Overview
This document outlines the exact folder structure and deployment strategy for the ConstructionRAG production system.

## Repository Structure

```
ConstructionRAG/
├── backend/                    # FastAPI Application (Railway Deployment)
│   ├── src/
│   │   ├── main.py            # FastAPI application entry point
│   │   ├── config/
│   │   │   ├── settings.py    # Application configuration
│   │   │   └── database.py    # Database connection setup
│   │   ├── api/
│   │   │   ├── auth.py        # Authentication endpoints
│   │   │   ├── documents.py   # Document management endpoints
│   │   │   ├── queries.py     # Query processing endpoints
│   │   │   └── pipeline.py    # Pipeline status endpoints
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py # Pipeline coordination
│   │   │   ├── partition.py   # Step 01: PDF partitioning
│   │   │   ├── metadata.py    # Step 02: Metadata extraction
│   │   │   ├── enrichment.py  # Step 03: Data enrichment
│   │   │   ├── chunking.py    # Step 04: Text chunking
│   │   │   ├── embedding.py   # Step 05: Text embedding
│   │   │   ├── storage.py     # Step 06: Vector storage
│   │   │   ├── query_processing.py # Step 07: Query processing
│   │   │   ├── retrieval.py   # Step 08: Document retrieval
│   │   │   └── generation.py  # Step 11: Response generation
│   │   ├── services/
│   │   │   ├── file_service.py # Supabase Storage file management
│   │   │   ├── auth_service.py # Supabase authentication
│   │   │   └── background_service.py # Background task management
│   │   ├── models/
│   │   │   ├── document.py    # Document data models
│   │   │   ├── query.py       # Query data models
│   │   │   └── pipeline.py    # Pipeline data models
│   │   └── utils/
│   │       ├── logging.py     # Structured logging
│   │       ├── monitoring.py  # Observability utilities
│   │       └── exceptions.py  # Custom exceptions
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── notebooks/         # Keep for exploration
│   ├── Dockerfile             # Backend Docker configuration
│   ├── requirements.txt       # Backend Python dependencies
│   ├── .dockerignore          # Docker ignore file
│   └── README.md              # Backend documentation
│
├── frontend/                  # Streamlit Application (Streamlit Cloud Deployment)
│   ├── streamlit_app/
│   │   ├── main.py            # Main Streamlit application entry point
│   │   ├── pages/
│   │   │   ├── 01_upload.py   # PDF upload and processing page
│   │   │   ├── 02_overview.py # Project overview and navigation
│   │   │   ├── 03_query.py    # Query interface with conversation history
│   │   │   ├── 04_systems.py  # Building systems exploration
│   │   │   ├── 05_documents.py # Document management and viewing
│   │   │   └── 06_settings.py # User preferences and configuration
│   │   ├── components/
│   │   │   ├── auth.py        # Authentication components
│   │   │   ├── upload.py      # File upload components
│   │   │   ├── progress.py    # Progress tracking components
│   │   │   ├── query.py       # Query interface components
│   │   │   ├── overview.py    # Project overview components
│   │   │   └── navigation.py  # Navigation and sidebar components
│   │   ├── utils/
│   │   │   ├── api_client.py  # FastAPI client utilities
│   │   │   ├── auth_utils.py  # Authentication utilities
│   │   │   ├── file_utils.py  # File handling utilities
│   │   │   └── display_utils.py # Display and formatting utilities
│   │   ├── config/
│   │   │   ├── settings.py    # Frontend configuration
│   │   │   └── constants.py   # Application constants
│   │   ├── assets/
│   │   │   ├── css/
│   │   │   │   └── custom.css # Custom styling
│   │   │   ├── images/
│   │   │   └── icons/
│   │   └── requirements.txt   # Frontend Python dependencies
│   ├── deployment/
│   │   ├── streamlit_config.toml # Streamlit configuration
│   │   └── Dockerfile.frontend # Frontend Docker (for local dev only)
│   └── README.md              # Frontend documentation
│
├── shared/                    # Shared code and utilities
│   ├── types/
│   │   ├── __init__.py
│   │   ├── document.py        # Shared document types
│   │   ├── query.py           # Shared query types
│   │   └── pipeline.py        # Shared pipeline types
│   ├── constants/
│   │   ├── __init__.py
│   │   └── app_constants.py   # Shared application constants
│   └── utils/
│       ├── __init__.py
│       └── common_utils.py    # Shared utility functions
│
├── config/                    # Configuration files
│   ├── pipeline/
│   │   ├── chunking_config.json
│   │   ├── embedding_config.json
│   │   ├── retrieval_config.json
│   │   └── generation_config.json
│   ├── deployment/
│   │   ├── railway_config.json
│   │   └── streamlit_config.json
│   └── monitoring/
│       ├── langsmith_config.json
│       └── logging_config.json
│
├── docs/                      # Documentation
│   ├── api/
│   │   ├── endpoints.md       # API endpoint documentation
│   │   └── models.md          # Data model documentation
│   ├── deployment/
│   │   ├── railway_setup.md   # Railway deployment guide
│   │   ├── streamlit_setup.md # Streamlit Cloud setup guide
│   │   └── environment.md     # Environment variables guide
│   └── user-guides/
│       ├── getting_started.md # User getting started guide
│       └── troubleshooting.md # Troubleshooting guide
│
├── scripts/                   # Deployment and utility scripts
│   ├── deploy/
│   │   ├── deploy_backend.sh  # Backend deployment script
│   │   └── deploy_frontend.sh # Frontend deployment script
│   ├── backup/
│   │   └── backup_data.sh     # Data backup script
│   └── monitoring/
│       └── health_check.sh    # Health check script
│
├── tests/                     # End-to-end tests
│   ├── e2e/
│   │   ├── test_upload_flow.py
│   │   ├── test_query_flow.py
│   │   └── test_pipeline_flow.py
│   ├── integration/
│   │   ├── test_api_integration.py
│   │   └── test_db_integration.py
│   └── performance/
│       ├── test_load_performance.py
│       └── test_pdf_processing.py
│
├── .github/                   # CI/CD workflows
│   └── workflows/
│       ├── backend-tests.yml  # Backend testing workflow
│       ├── frontend-tests.yml # Frontend testing workflow
│       └── deploy.yml         # Deployment workflow
│
├── notebooks/                 # Keep existing notebooks for exploration
│   ├── 01_partition/
│   ├── 02_meta_data/
│   ├── 03_enrich_data/
│   ├── 04_chunk/
│   ├── 05_embed/
│   ├── 06_store/
│   ├── 07_query/
│   ├── 08_retrieve/
│   └── 11_generate/
│
├── data/                      # Keep existing data structure
│   ├── external/
│   │   └── construction_pdfs/
│   └── internal/
│
├── backend/.env.example        # Backend environment variables template
├── frontend/.env.example       # Frontend environment variables template
├── .gitignore                 # Git ignore file
├── docker-compose.yml         # Local development (full stack)
├── README.md                  # Main project documentation
├── PRODUCTION_ARCHITECTURE.md # Architecture documentation
└── IMPLEMENTATION_TASK_LIST.md # Implementation tasks
```

## Deployment Strategy

### 1. Backend Deployment (Railway)

**Location**: `backend/` folder
**Dockerfile**: `backend/Dockerfile`
**Entry Point**: `backend/src/main.py`

**Railway Configuration**:
- Railway connects to your Git repository
- Detects `backend/Dockerfile`
- Builds Docker image from `backend/` context
- Deploys FastAPI application
- Runs on Railway infrastructure

**Dockerfile Structure**:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Frontend Deployment (Streamlit Cloud)

**Location**: `frontend/` folder
**Entry Point**: `frontend/streamlit_app/main.py`
**No Dockerfile needed**: Streamlit Cloud deploys directly from Git

**Streamlit Cloud Configuration**:
- Streamlit Cloud connects to your Git repository
- Detects `frontend/streamlit_app/main.py` as entry point
- Installs dependencies from `frontend/requirements.txt`
- Deploys to Streamlit Cloud infrastructure

**Streamlit Configuration**:
```toml
# frontend/deployment/streamlit_config.toml
[server]
port = 8501
enableCORS = true
enableXsrfProtection = false

[browser]
gatherUsageStats = false
```

### 3. Local Development

**Docker Compose**: `docker-compose.yml` (root level)
**Purpose**: Local development with both services

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
    env_file:
      - backend/.env
    volumes:
      - ./backend:/app
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    environment:
      - ENVIRONMENT=development
    env_file:
      - frontend/.env
    depends_on:
      - backend
```

## Environment Variables Management

### Local Development - Backend (.env)
```bash
# Database
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# AI/ML APIs
OPENAI_API_KEY=your_openai_api_key
VOYAGE_API_KEY=your_voyage_api_key
LANGCHAIN_API_KEY=your_langsmith_api_key

# Application
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### Local Development - Frontend (.env)
```bash
# Backend connection
BACKEND_API_URL=http://backend:8000

# Public authentication (frontend only needs public keys)
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Application
ENVIRONMENT=development
```

### Railway Production (Environment Variables)
```bash
# Database
SUPABASE_URL=your_production_supabase_url
SUPABASE_ANON_KEY=your_production_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_production_service_role_key

# AI/ML APIs
OPENAI_API_KEY=your_production_openai_api_key
VOYAGE_API_KEY=your_production_voyage_api_key
LANGCHAIN_API_KEY=your_production_langsmith_api_key

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
PORT=8000
```

### Streamlit Cloud Production (Environment Variables)
```bash
# Backend API
BACKEND_API_URL=https://your-railway-app.railway.app

# Authentication
SUPABASE_URL=your_production_supabase_url
SUPABASE_ANON_KEY=your_production_supabase_anon_key

# Application
ENVIRONMENT=production
```

## Key Benefits of This Structure

### 1. **Clear Separation of Concerns**
- Backend and frontend are completely separate
- Each has its own dependencies and configuration
- Easy to maintain and deploy independently

### 2. **Platform-Specific Optimization**
- Backend optimized for Railway's Docker deployment
- Frontend optimized for Streamlit Cloud's Git deployment
- No unnecessary complexity for either platform

### 3. **Local Development Simplicity**
- Single `docker-compose.yml` for local development
- Separate `.env` files for each service (security best practice)
- Easy to test both services together
- Consistent with production deployment

### 4. **Scalability**
- Each service can scale independently
- Easy to add additional services later
- Clear migration path to microservices if needed

### 5. **Cost Efficiency**
- Railway free tier for backend
- Streamlit Cloud free tier for frontend
- No additional infrastructure costs

## Migration Strategy

### Phase 1: Structure Setup
1. Create new folder structure
2. Move existing notebook code to `backend/src/pipeline/`
3. Create basic FastAPI application
4. Create basic Streamlit application
5. Set up separate `.env` files for backend and frontend

### Phase 2: Backend Migration
1. Migrate pipeline steps to FastAPI modules
2. Add API endpoints
3. Implement background processing
4. Deploy to Railway

### Phase 3: Frontend Migration
1. Create Streamlit application
2. Implement UI components
3. Connect to Railway backend
4. Deploy to Streamlit Cloud

### Phase 4: Integration & Testing
1. Test end-to-end workflows
2. Optimize performance
3. Add monitoring and observability
4. Finalize documentation 