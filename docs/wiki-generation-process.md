# Wiki Generation Process

## Overview
The wiki generation pipeline transforms indexed construction documents into a structured, navigable knowledge base with organized pages and sections.

## End-to-End Flow

### 1. Trigger Points
Wiki generation can be initiated through:
- **Automatic**: Webhook callback after indexing completion
- **Manual**: API call to `/api/wiki/runs` endpoint

### 2. Pipeline Steps

#### Step 1: Metadata Collection
- Extracts document metadata from indexed chunks
- Collects document types, titles, dates, and structural information
- Creates document inventory for overview generation

#### Step 2: Overview Generation
- Generates project summary from collected metadata
- Creates high-level project description
- Identifies key themes and document categories

#### Step 3: Semantic Clustering
- Groups related content using vector similarity
- Clusters chunks by semantic meaning (cosine similarity threshold: 0.85)
- Identifies natural content groupings for wiki structure

#### Step 4: Structure Generation
- Analyzes clusters to define wiki hierarchy
- Creates page titles and navigation structure
- Generates table of contents with logical organization

#### Step 5: Page Content Retrieval
- Retrieves relevant chunks for each wiki page
- Performs semantic search (top 20 chunks per page)
- Ensures comprehensive coverage of page topics

#### Step 6: Markdown Generation
- Transforms retrieved content into formatted markdown
- Generates structured pages with headers, sections, and references
- Creates navigation links between related pages

### 3. Storage & Access
- Wiki pages stored in `wiki_pages` table
- Metadata stored in `wiki_runs` table
- Content accessible via public or authenticated routes

### 4. Integration Flow
```
Document Upload → Indexing (Beam) → Webhook → Wiki Generation → Structured Wiki
```

## Configuration
- Pipeline config: `backend/src/config/pipeline/pipeline_config.json`
- LLM models: OpenRouter (generation), Voyage AI (embeddings)
- Clustering threshold: 0.85 cosine similarity
- Retrieval: Top 20 chunks per page

## API Access
- Create wiki: `POST /api/wiki/runs`
- Get pages: `GET /api/wiki/runs/{wiki_run_id}/pages`
- Get content: `GET /api/wiki/runs/{wiki_run_id}/pages/{page_name}`