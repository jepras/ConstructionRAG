# RAG Pipeline Design Document
## Remaining Implementation Steps & Design Decisions

---

## 📋 **Current Pipeline Status**

### ✅ **Completed Steps (1-5)**
- **01_partition**: Document partitioning with vision processing
- **02_meta_data**: Rich metadata extraction and enhancement  
- **03_enrich_data**: Data enrichment from metadata
- **04_chunk**: Intelligent chunking with adaptive strategies
- **05_embed**: Vector embeddings with Voyage AI

### 🔄 **Remaining Steps (6-12)**
- **06_store**: Vector storage with Chroma + metadata indexing + validation
- **07_query**: Query processing and expansion (no intent detection)
- **08_retrieve**: Hybrid search (semantic + keyword) with metadata filtering
- **09_rerank**: Re-ranking retrieved results for relevance optimization
- **10_context**: Context assembly and prompt engineering
- **11_generate**: LLM response generation with OpenAI
- **12_evaluate**: Evaluation framework and metrics

---

## 🏗️ **Notebook Structure Guidelines**

### **Standard Notebook Template Structure**

Based on analysis of existing notebooks (`chunking_stripped.py`, `embed_voyage.py`, `meta_data_unified.py`):

```python
# ==============================================================================
# [NOTEBOOK TITLE] - [BRIEF DESCRIPTION]
# [Purpose and context description]
# ==============================================================================

import os
import sys
import pickle
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# --- External Libraries ---
# (Import third-party libraries here)

# --- Environment Variables ---
# (Load API keys, environment configs)

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

# --- Input Data Configuration ---
PREVIOUS_STEP_RUN = "XX_run_YYYYMMDD_HHMMSS"  # Which previous run to load

# --- Model/Service Configuration ---
# (API keys, model names, parameters)

# --- Path Configuration ---
INPUT_BASE_DIR = "../../data/internal/XX_previous_step"
OUTPUT_BASE_DIR = "../../data/internal/XX_current_step"

# --- Create timestamped output directory ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CURRENT_RUN_DIR = Path(OUTPUT_BASE_DIR) / f"XX_run_{timestamp}"
CURRENT_RUN_DIR.mkdir(parents=True, exist_ok=True)

# --- Processing Configuration ---
# (Load from config file or define parameters)

# ==============================================================================
# 2. DATA MODELS
# ==============================================================================

# (Pydantic models for type safety)

# ==============================================================================
# 3. CORE FUNCTIONS
# ==============================================================================

# (Main processing logic)

# ==============================================================================
# 4. MAIN EXECUTION
# ==============================================================================
```

### **Directory Structure Pattern**
```
notebooks/XX_step_name/
├── main_processing_script.py        # Core implementation
├── config/
│   └── step_config.json            # Configuration parameters
├── data/                            # Local test data (if needed)
├── README.md                        # Step-specific documentation
└── [ANALYSIS].md                    # Analysis and findings (optional)
```

### **Data Flow Pattern**
```
data/internal/
├── 01_partition_data/
├── 02_meta_data/
├── 03_enrich_data/
├── 04_chunking/
│   ├── 04_run_20250722_134606/      # Timestamped runs
│   └── 04_run_20250722_134421/
├── 05_embedding/
│   ├── 05_voyage_run_20250723_074238/
│   └── 05_run_20250723_075021/
└── [06-12]_[step_name]/
    └── [XX]_run_[timestamp]/
```

---

## 🎯 **Design Decisions for Remaining Steps**

### **06_store - Vector Storage & Indexing**

#### **Technology Stack**
- **Vector DB**: Chroma (as requested)
- **Storage Strategy**: Persistent local storage with collections
- **Metadata Indexing**: Full metadata preserved for filtering

#### **Implementation Approach**
- **Collection Strategy**: Single collection with rich metadata filtering
- **Document Storage**: Store original chunks + embeddings + full metadata
- **Indexing**: Create indexes on key metadata fields for fast filtering

