### ConstructionRAG System Architecture Overview

This document provides a high-level and detailed view of the ConstructionRAG system across frontend, backend, pipelines, data model, access control, and external integrations. Diagrams are Mermaid-based for clarity.

### High-Level System

```mermaid
flowchart LR
  U[User Browser] --> FE[Streamlit Frontend]
  FE -->|HTTP/JSON| BE[FastAPI Backend]
  BE -->|PostgREST/RPC| PG[Supabase Postgres]
  BE -->|Storage SDK| ST[Supabase Storage]
  BE -->|OpenRouter API| LLM[OpenRouter LLMs]
  BE -->|Voyage API| EMB[Voyage AI Embeddings]
  BE -->|Webhook/Task| BW[Beam Worker - Indexing]
```

### Frontend to Backend API Surface

- **Documents**: `POST /api/uploads`, `GET /api/documents`, `GET /api/documents/{id}`
- **Indexing Runs**: `GET /api/indexing-runs`, `GET /api/indexing-runs/{id}`, `GET /api/indexing-runs/{id}/progress`
- **Queries**: `POST /api/queries`, `GET /api/queries`, `GET /api/queries/{id}`
- **Health**: `/health`, `/api/health`

```mermaid
sequenceDiagram
  participant FE as Streamlit FE
  participant API as FastAPI
  participant DB as Supabase
  participant EXT as External APIs
  FE->>API: REST calls
  API->>DB: CRUD on tables / RPC
  API->>EXT: LLM / Embedding calls (as needed)
  API-->>FE: JSON responses
```

### Backend Module Architecture

- API routers: `src/api` (`queries.py`, `documents.py`, `pipeline.py`, `auth.py`)
- Services: `src/services` (`query_service.py`, `pipeline_service.py`, `document_service.py`, `storage_service.py`, ...)
- Pipelines:
  - Indexing: `src/pipeline/indexing/orchestrator.py` + steps (`partition`, `metadata`, `enrichment`, `chunking`, `embedding`)
  - Querying: `src/pipeline/querying/orchestrator.py` + steps (`query_processing`, `retrieval`, `generation`)

```mermaid
flowchart TB
  subgraph API[API Routers]
    QRY[queries.py]
    DOC[documents.py]
    RUN[pipeline.py]
    AUT[auth.py]
  end

  subgraph SVC[Services]
    QS[QueryService]
    QRS[QueryReadService]
    PS[PipelineService]
    DRS[DocumentReadService]
    SS[StorageService]
    CS[ConfigService]
  end

  subgraph IDX[Indexing Pipeline]
    IO[IndexingOrchestrator]
    P[Partition]
    M[Metadata]
    E[Enrichment]
    C[Chunking]
    EM[Embedding]
  end

  subgraph QP[Query Pipeline]
    QO[QueryPipelineOrchestrator]
    QPrc[Query Processing]
    R[Retrieval]
    G[Generation]
  end

  QRY --> QS
  QRY --> QRS
  DOC --> PS
  RUN --> PS
  QS --> QO
  QO --> QPrc --> R --> G
  IO --> P --> M --> E --> C --> EM
  PS -->|DB ops| PG[(Supabase)]
  SS -->|Storage ops| ST[(Storage)]
```

### Query Flow (Detailed)

```mermaid
sequenceDiagram
  autonumber
  participant FE as Streamlit
  participant API as /api/queries
  participant SVC as QueryService
  participant ORCH as QueryPipelineOrchestrator
  participant RET as DocumentRetriever
  participant GEN as ResponseGenerator
  participant DB as Supabase
  participant LLM as OpenRouter
  participant EMB as Voyage

  FE->>API: POST /api/queries {query, indexing_run_id?}
  API->>SVC: create_query(user, text, indexing_run_id)
  SVC->>DB: Resolve access: allowed_document_ids or run ownership
  SVC->>ORCH: process_query(QueryRequest)
  ORCH->>RET: execute(variations, run_id?, allowed_ids?)
  RET->>EMB: Embed query (voyage-multilingual-2)
  RET->>DB: Search document_chunks by similarity
  RET-->>ORCH: SearchResult[]
  ORCH->>GEN: execute(results)
  GEN->>LLM: Generate answer with sources
  GEN-->>ORCH: QueryResponse
  ORCH->>DB: Persist query_runs (+step_timings, metrics)
  ORCH-->>API: envelope {response, search_results, metrics}
  API-->>FE: JSON
```

### Indexing Flow (Email and Project Uploads)

```mermaid
sequenceDiagram
  autonumber
  participant FE as Streamlit
  participant API as /api/uploads
  participant SS as StorageService
  participant DB as Supabase
  participant Beam as Beam Worker
  participant Orch as IndexingOrchestrator
  participant P as Partition
  participant M as Metadata
  participant En as Enrichment
  participant Ch as Chunking
  participant Em as Embedding
  participant EMB as Voyage

  FE->>API: POST /api/uploads (files, email? project_id?)
  API->>DB: Create indexing_runs (public for email, private for project)
  API->>SS: create_storage_structure(...)
  API->>DB: Create documents + link via indexing_run_documents
  API->>Beam: trigger_indexing_pipeline(run_id, document_ids)
  API-->>FE: 202 Accepted {index_run_id}
  Beam->>Orch: process_documents([...], run_id)
  Orch->>P: execute
  P-->>M: StepResult
  M-->>En: StepResult
  En-->>Ch: StepResult
  Ch->>DB: Insert document_chunks (content, metadata)
  Orch->>Em: execute(batch)
  Em->>EMB: get_embeddings(texts)
  Em->>DB: Update document_chunks.embedding_1024
  Orch->>DB: Update indexing_runs status/step_results
```

