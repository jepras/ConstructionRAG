# ==============================================================================
# HYBRID SEARCH TESTING & OPTIMIZATION - CONSTRUCTION RAG PIPELINE
# Test all query variations with hybrid search combinations using LangChain
# ==============================================================================

import os
import sys
import json
import time
import psutil
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field

# --- LangChain for Keyword Search ---
from langchain_community.retrievers import BM25Retriever
from langchain.schema import Document

# --- Voyage AI for Embeddings ---
from voyageai import Client as VoyageClient

# --- ChromaDB for Semantic Search ---
import chromadb

# --- Environment Variables ---
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

# --- API Configuration ---
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
if not VOYAGE_API_KEY:
    raise ValueError("VOYAGE_API_KEY environment variable is required")

# --- Path Configuration ---
OUTPUT_BASE_DIR = "../../data/internal/08_retrieve"

# --- Create timestamped output directory ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CURRENT_RUN_DIR = Path(OUTPUT_BASE_DIR) / f"08_run_{timestamp}"
CURRENT_RUN_DIR.mkdir(parents=True, exist_ok=True)

# --- Load Configuration ---
config_path = Path(__file__).parent / "config" / "retrieval_config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# Extract configuration
COLLECTION_SELECTION = config["collection_selection"]
QUERY_SOURCE = config["query_source"]
TESTING_CONFIG = config["testing_config"]
PERFORMANCE_CONFIG = config["performance_config"]
CHROMA_CONFIG = config["chroma_config"]
VOYAGE_CONFIG = config["voyage_config"]
HTML_CONFIG = config["html_output"]

print(f"🔍 Hybrid Search Testing & Optimization - Construction RAG Pipeline")
print(f"📁 Output directory: {CURRENT_RUN_DIR}")
print(f"🔑 Using Voyage model: {VOYAGE_CONFIG['model']}")
print(f"⚙️  Testing {len(TESTING_CONFIG['weight_combinations'])} weight combinations")
print(f"📊 Retrieving {TESTING_CONFIG['top_k_results']} results per combination")

# ==============================================================================
# 2. DATA MODELS
# ==============================================================================

# Add normalization configuration
NORMALIZATION_CONFIG = {
    "use_min_max_normalization": True,
    "use_rrf_fusion": False,  # Set to False to use weighted fusion instead
    "rrf_k": 10,  # Reduced from 60 to get more meaningful scores
    "normalize_rrf_scores": True,  # Normalize RRF scores after calculation
}


class SearchResult(BaseModel):
    """Individual search result with metadata"""

    rank: int
    similarity_score: float
    content: str
    content_snippet: str
    metadata: Dict[str, Any]
    source_filename: str
    page_number: int
    element_category: str


def normalize_scores_min_max(scores: List[float]) -> List[float]:
    """Normalize scores using min-max normalization to 0-1 range"""
    if not scores:
        return []

    min_score = min(scores)
    max_score = max(scores)

    # Handle case where all scores are the same
    if max_score == min_score:
        return [0.5] * len(scores)

    return [(score - min_score) / (max_score - min_score) for score in scores]


def calculate_rrf_scores(
    semantic_ranks: Dict[str, int], keyword_ranks: Dict[str, int], k: int = 60
) -> Dict[str, float]:
    """Calculate Reciprocal Rank Fusion scores"""
    rrf_scores = {}

    # Get all unique document IDs
    all_docs = set(semantic_ranks.keys()) | set(keyword_ranks.keys())

    for doc_id in all_docs:
        semantic_rank = semantic_ranks.get(doc_id, float("inf"))
        keyword_rank = keyword_ranks.get(doc_id, float("inf"))

        # RRF formula: 1 / (k + rank)
        rrf_score = (1 / (k + semantic_rank)) + (1 / (k + keyword_rank))
        rrf_scores[doc_id] = rrf_score

    return rrf_scores


class RetrievalMatrixResult(BaseModel):
    """Result for a single query variation + search method combination"""

    query_variation: str
    search_method: str
    semantic_weight: float
    keyword_weight: float
    top_3_similarities: List[float]
    avg_top_3_similarity: float
    result_count: int
    top_content_snippets: List[str]
    performance_rank: int
    response_time_ms: float
    memory_usage_mb: float


class PerformanceBenchmark(BaseModel):
    """Performance metrics for a single combination"""

    query_variation: str
    search_method: str
    response_time_ms: float
    memory_usage_mb: float
    avg_similarity: float
    similarity_range: float
    throughput_qps: float
    result_count: int


class QueryRetrievalReport(BaseModel):
    """Complete report for all combinations of a single query"""

    original_query: str
    query_variations: List[str]
    matrix_results: Dict[str, RetrievalMatrixResult]
    performance_benchmarks: List[PerformanceBenchmark]
    best_combination: str
    best_similarity_score: float
    processing_time_seconds: float


class OverallRetrievalReport(BaseModel):
    """Overall report across all test queries"""

    test_queries: List[str]
    query_reports: Dict[str, QueryRetrievalReport]
    overall_insights: List[str]
    best_combinations: Dict[str, int]
    performance_summary: Dict[str, Any]
    recommendations: List[str]


# ==============================================================================
# 3. CORE FUNCTIONS
# ==============================================================================