#### **Collection Strategy for Multiple Project Documents**

**Option A: Single Collection (Recommended)**
- **Pros**: Cross-document search, unified metadata filtering, simpler management
- **Cons**: Larger collection size, potential slower specific document queries
- **Best for**: 20-50 documents per project, cross-document research queries

**Recommended Approach**: Single collection with project-level metadata filtering

#### **Key Configuration Variables**
```python
# Chroma Configuration
CHROMA_PERSIST_DIRECTORY = "../../chroma_db"
COLLECTION_NAME = "construction_documents"  # Single collection for all project docs
EMBEDDING_DIMENSION = 1024  # Voyage multilingual-2

# Project Organization Strategy
PROJECT_METADATA_FIELDS = [
    "project_id",           # Unique project identifier
    "project_name",         # Human-readable project name
    "document_category",    # "building_code", "specification", "regulation", "standard"
    "document_authority",   # "municipal", "national", "international", "private"
]

# Flattened Metadata Strategy (Chroma limitation)
FLATTENED_METADATA_FIELDS = [
    "source_filename", "page_number", "element_category",
    "section_title_inherited", "text_complexity", "processing_strategy",
    "project_id", "document_category", "has_numbers", "has_tables_on_page",
    "content_length", "page_context"
]
```

#### **Nested Data Handling Strategy**

**Chroma Limitation**: Only supports flat dictionaries for metadata (no nested objects)

**Solution**: Flatten complex metadata during storage
```python
# Original nested structure
original_metadata = {
    "source_filename": "building_code_2023.pdf",
    "structural": {
        "section_title": "Foundation Requirements", 
        "complexity": "complex"
    },
    "processing": {
        "strategy": "unified_fast_vision",
        "confidence": 0.95
    }
}

# Flattened for Chroma
flattened_metadata = {
    "source_filename": "building_code_2023.pdf",
    "structural_section_title": "Foundation Requirements",
    "structural_complexity": "complex", 
    "processing_strategy": "unified_fast_vision",
    "processing_confidence": 0.95
}
```

#### **Data Conversion Strategy**
```python
class ChromaDocument(BaseModel):
    id: str                    # chunk_id from embedding data
    content: str              # chunk content
    embedding: List[float]    # voyage embedding vector
    metadata: Dict[str, Any]  # flattened metadata only
    
def convert_embedded_chunks_to_chroma(embedded_chunks_file: str) -> List[ChromaDocument]:
    """Convert our rich embedded chunks to Chroma-compatible format"""
    # Load embedded chunks with rich metadata
    # Flatten nested metadata structures  
    # Create ChromaDocument objects
    # Return list ready for Chroma storage
```

#### **Integrated Storage Validation**

**Storage verification happens automatically after storage completion:**

- **Chunk Count Validation**: Verify all chunks from embedding step were stored
- **Metadata Integrity**: Check flattened metadata fields are correctly indexed
- **Embedding Quality**: Validate embedding vectors are properly stored
- **Collection Health**: Verify Chroma collection structure and persistence

#### **Basic Search Testing**
- **Semantic Search**: Test basic similarity queries with known documents
- **Metadata Filtering**: Verify filtering by source_filename, page_number, etc.
- **Performance Benchmarking**: Measure query response times with sample data
- **Error Handling**: Test edge cases and malformed queries

#### **Test Query Suite**
```python
VALIDATION_QUERIES = [
    # Basic semantic search
    "foundation requirements",
    "fundament krav",  # Danish equivalent
    
    # Metadata filtering tests  
    {"query": "insulation", "filter": {"source_filename": "building_code_2023.pdf"}},
    {"query": "structural", "filter": {"element_category": "NarrativeText"}},
    
    # Performance tests
    {"query": "renovation", "top_k": 100},  # Large result set
]
```

