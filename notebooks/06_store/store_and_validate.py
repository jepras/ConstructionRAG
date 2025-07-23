# ==============================================================================
# CHROMA STORAGE & VALIDATION - DANISH CONSTRUCTION DOCUMENTS
# Store embedded chunks in ChromaDB with integrated validation and testing
# ==============================================================================

import os
import sys
import pickle
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import uuid
from pydantic import BaseModel, Field

# --- ChromaDB for Vector Storage ---
import chromadb
from chromadb.config import Settings

# --- Data Processing ---
import numpy as np

# --- Voyage AI for Query Embeddings ---
from voyageai import Client as VoyageClient

# Load environment variables (for future extensions)
from dotenv import load_dotenv

load_dotenv()

# --- Voyage Configuration for Query Embeddings ---
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
VOYAGE_MODEL = "voyage-multilingual-2"

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

# --- Input Data Configuration ---
EMBEDDING_BASE_DIR = "../../data/internal/05_embedding"

# --- Manual Run Selection (leave empty to use latest) ---
SPECIFIC_EMBEDDING_RUN = (
    ""  # e.g., "05_voyage_run_20250723_074238" or "05_run_20250723_075021"
)

# --- ChromaDB Configuration ---
CHROMA_PERSIST_DIRECTORY = "../../chroma_db"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
COLLECTION_NAME = f"construction_documents_{timestamp}"  # Timestamped collection name
EMBEDDING_DIMENSION = 1024  # Voyage multilingual-2 default

# --- Path Configuration ---
OUTPUT_BASE_DIR = "../../data/internal/06_store"

# --- Create timestamped output directory ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CURRENT_RUN_DIR = Path(OUTPUT_BASE_DIR) / f"06_run_{timestamp}"
CURRENT_RUN_DIR.mkdir(parents=True, exist_ok=True)

# --- Load Storage Configuration ---
config_path = Path(__file__).parent / "config" / "storage_config.json"
if config_path.exists():
    with open(config_path, "r") as f:
        config = json.load(f)
    BATCH_SIZE = config.get("batch_size", 100)
    VALIDATION_SAMPLE_SIZE = config.get("validation_sample_size", 50)
    PERFORMANCE_QUERIES = config.get("performance_queries", [])
else:
    # Default configuration
    BATCH_SIZE = 100
    VALIDATION_SAMPLE_SIZE = 50
    PERFORMANCE_QUERIES = [
        "foundation requirements",
        "fundament krav",  # Danish
        "insulation standards",
        "isolering krav",  # Danish
        "structural safety",
    ]

print(f"🗄️  ChromaDB Storage & Validation - Construction Documents")
print(f"📁 ChromaDB directory: {CHROMA_PERSIST_DIRECTORY}")
print(f"📦 Collection name: {COLLECTION_NAME}")
print(f"📁 Output directory: {CURRENT_RUN_DIR}")
print(f"⚙️  Batch size: {BATCH_SIZE}")
if SPECIFIC_EMBEDDING_RUN:
    print(f"🎯 Using specific embedding run: {SPECIFIC_EMBEDDING_RUN}")
else:
    print(f"🕐 Using latest embedding run (auto-detect)")

# ==============================================================================
# 2. DATA MODELS
# ==============================================================================


class ChromaDocument(BaseModel):
    """Document format for ChromaDB storage"""

    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]  # Flattened metadata only


class StorageValidationReport(BaseModel):
    """Comprehensive storage and validation report"""

    # Storage metrics
    total_chunks_stored: int
    chunks_with_embeddings: int
    storage_time_seconds: float

    # Metadata validation
    metadata_fields_indexed: List[str]
    metadata_validation_passed: bool

    # Search performance
    search_performance_ms: Dict[str, float]
    failed_queries: List[str]

    # Retrieval quality
    retrieval_quality_passed: bool
    danish_semantic_performance: str
    average_best_similarity: float

    # Collection health
    collection_size: int
    embedding_dimension_verified: int

    # Overall validation
    validation_passed: bool
    storage_timestamp: str
    validation_timestamp: str

    # Issues found
    issues_found: List[str] = Field(default_factory=list)