def get_latest_collection() -> str:
    """Auto-detect the latest timestamped collection"""
    client = chromadb.PersistentClient(path=CHROMA_CONFIG["persist_directory"])

    try:
        collections = client.list_collections()
        timestamped_collections = []

        for collection in collections:
            if (
                collection.name.startswith("construction_documents_")
                and "_" in collection.name
            ):
                timestamped_collections.append(collection.name)

        if timestamped_collections:
            # Sort by timestamp (newest first)
            latest = sorted(timestamped_collections, reverse=True)[0]
            print(f"✅ Auto-detected latest collection: {latest}")
            return latest
        else:
            # Fallback to original collection
            print(
                f"⚠️  No timestamped collections found, using 'construction_documents'"
            )
            return "construction_documents"

    except Exception as e:
        print(f"❌ Error detecting collections: {e}")
        return "construction_documents"


def get_latest_query_run() -> Path:
    """Auto-detect the latest 07_query run directory"""
    query_base_dir = Path("../../data/internal/07_query")

    if not query_base_dir.exists():
        raise ValueError(f"07_query directory not found: {query_base_dir}")

    # Find all run directories
    run_dirs = [
        d
        for d in query_base_dir.iterdir()
        if d.is_dir() and d.name.startswith("07_run_")
    ]

    if not run_dirs:
        raise ValueError(f"No 07_query run directories found in {query_base_dir}")

    # Sort by timestamp (newest first)
    latest_run = sorted(run_dirs, key=lambda x: x.name, reverse=True)[0]
    print(f"✅ Auto-detected latest query run: {latest_run.name}")
    return latest_run


def load_query_variations(query_run_dir: Path) -> Dict[str, List[str]]:
    """Load query variations from step 7 output"""
    query_reports_path = query_run_dir / "query_performance_reports.json"

    if not query_reports_path.exists():
        raise ValueError(f"Query performance reports not found: {query_reports_path}")

    with open(query_reports_path, "r", encoding="utf-8") as f:
        query_reports = json.load(f)

    # Extract query variations
    query_variations = {}
    for original_query, report in query_reports.items():
        variations = []
        for variation in report["query_variations"]:
            if variation["success"]:
                variations.append(variation["query_text"])
        query_variations[original_query] = variations

    print(f"📝 Loaded {len(query_variations)} queries with variations")
    return query_variations


def create_query_embedding(query: str) -> Optional[List[float]]:
    """Create embedding for query using Voyage API"""
    try:
        client = VoyageClient(api_key=VOYAGE_API_KEY)
        response = client.embed(texts=[query], model=VOYAGE_CONFIG["model"])
        return response.embeddings[0]
    except Exception as e:
        print(f"❌ Failed to create embedding for query: {e}")
        return None


def initialize_retrievers(
    collection_name: str,
) -> Tuple[chromadb.Collection, BM25Retriever]:
    """Initialize semantic (ChromaDB) and keyword (BM25) retrievers"""

    # Initialize ChromaDB client for semantic search
    chroma_client = chromadb.PersistentClient(path=CHROMA_CONFIG["persist_directory"])
    collection = chroma_client.get_collection(name=collection_name)

    # Get all documents for BM25
    all_results = collection.get(include=["documents", "metadatas"])

    # Create LangChain Documents for BM25
    documents = []
    for i, (doc, metadata) in enumerate(
        zip(all_results["documents"], all_results["metadatas"])
    ):
        documents.append(Document(page_content=doc, metadata=metadata or {}))

    # Initialize keyword retriever (BM25)
    keyword_retriever = BM25Retriever.from_documents(documents)

    print(f"✅ Initialized retrievers")
    print(f"   - Semantic: ChromaDB with {collection.count()} documents")
    print(f"   - Keyword: BM25 with {len(documents)} documents")

    return collection, keyword_retriever