#### **Validation Output**
```python
class StorageValidationReport(BaseModel):
    total_chunks_stored: int
    chunks_with_embeddings: int
    metadata_fields_indexed: List[str]
    search_performance_ms: Dict[str, float]
    failed_queries: List[str]
    validation_passed: bool
    storage_timestamp: str
    validation_timestamp: str
```

### **07_query - Language-Agnostic Query Processing**

#### **LLM-Based Semantic Query Expansion**
```python
def expand_query_semantically(original_query: str) -> List[str]:
    """Generate semantic variations using GPT without hardcoded terms"""
    
    prompt = f"""
    Given this construction/tender query: "{original_query}"
    
    Generate 4 semantically similar queries that could find the same information.
    Consider:
    - Alternative technical terminology
    - Different phrasing styles (formal/informal)  
    - Related concepts that might contain the answer
    - Broader and narrower interpretations
    
    Return only the alternative queries, one per line.
    """
    
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    return [q.strip() for q in response.choices[0].message.content.strip().split('\n') if q.strip()]
```

#### **Metadata-Driven Query Routing**
```python
def route_query_by_content_type(query: str) -> Dict[str, Any]:
    """Route queries based on semantic content, not language"""
    
    type_prompt = f"""
    Classify this query into one category:
    - quantities (amounts, numbers, measurements, dimensions)
    - requirements (specifications, standards, compliance, regulations)
    - procedures (processes, steps, methods, instructions)
    - materials (substances, components, products, equipment)
    - timeline (deadlines, schedules, durations, phases)
    
    Query: "{query}"
    Return only the category name.
    """
    
    category = get_category_from_llm(type_prompt)
    
    # Content-based metadata filtering (language-agnostic)
    routing_config = {
        "quantities": {
            "metadata_filter": {"has_numbers": True},
            "boost_fields": ["content_length"],
            "search_weight": "precise"
        },
        "requirements": {
            "metadata_filter": {"element_category": {"$in": ["NarrativeText", "Title"]}},
            "boost_fields": ["section_title_inherited"],
            "search_weight": "comprehensive"
        },
        "procedures": {
            "metadata_filter": {"text_complexity": {"$in": ["medium", "complex"]}},
            "boost_fields": ["element_category"],
            "search_weight": "sequential"
        },
        "materials": {
            "metadata_filter": {"has_tables_on_page": True},
            "boost_fields": ["page_context"],
            "search_weight": "specific"
        },
        "timeline": {
            "metadata_filter": {"has_numbers": True, "element_category": "NarrativeText"},
            "boost_fields": ["content_length"],
            "search_weight": "contextual"
        }
    }
    
    return routing_config.get(category, routing_config["requirements"])
```

#### **Hypothetical Document Embeddings (HyDE)**
```python
def generate_hypothetical_document(query: str) -> str:
    """Generate hypothetical answer document for better embedding matching"""
    
    hyde_prompt = f"""
    Given this construction query: "{query}"
    
    Write a detailed, technical paragraph that would likely contain the answer.
    Write as if you're from an official construction document or building code.
    Include specific details, measurements, and technical language that would appear in real documents.
    
    Query: {query}
    
    Hypothetical document excerpt:
    """
    
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": hyde_prompt}],
        temperature=0.2  # Lower temperature for more consistent technical content
    )
    
    return response.choices[0].message.content.strip()

def create_hyde_embeddings(query: str, hypothetical_doc: str) -> Dict[str, Any]:
    """Create embeddings for both query and hypothetical document"""
    
    # Embed both the original query and hypothetical document
    voyage_client = VoyageClient(api_key=os.getenv("VOYAGE_API_KEY"))
    
    embeddings = voyage_client.embed([query, hypothetical_doc], model="voyage-multilingual-2")
    
    return {
        "query_embedding": embeddings.embeddings[0],
        "hyde_embedding": embeddings.embeddings[1],
        "hypothetical_document": hypothetical_doc
    }
```

