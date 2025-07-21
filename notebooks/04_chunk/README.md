# Chunking Pipeline

## Overview

This notebook implements intelligent chunking with rich metadata preservation for construction documents. It is the final preprocessing stage before embedding and storing, and is now **separated from embedding and vector database storage**.

## Features

### 🧠 Intelligent Adaptive Chunking
- **Content-aware chunking**: Different chunk sizes based on text complexity
- **Construction-specific optimization**: Special handling for technical content
- **Section preservation**: Maintains document structure and relationships

### 📊 Rich Metadata Preservation
- **Complete context**: Preserves all metadata from previous pipeline stages
- **VLM integration**: Includes AI-generated captions and descriptions
- **Processing traceability**: Tracks chunking strategy and parameters

### 📝 List-Aware Grouping
- **Lists grouped with context**: List items are grouped with their preceding paragraph
- **Order preserved**: List order and context are maintained

### 🖼️ Table & Image Preservation
- **No chunking**: Tables and images are kept as single units with their VLM captions

## Outputs

- `chunked_elements_adaptive.json`: Chunks using adaptive strategy
- `chunked_elements_recursive.json`: Chunks using recursive strategy
- `chunking_analysis.json`: Chunking statistics and content distribution
- `sample_chunks_adaptive.json`: Sample chunks for inspection (adaptive)
- `sample_chunks_recursive.json`: Sample chunks for inspection (recursive)

## Chunking Analysis & Validation

- **Total chunks**
- **Average words/chars per chunk**
- **Content type distribution** (text, table, image, list)
- **List grouping accuracy**
- **Metadata preservation**
- **Sample chunk inspection**

## Usage

1. Ensure enriched elements are available at the expected input path.
2. Run `chunking.py` to generate chunked outputs and analysis.
3. Inspect the outputs and validation reports to verify chunking quality.
4. Use the outputs as input for the separate embedding and storage pipeline.

## Next Steps

- After chunking, proceed to embedding and storing using a dedicated notebook.
- Use the chunking analysis to select the best chunking strategy for your use case. 