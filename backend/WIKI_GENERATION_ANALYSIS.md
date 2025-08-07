# ConstructionRAG Wiki Generation System Analysis

## Overview

The `markdown_generation_overview.py` file implements a sophisticated 4-step RAG (Retrieval-Augmented Generation) pipeline that generates comprehensive wiki documentation from construction project data. The system leverages vector similarity search, semantic clustering, and LLM generation to create meaningful project overviews.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   STEP 1:       │    │   STEP 2:       │    │   STEP 3:       │    │   STEP 4:       │
│  Supabase       │───▶│  Vector Search  │───▶│  LLM Overview   │───▶│  Semantic       │
│  Metadata       │    │  with Voyage AI │    │  Generation     │    │  Clustering     │
│  Collection     │    │  Embeddings     │    │  (OpenRouter)   │    │  (K-Means)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Key Components

### 1. VoyageEmbeddingClient
- **Purpose**: Handles embedding generation using Voyage AI's multilingual model
- **Model**: `voyage-multilingual-2` (1024 dimensions)
- **Integration**: Matches production pipeline exactly

### 2. MarkdownWikiGenerator
- **Main orchestrator** for the 4-step pipeline
- **Configuration-driven** with tunable parameters
- **Language support**: Optimized for Danish construction documents
- **Error handling**: Robust with fallback mechanisms

## Detailed Step-by-Step Process

### Step 1: Supabase Tables - Metadata Collection

```
Supabase Database
├── indexing_runs
│   └── step_results (JSON)
├── indexing_run_documents  
│   └── document_id linkage
├── documents
│   └── filename, page_count, file_size
└── document_chunks
    └── content, metadata, embedding_1024
```

**Process Flow:**
1. Query `indexing_runs` table for specified run ID
2. Fetch linked documents via `indexing_run_documents`
3. Retrieve all chunks with embeddings for those documents
4. Extract processing statistics from step results
5. Clean and organize metadata for next steps

**Key Data Extracted:**
- Total documents, chunks, pages analyzed
- Section headers distribution
- Images and tables processed counts
- Document filenames and IDs

### Step 2: Vector Database Queries - Project Overview Retrieval

```
Danish Query Set (12 queries)
├── Project Identity
│   ├── "projekt navn titel beskrivelse oversigt"
│   ├── "byggeprojekt omfang målsætninger"
│   └── "projekt lokation byggeplads adresse"
├── Key Stakeholders  
│   ├── "entreprenør klient ejer udvikler"
│   └── "projektteam roller ansvar"
├── Timeline & Phases
│   ├── "projektplan tidsplan milepæle faser"
│   └── "startdato færdiggørelsesdato"
└── Project Scope
    ├── "projektværdi budget omkostningsoverslag"
    ├── "bygningstype bolig erhverv industri"
    └── "kvadratmeter etageareal størrelse"
```

**Vector Search Process:**
1. Generate query embedding using Voyage AI
2. Retrieve chunks with pgvector similarity search
3. Parse embeddings using `ast.literal_eval()` (production-compatible)
4. Calculate cosine similarity scores
5. Apply similarity threshold filtering (0.3)
6. Deduplicate based on content hash (first 200 chars)
7. Sort by similarity score (highest first)

**Quality Improvements Achieved:**
- **Proper deduplication**: Content hash prevents duplicates
- **Production compatibility**: Uses same parsing as query pipeline
- **Better relevance**: Distance-based sorting with similarity threshold
- **Unique results**: 40 unique chunks vs 45 with duplicates before

### Step 3: LLM Overview Generation

```
Input Preparation
├── Top 15 Retrieved Chunks
├── Document ID + Page Number
├── Similarity Scores
└── Source Query Attribution

Danish Prompt Template
├── Projektnavn, type, placering
├── Nøgleinteressenter og tidslinje
└── Projektomfang og leverancer

OpenRouter API Call
├── Model: google/gemini-2.5-flash
├── Temperature: 0.3
├── Max Tokens: 2000
└── Danish Language Output
```

**LLM Integration:**
- **Model**: Google Gemini 2.5 Flash via OpenRouter
- **Language**: Danish-optimized prompts
- **Context**: 15 most relevant chunks (up to 800 chars each)
- **Structure**: 3-section project overview with source citations
- **Fallback**: Dummy content for testing if API fails

**Quality Results:**
- **Content length**: ~2500 characters (vs 1597 before)
- **Rich information**: Project names, stakeholders, technical specs
- **Source citations**: Proper referencing with document:page format

### Step 4: Semantic Clustering - Topic Identification

```
Embedding Processing
├── Parse 1024-dim embeddings
├── Filter chunks with valid embeddings  
└── Convert to numpy arrays

K-Means Clustering
├── Determine cluster count (4-10 clusters)
├── Formula: min(10, max(4, n_chunks//20))
├── Random state: 42 for reproducibility
└── n_init: 10 for stability

Theme Detection (Danish Construction)
├── 24 specialized theme categories
├── Keyword scoring system
├── Unique name generation
└── Fallback naming scheme
```