def perform_hybrid_search(
    collection: chromadb.Collection,
    keyword_retriever: BM25Retriever,
    query: str,
    semantic_weight: float,
    keyword_weight: float,
    top_k: int,
) -> List[SearchResult]:
    """Perform hybrid search combining semantic and keyword results with normalization options"""

    # Perform semantic search (only if semantic_weight > 0)
    semantic_results = None
    semantic_scores = {}
    semantic_ranks = {}

    if semantic_weight > 0:
        query_embedding = create_query_embedding(query)
        if query_embedding:
            semantic_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "distances", "metadatas"],
            )

            # Extract semantic scores and create ranks
            if (
                semantic_results
                and semantic_results["ids"]
                and semantic_results["ids"][0]
            ):
                semantic_score_list = []
                for i in range(len(semantic_results["ids"][0])):
                    doc_id = semantic_results["ids"][0][i]
                    similarity = 1 - semantic_results["distances"][0][i]
                    semantic_scores[doc_id] = similarity
                    semantic_score_list.append(similarity)

                # Create ranks for RRF
                sorted_semantic = sorted(semantic_score_list, reverse=True)
                for i, score in enumerate(semantic_score_list):
                    rank = sorted_semantic.index(score) + 1
                    doc_id = semantic_results["ids"][0][i]
                    semantic_ranks[doc_id] = rank

    # Perform keyword search
    keyword_results = keyword_retriever.get_relevant_documents(query, k=top_k)
    keyword_scores = {}
    keyword_ranks = {}
    keyword_score_list = []

    # Process keyword results with proper BM25 scores
    for i, result in enumerate(keyword_results):
        content = result.page_content
        doc_id = f"keyword_{i}"

        # Extract actual BM25 score from the underlying BM25Okapi
        try:
            bm25_model = keyword_retriever.vectorizer
            all_docs = keyword_retriever.docs
            doc_index = None
            for idx, doc in enumerate(all_docs):
                if doc.page_content == content:
                    doc_index = idx
                    break

            if doc_index is not None:
                query_tokens = query.lower().split()
                scores = bm25_model.get_scores(query_tokens)
                keyword_score = float(scores[doc_index])
            else:
                keyword_score = 1.0 - (i / max(len(keyword_results), 1))
        except Exception as e:
            print(f"Warning: Could not extract BM25 score: {e}")
            keyword_score = 1.0 - (i / max(len(keyword_results), 1))

        keyword_scores[doc_id] = keyword_score
        keyword_score_list.append(keyword_score)

    # Create keyword ranks for RRF
    if keyword_score_list:
        sorted_keyword = sorted(keyword_score_list, reverse=True)
        for i, score in enumerate(keyword_score_list):
            rank = sorted_keyword.index(score) + 1
            doc_id = f"keyword_{i}"
            keyword_ranks[doc_id] = rank

    # Choose fusion method
    if (
        NORMALIZATION_CONFIG["use_rrf_fusion"]
        and semantic_weight > 0
        and keyword_weight > 0
    ):
        # Use RRF fusion
        rrf_scores = calculate_rrf_scores(
            semantic_ranks, keyword_ranks, NORMALIZATION_CONFIG["rrf_k"]
        )

        # Normalize RRF scores if enabled
        if NORMALIZATION_CONFIG["normalize_rrf_scores"] and rrf_scores:
            rrf_score_values = list(rrf_scores.values())
            normalized_rrf = normalize_scores_min_max(rrf_score_values)
            rrf_scores = dict(zip(rrf_scores.keys(), normalized_rrf))
        combined_results = {}

        # Add semantic results
        if semantic_results and semantic_results["ids"] and semantic_results["ids"][0]:
            for i in range(len(semantic_results["ids"][0])):
                doc_id = semantic_results["ids"][0][i]
                content = semantic_results["documents"][0][i]
                metadata = (
                    semantic_results["metadatas"][0][i]
                    if semantic_results["metadatas"]
                    else {}
                )
                combined_results[doc_id] = {
                    "content": content,
                    "metadata": metadata,
                    "semantic_score": semantic_scores.get(doc_id, 0.0),
                    "keyword_score": 0.0,
                    "combined_score": rrf_scores.get(doc_id, 0.0),
                }

        # Add keyword results
        for i, result in enumerate(keyword_results):
            content = result.page_content
            doc_id = f"keyword_{i}"

            # Check if content already exists in combined results
            existing_doc_id = None
            for existing_id, doc_data in combined_results.items():
                if doc_data["content"] == content:
                    existing_doc_id = existing_id
                    break

            if existing_doc_id:
                combined_results[existing_doc_id]["keyword_score"] = keyword_scores[
                    doc_id
                ]
                combined_results[existing_doc_id]["combined_score"] = rrf_scores.get(
                    existing_doc_id, 0.0
                )
            else:
                combined_results[doc_id] = {
                    "content": content,
                    "metadata": result.metadata,
                    "semantic_score": 0.0,
                    "keyword_score": keyword_scores[doc_id],
                    "combined_score": rrf_scores.get(doc_id, 0.0),
                }

    else:
        # Use weighted fusion with optional normalization
        combined_results = {}

        # Collect all scores for normalization
        all_semantic_scores = list(semantic_scores.values()) if semantic_scores else []
        all_keyword_scores = list(keyword_scores.values()) if keyword_scores else []

        # Apply min-max normalization if enabled
        if NORMALIZATION_CONFIG["use_min_max_normalization"]:
            if all_semantic_scores:
                normalized_semantic = normalize_scores_min_max(all_semantic_scores)
                semantic_scores_normalized = dict(
                    zip(semantic_scores.keys(), normalized_semantic)
                )
            else:
                semantic_scores_normalized = {}

            if all_keyword_scores:
                normalized_keyword = normalize_scores_min_max(all_keyword_scores)
                keyword_scores_normalized = dict(
                    zip(keyword_scores.keys(), normalized_keyword)
                )
            else:
                keyword_scores_normalized = {}
        else:
            semantic_scores_normalized = semantic_scores
            keyword_scores_normalized = keyword_scores

        # Add semantic results
        if semantic_results and semantic_results["ids"] and semantic_results["ids"][0]:
            for i in range(len(semantic_results["ids"][0])):
                doc_id = semantic_results["ids"][0][i]
                content = semantic_results["documents"][0][i]
                metadata = (
                    semantic_results["metadatas"][0][i]
                    if semantic_results["metadatas"]
                    else {}
                )

                semantic_score = (
                    semantic_scores_normalized.get(doc_id, 0.0) * semantic_weight
                )
                combined_results[doc_id] = {
                    "content": content,
                    "metadata": metadata,
                    "semantic_score": semantic_scores.get(doc_id, 0.0),
                    "keyword_score": 0.0,
                    "combined_score": semantic_score,
                }

        # Add keyword results
        for i, result in enumerate(keyword_results):
            content = result.page_content
            doc_id = f"keyword_{i}"

            # Check if content already exists in combined results
            existing_doc_id = None
            for existing_id, doc_data in combined_results.items():
                if doc_data["content"] == content:
                    existing_doc_id = existing_id
                    break

            keyword_score = keyword_scores_normalized.get(doc_id, 0.0) * keyword_weight

            if existing_doc_id:
                combined_results[existing_doc_id]["keyword_score"] = keyword_scores[
                    doc_id
                ]
                combined_results[existing_doc_id]["combined_score"] += keyword_score
            else:
                combined_results[doc_id] = {
                    "content": content,
                    "metadata": result.metadata,
                    "semantic_score": 0.0,
                    "keyword_score": keyword_scores[doc_id],
                    "combined_score": keyword_score,
                }

    # Sort by combined score and create SearchResult objects
    sorted_results = sorted(
        combined_results.items(), key=lambda x: x[1]["combined_score"], reverse=True
    )

    search_results = []
    for i, (doc_id, doc_data) in enumerate(sorted_results[:top_k]):
        # Create content snippet
        content = doc_data["content"]
        snippet_length = HTML_CONFIG["content_snippet_length"]
        content_snippet = (
            content[:snippet_length] + "..."
            if len(content) > snippet_length
            else content
        )

        # Extract metadata
        metadata = doc_data["metadata"]
        search_result = SearchResult(
            rank=i + 1,
            similarity_score=doc_data["combined_score"],
            content=content,
            content_snippet=content_snippet,
            metadata=metadata,
            source_filename=metadata.get("source_filename", "Unknown"),
            page_number=metadata.get("page_number", 0),
            element_category=metadata.get("element_category", "Unknown"),
        )
        search_results.append(search_result)

    return search_results