#### **Query Processing Pipeline**
```python
class ProcessedQuery(BaseModel):
    original_query: str
    expanded_queries: List[str]                    # LLM-generated variations
    content_category: str                          # quantities/requirements/etc
    routing_config: Dict[str, Any]                 # metadata filters and weights
    hypothetical_document: Optional[str] = None    # HyDE document
    hyde_embedding: Optional[List[float]] = None   # HyDE embedding
    processing_time_ms: float
```

### **08_retrieve - Hybrid Search Implementation**

#### **Search Strategy**
- **Semantic Search**: Voyage embeddings for conceptual matching
- **Keyword Search**: BM25/TF-IDF for exact term matching  
- **Metadata Filtering**: Pre-filter by document type, complexity, source
- **Result Fusion**: Combine semantic + keyword results with weighted scoring

#### **Rich Metadata Leveraging**
- **Citation Generation**: Use `source_filename`, `page_number`, `section_title_inherited`
- **Content Type Filtering**: Filter by `element_category` (tables vs. narrative)
- **Complexity Matching**: Match query complexity to `text_complexity`
- **Quality Weighting**: Weight by `processing_strategy` confidence

#### **Retrieval Output Format**
```python
class RetrievalResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    citation: Dict[str, str]  # Document, page, section references
    search_type: str  # "semantic", "keyword", "hybrid"
```

### **09_rerank - Re-ranking Implementation**

#### **What Re-ranking Provides**
- **Query-Context Understanding**: Cross-encoder models process query + chunk together
- **Domain Relevance**: Construction-specific relevance beyond pure similarity
- **Quality Optimization**: Prioritize authoritative sources and clear content

#### **Implementation Strategy**
- **Model**: `ms-marco-MiniLM-L-6-v2` or `bge-reranker-base`
- **Input**: Top K results from hybrid search (e.g., top 20)
- **Output**: Re-ranked top N results (e.g., top 5-10)
- **Metadata Integration**: Boost official documents, recent content

#### **Value Demonstration Output**
```python
class RerankingAnalysis(BaseModel):
    original_ranking: List[RetrievalResult]
    reranked_results: List[RetrievalResult]
    ranking_changes: Dict[str, Any]  # Show position changes
    confidence_scores: List[float]   # Re-ranking confidence
```

### **10_context - Context Assembly & Prompt Engineering**

#### **Context Strategy**
- **Token Management**: Respect OpenAI context limits (4K/8K/32K based on model)
- **Source Attribution**: Include document references in context
- **Metadata Enhancement**: Use metadata to enrich context understanding

#### **Prompt Template Structure**
```python
SYSTEM_PROMPT = """
You are a construction industry expert assistant helping with tender bidding.
Use the provided documents to answer questions accurately and cite your sources.

When answering:
1. Provide specific, actionable information
2. Always cite document sources, pages, and sections
3. Highlight regulatory requirements vs. recommendations
4. Note any regional or temporal limitations
"""

CONTEXT_TEMPLATE = """
Relevant Documents:
{context_with_citations}

Question: {query}

Answer based on the provided documents, including specific citations:
"""
```

### **11_generate - LLM Response Generation**

#### **Model Configuration**
- **Primary Model**: OpenAI GPT-4 or GPT-3.5-turbo
- **Response Format**: Structured with citations
- **Temperature**: Low (0.1-0.3) for factual accuracy

#### **Response Enhancement**
- **Citation Integration**: Automatic source referencing
- **Confidence Indicators**: Mark uncertain information
- **Follow-up Suggestions**: Related queries for deeper exploration

### **12_evaluate - Evaluation Framework**

#### **Evaluation Dataset Creation**
1. **Historical Queries**: Real client questions from tender preparation
2. **Synthetic Generation**: GPT-4 generated Q&A from documents
3. **Expert Validation**: Construction professional review
4. **Tender-Specific Scenarios**: Actual tender requirement questions

#### **Metrics for Tender Bidding Use Case**
- **Retrieval Metrics**:
  - Precision@K, Recall@K for document retrieval
  - Citation accuracy (correct page/section references)
  - Coverage (% of ground truth sources found)