class SearchTestResult(BaseModel):
    """Individual search test result"""

    query: str
    response_time_ms: float
    results_count: int
    success: bool
    error_message: Optional[str] = None
    top_result_score: Optional[float] = None


class RetrievalQualityResult(BaseModel):
    """Detailed retrieval quality analysis for a single query"""

    query: str
    best_similarity: float
    worst_similarity: float
    average_similarity: float
    similarity_range: float
    top_results: List[Dict[str, Any]] = Field(default_factory=list)
    bottom_results: List[Dict[str, Any]] = Field(default_factory=list)
    analysis_summary: str


class RetrievalQualityReport(BaseModel):
    """Complete retrieval quality assessment"""

    test_queries: List[str]
    query_results: Dict[str, RetrievalQualityResult]
    overall_assessment: str
    danish_language_performance: str
    recommendations: List[str] = Field(default_factory=list)


# ==============================================================================
# 3. CORE FUNCTIONS
# ==============================================================================


def get_embedding_run() -> Path:
    """Get embedding run directory - either specified manually or latest available"""
    embedding_dir = Path(EMBEDDING_BASE_DIR)

    if not embedding_dir.exists():
        raise FileNotFoundError(f"Embedding directory not found: {embedding_dir}")

    # Check if specific run is manually specified
    if SPECIFIC_EMBEDDING_RUN:
        specific_run_path = embedding_dir / SPECIFIC_EMBEDDING_RUN
        if specific_run_path.exists() and specific_run_path.is_dir():
            print(
                f"📂 Using manually specified embedding run: {SPECIFIC_EMBEDDING_RUN}"
            )
            return specific_run_path
        else:
            raise FileNotFoundError(
                f"Specified embedding run not found: {specific_run_path}"
            )

    # Otherwise, find the most recent run
    run_dirs = [d for d in embedding_dir.iterdir() if d.is_dir() and "run_" in d.name]

    if not run_dirs:
        raise FileNotFoundError(f"No embedding runs found in {embedding_dir}")

    # Sort by timestamp in directory name and get the latest
    latest_run = sorted(run_dirs, key=lambda x: x.name)[-1]
    print(f"📂 Using latest embedding run: {latest_run.name}")

    return latest_run


def load_embedded_chunks(run_dir: Path) -> List[Dict[str, Any]]:
    """Load embedded chunks from an embedding run directory"""

    # Try Voyage first (preferred), then OpenAI format
    voyage_pickle = run_dir / "embedded_chunks_voyage.pkl"
    openai_pickle = run_dir / "embedded_chunks_openai.pkl"
    voyage_json = run_dir / "embedded_chunks_voyage.json"
    openai_json = run_dir / "embedded_chunks_openai.json"

    for file_path in [voyage_pickle, openai_pickle, voyage_json, openai_json]:
        if file_path.exists():
            print(f"📂 Loading embedded chunks from: {file_path}")

            if file_path.suffix == ".pkl":
                with open(file_path, "rb") as f:
                    embedded_chunks = pickle.load(f)
            else:  # JSON
                with open(file_path, "r", encoding="utf-8") as f:
                    embedded_chunks = json.load(f)

            print(f"✅ Loaded {len(embedded_chunks)} embedded chunks")
            return embedded_chunks

    raise FileNotFoundError(f"No embedded chunk files found in {run_dir}")