def get_memory_usage() -> float:
    """Get current memory usage in MB"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def search_with_benchmarking(
    retriever, query: str, top_k: int
) -> Tuple[List[SearchResult], float, float]:
    """Perform search with performance benchmarking"""

    start_time = time.time()
    start_memory = get_memory_usage()

    try:
        # Perform search
        results = retriever.get_relevant_documents(query, k=top_k)

        # Convert to SearchResult objects
        search_results = []
        for i, result in enumerate(results):
            # Extract similarity score if available
            similarity_score = getattr(result, "metadata", {}).get("score", 0.0)

            # Create content snippet
            content = result.page_content
            snippet_length = HTML_CONFIG["content_snippet_length"]
            content_snippet = (
                content[:snippet_length] + "..."
                if len(content) > snippet_length
                else content
            )

            # Extract metadata
            metadata = result.metadata
            search_result = SearchResult(
                rank=i + 1,
                similarity_score=similarity_score,
                content=content,
                content_snippet=content_snippet,
                metadata=metadata,
                source_filename=metadata.get("source_filename", "Unknown"),
                page_number=metadata.get("page_number", 0),
                element_category=metadata.get("element_category", "Unknown"),
            )
            search_results.append(search_result)

        end_time = time.time()
        end_memory = get_memory_usage()

        response_time = (end_time - start_time) * 1000  # Convert to ms
        memory_usage = end_memory - start_memory

        return search_results, response_time, memory_usage

    except Exception as e:
        print(f"❌ Search error: {e}")
        end_time = time.time()
        end_memory = get_memory_usage()
        response_time = (end_time - start_time) * 1000
        memory_usage = end_memory - start_memory
        return [], response_time, memory_usage


def analyze_search_results(results: List[SearchResult]) -> Dict[str, Any]:
    """Analyze search results for performance metrics"""
    if not results:
        return {
            "avg_similarity": 0.0,
            "similarity_range": 0.0,
            "top_3_similarities": [],
            "avg_top_3_similarity": 0.0,
            "result_count": 0,
        }

    similarities = [r.similarity_score for r in results]
    top_3_similarities = similarities[:3] if len(similarities) >= 3 else similarities

    return {
        "avg_similarity": sum(similarities) / len(similarities),
        "similarity_range": max(similarities) - min(similarities),
        "top_3_similarities": top_3_similarities,
        "avg_top_3_similarity": sum(top_3_similarities) / len(top_3_similarities),
        "result_count": len(results),
    }


def test_query_combinations(
    original_query: str,
    query_variations: List[str],
    collection: chromadb.Collection,
    keyword_retriever: BM25Retriever,
) -> QueryRetrievalReport:
    """Test all combinations of query variations and search methods"""

    start_time = time.time()
    print(f"\n{'='*60}")
    print(f"🔍 TESTING QUERY: '{original_query}'")
    print(f"{'='*60}")

    matrix_results = {}
    performance_benchmarks = []

    # Test each query variation
    for variation_idx, query_variation in enumerate(query_variations):
        variation_type = [
            "original",
            "semantic_expansion",
            "hyde_document",
            "formal_variation",
        ][variation_idx]
        print(f"\n📝 Testing variation {variation_idx + 1}/4: {variation_type}")

        # Test each weight combination
        for weight_idx, (semantic_weight, keyword_weight) in enumerate(
            TESTING_CONFIG["weight_combinations"]
        ):

            # Determine search method name
            if semantic_weight == 1.0 and keyword_weight == 0.0:
                search_method = "semantic_only"
            elif semantic_weight == 0.0 and keyword_weight == 1.0:
                search_method = "keyword_only"
            else:
                search_method = (
                    f"hybrid_{int(semantic_weight*100)}_{int(keyword_weight*100)}"
                )

            print(
                f"   Testing: {search_method} ({semantic_weight:.1f}/{keyword_weight:.1f})"
            )

            # Perform hybrid search with benchmarking
            start_time = time.time()
            start_memory = get_memory_usage()

            try:
                results = perform_hybrid_search(
                    collection,
                    keyword_retriever,
                    query_variation,
                    semantic_weight,
                    keyword_weight,
                    TESTING_CONFIG["top_k_results"],
                )

                end_time = time.time()
                end_memory = get_memory_usage()
                response_time = (end_time - start_time) * 1000
                memory_usage = end_memory - start_memory

            except Exception as e:
                print(f"❌ Search error: {e}")
                results = []
                end_time = time.time()
                end_memory = get_memory_usage()
                response_time = (end_time - start_time) * 1000
                memory_usage = end_memory - start_memory

            # Analyze results
            analysis = analyze_search_results(results)

            # Save individual search results
            search_response = {
                "query": query_variation,
                "method": search_method,
                "semantic_weight": semantic_weight,
                "keyword_weight": keyword_weight,
                "results": [result.model_dump() for result in results],
                "analysis": analysis,
                "response_time_ms": response_time,
                "memory_usage_mb": memory_usage,
                "timestamp": datetime.now().isoformat(),
            }

            # Create query identifier from original query
            query_identifier = original_query[:30].replace(" ", "_")
            saved_filepath = save_search_results(
                search_response, str(CURRENT_RUN_DIR), query_identifier
            )

            # Create matrix result
            matrix_result = RetrievalMatrixResult(
                query_variation=variation_type,
                search_method=search_method,
                semantic_weight=semantic_weight,
                keyword_weight=keyword_weight,
                top_3_similarities=analysis["top_3_similarities"],
                avg_top_3_similarity=analysis["avg_top_3_similarity"],
                result_count=analysis["result_count"],
                top_content_snippets=[r.content_snippet for r in results[:3]],
                performance_rank=0,  # Will be calculated later
                response_time_ms=response_time,
                memory_usage_mb=memory_usage,
            )

            # Create performance benchmark
            benchmark = PerformanceBenchmark(
                query_variation=variation_type,
                search_method=search_method,
                response_time_ms=response_time,
                memory_usage_mb=memory_usage,
                avg_similarity=analysis["avg_similarity"],
                similarity_range=analysis["similarity_range"],
                throughput_qps=1000 / response_time if response_time > 0 else 0,
                result_count=analysis["result_count"],
            )

            # Store results
            key = f"{variation_type}_{search_method}"
            matrix_results[key] = matrix_result
            performance_benchmarks.append(benchmark)

    # Calculate performance rankings
    all_similarities = [r.avg_top_3_similarity for r in matrix_results.values()]
    sorted_combinations = sorted(
        matrix_results.items(), key=lambda x: x[1].avg_top_3_similarity, reverse=True
    )

    for rank, (key, result) in enumerate(sorted_combinations):
        result.performance_rank = rank + 1

    # Find best combination
    best_combination = sorted_combinations[0][0] if sorted_combinations else "none"
    best_similarity = (
        sorted_combinations[0][1].avg_top_3_similarity if sorted_combinations else 0.0
    )

    processing_time = time.time() - start_time

    print(
        f"\n🏆 Best combination: {best_combination} (similarity: {best_similarity:.3f})"
    )

    return QueryRetrievalReport(
        original_query=original_query,
        query_variations=query_variations,
        matrix_results=matrix_results,
        performance_benchmarks=performance_benchmarks,
        best_combination=best_combination,
        best_similarity_score=best_similarity,
        processing_time_seconds=processing_time,
    )


def create_retrieval_matrix_html(query_reports: Dict[str, QueryRetrievalReport]) -> str:
    """Create comprehensive HTML matrix showing all combinations"""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hybrid Search Matrix Analysis</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; font-size: 11px; }}
            th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; vertical-align: top; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
            .query-header {{ background-color: #e6f3ff; font-weight: bold; }}
            .best-score {{ 
                background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%) !important; 
                font-weight: bold; 
                border: 3px solid #28a745 !important;
                box-shadow: 0 2px 4px rgba(40, 167, 69, 0.3);
            }}
            .excellent {{ 
                background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); 
                border-left: 4px solid #28a745;
            }}
            .good {{ 
                background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); 
                border-left: 4px solid #ffc107;
            }}
            .acceptable {{ 
                background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); 
                border-left: 4px solid #dc3545;
            }}
            .poor {{ 
                background: linear-gradient(135deg, #f5c6cb 0%, #f1b0b7 100%); 
                border-left: 4px solid #721c24;
                color: #721c24;
            }}
            .similarity-score {{ text-align: center; font-weight: bold; }}
            .performance-metrics {{ font-size: 10px; color: #666; }}
            .result-item {{ margin-bottom: 4px; padding: 2px; background-color: #f9f9f9; border-radius: 2px; }}
            .result-score {{ font-weight: bold; color: #2d5aa0; }}
            .result-content {{ font-size: 9px; color: #666; }}
            .collapsible {{ cursor: pointer; }}
            .collapsible:hover {{ background-color: #f0f0f0; }}
            .content {{ display: none; padding: 10px; background-color: #f9f9f9; }}
        </style>
        <script>
            function toggleDetails(id) {{
                var content = document.getElementById(id);
                if (content.style.display === "none") {{
                    content.style.display = "block";
                }} else {{
                    content.style.display = "none";
                }}
            }}
        </script>
    </head>
    <body>
        <h1>🔍 Hybrid Search Matrix Analysis - Construction RAG Pipeline</h1>
        <p><strong>Analysis Date:</strong> {timestamp}</p>
        <p><strong>Total Combinations Tested:</strong> {len(query_reports) * 24}</p>
        
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0; border: 1px solid #dee2e6;">
            <h3>🎨 Color Coding Legend</h3>
            <div style="display: flex; flex-wrap: wrap; gap: 20px; margin-top: 10px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 20px; height: 20px; background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); border: 2px solid #28a745; border-radius: 4px;"></div>
                    <span><strong>🟢 Excellent</strong> (Top 20% - Best performing combinations)</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 20px; height: 20px; background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); border: 2px solid #ffc107; border-radius: 4px;"></div>
                    <span><strong>🟡 Good</strong> (Top 40% - Above average performance)</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 20px; height: 20px; background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); border: 2px solid #dc3545; border-radius: 4px;"></div>
                    <span><strong>🟠 Acceptable</strong> (Top 70% - Below average performance)</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 20px; height: 20px; background: linear-gradient(135deg, #f5c6cb 0%, #f1b0b7 100%); border: 2px solid #721c24; border-radius: 4px;"></div>
                    <span><strong>🔴 Poor</strong> (Bottom 30% - Worst performing combinations)</span>
                </div>
            </div>
            <div style="margin-top: 15px; padding: 10px; background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); border: 3px solid #28a745; border-radius: 6px; box-shadow: 0 2px 4px rgba(40, 167, 69, 0.3);">
                <strong>🏆 Best Combination</strong>: Highlighted with green border and shadow - the optimal search method for each query
            </div>
        </div>
    """

    # Create matrix for each query
    for original_query, report in query_reports.items():
        html += f"""
        <h2>📝 Query: "{original_query}"</h2>
        <table>
            <thead>
                <tr>
                    <th>Query Variation</th>
                    <th>Semantic Only<br>(100/0)</th>
                    <th>Hybrid 80/20</th>
                    <th>Hybrid 60/40</th>
                    <th>Hybrid 40/60</th>
                    <th>Hybrid 20/80</th>
                    <th>Keyword Only<br>(0/100)</th>
                </tr>
            </thead>
            <tbody>
        """

        # Define variation types in order
        variation_types = [
            "original",
            "semantic_expansion",
            "hyde_document",
            "formal_variation",
        ]

        for variation_type in variation_types:
            html += f'<tr><td class="query-header">{variation_type.replace("_", " ").title()}</td>'

            # Test each search method
            search_methods = [
                "semantic_only",
                "hybrid_80_20",
                "hybrid_60_40",
                "hybrid_40_60",
                "hybrid_20_80",
                "keyword_only",
            ]

            for search_method in search_methods:
                key = f"{variation_type}_{search_method}"
                if key in report.matrix_results:
                    result = report.matrix_results[key]

                    # Determine color class based on similarity with dynamic thresholds
                    similarity = result.avg_top_3_similarity

                    # Get all similarities for this query to calculate dynamic thresholds
                    all_similarities = [
                        r.avg_top_3_similarity for r in report.matrix_results.values()
                    ]
                    max_similarity = max(all_similarities) if all_similarities else 1.0
                    min_similarity = min(all_similarities) if all_similarities else 0.0
                    range_similarity = max_similarity - min_similarity

                    # Calculate dynamic thresholds based on percentile
                    if range_similarity > 0:
                        # Top 20% = excellent (green)
                        # Top 40% = good (yellow)
                        # Top 70% = acceptable (orange)
                        # Bottom 30% = poor (red)
                        excellent_threshold = max_similarity - (range_similarity * 0.2)
                        good_threshold = max_similarity - (range_similarity * 0.4)
                        acceptable_threshold = max_similarity - (range_similarity * 0.7)

                        if similarity >= excellent_threshold:
                            color_class = "excellent"
                        elif similarity >= good_threshold:
                            color_class = "good"
                        elif similarity >= acceptable_threshold:
                            color_class = "acceptable"
                        else:
                            color_class = "poor"
                    else:
                        # All scores are the same
                        color_class = "excellent"

                    # Check if this is the best combination for this query
                    is_best = key == report.best_combination
                    best_class = "best-score" if is_best else ""

                    # Calculate percentile for this result
                    sorted_similarities = sorted(all_similarities, reverse=True)
                    percentile = (
                        (sorted_similarities.index(similarity) + 1)
                        / len(sorted_similarities)
                        * 100
                    )

                    html += f"""
                    <td class="{color_class} {best_class}">
                        <div class="similarity-score">{result.avg_top_3_similarity:.3f}</div>
                        <div style="font-size: 9px; text-align: center; margin: 2px 0; color: #666;">
                            Top {percentile:.0f}%
                        </div>
                        <div class="performance-metrics">
                            ⏱️ {result.response_time_ms:.0f}ms<br>
                            💾 {result.memory_usage_mb:.1f}MB<br>
                            📊 Rank: {result.performance_rank}/24
                        </div>
                        <div class="collapsible" onclick="toggleDetails('{key}')">
                            📋 Show Top 3 Results
                        </div>
                        <div id="{key}" class="content">
                    """

                    # Add top 3 results
                    for i, snippet in enumerate(result.top_content_snippets[:3]):
                        html += f"""
                        <div class="result-item">
                            <span class="result-score">{result.top_3_similarities[i]:.3f}</span><br>
                            <span class="result-content">{snippet}</span>
                        </div>
                        """

                    html += "</div></td>"
                else:
                    html += "<td>N/A</td>"

            html += "</tr>"

        html += """
            </tbody>
        </table>
        """

    # Add summary insights
    html += """
        <h2>📊 Performance Summary</h2>
        <ul>
    """

    # Count best combinations
    best_combinations = {}
    for report in query_reports.values():
        combo = report.best_combination
        best_combinations[combo] = best_combinations.get(combo, 0) + 1

    for combo, count in sorted(
        best_combinations.items(), key=lambda x: x[1], reverse=True
    ):
        html += f"<li><strong>{combo}</strong>: {count} wins</li>"

    # Calculate average similarities
    all_similarities = []
    for report in query_reports.values():
        for result in report.matrix_results.values():
            all_similarities.append(result.avg_top_3_similarity)

    if all_similarities:
        avg_similarity = sum(all_similarities) / len(all_similarities)
        min_sim = min(all_similarities)
        max_sim = max(all_similarities)
        html += f"<li><strong>Average Similarity</strong>: {avg_similarity:.3f}</li>"
        html += f"<li><strong>Similarity Range</strong>: {min_sim:.3f} to {max_sim:.3f}</li>"

    html += """
        </ul>
        
        <h2>🎯 Key Findings</h2>
        <ul>
            <li><strong>Hybrid Search</strong>: Testing all combinations systematically</li>
            <li><strong>Performance Metrics</strong>: Response time and memory usage tracked</li>
            <li><strong>Visual Analysis</strong>: Color-coded performance matrix</li>
            <li><strong>Metadata Preservation</strong>: All metadata preserved for citation</li>
        </ul>
    </body>
    </html>
    """

    return html


