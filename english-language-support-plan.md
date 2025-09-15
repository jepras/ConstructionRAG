# English Language Support Implementation Plan

## Overview
Add support for English language selection during project upload, ensuring the language choice persists through the entire pipeline (indexing → wiki generation → Q&A).

## Current State
- System defaults to Danish for all operations
- `pipeline_config.json` has `language: "danish"` hardcoded
- Pipeline steps load fresh config from `ConfigService` (ignoring stored run configs)
- All prompts are hardcoded in Danish

## Required Changes

### 1. Frontend Changes
**File: Frontend upload form**
- [ ] Add language selector dropdown (English/Danish) 
- [ ] Default to English
- [ ] Pass language parameter in upload API call

### 2. Backend API Changes

#### Upload Endpoint (`/api/uploads`)
**File: `backend/src/api/documents.py`**
```python
@router.post("/uploads", response_model=UploadCreateResponse)
async def create_upload(
    # ... existing parameters
    language: str = Form("english"),  # 🆕 ADD THIS
):
    # Load base config and override language
    config_service = ConfigService()
    base_config = config_service._load_config()  # Load raw config
    base_config["defaults"]["language"] = language  # Override language
    
    # Store with language-specific config
    db.table("indexing_runs").insert({
        "pipeline_config": base_config,  # Store complete config with language
        # ... existing fields
    })
```

### 3. Pipeline Configuration Changes

#### Default Config Update
**File: `backend/src/config/pipeline/pipeline_config.json`**
```json
{
  "defaults": {
    "language": "english"  // Change default from "danish" to "english"
  }
}
```

#### Remove Language-Specific Hardcoded Settings
**File: `backend/src/config/pipeline/pipeline_config.json`**
- [ ] Remove `ocr_languages: ["dan"]` from indexing.partition
- [ ] Remove `language: "danish"` from query.generation.response_format  
- [ ] Add dynamic language mapping logic

### 4. Pipeline Steps - Use Stored Config

**Important:** The indexing orchestrator already passes the stored config to each step. The partition step receives it in `config` parameter.

#### For Indexing Steps (Already Receiving Config):
The indexing orchestrator passes config to steps, so partition step just needs to read language from it:

```python
# In PartitionStep.__init__ (already receives config):
def __init__(self, config: Dict[str, Any], ...):
    # Config already contains the stored pipeline_config with language
    language = config.get("defaults", {}).get("language", "english")
    self.ocr_languages = self._get_ocr_languages(language)
```

#### For Wiki Generation Steps:
Wiki generation steps need to receive the indexing run's stored config. **The wiki orchestrator currently uses fresh config from ConfigService, which is WRONG.**

**File: `backend/src/pipeline/wiki_generation/orchestrator.py`**

```python
# In WikiGenerationOrchestrator.run_pipeline method:
async def run_pipeline(
    self,
    index_run_id: str,
    user_id: UUID | None = None,
    project_id: UUID | None = None,
    upload_type: UploadType | str = "user_project",
) -> WikiGenerationRun:
    # 🆕 CRITICAL: Fetch the indexing run's stored config with language
    run_result = self.supabase.table("indexing_runs").select("pipeline_config").eq("id", str(index_run_id)).execute()
    
    if run_result.data and run_result.data[0].get("pipeline_config"):
        stored_config = run_result.data[0]["pipeline_config"]
        
        # Override the fresh config with stored config (includes user's language choice)
        self.config = stored_config
        
        # Re-initialize steps with the correct language config
        self.steps = self._initialize_steps(db_client=self.supabase)
        
        logger.info(f"🌐 Wiki generation using language: {stored_config.get('defaults', {}).get('language', 'unknown')}")
    
    # Continue with normal pipeline execution...
```

**Why this is critical:** Without this change, wiki generation will always use the default language from `pipeline_config.json`, ignoring the user's language choice!

#### Files That Need Updates:
- [ ] `backend/src/pipeline/indexing/steps/partition.py` - Read language from passed config
- [ ] `backend/src/pipeline/wiki_generation/orchestrator.py` - Pass stored config to steps
- [ ] `backend/src/pipeline/wiki_generation/steps/semantic_clustering.py` - Use passed config
- [ ] `backend/src/pipeline/wiki_generation/steps/overview_generation.py` - Use passed config
- [ ] `backend/src/pipeline/wiki_generation/steps/structure_generation.py` - Use passed config
- [ ] `backend/src/pipeline/wiki_generation/steps/markdown_generation.py` - Use passed config

### 5. Language-Aware Prompt Updates (Single English Prompt Approach)

#### Generation Step
**File: `backend/src/pipeline/querying/steps/generation.py`**

