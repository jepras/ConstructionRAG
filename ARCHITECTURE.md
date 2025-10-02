# Specfinder Architecture Documentation

## Overview

Specfinder is an AI-powered construction document processing and Q&A system - a "DeepWiki for Construction Sites" that automatically processes construction documents and enables intelligent Q&A about project requirements, timelines, and specifications.

## High-Level System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        NextJS[Next.js 15.3 Frontend<br/>React + App Router]
        Streamlit[Streamlit Dev UI<br/>Legacy]
    end

    subgraph "Backend Layer"
        API[FastAPI Backend<br/>REST API]
        Auth[Authentication<br/>Supabase Auth]
    end

    subgraph "Processing Layer"
        Beam[Beam Cloud<br/>Indexing Worker]
        WikiGen[Wiki Generation<br/>Background Worker]
    end

    subgraph "Data Layer"
        Supabase[(Supabase PostgreSQL<br/>+ pgvector)]
        Storage[Supabase Storage<br/>PDF Files]
    end

    subgraph "AI Services"
        Voyage[Voyage AI<br/>Embeddings]
        OpenRouter[OpenRouter<br/>LLM Generation]
        Anthropic[Anthropic Claude<br/>Vision + Captions]
    end

    NextJS -->|REST API| API
    Streamlit -->|REST API| API
    API -->|Auth| Auth
    API -->|Trigger| Beam
    API -->|Store/Retrieve| Supabase
    API -->|Upload/Download| Storage

    Beam -->|Webhook| API
    Beam -->|Embeddings| Voyage
    Beam -->|VLM Captions| Anthropic
    Beam -->|Store| Supabase

    WikiGen -->|Query Data| Supabase
    WikiGen -->|Generate Content| OpenRouter
    WikiGen -->|Store Wiki| Supabase

    API -->|Generate Responses| OpenRouter
    API -->|Search Vectors| Supabase

    style NextJS fill:#61dafb
    style API fill:#009688
    style Beam fill:#ff9800
    style Supabase fill:#3ecf8e
    style Voyage fill:#9c27b0
    style OpenRouter fill:#e91e63
    style Anthropic fill:#673ab7
```

## Indexing Pipeline - AI Integration

The indexing pipeline transforms raw PDF documents into searchable, AI-enhanced knowledge:

```mermaid
graph LR
    subgraph "Step 1: Partition"
        PDF[PDF Upload] -->|PyMuPDF/Unstructured| Extract[Text + Tables + Images]
    end

    subgraph "Step 2: Metadata"
        Extract --> Meta[Document Structure<br/>+ Metadata]
    end

    subgraph "Step 3: Enrichment 🤖"
        Meta --> VLM{Has Tables/Images?}
        VLM -->|Yes| Claude[Anthropic Claude Vision<br/>Generate Captions]
        VLM -->|No| Skip[Skip]
        Claude --> Enriched[Enriched Content]
        Skip --> Enriched
    end

    subgraph "Step 4: Chunking"
        Enriched --> Chunk[Semantic Chunks<br/>1000 chars, 200 overlap]
    end

    subgraph "Step 5: Embedding 🤖"
        Chunk --> Voyage[Voyage AI<br/>voyage-multilingual-2<br/>1024 dimensions]
        Voyage --> Vector[Vector Embeddings]
    end

    Vector --> Store[(Supabase<br/>pgvector)]

    style Claude fill:#673ab7,color:#fff
    style Voyage fill:#9c27b0,color:#fff
```

### AI Usage in Indexing:
1. **Anthropic Claude Vision** - Generates natural language captions for tables and images, making visual content searchable
2. **Voyage AI Embeddings** - Creates semantic vector representations of all text chunks for similarity search

## Query Pipeline - AI-Powered Q&A

The query pipeline uses AI at multiple stages to provide accurate, context-aware answers:

```mermaid
graph TB
    Query[User Question] --> Process

    subgraph "Step 1: Query Processing 🤖"
        Process[Query Enhancement]
        Process --> Variations[Generate Semantic<br/>Variations]
        Process --> HyDE[HyDE: Generate<br/>Hypothetical Answer]

        Variations -.->|OpenRouter LLM| LLM1[AI Model]
        HyDE -.->|OpenRouter LLM| LLM1
    end

    subgraph "Step 2: Retrieval"
        Variations --> Embed[Embed Queries]
        HyDE --> Embed
        Embed -.->|Voyage AI| VoyageAPI[voyage-multilingual-2]
        Embed --> Search[Vector Similarity<br/>Search]
        Search --> Rerank[Rerank Results]
    end

    subgraph "Step 3: Generation 🤖"
        Rerank --> Context[Build Context<br/>with Retrieved Chunks]
        Context --> Generate[Generate Answer<br/>with Citations]
        Generate -.->|OpenRouter LLM| LLM2[AI Model]
        Generate --> Answer[Final Answer<br/>+ Source Citations]
    end

    Search -.->|pgvector| DB[(Supabase)]

    style LLM1 fill:#e91e63,color:#fff
    style VoyageAPI fill:#9c27b0,color:#fff
    style LLM2 fill:#e91e63,color:#fff
