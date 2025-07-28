# Production Architecture: DeepWiki for Construction Sites

## Vision: The DeepWiki for Construction Projects

This project aims to create a **DeepWiki for Construction Sites** - an AI-powered knowledge base that automatically generates comprehensive project overviews from construction documents and enables intelligent Q&A about every aspect of the project. Inspired by DeepWiki's success with code repositories, we're applying the same principles to construction documentation.

### What is DeepWiki for Construction?

Just as DeepWiki analyzes code repositories to create comprehensive wikis, our system will:

1. **Generate Project Overviews**: Create executive summaries of entire construction projects from uploaded PDFs
2. **Build Knowledge Graphs**: Map relationships between different building systems, documents, and stakeholders
3. **Enable Intelligent Q&A**: Answer complex questions about project requirements, timelines, and specifications

### Key Differentiators from Generic RAG
- **Construction-Specific Structuring**: Organize by building systems (electrical, plumbing, HVAC, structural) rather than generic document types
- **Cross-Document Analysis**: Understand relationships between plans, specifications, permits, and inspections
- **Stakeholder Context**: Track responsibilities across architects, engineers, contractors, and inspectors
- **Project Lifecycle Awareness**: Understand how documents relate to different construction phases

## Desired End State

### High-Level Architecture
```
Users → Streamlit Frontend → FastAPI Backend (Modular Monolith) → Databases
                                    ↓
                              FastAPI Background Tasks → PDF Processing
                                    ↓
                              LangSmith → LLM Observability
```

### Core Components
- **Frontend**: Streamlit (deployed on Streamlit Cloud)
- **Backend**: FastAPI (deployed on Railway)
- **Authentication**: Supabase Auth
- **Database**: Supabase PostgreSQL with pgvector
- **Vector Database**: Supabase pgvector (free tier)
- **File Storage**: Supabase Storage (free tier)
- **Background Processing**: FastAPI Background Tasks (free)
- **Observability**: LangSmith (LLM) + Supabase (basic metrics) + Honeycomb (detailed tracing - later)

### Key Features
- User authentication and session management
- PDF upload and processing (10-50 PDFs, 1-200 pages each)
- Automatic project overview generation
- Construction-specific document structuring
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

## DeepWiki-Inspired Approach

### Initial Project Overview Generation
Following DeepWiki's pattern of generating comprehensive wikis from repositories, our system will:

1. **Project Executive Summary**: High-level overview of the entire construction project
2. **Document Index**: What each PDF contains and its purpose in the project
3. **Building Systems Map**: How electrical, plumbing, HVAC, and structural systems interact
4. **Timeline & Milestones**: Key dates and phases extracted from documents
5. **Stakeholder Matrix**: Who's responsible for what across the project

### Hierarchical Information Architecture
```
Project Overview
├── Building Systems
│   ├── Electrical
│   ├── Plumbing
│   ├── HVAC
│   └── Structural
├── Project Phases
│   ├── Design
│   ├── Permitting
│   ├── Construction
│   └── Inspection
├── Document Types
│   ├── Plans
│   ├── Specifications
│   ├── Permits
│   └── Inspections
└── Stakeholders
    ├── Architects
    ├── Engineers
    ├── Contractors
    └── Inspectors
```

### Progressive User Experience
1. **Start with Overview**: Users see project summary immediately after upload
2. **Navigate by System**: Drill down into specific building systems
3. **Ask Complex Questions**: Enable multi-turn investigations
4. **Cross-Reference Analysis**: Understand system interactions


## Technical Specifications

### Application Structure (Modular Monolith)

#### Backend Structure (FastAPI)
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
│   ├── file_service.py     # Supabase Storage file management
│   ├── auth_service.py     # Supabase authentication
│   └── background_service.py # Concurrent background task management
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