def save_retrieval_matrix_html(query_reports: Dict[str, QueryRetrievalReport]):
    """Save retrieval matrix as HTML file"""
    html_content = create_retrieval_matrix_html(query_reports)

    html_path = CURRENT_RUN_DIR / "retrieval_matrix.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"📊 Retrieval matrix saved to: {html_path}")


def create_overall_retrieval_report(
    query_reports: Dict[str, QueryRetrievalReport],
) -> OverallRetrievalReport:
    """Create overall retrieval report across all test queries"""

    # Count best combinations
    best_combinations = {}
    for report in query_reports.values():
        combo = report.best_combination
        best_combinations[combo] = best_combinations.get(combo, 0) + 1

    # Calculate performance summary
    all_similarities = []
    all_response_times = []
    all_memory_usage = []

    for report in query_reports.values():
        for result in report.matrix_results.values():
            all_similarities.append(result.avg_top_3_similarity)
            all_response_times.append(result.response_time_ms)
            all_memory_usage.append(result.memory_usage_mb)

    performance_summary = {
        "avg_similarity": (
            sum(all_similarities) / len(all_similarities) if all_similarities else 0
        ),
        "avg_response_time_ms": (
            sum(all_response_times) / len(all_response_times)
            if all_response_times
            else 0
        ),
        "avg_memory_usage_mb": (
            sum(all_memory_usage) / len(all_memory_usage) if all_memory_usage else 0
        ),
        "total_combinations_tested": len(all_similarities),
    }

    # Generate insights
    insights = []
    most_effective_combo = (
        max(best_combinations.items(), key=lambda x: x[1])[0]
        if best_combinations
        else "none"
    )
    insights.append(
        f"Most effective combination: {most_effective_combo} (won {best_combinations.get(most_effective_combo, 0)} times)"
    )
    insights.append(
        f"Average similarity across all combinations: {performance_summary['avg_similarity']:.3f}"
    )
    insights.append(
        f"Average response time: {performance_summary['avg_response_time_ms']:.0f}ms"
    )

    # Generate recommendations
    recommendations = []
    if performance_summary["avg_similarity"] > -0.3:
        recommendations.append(
            "Excellent hybrid search performance - ready for production"
        )
    else:
        recommendations.append(
            "Consider optimizing query variations or document collection"
        )

    recommendations.append(f"Best performing combination: {most_effective_combo}")
    recommendations.append(
        "Use LangChain EnsembleRetriever for consistent hybrid search"
    )

    return OverallRetrievalReport(
        test_queries=list(query_reports.keys()),
        query_reports=query_reports,
        overall_insights=insights,
        best_combinations=best_combinations,
        performance_summary=performance_summary,
        recommendations=recommendations,
    )