**New Universal English Prompt with Language Output Instruction:**
```python
def _create_prompt(self, query: str, context: str, language: str = "english") -> str:
    # Map language codes to full names for clearer instruction
    language_names = {
        "english": "English",
        "danish": "Danish",
        "norwegian": "Norwegian",  # Future support
        "swedish": "Swedish",      # Future support
    }
    output_language = language_names.get(language, "English")
    
    prompt = f"""You are an expert in construction and building engineering. Answer the following question based on the provided context:

QUESTION:
{query}

CONTEXT:
{context}

Assess whether to provide a detailed comprehensive answer or a brief response.

IMPORTANT:
- If insufficient context, respond ONLY: "I don't have enough information to answer your question"
- Use precise and factual information
- Cite relevant sources using numbered references [1], [2], etc.
- Include a "References:" section with format:
  [1] document-name.pdf, page X
  [2] other-document.pdf, page Y
- Keep response under 500 words
- Format in plain text, no markdown

Output your response in {output_language}.

ANSWER:"""
    
    return prompt
```

**Error Messages with Language Support:**
```python
def get_error_message(self, error_type: str, language: str = "english") -> str:
    """Get error message in appropriate language."""
    error_messages = {
        "no_info": {
            "english": "Sorry, I couldn't find relevant information for your question.",
            "danish": "Beklager, jeg kunne ikke finde relevant information til dit spørgsmål.",
        },
        "generation_failed": {
            "english": "Sorry, I couldn't generate a response right now. Please try again later.",
            "danish": "Beklager, jeg kunne ikke generere et svar lige nu. Prøv venligst igen senere.",
        }
    }
    return error_messages.get(error_type, {}).get(language, error_messages[error_type]["english"])
```

#### Semantic Clustering Step  
**File: `backend/src/pipeline/wiki_generation/steps/semantic_clustering.py`**

**New Universal English Prompt with Language Output Instruction:**
```python
def _create_cluster_naming_prompt(self, samples_text: str, language: str = "english") -> str:
    language_names = {
        "english": "English",
        "danish": "Danish",
    }
    output_language = language_names.get(language, "English")
    
    return f"""Based on the following document content from a construction project database, generate short, descriptive names for each cluster.

Names should be:
- Short and precise (2-4 words)
- Descriptive of cluster content
- Professional and technical
- Unique (no repetitions)

Document clusters:
{samples_text}

Generate names in the following format:
Cluster 0: [Name]
Cluster 1: [Name]
...

Output your response in {output_language}.
"""
```

**Fallback Names:**
```python
generic_names = {
    "danish": [
        "Tekniske Specifikationer",
        "Projektdokumentation", 
        "Bygningskomponenter",
        # ...
    ],
    "english": [
        "Technical Specifications",
        "Project Documentation",
        "Building Components", 
        # ...
    ]
}
fallback_names = generic_names.get(language, generic_names["english"])
```

#### Markdown Generation Step
**File: `backend/src/pipeline/wiki_generation/steps/markdown_generation.py`**

**New Universal Approach:**
```python
# In the prompt construction:
language_names = {
    "english": "English",
    "danish": "Danish",
}
output_language = language_names.get(language, "English")

# In the prompt string:
"""
IMPORTANT: 
- Generate the content in {output_language} language.
- Avoid filler text. Get straight to the point.
- Prioritize bullets for readability.
"""
```

### 6. OCR Language Mapping - COMPLETE IMPLEMENTATION

**File: `backend/src/pipeline/indexing/steps/partition.py`**

The partition step currently reads OCR languages from config (line 61):
```python
# CURRENT:
self.ocr_languages = config.get("ocr_languages", ["dan"])
```

**UPDATE TO:**
```python
# In __init__ method (line 61):
# Get language from config and map to OCR languages
language = config.get("language", "english")  # From defaults.language
self.ocr_languages = self._get_ocr_languages(language)

# Add new method to PartitionStep class:
def _get_ocr_languages(self, language: str) -> list[str]:
    """Map language setting to OCR language codes."""
    ocr_mapping = {
        "english": ["eng"],
        "danish": ["dan"],
        "multilingual": ["eng", "dan"]  # Support both if needed
    }
    return ocr_mapping.get(language, ["eng"])
```

**How the config flows:**
1. Orchestrator passes stored `pipeline_config` to PartitionStep
2. PartitionStep reads `config["defaults"]["language"]`
3. Maps language to OCR codes
4. Uses correct OCR languages for document processing

### 7. Query Pipeline Integration - COMPLETE IMPLEMENTATION

#### A. Authenticated Users (Private Projects)
**Context:** When user is on Q&A tab at `/dashboard/projects/{projectSlug}/{runId}`, the frontend already knows the `runId` (indexing_run_id).

**File: `backend/src/api/queries.py` (or similar query endpoint)**
```python
@router.post("/queries", response_model=QueryResponse)
async def create_query(
    query_text: str,
    indexing_run_id: UUID,  # 🆕 ADD THIS - comes from frontend context
    # ... existing parameters
):
    # Get language from the specific indexing run's stored config
    db = get_supabase_client()
    result = db.table("indexing_runs").select("pipeline_config").eq("id", str(indexing_run_id)).execute()
    
    language = "english"  # default fallback
    if result.data and result.data[0].get("pipeline_config"):
        pipeline_config = result.data[0]["pipeline_config"]
        language = pipeline_config.get("defaults", {}).get("language", "english")
    
    # Pass language to query pipeline
    response = await query_pipeline.process(
        query_text, 
        indexing_run_id=indexing_run_id,
        language=language
    )
    return response
```