```

### AI Usage in Querying:
1. **Query Enhancement (OpenRouter)** - Generates semantic variations and hypothetical answers to improve retrieval
2. **Voyage AI Embeddings** - Converts queries to vectors for similarity search
3. **Response Generation (OpenRouter)** - Generates accurate, contextual answers with citations

## Wiki Generation Pipeline - AI-Structured Knowledge

The wiki generation pipeline creates structured, navigable documentation from indexed content:

```mermaid
graph TB
    Start[Indexing Complete<br/>Webhook Trigger] --> Collect

    subgraph "Step 1: Metadata Collection"
        Collect[Gather Document<br/>Metadata + Structure]
    end

    subgraph "Step 2: Overview Generation 🤖"
        Collect --> Overview[Generate Project<br/>Overview]
        Overview -.->|OpenRouter LLM| LLM1[AI Model:<br/>Summarize Project]
    end

    subgraph "Step 3: Semantic Clustering"
        Overview --> Cluster[Cluster Related<br/>Content by Similarity]
        Cluster -.->|Vector Similarity| DB1[(pgvector)]
    end

    subgraph "Step 4: Structure Generation 🤖"
        Cluster --> Structure[Define Wiki<br/>Page Hierarchy]
        Structure -.->|OpenRouter LLM| LLM2[AI Model:<br/>Create Structure]
    end

    subgraph "Step 5: Content Retrieval"
        Structure --> Retrieve[Gather Content<br/>for Each Page]
        Retrieve -.->|Vector Search| DB2[(pgvector)]
    end

    subgraph "Step 6: Markdown Generation 🤖"
        Retrieve --> Generate[Generate Markdown<br/>Pages with Formatting]
        Generate -.->|OpenRouter LLM| LLM3[AI Model:<br/>Write Pages]
    end

    Generate --> Store[(Store Wiki<br/>in Supabase)]

    style LLM1 fill:#e91e63,color:#fff
    style LLM2 fill:#e91e63,color:#fff
    style LLM3 fill:#e91e63,color:#fff
```

### AI Usage in Wiki Generation:
1. **Overview Generation (OpenRouter)** - Summarizes entire project into coherent overview
2. **Structure Generation (OpenRouter)** - Analyzes content clusters to create logical wiki hierarchy
3. **Content Generation (OpenRouter)** - Writes formatted markdown pages with proper sectioning and citations

## Deployment Architecture

```mermaid
graph TB
    subgraph "Production Environment"
        subgraph "Railway Platform"
            FE[Next.js Frontend<br/>specfinder.io]
            BE[FastAPI Backend<br/>api.specfinder.io]
        end

        subgraph "Beam Cloud"
            Worker[Indexing Worker<br/>Serverless Container]
        end

        subgraph "Streamlit Cloud"
            DevUI[Streamlit Dev UI<br/>Legacy Interface]
        end

        subgraph "Supabase Cloud"
            DB[(PostgreSQL + pgvector)]
            Stor[Storage Buckets]
            AuthSvc[Auth Service]
        end
    end

    subgraph "Local Development"
        LocalFE[Next.js Dev Server<br/>localhost:3000]
        LocalBE[FastAPI Dev Server<br/>localhost:8000]
        LocalWorker[Docker Container<br/>localhost:8001]
        LocalDB[(Local Supabase<br/>localhost:54321)]
        Ngrok[Ngrok Tunnel<br/>Webhook Testing]
    end

    FE -->|HTTPS| BE
    DevUI -->|HTTPS| BE
    BE -->|Trigger| Worker
    Worker -->|Webhook| BE
    BE --> DB
    BE --> Stor
    BE --> AuthSvc

    LocalFE -->|HTTP| LocalBE
    LocalBE -->|HTTP| LocalWorker
    LocalWorker -->|Ngrok| Ngrok
    Ngrok -->|HTTP| LocalBE
    LocalBE --> LocalDB

    style FE fill:#61dafb
    style BE fill:#009688
    style Worker fill:#ff9800
    style DB fill:#3ecf8e
```

## Access Control Flow

```mermaid
graph TB
    User[User Request] --> Type{Upload Type?}

    Type -->|email| Public[Public Access<br/>Anonymous OK]
    Type -->|user_project| Auth{Authenticated?}

    Auth -->|No| Reject[401 Unauthorized]
    Auth -->|Yes| Owner{Is Owner?}

    Owner -->|No| RLS[Supabase RLS<br/>Row-Level Security]
    Owner -->|Yes| Allow[Access Granted]

    RLS -->|Fail| Deny[403 Forbidden]
    RLS -->|Pass| Allow

    Public --> Allow
    Allow --> Resource[Access Resource]

    style Public fill:#4caf50,color:#fff
    style Reject fill:#f44336,color:#fff
    style Deny fill:#f44336,color:#fff
    style Allow fill:#4caf50,color:#fff
```

## Key Technology Choices

### AI Services
- **Voyage AI (voyage-multilingual-2)**: Best-in-class multilingual embeddings, optimized for Danish content
- **OpenRouter**: Flexible LLM routing, supports multiple models for different use cases
- **Anthropic Claude Vision**: Superior vision capabilities for table/image understanding

### Infrastructure
- **Railway**: Simple deployment, automatic scaling, great DX
- **Beam Cloud**: Serverless containers for heavy processing, pay-per-use
- **Supabase**: PostgreSQL + pgvector + auth + storage in one platform

### Framework Choices
- **FastAPI**: High performance, automatic API docs, excellent type safety
- **Next.js 15.3**: Server-side rendering, App Router for modern React patterns
- **Pydantic**: Runtime validation, settings management, type safety
