# Multilingual Implementation Plan

## Overview
Convert the system from Danish-only to support both Danish and English based on a single `language` parameter in the pipeline configuration.

## Configuration Changes

### Pipeline Config Structure
Add a single `language` parameter under `defaults` in `pipeline_config.json`:

```json
{
  "defaults": {
    "language": "english",  // Default to English, overridden by user upload choice
    // ... other defaults
  }
}
```

Remove existing language-specific parameters:
- `indexing.partition.ocr_languages` (replace with dynamic language mapping)
- `query.generation.response_format.language` (use top-level language setting)

## Core Pipeline Updates

### 1. Generation.py (`backend/src/pipeline/querying/steps/generation.py`)

**Current Danish Prompt (Lines 206-231):**
```
Du er en ekspert på dansk byggeri og konstruktion. Du skal besvare følgende spørgsmål baseret på den kontekst du får leveret:
[Full Danish prompt...]
INSTRUKTIONER:
- Svar på dansk
- Vær præcis og faktuel
[...]
```

**New English-First Approach:**
```
You are an expert in construction and building engineering. Answer the following question based on the provided context:

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

Output your response in {language}.

ANSWER:
```

**Error Messages:**
- Line 103: `"Sorry, I couldn't find relevant information for your question."`
- Line 198: `"Sorry, I couldn't generate a response right now. Please try again later."`
- Add language parameter to return appropriate language version

### 2. Semantic Clustering (`backend/src/pipeline/wiki_generation/steps/semantic_clustering.py`)

**Current Danish Prompt (Lines 283-300):**
```
Baseret på følgende dokumentindhold fra en byggeprojekt-database, generer korte, beskrivende navne for hver klynge.

Navnene skal være:
- Korte og præcise (2-4 ord)
- Beskrivende for klyngens indhold
- Professionelle og faglige
- På dansk
- Unikke (ingen gentagelser)
```

**New English-First Approach:**
```
Based on the following document content from a construction project database, generate short, descriptive names for each cluster.

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

Output your response in {language}.
```

**Fallback Content Updates:**
- Lines 344-353: Convert generic names to English defaults
- Line 242: Change `"Temaområde {cluster_id}"` to `"Topic Area {cluster_id}"`

### 3. Markdown Generation (`backend/src/pipeline/wiki_generation/steps/markdown_generation.py`)

**Current Language Specification (Line 378):**
```
IMPORTANT: 
- Generate the content in Danish language.
```

**New Approach:**
```
IMPORTANT: 
- Generate the content in {language} language.
```

## Fallback Content & Error Messages

### Generic Fallback Names (English Defaults)
```python
generic_names = [
    "Technical Specifications",
    "Project Documentation", 
    "Building Components",
    "System Installations",
    "Execution Details",
    "Operations & Maintenance",
    "Quality Assurance",
    "Safety Requirements",
]
```

### Error Messages
Create language mapping for all user-facing messages:
- Console messages: Keep in English (for developers)
- User error responses: Language-dependent
- API error messages: Language-dependent

### Debug Messages
Keep all console/logging messages in English for developer consistency.

## Implementation Strategy

1. **Configuration Update**: Add `language` parameter to pipeline config defaults
2. **Language Context**: Pass language parameter to all step constructors
3. **Prompt Templates**: Convert all prompts to English base + language instruction suffix
4. **Fallback Mapping**: Create English/Danish mappings for all fallback content
5. **API Integration**: Ensure upload endpoints accept and store language preference
6. **Logging Integration**: Add comprehensive logging to verify language parameter propagation
7. **Testing**: Update tests to validate both languages

## Logging Requirements

### Language Parameter Verification
Add logging in each pipeline step to ensure proper language parameter handling:

**Step Initialization:**
```python
logger.info(f"🌐 {self.__class__.__name__} initialized with language: {self.language}")
```

**Language-Dependent Operations:**
```python
logger.info(f"🌐 Generating {operation_type} content in {self.language}")
logger.info(f"🌐 Using {self.language} prompt template")
logger.info(f"🌐 Applying {self.language} fallback content")
```

**Configuration Validation:**
```python
logger.info(f"🌐 Pipeline config language setting: {config.get('language', 'NOT_SET')}")
logger.warning(f"⚠️ Language parameter missing, falling back to: {fallback_language}")
```

### Debug Logging for Language Flow
- Log language parameter at pipeline orchestrator level
- Track language propagation through each step
- Validate language parameter exists before language-dependent operations
- Log when fallback language is used due to missing configuration

## OCR Language Mapping
Map config language to OCR language codes:
- `english` → `["eng"]`
- `danish` → `["dan"]`

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Analyze current multilingual architecture requirements", "status": "completed", "activeForm": "Analyzing current multilingual architecture requirements"}, {"content": "Review pipeline config structure for language parameter", "status": "completed", "activeForm": "Reviewing pipeline config structure for language parameter"}, {"content": "Check generation.py for prompt modifications needed", "status": "completed", "activeForm": "Checking generation.py for prompt modifications needed"}, {"content": "Check semantic_clustering.py for language-dependent content", "status": "completed", "activeForm": "Checking semantic_clustering.py for language-dependent content"}, {"content": "Check markdown_generation.py for language settings", "status": "completed", "activeForm": "Checking markdown_generation.py for language settings"}, {"content": "Write multilingual implementation plan", "status": "completed", "activeForm": "Writing multilingual implementation plan"}]