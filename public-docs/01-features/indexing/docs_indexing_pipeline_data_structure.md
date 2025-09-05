# Indexing Pipeline Data Structure and Relationships

## Overview

This document explains the comprehensive data structure and relationships within SpecFinder's indexing pipeline - a sophisticated document processing system that transforms construction PDFs into searchable knowledge bases through a 5-step processing pipeline.

The system uses a dual-tracking approach where both indexing runs and individual documents store step results, enabling fine-grained progress tracking and flexible processing workflows.

## Core Architecture

The indexing pipeline follows a many-to-many relationship model between indexing runs and documents, with sophisticated step result tracking at multiple levels:

```mermaid
erDiagram
    projects ||--o{ indexing_runs : "has many"
    indexing_runs ||--o{ indexing_run_documents : "processes through"
    documents ||--o{ indexing_run_documents : "belongs to"
    documents ||--o{ document_chunks : "contains"
    indexing_runs ||--o{ query_runs : "enables"
    indexing_runs ||--o{ wiki_generation_runs : "generates"
    
    projects {
        uuid id PK
        uuid user_id FK
        text name
        text description
        text access_level
        timestamptz created_at
        timestamptz updated_at
    }
    
    indexing_runs {
        uuid id PK
        text upload_type
        uuid user_id FK
        text access_level
        uuid project_id FK
        text status
        jsonb step_results
        jsonb pipeline_config
        timestamptz started_at
        timestamptz completed_at
        text error_message
        timestamptz created_at
        timestamptz updated_at
    }
    
    documents {
        uuid id PK
        uuid user_id FK
        text access_level
        text filename
        integer file_size
        text file_path
        integer page_count
        text status
        jsonb step_results
        text indexing_status
        text error_message
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }
    
    indexing_run_documents {
        uuid id PK
        uuid indexing_run_id FK
        uuid document_id FK
        timestamptz created_at
    }
    
    document_chunks {
        uuid id PK
        uuid document_id FK
        integer chunk_index
        text content
        vector embedding
        jsonb metadata
        integer page_number
        text section_title
        timestamptz created_at
    }
```

## Entity Relationships and Purpose

### 1. Projects - Project Management Layer
**Purpose**: Organizational containers for related documents and processing runs

**Key Features**:
- Owner-only access control by default
- Support for multiple indexing runs per project
- Access levels: `public`, `auth`, `owner`, `private`

### 2. Indexing Runs - Processing Orchestration
**Purpose**: High-level processing coordination and run-level step tracking

**Key Features**:
- **Many-to-many relationship** with documents through junction table
- **Dual upload types**: `email` (anonymous) vs `user_project` (authenticated)
- **Pipeline configuration storage** for reproducible processing
- **Aggregate step results** combining all document processing

**Step Results Structure**:
```json
{
  "partition": {
    "step": "partition",
    "status": "completed",
    "duration_seconds": 45.2,
    "summary_stats": {
      "text_elements": 156,
      "table_elements": 12,
      "extracted_pages": 8
    },
    "started_at": "2025-01-15T10:00:00Z",
    "completed_at": "2025-01-15T10:00:45Z"
  },
  "metadata": { /* ... */ },
  "enrichment": { /* ... */ },
  "chunking": { /* ... */ },
  "embedding": { /* ... */ }
}
```

### 3. Documents - Individual File Processing
**Purpose**: File-level metadata and document-specific step results

**Key Features**:
- **Individual step tracking** for each document in a multi-document run
- **Processing status management** with detailed error tracking
- **Current step detection** for progress visualization
- **File metadata storage** (size, pages, storage path)

**Document Step Results**:
- Mirrors indexing run structure but specific to individual documents
- Enables partial processing recovery and document-level debugging
- Supports computed properties for timing analysis

### 4. Indexing Run Documents Junction Table
**Purpose**: Many-to-many relationship management

**Key Features**:
- Enables batch processing of multiple documents in single runs
- Supports document reprocessing across different runs
- Maintains processing history and audit trails

### 5. Document Chunks - Vector Storage
**Purpose**: Final processed units for semantic search and retrieval

**Key Features**:
- **1024-dimensional embeddings** using Voyage-multilingual-2
- **Semantic chunking** with 1000 character size, 200 character overlap
- **Rich metadata** including page numbers, section titles, processing context
- **pgvector integration** for high-performance similarity search

## Processing Pipeline Flow

The indexing pipeline processes documents through five sequential steps, with results stored at both run and document levels:

