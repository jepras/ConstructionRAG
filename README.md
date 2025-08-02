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
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Production Deployment

#### Backend (Railway)
1. Connect your GitHub repository to Railway
2. Railway will automatically detect the `backend/Dockerfile`
3. Add environment variables in Railway dashboard
4. Deploy - Live at: https://constructionrag-production.up.railway.app/

#### Frontend (Streamlit Cloud)
1. Connect your GitHub repository to Streamlit Cloud
2. Streamlit Cloud will automatically detect `frontend/streamlit_app/main.py`
3. Add environment variables in Streamlit Cloud dashboard
4. Deploy - Live at: https://constructionrag.streamlit.app/

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
├── frontend/                  # Streamlit Application (Streamlit Cloud)
│   ├── streamlit_app/
│   │   ├── main.py            # Main Streamlit application
│   │   ├── components/        # Authentication, upload, query components
│   │   └── utils/             # Frontend utilities
│   └── requirements.txt       # Frontend dependencies
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
The system uses YAML configuration files for pipeline parameters:

- `backend/src/pipeline/indexing/config/indexing_config.yaml` - Document processing pipeline
- `backend/src/pipeline/querying/config/query_config.yaml` - Query processing pipeline

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
BACKEND_API_URL=http://localhost:8000

# Authentication
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

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
streamlit run streamlit_app/main.py
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
- **Streamlit Cloud**: Frontend metrics and logs
- **Structured Logging**: Comprehensive logging with correlation IDs
- **Health Checks**: `/health` endpoint for monitoring

## 🚀 Deployment

### Railway (Backend)
- Automatic deployment from GitHub
- Docker-based deployment
- Environment variable management
- Health checks and monitoring

### Streamlit Cloud (Frontend)
- Automatic deployment from GitHub
- Git-based deployment
- Environment variable management
- Custom domain support

## 📈 Performance

### Targets
- PDF processing: <30 minutes for 200-page document
- Query response: <5 seconds for typical queries
- System uptime: >99.5%
- Concurrent users: Support 10+ simultaneous users

### Cost Optimization
- Free tier usage (Railway, Streamlit Cloud, Supabase)
- Efficient embedding batching (voyage-multilingual-2)
- Background processing for heavy tasks
- Danish language optimization for better accuracy

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation in the `own/` folder
- Review the implementation task list in `IMPLEMENTATION_TASK_LIST.md`

## 📚 Documentation

For detailed system understanding, see the documentation in the `own/` folder:
- **`ARCHITECTURE_OVERVIEW.md`** - High-level system architecture and workflows
- **`PIPELINE_CONFIGURATION.md`** - Detailed pipeline configuration guide
- **`DATABASE_DESIGN.md`** - Database schema and data flow patterns
- **`SYSTEM_INTEGRATION.md`** - Component integration and communication

## 🔮 Roadmap

See `PRODUCTION_ARCHITECTURE.md` for the complete roadmap and future features including:
- Project overview generation
- Construction-specific structuring
- Advanced analytics
- Enterprise features
- Next.js migration