- **Generation Metrics**:
  - Answer completeness vs. ground truth
  - Citation quality and accuracy
  - Regulatory compliance coverage

- **User Experience Metrics**:
  - Time to answer vs. manual search
  - Client satisfaction scores
  - Successful bid correlation (long-term)

---

## 📚 **Notebook Implementation Queue**

### **Immediate Priority (Core Functionality)**
1. **06_store**: `store_and_validate.py` - Set up Chroma storage + integrated validation
2. **07_query**: `query_processing.py` - Simple query expansion (no intent detection)
3. **08_retrieve**: `retrieve_hybrid.py` - Implement hybrid search + metadata filtering
4. **11_generate**: `generate_openai.py` - Basic OpenAI integration with citations

### **Enhancement Priority (Optimization)**
5. **09_rerank**: `rerank_analysis.py` - Re-ranking with value demonstration
6. **10_context**: `context_assembly.py` - Advanced prompt engineering
7. **12_evaluate**: `evaluate_pipeline.py` - Evaluation framework

### **Configuration Files Needed**
```
06_store/config/storage_config.json    # Includes validation settings
07_query/config/query_processing_config.json
08_retrieve/config/retrieval_config.json
09_rerank/config/reranking_config.json
10_context/config/prompt_templates.json
11_generate/config/generation_config.json
12_evaluate/config/evaluation_config.json
```

---

## **🛠️ Strategic Technology Stack**

### **🎯 LangChain Adoption Strategy**

```python
# Use LangChain only where it adds clear value
LANGCHAIN_COMPONENTS = [
    "08_retrieve",    # Hybrid search patterns
    "10_context",     # Prompt management  
    "12_evaluate"     # Evaluation framework
]

DIRECT_IMPLEMENTATION = [
    "06_store",       # Complex metadata needs direct control
    "07_query",       # Custom multilingual logic
    "09_rerank",      # Performance-critical
    "11_generate"     # Citation parsing needs custom logic
]

# Migration path: Later move more components to LangChain as needed
```

### **📚 Technology Stack by Component**

#### **06_store - Vector Storage + Validation (Direct Implementation)**
- **Primary**: `chromadb` - Direct client for complex metadata flattening
- **Data Models**: `pydantic` - Type safety and validation
- **Processing**: `json`, `pickle` - Loading embedded chunks
- **Testing**: `pytest` - Integrated validation testing
- **Performance**: `time` - Query response benchmarking
- **Reports**: `json` - Combined storage and validation report
- **Observability**: `langsmith` decorators for tracing
- **Why Direct**: Complex metadata flattening + performance-critical validation need precise control

#### **07_query - Language-Agnostic Processing (Direct Implementation)**
- **LLM**: `openai` - Direct API for GPT-3.5-turbo expansion & classification
- **Embeddings**: `voyageai` - For HyDE embedding generation
- **Environment**: `python-dotenv` - API key management
- **Observability**: `langsmith` decorators for tracing
- **Why Direct**: Custom multilingual logic and HyDE implementation

#### **08_retrieve - Hybrid Search (LangChain)**
- **Framework**: `langchain.retrievers` - EnsembleRetriever for hybrid search
- **Vector Search**: `langchain_chroma` - Chroma integration
- **Keyword Search**: `langchain_community.retrievers.BM25Retriever`
- **Result Fusion**: Built-in ensemble weighting
- **Why LangChain**: Proven hybrid retrieval patterns, excellent observability

#### **09_rerank - Result Optimization (Direct Implementation)**
- **Cross-Encoders**: `sentence-transformers` - Direct model access
- **Models**: `transformers` - HuggingFace model loading
- **Scoring**: `torch` - GPU-optimized model inference
- **Observability**: `langsmith` decorators for tracing
- **Why Direct**: Performance-critical, need GPU optimization control

