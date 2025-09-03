# ConstructionRAG Architecture Overview

## Table of Contents
1. [System Architecture Overview](#1-system-architecture-overview)
2. [Data Flow Diagrams](#2-data-flow-diagrams)
3. [Component Integration Map](#3-component-integration-map)
4. [Security Architecture](#4-security-architecture)
5. [Deployment Pipeline](#5-deployment-pipeline)
6. [Coding Standards & Practices](#6-coding-standards--practices)
7. [Data Models & Schemas](#7-data-models--schemas)
8. [Performance & Scaling](#8-performance--scaling)
9. [User Journey Sequence Diagrams](#9-user-journey-sequence-diagrams)

---

## 1. System Architecture Overview

### High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Next.js Frontend<br/>Railway]
        LEGACY[Streamlit Frontend<br/>Streamlit Cloud]
    end
    
    subgraph "API Gateway"
        FASTAPI[FastAPI Backend<br/>Railway]
    end
    
    subgraph "Processing Layer"
        BEAM[Beam Service<br/>Indexing Pipeline]
        WIKI[Wiki Generator<br/>Internal Service]
    end
    
    subgraph "Data Layer"
        SUPABASE[(Supabase<br/>PostgreSQL + pgvector)]
        STORAGE[Supabase Storage<br/>PDF Files]
    end
    
    subgraph "External Services"
        VOYAGE[Voyage AI<br/>Embeddings]
        OPENROUTER[OpenRouter<br/>LLM Generation]
        ANTHROPIC[Anthropic<br/>VLM for Tables/Images]
    end
    
    WEB --> FASTAPI
    LEGACY --> FASTAPI
    FASTAPI --> SUPABASE
    FASTAPI --> STORAGE
    FASTAPI --> BEAM
    BEAM --> SUPABASE
    BEAM --> STORAGE
    BEAM --> VOYAGE
    BEAM --> OPENROUTER
    BEAM --> ANTHROPIC
    BEAM -.webhook.-> WIKI
    WIKI --> FASTAPI
    FASTAPI --> VOYAGE
    FASTAPI --> OPENROUTER
    
    style WEB fill:#4A90E2
    style LEGACY fill:#4A90E2
    style FASTAPI fill:#48C774
    style BEAM fill:#FF9F40
    style WIKI fill:#FF9F40
    style SUPABASE fill:#9B59B6
    style STORAGE fill:#9B59B6
    style VOYAGE fill:#F39C12
    style OPENROUTER fill:#F39C12
    style ANTHROPIC fill:#F39C12
```

### Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Frontend** | Next.js | 15.3 | Production React frontend with App Router |
| **Frontend (Legacy)** | Streamlit | Latest | Development/demo interface |
| **Backend API** | FastAPI | Latest | RESTful API server |
| **Language** | Python | 3.11+ | Backend development |
| **Database** | PostgreSQL | 15+ | Primary data storage |
| **Vector DB** | pgvector | 0.5+ | Vector similarity search |
| **Auth** | Supabase Auth | Latest | JWT-based authentication |
| **File Storage** | Supabase Storage | Latest | PDF document storage |
| **Embeddings** | Voyage AI | voyage-multilingual-2 | 1024-dim multilingual embeddings |
| **LLM** | OpenRouter | Various | Text generation (multiple models) |
| **VLM** | Anthropic | Claude 3.5 | Table/image understanding |
| **Processing** | Beam | Latest | Serverless GPU compute |
| **Deployment** | Railway | Latest | Backend & frontend hosting |
| **Deployment** | Streamlit Cloud | Latest | Legacy frontend hosting |

### Deployment Architecture

```mermaid
graph LR
    subgraph "Development"
        DEV_LOCAL[Local Docker<br/>Compose]
    end
    
    subgraph "CI/CD"
        GITHUB[GitHub<br/>Repository]
    end
    
    subgraph "Production - Railway"
        RAIL_BACK[Backend API<br/>Dockerfile]
        RAIL_FRONT[Frontend<br/>Dockerfile]
    end
    
    subgraph "Production - Beam"
        BEAM_PROC[Indexing<br/>beam-app.py]
    end
    
    subgraph "Production - Streamlit"
        STREAM_APP[Legacy UI<br/>streamlit_app/]
    end
    
    DEV_LOCAL --> |push| GITHUB
    GITHUB --> |auto-deploy| RAIL_BACK
    GITHUB --> |auto-deploy| RAIL_FRONT
    GITHUB --> |manual: beam deploy| BEAM_PROC
    GITHUB --> |auto-deploy| STREAM_APP
    
    style DEV_LOCAL fill:#95A5A6
    style GITHUB fill:#2C3E50
    style RAIL_BACK fill:#48C774
    style RAIL_FRONT fill:#4A90E2
    style BEAM_PROC fill:#FF9F40
    style STREAM_APP fill:#4A90E2
```

---

## 2. Data Flow Diagrams

### Indexing Pipeline Flow

```mermaid
graph TD
    START["PDF Upload"] --> VALIDATE["Validate Files<br/>Max 10 files, 50MB each"]
    VALIDATE --> STORE["Store in Supabase<br/>Storage"]
    STORE --> TRIGGER["Trigger Beam<br/>Indexing"]
    
    subgraph "Beam Processing - 5 Steps"
        PARTITION["1 Partition<br/>PyMuPDF extraction"]
        METADATA["2 Metadata<br/>Extract structure"]
        ENRICHMENT["3 Enrichment<br/>VLM captions"]
        CHUNKING["4 Chunking<br/>1000 chars, 200 overlap"]
        EMBEDDING["5 Embedding<br/>Voyage multilingual"]
        
        PARTITION --> METADATA
        METADATA --> ENRICHMENT
        ENRICHMENT --> CHUNKING
        CHUNKING --> EMBEDDING
    end
    
    TRIGGER --> PARTITION
    EMBEDDING --> SAVE["Save to Database<br/>documents + chunks"]
    SAVE --> WEBHOOK["Webhook Callback"]
    WEBHOOK --> WIKI_GEN["Trigger Wiki<br/>Generation"]
    
    style START fill:#E74C3C
    style PARTITION fill:#3498DB
    style METADATA fill:#3498DB
    style ENRICHMENT fill:#3498DB
    style CHUNKING fill:#3498DB
    style EMBEDDING fill:#3498DB
    style WIKI_GEN fill:#2ECC71
```

### Query Processing Pipeline

```mermaid
graph LR
    QUERY[User Query] --> PROCESS[Query Processing]
    
    subgraph "Processing Steps"
        PROCESS --> VARIATIONS[Generate<br/>Variations]
        VARIATIONS --> HYDE[HyDE Query<br/>Generation]
        HYDE --> EMBED[Embed Query<br/>Voyage AI]
    end
    
    subgraph "Retrieval"
        EMBED --> VECTOR[Vector Search<br/>pgvector]
        VECTOR --> RANK[Rank Results<br/>Similarity Score]
        RANK --> FILTER[Apply Filters<br/>Access Control]
    end
    
    subgraph "Generation"
        FILTER --> CONTEXT[Build Context<br/>Top K chunks]
        CONTEXT --> GENERATE[Generate Answer<br/>OpenRouter]
        GENERATE --> FORMAT[Format Response<br/>with Citations]
    end
    
    FORMAT --> RESPONSE[Return to User]
    
    style QUERY fill:#E74C3C
    style EMBED fill:#3498DB
    style VECTOR fill:#9B59B6
    style GENERATE fill:#F39C12
    style RESPONSE fill:#2ECC71
```

### Wiki Generation Pipeline

```mermaid
graph TD
    TRIGGER["Indexing Complete<br/>Webhook"] --> START["Start Wiki Generation"]
    
    subgraph "Wiki Generation Steps"
        META_COLLECT["1 Metadata Collection<br/>Gather doc info"]
        OVERVIEW["2 Overview Generation<br/>Project summary"]
        CLUSTER["3 Semantic Clustering<br/>Group related content"]
        STRUCTURE["4 Structure Generation<br/>Define hierarchy"]
        CONTENT["5 Page Content Retrieval<br/>Gather page data"]
        MARKDOWN["6 Markdown Generation<br/>Create wiki pages"]
        
        META_COLLECT --> OVERVIEW
        OVERVIEW --> CLUSTER
        CLUSTER --> STRUCTURE
        STRUCTURE --> CONTENT
        CONTENT --> MARKDOWN
    end
    
    START --> META_COLLECT
    MARKDOWN --> STORE_WIKI["Store Wiki Pages<br/>Database"]
    STORE_WIKI --> NOTIFY["Update Status<br/>Available"]
    
    style TRIGGER fill:#FF9F40
    style META_COLLECT fill:#3498DB
    style OVERVIEW fill:#3498DB
    style CLUSTER fill:#3498DB
    style STRUCTURE fill:#3498DB
    style CONTENT fill:#3498DB
    style MARKDOWN fill:#3498DB
    style NOTIFY fill:#2ECC71
```

### Authentication & Authorization Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Supabase Auth
    participant Database
    
    User->>Frontend: Login Request
    Frontend->>Supabase Auth: Authenticate
    Supabase Auth-->>Frontend: JWT Token
    Frontend->>API: Request with JWT
    API->>API: Validate JWT
    API->>Database: Query with User Context
    Note over Database: RLS Policies Applied
    Database-->>API: Filtered Results
    API-->>Frontend: Response
    Frontend-->>User: Display Data
```

### File Upload Flow

```mermaid
graph TD
    USER[User] --> DECIDE{Auth Status?}
    
    DECIDE -->|Anonymous| EMAIL[Email Upload]
    DECIDE -->|Authenticated| PROJECT[Project Upload]
    
    EMAIL --> EMAIL_VALID[Validate Email]
    EMAIL_VALID --> PUBLIC_STORE[Store as Public<br/>upload_type: email]
    
    PROJECT --> AUTH_VALID[Validate Auth]
    AUTH_VALID --> PROJECT_STORE[Store as Private<br/>upload_type: user_project]
    
    PUBLIC_STORE --> PROCESS[Process Documents]
    PROJECT_STORE --> PROCESS
    
    PROCESS --> INDEX[Run Indexing<br/>Pipeline]
    
    style USER fill:#E74C3C
    style EMAIL fill:#3498DB
    style PROJECT fill:#2ECC71
    style PROCESS fill:#FF9F40
```

---

## 3. Component Integration Map

### API Endpoint Structure

```mermaid
graph TD
    API["FastAPI Root /"]
    
    API --> AUTH["/api/auth"]
    API --> DOCS["/api/documents"]
    API --> PIPE["/api/pipeline"]
    API --> PROJ["/api/projects"]
    API --> QUERY["/api/queries"]
    API --> WIKI["/api/wiki"]
    API --> HEALTH["/health"]
    
    AUTH --> AUTH_EP["signup<br/>signin<br/>signout<br/>reset-password<br/>me<br/>refresh"]
    
    DOCS --> DOCS_EP["uploads<br/>list<br/>get/{id}"]
    
    PIPE --> PIPE_EP["indexing-runs<br/>progress"]
    
    PROJ --> PROJ_EP["create<br/>list<br/>get/{id}<br/>update<br/>delete<br/>runs"]
    
    QUERY --> QUERY_EP["create<br/>list<br/>get/{id}"]
    
    WIKI --> WIKI_EP["runs<br/>pages<br/>metadata<br/>status<br/>webhook"]
    
    style API fill:#48C774
    style AUTH fill:#4A90E2
    style DOCS fill:#4A90E2
    style PIPE fill:#4A90E2
    style PROJ fill:#4A90E2
    style QUERY fill:#4A90E2
    style WIKI fill:#4A90E2
```

### Service Dependencies

```mermaid
graph LR
    subgraph "API Layer"
        AUTH_ROUTER[Auth Router]
        DOC_ROUTER[Document Router]
        PIPE_ROUTER[Pipeline Router]
        PROJ_ROUTER[Project Router]
        QUERY_ROUTER[Query Router]
        WIKI_ROUTER[Wiki Router]
    end
    
    subgraph "Service Layer"
        AUTH_SVC[AuthService]
        DOC_SVC[DocumentService]
        BEAM_SVC[BeamService]
        PROJ_SVC[ProjectService]
        QUERY_SVC[QueryService]
        WIKI_SVC[WikiService]
    end
    
    subgraph "Data Layer"
        SUPABASE[Supabase Client]
        STORAGE[Storage Client]
    end
    
    AUTH_ROUTER --> AUTH_SVC
    DOC_ROUTER --> DOC_SVC
    PIPE_ROUTER --> BEAM_SVC
    PROJ_ROUTER --> PROJ_SVC
    QUERY_ROUTER --> QUERY_SVC
    WIKI_ROUTER --> WIKI_SVC
    
    AUTH_SVC --> SUPABASE
    DOC_SVC --> SUPABASE
    DOC_SVC --> STORAGE
    BEAM_SVC --> SUPABASE
    PROJ_SVC --> SUPABASE
    QUERY_SVC --> SUPABASE
    WIKI_SVC --> SUPABASE
    
    style AUTH_ROUTER fill:#4A90E2
    style DOC_ROUTER fill:#4A90E2
    style PIPE_ROUTER fill:#4A90E2
    style PROJ_ROUTER fill:#4A90E2
    style QUERY_ROUTER fill:#4A90E2
    style WIKI_ROUTER fill:#4A90E2
    style SUPABASE fill:#9B59B6
    style STORAGE fill:#9B59B6
```

### Database Schema Relationships

```mermaid
erDiagram
    users ||--o{ user_profiles : has
    users ||--o{ projects : owns
    users ||--o{ indexing_runs : creates
    users ||--o{ queries : makes
    
    projects ||--o{ indexing_runs : contains
    projects ||--o{ documents : includes
    
    indexing_runs ||--o{ documents : processes
    indexing_runs ||--o{ queries : enables
    indexing_runs ||--o{ wiki_generation_runs : triggers
    
    documents ||--o{ document_chunks : contains
    documents ||--o{ document_metadata : has
    
    document_chunks ||--o{ query_results : matches
    
    wiki_generation_runs ||--o{ wiki_page_metadata : creates
    
    queries ||--o{ query_results : produces
    
    users {
        uuid id PK
        string email
        timestamp created_at
    }
    
    projects {
        uuid id PK
        uuid user_id FK
        string name
        string description
        timestamp created_at
    }
    
    indexing_runs {
        uuid id PK
        uuid project_id FK
        uuid user_id FK
        string status
        json config
        timestamp created_at
    }
    
    documents {
        uuid id PK
        uuid indexing_run_id FK
        string filename
        string storage_path
        string status
        timestamp created_at
    }
    
    document_chunks {
        uuid id PK
        uuid document_id FK
        text content
        vector embedding
        json metadata
        int chunk_index
    }
    
    wiki_generation_runs {
        uuid id PK
        uuid indexing_run_id FK
        string status
        json config
        timestamp created_at
    }
    
    queries {
        uuid id PK
        uuid user_id FK
        uuid indexing_run_id FK
        text query_text
        json response
        timestamp created_at
    }
```

### External Service Integration

```mermaid
graph TD
    subgraph "ConstructionRAG Core"
        BACKEND[FastAPI Backend]
        BEAM[Beam Service]
    end
    
    subgraph "Voyage AI"
        VOYAGE_API[Embeddings API<br/>voyage-multilingual-2]
    end
    
    subgraph "OpenRouter"
        OR_API[LLM API<br/>Multiple Models]
    end
    
    subgraph "Anthropic"
        CLAUDE_API[Claude API<br/>Vision Models]
    end
    
    BACKEND -->|Generate Embeddings| VOYAGE_API
    BACKEND -->|Generate Responses| OR_API
    
    BEAM -->|Embed Chunks| VOYAGE_API
    BEAM -->|Generate HyDE| OR_API
    BEAM -->|Caption Images/Tables| CLAUDE_API
    
    style BACKEND fill:#48C774
    style BEAM fill:#FF9F40
    style VOYAGE_API fill:#F39C12
    style OR_API fill:#F39C12
    style CLAUDE_API fill:#F39C12
```

---

## 4. Security Architecture

### Authentication Mechanisms

```mermaid
graph TD
    subgraph "Authentication Flow"
        USER[User] --> LOGIN[Login/Signup]
        LOGIN --> SUPABASE_AUTH[Supabase Auth]
        SUPABASE_AUTH --> JWT[JWT Token]
        JWT --> STORE[Store in Cookie/LocalStorage]
    end
    
    subgraph "Request Authorization"
        REQUEST[API Request] --> CHECK_JWT[Check JWT]
        CHECK_JWT --> VALIDATE[Validate with Supabase]
        VALIDATE --> |Valid| CONTEXT[Set User Context]
        VALIDATE --> |Invalid| REJECT[401 Unauthorized]
        CONTEXT --> PROCEED[Process Request]
    end
    
    subgraph "Database Access"
        PROCEED --> DB_QUERY[Database Query]
        DB_QUERY --> RLS[RLS Policies]
        RLS --> FILTERED[Filtered Results]
    end
    
    style USER fill:#E74C3C
    style SUPABASE_AUTH fill:#3498DB
    style JWT fill:#2ECC71
    style REJECT fill:#E74C3C
    style RLS fill:#9B59B6
```

### Row-Level Security (RLS) Implementation

```mermaid
graph LR
    subgraph "RLS Policies"
        PUBLIC[Public Access<br/>upload_type='email']
        AUTH[Authenticated<br/>Any logged user]
        OWNER[Owner Only<br/>user_id match]
        PRIVATE[Private<br/>Specific permissions]
    end
    
    subgraph "Resource Types"
        DOCS[Documents]
        CHUNKS[Chunks]
        QUERIES[Queries]
        PROJECTS[Projects]
        RUNS[Indexing Runs]
        WIKI[Wiki Pages]
    end
    
    PUBLIC --> DOCS
    PUBLIC --> CHUNKS
    PUBLIC --> QUERIES
    
    AUTH --> PROJECTS
    AUTH --> RUNS
    
    OWNER --> PROJECTS
    OWNER --> DOCS
    
    PRIVATE --> WIKI
    
    style PUBLIC fill:#2ECC71
    style AUTH fill:#3498DB
    style OWNER fill:#F39C12
    style PRIVATE fill:#E74C3C
```

### API Security Patterns

```mermaid
graph TD
    subgraph "Middleware Stack"
        REQUEST[Incoming Request]
        REQUEST --> CORS[CORS Middleware<br/>Origin Validation]
        CORS --> REQUEST_ID[Request ID<br/>Tracking]
        REQUEST_ID --> AUTH_MW[Auth Middleware<br/>JWT Validation]
        AUTH_MW --> ERROR_HANDLER[Error Handler<br/>Sanitization]
        ERROR_HANDLER --> ROUTE[Route Handler]
    end
    
    subgraph "Security Checks"
        ROUTE --> INPUT_VAL[Input Validation<br/>Pydantic]
        INPUT_VAL --> RATE_LIMIT[Rate Limiting<br/>Per User/IP]
        RATE_LIMIT --> OWNERSHIP[Ownership Check<br/>Resource Access]
        OWNERSHIP --> PROCESS[Process Request]
    end
    
    style REQUEST fill:#E74C3C
    style CORS fill:#3498DB
    style AUTH_MW fill:#3498DB
    style INPUT_VAL fill:#2ECC71
    style OWNERSHIP fill:#F39C12
```

### Data Access Control Matrix

| Resource | Public (Anonymous) | Authenticated | Owner | Admin |
|----------|-------------------|---------------|-------|-------|
| **Projects** | ❌ | Read own | Full CRUD | Full CRUD |
| **Documents (email)** | Read | Read | N/A | Full CRUD |
| **Documents (project)** | ❌ | Read if member | Full CRUD | Full CRUD |
| **Chunks** | Read if doc public | Read if doc access | Full access | Full CRUD |
| **Queries** | Create/Read own | Create/Read own | Full CRUD | Full CRUD |
| **Indexing Runs** | Read if public | Read own | Full CRUD | Full CRUD |
| **Wiki Pages** | Read if public | Read if access | Full CRUD | Full CRUD |
| **User Profiles** | ❌ | Read/Update own | Full CRUD | Full CRUD |

### Webhook Security

```mermaid
sequenceDiagram
    participant Beam
    participant Webhook Endpoint
    participant API Key Store
    participant Wiki Service
    
    Note over Beam: Indexing Complete
    Beam->>Webhook Endpoint: POST /api/wiki/internal/webhook
    Note over Beam: Headers: X-API-Key
    
    Webhook Endpoint->>API Key Store: Validate API Key
    API Key Store-->>Webhook Endpoint: Valid/Invalid
    
    alt Valid API Key
        Webhook Endpoint->>Wiki Service: Trigger Generation
        Wiki Service-->>Webhook Endpoint: Accepted
        Webhook Endpoint-->>Beam: 200 OK
    else Invalid API Key
        Webhook Endpoint-->>Beam: 401 Unauthorized
    end
```

---

## 5. Deployment Pipeline

### CI/CD Workflow

```mermaid
graph LR
    subgraph "Development"
        DEV[Developer] --> COMMIT[Git Commit]
        COMMIT --> PUSH[Git Push]
    end
    
    subgraph "GitHub"
        PUSH --> MAIN[main branch]
        MAIN --> TRIGGER[Trigger Deploy]
    end
    
    subgraph "Auto Deployment"
        TRIGGER --> RAILWAY[Railway Build]
        TRIGGER --> STREAMLIT[Streamlit Build]
        
        RAILWAY --> BACKEND_DEPLOY[Backend Docker]
        RAILWAY --> FRONTEND_DEPLOY[Frontend Docker]
        
        STREAMLIT --> LEGACY_DEPLOY[Streamlit App]
    end
    
    subgraph "Manual Deployment"
        DEV --> BEAM_CLI[beam deploy]
        BEAM_CLI --> BEAM_DEPLOY[Beam Function]
    end
    
    style DEV fill:#95A5A6
    style MAIN fill:#2C3E50
    style RAILWAY fill:#48C774
    style STREAMLIT fill:#4A90E2
    style BEAM_DEPLOY fill:#FF9F40
```

### Environment Management

```mermaid
graph TD
    subgraph "Environment Variables"
        ENV_LOCAL[.env.local<br/>Local Development]
        ENV_DEV[.env.development<br/>Dev Settings]
        ENV_PROD[Railway/Beam<br/>Production Secrets]
    end
    
    subgraph "Configuration Sources"
        JSON_CONFIG[pipeline_config.json<br/>Pipeline Settings]
        ENV_VARS[Environment Variables<br/>Secrets & URLs]
        CODE_DEFAULTS[Code Defaults<br/>Fallback Values]
    end
    
    subgraph "Configuration Loading"
        JSON_CONFIG --> CONFIG_SERVICE[ConfigService]
        ENV_VARS --> CONFIG_SERVICE
        CODE_DEFAULTS --> CONFIG_SERVICE
        CONFIG_SERVICE --> RUNTIME[Runtime Config]
    end
    
    style ENV_LOCAL fill:#95A5A6
    style ENV_PROD fill:#E74C3C
    style JSON_CONFIG fill:#3498DB
    style CONFIG_SERVICE fill:#2ECC71
```

### Infrastructure as Code

```yaml
# Railway Configuration (railway.toml)
[build]
builder = "DOCKERFILE"
dockerfilePath = "./Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

# Beam Configuration (beam-config.py)
app.run(
    "process_documents",
    cpu=4,
    memory="16Gi",
    gpu="T4",
    python_version="3.11",
    python_packages=[
        "pymupdf",
        "voyage-ai",
        "anthropic",
        "supabase"
    ]
)
```

### Monitoring & Health Checks

```mermaid
graph TD
    subgraph "Health Check Endpoints"
        HEALTH["/health"] --> CHECK_DB["Database Connection"]
        HEALTH --> CHECK_STORAGE["Storage Access"]
        HEALTH --> CHECK_APIS["External APIs"]
        
        CHECK_DB --> STATUS["Return Status"]
        CHECK_STORAGE --> STATUS
        CHECK_APIS --> STATUS
    end
    
    subgraph "Monitoring"
        LOGS["Application Logs"] --> RAILWAY_LOGS["Railway Logs"]
        METRICS["Performance Metrics"] --> RAILWAY_METRICS["Railway Metrics"]
        ERRORS["Error Tracking"] --> ERROR_SERVICE["Error Handler"]
    end
    
    subgraph "Alerts"
        STATUS --> |Unhealthy| ALERT["Alert System"]
        ERROR_SERVICE --> |Critical| ALERT
        ALERT --> NOTIFY["Notifications"]
    end
    
    style HEALTH fill:#2ECC71
    style STATUS fill:#3498DB
    style ALERT fill:#E74C3C
```

---

## 6. Coding Standards & Practices

### Code Organization Principles

```mermaid
graph TD
    subgraph "Design Principles"
        KISS[KISS<br/>Keep It Simple]
        YAGNI[YAGNI<br/>You Aren't Gonna Need It]
        SRP[Single Responsibility<br/>One purpose per unit]
        FAIL_FAST[Fail Fast<br/>Early error detection]
    end
    
    subgraph "Code Limits"
        FILE_LIMIT[Files<br/>Max 500 lines]
        FUNC_LIMIT[Functions<br/>Max 50 lines]
        CLASS_LIMIT[Classes<br/>Max 100 lines]
        MODULE[Modules<br/>Feature-based]
    end
    
    subgraph "Style Guide"
        RUFF[Ruff Format<br/>Code formatting]
        ASYNC[Async/Await<br/>I/O operations]
        TYPES[Type Hints<br/>All functions]
        PYDANTIC[Pydantic<br/>Validation]
    end
    
    KISS --> FILE_LIMIT
    YAGNI --> MODULE
    SRP --> FUNC_LIMIT
    FAIL_FAST --> PYDANTIC
    
    style KISS fill:#2ECC71
    style YAGNI fill:#2ECC71
    style SRP fill:#2ECC71
    style FAIL_FAST fill:#2ECC71
```

### File Size and Modularization Rules

| Component | Maximum Size | Organization |
|-----------|-------------|--------------|
| **Python Files** | 500 lines | Split by feature/responsibility |
| **Functions** | 50 lines | Single clear purpose |
| **Classes** | 100 lines | Single concept/entity |
| **React Components** | 200 lines | Split into sub-components |
| **API Routes** | 30 lines/endpoint | Delegate to services |
| **Test Files** | 300 lines | One test file per module |

### Testing Strategy

```mermaid
graph LR
    subgraph "Test Types"
        UNIT[Unit Tests<br/>Services & Utils]
        INTEGRATION[Integration Tests<br/>Full Pipelines]
        E2E[E2E Tests<br/>User Flows]
    end
    
    subgraph "Test Structure"
        TESTS[tests/]
        TESTS --> TESTS_INT[integration/<br/>Pipeline tests]
        TESTS --> TESTS_UNIT[unit/<br/>Component tests]
    end
    
    subgraph "Test Execution"
        PYTEST[pytest<br/>Test runner]
        COVERAGE[Coverage<br/>Report]
        CI[CI Pipeline<br/>Auto-run]
    end
    
    UNIT --> PYTEST
    INTEGRATION --> PYTEST
    PYTEST --> COVERAGE
    COVERAGE --> CI
    
    style UNIT fill:#3498DB
    style INTEGRATION fill:#2ECC71
    style PYTEST fill:#F39C12
```

### Error Handling Patterns

```python
# Early Return Pattern
async def process_document(doc_id: str) -> Document:
    # Fail fast with validation
    if not doc_id:
        raise ValueError("Document ID required")
    
    # Check permissions early
    if not has_access(doc_id):
        raise PermissionError("Access denied")
    
    # Main logic after validations
    document = await fetch_document(doc_id)
    return document

# Consistent Error Middleware
@app.exception_handler(AppError)
async def app_error_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )
```

### Configuration Management

```mermaid
graph TD
    subgraph "Configuration Sources"
        JSON[pipeline_config.json<br/>Single Source of Truth]
        ENV[.env files<br/>Secrets & URLs]
        DEFAULTS[Code Defaults<br/>Fallbacks]
    end
    
    subgraph "Loading Strategy"
        JSON --> LOADER[ConfigService]
        ENV --> LOADER
        DEFAULTS --> LOADER
        LOADER --> VALIDATE[Validation]
        VALIDATE --> CACHE[Hot Reload Cache]
    end
    
    subgraph "Usage"
        CACHE --> PIPELINE[Pipeline Config]
        CACHE --> API[API Settings]
        CACHE --> SERVICES[Service Config]
    end
    
    style JSON fill:#3498DB
    style ENV fill:#E74C3C
    style CACHE fill:#2ECC71
```

---

## 7. Data Models & Schemas

### Core Pydantic Models Hierarchy

```mermaid
graph TD
    subgraph "User Models"
        USER[UserProfile]
        USER_CREATE[UserProfileCreate]
        USER_UPDATE[UserProfileUpdate]
    end
    
    subgraph "Document Models"
        DOC[Document]
        DOC_CREATE[DocumentCreate]
        DOC_UPDATE[DocumentUpdate]
        DOC_CHUNK[DocumentChunk]
        DOC_WITH_CHUNKS[DocumentWithChunks]
    end
    
    subgraph "Pipeline Models"
        PIPELINE_CONFIG[PipelineConfig]
        PIPELINE_STATUS[PipelineStatus]
        INDEXING_RUN[IndexingRun]
        QUERY_RUN[QueryRun]
        WIKI_RUN[WikiGenerationRun]
    end
    
    subgraph "Query Models"
        QUERY[Query]
        QUERY_CREATE[QueryCreate]
        QUERY_RESPONSE[QueryResponse]
        QUERY_HISTORY[QueryHistory]
    end
    
    USER --> USER_CREATE
    USER --> USER_UPDATE
    
    DOC --> DOC_CREATE
    DOC --> DOC_UPDATE
    DOC --> DOC_CHUNK
    DOC --> DOC_WITH_CHUNKS
    
    PIPELINE_CONFIG --> INDEXING_RUN
    PIPELINE_CONFIG --> QUERY_RUN
    PIPELINE_CONFIG --> WIKI_RUN
    
    QUERY --> QUERY_CREATE
    QUERY --> QUERY_RESPONSE
    
    style USER fill:#4A90E2
    style DOC fill:#2ECC71
    style PIPELINE_CONFIG fill:#F39C12
    style QUERY fill:#9B59B6
```

### Database Table Structures

```sql
-- Core Tables with Key Fields
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE projects (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE indexing_runs (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    user_id UUID REFERENCES users(id),
    status VARCHAR(50), -- pending, processing, completed, failed
    config JSONB,
    upload_type VARCHAR(20), -- email, user_project
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE documents (
    id UUID PRIMARY KEY,
    indexing_run_id UUID REFERENCES indexing_runs(id),
    filename VARCHAR(500),
    storage_path TEXT,
    status VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    content TEXT,
    embedding VECTOR(1024), -- Voyage multilingual-2
    metadata JSONB,
    chunk_index INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for Performance
CREATE INDEX idx_chunks_embedding ON document_chunks 
    USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_documents_run ON documents(indexing_run_id);
```

### Vector Embedding Specifications

```mermaid
graph LR
    subgraph "Embedding Configuration"
        MODEL[voyage-multilingual-2]
        DIM[1024 Dimensions]
        BATCH[Batch Size: 128]
        MAX_TOKENS[Max Tokens: 1000]
    end
    
    subgraph "Storage"
        PGVECTOR[pgvector Extension]
        INDEX[IVFFlat Index]
        SIMILARITY[Cosine Similarity]
    end
    
    subgraph "Usage"
        CHUNKS[Document Chunks]
        QUERIES[User Queries]
        CLUSTERING[Semantic Clustering]
    end
    
    MODEL --> PGVECTOR
    DIM --> PGVECTOR
    PGVECTOR --> INDEX
    INDEX --> SIMILARITY
    
    SIMILARITY --> CHUNKS
    SIMILARITY --> QUERIES
    SIMILARITY --> CLUSTERING
    
    style MODEL fill:#F39C12
    style PGVECTOR fill:#9B59B6
    style SIMILARITY fill:#2ECC71
```

### API Request/Response Schemas

```typescript
// Upload Request
interface UploadRequest {
    files: File[];  // Max 10 files, 50MB each
    email?: string; // For anonymous uploads
    project_id?: string; // For authenticated uploads
}

// Query Request
interface QueryRequest {
    query: string;
    indexing_run_id: string;
    max_results?: number; // Default: 10
    include_metadata?: boolean;
}

// Query Response
interface QueryResponse {
    id: string;
    query: string;
    answer: string;
    sources: Array<{
        document_name: string;
        chunk_index: number;
        relevance_score: number;
        content_preview: string;
    }>;
    processing_time_ms: number;
    created_at: string;
}

// Indexing Progress Response
interface IndexingProgress {
    run_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    current_step: string;
    steps_completed: number;
    total_steps: number;
    documents_processed: number;
    total_documents: number;
    error_message?: string;
}
```

---

## 8. Performance & Scaling

### Concurrency Patterns

```mermaid
graph TD
    subgraph "Document Processing"
        UPLOAD[Document Upload] --> QUEUE[Processing Queue]
        QUEUE --> WORKERS[Worker Pool<br/>Max 5 concurrent]
        WORKERS --> PROCESS1[Doc 1]
        WORKERS --> PROCESS2[Doc 2]
        WORKERS --> PROCESS3[Doc 3]
        WORKERS --> PROCESS4[Doc 4]
        WORKERS --> PROCESS5[Doc 5]
    end
    
    subgraph "Async Operations"
        API[API Request] --> ASYNC[Async Handler]
        ASYNC --> IO1[Database I/O]
        ASYNC --> IO2[Storage I/O]
        ASYNC --> IO3[External API]
        IO1 --> GATHER[Gather Results]
        IO2 --> GATHER
        IO3 --> GATHER
        GATHER --> RESPONSE[Response]
    end
    
    style WORKERS fill:#FF9F40
    style ASYNC fill:#3498DB
    style GATHER fill:#2ECC71
```

### Caching Strategies

```mermaid
graph LR
    subgraph "Cache Layers"
        REQUEST[Request] --> L1[L1: WebFetch Cache<br/>15 minutes]
        L1 --> L2[L2: Query Cache<br/>In-memory]
        L2 --> L3[L3: Embedding Cache<br/>Database]
        L3 --> SOURCE[Source Data]
    end
    
    subgraph "Cache Keys"
        URL_HASH[URL Hash]
        QUERY_HASH[Query + Run Hash]
        CONTENT_HASH[Content Hash]
    end
    
    subgraph "Invalidation"
        TTL[Time-based TTL]
        EVENT[Event-based]
        MANUAL[Manual Clear]
    end
    
    URL_HASH --> L1
    QUERY_HASH --> L2
    CONTENT_HASH --> L3
    
    TTL --> L1
    EVENT --> L2
    MANUAL --> L3
    
    style L1 fill:#3498DB
    style L2 fill:#2ECC71
    style L3 fill:#F39C12
```

### Rate Limiting Implementation

```python
# Rate Limiting Configuration
RATE_LIMITS = {
    "anonymous": {
        "uploads": "10/hour",
        "queries": "50/hour",
        "api_calls": "100/hour"
    },
    "authenticated": {
        "uploads": "100/hour",
        "queries": "500/hour",
        "api_calls": "1000/hour"
    },
    "premium": {
        "uploads": "1000/hour",
        "queries": "5000/hour",
        "api_calls": "10000/hour"
    }
}
```

### Resource Optimization

```mermaid
graph TD
    subgraph "Processing Optimization"
        CHUNK_SIZE[Chunk Size: 1000 chars<br/>Optimal for embeddings]
        OVERLAP[Overlap: 200 chars<br/>Context preservation]
        BATCH[Batch Processing<br/>128 chunks/batch]
    end
    
    subgraph "Timeout Management"
        STEP_TIMEOUT[Step Timeout<br/>30 minutes]
        PIPELINE_TIMEOUT[Pipeline Timeout<br/>2 hours]
        QUERY_TIMEOUT[Query Timeout<br/>30 seconds]
    end
    
    subgraph "Memory Management"
        STREAM[Stream Processing<br/>Large files]
        CLEANUP[Auto Cleanup<br/>Temp files]
        POOL[Connection Pooling<br/>Database]
    end
    
    style CHUNK_SIZE fill:#3498DB
    style STEP_TIMEOUT fill:#F39C12
    style STREAM fill:#2ECC71
```

### Performance Metrics

| Metric | Target | Current | Optimization |
|--------|--------|---------|--------------|
| **Document Processing** | < 30s/MB | ~25s/MB | Parallel extraction |
| **Embedding Generation** | < 100ms/chunk | ~80ms/chunk | Batch processing |
| **Query Response** | < 2s | ~1.5s | Caching + indexing |
| **Wiki Generation** | < 5min | ~4min | Concurrent pages |
| **API Latency (p50)** | < 100ms | ~75ms | Connection pooling |
| **API Latency (p99)** | < 1s | ~800ms | Query optimization |
| **Concurrent Users** | 1000+ | 500 tested | Horizontal scaling |

---

## 9. User Journey Sequence Diagrams

### Anonymous User Document Upload and Query

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Storage
    participant Beam
    participant Database
    
    Note over User: Anonymous User Journey
    
    User->>Frontend: Upload PDFs + Email
    Frontend->>API: POST /api/uploads (email)
    API->>API: Validate files & email
    API->>Storage: Store PDFs
    Storage-->>API: Storage paths
    API->>Database: Create indexing run (public)
    API->>Beam: Trigger indexing
    API-->>Frontend: Run ID & tracking link
    Frontend-->>User: Show progress page
    
    Note over Beam: Async Processing
    Beam->>Storage: Fetch PDFs
    Beam->>Beam: Process 5 steps
    Beam->>Database: Store chunks
    Beam->>API: Webhook complete
    
    User->>Frontend: View project
    Frontend->>API: GET /projects/{runId}
    API->>Database: Fetch public data
    Database-->>API: Project info
    API-->>Frontend: Project data
    Frontend-->>User: Display wiki & query
    
    User->>Frontend: Ask question
    Frontend->>API: POST /api/queries
    API->>Database: Vector search
    API->>API: Generate response
    API-->>Frontend: Answer + sources
    Frontend-->>User: Display result
```

### Authenticated User Project Management

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Auth
    participant Database
    participant Beam
    
    Note over User: Authenticated User Journey
    
    User->>Frontend: Login
    Frontend->>Auth: Authenticate
    Auth-->>Frontend: JWT Token
    Frontend->>Frontend: Store token
    
    User->>Frontend: Create project
    Frontend->>API: POST /api/projects (JWT)
    API->>Auth: Validate JWT
    API->>Database: Create project (owner)
    Database-->>API: Project created
    API-->>Frontend: Project details
    
    User->>Frontend: Upload documents
    Frontend->>API: POST /api/uploads (JWT, project_id)
    API->>Database: Create indexing run (private)
    API->>Beam: Process with user context
    API-->>Frontend: Indexing started
    
    Note over User: Managing project
    User->>Frontend: View dashboard
    Frontend->>API: GET /api/projects (JWT)
    API->>Database: Fetch user projects (RLS)
    Database-->>API: Filtered projects
    API-->>Frontend: Project list
    
    User->>Frontend: Select project version
    Frontend->>API: GET /projects/{projectId}/runs/{runId}
    API->>Database: Fetch with permissions
    Database-->>API: Project + run data
    API-->>Frontend: Combined view
    Frontend-->>User: Display project
```

### Public vs Private Project Access Flow

```mermaid
sequenceDiagram
    participant Anonymous
    participant AuthUser as Authenticated User
    participant Frontend
    participant API
    participant Database
    
    Note over Anonymous: Public Project Access
    Anonymous->>Frontend: /projects/downtown-tower-abc123
    Frontend->>API: GET /api/projects/public/abc123
    API->>Database: Fetch if upload_type='email'
    Database-->>API: Public data only
    API-->>Frontend: Limited features
    Frontend-->>Anonymous: Read-only wiki/query
    
    Note over AuthUser: Private Project Access
    AuthUser->>Frontend: /dashboard/projects/tower/abc123
    Frontend->>API: GET /api/projects/abc123 (JWT)
    API->>API: Validate ownership
    API->>Database: Fetch with RLS
    Database-->>API: Full project data
    API-->>Frontend: All features
    Frontend-->>AuthUser: Full management UI
    
    Note over Anonymous: Attempting Private Access
    Anonymous->>Frontend: /dashboard/projects/tower/abc123
    Frontend->>Frontend: Check auth status
    Frontend-->>Anonymous: Redirect to login
```

### Wiki Generation Webhook Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Beam
    participant WikiService
    participant Database
    
    Note over User: Trigger indexing
    User->>API: POST /api/uploads
    API->>Beam: Start indexing with webhook URL
    API-->>User: Indexing started
    
    Note over Beam: Processing documents
    loop For each document
        Beam->>Beam: Partition
        Beam->>Beam: Extract metadata
        Beam->>Beam: Enrich with VLM
        Beam->>Beam: Chunk text
        Beam->>Beam: Generate embeddings
    end
    
    Beam->>Database: Store chunks
    Beam->>API: POST /api/wiki/internal/webhook
    Note over Beam: Include API key
    
    API->>API: Validate webhook key
    API->>WikiService: Trigger wiki generation
    WikiService-->>API: Accepted
    API-->>Beam: 200 OK
    
    Note over WikiService: Background processing
    WikiService->>Database: Collect metadata
    WikiService->>WikiService: Generate overview
    WikiService->>WikiService: Cluster content
    WikiService->>WikiService: Create structure
    WikiService->>Database: Retrieve content
    WikiService->>WikiService: Generate markdown
    WikiService->>Database: Store wiki pages
    
    User->>API: GET /api/wiki/runs/{runId}/status
    API->>Database: Check status
    Database-->>API: Complete
    API-->>User: Wiki ready
```

### Error Handling and Recovery Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Service
    participant Database
    
    Note over User: Request with error
    User->>Frontend: Perform action
    Frontend->>API: API request
    
    alt Validation Error
        API->>API: Pydantic validation
        API-->>Frontend: 422 Validation Error
        Frontend-->>User: Show field errors
    else Authentication Error
        API->>API: JWT validation fails
        API-->>Frontend: 401 Unauthorized
        Frontend-->>User: Redirect to login
    else Permission Error
        API->>Database: Query with RLS
        Database-->>API: No access
        API-->>Frontend: 403 Forbidden
        Frontend-->>User: Access denied message
    else Processing Error
        API->>Service: Process request
        Service-->>API: Service error
        API->>API: Log error with request ID
        API-->>Frontend: 500 Internal Error
        Frontend-->>User: Retry option
    else Rate Limit
        API->>API: Check rate limit
        API-->>Frontend: 429 Too Many Requests
        Frontend-->>User: Wait message
    end
    
    Note over User: Retry mechanism
    User->>Frontend: Retry action
    Frontend->>Frontend: Exponential backoff
    Frontend->>API: Retry request
    API->>Service: Process
    Service-->>API: Success
    API-->>Frontend: 200 OK
    Frontend-->>User: Success
```

---

## Appendix: Quick Reference

### Key URLs and Endpoints

| Service | Environment | URL |
|---------|------------|-----|
| **Frontend** | Local | http://localhost:3000 |
| **Backend API** | Local | http://localhost:8000 |
| **API Docs** | Local | http://localhost:8000/docs |
| **Streamlit** | Local | http://localhost:8501 |
| **Frontend** | Production | https://constructionrag.railway.app |
| **Backend API** | Production | https://api.constructionrag.railway.app |
| **Streamlit** | Production | https://constructionrag.streamlit.app |

### Common Commands

```bash
# Local Development
docker-compose up --build          # Start full stack
npm run dev                        # Frontend only
uvicorn src.main:app --reload     # Backend only
streamlit run streamlit_app/main.py # Legacy frontend

# Testing
pytest tests/                      # Run all tests
pytest tests/integration/          # Integration only
pytest tests/unit/                 # Unit tests only

# Code Quality
ruff format .                      # Format code
ruff check .                       # Lint code
mypy .                            # Type checking

# Deployment
git push origin main              # Auto-deploy Railway/Streamlit
beam deploy beam-app.py:process_documents  # Deploy Beam
```

### Configuration Files

| File | Purpose |
|------|---------|
| `backend/config/pipeline/pipeline_config.json` | Pipeline configuration |
| `backend/.env` | Local environment variables |
| `frontend/.env.local` | Frontend local config |
| `docker-compose.yml` | Local development setup |
| `backend/Dockerfile` | Production backend container |
| `frontend/Dockerfile` | Production frontend container |
| `railway.toml` | Railway deployment config |

### Critical Performance Parameters

| Parameter | Value | Location |
|-----------|-------|----------|
| **Chunk Size** | 1000 chars | pipeline_config.json |
| **Chunk Overlap** | 200 chars | pipeline_config.json |
| **Embedding Model** | voyage-multilingual-2 | pipeline_config.json |
| **Embedding Dimensions** | 1024 | Database schema |
| **Max Upload Size** | 50MB/file | API validation |
| **Max Files** | 10/upload | API validation |
| **Pipeline Timeout** | 30 min/step | Beam config |
| **Max Concurrent Docs** | 5 | Pipeline config |
| **WebFetch Cache** | 15 minutes | Service config |

---

*This document provides a comprehensive technical overview of the ConstructionRAG system architecture. For implementation details, refer to the source code and inline documentation.*