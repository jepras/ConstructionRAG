# Wiki Generation Implementation Guide

## Overview

The wiki generation system is a 7-step RAG pipeline that creates comprehensive markdown documentation from construction project data. It uses semantic clustering, strategic page planning, and professional markdown generation with Mermaid diagrams and citations.

## Architecture

### Pipeline Steps

1. **Metadata Collection** - Collects project metadata and document chunks from Supabase
2. **Overview Generation** - Retrieves relevant content and generates project overview using LLM
3. **Structure Generation** - Creates strategic wiki page structure using LLM
4. **Page Content Retrieval** - Retrieves specific content for each planned page
5. **Markdown Generation** - Generates professional markdown pages with diagrams and citations

### Key Components

- **Orchestrator**: `backend/src/pipeline/wiki_generation/orchestrator.py`
- **Configuration**: `backend/src/pipeline/wiki_generation/config/wiki_config.py`
- **Steps**: `backend/src/pipeline/wiki_generation/steps/`
- **API Endpoints**: `backend/src/api/wiki.py`

## Configuration

### WikiConfig Settings

```python
# backend/src/pipeline/wiki_generation/config/wiki_config.py
class WikiConfig(BaseModel):
    language: str = Field("danish", description="Output language")
    model: str = Field("google/gemini-2.5-flash", description="LLM model to use")
    similarity_threshold: float = Field(0.3, description="Similarity threshold for vector search")
    max_chunks_per_query: int = Field(10, description="Maximum chunks to return per query")
    overview_query_count: int = Field(12, description="Number of overview queries to use")
    max_pages: int = Field(10, description="Maximum number of pages to generate")
    max_queries_per_page: int = Field(10, description="Maximum number of queries per page")
```

## API Endpoints

### 1. Generate Wiki

**Endpoint**: `POST /api/wiki/generate`

**Request Body**:
```json
{
  "index_run_id": "668ecac8-beb5-4f94-94d6-eee8c771044d",
  "config": {
    "language": "danish",
    "model": "google/gemini-2.5-flash",
    "max_pages": 10,
    "max_queries_per_page": 10
  }
}
```

**Response**:
```json
{
  "wiki_run_id": "uuid",
  "status": "completed",
  "pages": [
    {
      "id": "page-1",
      "title": "Projekt Oversigt",
      "description": "Comprehensive project overview",
      "content": "# Projekt Oversigt\n\n...",
      "content_length": 11586
    }
  ],
  "metadata": {
    "total_documents": 3,
    "total_chunks": 479,
    "processing_time": 45.2
  }
}
```

### 2. Get Wiki Status

**Endpoint**: `GET /api/wiki/status/{wiki_run_id}`

**Response**:
```json
{
  "wiki_run_id": "uuid",
  "status": "in_progress|completed|failed",
  "progress": {
    "current_step": 3,
    "total_steps": 5,
    "step_name": "Structure Generation"
  },
  "error": null
}
```

### 3. Get Wiki Pages

**Endpoint**: `GET /api/wiki/pages/{wiki_run_id}`

**Response**:
```json
{
  "wiki_run_id": "uuid",
  "pages": [
    {
      "id": "page-1",
      "title": "Projekt Oversigt",
      "description": "Comprehensive project overview",
      "content": "# Projekt Oversigt\n\n...",
      "content_length": 11586,
      "created_at": "2025-01-07T14:25:10Z"
    }
  ]
}
```

### 4. Download Wiki

**Endpoint**: `GET /api/wiki/download/{wiki_run_id}`

**Response**: ZIP file containing all markdown pages

## Database Schema

### Wiki Generation Tables

