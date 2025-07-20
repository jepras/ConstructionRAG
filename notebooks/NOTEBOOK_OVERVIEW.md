# ConstructionRAG Notebook Overview

## System Architecture

```mermaid
graph TB
    subgraph "Input Layer"
        A[PDF Documents] --> B[Unstructured PDF Parser]
    end
    
    subgraph "Processing Pipeline"
        B --> C[Element Categorization]
        C --> D[Text Processing]
        C --> E[Table Processing]
        C --> F[Image Detection]
        
        D --> G[Text Chunking]
        E --> H[Table HTML]
        F --> I[Image Metadata]
    end
    
    subgraph "AI Services"
        J[OpenAI Embeddings] --> K[Vector Generation]
        L[OpenRouter VLM] --> M[Image Captioning]
    end
    
    subgraph "Storage Layer"
        N[ChromaDB Collection] --> O[Vector Database]
    end
    
    G --> K
    H --> K
    I --> M
    M --> K
    K --> O
```

## Data Flow

```mermaid
flowchart TD
    A[Start: Load Configuration] --> B[Initialize Clients]
    B --> C[Clear & Create ChromaDB Collection]
    C --> D[Partition PDF with Unstructured]
    
    D --> E[Count Elements by Category]
    E --> F{Element Type?}
    
    F -->|Text| G[Split into Chunks]
    F -->|Table| H[Extract HTML]
    F -->|Image| I[Skip Processing]
    
    G --> J[Generate Embeddings]
    H --> J
    I --> K[Store Metadata Only]
    
    J --> L[Store in ChromaDB]
    K --> L
    
    L --> M[Query Verification]
    M --> N[End]
```

## Element Processing Logic

```mermaid
graph LR
    subgraph "PDF Elements"
        A[Text Elements] --> B[RecursiveCharacterTextSplitter]
        C[Table Elements] --> D[HTML Extraction]
        E[Image Elements] --> F[Skip VLM Processing]
    end
    
    subgraph "Processing"
        B --> G[1000 char chunks<br/>200 char overlap]
        D --> H[Table HTML format]
        F --> I[Image metadata only]
    end
    
    subgraph "Output"
        G --> J[Text Chunks]
        H --> K[Table HTML]
        I --> L[Image Placeholders]
    end
```

## Configuration & Models

```mermaid
graph TD
    subgraph "Embedding Model"
        A[text-embedding-ada-002] --> B[1536 dimensions]
    end
    
    subgraph "VLM Model (Disabled)"
        C[anthropic/claude-3-5-sonnet] --> D[Vision capabilities]
    end
    
    subgraph "Database"
        E[ChromaDB Persistent] --> F[project_docs collection]
    end
    
    subgraph "PDF Processing"
        G[Unstructured hi_res] --> H[OCR: eng, dan]
    end
```

## Data Structure

```mermaid
erDiagram
    RichMetadata {
        string source_filename
        string source_document_type
        int page_number
        string content_type
    }
    
    StructuredData {
        string content
        RichMetadata metadata
    }
    
    ChromaDBCollection {
        string id
        vector embedding
        string document
        RichMetadata metadata
    }
    
    StructuredData ||--|| RichMetadata : contains
    StructuredData ||--|| ChromaDBCollection : stored_as
```

## How the Notebook Works

### 1. **Initialization Phase**
- Loads environment variables (API keys)
- Defines Pydantic models for structured metadata
- Initializes OpenAI embedding client
- Creates/clears ChromaDB collection to avoid dimension mismatches
- Verifies embedding model produces correct dimensions (1536)

### 2. **PDF Processing Phase**
- Uses Unstructured library with `hi_res` strategy
- Extracts text, tables, and images from PDF
- Counts elements by category for transparency
- Processes documents in Danish and English (OCR)

### 3. **Element Categorization**
- **Text Elements**: Split into 1000-character chunks with 200-character overlap
- **Table Elements**: Converted to HTML format for structured storage
- **Image Elements**: Currently skipped (VLM processing disabled)

### 4. **Embedding Generation**
- Uses OpenAI's `text-embedding-ada-002` model
- Generates 1536-dimensional vectors for all text content
- Ensures consistency between storage and query embeddings

### 5. **Database Storage**
- Stores in ChromaDB with rich metadata
- Each entry includes: content, embedding, source file, page number, content type
- Uses UUIDs for unique identification

### 6. **Verification Phase**
- Performs test query using explicit embedding generation
- Demonstrates retrieval with distance scores
- Validates end-to-end pipeline functionality

## Key Features

### ✅ **Working Components**
- PDF parsing with Unstructured
- Text and table extraction
- Element categorization and counting
- Embedding generation with OpenAI
- ChromaDB storage and retrieval
- Explicit embedding consistency for queries

### ⏸️ **Disabled Components**
- VLM image captioning (commented out with `'''`)
- VLM test functionality (commented out with `'''`)

### 📊 **Output Metrics**
- Total elements found
- Breakdown by category (Text, Image, Table)
- Image count for future VLM processing
- Embedding dimensions verification
- Query results with distances

## Technical Details

### **Embedding Consistency Fix**
The notebook solves the common ChromaDB dimension mismatch issue by:
1. Explicitly generating query embeddings using the same model
2. Using `query_embeddings` parameter instead of `query_texts`
3. Ensuring the same `text-embedding-ada-002` model is used throughout

### **Error Handling**
- Graceful handling of missing image files
- Collection recreation to avoid dimension conflicts
- Comprehensive logging for debugging

### **Scalability Considerations**
- Modular design allows easy re-enabling of VLM features
- Configurable chunk sizes and overlap
- Support for multiple document types and languages

## Usage Instructions

1. **Setup**: Ensure `.env` file contains `OPENAI_API_KEY` and `OPENROUTER_API_KEY`
2. **Run**: Execute the notebook cells in order
3. **Monitor**: Watch the category breakdown and embedding verification
4. **Query**: Test retrieval with the verification query
5. **Extend**: Uncomment VLM sections when ready to process images

## Future Enhancements

- Re-enable VLM image captioning
- Add support for multiple PDF files
- Implement semantic search capabilities
- Add document similarity analysis
- Create web interface for querying

---

*This notebook provides a complete RAG pipeline for construction documents, with the ability to easily re-enable image processing when VLM services are properly configured.* 