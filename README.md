# ConstructionRAG - DeepWiki for Construction Sites

An AI-powered construction document processing and Q&A system that automatically generates comprehensive project overviews from construction documents and enables intelligent Q&A about every aspect of the project.

## 🏗️ What is ConstructionRAG?

Just as DeepWiki analyzes code repositories to create comprehensive wikis, ConstructionRAG:

1. **Generates Project Overviews**: Create executive summaries of entire construction projects from uploaded PDFs
2. **Builds Knowledge Graphs**: Map relationships between different building systems, documents, and stakeholders
3. **Enables Intelligent Q&A**: Answer complex questions about project requirements, timelines, and specifications

### Key Features
- **Construction-Specific Structuring**: Organize by building systems (electrical, plumbing, HVAC, structural)
- **Cross-Document Analysis**: Understand relationships between plans, specifications, permits, and inspections
- **Stakeholder Context**: Track responsibilities across architects, engineers, contractors, and inspectors
- **Project Lifecycle Awareness**: Understand how documents relate to different construction phases

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Docker and Docker Compose
- API keys for:
  - OpenAI (GPT-4)
  - Voyage AI (embeddings)
  - LangSmith (observability)

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
   # Edit backend/.env with your API keys
   
   # Frontend
   cp frontend/env.example frontend/.env
   # Edit frontend/.env with your backend URL
   ```

3. **Start the application**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Production Deployment

#### Backend (Railway)
1. Connect your GitHub repository to Railway
2. Railway will automatically detect the `backend/Dockerfile`
3. Add environment variables in Railway dashboard
4. Deploy

#### Frontend (Streamlit Cloud)
1. Connect your GitHub repository to Streamlit Cloud
2. Streamlit Cloud will automatically detect `frontend/streamlit_app/main.py`
3. Add environment variables in Streamlit Cloud dashboard
4. Deploy

## 📁 Project Structure

```
ConstructionRAG/
├── backend/                    # FastAPI Application (Railway)
│   ├── src/
│   │   ├── main.py            # FastAPI application entry point
│   │   ├── config/            # Configuration management
│   │   ├── api/               # API endpoints
│   │   ├── pipeline/          # RAG pipeline steps
│   │   ├── services/          # Business logic services
│   │   ├── models/            # Data models
│   │   └── utils/             # Utilities
│   ├── Dockerfile             # Backend Docker configuration
│   └── requirements.txt       # Backend dependencies
├── frontend/                  # Streamlit Application (Streamlit Cloud)
│   ├── streamlit_app/
│   │   ├── main.py            # Main Streamlit application
│   │   ├── pages/             # Streamlit pages
│   │   ├── components/        # Reusable components
│   │   └── utils/             # Frontend utilities
│   └── requirements.txt       # Frontend dependencies
├── shared/                    # Shared code and utilities
├── config/                    # Configuration files
├── docs/                      # Documentation
├── tests/                     # End-to-end tests
└── docker-compose.yml         # Local development
```

## 🔧 Configuration

### Pipeline Configuration
The system uses JSON configuration files for different pipeline components:

- `config/pipeline/chunking_config.json` - Text chunking settings
- `config/pipeline/embedding_config.json` - Embedding model settings
- `config/pipeline/retrieval_config.json` - Document retrieval settings
- `config/pipeline/generation_config.json` - Response generation settings

### Environment Variables

#### Backend (.env)
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
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
streamlit run streamlit_app/main.py
```

### End-to-End Testing
```bash
# Start the full stack
docker-compose up --build

# Run E2E tests
pytest tests/e2e/
```

## 📊 Monitoring & Observability

- **LangSmith**: LLM call tracing and monitoring
- **Supabase**: Database metrics and logs
- **Railway**: Application metrics and logs
- **Streamlit Cloud**: Frontend metrics and logs

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
- Project overview generation: <10 minutes for complete project
- System uptime: >99.5%

### Cost Optimization
- Free tier usage (Railway, Streamlit Cloud, Supabase)
- Efficient embedding batching
- Intelligent caching strategies
- Background processing for heavy tasks

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
- Check the documentation in the `docs/` folder
- Review the implementation task list in `IMPLEMENTATION_TASK_LIST.md`

## 🔮 Roadmap

See `PRODUCTION_ARCHITECTURE.md` for the complete roadmap and future features including:
- DeepResearch implementation
- Multi-modal processing
- Advanced analytics
- Enterprise features
- Next.js migration
