# ConstructionRAG System Architecture Overview

## Table of Contents
1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Backend Architecture](#backend-architecture)
4. [Pipeline Architecture](#pipeline-architecture)
5. [Data Flow](#data-flow)
6. [Security & Access Control](#security--access-control)
7. [Storage Architecture](#storage-architecture)
8. [Frontend Architecture](#frontend-architecture)
9. [Deployment Architecture](#deployment-architecture)
10. [Integration Points](#integration-points)

## System Overview

ConstructionRAG is an AI-powered construction document processing and Q&A system that combines document indexing, semantic search, and intelligent question answering. The system processes construction documents (PDFs) through multiple AI-powered pipelines to create searchable knowledge bases and generate comprehensive wikis.

### Key Components
- **Document Processing Pipeline**: Multi-stage AI processing for PDF documents
- **Vector Database**: Supabase with pgvector for semantic search
- **Query Pipeline**: Intelligent question answering with context retrieval
- **Wiki Generation**: Automated wiki creation from processed documents
- **Web Interface**: Streamlit-based frontend for user interaction

## High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Streamlit Web Interface]
        Auth[Authentication & Authorization]
    end
    
    subgraph "API Layer"
        FastAPI[FastAPI Backend]
        Middleware[Middleware & Error Handling]
    end
    
    subgraph "Pipeline Layer"
        Indexing[Document Indexing Pipeline]
        Querying[Query Processing Pipeline]
        WikiGen[Wiki Generation Pipeline]
    end
    
    subgraph "AI/ML Layer"
        Embedding[Embedding Models]
        LLM[Large Language Models]
        VLM[Vision Language Models]
    end
    
    subgraph "Data Layer"
        Supabase[(Supabase Database)]
        Storage[Supabase Storage]
        VectorDB[pgvector Vector Store]
    end
    
    subgraph "External Services"
        OpenRouter[OpenRouter API]
        Voyage[Voyage AI]
        Beam[Apache Beam]
    end
    
    UI --> Auth
    Auth --> FastAPI
    FastAPI --> Middleware
    Middleware --> Indexing
    Middleware --> Querying
    Middleware --> WikiGen
    
    Indexing --> Embedding
    Querying --> LLM
    WikiGen --> VLM
    
    Indexing --> VectorDB
    Querying --> VectorDB
    WikiGen --> Storage
    
    Embedding --> Voyage
    LLM --> OpenRouter
    Indexing --> Beam
    
    VectorDB --> Supabase
    Storage --> Supabase
```

## Backend Architecture

### FastAPI Application Structure

```mermaid
graph TB
    subgraph "FastAPI App"
        Main[main.py]
        Settings[Settings Configuration]
        Database[Database Connection]
    end
    
    subgraph "API Routes"
        Auth[Authentication API]
        Documents[Document Management API]
        Pipeline[Pipeline Control API]
        Queries[Query API]
        Wiki[Wiki Generation API]
    end
    
    subgraph "Middleware"
        ErrorHandler[Error Handler]
        RequestID[Request ID Middleware]
        CORS[CORS Middleware]
    end
    
    subgraph "Services"
        AuthService[Authentication Service]
        DocumentService[Document Service]
        PipelineService[Pipeline Service]
        QueryService[Query Service]
        StorageService[Storage Service]
        ConfigService[Configuration Service]
    end
    
    subgraph "Models"
        DomainModels[Domain Models]
        PipelineModels[Pipeline Models]
        QueryModels[Query Models]
        UserModels[User Models]
    end
    
    Main --> Settings
    Main --> Database
    Main --> Auth
    Main --> Documents
    Main --> Pipeline
    Main --> Queries
    Main --> Wiki
    
    Auth --> ErrorHandler
    Documents --> ErrorHandler
    Pipeline --> ErrorHandler
    Queries --> ErrorHandler
    Wiki --> ErrorHandler
    
    ErrorHandler --> RequestID
    RequestID --> CORS
    
    Auth --> AuthService
    Documents --> DocumentService
    Pipeline --> PipelineService
    Queries --> QueryService
    Wiki --> StorageService
    
    AuthService --> DomainModels
    DocumentService --> DomainModels
    PipelineService --> PipelineModels
    QueryService --> QueryModels
    StorageService --> DomainModels
```

## Pipeline Architecture

### Document Indexing Pipeline

```mermaid
graph LR
    subgraph "Input"
        PDF[PDF Document]
        Metadata[Document Metadata]
    end
    
    subgraph "Pipeline Steps"
        Partition[Partition Step<br/>PDF Text Extraction]
        MetadataStep[Metadata Step<br/>Document Analysis]
        Enrichment[Enrichment Step<br/>Content Enhancement]
        Chunking[Chunking Step<br/>Text Segmentation]
        Embedding[Embedding Step<br/>Vector Generation]
    end
    
    subgraph "Output"
        Chunks[Document Chunks]
        Vectors[Vector Embeddings]
        Index[Searchable Index]
    end
    
    PDF --> Partition
    Metadata --> MetadataStep
    
    Partition --> MetadataStep
    MetadataStep --> Enrichment
    Enrichment --> Chunking
    Chunking --> Embedding
    
    Chunking --> Chunks
    Embedding --> Vectors
    Chunks --> Index
    Vectors --> Index
```

### Query Processing Pipeline

```mermaid
graph LR
    subgraph "Input"
        Query[User Question]
        Context[Query Context]
    end
    
    subgraph "Processing Steps"
        QueryProc[Query Processing<br/>Semantic Expansion]
        Retrieval[Document Retrieval<br/>Vector Search]
        Generation[Response Generation<br/>LLM Processing]
    end
    
    subgraph "Output"
        Answer[AI Answer]
        Citations[Source Citations]
        Confidence[Confidence Score]
    end
    
    Query --> QueryProc
    Context --> QueryProc
    
    QueryProc --> Retrieval
    Retrieval --> Generation
    
    Generation --> Answer
    Generation --> Citations
    Generation --> Confidence
```

### Wiki Generation Pipeline

```mermaid
graph LR
    subgraph "Input"
        IndexRun[Indexing Run]
        Documents[Processed Documents]
    end
    
    subgraph "Generation Steps"
        Metadata[Metadata Collection]
        Overview[Overview Generation]
        Clustering[Semantic Clustering]
        Structure[Structure Generation]
        Content[Page Content Retrieval]
        Markdown[Markdown Generation]
    end
    
    subgraph "Output"
        Wiki[Generated Wiki]
        Navigation[Navigation Structure]
        Pages[Wiki Pages]
    end
    
    IndexRun --> Metadata
    Documents --> Metadata
    
    Metadata --> Overview
    Overview --> Clustering
    Clustering --> Structure
    Structure --> Content
    Content --> Markdown
    
    Markdown --> Wiki
    Structure --> Navigation
    Markdown --> Pages
```

## Data Flow

### Document Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant IndexingPipeline
    participant Storage
    participant Database
    participant VectorDB
    
    User->>Frontend: Upload PDF Document
    Frontend->>Backend: POST /api/documents/upload
    Backend->>Storage: Store Original PDF
    Backend->>Database: Create Document Record
    Backend->>IndexingPipeline: Start Indexing Process
    
    loop Pipeline Steps
        IndexingPipeline->>Storage: Store Intermediate Results
        IndexingPipeline->>Database: Update Progress
    end
    
    IndexingPipeline->>VectorDB: Store Vector Embeddings
    IndexingPipeline->>Database: Mark Indexing Complete
    Backend->>Frontend: Return Success Response
    Frontend->>User: Show Completion Status
```

### Query Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant QueryPipeline
    participant VectorDB
    participant LLM
    participant Database
    
    User->>Frontend: Submit Question
    Frontend->>Backend: POST /api/queries/ask
    Backend->>QueryPipeline: Process Query
    
    QueryPipeline->>VectorDB: Semantic Search
    VectorDB->>QueryPipeline: Return Relevant Chunks
    QueryPipeline->>LLM: Generate Response
    LLM->>QueryPipeline: Return Answer
    
    QueryPipeline->>Database: Store Query Run
    Backend->>Frontend: Return Answer + Citations
    Frontend->>User: Display Response
```

## Security & Access Control

### Authentication & Authorization Flow

```mermaid
graph TB
    subgraph "Client"
        Browser[Web Browser]
        API[API Client]
    end
    
    subgraph "Authentication"
        SupabaseAuth[Supabase Auth]
        JWT[JWT Tokens]
        Session[Session Management]
    end
    
    subgraph "Authorization"
        RLS[Row Level Security]
        Policies[Access Control Policies]
        UserContext[User Context]
    end
    
    subgraph "Protected Resources"
        Documents[User Documents]
        Projects[User Projects]
        Pipelines[Pipeline Runs]
    end
    
    Browser --> SupabaseAuth
    API --> SupabaseAuth
    
    SupabaseAuth --> JWT
    JWT --> Session
    
    Session --> RLS
    RLS --> Policies
    Policies --> UserContext
    
    UserContext --> Documents
    UserContext --> Projects
    UserContext --> Pipelines
```

### Access Control Matrix

```mermaid
graph LR
    subgraph "User Types"
        Admin[Admin User]
        Regular[Regular User]
        Guest[Guest User]
    end
    
    subgraph "Resource Access"
        OwnDocs[Own Documents]
        OwnProjects[Own Projects]
        PublicDocs[Public Documents]
        SystemConfig[System Configuration]
    end
    
    Admin --> OwnDocs
    Admin --> OwnProjects
    Admin --> PublicDocs
    Admin --> SystemConfig
    
    Regular --> OwnDocs
    Regular --> OwnProjects
    Regular --> PublicDocs
    
    Guest --> PublicDocs
```

## Storage Architecture

### Supabase Storage Structure

```mermaid
graph TB
    subgraph "Supabase Storage"
        Bucket[Pipeline Assets Bucket]
        
        subgraph "User Projects"
            UserFolder[User ID Folders]
            ProjectFolder[Project ID Folders]
            IndexFolder[Index Run Folders]
        end
        
        subgraph "Pipeline Assets"
            OriginalPDFs[Original PDFs]
            ExtractedImages[Extracted Images]
            GeneratedFiles[Generated Files]
            WikiPages[Wiki Pages]
        end
        
        subgraph "Temporary Files"
            TempProcessing[Processing Temp Files]
            TempUploads[Upload Temp Files]
        end
    end
    
    Bucket --> UserFolder
    UserFolder --> ProjectFolder
    ProjectFolder --> IndexFolder
    
    IndexFolder --> OriginalPDFs
    IndexFolder --> ExtractedImages
    IndexFolder --> GeneratedFiles
    IndexFolder --> WikiPages
    
    IndexFolder --> TempProcessing
    IndexFolder --> TempUploads
```

### Database Schema Overview

```mermaid
erDiagram
    users {
        uuid id PK
        string email
        string role
        timestamp created_at
    }
    
    projects {
        uuid id PK
        uuid user_id FK
        string name
        string description
        timestamp created_at
    }
    
    documents {
        uuid id PK
        uuid project_id FK
        string filename
        string status
        timestamp created_at
    }
    
    document_chunks {
        uuid id PK
        uuid document_id FK
        text content
        vector embedding
        json metadata
    }
    
    indexing_runs {
        uuid id PK
        uuid document_id FK
        string status
        json step_results
        timestamp started_at
        timestamp completed_at
    }
    
    query_runs {
        uuid id PK
        string query_text
        text response
        json search_results
        timestamp created_at
    }
    
    wiki_generation_runs {
        uuid id PK
        uuid index_run_id FK
        string status
        json wiki_structure
        timestamp created_at
    }
    
    users ||--o{ projects : owns
    projects ||--o{ documents : contains
    documents ||--o{ document_chunks : has
    documents ||--o{ indexing_runs : processed_by
    indexing_runs ||--o{ wiki_generation_runs : generates
    documents ||--o{ query_runs : queried_by
```

## Frontend Architecture

### Streamlit Application Structure

```mermaid
graph TB
    subgraph "Streamlit App"
        Main[Main Application]
        Auth[Authentication Module]
    end
    
    subgraph "Pages"
        Overview[Overview Page]
        Upload[Upload Page]
        Progress[Progress Page]
        Query[Query Page]
        Settings[Settings Page]
    end
    
    subgraph "Components"
        AuthComponent[Auth Component]
        FileUpload[File Upload Component]
        ProgressTracker[Progress Tracker]
        QueryInterface[Query Interface]
    end
    
    subgraph "Utilities"
        APIClient[API Client]
        AuthUtils[Authentication Utils]
        SharedUtils[Shared Utilities]
    end
    
    Main --> Auth
    Main --> Overview
    Main --> Upload
    Main --> Progress
    Main --> Query
    Main --> Settings
    
    Auth --> AuthComponent
    Upload --> FileUpload
    Progress --> ProgressTracker
    Query --> QueryInterface
    
    AuthComponent --> AuthUtils
    FileUpload --> APIClient
    ProgressTracker --> APIClient
    QueryInterface --> APIClient
    
    APIClient --> SharedUtils
    AuthUtils --> SharedUtils
```

## Deployment Architecture

### System Deployment

```mermaid
graph TB
    subgraph "Client Layer"
        WebBrowser[Web Browser]
        MobileApp[Mobile App]
    end
    
    subgraph "Frontend Layer"
        StreamlitApp[Streamlit Application]
        CDN[Content Delivery Network]
    end
    
    subgraph "Backend Layer"
        FastAPI[FastAPI Backend]
        LoadBalancer[Load Balancer]
        Workers[Worker Processes]
    end
    
    subgraph "Pipeline Layer"
        BeamWorkers[Apache Beam Workers]
        BackgroundTasks[Background Tasks]
    end
    
    subgraph "Data Layer"
        Supabase[Supabase Platform]
        VectorDB[pgvector Database]
        ObjectStorage[Object Storage]
    end
    
    subgraph "External Services"
        AIAPIs[AI/ML APIs]
        Monitoring[Monitoring & Logging]
    end
    
    WebBrowser --> CDN
    MobileApp --> CDN
    CDN --> StreamlitApp
    
    StreamlitApp --> LoadBalancer
    LoadBalancer --> FastAPI
    FastAPI --> Workers
    
    FastAPI --> BeamWorkers
    FastAPI --> BackgroundTasks
    
    Workers --> Supabase
    BeamWorkers --> Supabase
    BackgroundTasks --> Supabase
    
    Supabase --> VectorDB
    Supabase --> ObjectStorage
    
    Workers --> AIAPIs
    BeamWorkers --> AIAPIs
    BackgroundTasks --> AIAPIs
    
    FastAPI --> Monitoring
    BeamWorkers --> Monitoring
```

## Integration Points

### External API Integrations

```mermaid
graph LR
    subgraph "ConstructionRAG"
        Backend[Backend API]
        Pipelines[Pipeline Services]
    end
    
    subgraph "AI/ML Services"
        OpenRouter[OpenRouter API]
        VoyageAI[Voyage AI API]
        OpenAI[OpenAI API]
    end
    
    subgraph "Infrastructure"
        Supabase[Supabase Platform]
        Beam[Apache Beam]
        Railway[Railway Deployment]
    end
    
    subgraph "Monitoring"
        Logging[Structured Logging]
        Metrics[Performance Metrics]
        Tracing[Request Tracing]
    end
    
    Backend --> OpenRouter
    Backend --> VoyageAI
    Backend --> OpenAI
    
    Pipelines --> VoyageAI
    Pipelines --> OpenAI
    
    Backend --> Supabase
    Pipelines --> Supabase
    
    Pipelines --> Beam
    
    Backend --> Logging
    Backend --> Metrics
    Backend --> Tracing
```

### Configuration Management

```mermaid
graph TB
    subgraph "Configuration Sources"
        Environment[Environment Variables]
        ConfigFiles[Configuration Files]
        Database[Database Config]
    end
    
    subgraph "Configuration Service"
        ConfigService[Configuration Service]
        Validation[Configuration Validation]
        Merging[Config Merging]
    end
    
    subgraph "Pipeline Configs"
        IndexingConfig[Indexing Configuration]
        QueryConfig[Query Configuration]
        WikiConfig[Wiki Configuration]
    end
    
    subgraph "Runtime Config"
        EffectiveConfig[Effective Configuration]
        DynamicConfig[Dynamic Configuration]
    end
    
    Environment --> ConfigService
    ConfigFiles --> ConfigService
    Database --> ConfigService
    
    ConfigService --> Validation
    Validation --> Merging
    
    Merging --> IndexingConfig
    Merging --> QueryConfig
    Merging --> WikiConfig
    
    IndexingConfig --> EffectiveConfig
    QueryConfig --> EffectiveConfig
    WikiConfig --> EffectiveConfig
    
    EffectiveConfig --> DynamicConfig
```

## Key Technical Decisions

### Architecture Patterns
- **Pipeline Pattern**: Modular, configurable processing steps
- **Orchestrator Pattern**: Centralized pipeline coordination
- **Service Layer**: Business logic separation from API layer
- **Repository Pattern**: Data access abstraction
- **Factory Pattern**: Dynamic pipeline step creation

### Technology Choices
- **Backend**: FastAPI for high-performance async API
- **Database**: Supabase with pgvector for vector operations
- **Storage**: Supabase Storage for file management
- **AI/ML**: OpenRouter for LLM access, Voyage AI for embeddings
- **Frontend**: Streamlit for rapid prototyping and deployment
- **Processing**: Apache Beam for scalable data processing
- **Authentication**: Supabase Auth with JWT tokens

### Scalability Considerations
- **Async Processing**: Background tasks for long-running operations
- **Vector Database**: Efficient similarity search with pgvector
- **Configurable Pipelines**: Dynamic pipeline composition
- **Storage Optimization**: Hierarchical storage structure
- **Caching Strategy**: Intelligent result caching

This architecture provides a robust foundation for AI-powered document processing while maintaining flexibility for future enhancements and scaling requirements.
