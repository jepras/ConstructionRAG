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

### **06_store - ✅ IMPLEMENTED**

**Comprehensive ChromaDB storage with integrated validation and Danish semantic search testing.**

#### **Implementation**
- **Notebook**: `store_and_validate.py` 
- **Technology**: ChromaDB with persistent storage
- **Input**: Step 05 embedded chunks (auto-detects latest or specify run)
- **Output**: Persistent vector database + validation reports

#### **Key Features**
- **Automatic metadata flattening** for ChromaDB compatibility
- **Batch processing** with configurable batch sizes
- **Integrated validation** across storage, search, and retrieval quality
- **Danish semantic search testing** with construction-specific queries

#### **Configuration**
```python
SPECIFIC_EMBEDDING_RUN = ""  # Auto-detect latest or specify: "05_voyage_run_20250723_074238"
CHROMA_PERSIST_DIRECTORY = "../../chroma_db"
COLLECTION_NAME = "construction_documents"
EMBEDDING_DIMENSION = 1024  # Voyage multilingual-2
```

#### **Validation Tests**
1. **Storage Integrity**: Document count, metadata indexing, embedding dimensions
2. **Search Performance**: 16 bilingual queries (Danish/English) with response time < 500ms
3. **Metadata Filtering**: Source filename and element category filtering
4. **Retrieval Quality**: Danish construction queries ("regnvand", "omkostninger", "projekt information")

#### **Validation Results** 
✅ **Production Ready**: Average similarity -0.289, excellent Danish semantic search  
✅ **Performance**: Sub-millisecond response times  
✅ **Quality**: Clear ranking differentiation (0.2-0.6 similarity range)

#### **Output Files**
- `storage_validation_report.json` - Overall validation summary
- `retrieval_quality_report.json` - Detailed Danish semantic search analysis

### **07_query - ✅ IMPLEMENTED**

**Danish Query Processing with Query Variations and Collection Management**

#### **Implementation**
- **Notebook**: `query_processing.py`
- **Technology**: OpenAI GPT-3.5-turbo for query expansion, Voyage AI for embeddings
- **Input**: ChromaDB collection (configurable via `COLLECTION_TO_TEST`)
- **Output**: Query performance analysis + HTML reports

#### **Key Features**
- **Query Variations**: Original, semantic expansion, HyDE document, formal variation
- **Collection Management**: Easy switching between timestamped collections
- **Performance Testing**: Compare all variations on Danish construction queries
- **Content Snippets**: 120-character snippets in HTML output for better visibility

#### **Collection Selection**
```python
# --- Collection Selection ---
COLLECTION_TO_TEST = "construction_documents_20250723_113112"  # Latest timestamped
# COLLECTION_TO_TEST = "construction_documents"  # Original collection
```

#### **Query Variations Generated**
1. **Original Query**: Direct user input
2. **Semantic Expansion**: 4 Danish alternatives using GPT-3.5-turbo
3. **HyDE Document**: Hypothetical Danish document excerpt for better embedding matching
4. **Formal Variation**: Professional construction language variation

#### **Test Queries Used**
- "regnvand" (rainwater)
- "omkostninger for opmåling og beregning" (costs for surveying and calculation)
- "projekt information" (project information)

#### **Performance Results**
- **Best Technique**: HyDE Document (won 2/3 queries)
- **Average Similarity**: -0.033 to 0.032 (excellent performance)
- **Danish Recognition**: Excellent semantic search working very well

#### **Output Files**
- `query_performance_reports.json` - Individual query analysis
- `overall_performance_report.json` - Summary across all queries
- `query_variations_table.html` - Visual comparison table

#### **Key Insights for Step 8**
- **HyDE technique most effective** for Danish construction queries
- **Semantic expansion** provides good alternatives
- **Collection switching** works seamlessly with timestamped collections
- **No content categorization needed** - removed for simplicity and performance

### **08_retrieve - Hybrid Search Testing & Optimization**

#### **Implementation Strategy**
- **Notebook**: `retrieve_hybrid.py`
- **Technology**: ChromaDB semantic search + keyword search (BM25/TF-IDF)
- **Input**: Processed queries from step 07 + ChromaDB collection
- **Output**: HTML matrix showing optimal query + search combinations

#### **Testing Strategy**
- **Query Variations**: Test all 4 variations from step 7 (original, semantic expansion, HyDE, formal)
- **Search Methods**: Test semantic-only, keyword-only, and hybrid combinations
- **Weight Combinations**: Test different semantic/keyword weight ratios (100/0, 80/20, 60/40, 40/60, 20/80, 0/100)
- **Early Insight**: Step 7 showed HyDE performed well, but test all combinations systematically

#### **Search Strategy**
- **Semantic Search**: Voyage embeddings for conceptual matching
- **Keyword Search**: BM25/TF-IDF for exact term matching
- **Hybrid Fusion**: Weighted combination with configurable ratios
- **Rich Results**: Retrieve 20-30 results per combination (will be reranked in step 9)

#### **HTML Matrix Output**
```python
class RetrievalMatrixResult(BaseModel):
    query_variation: str  # "original", "semantic_expansion", "hyde", "formal"
    search_method: str    # "semantic_only", "keyword_only", "hybrid_80_20", etc.
    semantic_weight: float
    keyword_weight: float
    top_3_similarities: List[float]
    avg_top_3_similarity: float
    result_count: int
    top_content_snippets: List[str]  # 120-char snippets for visibility
    performance_rank: int  # Rank among all combinations
```

#### **Matrix Visualization**
Generate HTML table showing:
- **Rows**: Query variations (original, semantic expansion, HyDE, formal)
- **Columns**: Search methods (semantic-only, keyword-only, hybrid weights)
- **Cells**: Average top-3 similarity scores + color coding
- **Winner Highlighting**: Best performing combination clearly marked

#### **Configuration**
```python
# --- Collection Selection ---
COLLECTION_TO_TEST = "construction_documents_20250723_113112"  # From step 7

# --- Testing Configuration ---
TOP_K_RESULTS = 25  # Retrieve more results for step 9 reranking
TEST_QUERIES = ["regnvand", "omkostninger for opmåling og beregning", "projekt information"]
WEIGHT_COMBINATIONS = [
    (1.0, 0.0),  # Semantic only
    (0.8, 0.2),  # 80% semantic, 20% keyword
    (0.6, 0.4),  # 60% semantic, 40% keyword
    (0.4, 0.6),  # 40% semantic, 60% keyword
    (0.2, 0.8),  # 20% semantic, 80% keyword
    (0.0, 1.0),  # Keyword only
]
```

#### **Key Requirements**
- **Comprehensive Testing**: Don't assume HyDE is best - test all combinations
- **Rich Output**: Include 20-30 results per combination (not just top 3)
- **Visual Analysis**: HTML matrix makes it easy to spot optimal combinations
- **Step 9 Preparation**: Output format ready for reranking pipeline

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
1. **06_store**: ✅ `store_and_validate.py` - Chroma storage + integrated validation
2. **07_query**: ✅ `query_processing.py` - Query variations + collection management
3. **08_retrieve**: `retrieve_hybrid.py` - Hybrid search + metadata filtering (NEXT)
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