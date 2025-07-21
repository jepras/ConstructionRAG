# ==============================================================================
# INTELLIGENT CHUNKING & EMBEDDING PIPELINE
# Advanced chunking with rich metadata before vector database storage
# Works with enriched elements from enrich_data_from_meta.py
# ==============================================================================

import os
import sys
import pickle
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# --- Environment & API ---
from dotenv import load_dotenv

# --- LangChain Components ---
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

# --- Vector Database ---
import chromadb
from chromadb.config import Settings

# --- Pydantic for Enhanced Metadata ---
from pydantic import BaseModel, Field
from typing import Literal

# ==============================================================================
# CONFIGURATION - ALL CONFIGURABLE VARIABLES
# ==============================================================================

# --- Data Source Configuration ---
ENRICH_DATA_RUN_TO_LOAD = (
    "03_run_20250721_100823"  # Change this to load different enrich_data runs
)

# --- Chunking Configuration ---
CHUNKING_STRATEGY = "adaptive"  # "adaptive", "fixed", "semantic"
BASE_CHUNK_SIZE = 1000
BASE_CHUNK_OVERLAP = 200

# Adaptive chunking parameters
ADAPTIVE_CHUNK_SIZES = {
    "simple": 1500,  # Simple text gets larger chunks
    "medium": 1000,  # Medium complexity gets standard chunks
    "complex": 600,  # Complex text gets smaller chunks
    "table": 800,  # Tables get medium chunks
    "image_page": 1200,  # Image pages get larger chunks
}

ADAPTIVE_CHUNK_OVERLAPS = {
    "simple": 100,
    "medium": 200,
    "complex": 300,
    "table": 150,
    "image_page": 250,
}

# --- Embedding Configuration ---
EMBEDDING_MODEL = "text-embedding-ada-002"
EMBEDDING_DIMENSIONS = 1536

# --- Vector Database Configuration ---
DB_PATH = "../../chroma_db"
COLLECTION_NAME = "construction_docs"
COLLECTION_DESCRIPTION = "Construction documents with rich metadata"

# --- Path Configuration ---
DATA_BASE_DIR = "../../data/internal"
ENRICH_DATA_DIR = f"{DATA_BASE_DIR}/03_enrich_data"
OUTPUT_BASE_DIR = f"{DATA_BASE_DIR}/04_chunk_and_embed"

# ==============================================================================
# 1. ENHANCED CHUNK METADATA MODELS
# ==============================================================================


class ChunkMetadata(BaseModel):
    """Rich metadata for each chunk with construction-specific fields"""

    # Core chunk identification
    chunk_id: str
    source_element_id: str
    chunk_index: int  # Position within element
    total_chunks_in_element: int

    # Source document info
    source_filename: str
    page_number: int
    content_type: Literal["text", "table", "full_page_with_images"]

    # Structural metadata (inherited from previous stages)
    page_context: str = "unknown"
    content_length: int = 0
    has_numbers: bool = False
    element_category: str = "unknown"
    has_tables_on_page: bool = False
    has_images_on_page: bool = False
    text_complexity: str = "medium"
    section_title_category: Optional[str] = None
    section_title_inherited: Optional[str] = None
    section_title_pattern: Optional[str] = None

    # VLM enrichment metadata (if applicable)
    vlm_processed: bool = False
    table_html_caption: Optional[str] = None
    table_image_caption: Optional[str] = None
    full_page_image_caption: Optional[str] = None
    page_text_context: Optional[str] = None

    # Chunking metadata
    chunking_strategy: str = "adaptive"
    chunk_size: int = BASE_CHUNK_SIZE
    chunk_overlap: int = BASE_CHUNK_OVERLAP
    chunk_word_count: int = 0
    chunk_character_count: int = 0

    # Processing metadata
    processing_timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )
    pipeline_stage: str = "chunk_and_embed"


