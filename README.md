# ConstructionRAG - DeepWiki for Construction Sites

An AI-powered construction document processing and Q&A system that automatically processes construction documents and enables intelligent Q&A about every aspect of construction projects. Think of it as a **DeepWiki for Construction Sites** - just like DeepWiki analyzes code repositories, we analyze construction documentation to create comprehensive project knowledge bases.

## 🏗️ What is ConstructionRAG?

ConstructionRAG is a production-ready RAG (Retrieval-Augmented Generation) system specifically designed for construction projects. It:

1. **Processes Construction Documents**: Automatically extracts text, tables, and images from PDFs (plans, specifications, permits)
2. **Generates Intelligent Responses**: Answers complex questions about project requirements, timelines, and specifications
3. **Organizes by Building Systems**: Structures information by electrical, plumbing, HVAC, and structural systems
4. **Supports Danish Language**: Optimized for Danish construction documents with multilingual AI models

### Key Features
- **Complete Document Pipeline**: Partition → Metadata → Enrichment → Chunking → Embedding
- **Advanced Query Processing**: Semantic variations, HyDE queries, and vector similarity search
- **Dual Upload System**: Anonymous email uploads + authenticated user projects
- **Production Deployment**: Live on Railway (backend) and Streamlit Cloud (frontend)
- **Construction-Specific**: Optimized for technical construction content and Danish language

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Docker and Docker Compose
- API keys for:
  - Voyage AI (embeddings - voyage-multilingual-2)
  - OpenRouter (query processing and generation)
  - Anthropic (VLM captioning)
  - Supabase (database and authentication)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ConstructionRAG
   ```

2. **Set up environment variables**
   ```bash
   # Backend
   cp backend/env.example backend/.env
   # Edit backend/.env with your API keys and Supabase credentials
   
   # Frontend
   cp frontend/env.example frontend/.env
   # Edit frontend/.env with your backend URL and Supabase credentials
   ```

3. **Start the application**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Production Deployment

#### Backend (Railway)
1. Connect your GitHub repository to Railway
2. Railway will automatically detect the `backend/Dockerfile`
3. Add environment variables in Railway dashboard
4. Deploy - Live at: https://constructionrag-production.up.railway.app/

#### Frontend (Railway)
1. Connect your GitHub repository to Railway
2. Railway will automatically detect the `frontend/Dockerfile`
3. Add environment variables in Railway dashboard
4. Deploy

## 📁 Project Structure

```
ConstructionRAG/
├── backend/                    # FastAPI Application (Railway)
│   ├── src/
│   │   ├── main.py            # FastAPI application entry point
│   │   ├── config/            # Configuration management
│   │   ├── api/               # API endpoints (auth, documents, queries, pipeline)
│   │   ├── pipeline/          # RAG pipeline steps
│   │   │   ├── indexing/      # Document processing pipeline
│   │   │   │   ├── steps/     # Partition, Metadata, Enrichment, Chunking, Embedding
│   │   │   │   └── config/    # Pipeline configuration
│   │   │   └── querying/      # Query processing pipeline
│   │   │       ├── steps/     # Query Processing, Retrieval, Generation
│   │   │       └── config/    # Query configuration
│   │   ├── services/          # Business logic services
│   │   ├── models/            # Data models
│   │   └── utils/             # Utilities
│   ├── tests/                 # Integration and unit tests
│   ├── Dockerfile             # Backend Docker configuration
│   └── requirements.txt       # Backend dependencies
├── frontend/                  # Next.js Application (Railway)
│   ├── src/
│   │   ├── app/               # Next.js App Router
│   │   │   ├── layout.tsx     # Root layout
│   │   │   ├── page.tsx       # Home page
│   │   │   ├── projects/      # Public projects (anonymous access)
│   │   │   └── (app)/         # Authenticated app routes
│   │   │       └── dashboard/ # Private projects and user management
│   │   ├── components/        # Reusable UI components
│   │   └── lib/               # Utilities and helpers
│   ├── package.json           # Node.js dependencies
│   └── Dockerfile             # Frontend Docker configuration
├── own/                       # Project documentation and learning
│   ├── ARCHITECTURE_OVERVIEW.md
│   ├── PIPELINE_CONFIGURATION.md
│   ├── DATABASE_DESIGN.md
│   └── SYSTEM_INTEGRATION.md
├── config/                    # Configuration files
├── supabase/                  # Database migrations and schema
├── notebooks/                 # Development notebooks and experiments
└── docker-compose.yml         # Local development
```

## 🔧 Configuration

### Pipeline Configuration
The system uses JSON configuration files for pipeline parameters:

- `backend/src/config/pipeline/pipeline_config.json` - Unified pipeline configuration

### Configuration Features
- **Hot Reloading**: Changes take effect immediately for new jobs
- **Environment Variables**: Support for variable substitution
- **Validation**: Automatic validation of configuration parameters
- **Optimization Guides**: Pre-configured settings for different use cases

### Environment Variables

#### Backend (.env)
```bash
# Database
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# AI/ML APIs
VOYAGE_API_KEY=your_voyage_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Application
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

#### Frontend (.env)
```bash
# Backend connection
NEXT_PUBLIC_API_URL=http://localhost:8000

# Authentication
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Application
ENVIRONMENT=development
```

## 🧪 Testing

### Local Testing
```bash
# Backend tests (from project root)
cd backend
pytest tests/

# Integration tests
pytest tests/integration/

# Frontend tests
cd frontend
npm run dev
```

### End-to-End Testing
```bash
# Start the full stack
docker-compose up --build

# Run integration tests
pytest backend/tests/integration/
```

## 📊 Monitoring & Observability

- **Supabase**: Database metrics, logs, and Row Level Security
- **Railway**: Application metrics, logs, and health checks
- **Railway Frontend**: Frontend metrics and logs
- **Structured Logging**: Comprehensive logging with correlation IDs
- **Health Checks**: `/health` endpoint for monitoring

## 🚀 Deployment

### Railway (Backend)
- Automatic deployment from GitHub
- Docker-based deployment
- Environment variable management
- Health checks and monitoring

### Railway (Frontend)
- Automatic deployment from GitHub
- Docker-based deployment
- Environment variable management
- Custom domain support