#### Frontend Structure (Streamlit - Current)
```
frontend/
├── streamlit_app/
│   ├── main.py             # Main Streamlit application entry point
│   ├── pages/
│   │   ├── 01_upload.py    # PDF upload and processing page
│   │   ├── 02_overview.py  # Project overview and navigation
│   │   ├── 03_query.py     # Query interface with conversation history
│   │   ├── 04_systems.py   # Building systems exploration
│   │   ├── 05_documents.py # Document management and viewing
│   │   └── 06_settings.py  # User preferences and configuration
│   ├── components/
│   │   ├── auth.py         # Authentication components
│   │   ├── upload.py       # File upload components
│   │   ├── progress.py     # Progress tracking components
│   │   ├── query.py        # Query interface components
│   │   ├── overview.py     # Project overview components
│   │   └── navigation.py   # Navigation and sidebar components
│   ├── utils/
│   │   ├── api_client.py   # FastAPI client utilities
│   │   ├── auth_utils.py   # Authentication utilities
│   │   ├── file_utils.py   # File handling utilities
│   │   └── display_utils.py # Display and formatting utilities
│   ├── config/
│   │   ├── settings.py     # Frontend configuration
│   │   └── constants.py    # Application constants
│   ├── assets/
│   │   ├── css/
│   │   │   └── custom.css  # Custom styling
│   │   ├── images/
│   │   └── icons/
│   └── requirements.txt    # Frontend dependencies
├── shared/
│   ├── types.py            # Shared type definitions
│   ├── constants.py        # Shared constants
│   └── utils.py            # Shared utilities
└── deployment/
    ├── streamlit_config.toml # Streamlit configuration
    └── Dockerfile.frontend  # Frontend Docker configuration
```

#### Future Frontend Structure (Next.js - Phase 8+)
```
frontend-next/
├── src/
│   ├── app/
│   │   ├── layout.tsx      # Root layout
│   │   ├── page.tsx        # Homepage
│   │   ├── auth/
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── projects/
│   │   │   ├── page.tsx    # Projects list
│   │   │   ├── upload/
│   │   │   │   └── page.tsx # Upload interface
│   │   │   └── [projectId]/
│   │   │       ├── page.tsx # Project overview (MDX)
│   │   │       ├── systems/
│   │   │       │   ├── electrical.mdx
│   │   │       │   ├── plumbing.mdx
│   │   │       │   ├── hvac.mdx
│   │   │       │   └── structural.mdx
│   │   │       ├── documents/
│   │   │       │   └── page.tsx
│   │   │       ├── queries/
│   │   │       │   └── page.tsx
│   │   │       └── deep-research/
│   │   │           └── page.tsx
│   │   └── settings/
│   │       └── page.tsx
│   ├── components/
│   │   ├── ui/             # Reusable UI components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   └── dialog.tsx
│   │   ├── auth/
│   │   │   ├── login-form.tsx
│   │   │   └── auth-provider.tsx
│   │   ├── projects/
│   │   │   ├── project-overview.tsx
│   │   │   ├── system-diagram.tsx
│   │   │   ├── document-viewer.tsx
│   │   │   └── query-interface.tsx
│   │   ├── upload/
│   │   │   ├── file-upload.tsx
│   │   │   └── progress-tracker.tsx
│   │   └── navigation/
│   │       ├── sidebar.tsx
│   │       └── breadcrumbs.tsx
│   ├── lib/
│   │   ├── api.ts          # API client
│   │   ├── auth.ts         # Authentication utilities
│   │   ├── mdx.ts          # MDX processing
│   │   ├── mermaid.ts      # Mermaid diagram generation
│   │   └── construction-utils.ts # Construction-specific utilities
│   ├── hooks/
│   │   ├── use-auth.ts
│   │   ├── use-projects.ts
│   │   └── use-queries.ts
│   ├── types/
│   │   ├── project.ts
│   │   ├── document.ts
│   │   └── query.ts
│   └── styles/
│       └── globals.css
├── public/
│   ├── images/
│   └── icons/
├── mdx/
│   ├── templates/
│   │   ├── project-overview.mdx
│   │   ├── system-overview.mdx
│   │   └── document-index.mdx
│   └── components/
│       ├── mermaid-diagram.tsx
│       ├── system-matrix.tsx
│       └── timeline-chart.tsx
├── next.config.js
├── tailwind.config.js
├── package.json
└── tsconfig.json
```

