# Production Architecture: From Notebooks to Production RAG App

## Desired End State

### High-Level Architecture
```
Users → Streamlit Frontend → FastAPI Backend (Modular Monolith) → Databases
                                    ↓
                              Celery Workers → PDF Processing
                                    ↓
                              LangSmith → LLM Observability
```

### Core Components
- **Frontend**: Streamlit (deployed on Streamlit Cloud)
- **Backend**: FastAPI (deployed on Railway)
- **Authentication**: Supabase Auth
- **Database**: Supabase PostgreSQL
- **Vector Database**: ChromaDB
- **File Storage**: AWS S3
- **Background Processing**: Celery + Redis
- **Observability**: LangSmith (LLM) + Supabase (basic metrics) + Honeycomb (detailed tracing - later)

### Key Features
- User authentication and session management
- PDF upload and processing (10-50 PDFs, 1-200 pages each)
- Configurable pipeline parameters (chunking, embedding models, retrieval methods)
- Query interface with conversation history
- Background processing with progress tracking
- Comprehensive observability and monitoring
- Modular, testable architecture

## Design Decisions

### Architecture Pattern
- **Modular Monolith**: Single FastAPI application with clear module separation
- **State Management**: Stateless application with persistent state in Supabase
- **Configuration**: YAML for human-edited configs, JSON for programmatic ones
- **Code Structure**: Pydantic for config validation and data structures, functions for business logic

### Observability Strategy
- **Frontend**: Minimal logging, basic progress indicators
- **Backend**: Comprehensive structured logging with correlation IDs
- **LLM Tracking**: LangSmith for embedding and generation monitoring
- **Application Metrics**: Supabase for basic analytics, Honeycomb for detailed tracing

### User Experience
- **Authentication**: Supabase Auth (Google, GitHub, email/password)
- **Configuration**: User-selectable pipeline parameters
- **Transparency**: Backend observability for debugging, minimal frontend complexity
- **Processing**: Background jobs with progress tracking

## Task List

### Phase 1: Foundation & Core Infrastructure (Week 1-2)

#### 1.1 Project Structure Setup
- [ ] Create new production repository structure
- [ ] Set up Python environment with production dependencies
- [ ] Configure development tools (linting, formatting, testing)
- [ ] Set up CI/CD pipeline

#### 1.2 Database & Authentication Setup
- [ ] Set up Supabase project
- [ ] Design database schema (users, documents, queries, pipeline_runs)
- [ ] Configure Supabase Auth
- [ ] Set up database migrations
- [ ] Create initial data models with Pydantic

#### 1.3 Cloud Infrastructure
- [ ] Set up AWS S3 bucket for file storage
- [ ] Configure IAM roles and permissions
- [ ] Set up ChromaDB deployment
- [ ] Configure environment variables and secrets management

#### 1.4 Basic Backend Framework
- [ ] Create FastAPI application structure
- [ ] Set up dependency injection and configuration management
- [ ] Implement basic health check and status endpoints
- [ ] Set up structured logging with correlation IDs

### Phase 2: Core Pipeline Migration (Week 3-4)

#### 2.1 Pipeline Orchestrator
- [ ] Design pipeline orchestrator with sequential execution pattern
- [ ] Implement step dependency management within single application
- [ ] Add error handling and retry logic
- [ ] Create pipeline configuration management

#### 2.2 Pipeline Steps Migration
- [ ] Create pipeline module structure within FastAPI application
- [ ] Migrate partition step (notebook 01) to pipeline/partition.py
- [ ] Migrate metadata extraction step (notebook 02) to pipeline/metadata.py
- [ ] Migrate data enrichment step (notebook 03) to pipeline/enrichment.py
- [ ] Migrate chunking step (notebook 04) to pipeline/chunking.py
- [ ] Migrate embedding step (notebook 05) to pipeline/embedding.py
- [ ] Migrate storage step (notebook 06) to pipeline/storage.py
- [ ] Migrate query processing step (notebook 07) to pipeline/query_processing.py
- [ ] Migrate retrieval step (notebook 08) to pipeline/retrieval.py
- [ ] Migrate generation step (notebook 11) to pipeline/generation.py

