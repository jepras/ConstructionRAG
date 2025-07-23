# ==============================================================================
# VOYAGE EMBEDDING API - DANISH CONSTRUCTION DOCUMENTS
# Test and evaluate Voyage voyage-multilingual-2 for Danish construction embeddings
# ==============================================================================

import os
import sys
import pickle
import json
import numpy as np
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# --- Voyage AI for Embeddings ---
from voyageai import Client as VoyageClient

# Load environment variables
load_dotenv()

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

# --- API Configuration ---
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

if not VOYAGE_API_KEY:
    raise ValueError("VOYAGE_API_KEY not found in environment variables")

# --- Model Configuration ---
VOYAGE_MODEL = "voyage-multilingual-2"
VOYAGE_DIMENSION = 1024  # Voyage multilingual-2 dimension

# --- Data Source Configuration ---
CHUNKING_BASE_DIR = "../../data/internal/04_chunking"

# --- Path Configuration ---
OUTPUT_BASE_DIR = "../../data/internal/05_embedding"

# --- Create timestamped output directory ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CURRENT_RUN_DIR = Path(OUTPUT_BASE_DIR) / f"05_voyage_run_{timestamp}"

# --- Create directories ---
Path(OUTPUT_BASE_DIR).mkdir(parents=True, exist_ok=True)
CURRENT_RUN_DIR.mkdir(exist_ok=True)

print(f"🚢 Voyage Embedding API - Danish Construction Documents")
print(f"🤖 Model: {VOYAGE_MODEL} ({VOYAGE_DIMENSION}D)")
print(f"📁 Output directory: {CURRENT_RUN_DIR}")
print(f"🔑 API Key: {'✅ Loaded' if VOYAGE_API_KEY else '❌ Missing'}")

# --- Test Texts for Danish Construction Domain ---
DANISH_CONSTRUCTION_TEXTS = [
    "Facaderne er pudsede, og de skal renoveres både på vej- og gårdfacaden",
    "Der er 53 vindues- og dørhuller i hver af de to facader",
    "Taget er et 45 graders skifertag med tre kviste",
    "Fundamentet er støbt i beton med armering",
    "Vinduerne er dobbeltglas med energisparprofil",
    "Tagrenovering omfatter nye tagsten og isolering",
    "Facadepudsen skal fjernes og erstattes med nyt",
    "Gulvene er af træ og skal slibes og lakkeres",
    "Elektrisk installation skal opgraderes til moderne standard",
    "Ventilationssystemet skal renoveres og udvides",
]

# --- Similarity Test Pairs ---
SIMILARITY_TEST_PAIRS = [
    # Similar construction terms (should have high similarity)
    ("renovering", "renovering af tag"),
    ("facade", "facadepuds"),
    ("vindue", "vindueskarm"),
    ("tag", "tagrenovering"),
    ("fundament", "grundmur"),
    # Different terms (should have lower similarity)
    ("renovering", "madlavning"),
    ("tag", "biler"),
    ("facade", "musik"),
    ("vindue", "sport"),
    ("fundament", "kunst"),
]

# ==============================================================================
# 2. UTILITY FUNCTIONS
# ==============================================================================


def find_latest_chunking_run() -> Path:
    """Find the most recent chunking run directory"""
    chunking_dir = Path(CHUNKING_BASE_DIR)
    if not chunking_dir.exists():
        raise FileNotFoundError(f"Chunking directory not found: {chunking_dir}")

    # Find all run directories
    run_dirs = [
        d for d in chunking_dir.iterdir() if d.is_dir() and d.name.startswith("04_run_")
    ]

    if not run_dirs:
        raise FileNotFoundError(f"No chunking runs found in {chunking_dir}")

    # Sort by timestamp and get the latest
    latest_run = sorted(run_dirs, key=lambda x: x.name)[-1]
    print(f"📂 Found latest chunking run: {latest_run.name}")

    return latest_run