### Complete Production Folder Structure
```
construction-rag/
├── backend/                # FastAPI application
│   ├── src/               # (Backend structure as above)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/              # Streamlit application (current)
│   ├── streamlit_app/     # (Frontend structure as above)
│   └── deployment/
├── frontend-next/         # Next.js application (future)
│   ├── src/              # (Future frontend structure as above)
│   └── deployment/
├── shared/               # Shared code and utilities
│   ├── types/
│   ├── constants/
│   └── utils/
├── config/               # Configuration files
│   ├── pipeline/
│   ├── deployment/
│   └── monitoring/
├── docs/                 # Documentation
│   ├── api/
│   ├── deployment/
│   └── user-guides/
├── scripts/              # Deployment and utility scripts
│   ├── deploy/
│   ├── backup/
│   └── monitoring/
├── tests/                # End-to-end tests
│   ├── e2e/
│   ├── integration/
│   └── performance/
├── .github/              # CI/CD workflows
│   └── workflows/
├── .env.example
├── README.md
└── docker-compose.yml    # Full stack deployment
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

## Cost-Effective Implementation

### Starting Costs (Free/Minimal)
```
Frontend: Streamlit Cloud (Free)
Backend: Railway (Free tier - $5 credit/month)
Database: Supabase (Free tier)
Storage: Supabase Storage (Free tier - 1GB)
Vector DB: Supabase pgvector (Free)
Background Processing: FastAPI Background Tasks (Free)
Embeddings: API (pay per use - ~$10-15/month for 100 PDFs)
Total: ~$10-15/month
```

### Scaling Costs (When Needed)
```
Railway Pro: $20/month (when free tier limits reached)
Supabase Pro: $25/month (when free tier limits reached)
ChromaDB Cloud: $10/month (if pgvector limits reached)
Total: ~$55/month for 1000+ PDFs/month
```

### Migration Path
1. **Phase 1**: Use free tiers and concurrent background tasks
2. **Phase 2**: Upgrade to paid tiers when free limits reached
3. **Phase 3**: Consider ChromaDB if pgvector performance issues
4. **Phase 4**: Add Celery + Redis only if background task limits are reached

### Concurrent Background Processing
```python
# FastAPI with concurrent background tasks
@app.post("/upload")
async def upload_pdfs(files: List[UploadFile]):
    # Start multiple PDF processing tasks concurrently
    tasks = []
    for file in files:
        task = asyncio.create_task(process_pdf_async(file))
        tasks.append(task)
    
    # Return immediately, let tasks run in background
    return {"status": "processing", "task_count": len(tasks)}

async def process_pdf_async(file: UploadFile):
    # Your 10-step pipeline here
    # Runs concurrently with other PDFs
    pass