#### 2.3 Background Processing
- [ ] Set up Celery with Redis
- [ ] Implement PDF processing background tasks
- [ ] Add job status tracking and progress updates
- [ ] Create task queue management

#### 2.4 File Processing Module
- [ ] Implement PDF upload and validation within FastAPI
- [ ] Create S3 file management utilities
- [ ] Add file processing status tracking
- [ ] Implement file cleanup and retention policies

### Phase 3: API Development (Week 5-6)

#### 3.1 Core API Endpoints
- [ ] Implement user authentication endpoints
- [ ] Create document upload and management endpoints
- [ ] Build query processing endpoints
- [ ] Add pipeline status and monitoring endpoints

#### 3.2 Data Management APIs
- [ ] Implement document CRUD operations
- [ ] Create query history management
- [ ] Add user preferences and settings endpoints
- [ ] Build analytics and reporting endpoints

#### 3.3 Integration & Testing
- [ ] Set up comprehensive API testing
- [ ] Implement integration tests for pipeline modules
- [ ] Add performance testing for heavy PDF processing
- [ ] Create API documentation with OpenAPI/Swagger

### Phase 4: Frontend Development (Week 7-8)

#### 4.1 Streamlit Application
- [ ] Create main application layout and navigation
- [ ] Implement user authentication UI
- [ ] Build PDF upload interface with progress tracking
- [ ] Create query interface with conversation history

#### 4.2 User Experience Features
- [ ] Add pipeline configuration interface
- [ ] Implement real-time status updates
- [ ] Create results display and export functionality
- [ ] Add user preferences and settings UI

#### 4.3 Integration Testing
- [ ] Test frontend-backend integration
- [ ] Validate user workflows end-to-end
- [ ] Test error handling and edge cases
- [ ] Performance testing with large files

### Phase 5: Observability & Monitoring (Week 9)

#### 5.1 LangSmith Integration
- [ ] Set up LangSmith project and API keys
- [ ] Instrument LLM calls with tracing
- [ ] Configure embedding and generation monitoring
- [ ] Set up cost tracking and performance alerts

#### 5.2 Application Monitoring
- [ ] Implement comprehensive logging strategy
- [ ] Set up error tracking and alerting
- [ ] Create performance monitoring dashboards
- [ ] Add user analytics and usage tracking

#### 5.3 Pipeline Observability
- [ ] Track pipeline execution metrics within single application
- [ ] Monitor processing times and success rates
- [ ] Implement data quality monitoring
- [ ] Create debugging and troubleshooting tools

### Phase 6: Deployment & Production Setup (Week 10)

#### 6.1 Backend Deployment
- [ ] Deploy single FastAPI application to Railway
- [ ] Configure Celery workers and Redis
- [ ] Set up production environment variables
- [ ] Implement health checks and monitoring

#### 6.2 Frontend Deployment
- [ ] Deploy Streamlit application to Streamlit Cloud
- [ ] Configure custom domain and SSL
- [ ] Set up production API endpoints
- [ ] Test production deployment

#### 6.3 Production Configuration
- [ ] Configure production database and backups
- [ ] Set up monitoring and alerting
- [ ] Implement security best practices
- [ ] Create disaster recovery procedures

### Phase 7: Testing & Optimization (Week 11-12)

#### 7.1 Load Testing
- [ ] Test with multiple concurrent users
- [ ] Validate PDF processing performance
- [ ] Test database performance under load
- [ ] Optimize bottlenecks and resource usage

#### 7.2 Security Testing
- [ ] Conduct security audit
- [ ] Test authentication and authorization
- [ ] Validate file upload security
- [ ] Review and fix security vulnerabilities

#### 7.3 User Acceptance Testing
- [ ] Test complete user workflows
- [ ] Validate error handling and edge cases
- [ ] Gather user feedback and iterate
- [ ] Finalize documentation and user guides

## Technical Specifications