def save_search_results(
    search_response: Dict, run_folder: str, query_identifier: str = None
) -> str:
    """Save individual search results to run folder."""
    if query_identifier is None:
        # Extract from the query text itself
        query_identifier = search_response["query"][:30].replace(" ", "_")

    filename = f"{search_response['method']}_{query_identifier}.json"
    filepath = os.path.join(run_folder, "search_results", filename)

    # Create search_results directory if it doesn't exist
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(search_response, f, indent=2, ensure_ascii=False)

    return filepath


def save_reports(
    query_reports: Dict[str, QueryRetrievalReport],
    overall_report: OverallRetrievalReport,
):
    """Save all reports to files"""

    # Save individual query reports
    query_reports_data = {
        query: report.model_dump() for query, report in query_reports.items()
    }
    query_reports_path = CURRENT_RUN_DIR / "query_retrieval_reports.json"
    with open(query_reports_path, "w", encoding="utf-8") as f:
        json.dump(query_reports_data, f, indent=2, ensure_ascii=False)

    # Save overall report
    overall_report_path = CURRENT_RUN_DIR / "overall_retrieval_report.json"
    with open(overall_report_path, "w", encoding="utf-8") as f:
        json.dump(overall_report.model_dump(), f, indent=2, ensure_ascii=False)

    # Save performance benchmarks
    all_benchmarks = []
    for report in query_reports.values():
        all_benchmarks.extend([b.model_dump() for b in report.performance_benchmarks])

    benchmarks_path = CURRENT_RUN_DIR / "performance_benchmarks.json"
    with open(benchmarks_path, "w", encoding="utf-8") as f:
        json.dump(all_benchmarks, f, indent=2, ensure_ascii=False)

    print(f"📊 Query retrieval reports saved to: {query_reports_path}")
    print(f"📊 Overall retrieval report saved to: {overall_report_path}")
    print(f"📊 Performance benchmarks saved to: {benchmarks_path}")
    print(f"📊 Individual search results saved to: {CURRENT_RUN_DIR}/search_results/")