#### **10_context - Prompt Assembly (LangChain)**
- **Framework**: `langchain.prompts` - ChatPromptTemplate management
- **Token Counting**: `tiktoken` - OpenAI token estimation
- **Template Engine**: Built-in Jinja2 support
- **Context Management**: Automatic context window handling
- **Why LangChain**: Excellent prompt management, template versioning

#### **11_generate - Response Generation (Direct Implementation)**
- **LLM**: `openai` - Direct API for GPT-4/GPT-3.5-turbo
- **Streaming**: `openai` streaming for real-time responses
- **Citation**: Custom citation parsing and formatting logic
- **Observability**: `langsmith` decorators for tracing
- **Why Direct**: Complex citation logic, custom response formatting

#### **12_evaluate - Performance Measurement (LangChain)**
- **Framework**: `langchain.evaluation` - Built-in evaluators
- **Metrics**: `ragas` - RAG evaluation framework integration
- **Datasets**: `langsmith` - Dataset management and versioning
- **Analysis**: `pandas` - Results analysis and reporting
- **Why LangChain**: Comprehensive evaluation ecosystem, dataset management

## **🔗 LangSmith Integration Strategy**

### **Universal Observability**
```python
from langsmith import traceable

# All components get LangSmith tracing regardless of implementation
@traceable
def custom_storage_function():
    # Direct implementation with full observability
    pass

@traceable  
def langchain_retrieval_function():
    # LangChain components get automatic tracing
    pass
```

### **Hybrid Benefits**
- **🔍 Full Observability**: LangSmith tracing across all components
- **🎛️ Control Where Needed**: Direct implementation for complex logic
- **🧩 LangChain Where Valuable**: Proven patterns for standard workflows
- **📈 Migration Path**: Gradual adoption as LangChain improves

### **📦 Core Dependencies**
```python
# LangChain (selective usage)
langchain>=0.1.0
langchain-openai
langchain-chroma
langchain-community

# LangSmith (universal observability)
langsmith

# Direct implementation dependencies
chromadb>=0.4.0           # Vector database
openai>=1.0.0             # LLM API
voyageai>=0.2.0           # Embeddings
sentence-transformers     # Re-ranking models

# Data & ML
pydantic>=2.0.0          # Type safety
numpy                    # Numerical operations
pandas                   # Data analysis
scikit-learn            # Keyword search (if not using LangChain BM25)

# Evaluation & Testing
ragas                   # RAG evaluation
pytest                 # Testing framework

# Utilities
python-dotenv          # Environment management
tiktoken              # Token counting
```

---

## 🎯 **Client-Specific Optimizations for Tender Bidding**

### **Domain Expertise Integration**
- **Regulatory Prioritization**: Weight official building codes higher
- **Geographic Filtering**: Filter by jurisdiction for local requirements
- **Project Type Matching**: Commercial vs. residential specific content
- **Temporal Relevance**: Prioritize current regulations and standards

### **Citation Excellence for Professional Use**
```python
class ProfessionalCitation(BaseModel):
    document_name: str
    section_title: str
    page_number: int
    regulatory_status: str  # "official", "guidance", "reference"
    last_updated: Optional[str]
    authority: str  # Building department, standards body, etc.
```

### **Efficiency Metrics**
- **Query Resolution Time**: Target <30 seconds for complex queries
- **Source Coverage**: Ensure comprehensive document coverage
- **Update Frequency**: Track when documents need refreshing
- **Client Success**: Measure bid win rates (long-term correlation)

---

## 🚀 **Next Steps**

1. **Start with 06_store**: Create Chroma storage foundation + integrated validation
2. **Add 07_query**: Implement simple query expansion 
3. **Implement 08_retrieve**: Get basic hybrid search working  
4. **Add 11_generate**: Complete end-to-end pipeline
5. **Optimize with 09_rerank**: Enhance result quality
6. **Refine with 10_context**: Polish prompt engineering
7. **Validate with 12_evaluate**: Measure and improve performance

The modular approach ensures each step can be developed and tested independently while maintaining the established patterns from your existing notebooks. 