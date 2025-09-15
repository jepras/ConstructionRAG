# Language Parameter Flow Analysis

## Current State Analysis

Based on my analysis of the codebase, here's the complete flow and what needs to be updated for language parameter persistence:

## 🔍 Current Language Support Status

### ✅ Already Implemented
- **WikiGenerationRun model**: Has `language: str = Field("danish")` (Line 104 in `pipeline.py`)
- **WikiGenerationRunCreate model**: Has `language: str = "danish"` (Line 424)
- **Database storage**: `wiki_generation_runs` table already stores language
- **API query support**: Pipeline API already selects `language` from wiki runs (Line 109)

### ❌ Missing Components
- **Upload endpoint**: No language parameter in `/uploads` POST endpoint
- **IndexingRun model**: No `language` field in the indexing run model
- **Pipeline config**: No language parameter passed to indexing pipeline
- **Query pipeline**: No language-aware response generation

## 📊 Complete Data Flow & Required Updates

### 1. Frontend Upload → Backend Storage
**Current Flow:**
```
Frontend → POST /uploads → IndexingRun (no language) → Beam processing
```

**Required Updates:**
```python
# API Endpoint: /uploads
@router.post("/uploads", response_model=UploadCreateResponse)
async def create_upload(
    # ... existing parameters
    language: str = Form("english"),  # 🆕 ADD THIS
):
    # Load base pipeline config and override language
    config = load_pipeline_config()
    config["defaults"]["language"] = language
    
    # Store in indexing_runs table with complete config
    db.table("indexing_runs").insert({
        "pipeline_config": config,  # 🆕 UPDATED - includes language
        # ... existing fields
    })
```

**No Pydantic Model Changes Required:**
- `IndexingRun` model already has `pipeline_config: dict[str, Any] | None`
- Language will be stored as `pipeline_config.defaults.language`
- Access language via: `indexing_run.pipeline_config["defaults"]["language"]`

### 2. Indexing Pipeline Configuration
**Current Flow:**
```
Beam gets indexing_run_id → Loads default pipeline_config.json → No language context
```

**Required Updates:**
```python
# Pipeline config loading needs to:
1. Fetch indexing run from DB including pipeline_config field
2. Use stored pipeline_config (which includes language) instead of defaults
3. Pass language-aware config to all pipeline steps

# In Beam processing:
indexing_run = get_indexing_run(indexing_run_id)
config = indexing_run.pipeline_config  # Already contains language setting
language = config["defaults"]["language"]  # Extract for pipeline steps
```

### 3. Wiki Generation Webhook
**Current Flow:**
```
Indexing complete → Webhook → WikiGenerationRun (has language) ✅ Already works
```

**No changes needed** - This already works because:
- Wiki generation fetches the indexing run 
- WikiGenerationRun model already has language field
- Language gets stored properly

### 4. Query/Response Generation
**Current Flow:**
```
User query → No language context → Danish-hardcoded prompts
```

**Required Updates:**
```python
# Query endpoint needs to:
1. Accept indexing_run_id parameter
2. Fetch indexing run to get language from pipeline_config
3. Pass language to generation step
4. Use language-aware prompts

# In query processing:
indexing_run = get_indexing_run(indexing_run_id)
language = indexing_run.pipeline_config["defaults"]["language"]
```

## 🗄️ Database Schema Updates

### No Database Schema Changes Required! ✅

The `indexing_runs` table already has a `pipeline_config` JSONB column that can store the language setting:

```json
{
  "defaults": {
    "language": "english"
  },
  // ... rest of pipeline config
}
```

This approach is much cleaner because:
- No new columns needed
- Language is part of the complete pipeline configuration
- Easy to extend with other language-related settings
- Maintains consistency with existing config storage pattern

## 🔧 API Endpoints Requiring Updates

### 1. POST `/uploads` (Critical)
**Add language parameter:**
```python
language: str = Form("english")  # Default to English
```

### 2. POST `/queries` (Critical)  
**Add indexing_run_id to get language context:**
```python
async def create_query(
    indexing_run_id: UUID,  # 🆕 ADD THIS to get language context
    query_text: str,
    # ... existing parameters
):
    # Fetch indexing run to get language
    indexing_run = await get_indexing_run(indexing_run_id)
    language = indexing_run.language
    
    # Pass language to generation pipeline
    response = await query_pipeline.process(query_text, language=language)
```

### 3. POST `/indexing-runs` (If exists - needs language parameter)

## 📋 Implementation Checklist

### Phase 1: Data Storage (Critical)
- [ ] Add `language` parameter to `/uploads` endpoint  
- [ ] Update upload logic to store language in `pipeline_config`
- [ ] Load base config and override language before storing

### Phase 2: Pipeline Configuration (Critical)
- [ ] Update pipeline config loading to read language from indexing_run
- [ ] Modify `pipeline_config.json` to have `defaults.language: "english"`
- [ ] Update Beam integration to pass language-aware config

### Phase 3: Language-Aware Processing (Critical)
- [ ] Update generation.py to use language parameter
- [ ] Update semantic_clustering.py to use language parameter
- [ ] Update markdown_generation.py to use language parameter
- [ ] Add language parameter to query endpoints

### Phase 4: Frontend Integration (Medium)
- [ ] Add language selector to upload form
- [ ] Update upload API calls to include language
- [ ] Store user language preference

### Phase 5: Testing & Validation (Medium)
- [ ] Test English pipeline end-to-end
- [ ] Test Danish pipeline backward compatibility
- [ ] Validate language persistence through full lifecycle
- [ ] Update automated tests

## 🚨 Critical Path Dependencies

1. **Upload API** must accept language parameter first
2. **IndexingRun model** must store language 
3. **Pipeline config** must read language from stored indexing run
4. **Processing steps** must use language parameter
5. **Query API** must get language context from indexing run

## 💡 Recommended Implementation Order

1. **Backend Models & API**: Add language fields and upload endpoint parameter
2. **Pipeline Configuration**: Update config loading to be language-aware  
3. **Processing Steps**: Update prompt generation to use language parameter
4. **Query Integration**: Make queries language-aware
5. **Frontend**: Add language selector to upload flow

This ensures the language parameter flows correctly from user selection → storage → processing → output throughout the entire project lifecycle.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Analyze current data flow for pipeline config persistence", "status": "completed", "activeForm": "Analyzing current data flow for pipeline config persistence"}, {"content": "Check API endpoints that need language parameter", "status": "completed", "activeForm": "Checking API endpoints that need language parameter"}, {"content": "Review Pydantic models for language support", "status": "completed", "activeForm": "Reviewing Pydantic models for language support"}, {"content": "Identify database schema updates needed", "status": "completed", "activeForm": "Identifying database schema updates needed"}, {"content": "Document complete language parameter flow", "status": "completed", "activeForm": "Documenting complete language parameter flow"}]