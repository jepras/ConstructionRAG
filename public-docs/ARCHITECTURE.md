# Specfinder System Architecture

## System Overview

Specfinder implements a distributed document processing architecture that transforms construction PDFs into an intelligent, searchable knowledge base. The system separates compute-intensive processing from user-facing services to ensure scalability and responsiveness.

## High-Level Architecture

```mermaid
graph TB
    subgraph "User Interface Layer"
        UI[React Frontend]
        ST[Streamlit Dev UI]
    end
    
    subgraph "Application Layer - Railway"
        API[FastAPI Backend]
        AUTH[Authentication]
        PROJ[Project Management] 
        WIKI[Wiki Generation]
    end
    
    subgraph "Processing Layer - Beam"
        WORKER[Document Processor]
        PIPE[Indexing Pipeline]
        VLM[Vision Language Model]
    end
    
    subgraph "Data Layer"
        DB[(Supabase PostgreSQL)]
        VDB[(pgvector Extension)]
        STORAGE[(Supabase Storage)]
    end
    
    subgraph "External Services"
        VOYAGE[Voyage AI Embeddings]
        OPENR[OpenRouter VLM]
        UNSTR[Unstructured OCR]
    end
    
    UI --> API
    ST --> API
    API --> AUTH
    API --> PROJ
    API --> WIKI
    
    API --> WORKER
    WORKER --> PIPE
    PIPE --> VLM
    
    API --> DB
    PIPE --> DB
    PIPE --> VDB
    PIPE --> STORAGE
    
    PIPE --> VOYAGE
    VLM --> OPENR
    PIPE --> UNSTR
    
    style API fill:#e3f2fd
    style PIPE fill:#f3e5f5
    style DB fill:#e8f5e8
    style WORKER fill:#fff3e0
```

## Component Architecture

### Railway Backend Services
- **Role**: User-facing API, authentication, project management, and workflow orchestration
- **Key Components**: FastAPI app, Authentication service, Project service, Beam service, Wiki service
- **Deployment**: Railway cloud platform with automatic scaling

### Beam Processing Workers
- **Role**: GPU-accelerated document processing with heavy compute workloads
- **Key Components**: Indexing orchestrator, Document partitioner, VLM enrichment, Vector processing
- **Deployment**: Beam cloud with on-demand CPU instances (GPU removed for cost optimization)

### Data Storage Architecture

```mermaid
erDiagram
    USER ||--o{ PROJECT : owns
    PROJECT ||--o{ INDEXING_RUN : contains
    INDEXING_RUN ||--o{ DOCUMENT : processes
    DOCUMENT ||--o{ CHUNK : generates
    CHUNK ||--|| EMBEDDING : has
    
    USER {
        uuid id PK
        string email
        string name
        timestamp created_at
    }
    
    PROJECT {
        uuid id PK
        uuid user_id FK
        string name
        string slug
        string access_level
    }
    
    INDEXING_RUN {
        uuid id PK
        uuid project_id FK
        string status
        jsonb step_results
        timestamp started_at
    }
    
    DOCUMENT {
        uuid id PK
        string filename
        string file_path
        string upload_type
        jsonb metadata
    }
    
    CHUNK {
        uuid id PK
        uuid document_id FK
        text content
        integer page_number
        string section_title
        jsonb metadata
    }
    
    EMBEDDING {
        uuid chunk_id PK
        vector embedding
        float similarity_threshold
    }
```

## Processing Flow

### Document Ingestion Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant B as Beam Service
    participant W as Worker
    participant D as Database
    
    U->>F: Upload PDF documents
    F->>A: POST /api/uploads
    A->>A: Validate files
    A->>D: Create document records
    A->>B: Trigger indexing pipeline
    B->>W: Launch Beam worker
    W->>W: Execute 5-stage pipeline
    W->>D: Store processed chunks
    W->>A: Webhook completion
    A->>A: Trigger wiki generation
    A->>F: Return processing status
    F->>U: Show progress updates
```

### Multi-Document Processing Timeline

```mermaid
gantt
    title Multi-Document Processing Timeline
    dateFormat HH:mm
    axisFormat %H:%M
    
    section Doc 1
    Partition     :active, doc1-part, 10:00, 10:02
    Metadata      :active, doc1-meta, 10:02, 10:03
    Enrichment    :active, doc1-enrich, 10:03, 10:08
    Chunking      :active, doc1-chunk, 10:08, 10:09
    
    section Doc 2
    Partition     :active, doc2-part, 10:00, 10:01
    Metadata      :active, doc2-meta, 10:01, 10:02
    Enrichment    :active, doc2-enrich, 10:02, 10:05
    Chunking      :active, doc2-chunk, 10:05, 10:06
    
    section Batch
    Embedding     :crit, embed, 10:09, 10:12
    Storage       :crit, store, 10:12, 10:13