def print_overall_summary(overall_report: OverallRetrievalReport):
    """Print overall retrieval summary"""
    print(f"\n{'='*80}")
    print(f"🎯 OVERALL HYBRID SEARCH PERFORMANCE")
    print(f"{'='*80}")

    print(f"📝 Queries Tested: {len(overall_report.test_queries)}")
    for query in overall_report.test_queries:
        print(f'   - "{query}"')

    print(f"\n🏆 Best Combinations:")
    for combo, count in overall_report.best_combinations.items():
        print(f"   - {combo}: {count} wins")

    print(f"\n📊 Performance Summary:")
    summary = overall_report.performance_summary
    print(f"   - Average Similarity: {summary['avg_similarity']:.3f}")
    print(f"   - Average Response Time: {summary['avg_response_time_ms']:.0f}ms")
    print(f"   - Average Memory Usage: {summary['avg_memory_usage_mb']:.1f}MB")
    print(f"   - Total Combinations Tested: {summary['total_combinations_tested']}")

    print(f"\n💡 Overall Insights:")
    for insight in overall_report.overall_insights:
        print(f"   - {insight}")

    print(f"\n🎯 Recommendations:")
    for recommendation in overall_report.recommendations:
        print(f"   - {recommendation}")


# ==============================================================================
# 4. MAIN EXECUTION
# ==============================================================================