### Data Model (Core Entities)

```mermaid
erDiagram
  users ||--o{ projects : owns
  projects ||--o{ documents : contains
  indexing_runs ||--o{ indexing_run_documents : links
  documents ||--o{ indexing_run_documents : linked
  documents ||--o{ document_chunks : splits
  indexing_runs ||--o{ document_chunks : groups
  users ||--o{ query_runs : issues

  documents {
    uuid id PK
    uuid user_id
    uuid project_id
    text filename
    jsonb step_results
    text indexing_status
    text access_level
  }
  indexing_runs {
    uuid id PK
    text upload_type
    uuid project_id
    text status
    jsonb step_results
    jsonb pipeline_config
    text access_level
    timestamptz started_at
    timestamptz completed_at
    text error_message
  }
  indexing_run_documents {
    uuid id PK
    uuid indexing_run_id
    uuid document_id
  }
  document_chunks {
    uuid id PK
    uuid document_id
    uuid indexing_run_id
    text content
    jsonb metadata
    vector embedding_1024
    text embedding_model
    text embedding_provider
  }
  query_runs {
    uuid id PK
    uuid user_id
    text original_query
    jsonb query_variations
    jsonb search_results
    text final_response
    jsonb performance_metrics
    jsonb quality_metrics
    int4 response_time_ms
    text access_level
    jsonb step_timings
    jsonb pipeline_config
  }
```

### Access Control and RLS Boundaries

- **Anonymous**: allowed only for email-based `indexing_runs` marked `access_level=public`; queries scoped to that run.
- **Authenticated**: can access own project data (private) + `public` and `auth` content.
- Query path computes `allowed_document_ids` or relies on `indexing_run_id` join filtering; read APIs double-check ownership.

```mermaid
flowchart TB
  ANON[Anonymous user]
  AUTH[Authenticated user]
  RUN[email indexing run - public or auth]
  PROJ[Project owned runs and docs]
  QSvc[QueryService]
  RLS[RLS Policies in Supabase]

  ANON -->|/api/uploads email| RUN
  AUTH -->|/api/uploads project| PROJ
  AUTH -->|/api/queries| QSvc
  ANON -->|/api/queries with run_id| QSvc
  QSvc -->|resolve access| RLS
  RLS -->|filters data sets| QSvc
```

### Storage Layout (Private Buckets with Signed URLs)

```text
pipeline-assets/
  email-uploads/index-runs/{index_run_id}/
    pdfs/
    temp/{partition|metadata|enrichment|chunking|embedding}/
    generated/{markdown|pages|assets/{images,css,js}}
    wiki/{wiki_run_id}/
  users/{user_id}/projects/{project_id}/index-runs/{index_run_id}/
    pdfs/
    temp/{...}
    generated/{...}
    wiki/{wiki_run_id}/
```

Uploads use admin context to bypass storage RLS server-side; clients receive signed URLs. See `src/services/storage_service.py`.

### Configuration and SoT

- Centralized effective config built by `src/services/config_service.py` from `config/pipeline/*.json` and used by orchestrators.
- Query pipeline uses effective `generation` and `retrieval` settings; indexing stores the effective config snapshot on each run.

### Error Handling, Logging, and Observability

- `src/middleware/request_id.py` injects a per-request ID.
- Central exception handlers in `src/middleware/error_handler.py` return consistent error envelopes.
- `src/utils/logging.py` sets structured logging; services use contextual logging.
- Query and indexing orchestrators persist timings and metrics to `query_runs` and `indexing_runs.step_results`.

### Deployment Topology

```mermaid
flowchart LR
  subgraph Docker Compose
    FE[streamlit_app]
    BE[backend FastAPI]
  end
  BE -->|HTTPS| Supa[(Supabase Cloud)]
  BE -->|HTTPS| OpenRouter[(OpenRouter)]
  BE -->|HTTPS| Voyage[(Voyage AI)]
  BE --> Beam[(Beam workers)]
```

### Key Files and Entry Points

- Backend app: `backend/src/main.py`
- API routers: `backend/src/api/*.py`
- Indexing orchestrator: `backend/src/pipeline/indexing/orchestrator.py`
- Query orchestrator: `backend/src/pipeline/querying/orchestrator.py`
- Services (DB/Storage/Config): `backend/src/services/*.py`
- Frontend app: `frontend/streamlit_app/main.py`

### End-to-End Quality Controls

- Embedding model: `voyage-multilingual-2` with 1024 dims; stored in `document_chunks.embedding_1024`.
- Retrieval filters by `indexing_run_id` and/or precomputed `allowed_document_ids`.
- Generation uses OpenRouter with fallbacks; returns citations and confidence.