def load_chunks_from_run(run_dir: Path) -> List[Dict[str, Any]]:
    """Load chunks from a chunking run directory"""
    # Try pickle first, then JSON
    pickle_path = run_dir / "final_chunks_intelligent.pkl"
    json_path = run_dir / "final_chunks_intelligent.json"

    if pickle_path.exists():
        print(f"📂 Loading chunks from pickle: {pickle_path}")
        with open(pickle_path, "rb") as f:
            chunks = pickle.load(f)
    elif json_path.exists():
        print(f"📂 Loading chunks from JSON: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
    else:
        raise FileNotFoundError(f"No chunk files found in {run_dir}")

    print(f"✅ Loaded {len(chunks)} chunks")
    return chunks


def validate_chunk_structure(chunks: List[Dict[str, Any]]) -> bool:
    """Validate that chunks have the required structure"""
    required_fields = ["chunk_id", "content", "metadata"]
    required_metadata_fields = ["source_filename", "page_number"]

    for i, chunk in enumerate(chunks):
        # Check required top-level fields
        for field in required_fields:
            if field not in chunk:
                print(f"❌ Chunk {i} missing required field: {field}")
                return False

        # Check required metadata fields
        metadata = chunk.get("metadata", {})
        for field in required_metadata_fields:
            if field not in metadata:
                print(f"❌ Chunk {i} missing required metadata field: {field}")
                return False

        # Check that content is not empty
        if not chunk.get("content", "").strip():
            print(f"❌ Chunk {i} has empty content")
            return False

    print("✅ All chunks have valid structure")
    return True


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    a_array = np.array(a)
    b_array = np.array(b)
    return np.dot(a_array, b_array) / (
        np.linalg.norm(a_array) * np.linalg.norm(b_array)
    )


def convert_numpy_types(obj):
    """Convert NumPy types to Python native types for JSON serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj


# ==============================================================================
# 3. VOYAGE EMBEDDING FUNCTIONS
# ==============================================================================


def initialize_voyage_client():
    """Initialize Voyage client"""
    print(f"🔗 Initializing Voyage client...")

    try:
        client = VoyageClient(api_key=VOYAGE_API_KEY)

        # Test the connection with a simple embedding
        test_response = client.embed(texts=["test sentence"], model=VOYAGE_MODEL)

        test_embedding = test_response.embeddings[0]
        actual_dim = len(test_embedding)

        print(f"✅ Voyage client initialized successfully")
        print(f"📏 Embedding dimension: {actual_dim} (expected: {VOYAGE_DIMENSION})")

        if actual_dim != VOYAGE_DIMENSION:
            print(
                f"⚠️  Warning: Expected dimension {VOYAGE_DIMENSION}, got {actual_dim}"
            )

        return client

    except Exception as e:
        print(f"❌ Error initializing Voyage client: {e}")
        return None


def generate_embeddings_voyage(
    client: VoyageClient,
    texts: List[str],
    batch_size: int = 100,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> List[List[float]]:
    """Generate embeddings using Voyage API with retry logic"""
    print(f"🔗 Generating embeddings for {len(texts)} texts using Voyage API...")

    all_embeddings = []
    total_batches = (len(texts) + batch_size - 1) // batch_size

    for i in range(0, len(texts), batch_size):
        batch_num = (i // batch_size) + 1
        batch_texts = texts[i : i + batch_size]

        print(
            f"📦 Processing batch {batch_num}/{total_batches} ({len(batch_texts)} texts)"
        )

        # Retry logic
        for attempt in range(max_retries):
            try:
                # Create embeddings using Voyage API
                response = client.embed(texts=batch_texts, model=VOYAGE_MODEL)

                batch_embeddings = response.embeddings
                all_embeddings.extend(batch_embeddings)

                print(f"✅ Batch {batch_num} completed")
                break

            except Exception as e:
                print(
                    f"❌ Error processing batch {batch_num} (attempt {attempt + 1}/{max_retries}): {e}"
                )

                if attempt < max_retries - 1:
                    print(f"⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print(
                        f"❌ Failed to process batch {batch_num} after {max_retries} attempts"
                    )
                    raise

    print(f"✅ Generated {len(all_embeddings)} embeddings with Voyage")
    return all_embeddings


def validate_embeddings(
    embeddings: List[List[float]], chunks: List[Dict[str, Any]]
) -> bool:
    """Validate that embeddings were generated correctly"""
    if len(embeddings) != len(chunks):
        print(f"❌ Mismatch: {len(embeddings)} embeddings vs {len(chunks)} chunks")
        return False

    # Check embedding dimensions
    for i, embedding in enumerate(embeddings):
        if len(embedding) != VOYAGE_DIMENSION:
            print(
                f"❌ Chunk {i}: embedding dimension {len(embedding)} != expected {VOYAGE_DIMENSION}"
            )
            return False

    # Check for zero vectors
    zero_vectors = sum(1 for emb in embeddings if all(val == 0 for val in emb))
    if zero_vectors > 0:
        print(f"⚠️  Warning: {zero_vectors} zero vectors found")

    print(f"✅ Basic embeddings validation passed")
    return True


# ==============================================================================
# 4. QUALITY EVALUATION FUNCTIONS
# ==============================================================================


def test_embedding_quality_voyage(
    client: VoyageClient, texts: List[str]
) -> Dict[str, Any]:
    """Test Voyage embedding quality on Danish construction texts"""
    print("🔍 Testing Voyage embedding quality...")

    results = {
        "self_similarity_tests": [],
        "similarity_tests": [],
        "danish_character_tests": [],
        "construction_domain_tests": [],
    }

    # Test 1: Self-similarity (identical content should have identical embeddings)
    test_text = "test sætning for validering"
    test_embedding1 = client.embed([test_text], model=VOYAGE_MODEL).embeddings[0]
    test_embedding2 = client.embed([test_text], model=VOYAGE_MODEL).embeddings[0]

    self_similarity = cosine_similarity(test_embedding1, test_embedding2)
    results["self_similarity_tests"].append(
        {
            "test_text": test_text,
            "similarity": self_similarity,
            "passed": self_similarity > 0.9999,
        }
    )

    # Test 2: Similarity tests with construction terms
    for text1, text2 in SIMILARITY_TEST_PAIRS:
        emb1 = client.embed([text1], model=VOYAGE_MODEL).embeddings[0]
        emb2 = client.embed([text2], model=VOYAGE_MODEL).embeddings[0]
        similarity = cosine_similarity(emb1, emb2)

        # Determine if this should be similar or different
        is_similar_pair = (
            text1 in text2
            or text2 in text1
            or any(word in text2 for word in text1.split())
        )

        results["similarity_tests"].append(
            {
                "text1": text1,
                "text2": text2,
                "similarity": similarity,
                "expected_similar": is_similar_pair,
                "passed": (similarity > 0.7) if is_similar_pair else (similarity < 0.5),
            }
        )

    # Test 3: Danish character handling
    danish_texts = ["æblemost", "økologi", "åbning", "facadepuds", "vindueskarm"]

    for text in danish_texts:
        emb1 = client.embed([text], model=VOYAGE_MODEL).embeddings[0]
        emb2 = client.embed([text], model=VOYAGE_MODEL).embeddings[
            0
        ]  # Encode same text twice
        similarity = cosine_similarity(emb1, emb2)

        results["danish_character_tests"].append(
            {"text": text, "similarity": similarity, "passed": similarity > 0.9999}
        )

    # Test 4: Construction domain clustering
    construction_terms = ["renovering", "tag", "facade", "vindue", "fundament"]
    non_construction_terms = ["madlavning", "musik", "sport", "biler", "kunst"]

    # Get embeddings for construction terms
    construction_embeddings = client.embed(
        construction_terms, model=VOYAGE_MODEL
    ).embeddings
    non_construction_embeddings = client.embed(
        non_construction_terms, model=VOYAGE_MODEL
    ).embeddings

    # Calculate average similarity within construction terms
    construction_similarities = []
    for i in range(len(construction_embeddings)):
        for j in range(i + 1, len(construction_embeddings)):
            sim = cosine_similarity(
                construction_embeddings[i], construction_embeddings[j]
            )
            construction_similarities.append(sim)

    # Calculate average similarity within non-construction terms
    non_construction_similarities = []
    for i in range(len(non_construction_embeddings)):
        for j in range(i + 1, len(non_construction_embeddings)):
            sim = cosine_similarity(
                non_construction_embeddings[i], non_construction_embeddings[j]
            )
            non_construction_similarities.append(sim)

    avg_construction_sim = np.mean(construction_similarities)
    avg_non_construction_sim = np.mean(non_construction_similarities)

    results["construction_domain_tests"].append(
        {
            "avg_construction_similarity": avg_construction_sim,
            "avg_non_construction_similarity": avg_non_construction_sim,
            "clustering_quality": avg_construction_sim - avg_non_construction_sim,
            "passed": avg_construction_sim > avg_non_construction_sim,
        }
    )

    return results


def performance_benchmark(
    client: VoyageClient, sample_texts: List[str]
) -> Dict[str, Any]:
    """Benchmark performance (speed and cost) of Voyage API"""
    print("⚡ Running performance benchmark...")

    results = {}

    # Test Voyage performance
    print("🔗 Testing Voyage performance...")
    voyage_start = time.time()
    voyage_embeddings = generate_embeddings_voyage(client, sample_texts)
    voyage_end = time.time()

    voyage_time = voyage_end - voyage_start
    voyage_time_per_text = voyage_time / len(sample_texts)

    results = {
        "total_time": voyage_time,
        "time_per_text": voyage_time_per_text,
        "texts_per_second": len(sample_texts) / voyage_time,
        "estimated_cost_per_1k_texts": 0.005,  # Rough estimate for Voyage
        "total_texts_processed": len(sample_texts),
    }

    # Print benchmark results
    print(f"\n⚡ PERFORMANCE BENCHMARK:")
    print(f"  Voyage: {voyage_time:.2f}s ({voyage_time_per_text:.3f}s per text)")
    print(f"  Speed: {results['texts_per_second']:.2f} texts/second")
    print(
        f"  Estimated cost per 1k texts: ${results['estimated_cost_per_1k_texts']:.4f}"
    )

    return results


def outlier_detection(
    embeddings: List[List[float]], chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Detect outliers in embeddings"""
    print("🔍 Running outlier detection...")

    results = {"summary": {}, "examples": []}

    embeddings_array = np.array(embeddings)

    # Test 1: Norm outliers (embeddings with unusually large or small norms)
    norms = np.linalg.norm(embeddings_array, axis=1)
    norm_mean = np.mean(norms)
    norm_std = np.std(norms)

    # Find outliers (more than 2.5 standard deviations from mean)
    norm_outliers = []
    for i, norm in enumerate(norms):
        if abs(norm - norm_mean) > 2.5 * norm_std:
            norm_outliers.append(
                {
                    "chunk_id": chunks[i]["chunk_id"],
                    "norm": norm,
                    "deviation": abs(norm - norm_mean) / norm_std,
                    "content_preview": chunks[i]["content"][:100] + "...",
                }
            )

    # Test 2: Statistical outliers using IQR method
    q1 = np.percentile(embeddings_array, 25, axis=0)
    q3 = np.percentile(embeddings_array, 75, axis=0)
    iqr = q3 - q1

    statistical_outliers = []
    for i, embedding in enumerate(embeddings):
        outlier_dims = []
        for dim, value in enumerate(embedding):
            if value < q1[dim] - 2.0 * iqr[dim] or value > q3[dim] + 2.0 * iqr[dim]:
                outlier_dims.append(dim)

        if outlier_dims:
            statistical_outliers.append(
                {
                    "chunk_id": chunks[i]["chunk_id"],
                    "outlier_dimensions": len(outlier_dims),
                    "content_preview": chunks[i]["content"][:100] + "...",
                }
            )

    # Summary statistics
    results["summary"] = {
        "total_chunks": len(chunks),
        "norm_outliers_count": len(norm_outliers),
        "statistical_outliers_count": len(statistical_outliers),
        "norm_stats": {
            "mean": float(norm_mean),
            "std": float(norm_std),
            "min": float(np.min(norms)),
            "max": float(np.max(norms)),
        },
    }

    # Examples (top 3 most extreme outliers)
    examples = []

    # Add norm outliers as examples
    if norm_outliers:
        norm_outliers_sorted = sorted(
            norm_outliers, key=lambda x: x["deviation"], reverse=True
        )
        examples.extend(norm_outliers_sorted[:2])

    # Add statistical outliers as examples
    if statistical_outliers:
        statistical_outliers_sorted = sorted(
            statistical_outliers, key=lambda x: x["outlier_dimensions"], reverse=True
        )
        examples.extend(statistical_outliers_sorted[:2])

    results["examples"] = examples[:3]  # Limit to 3 examples

    # Print results
    print(f"📊 Outlier Summary:")
    print(f"  Total chunks: {len(chunks)}")
    print(
        f"  Norm outliers: {len(norm_outliers)} ({len(norm_outliers)/len(chunks)*100:.1f}%)"
    )
    print(
        f"  Statistical outliers: {len(statistical_outliers)} ({len(statistical_outliers)/len(chunks)*100:.1f}%)"
    )

    if examples:
        print(f"  Examples: {len(examples)} shown")

    return results


def comprehensive_validation(
    client: VoyageClient, embeddings: List[List[float]], chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Run all validation tests"""
    print("\n🔍 Running comprehensive embedding validation...")

    validation_results = {
        "quality_testing": test_embedding_quality_voyage(
            client, DANISH_CONSTRUCTION_TEXTS
        ),
        "outlier_detection": outlier_detection(embeddings, chunks),
    }

    # Calculate overall validation score
    total_tests = 0
    passed_tests = 0

    # Count tests from quality testing
    quality_results = validation_results["quality_testing"]
    for test_category, test_results in quality_results.items():
        if isinstance(test_results, list):
            for test in test_results:
                if "passed" in test:
                    total_tests += 1
                    if test["passed"]:
                        passed_tests += 1

    validation_score = passed_tests / total_tests if total_tests > 0 else 0

    validation_results["summary"] = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "validation_score": validation_score,
        "overall_status": (
            "PASS"
            if validation_score > 0.8
            else "WARNING" if validation_score > 0.6 else "FAIL"
        ),
    }

    print(f"\n📊 VALIDATION SUMMARY:")
    print(f"  Total tests: {total_tests}")
    print(f"  Passed tests: {passed_tests}")
    print(f"  Validation score: {validation_score:.2%}")
    print(f"  Overall status: {validation_results['summary']['overall_status']}")

    # Convert NumPy types to Python native types for JSON serialization
    validation_results = convert_numpy_types(validation_results)

    return validation_results


# ==============================================================================
# 5. OUTPUT FUNCTIONS
# ==============================================================================


def create_embedded_chunks(
    chunks: List[Dict[str, Any]], embeddings: List[List[float]]
) -> List[Dict[str, Any]]:
    """Combine chunks with their embeddings"""
    embedded_chunks = []

    for chunk, embedding in zip(chunks, embeddings):
        embedded_chunk = chunk.copy()
        embedded_chunk["embedding"] = embedding
        embedded_chunk["embedding_provider"] = "voyage"
        embedded_chunk["embedding_model"] = VOYAGE_MODEL
        embedded_chunks.append(embedded_chunk)

    return embedded_chunks


def save_embedded_chunks(embedded_chunks: List[Dict[str, Any]], base_name: str):
    """Save embedded chunks to both pickle and JSON formats"""
    pickle_path = CURRENT_RUN_DIR / f"{base_name}.pkl"
    json_path = CURRENT_RUN_DIR / f"{base_name}.json"

    # Save pickle (complete data with embeddings)
    with open(pickle_path, "wb") as f:
        pickle.dump(embedded_chunks, f)

    # Save JSON (human-readable, embeddings as lists)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(embedded_chunks, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(embedded_chunks)} embedded chunks to:")
    print(f"   📄 {pickle_path}")
    print(f"   📄 {json_path}")


def analyze_embeddings(embedded_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate analysis of embeddings"""
    if not embedded_chunks:
        return {"error": "No embedded chunks to analyze"}

    # Extract embeddings
    embeddings = [chunk["embedding"] for chunk in embedded_chunks]
    embeddings_array = np.array(embeddings)

    # Basic statistics
    analysis = {
        "total_chunks": len(embedded_chunks),
        "embedding_dimension": len(embeddings[0]),
        "embedding_stats": {
            "mean": float(np.mean(embeddings_array)),
            "std": float(np.std(embeddings_array)),
            "min": float(np.min(embeddings_array)),
            "max": float(np.max(embeddings_array)),
        },
        "content_type_distribution": {},
        "chunk_size_distribution": {"small": 0, "medium": 0, "large": 0},
    }

    # Content type distribution
    for chunk in embedded_chunks:
        category = chunk["metadata"].get("element_category", "unknown")
        analysis["content_type_distribution"][category] = (
            analysis["content_type_distribution"].get(category, 0) + 1
        )

    # Chunk size distribution
    for chunk in embedded_chunks:
        content_length = len(chunk["content"])
        if content_length < 500:
            analysis["chunk_size_distribution"]["small"] += 1
        elif content_length < 1000:
            analysis["chunk_size_distribution"]["medium"] += 1
        else:
            analysis["chunk_size_distribution"]["large"] += 1

    return analysis


def save_analysis(analysis: Dict[str, Any]):
    """Save analysis to JSON file"""
    analysis_path = CURRENT_RUN_DIR / "embedding_analysis.json"
    with open(analysis_path, "w") as f:
        json.dump(analysis, f, indent=2)

    print(f"📊 Analysis saved to: {analysis_path}")


def print_summary(analysis: Dict[str, Any]):
    """Print summary to console"""
    print(f"\n=== VOYAGE EMBEDDING SUMMARY ===")
    print(f"  Total chunks: {analysis['total_chunks']}")
    print(f"  Embedding dimension: {analysis['embedding_dimension']}")
    print(f"  Embedding stats:")
    stats = analysis["embedding_stats"]
    print(f"    Mean: {stats['mean']:.4f}")
    print(f"    Std: {stats['std']:.4f}")
    print(f"    Min: {stats['min']:.4f}")
    print(f"    Max: {stats['max']:.4f}")

    print(f"  Content type distribution:")
    for k, v in analysis["content_type_distribution"].items():
        print(f"    {k}: {v}")

    print(f"  Chunk size distribution:")
    for k, v in analysis["chunk_size_distribution"].items():
        print(f"    {k}: {v}")


def create_similarity_analysis(
    embedded_chunks: List[Dict[str, Any]], sample_size: int = 10
) -> Dict[str, Any]:
    """Create similarity analysis for random sample of chunks"""
    print(f"\n🔍 Creating similarity analysis for {sample_size} random chunks...")

    # Select random chunks
    random.seed(42)  # For reproducible results
    sample_chunks = random.sample(
        embedded_chunks, min(sample_size, len(embedded_chunks))
    )

    # Calculate pairwise similarities
    similarities = []
    for i, chunk1 in enumerate(sample_chunks):
        for j, chunk2 in enumerate(sample_chunks):
            if i < j:  # Only calculate each pair once
                similarity = cosine_similarity(chunk1["embedding"], chunk2["embedding"])
                similarities.append(
                    {
                        "chunk1_id": chunk1["chunk_id"],
                        "chunk2_id": chunk2["chunk_id"],
                        "chunk1_content": (
                            chunk1["content"][:200] + "..."
                            if len(chunk1["content"]) > 200
                            else chunk1["content"]
                        ),
                        "chunk2_content": (
                            chunk2["content"][:200] + "..."
                            if len(chunk2["content"]) > 200
                            else chunk2["content"]
                        ),
                        "chunk1_metadata": {
                            "source_filename": chunk1["metadata"].get(
                                "source_filename", "unknown"
                            ),
                            "page_number": chunk1["metadata"].get(
                                "page_number", "unknown"
                            ),
                            "element_category": chunk1["metadata"].get(
                                "element_category", "unknown"
                            ),
                        },
                        "chunk2_metadata": {
                            "source_filename": chunk2["metadata"].get(
                                "source_filename", "unknown"
                            ),
                            "page_number": chunk2["metadata"].get(
                                "page_number", "unknown"
                            ),
                            "element_category": chunk2["metadata"].get(
                                "element_category", "unknown"
                            ),
                        },
                        "similarity": similarity,
                    }
                )

    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x["similarity"], reverse=True)

    # Create analysis summary
    similarity_values = [s["similarity"] for s in similarities]
    analysis = {
        "sample_size": len(sample_chunks),
        "total_pairs": len(similarities),
        "similarity_stats": {
            "mean": float(np.mean(similarity_values)),
            "std": float(np.std(similarity_values)),
            "min": float(np.min(similarity_values)),
            "max": float(np.max(similarity_values)),
            "median": float(np.median(similarity_values)),
        },
        "sample_chunks": [
            {
                "chunk_id": chunk["chunk_id"],
                "content": (
                    chunk["content"][:300] + "..."
                    if len(chunk["content"]) > 300
                    else chunk["content"]
                ),
                "metadata": {
                    "source_filename": chunk["metadata"].get(
                        "source_filename", "unknown"
                    ),
                    "page_number": chunk["metadata"].get("page_number", "unknown"),
                    "element_category": chunk["metadata"].get(
                        "element_category", "unknown"
                    ),
                },
            }
            for chunk in sample_chunks
        ],
        "top_similarities": similarities[:10],  # Top 10 most similar pairs
        "bottom_similarities": similarities[-10:],  # Bottom 10 least similar pairs
        "all_similarities": similarities,
    }

    # Save similarity analysis
    similarity_path = CURRENT_RUN_DIR / "similarity_analysis.json"
    with open(similarity_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    print(f"📊 Similarity analysis saved to: {similarity_path}")
    print(f"  Sample chunks: {len(sample_chunks)}")
    print(f"  Total pairs: {len(similarities)}")
    print(f"  Average similarity: {analysis['similarity_stats']['mean']:.4f}")
    print(f"  Highest similarity: {analysis['similarity_stats']['max']:.4f}")
    print(f"  Lowest similarity: {analysis['similarity_stats']['min']:.4f}")

    return analysis


# ==============================================================================
# 6. MAIN EXECUTION
# ==============================================================================


def main():
    """Main execution function"""
    print("🚢 VOYAGE EMBEDDING PIPELINE - DANISH CONSTRUCTION DOCUMENTS")
    print("=" * 70)

    try:
        # Step 1: Find and load chunks
        print("\n📂 Step 1: Loading chunks from latest chunking run...")
        latest_run = find_latest_chunking_run()
        chunks = load_chunks_from_run(latest_run)

        # Step 2: Validate chunk structure
        print("\n✅ Step 2: Validating chunk structure...")
        if not validate_chunk_structure(chunks):
            raise ValueError("Chunk validation failed")

        # Step 3: Initialize Voyage client
        print("\n🔗 Step 3: Initializing Voyage client...")
        client = initialize_voyage_client()
        if client is None:
            raise ValueError("Failed to initialize Voyage client")

        # Step 4: Generate embeddings
        print("\n🔗 Step 4: Generating embeddings...")
        embeddings = generate_embeddings_voyage(
            client, [chunk["content"] for chunk in chunks]
        )

        # Step 5: Validate embeddings
        print("\n✅ Step 5: Validating embeddings...")
        if not validate_embeddings(embeddings, chunks):
            raise ValueError("Embedding validation failed")

        # Step 6: Comprehensive validation
        print("\n🔍 Step 6: Running comprehensive validation...")
        validation_results = comprehensive_validation(client, embeddings, chunks)

        # Save validation results
        validation_path = CURRENT_RUN_DIR / "embedding_validation.json"
        with open(validation_path, "w") as f:
            json.dump(validation_results, f, indent=2)
        print(f"📊 Validation results saved to: {validation_path}")

        # Step 7: Performance benchmark
        print("\n⚡ Step 7: Running performance benchmark...")
        performance_results = performance_benchmark(client, DANISH_CONSTRUCTION_TEXTS)

        # Save performance results
        performance_path = CURRENT_RUN_DIR / "performance_benchmark.json"
        with open(performance_path, "w") as f:
            json.dump(performance_results, f, indent=2)
        print(f"⚡ Performance results saved to: {performance_path}")

        # Step 8: Combine chunks with embeddings
        print("\n🔗 Step 8: Combining chunks with embeddings...")
        embedded_chunks = create_embedded_chunks(chunks, embeddings)

        # Step 9: Save results
        print("\n💾 Step 9: Saving embedded chunks...")
        save_embedded_chunks(embedded_chunks, "embedded_chunks_voyage")

        # Step 10: Generate and save analysis
        print("\n📊 Step 10: Generating analysis...")
        analysis = analyze_embeddings(embedded_chunks)
        save_analysis(analysis)

        # Step 11: Create similarity analysis
        print("\n🔍 Step 11: Creating similarity analysis...")
        similarity_analysis = create_similarity_analysis(
            embedded_chunks, sample_size=10
        )

        # Step 12: Print summary
        print_summary(analysis)

        print(f"\n🎉 Voyage embedding pipeline complete!")
        print(f"📁 Output directory: {CURRENT_RUN_DIR}")
        print(f"📄 Embedded chunks: {len(embedded_chunks)} chunks with embeddings")
        print(f"🤖 Model used: {VOYAGE_MODEL}")
        print(f"💰 Cost: ~${len(chunks) * 0.000005:.4f} (estimated)")
        print(f"⚡ Speed: {performance_results['texts_per_second']:.2f} texts/second")

    except Exception as e:
        print(f"\n❌ Error in Voyage embedding pipeline: {e}")
        raise


if __name__ == "__main__":
    main()