```

**Benefits:**
- ✅ Multiple PDFs processed simultaneously
- ✅ No additional infrastructure needed
- ✅ Free (built into FastAPI)
- ✅ Simple to implement
- ✅ Scales with server resources

## Future Enhancements

### Phase 8: DeepWiki-Style Features (Week 13-14)

#### 8.1 DeepResearch Implementation
- [ ] Implement multi-turn research process for complex construction questions
- [ ] Create research plan generation for complex queries
- [ ] Add automatic research continuation (up to 5 iterations)
- [ ] Build structured research conclusion generation
- [ ] Enable cross-document investigation capabilities

#### 8.2 Advanced Caching Strategy
- [ ] Implement aggressive caching for generated project overviews
- [ ] Cache document summaries and system interaction maps
- [ ] Add intelligent cache invalidation for document updates
- [ ] Create cache warming for frequently accessed project data
- [ ] Implement cache analytics and optimization

#### 8.3 Multi-Model Provider Support
- [ ] Add OpenRouter integration for access to multiple LLM providers
- [ ] Implement model selection based on task type (embedding vs generation)
- [ ] Create fallback mechanisms for provider outages
- [ ] Add cost optimization through model selection
- [ ] Enable A/B testing of different models for construction domain

#### 8.4 Construction-Specific Structuring
- [ ] Implement building system classification and mapping
- [ ] Create stakeholder responsibility tracking
- [ ] Add project phase awareness and timeline extraction
- [ ] Build cross-system interaction analysis
- [ ] Enable permit and inspection requirement mapping

### Phase 9: Advanced Construction Features (Week 15-16)

#### 9.1 Multi-Modal Processing
- [ ] Integrate image analysis for plans and drawings
- [ ] Add table and schedule extraction capabilities
- [ ] Implement cross-reference detection and linking
- [ ] Create visual relationship mapping
- [ ] Enable drawing-to-specification correlation

#### 9.2 Advanced Analytics
- [ ] Build construction-specific analytics dashboards
- [ ] Create compliance tracking and reporting
- [ ] Add risk assessment and mitigation analysis
- [ ] Implement cost tracking and budget analysis
- [ ] Enable performance benchmarking across projects

#### 9.3 Integration Capabilities
- [ ] Integrate with construction management software (Procore, PlanGrid)
- [ ] Add BIM model integration capabilities
- [ ] Create API for external construction tools
- [ ] Enable mobile application development
- [ ] Build webhook system for real-time updates

### Phase 10: Enterprise Features (Week 17-18)

#### 10.1 Multi-Tenant Support
- [ ] Implement organization and project-level isolation
- [ ] Add role-based access control for construction teams
- [ ] Create project sharing and collaboration features
- [ ] Enable cross-project knowledge sharing
- [ ] Build enterprise SSO integration

#### 10.2 Advanced Security
- [ ] Implement document-level encryption
- [ ] Add audit logging for compliance requirements
- [ ] Create data retention and deletion policies
- [ ] Enable secure file sharing and collaboration
- [ ] Build GDPR and construction industry compliance features

#### 10.3 Performance Optimization
- [ ] Implement advanced caching strategies
- [ ] Add database query optimization
- [ ] Create CDN integration for global access
- [ ] Enable horizontal scaling capabilities
- [ ] Build performance monitoring and alerting

### Phase 11: Next.js Migration (Week 19-20)

#### 11.1 Next.js Foundation Setup
- [ ] Set up Next.js 14 with App Router
- [ ] Configure MDX and Mermaid.js integration
- [ ] Implement Tailwind CSS and component library
- [ ] Set up TypeScript and shared type definitions
- [ ] Create authentication integration with Supabase

#### 11.2 Core Features Migration
- [ ] Migrate project overview generation to MDX
- [ ] Implement Mermaid diagram generation for building systems
- [ ] Create responsive navigation and layout components
- [ ] Build document viewer with rich formatting
- [ ] Implement real-time query interface

#### 11.3 Advanced Features Implementation
- [ ] Add DeepResearch interface with multi-turn capabilities
- [ ] Implement advanced caching with Redis
- [ ] Create mobile-responsive design
- [ ] Add progressive web app capabilities
- [ ] Implement offline functionality for cached content

#### 11.4 Performance and SEO
- [ ] Implement static generation for project overviews
- [ ] Add SEO optimization for project pages
- [ ] Create sitemap generation
- [ ] Implement structured data for construction projects
- [ ] Add analytics and performance monitoring

### Phase 12+: Scaling and Innovation

#### 12.1 Advanced AI Features
- [ ] Implement construction-specific model fine-tuning
- [ ] Add predictive analytics for project risks
- [ ] Create automated compliance checking
- [ ] Enable AI-powered project recommendations
- [ ] Build construction knowledge graph expansion

#### 12.2 Platform Evolution
- [ ] Advanced search and filtering capabilities
- [ ] Document versioning and collaboration features
- [ ] Mobile application development
- [ ] API marketplace for third-party integrations
- [ ] Real-time collaboration features

#### 12.3 Infrastructure Scaling
- [ ] **Potential microservice extraction** (if scaling needs arise)
- [ ] **Consider ChromaDB Cloud** (if pgvector performance issues)
- [ ] **Implement Kubernetes orchestration** (if enterprise scaling required)
- [ ] **Add global CDN and edge computing** (for international construction firms)
- [ ] **Add Celery + Redis** (only if FastAPI background task limits are reached)

## Success Metrics

### Performance Targets
- PDF processing: <30 minutes for 200-page document
- Query response: <5 seconds for typical queries
- **Project overview generation: <10 minutes for complete project**
- System uptime: >99.5%
- Concurrent users: Support 10+ simultaneous users

### Quality Metrics
- Query relevance: >80% user satisfaction
- Processing success rate: >95%
- **Project overview accuracy: >90% stakeholder validation**
- Error rate: <2%
- User retention: >70% after first use

### Observability Goals
- Complete pipeline traceability
- Real-time performance monitoring
- Automated error detection and alerting
- Comprehensive user analytics
- **Construction-specific usage analytics**

## Risk Mitigation

### Technical Risks
- **Heavy PDF processing**: Implement proper timeout handling with concurrent background tasks
- **Memory usage**: Monitor and optimize chunking strategies within single application
- **API rate limits**: Implement retry logic and rate limiting
- **Data consistency**: Use database transactions and proper error handling
- **Construction domain complexity**: Start with simple use cases, gradually add complexity

### Operational Risks
- **User adoption**: Start with simple interface, add complexity gradually
- **Performance issues**: Implement comprehensive monitoring and alerting
- **Security vulnerabilities**: Regular security audits and updates
- **Scalability**: Design for horizontal scaling from the start
- **Construction industry compliance**: Ensure data handling meets industry standards 