```

## Access Control and Security

### Multi-Tenant Architecture

**Access Levels**:
- `public`: Anonymous access to email-uploaded documents
- `auth`: Authenticated user access with RLS policies
- `owner`: Full access to user's projects and documents
- `private`: Restricted access to specific resources

### Data Flow Security

```mermaid
flowchart LR
    subgraph "Public Access"
        PUB[Anonymous Users] --> EMAIL[Email Uploads]
        EMAIL --> PUBDATA[Public Knowledge Base]
    end
    
    subgraph "Authenticated Access"
        AUTH[Authenticated Users] --> PROJ[User Projects]
        PROJ --> PRIVDATA[Private Knowledge Base]
    end
    
    subgraph "Processing Layer"
        PUBDATA --> BEAM[Beam Workers]
        PRIVDATA --> BEAM
        BEAM --> DB[(Database + RLS)]
    end
    
    style BEAM fill:#f0f0f0
    style DB fill:#e8f5e8
```

### Row-Level Security (RLS)
```sql
-- Example RLS policy for chunks table
CREATE POLICY chunks_access_policy ON chunks
FOR SELECT USING (
  -- Public access for email uploads
  (SELECT upload_type FROM documents WHERE id = document_id) = 'email'
  OR
  -- User access for their projects
  (SELECT user_id FROM projects WHERE id = 
    (SELECT project_id FROM indexing_runs WHERE id = 
      (SELECT indexing_run_id FROM chunks WHERE id = chunks.id)
    )
  ) = auth.uid()
);
```

## Deployment Architecture

```mermaid
flowchart TB
    subgraph "Development"
        DEV_FE[Local Frontend:3000]
        DEV_BE[Local Backend:8000]
        DEV_ST[Streamlit:8501]
    end
    
    subgraph "Production"
        PROD_FE[Railway Frontend]
        PROD_BE[Railway Backend]
        BEAM_WORKERS[Beam Workers]
    end
    
    subgraph "Data Services"
        SUPA[Supabase PostgreSQL]
        STORAGE[Supabase Storage]
    end
    
    DEV_FE --> DEV_BE
    DEV_BE --> SUPA
    DEV_ST --> DEV_BE
    
    PROD_FE --> PROD_BE
    PROD_BE --> BEAM_WORKERS
    PROD_BE --> SUPA
    BEAM_WORKERS --> SUPA
    BEAM_WORKERS --> STORAGE
    
    style BEAM_WORKERS fill:#fff3e0
    style SUPA fill:#e8f5e8
```

## Performance and Scalability

### System Capacity
- **Concurrent Users**: 100+ simultaneous users (Railway auto-scaling)
- **Document Processing**: 10 concurrent Beam workers
- **File Size**: 100MB maximum per PDF
- **Batch Size**: 5 documents per indexing run (optimal)

### Optimization Strategies
1. **Intelligent Caching**: VLM captions cached, embeddings reused for duplicate content
2. **Batch Processing**: Unified embedding generation reduces API calls by 80%
3. **Resource Management**: Auto-terminating workers, temp file cleanup, connection pooling

## Integration Patterns

### External Service Integration
- **Voyage AI**: Batch API calls with retry logic and quota management
- **OpenRouter**: Model selection based on complexity with timeout handling
- **Unstructured.io**: Hi-res OCR with coordinate normalization

### Internal Service Communication
- **Synchronous APIs**: User-facing operations (upload, query)
- **Asynchronous Processing**: Document indexing and wiki generation
- **Event-Driven**: Webhook notifications between Railway and Beam

## Monitoring and Observability

```mermaid
flowchart LR
    subgraph "Metrics Collection"
        M1[Processing Times]
        M2[Error Rates]
        M3[Resource Usage]
        M4[API Costs]
    end
    
    subgraph "Alerting"
        A1[High Error Rate]
        A2[Long Processing Times]
        A3[API Quota Limits]
    end
    
    subgraph "Dashboard"
        D1[System Health]
        D2[Pipeline Performance]
        D3[User Analytics]
    end
    
    M1 --> A2
    M2 --> A1
    M4 --> A3
    
    M1 --> D2
    M2 --> D1
    M3 --> D1
    M4 --> D3
```

## Technology Stack
- **Backend**: FastAPI (Python) on Railway
- **Frontend**: Next.js 15.3 with App Router on Railway
- **Database**: Supabase (PostgreSQL with pgvector)
- **Processing**: Beam for compute-intensive tasks
- **AI Services**: Voyage AI (embeddings), OpenRouter (VLM)
- **Language**: Optimized for Danish construction documents

## Related Documentation
- For indexing pipeline details, see: `/public-docs/features/indexing-pipeline.md`
- For API endpoints, see: `/public-docs/api/endpoints.md`
- For deployment guide, see: `/public-docs/implementation/deployment.md`
- For configuration, see: `/public-docs/implementation/configuration.md`