#### B. Public/Anonymous Users (Public Projects)
**Context:** When anonymous user is on Q&A tab at `/projects/{projectNameWithId}`, the URL contains the full indexing run ID embedded in the slug.

**Example URL:** `/projects/klub-guldberg-bygge-wiki-eae48abc-0129-4f7a-8953-eca865ec880b`

**File: `frontend/src/app/projects/[indexingRunId]/page.tsx` (or similar)**
```typescript
// Public pages use composite slug format: projectname-uuid
// The entire slug IS the indexingRunId
const { indexingRunId } = useParams(); 
// indexingRunId = "klub-guldberg-bygge-wiki-eae48abc-0129-4f7a-8953-eca865ec880b"

// Extract the UUID portion (last 36 characters for standard UUID)
const extractUUID = (slug: string) => {
  // UUID pattern: 8-4-4-4-12 characters (36 total with hyphens)
  const uuidMatch = slug.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
  return uuidMatch ? uuidMatch[0] : slug;
};

const submitQuery = async (queryText: string) => {
  const actualIndexingRunId = extractUUID(indexingRunId);
  
  // Same API call - indexing_run_id determines language, not auth status
  const response = await fetch('/api/queries', {
    method: 'POST',
    body: JSON.stringify({
      query_text: queryText,
      indexing_run_id: actualIndexingRunId,  // ✅ Pass the extracted UUID
      // No auth token needed for public projects
    })
  });
};
```

**Backend handles both authenticated and public queries the same way:**
- Both pass `indexing_run_id`
- Backend fetches language from that indexing run's `pipeline_config`
- Language determines response language regardless of auth status

**Update Query Orchestrator:**
```python
# In QueryOrchestrator.process method:
async def process(self, query: str, indexing_run_id: UUID = None, language: str = "english"):
    # Pass language to generation step
    generation_config = GenerationConfig(
        model=self.config["generation"]["model"],
        language=language,  # 🆕 ADD THIS
        # ... other config
    )
```

## Implementation Order

### Phase 1: Configuration Infrastructure
1. [ ] Update `pipeline_config.json` default language to English
2. [ ] Add language parameter to `/uploads` endpoint
3. [ ] Modify upload logic to store language in pipeline_config

### Phase 2: Pipeline Step Updates  
4. [ ] Update all pipeline steps to use stored config instead of fresh ConfigService
5. [ ] Add language parameter passing to all step constructors

### Phase 3: Language-Aware Processing
6. [ ] Update generation.py prompts to be language-aware
7. [ ] Update semantic_clustering.py prompts and fallbacks
8. [ ] Update markdown_generation.py language instructions
9. [ ] Add OCR language mapping

### Phase 4: Query Integration
10. [ ] Add language context to query endpoints
11. [ ] Test full end-to-end language flow

### Phase 5: Frontend & Testing
12. [ ] Add language selector to frontend upload
13. [ ] Test English and Danish pipelines
14. [ ] Update automated tests

## Key Insight

The main issue is that **pipeline steps ignore stored configs and always load fresh from ConfigService**. This must be fixed for language persistence to work properly.

## Success Criteria Verification

This plan now fully addresses all success criteria:

### ✅ Criterion 1: Allow user to choose English at /upload page, stored in pipeline_config
- Frontend language selector added (Phase 5)
- Upload endpoint accepts `language` parameter  
- Language stored in `pipeline_config["defaults"]["language"]`

### ✅ Criterion 2: Indexing pipeline reads from pipeline_config for OCR language
- PartitionStep reads language from passed config (Section 6)
- Maps language to OCR codes dynamically
- Uses correct OCR languages for document processing

### ✅ Criterion 3: Wiki generation uses language for chunks & prompts  
- **CRITICAL FIX:** Wiki orchestrator must fetch indexing run's stored config (Section 4)
- Without this fix, wiki generation ignores user's language choice!
- All wiki steps use language from passed config
- Prompts made language-aware (Section 5)

### ✅ Criterion 4: Q&A responses use language from pipeline_config
- Query endpoint receives `indexing_run_id` from frontend context (Section 7)
- Fetches language from specific indexing run's `pipeline_config`
- Generation step uses language-aware prompts

## Testing Checklist

- [ ] Upload project with English → Verify `pipeline_config` has `"language": "english"`
- [ ] Upload project with Danish → Verify `pipeline_config` has `"language": "danish"`
- [ ] Indexing uses correct OCR languages (eng vs dan)
- [ ] Wiki generation produces English/Danish content based on config
- [ ] Q&A responses match language from indexing run's config
- [ ] Fallback content appears in correct language