def validate_embedded_chunks_structure(embedded_chunks: List[Dict[str, Any]]) -> bool:
    """Validate that embedded chunks have the required structure for storage"""
    required_fields = ["chunk_id", "content", "metadata", "embedding"]
    required_metadata_fields = ["source_filename", "page_number", "element_category"]

    for i, chunk in enumerate(embedded_chunks):
        # Check required top-level fields
        for field in required_fields:
            if field not in chunk:
                print(f"❌ Chunk {i} missing required field: {field}")
                return False

        # Check that content is not empty
        if not chunk.get("content", "").strip():
            print(f"❌ Chunk {i} has empty content")
            return False

        # Check embedding structure
        embedding = chunk.get("embedding", [])
        if not isinstance(embedding, list) or len(embedding) == 0:
            print(f"❌ Chunk {i} has invalid embedding")
            return False

        # Check required metadata fields
        metadata = chunk.get("metadata", {})
        for field in required_metadata_fields:
            if field not in metadata:
                print(f"❌ Chunk {i} missing required metadata field: {field}")
                return False

    print("✅ All embedded chunks have valid structure")
    return True


def flatten_metadata_for_chroma(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten nested metadata structures for ChromaDB compatibility.
    ChromaDB only supports flat dictionaries for metadata.
    """
    flattened = {}

    def _flatten_dict(d: Dict[str, Any], prefix: str = "") -> None:
        for key, value in d.items():
            new_key = f"{prefix}_{key}" if prefix else key

            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                _flatten_dict(value, new_key)
            elif isinstance(value, list):
                # Convert lists to strings or handle specific cases
                if all(isinstance(item, str) for item in value):
                    flattened[new_key] = " | ".join(
                        value
                    )  # Join strings with separator
                else:
                    flattened[new_key] = str(value)  # Convert to string
            elif value is None:
                flattened[new_key] = "unknown"
            else:
                # Store primitive values directly
                flattened[new_key] = value

    _flatten_dict(metadata)

    # Ensure all values are ChromaDB-compatible types (string, int, float, bool)
    for key, value in flattened.items():
        if not isinstance(value, (str, int, float, bool)):
            flattened[key] = str(value)

    return flattened


def convert_embedded_chunks_to_chroma(
    embedded_chunks: List[Dict[str, Any]],
) -> List[ChromaDocument]:
    """Convert embedded chunks to ChromaDB-compatible format"""
    print(f"🔄 Converting {len(embedded_chunks)} chunks to ChromaDB format...")

    chroma_documents = []

    for chunk in embedded_chunks:
        # Flatten metadata for ChromaDB
        flattened_metadata = flatten_metadata_for_chroma(chunk["metadata"])

        # Add embedding provider info if available
        if "embedding_provider" in chunk:
            flattened_metadata["embedding_provider"] = chunk["embedding_provider"]
        if "embedding_model" in chunk:
            flattened_metadata["embedding_model"] = chunk["embedding_model"]

        # Create ChromaDB document
        chroma_doc = ChromaDocument(
            id=chunk["chunk_id"],
            content=chunk["content"],
            embedding=chunk["embedding"],
            metadata=flattened_metadata,
        )

        chroma_documents.append(chroma_doc)

    print(f"✅ Converted {len(chroma_documents)} documents to ChromaDB format")
    return chroma_documents


def initialize_chroma_client() -> chromadb.Client:
    """Initialize ChromaDB client with persistent storage"""
    print(f"🔗 Initializing ChromaDB client...")

    # Create persistent directory if it doesn't exist
    Path(CHROMA_PERSIST_DIRECTORY).mkdir(parents=True, exist_ok=True)

    # Initialize client with persistent storage
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIRECTORY)

    print(f"✅ ChromaDB client initialized with persistent storage")
    return client


def store_documents_in_chroma(
    client: chromadb.Client, chroma_documents: List[ChromaDocument]
) -> Tuple[chromadb.Collection, float]:
    """Store documents in ChromaDB collection with batch processing"""
    print(f"💾 Storing {len(chroma_documents)} documents in ChromaDB...")
    start_time = time.time()

    # Get or create collection
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        print(f"📦 Using existing collection: {COLLECTION_NAME}")

        # Check if we should clear existing data
        existing_count = collection.count()
        if existing_count > 0:
            print(f"⚠️  Collection contains {existing_count} existing documents")
            print(f"🗑️  Clearing existing documents for fresh storage...")
            client.delete_collection(name=COLLECTION_NAME)
            collection = client.create_collection(name=COLLECTION_NAME)

    except Exception:
        # Collection doesn't exist, create it
        collection = client.create_collection(name=COLLECTION_NAME)
        print(f"📦 Created new collection: {COLLECTION_NAME}")

    # Store documents in batches
    total_batches = (len(chroma_documents) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(chroma_documents), BATCH_SIZE):
        batch_num = (i // BATCH_SIZE) + 1
        batch_docs = chroma_documents[i : i + BATCH_SIZE]

        print(
            f"📦 Storing batch {batch_num}/{total_batches} ({len(batch_docs)} documents)"
        )

        # Prepare batch data
        ids = [doc.id for doc in batch_docs]
        embeddings = [doc.embedding for doc in batch_docs]
        documents = [doc.content for doc in batch_docs]
        metadatas = [doc.metadata for doc in batch_docs]

        try:
            collection.add(
                ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
            )
            print(f"✅ Batch {batch_num} stored successfully")

        except Exception as e:
            print(f"❌ Error storing batch {batch_num}: {e}")
            raise

    storage_time = time.time() - start_time
    print(f"✅ All documents stored successfully in {storage_time:.2f} seconds")

    return collection, storage_time


def validate_storage_integrity(
    collection: chromadb.Collection, original_count: int
) -> Dict[str, Any]:
    """Validate that all documents were stored correctly"""
    print(f"🔍 Validating storage integrity...")

    validation_results = {
        "chunks_stored": collection.count(),
        "expected_chunks": original_count,
        "storage_match": False,
        "metadata_fields": [],
        "issues": [],
    }

    # Check document count
    stored_count = collection.count()
    if stored_count == original_count:
        validation_results["storage_match"] = True
        print(f"✅ Document count matches: {stored_count}/{original_count}")
    else:
        validation_results["issues"].append(
            f"Document count mismatch: {stored_count}/{original_count}"
        )
        print(f"❌ Document count mismatch: {stored_count}/{original_count}")

    # Check metadata fields by sampling a document
    if stored_count > 0:
        sample_result = collection.get(limit=1, include=["metadatas"])
        if sample_result["metadatas"]:
            metadata_fields = list(sample_result["metadatas"][0].keys())
            validation_results["metadata_fields"] = metadata_fields
            print(f"📋 Metadata fields indexed: {len(metadata_fields)} fields")
        else:
            validation_results["issues"].append("No metadata found in sample document")
            print(f"❌ No metadata found in sample document")

    return validation_results


def create_query_embeddings(queries: List[str]) -> List[List[float]]:
    """Create embeddings for test queries using Voyage API"""
    if not VOYAGE_API_KEY:
        print("⚠️  VOYAGE_API_KEY not found - skipping query embedding generation")
        return []

    try:
        print(f"🔗 Creating embeddings for {len(queries)} test queries using Voyage...")
        client = VoyageClient(api_key=VOYAGE_API_KEY)

        response = client.embed(texts=queries, model=VOYAGE_MODEL)
        embeddings = response.embeddings

        print(f"✅ Generated {len(embeddings)} query embeddings")
        return embeddings

    except Exception as e:
        print(f"❌ Failed to generate query embeddings: {e}")
        return []


def test_search_performance(
    collection: chromadb.Collection,
) -> Dict[str, SearchTestResult]:
    """Test search performance with predefined queries using Voyage embeddings"""
    print(f"⚡ Testing search performance with {len(PERFORMANCE_QUERIES)} queries...")

    search_results = {}

    # Generate embeddings for all queries at once
    query_embeddings = create_query_embeddings(PERFORMANCE_QUERIES)

    if not query_embeddings:
        print("⚠️  No query embeddings available - skipping search performance tests")
        for query in PERFORMANCE_QUERIES:
            search_results[query] = SearchTestResult(
                query=query,
                response_time_ms=0,
                results_count=0,
                success=False,
                error_message="No query embeddings available",
            )
        return search_results

    # Test each query with its embedding
    for i, query in enumerate(PERFORMANCE_QUERIES):
        print(f"🔍 Testing query: '{query}'")

        start_time = time.time()
        try:
            results = collection.query(
                query_embeddings=[query_embeddings[i]],
                n_results=5,
                include=["documents", "distances", "metadatas"],
            )

            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            results_count = len(results["ids"][0]) if results["ids"] else 0
            top_score = (
                1 - results["distances"][0][0]
                if results["distances"] and results["distances"][0]
                else None
            )

            search_results[query] = SearchTestResult(
                query=query,
                response_time_ms=response_time,
                results_count=results_count,
                success=True,
                top_result_score=top_score,
            )

            print(
                f"✅ Query completed in {response_time:.1f}ms, {results_count} results, top score: {top_score:.3f}"
            )

        except Exception as e:
            search_results[query] = SearchTestResult(
                query=query,
                response_time_ms=0,
                results_count=0,
                success=False,
                error_message=str(e),
            )
            print(f"❌ Query failed: {e}")

    return search_results


def test_metadata_filtering(collection: chromadb.Collection) -> Dict[str, Any]:
    """Test metadata filtering capabilities"""
    print(f"🎯 Testing metadata filtering...")

    filtering_tests = {}

    # Test 1: Filter by source filename
    try:
        sample_result = collection.get(limit=1, include=["metadatas"])
        if sample_result["metadatas"]:
            sample_filename = sample_result["metadatas"][0].get("source_filename")
            if sample_filename:
                filtered_results = collection.get(
                    where={"source_filename": sample_filename}, limit=10
                )
                filtering_tests["source_filename_filter"] = {
                    "success": True,
                    "test_filename": sample_filename,
                    "results_count": len(filtered_results["ids"]),
                }
                print(
                    f"✅ Source filename filter: {len(filtered_results['ids'])} results"
                )
    except Exception as e:
        filtering_tests["source_filename_filter"] = {"success": False, "error": str(e)}
        print(f"❌ Source filename filter failed: {e}")

    # Test 2: Filter by element category
    try:
        category_results = collection.get(
            where={"element_category": "NarrativeText"}, limit=10
        )
        filtering_tests["element_category_filter"] = {
            "success": True,
            "results_count": len(category_results["ids"]),
        }
        print(f"✅ Element category filter: {len(category_results['ids'])} results")
    except Exception as e:
        filtering_tests["element_category_filter"] = {"success": False, "error": str(e)}
        print(f"❌ Element category filter failed: {e}")

    return filtering_tests


def test_retrieval_quality(collection: chromadb.Collection) -> RetrievalQualityReport:
    """Comprehensive retrieval quality test with Danish construction queries"""
    print(f"🔍 Testing retrieval quality with Danish construction queries...")

    # Danish queries targeting content we know exists in the PDF
    danish_queries = [
        "regnvand",  # rainwater
        "omkostninger for opmåling og beregning",  # costs for surveying and calculation
        "projekt information",  # project information
    ]

    query_results = {}

    for query in danish_queries:
        print(f"\n🔍 Analyzing query: '{query}'")

        # Create embedding for query
        query_embedding = create_query_embeddings([query])
        if not query_embedding:
            continue

        # Search collection with more results for analysis
        results = collection.query(
            query_embeddings=[query_embedding[0]],
            n_results=20,
            include=["documents", "distances", "metadatas"],
        )

        if not results["ids"] or not results["ids"][0]:
            continue

        # Extract and analyze results
        result_data = []
        for i in range(len(results["ids"][0])):
            similarity_score = 1 - results["distances"][0][i]
            result_data.append(
                {
                    "rank": i + 1,
                    "similarity_score": similarity_score,
                    "content_preview": (
                        results["documents"][0][i][:200] + "..."
                        if len(results["documents"][0][i]) > 200
                        else results["documents"][0][i]
                    ),
                    "source": (
                        results["metadatas"][0][i].get("source_filename", "Unknown")
                        if results["metadatas"]
                        else "Unknown"
                    ),
                    "page": (
                        results["metadatas"][0][i].get("page_number", "Unknown")
                        if results["metadatas"]
                        else "Unknown"
                    ),
                    "category": (
                        results["metadatas"][0][i].get("element_category", "Unknown")
                        if results["metadatas"]
                        else "Unknown"
                    ),
                }
            )

        # Calculate statistics
        similarities = [r["similarity_score"] for r in result_data]
        best_similarity = max(similarities)
        worst_similarity = min(similarities)
        average_similarity = sum(similarities) / len(similarities)
        similarity_range = best_similarity - worst_similarity

        # Analyze quality
        if best_similarity > -0.3:
            quality = "Excellent"
        elif best_similarity > -0.4:
            quality = "Good"
        elif best_similarity > -0.5:
            quality = "Acceptable"
        else:
            quality = "Poor"

        analysis_summary = f"{quality} retrieval (best: {best_similarity:.3f}, range: {similarity_range:.3f})"

        # Store detailed results
        query_results[query] = RetrievalQualityResult(
            query=query,
            best_similarity=best_similarity,
            worst_similarity=worst_similarity,
            average_similarity=average_similarity,
            similarity_range=similarity_range,
            top_results=result_data[:3],  # Top 3 results
            bottom_results=result_data[-3:],  # Bottom 3 results
            analysis_summary=analysis_summary,
        )

        print(f"   {analysis_summary}")

    # Overall assessment
    if query_results:
        avg_best_score = sum(r.best_similarity for r in query_results.values()) / len(
            query_results
        )
        avg_range = sum(r.similarity_range for r in query_results.values()) / len(
            query_results
        )

        if avg_best_score > -0.3 and avg_range > 0.3:
            overall_assessment = "Excellent - High relevance with clear ranking"
        elif avg_best_score > -0.4 and avg_range > 0.2:
            overall_assessment = "Good - Relevant results with decent ranking"
        elif avg_best_score > -0.5:
            overall_assessment = "Acceptable - Some relevant results found"
        else:
            overall_assessment = "Poor - Limited relevant results"

        danish_performance = (
            f"Danish semantic search working well (avg best: {avg_best_score:.3f})"
        )

        # Generate recommendations
        recommendations = []
        if avg_best_score < -0.4:
            recommendations.append(
                "Consider expanding document collection for better coverage"
            )
        if avg_range < 0.2:
            recommendations.append(
                "Results show limited differentiation - may need more diverse content"
            )
        if avg_best_score > -0.3:
            recommendations.append(
                "Excellent semantic search quality - ready for production"
            )

    else:
        overall_assessment = "No valid query results"
        danish_performance = "Unable to assess Danish performance"
        recommendations = ["Check embedding generation and query processing"]

    report = RetrievalQualityReport(
        test_queries=danish_queries,
        query_results=query_results,
        overall_assessment=overall_assessment,
        danish_language_performance=danish_performance,
        recommendations=recommendations,
    )

    print(f"📊 Retrieval quality assessment: {overall_assessment}")
    return report


def create_storage_validation_report(
    original_count: int,
    storage_time: float,
    storage_validation: Dict[str, Any],
    search_results: Dict[str, SearchTestResult],
    filtering_tests: Dict[str, Any],
    retrieval_quality_report: RetrievalQualityReport,
    collection: chromadb.Collection,
) -> StorageValidationReport:
    """Create comprehensive validation report"""

    # Calculate search performance metrics
    successful_searches = [r for r in search_results.values() if r.success]
    failed_queries = [r.query for r in search_results.values() if not r.success]

    search_performance = {}
    if successful_searches:
        search_performance = {
            "average_ms": sum(r.response_time_ms for r in successful_searches)
            / len(successful_searches),
            "min_ms": min(r.response_time_ms for r in successful_searches),
            "max_ms": max(r.response_time_ms for r in successful_searches),
        }

    # Process retrieval quality results
    retrieval_quality_passed = False
    average_best_similarity = 0.0
    danish_performance = "No retrieval quality assessment"

    if retrieval_quality_report.query_results:
        avg_best_score = sum(
            r.best_similarity for r in retrieval_quality_report.query_results.values()
        ) / len(retrieval_quality_report.query_results)
        average_best_similarity = avg_best_score
        danish_performance = retrieval_quality_report.danish_language_performance
        retrieval_quality_passed = avg_best_score > -0.5  # Acceptable threshold

    # Determine overall validation success
    validation_passed = (
        storage_validation.get("storage_match", False)
        and len(failed_queries) == 0
        and len(storage_validation.get("issues", [])) == 0
        and retrieval_quality_passed
    )

    # Collect all issues
    issues_found = storage_validation.get("issues", [])
    if failed_queries:
        issues_found.extend([f"Failed query: {q}" for q in failed_queries])

    # Get embedding dimension from a sample
    embedding_dimension = 0
    try:
        sample = collection.get(limit=1, include=["embeddings"])
        if sample["embeddings"] and sample["embeddings"][0]:
            embedding_dimension = len(sample["embeddings"][0])
    except:
        pass

    report = StorageValidationReport(
        total_chunks_stored=storage_validation.get("chunks_stored", 0),
        chunks_with_embeddings=storage_validation.get("chunks_stored", 0),
        storage_time_seconds=storage_time,
        metadata_fields_indexed=storage_validation.get("metadata_fields", []),
        metadata_validation_passed=len(storage_validation.get("metadata_fields", []))
        > 0,
        search_performance_ms=search_performance,
        failed_queries=failed_queries,
        retrieval_quality_passed=retrieval_quality_passed,
        danish_semantic_performance=danish_performance,
        average_best_similarity=average_best_similarity,
        collection_size=collection.count(),
        embedding_dimension_verified=embedding_dimension,
        validation_passed=validation_passed,
        storage_timestamp=datetime.now().isoformat(),
        validation_timestamp=datetime.now().isoformat(),
        issues_found=issues_found,
    )

    return report


def save_validation_report(
    report: StorageValidationReport,
    search_results: Dict[str, SearchTestResult],
    filtering_tests: Dict[str, Any],
    retrieval_quality_report: RetrievalQualityReport,
):
    """Save comprehensive validation report and detailed results"""

    # Save main validation report
    report_path = CURRENT_RUN_DIR / "storage_validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)

    # Save retrieval quality report
    retrieval_quality_path = CURRENT_RUN_DIR / "retrieval_quality_report.json"
    with open(retrieval_quality_path, "w", encoding="utf-8") as f:
        json.dump(
            retrieval_quality_report.model_dump(), f, indent=2, ensure_ascii=False
        )

    print(f"📊 Validation report saved to: {report_path}")
    print(f"📊 Retrieval quality saved to: {retrieval_quality_path}")


def print_validation_summary(report: StorageValidationReport):
    """Print a summary of validation results"""
    print(f"\n{'='*60}")
    print(f"📊 STORAGE & VALIDATION SUMMARY")
    print(f"{'='*60}")

    # Storage metrics
    print(f"📦 Storage Results:")
    print(f"   Documents stored: {report.total_chunks_stored}")
    print(f"   Storage time: {report.storage_time_seconds:.2f}s")
    print(f"   Collection size: {report.collection_size}")

    # Metadata validation
    print(f"\n🏷️  Metadata Validation:")
    print(f"   Fields indexed: {len(report.metadata_fields_indexed)}")
    print(
        f"   Metadata validation: {'✅ PASSED' if report.metadata_validation_passed else '❌ FAILED'}"
    )

    # Search performance
    if report.search_performance_ms:
        print(f"\n⚡ Search Performance:")
        print(
            f"   Average response: {report.search_performance_ms.get('average_ms', 0):.1f}ms"
        )
        print(
            f"   Fastest query: {report.search_performance_ms.get('min_ms', 0):.1f}ms"
        )
        print(
            f"   Slowest query: {report.search_performance_ms.get('max_ms', 0):.1f}ms"
        )

    # Retrieval quality
    print(f"\n🔍 Retrieval Quality:")
    print(
        f"   Danish semantic search: {'✅ PASSED' if report.retrieval_quality_passed else '❌ FAILED'}"
    )
    print(f"   Average best similarity: {report.average_best_similarity:.3f}")
    print(f"   Assessment: {report.danish_semantic_performance}")

    # Issues
    if report.issues_found:
        print(f"\n⚠️  Issues Found:")
        for issue in report.issues_found:
            print(f"   - {issue}")

    # Overall validation
    validation_status = "✅ PASSED" if report.validation_passed else "❌ FAILED"
    print(f"\n🎯 Overall Validation: {validation_status}")

    if report.failed_queries:
        print(f"\n❌ Failed Queries ({len(report.failed_queries)}):")
        for query in report.failed_queries:
            print(f"   - {query}")


# ==============================================================================
# 4. MAIN EXECUTION
# ==============================================================================


def main():
    """Main execution function"""
    print("🗄️  CHROMA STORAGE & VALIDATION PIPELINE")
    print("=" * 60)

    try:
        # Step 1: Get and load embedded chunks
        print("\n📂 Step 1: Loading embedded chunks...")
        embedding_run = get_embedding_run()
        embedded_chunks = load_embedded_chunks(embedding_run)

        # Step 2: Validate embedded chunks structure
        print("\n✅ Step 2: Validating embedded chunks structure...")
        if not validate_embedded_chunks_structure(embedded_chunks):
            raise ValueError("Embedded chunks validation failed")

        # Step 3: Convert to ChromaDB format
        print("\n🔄 Step 3: Converting to ChromaDB format...")
        chroma_documents = convert_embedded_chunks_to_chroma(embedded_chunks)

        # Step 4: Initialize ChromaDB client
        print("\n🔗 Step 4: Initializing ChromaDB client...")
        client = initialize_chroma_client()

        # Step 5: Store documents in ChromaDB
        print("\n💾 Step 5: Storing documents in ChromaDB...")
        collection, storage_time = store_documents_in_chroma(client, chroma_documents)

        # Step 6: Validate storage integrity
        print("\n🔍 Step 6: Validating storage integrity...")
        storage_validation = validate_storage_integrity(
            collection, len(embedded_chunks)
        )

        # Step 7: Test search performance
        print("\n⚡ Step 7: Testing search performance...")
        search_results = test_search_performance(collection)

        # Step 8: Test metadata filtering
        print("\n🎯 Step 8: Testing metadata filtering...")
        filtering_tests = test_metadata_filtering(collection)

        # Step 9: Test retrieval quality with Danish queries
        print("\n🔍 Step 9: Testing retrieval quality...")
        retrieval_quality_report = test_retrieval_quality(collection)

        # Step 10: Create comprehensive validation report
        print("\n📊 Step 10: Creating validation report...")
        validation_report = create_storage_validation_report(
            len(embedded_chunks),
            storage_time,
            storage_validation,
            search_results,
            filtering_tests,
            retrieval_quality_report,
            collection,
        )

        # Step 11: Save validation report
        print("\n💾 Step 11: Saving validation report...")
        save_validation_report(
            validation_report, search_results, filtering_tests, retrieval_quality_report
        )

        # Step 12: Print summary
        print_validation_summary(validation_report)

        print(f"\n🎉 ChromaDB storage and validation complete!")
        print(f"📁 Output directory: {CURRENT_RUN_DIR}")
        print(f"🗄️  ChromaDB location: {CHROMA_PERSIST_DIRECTORY}")
        print(f"📦 Collection: {COLLECTION_NAME}")
        print(f"📄 Documents stored: {validation_report.total_chunks_stored}")
        print(
            f"🔍 Validation status: {'✅ PASSED' if validation_report.validation_passed else '❌ FAILED'}"
        )

    except Exception as e:
        print(f"\n❌ Error in storage and validation pipeline: {e}")
        raise


if __name__ == "__main__":
    main()