def main():
    """Main execution function"""
    print("🔍 HYBRID SEARCH TESTING & OPTIMIZATION PIPELINE")
    print("=" * 60)

    try:
        # Step 1: Auto-detect collection and query source
        print("\n🔗 Step 1: Auto-detecting collection and query source...")

        # Get collection
        if COLLECTION_SELECTION["auto_detect_latest"]:
            collection_name = get_latest_collection()
        else:
            collection_name = COLLECTION_SELECTION["manual_collection"]

        # Get query source
        if QUERY_SOURCE["auto_detect_latest"]:
            query_run_dir = get_latest_query_run()
        else:
            query_run_dir = Path(
                f"../../data/internal/07_query/{QUERY_SOURCE['manual_run']}"
            )

        print(f"🎯 Using collection: '{collection_name}'")
        print(f"🎯 Using query source: '{query_run_dir.name}'")

        # Step 2: Load query variations
        print(f"\n📝 Step 2: Loading query variations...")
        query_variations = load_query_variations(query_run_dir)

        # Step 3: Initialize retrievers
        print(f"\n🔧 Step 3: Initializing retrievers...")
        collection, keyword_retriever = initialize_retrievers(collection_name)

        # Step 4: Test all query combinations
        print(f"\n🔍 Step 4: Testing all query combinations...")
        query_reports = {}

        for original_query, variations in query_variations.items():
            query_report = test_query_combinations(
                original_query, variations, collection, keyword_retriever
            )
            query_reports[original_query] = query_report

        # Step 5: Create overall report
        print(f"\n📊 Step 5: Creating overall analysis...")
        overall_report = create_overall_retrieval_report(query_reports)

        # Step 6: Save reports
        print(f"\n💾 Step 6: Saving reports...")
        save_reports(query_reports, overall_report)

        # Step 7: Create and save HTML matrix
        print(f"\n📊 Step 7: Creating HTML matrix...")
        save_retrieval_matrix_html(query_reports)

        # Step 8: Print overall summary
        print_overall_summary(overall_report)

        print(f"\n🎉 Hybrid Search Testing Complete!")
        print(f"📁 Output directory: {CURRENT_RUN_DIR}")
        print(f"📊 Queries tested: {len(query_variations)}")
        print(f"🔍 Total combinations tested: {len(query_variations) * 24}")
        print(
            f"🏆 Best overall combination: {max(overall_report.best_combinations.items(), key=lambda x: x[1])[0] if overall_report.best_combinations else 'none'}"
        )

    except Exception as e:
        print(f"\n❌ Error in hybrid search testing pipeline: {e}")
        raise


if __name__ == "__main__":
    main()