class ChunkedElement(BaseModel):
    """A chunked element ready for embedding"""

    chunk_id: str
    content: str
    metadata: ChunkMetadata


# ==============================================================================
# 2. INTELLIGENT CHUNKING STRATEGIES
# ==============================================================================


class AdaptiveChunker:
    """Intelligent chunking based on content characteristics"""

    def __init__(self, strategy: str = "adaptive"):
        self.strategy = strategy
        self.splitters = self._initialize_splitters()

    def _initialize_splitters(self) -> Dict[str, RecursiveCharacterTextSplitter]:
        """Initialize different text splitters for different content types"""
        splitters = {}

        for complexity, chunk_size in ADAPTIVE_CHUNK_SIZES.items():
            overlap = ADAPTIVE_CHUNK_OVERLAPS[complexity]
            splitters[complexity] = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""],
            )

        return splitters

    def determine_chunking_parameters(self, element_metadata: dict) -> Tuple[int, int]:
        """Determine optimal chunk size and overlap based on metadata"""

        if self.strategy == "fixed":
            return BASE_CHUNK_SIZE, BASE_CHUNK_OVERLAP

        # Adaptive strategy based on content characteristics
        complexity = element_metadata.get("text_complexity", "medium")
        content_type = element_metadata.get("content_type", "text")

        if content_type == "table":
            return ADAPTIVE_CHUNK_SIZES["table"], ADAPTIVE_CHUNK_OVERLAPS["table"]
        elif content_type == "full_page_with_images":
            return (
                ADAPTIVE_CHUNK_SIZES["image_page"],
                ADAPTIVE_CHUNK_OVERLAPS["image_page"],
            )
        else:
            return ADAPTIVE_CHUNK_SIZES[complexity], ADAPTIVE_CHUNK_OVERLAPS[complexity]

    def chunk_element(self, element: dict) -> List[ChunkedElement]:
        """Chunk a single enriched element into multiple chunks"""

        # Extract content and metadata
        original_element = element["original_element"]
        structural_meta = element["structural_metadata"]
        enrichment_meta = element.get("enrichment_metadata", {})

        # Get element text content
        if hasattr(original_element, "text"):
            content = original_element.text
        else:
            content = str(original_element)

        # Determine chunking parameters
        chunk_size, chunk_overlap = self.determine_chunking_parameters(
            structural_meta.model_dump()
        )

        # Create appropriate splitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        # Split content
        chunks = splitter.split_text(content)

        # Create chunked elements
        chunked_elements = []
        for i, chunk_content in enumerate(chunks):
            # Create chunk metadata
            chunk_meta = ChunkMetadata(
                chunk_id=f"{element['element_id']}_chunk_{i}",
                source_element_id=element["element_id"],
                chunk_index=i,
                total_chunks_in_element=len(chunks),
                source_filename=structural_meta.source_filename,
                page_number=structural_meta.page_number,
                content_type=structural_meta.content_type,
                page_context=structural_meta.page_context,
                content_length=structural_meta.content_length,
                has_numbers=structural_meta.has_numbers,
                element_category=structural_meta.element_category,
                has_tables_on_page=structural_meta.has_tables_on_page,
                has_images_on_page=structural_meta.has_images_on_page,
                text_complexity=structural_meta.text_complexity,
                section_title_category=structural_meta.section_title_category,
                section_title_inherited=structural_meta.section_title_inherited,
                section_title_pattern=structural_meta.section_title_pattern,
                vlm_processed=enrichment_meta.get("vlm_processed", False),
                table_html_caption=enrichment_meta.get("table_html_caption"),
                table_image_caption=enrichment_meta.get("table_image_caption"),
                full_page_image_caption=enrichment_meta.get("full_page_image_caption"),
                page_text_context=enrichment_meta.get("page_text_context"),
                chunking_strategy=self.strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                chunk_word_count=len(chunk_content.split()),
                chunk_character_count=len(chunk_content),
            )

            # Create chunked element
            chunked_element = ChunkedElement(
                chunk_id=chunk_meta.chunk_id, content=chunk_content, metadata=chunk_meta
            )

            chunked_elements.append(chunked_element)

        return chunked_elements