### Application Structure (Modular Monolith)
```
src/
├── main.py                 # FastAPI application entry point
├── config/
│   ├── settings.py         # Application configuration
│   └── database.py         # Database connection setup
├── api/
│   ├── auth.py             # Authentication endpoints
│   ├── documents.py        # Document management endpoints
│   ├── queries.py          # Query processing endpoints
│   └── pipeline.py         # Pipeline status endpoints
├── pipeline/
│   ├── __init__.py
│   ├── orchestrator.py     # Pipeline coordination
│   ├── partition.py        # Step 01: PDF partitioning
│   ├── metadata.py         # Step 02: Metadata extraction
│   ├── enrichment.py       # Step 03: Data enrichment
│   ├── chunking.py         # Step 04: Text chunking
│   ├── embedding.py        # Step 05: Text embedding
│   ├── storage.py          # Step 06: Vector storage
│   ├── query_processing.py # Step 07: Query processing
│   ├── retrieval.py        # Step 08: Document retrieval
│   └── generation.py       # Step 11: Response generation
├── services/
│   ├── file_service.py     # S3 file management
│   ├── auth_service.py     # Supabase authentication
│   └── celery_service.py   # Background task management
├── models/
│   ├── document.py         # Document data models
│   ├── query.py            # Query data models
│   └── pipeline.py         # Pipeline data models
├── utils/
│   ├── logging.py          # Structured logging
│   ├── monitoring.py       # Observability utilities
│   └── exceptions.py       # Custom exceptions
└── tests/
    ├── unit/
    ├── integration/
    └── notebooks/          # Keep for exploration
```

### Database Schema (Supabase)
```sql
-- Users (handled by Supabase Auth)
-- Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    filename TEXT NOT NULL,
    s3_key TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pipeline Runs
CREATE TABLE pipeline_runs (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    status TEXT NOT NULL,
    step_results JSONB,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Queries
CREATE TABLE queries (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    query_text TEXT NOT NULL,
    response_text TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### API Endpoints
```
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/user

POST /api/documents/upload
GET  /api/documents
GET  /api/documents/{id}/status
DELETE /api/documents/{id}

POST /api/query
GET  /api/query/history
GET  /api/query/{id}

GET  /api/pipeline/status/{job_id}
GET  /api/pipeline/config
PUT  /api/pipeline/config
```

### Configuration Structure
```yaml
# pipeline_config.yaml
pipeline:
  chunking:
    chunk_size: 1000
    chunk_overlap: 200
    strategy: "semantic"
  
  embedding:
    model: "voyage-large-2"
    dimensions: 1536
    batch_size: 32
  
  retrieval:
    method: "hybrid"
    top_k: 5
    similarity_threshold: 0.7
  
  generation:
    model: "gpt-4"
    temperature: 0.1
    max_tokens: 1000
```

## Success Metrics

### Performance Targets
- PDF processing: <30 minutes for 200-page document
- Query response: <5 seconds for typical queries
- System uptime: >99.5%
- Concurrent users: Support 10+ simultaneous users

### Quality Metrics
- Query relevance: >80% user satisfaction
- Processing success rate: >95%
- Error rate: <2%
- User retention: >70% after first use

### Observability Goals
- Complete pipeline traceability
- Real-time performance monitoring
- Automated error detection and alerting
- Comprehensive user analytics

## Risk Mitigation

### Technical Risks
- **Heavy PDF processing**: Implement proper queuing and timeout handling with Celery
- **Memory usage**: Monitor and optimize chunking strategies within single application
- **API rate limits**: Implement retry logic and rate limiting
- **Data consistency**: Use database transactions and proper error handling

### Operational Risks
- **User adoption**: Start with simple interface, add complexity gradually
- **Performance issues**: Implement comprehensive monitoring and alerting
- **Security vulnerabilities**: Regular security audits and updates
- **Scalability**: Design for horizontal scaling from the start

## Future Enhancements

### Phase 8+: Advanced Features
- React frontend migration
- Advanced analytics and reporting
- Multi-tenant support
- API rate limiting and usage tracking
- Advanced caching strategies
- Machine learning model fine-tuning
- Integration with external construction tools
- Mobile application
- Advanced search and filtering
- Document versioning and collaboration
- **Potential microservice extraction** (if scaling needs arise) 