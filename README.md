# ConstructionRAG

A **Multimodal Agentic RAG (Retrieval-Augmented Generation)** system designed for intelligent analysis of complex construction project documents. This system can process PDFs containing text, tables, and blueprints, allowing users to interact with the content through semantic search and chat interfaces.

## 🏗️ Project Overview

ConstructionRAG intelligently parses construction documents and enables natural language querying of technical content including:
- Technical specifications and text
- Data tables and structured information  
- Blueprint images and diagrams
- Construction drawings and schematics

The system uses a sophisticated pipeline to extract, process, and store multimodal content in a searchable vector database.

## 🚀 Quick Start

### Prerequisites

- **Python 3.12** (recommended)
- **Git** for version control
- **API Keys** for:
  - OpenAI (for embeddings and language models)
  - OpenRouter (for alternative LLM access)

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd ConstructionRAG
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install python-dotenv
pip install unstructured[pdf]
pip install langchain
pip install langchain-openai
pip install chromadb
pip install openai
pip install pydantic
pip install pdf2image
pip install PyMuPDF
pip install Pillow
```

**Additional system dependencies** (for PDF processing):
```bash
# On macOS:
brew install poppler

# On Ubuntu/Debian:
sudo apt-get install poppler-utils

# On Windows:
# Download poppler binaries and add to PATH
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# OpenRouter API Configuration  
OPENROUTER_API_KEY=your_openrouter_api_key_here

# LangSmith Configuration (optional, for tracing)
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=ConstructionRAG
```

### 5. Add Your PDF Documents

Place your construction PDF documents in:
```
data/external/construction_pdfs/
```

The system currently includes sample documents:
- `sample_document.pdf`
- `test-with-variety.pdf`
- `test-with-little-variety.pdf`

## 📋 Usage Guide

### Processing Pipeline

The ConstructionRAG system follows a three-stage processing pipeline:

#### Stage 1: Document Partitioning
```bash
# Navigate to the partition notebook
cd notebooks/01_partition/

# Run the partitioning script
python partition_pdf.py
```

**What it does:**
- Extracts text, tables, and images from PDF documents
- Uses Unstructured library with high-resolution OCR
- Categorizes elements by type (text, table, image)
- Saves partitioned data to `data/internal/01_partition_data/`

#### Stage 2: Metadata Enhancement  
```bash
# Navigate to metadata notebook
cd notebooks/02_meta_data/

# Run metadata extraction
python meta_data.py
```

**What it does:**
- Adds rich metadata to partitioned elements
- Analyzes document structure and relationships
- Exports analysis to CSV for inspection
- Saves enhanced data to `data/internal/02_meta_data/`

#### Stage 3: Data Enrichment
```bash
# Navigate to enrichment notebook  
cd notebooks/03_enrich_data/

# Run data enrichment
python enrich_data.py
```

**What it does:**
- Generates embeddings using OpenAI's text-embedding-ada-002
- Processes images with Vision Language Models (VLM) when enabled
- Stores vectorized content in ChromaDB
- Saves final enriched data to `data/internal/03_enrich_data/`

### Alternative: All-in-One Processing

For rapid processing, you can also use the comprehensive pipeline:

```bash
cd notebooks/pdf_analysis/
python claude_ingest_pipeline.py
```

## 🗂️ Project Structure

```
ConstructionRAG/
├── data/
│   ├── external/construction_pdfs/     # Input PDF documents
│   └── internal/                       # Processed data by stage
│       ├── 01_partition_data/         # Raw partitioned elements
│       ├── 02_meta_data/              # Enhanced metadata
│       └── 03_enrich_data/            # Final vectorized data
├── notebooks/                          # Processing notebooks
│   ├── 01_partition/                  # PDF partitioning
│   ├── 02_meta_data/                  # Metadata enhancement
│   ├── 03_enrich_data/                # Data enrichment & embedding
│   └── pdf_analysis/                  # All-in-one processing
├── chroma_db/                          # Vector database storage
├── own/                               # Project documentation
│   ├── PROJECT_OVERVIEW.md           # Detailed project architecture
│   ├── HOW_TO_RUN.md                 # Execution guide
│   └── LEARNINGS.md                  # Development insights
└── venv/                              # Python virtual environment
```

## 🔍 Querying the System

Once your documents are processed, you can query the vector database:

```python
import chromadb
from langchain_openai import OpenAIEmbeddings

# Initialize ChromaDB client
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("project_docs")

# Initialize embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

# Query the system
query = "What are the safety requirements for this construction project?"
query_embedding = embeddings.embed_query(query)

# Retrieve relevant documents
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5
)

# Display results
for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
    print(f"Source: {metadata['source_filename']}, Page: {metadata['page_number']}")
    print(f"Content: {doc[:200]}...\n")
```

## 🛠️ Configuration

### Embedding Model Configuration
- **Default**: OpenAI `text-embedding-ada-002` (1536 dimensions)
- **Alternative**: Modify in scripts to use other embedding models

### PDF Processing Settings
- **OCR Languages**: English (`eng`) and Danish (`dan`)
- **Strategy**: High-resolution processing for maximum accuracy
- **Chunking**: 1000 character chunks with 200 character overlap

### Vector Database
- **Engine**: ChromaDB (persistent storage)
- **Collection**: `project_docs`
- **Storage**: Local `./chroma_db/` directory

## 🧪 Development & Testing

### Inspect Processing Results

```bash
# View metadata analysis
cat data/internal/02_meta_data/latest_run/sample_analysis.csv

# Check enriched elements (use JSON beautifier for readability)
cat data/internal/03_enrich_data/latest_run/enriched_elements.json
```

### Debugging Tools

1. **LangSmith Integration**: Enable tracing for detailed pipeline monitoring
2. **Element Counting**: Each stage reports processing statistics
3. **Visual Verification**: Check extracted images in `figures/` directories

## ⚠️ Troubleshooting

### Common Issues

**1. ChromaDB Dimension Mismatch**
```bash
# Clear and recreate collection
rm -rf chroma_db/
# Re-run enrichment stage
```

**2. Missing API Keys**
```bash
# Verify .env file exists and contains valid keys
cat .env
```

**3. PDF Processing Errors**
```bash
# Ensure poppler is installed for PDF conversion
# macOS: brew install poppler
# Ubuntu: sudo apt-get install poppler-utils
```

**4. Python Package Issues**
```bash
# Reinstall requirements
pip install --force-reinstall unstructured[pdf]
```

## 🔮 Future Enhancements

- **Web Interface**: Chat-based querying interface
- **Multi-document Support**: Hierarchical RAG for document collections
- **Advanced VLM**: Enhanced image and blueprint analysis
- **Deployment**: Containerized FastAPI application for Railway deployment

## 📚 Additional Resources

- [`own/PROJECT_OVERVIEW.md`](own/PROJECT_OVERVIEW.md) - Detailed system architecture
- [`notebooks/NOTEBOOK_OVERVIEW.md`](notebooks/NOTEBOOK_OVERVIEW.md) - Technical pipeline documentation
- [`own/HOW_TO_RUN.md`](own/HOW_TO_RUN.md) - Execution workflow guide

## 🤝 Contributing

1. Ensure your local branch is up to date
2. Follow the three-stage processing pipeline for testing
3. Update documentation for any architectural changes
4. Test with sample construction documents before committing

---

**Note**: This system is designed for complex construction documents with multimodal content. For simple text-only PDFs, consider using a standard RAG implementation for better performance.