```sql
-- Wiki generation runs
CREATE TABLE wiki_generation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    index_run_id UUID REFERENCES indexing_runs(id),
    config JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    progress JSONB,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Wiki pages
CREATE TABLE wiki_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wiki_run_id UUID REFERENCES wiki_generation_runs(id),
    page_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    content_length INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## File Storage

### Markdown Files Location

Generated markdown files are stored in:

1. **Database**: Full content stored in `wiki_pages` table
2. **File System**: Optional backup in `backend/data/internal/wiki_generation/`
3. **Frontend**: Can be downloaded as ZIP or accessed via API

### File Structure

```
backend/data/internal/wiki_generation/
├── wiki_run_20250807_142510/
│   ├── complete_seven_steps.json
│   └── wiki_pages/
│       ├── page-1.md
│       ├── page-2.md
│       └── page-3.md
```

## Frontend Integration

### 1. Wiki Generation Form

```typescript
interface WikiGenerationRequest {
  indexRunId: string;
  config: {
    language: 'danish' | 'english';
    model: string;
    maxPages: number;
    maxQueriesPerPage: number;
  };
}

const generateWiki = async (request: WikiGenerationRequest) => {
  const response = await fetch('/api/wiki/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  return response.json();
};
```

### 2. Progress Tracking

```typescript
const trackWikiProgress = async (wikiRunId: string) => {
  const response = await fetch(`/api/wiki/status/${wikiRunId}`);
  const status = await response.json();
  
  if (status.status === 'completed') {
    // Load wiki pages
    const pages = await fetch(`/api/wiki/pages/${wikiRunId}`);
    return pages.json();
  }
  
  return status;
};
```

### 3. Wiki Display

```typescript
interface WikiPage {
  id: string;
  title: string;
  description: string;
  content: string;
  contentLength: number;
}

const WikiPageViewer = ({ page }: { page: WikiPage }) => {
  return (
    <div className="wiki-page">
      <h1>{page.title}</h1>
      <p>{page.description}</p>
      <div 
        className="markdown-content"
        dangerouslySetInnerHTML={{ __html: marked(page.content) }}
      />
    </div>
  );
};
```

## Error Handling

### Common Errors

1. **No embeddings found**: Ensure documents have been indexed with embeddings
2. **API timeout**: Increase timeout for large projects
3. **Token limit exceeded**: Reduce max_pages or max_queries_per_page
4. **Invalid index_run_id**: Verify the indexing run exists and is completed

### Error Response Format

```json
{
  "error": "No embeddings found for documents",
  "details": "Index run 668ecac8-beb5-4f94-94d6-eee8c771044d has no document chunks with embeddings",
  "step": "overview_generation",
  "timestamp": "2025-01-07T14:25:10Z"
}
```

## Performance Considerations

### Optimization Tips

1. **Limit pages**: Start with 3-5 pages for testing
2. **Limit queries**: Use 4-6 queries per page initially
3. **Cache results**: Store generated wikis in database
4. **Background processing**: Use async processing for large projects
5. **Progress tracking**: Implement real-time progress updates

### Expected Processing Times

- **Small project** (1-3 documents): 30-60 seconds
- **Medium project** (5-10 documents): 2-5 minutes
- **Large project** (10+ documents): 5-15 minutes

## Testing

### Local Testing

```bash
# Test with specific index run
python test_wiki_generation_local.py --index-run-id 668ecac8-beb5-4f94-94d6-eee8c771044d

# Test with custom config
python test_wiki_generation_local.py --index-run-id <id> --max-pages 5 --max-queries 6
```

### Test Results Location

```
backend/test_results/
├── wiki_test_results_20250807_142510.json
└── wiki_test_results_20250807_141227.json
```

## Next Steps for Frontend Implementation

1. **Create wiki generation form** with configurable options
2. **Implement progress tracking** with real-time updates
3. **Add wiki page viewer** with markdown rendering
4. **Create download functionality** for ZIP files
5. **Add error handling** and user feedback
6. **Implement caching** for generated wikis
7. **Add search functionality** within wiki pages
8. **Create wiki management** (list, delete, regenerate)

## Key Files for Reference

- **Orchestrator**: `backend/src/pipeline/wiki_generation/orchestrator.py`
- **API Endpoints**: `backend/src/api/wiki.py`
- **Configuration**: `backend/src/pipeline/wiki_generation/config/wiki_config.py`
- **Test Script**: `backend/test_wiki_generation_local.py`
- **Reference Implementation**: `backend/markdown_generation_overview.py` 