# ==============================================================================
# 3. VECTOR DATABASE MANAGEMENT
# ==============================================================================


class ConstructionVectorDB:
    """Manages vector database operations for construction documents"""

    def __init__(self, db_path: str, collection_name: str):
        self.db_path = db_path
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.embeddings = None

    def initialize(self, embedding_model: str = EMBEDDING_MODEL):
        """Initialize the vector database and embedding model"""

        # Initialize embedding model
        self.embeddings = OpenAIEmbeddings(
            model=embedding_model, openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=self.db_path, settings=Settings(anonymized_telemetry=False)
        )

        # Create or get collection
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            print(f"✅ Connected to existing collection: {self.collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                description=COLLECTION_DESCRIPTION,
                metadata={"hnsw:space": "cosine"},
            )
            print(f"✅ Created new collection: {self.collection_name}")

        # Verify embedding dimensions
        test_embedding = self.embeddings.embed_query("test")
        print(f"✅ Embedding model produces {len(test_embedding)}-dimensional vectors")

    def store_chunks(self, chunked_elements: List[ChunkedElement]) -> Dict[str, Any]:
        """Store chunked elements in the vector database"""

        if not chunked_elements:
            return {"stored_count": 0, "errors": []}

        # Prepare data for storage
        ids = []
        contents = []
        metadatas = []

        for chunk in chunked_elements:
            ids.append(chunk.chunk_id)
            contents.append(chunk.content)
            metadatas.append(chunk.metadata.model_dump())

        # Generate embeddings
        print(f"🔗 Generating embeddings for {len(contents)} chunks...")
        embeddings_list = self.embeddings.embed_documents(contents)

        # Store in database
        print(f"💾 Storing chunks in vector database...")
        self.collection.add(
            ids=ids, embeddings=embeddings_list, documents=contents, metadatas=metadatas
        )

        print(f"✅ Successfully stored {len(chunked_elements)} chunks")
        return {
            "stored_count": len(chunked_elements),
            "collection_count": self.collection.count(),
            "errors": [],
        }

    def query_chunks(
        self, query: str, n_results: int = 5, filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Query the vector database with optional filters"""

        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)

        # Prepare query parameters
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }

        # Add filters if provided
        if filters:
            query_params["where"] = filters

        # Execute query
        results = self.collection.query(**query_params)

        return results


# ==============================================================================
# 4. DATA LOADING & PROCESSING FUNCTIONS
# ==============================================================================


def load_enriched_elements(pickle_file_path: str) -> List[dict]:
    """Load enriched elements from pickle file"""

    print(f"📂 Loading enriched elements from: {pickle_file_path}")

    if not os.path.exists(pickle_file_path):
        raise FileNotFoundError(f"Enriched elements file not found: {pickle_file_path}")

    with open(pickle_file_path, "rb") as f:
        enriched_elements = pickle.load(f)

    print(f"✅ Loaded {len(enriched_elements)} enriched elements")
    return enriched_elements


def process_enriched_elements(
    enriched_elements: List[dict], chunker: AdaptiveChunker
) -> List[ChunkedElement]:
    """Process enriched elements into chunks"""

    print(f"🔪 Chunking {len(enriched_elements)} enriched elements...")

    all_chunks = []

    for element in enriched_elements:
        try:
            chunks = chunker.chunk_element(element)
            all_chunks.extend(chunks)
        except Exception as e:
            print(
                f"❌ Error chunking element {element.get('element_id', 'unknown')}: {e}"
            )
            continue

    print(f"✅ Created {len(all_chunks)} total chunks")
    return all_chunks


def analyze_chunking_results(chunked_elements: List[ChunkedElement]) -> Dict[str, Any]:
    """Analyze chunking results and provide statistics"""

    if not chunked_elements:
        return {"error": "No chunks to analyze"}

    # Basic statistics
    total_chunks = len(chunked_elements)
    total_words = sum(chunk.metadata.chunk_word_count for chunk in chunked_elements)
    total_chars = sum(
        chunk.metadata.chunk_character_count for chunk in chunked_elements
    )

    # Content type distribution
    content_types = {}
    for chunk in chunked_elements:
        content_type = chunk.metadata.content_type
        content_types[content_type] = content_types.get(content_type, 0) + 1

    # Complexity distribution
    complexities = {}
    for chunk in chunked_elements:
        complexity = chunk.metadata.text_complexity
        complexities[complexity] = complexities.get(complexity, 0) + 1

    # Page distribution
    pages = {}
    for chunk in chunked_elements:
        page = chunk.metadata.page_number
        pages[page] = pages.get(page, 0) + 1

    # VLM processing statistics
    vlm_processed = sum(1 for chunk in chunked_elements if chunk.metadata.vlm_processed)

    return {
        "total_chunks": total_chunks,
        "total_words": total_words,
        "total_characters": total_chars,
        "average_words_per_chunk": (
            total_words / total_chunks if total_chunks > 0 else 0
        ),
        "average_chars_per_chunk": (
            total_chars / total_chunks if total_chunks > 0 else 0
        ),
        "content_type_distribution": content_types,
        "complexity_distribution": complexities,
        "page_distribution": pages,
        "vlm_processed_chunks": vlm_processed,
        "vlm_processing_rate": vlm_processed / total_chunks if total_chunks > 0 else 0,
    }


def save_chunking_results(
    chunked_elements: List[ChunkedElement], analysis: Dict[str, Any], output_dir: Path
):
    """Save chunking results and analysis"""

    # Save chunked elements as pickle
    pickle_path = output_dir / "chunked_elements.pkl"
    with open(pickle_path, "wb") as f:
        pickle.dump(chunked_elements, f)

    # Save analysis as JSON
    analysis_path = output_dir / "chunking_analysis.json"
    with open(analysis_path, "w") as f:
        json.dump(analysis, f, indent=2)

    # Save sample chunks as JSON for inspection
    sample_chunks = []
    for chunk in chunked_elements[:10]:  # First 10 chunks
        sample_chunks.append(
            {
                "chunk_id": chunk.chunk_id,
                "content_preview": (
                    chunk.content[:200] + "..."
                    if len(chunk.content) > 200
                    else chunk.content
                ),
                "metadata": chunk.metadata.model_dump(),
            }
        )

    sample_path = output_dir / "sample_chunks.json"
    with open(sample_path, "w") as f:
        json.dump(sample_chunks, f, indent=2)

    print(f"✅ Saved chunking results:")
    print(f"   📄 Chunked elements: {pickle_path}")
    print(f"   📊 Analysis: {analysis_path}")
    print(f"   🔍 Sample chunks: {sample_path}")


# ==============================================================================
# 5. MAIN PROCESSING PIPELINE
# ==============================================================================


def main():
    """Main processing pipeline"""

    print("=" * 60)
    print("🏗️ CONSTRUCTION RAG - CHUNKING & EMBEDDING PIPELINE")
    print("=" * 60)

    # Load environment variables
    load_dotenv()

    # Verify API keys
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY not found in .env file")

    # Setup paths
    enrich_data_run_dir = Path(ENRICH_DATA_DIR) / ENRICH_DATA_RUN_TO_LOAD
    input_pickle_path = enrich_data_run_dir / "enrich_data_output.pkl"

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_run_dir = Path(OUTPUT_BASE_DIR) / f"04_run_{timestamp}"
    current_run_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 Input: {input_pickle_path}")
    print(f"📁 Output: {current_run_dir}")

    # Step 1: Load enriched elements
    print(f"\n📂 STEP 1: LOADING ENRICHED ELEMENTS")
    print("-" * 40)

    enriched_elements = load_enriched_elements(str(input_pickle_path))

    # Step 2: Initialize chunker
    print(f"\n🔪 STEP 2: INITIALIZING CHUNKER")
    print("-" * 40)

    chunker = AdaptiveChunker(strategy=CHUNKING_STRATEGY)
    print(f"✅ Initialized {CHUNKING_STRATEGY} chunking strategy")

    # Step 3: Process elements into chunks
    print(f"\n🔪 STEP 3: CHUNKING ELEMENTS")
    print("-" * 40)

    chunked_elements = process_enriched_elements(enriched_elements, chunker)

    # Step 4: Analyze chunking results
    print(f"\n📊 STEP 4: ANALYZING RESULTS")
    print("-" * 40)

    analysis = analyze_chunking_results(chunked_elements)

    print("📈 Chunking Analysis:")
    print(f"   Total chunks: {analysis['total_chunks']}")
    print(f"   Average words per chunk: {analysis['average_words_per_chunk']:.1f}")
    print(f"   Average chars per chunk: {analysis['average_chars_per_chunk']:.1f}")
    print(f"   VLM processed: {analysis['vlm_processed_chunks']} chunks")

    print("\n📋 Content Type Distribution:")
    for content_type, count in analysis["content_type_distribution"].items():
        print(f"   {content_type}: {count} chunks")

    print("\n📋 Complexity Distribution:")
    for complexity, count in analysis["complexity_distribution"].items():
        print(f"   {complexity}: {count} chunks")

    # Step 5: Initialize vector database
    print(f"\n🗄️ STEP 5: INITIALIZING VECTOR DATABASE")
    print("-" * 40)

    vector_db = ConstructionVectorDB(DB_PATH, COLLECTION_NAME)
    vector_db.initialize()

    # Step 6: Store chunks in vector database
    print(f"\n💾 STEP 6: STORING IN VECTOR DATABASE")
    print("-" * 40)

    storage_results = vector_db.store_chunks(chunked_elements)

    # Step 7: Save results
    print(f"\n💾 STEP 7: SAVING RESULTS")
    print("-" * 40)

    save_chunking_results(chunked_elements, analysis, current_run_dir)

    # Step 8: Test query
    print(f"\n🔍 STEP 8: TESTING QUERY")
    print("-" * 40)

    test_query = "construction specifications technical requirements"
    print(f"🔍 Testing query: '{test_query}'")

    results = vector_db.query_chunks(test_query, n_results=3)

    if results["ids"] and results["ids"][0]:
        print(f"\n📋 Top 3 Results:")
        for i in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][i]
            distance = results["distances"][0][i]
            metadata = results["metadatas"][0][i]
            content = results["documents"][0][i]

            print(f"\n  Result {i+1} (Distance: {distance:.4f}):")
            print(
                f"    📄 Source: {metadata['source_filename']} | Page: {metadata['page_number']}"
            )
            print(
                f"    📝 Type: {metadata['content_type']} | Complexity: {metadata['text_complexity']}"
            )
            print(f"    🔗 Section: {metadata.get('section_title_inherited', 'N/A')}")
            print(f"    📖 Content: {content[:150]}...")
    else:
        print("❌ No results found")

    # Final summary
    print(f"\n🎉 CHUNKING & EMBEDDING PIPELINE COMPLETE!")
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"   📄 Input elements: {len(enriched_elements)}")
    print(f"   🔪 Output chunks: {len(chunked_elements)}")
    print(f"   💾 Stored in vector DB: {storage_results['stored_count']}")
    print(f"   🗄️ Total DB items: {storage_results['collection_count']}")
    print(f"   📁 Output directory: {current_run_dir}")
    print(f"\n🚀 Ready for RAG queries!")


if __name__ == "__main__":
    main()