```mermaid
flowchart TD
    A[Document Upload] --> B[Create Indexing Run]
    B --> C[Create Junction Record]
    C --> D[Step 1: Partition]
    D --> E[Step 2: Metadata Extraction]
    E --> F[Step 3: Enrichment]
    F --> G[Step 4: Chunking]
    G --> H[Step 5: Embedding]
    H --> I[Create Document Chunks]
    
    D --> D1[Update Document Step Results]
    E --> E1[Update Document Step Results]
    F --> F1[Update Document Step Results]
    G --> G1[Update Document Step Results]
    H --> H1[Update Document Step Results]
    
    D1 --> D2[Update Run Aggregate Results]
    E1 --> E2[Update Run Aggregate Results]
    F1 --> F2[Update Run Aggregate Results]
    G1 --> G2[Update Run Aggregate Results]
    H1 --> H2[Update Run Aggregate Results]
    
    I --> J[Enable Querying & Wiki Generation]
    
    subgraph "Step Result Tracking"
        D1
        E1
        F1
        G1
        H1
    end
    
    subgraph "Run Coordination"
        D2
        E2
        F2
        G2
        H2
    end
```

### Step-by-Step Processing Details

#### 1. Partition Step (`PartitionStep`)
**Purpose**: Extract and structure content from PDFs

**Outputs**:
- Text elements with bounding boxes and font metadata
- Table elements with extracted content and images
- Full-page extractions for visual content
- Document type detection (scanned vs regular)

**Technologies**: PyMuPDF + Unstructured (for scanned documents)

#### 2. Metadata Step
**Purpose**: Extract document structure and hierarchical information

**Outputs**:
- Section headings and document outline
- Page-level metadata and complexity analysis
- Font analysis for semantic structure detection

#### 3. Enrichment Step
**Purpose**: Generate VLM captions for visual content

**Outputs**:
- AI-generated captions for tables and diagrams
- Enhanced metadata for visual elements
- Context-aware descriptions using Anthropic models

#### 4. Chunking Step
**Purpose**: Create semantic text chunks for vector search

**Outputs**:
- Semantic chunks with optimal size for retrieval
- Preserved document structure and context
- Cross-reference metadata linking chunks to source pages

#### 5. Embedding Step
**Purpose**: Generate vector embeddings for semantic search

**Outputs**:
- 1024-dimensional vectors using Voyage-multilingual-2
- Batch processing for efficiency
- Storage in pgvector-enabled PostgreSQL

## Data Flow Examples

### Single Document Processing
```mermaid
sequenceDiagram
    participant Client
    participant API
    participant IndexingRun
    participant Document
    participant Pipeline
    participant Storage
    
    Client->>API: Upload PDF
    API->>Document: Create document record
    API->>IndexingRun: Create indexing run
    API->>IndexingRun: Link document via junction table
    
    Pipeline->>Document: Start partition step
    Pipeline->>Document: Update step_results.partition
    Pipeline->>IndexingRun: Aggregate to run step_results
    
    Pipeline->>Document: Start metadata step
    Pipeline->>Document: Update step_results.metadata  
    Pipeline->>IndexingRun: Aggregate to run step_results
    
    Pipeline->>Document: Process through remaining steps
    Pipeline->>Storage: Create document_chunks with embeddings
    
    Pipeline->>IndexingRun: Mark run as completed
    Pipeline->>Document: Mark document as completed
```

### Multi-Document Batch Processing
```mermaid
sequenceDiagram
    participant Client
    participant API
    participant IndexingRun
    participant Doc1
    participant Doc2
    participant Doc3
    participant Pipeline
    
    Client->>API: Upload multiple PDFs
    API->>Doc1: Create document 1
    API->>Doc2: Create document 2
    API->>Doc3: Create document 3
    API->>IndexingRun: Create single run
    API->>IndexingRun: Link all documents
    
    Pipeline->>Doc1: Process document 1 through all steps
    Pipeline->>Doc2: Process document 2 through all steps
    Pipeline->>Doc3: Process document 3 through all steps
    
    Pipeline->>IndexingRun: Aggregate all document results
    Pipeline->>IndexingRun: Mark run as completed when all docs done
```

## Access Control and Security

The system implements sophisticated access control through multiple levels:

### Upload Types
- **Email uploads**: Anonymous access, public sharing enabled
- **User project uploads**: Authenticated access with Row Level Security

### Access Levels
- **Public**: Anonymous read access
- **Auth**: Any authenticated user
- **Owner**: Resource owner only  
- **Private**: Restricted access

### Row Level Security (RLS)
PostgreSQL RLS policies ensure users can only access their own data:

```sql
-- Documents: Users can only access their own documents
CREATE POLICY "Users can access their own documents" ON documents
    FOR ALL USING (user_id::uuid = auth.uid());

-- Indexing runs: Access based on document ownership
CREATE POLICY "Users can access indexing runs for their documents" ON indexing_runs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM indexing_run_documents ird
            JOIN documents d ON ird.document_id = d.id
            WHERE ird.indexing_run_id = indexing_runs.id
            AND d.user_id::uuid = auth.uid()
        )
    );
```

## Performance Optimizations

### Database Indexing Strategy
```sql
-- Vector search optimization
CREATE INDEX idx_document_chunks_embedding ON document_chunks 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Step results querying
CREATE INDEX idx_documents_step_results ON documents USING GIN (step_results);

-- Junction table optimization
CREATE INDEX idx_indexing_run_documents_indexing_run_id ON indexing_run_documents(indexing_run_id);
CREATE INDEX idx_indexing_run_documents_document_id ON indexing_run_documents(document_id);
```

### Computed Properties
Documents and indexing runs include computed properties for efficient querying:

```python
@computed_field(return_type=dict[str, float])
def step_timings(self) -> dict[str, float]:
    """Extract step timings from step_results"""
    timings = {}
    for step_name, step_data in self.step_results.items():
        if isinstance(step_data, dict) and "duration_seconds" in step_data:
            timings[step_name] = step_data["duration_seconds"]
    return timings

@computed_field(return_type=str | None)  
def current_step(self) -> str | None:
    """Get the current step being processed"""
    step_order = ["partition", "metadata", "enrichment", "chunking", "embedding"]
    for step_name in step_order:
        step_data = self.step_results.get(step_name)
        if not step_data or step_data.get("status") != "completed":
            return step_name
    return None  # All steps completed
```

## Integration with Other Systems

### Wiki Generation Pipeline
Indexing runs automatically trigger wiki generation upon completion:

```mermaid
flowchart LR
    A[Indexing Run Completed] --> B[Webhook Triggered]
    B --> C[Wiki Generation Run Created]
    C --> D[Semantic Content Analysis]
    D --> E[Wiki Structure Generation]
    E --> F[Markdown Page Creation]
    F --> G[Storage & URL Generation]
```

### Query System Integration
Document chunks enable sophisticated query processing:

```mermaid
flowchart TD
    A[User Query] --> B[Query Processing Step]
    B --> C[Vector Similarity Search]
    C --> D[Retrieve Relevant Chunks]
    D --> E[Context Assembly]
    E --> F[LLM Generation]
    F --> G[Response with Sources]
    
    C --> H[(Document Chunks Table)]
    H --> I[pgvector Similarity Search]
    I --> J[Ranked Results by Similarity]
```

### Error Handling and Recovery

The dual-tracking system enables sophisticated error handling:

1. **Document-level failures**: Individual documents can fail without affecting the entire run
2. **Step-level recovery**: Processing can resume from any failed step
3. **Partial success scenarios**: Some documents in a batch can complete while others fail
4. **Detailed error tracking**: Error messages and details stored at both document and run levels

## Code References

### Key Files
- **Database Schema**: `/supabase/migrations/`
  - `20250728080000_add_pipeline_tables.sql` - Initial indexing run structure
  - `20250801030000_redesign_document_indexing_relationship.sql` - Many-to-many junction table
  - `20250802010000_add_step_results_to_documents.sql` - Document-level step tracking

- **Data Models**: `/backend/src/models/`
  - `pipeline.py` - IndexingRun, StepResult, and related models
  - `domain/document.py` - Document model with computed properties

- **Pipeline Implementation**: `/backend/src/pipeline/indexing/steps/`
  - `partition.py` - PDF processing and content extraction
  - `chunking.py` - Semantic text chunking
  - `embedding.py` - Vector embedding generation

### Example Usage

```python
# Create indexing run for user project
indexing_run = IndexingRun(
    upload_type=UploadType.USER_PROJECT,
    user_id=user.id,
    project_id=project.id,
    status=PipelineStatus.PENDING
)

# Process document through pipeline
for step_name in ["partition", "metadata", "enrichment", "chunking", "embedding"]:
    step_result = await pipeline_step.execute(document_input)
    
    # Update document step results
    document.step_results[step_name] = step_result
    
    # Aggregate to run level
    indexing_run.step_results[step_name] = aggregate_step_results(
        [doc.step_results[step_name] for doc in run_documents]
    )

# Final chunk creation
chunks = await create_document_chunks(enriched_content, embeddings)
```

This architecture provides a robust, scalable foundation for processing construction documents while maintaining detailed audit trails and enabling flexible recovery scenarios.