**Semantic Analysis Features:**
- **Dynamic clustering**: 4-10 clusters based on content volume
- **Danish construction focus**: 24 specialized theme categories
- **Intelligent naming**: Theme-based cluster names with uniqueness
- **Representative content**: Sample content from each cluster

**Theme Categories Include:**
- Elektriske Installationer
- Tekniske Specifikationer  
- Rum og Faciliteter
- VVS-installationer
- Brandsikkerhed
- Bygningskonstruktion
- And 18 more specialized areas

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONSTRUCTIONRAG WIKI GENERATOR               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐   │
│  │  Supabase   │────▶│   Voyage AI  │────▶│    OpenRouter   │   │
│  │  Database   │     │  Embeddings  │     │   LLM Service   │   │  
│  │             │     │              │     │                 │   │
│  │ ┌─────────┐ │     │ ┌──────────┐ │     │ ┌─────────────┐ │   │
│  │ │ Docs    │ │     │ │ Vector   │ │     │ │ Overview    │ │   │
│  │ │ Chunks  │ │     │ │ Search   │ │     │ │ Generation  │ │   │
│  │ │ Metadata│ │     │ │ Engine   │ │     │ │             │ │   │
│  │ └─────────┘ │     │ └──────────┘ │     │ └─────────────┘ │   │
│  └─────────────┘     └──────────────┘     └─────────────────┘   │
│         │                     │                       │         │
│         ▼                     ▼                       ▼         │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐   │
│  │  STEP 1:    │     │   STEP 2:    │     │    STEP 3:      │   │
│  │  Metadata   │────▶│   Vector     │────▶│    LLM          │   │
│  │  Collection │     │   Queries    │     │    Overview     │   │
│  │             │     │   (12 types) │     │    Generation   │   │
│  └─────────────┘     └──────────────┘     └─────────────────┘   │
│         │                                           │           │
│         │             ┌──────────────┐              │           │
│         └────────────▶│   STEP 4:    │◀─────────────┘           │
│                       │   Semantic   │                          │
│                       │   Clustering │                          │
│                       │   (K-Means)  │                          │
│                       └──────────────┘                          │
│                              │                                  │
│                              ▼                                  │
│                    ┌─────────────────┐                         │
│                    │  Output JSON    │                         │
│                    │  (Cleaned)      │                         │
│                    │  156 lines      │                         │
│                    └─────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration Management

```python
config = {
    "similarity_threshold": 0.3,      # Vector search threshold
    "max_chunks_per_query": 10,       # Retrieval limit
    "overview_query_count": 12,       # Number of overview queries
    "semantic_clusters": {
        "min_clusters": 4,            # Minimum cluster count
        "max_clusters": 10            # Maximum cluster count
    }
}
```

## Output Data Structure

The system generates a clean JSON structure with aggressive data cleaning:

```json
{
  "index_run_id": "uuid",
  "metadata": {
    "total_documents": 3,
    "total_chunks": 245,
    "total_pages_analyzed": 42,
    "documents": "summary with filenames only",
    "chunks": "count + sample IDs only"
  },
  "overview_queries": {
    "retrieved_chunks": "count + similarity scores only",
    "query_results": "condensed query performance metrics"
  },
  "project_overview": "2500+ character Danish project description",
  "semantic_analysis": {
    "cluster_summaries": [
      {
        "cluster_name": "Elektriske Installationer", 
        "chunk_count": 45,
        "sample_preview": "truncated content..."
      }
    ],
    "n_clusters": 8
  }
}
```

## Performance Metrics

**Processing Time**: ~23.6 seconds for full pipeline
**Memory Efficiency**: Aggressive data cleaning reduces output from thousands to 156 lines
**Quality Improvements**:
- Vector search: 0.588 top similarity (vs lower scores before)
- Deduplication: 40 unique chunks (vs 45 with duplicates)
- LLM output: 2500 characters (vs 1597 "limited info" before)
- Semantic clustering: 10 distinct Danish construction themes

## Error Handling & Resilience

1. **API Failures**: Fallback dummy content for testing
2. **Missing Embeddings**: Graceful filtering and warnings
3. **Invalid Data**: Robust parsing with ast.literal_eval()
4. **Timeout Protection**: 30-second API timeouts
5. **Data Validation**: Type checking and format verification

## Integration Points

**Production Compatibility:**
- Uses same embedding model as query pipeline (voyage-multilingual-2)
- Identical parsing approach with ast.literal_eval()
- Same similarity calculation and deduplication logic
- Compatible with Supabase schema and data types

**External Services:**
- **Supabase**: PostgreSQL with pgvector extension  
- **Voyage AI**: Multilingual embeddings (1024-dim)
- **OpenRouter**: LLM generation (Gemini 2.5 Flash)
- **Scikit-learn**: K-means clustering for semantic analysis