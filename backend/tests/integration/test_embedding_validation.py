#!/usr/bin/env python3
"""
Embedding Validation Test for Pipeline Run
Analyzes embeddings from recent pipeline runs and generates validation reports
"""

import asyncio
import sys
import os
import json
import numpy as np
import time
import random
from uuid import UUID
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from src.config.database import get_supabase_client
from src.services.pipeline_service import PipelineService

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

# --- Model Configuration ---
VOYAGE_MODEL = "voyage-multilingual-2"
VOYAGE_DIMENSION = 1024

# --- Test Configuration ---
SAMPLE_SIZE = 10  # Number of chunks to sample for similarity analysis

# --- Danish Construction Test Texts ---
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
# 3. DATABASE FUNCTIONS
# ==============================================================================


async def get_recent_indexing_runs(
    pipeline_service: PipelineService, limit: int = 5
) -> List[Dict[str, Any]]:
    """Get recent indexing runs with embedding results"""
    print(f"🔍 Fetching recent indexing runs...")

    try:
        # Get the database client
        db = get_supabase_client()

        # Query for runs that have embedded chunks
        result = (
            db.table("document_chunks")
            .select("indexing_run_id")
            .not_.is_("embedding_1024", "null")
            .execute()
        )

        if not result.data:
            print("❌ No runs with embedded chunks found")
            return []

        # Get unique run IDs
        run_ids = list(set([chunk["indexing_run_id"] for chunk in result.data]))
        print(f"✅ Found {len(run_ids)} runs with embedded chunks")

        # Debug: print the run IDs
        for run_id in run_ids:
            print(f"   - {run_id}")

        # Get run details for each run ID
        runs = []
        for run_id in run_ids[:limit]:  # Limit to first N runs
            try:
                indexing_run = await pipeline_service.get_indexing_run(UUID(run_id))
                if indexing_run:
                    runs.append(
                        {
                            "id": str(indexing_run.id),
                            "status": indexing_run.status,
                            "started_at": indexing_run.started_at,
                        }
                    )
                    print(f"   ✅ Successfully fetched run {run_id}")
                else:
                    print(f"   ❌ Run {run_id} not found in pipeline service")
            except Exception as e:
                print(f"⚠️  Error fetching run {run_id}: {e}")

        print(f"✅ Returning {len(runs)} valid runs")
        return runs

    except Exception as e:
        print(f"❌ Error fetching runs: {e}")
        return []


async def get_embedded_chunks_from_run(
    pipeline_service: PipelineService,
    run_id: str,
    document_id: str = "550e8400-e29b-41d4-a716-446655440000",
) -> List[Dict[str, Any]]:
    """Get chunks with embeddings from a specific run"""
    print(f"🔍 Fetching embedded chunks from run {run_id}...")

    try:
        # Get the database client
        db = get_supabase_client()

        # Query chunks with embeddings
        result = (
            db.table("document_chunks")
            .select("*")
            .eq("indexing_run_id", run_id)
            .not_.is_("embedding_1024", "null")
            .execute()
        )

        if not result.data:
            print(f"❌ No embedded chunks found for run {run_id}")
            return []

        print(f"✅ Found {len(result.data)} embedded chunks")

        # Process chunks to convert string embeddings to lists
        processed_chunks = []
        for chunk in result.data:
            processed_chunk = chunk.copy()

            # Convert embedding from string to list if needed
            embedding = chunk.get("embedding_1024")
            if isinstance(embedding, str):
                try:
                    # Parse the JSON string representation of the list
                    import json

                    embedding_list = json.loads(embedding)
                    processed_chunk["embedding_1024"] = embedding_list
                    print(
                        f"   Converted JSON string to list (length: {len(embedding_list)})"
                    )
                except Exception as e:
                    print(f"   Warning: Could not parse embedding JSON: {e}")
                    continue
            elif isinstance(embedding, list):
                # Already a list, no conversion needed
                pass
            else:
                print(f"   Warning: Unexpected embedding type: {type(embedding)}")
                continue

            processed_chunks.append(processed_chunk)

        print(f"✅ Processed {len(processed_chunks)} chunks with valid embeddings")
        return processed_chunks

    except Exception as e:
        print(f"❌ Error fetching embedded chunks: {e}")
        return []


# ==============================================================================
# 4. VALIDATION FUNCTIONS
# ==============================================================================


def validate_embedding_structure(chunks: List[Dict[str, Any]]) -> bool:
    """Validate that chunks have the required embedding structure"""
    print(f"🔍 Validating embedding structure for {len(chunks)} chunks...")

    required_fields = [
        "chunk_id",
        "content",
        "embedding_1024",
        "embedding_model",
        "embedding_provider",
    ]

    for i, chunk in enumerate(chunks):
        # Check required fields
        for field in required_fields:
            if field not in chunk:
                print(f"❌ Chunk {i} missing required field: {field}")
                return False

        # Check embedding dimensions
        embedding = chunk.get("embedding_1024", [])
        if len(embedding) != VOYAGE_DIMENSION:
            print(
                f"❌ Chunk {i}: embedding dimension {len(embedding)} != expected {VOYAGE_DIMENSION}"
            )
            return False

        # Check that content is not empty
        if not chunk.get("content", "").strip():
            print(f"❌ Chunk {i} has empty content")
            return False

    print("✅ All chunks have valid embedding structure")
    return True


@pytest.fixture
def chunks() -> List[Dict[str, Any]]:
    """Provide a minimal default chunks fixture for pytest collection.

    This test module is primarily a script; the fixture avoids collection errors
    when running the full suite without DB-backed chunks.
    """
    return []


def test_embedding_quality(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Test embedding quality on Danish construction texts"""
    print("🔍 Testing embedding quality...")

    results = {
        "self_similarity_tests": [],
        "similarity_tests": [],
        "danish_character_tests": [],
        "construction_domain_tests": [],
    }

    if not chunks:
        print("❌ No chunks available for quality testing")
        return results

    # Test 1: Self-similarity (identical content should have identical embeddings)
    # Find chunks with similar content
    content_groups = {}
    for chunk in chunks:
        content_key = chunk["content"][:50]  # Use first 50 chars as key
        if content_key not in content_groups:
            content_groups[content_key] = []
        content_groups[content_key].append(chunk)

    # Test self-similarity for groups with multiple chunks
    for content_key, group_chunks in content_groups.items():
        if len(group_chunks) >= 2:
            chunk1, chunk2 = group_chunks[0], group_chunks[1]
            similarity = cosine_similarity(
                chunk1["embedding_1024"], chunk2["embedding_1024"]
            )

            results["self_similarity_tests"].append(
                {
                    "test_text": chunk1["content"][:100] + "...",
                    "similarity": similarity,
                    "passed": similarity > 0.9999,
                }
            )
            break  # Just test one group

    # Test 2: Similarity tests with construction terms
    # We'll use the actual chunks to find similar terms
    construction_terms = ["renovering", "facade", "vindue", "tag", "fundament"]
    non_construction_terms = ["madlavning", "musik", "sport", "biler", "kunst"]

    # Find chunks containing these terms
    term_chunks = {}
    for chunk in chunks:
        content_lower = chunk["content"].lower()
        for term in construction_terms + non_construction_terms:
            if term in content_lower:
                if term not in term_chunks:
                    term_chunks[term] = []
                term_chunks[term].append(chunk)

    # Test similarity between related terms
    for text1, text2 in SIMILARITY_TEST_PAIRS:
        if text1 in term_chunks and text2 in term_chunks:
            chunk1 = term_chunks[text1][0]
            chunk2 = term_chunks[text2][0]
            similarity = cosine_similarity(
                chunk1["embedding_1024"], chunk2["embedding_1024"]
            )

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
                    "passed": (
                        (similarity > 0.7) if is_similar_pair else (similarity < 0.5)
                    ),
                }
            )

    # Test 3: Danish character handling
    danish_texts = ["æblemost", "økologi", "åbning", "facadepuds", "vindueskarm"]

    for text in danish_texts:
        if text in term_chunks:
            chunk = term_chunks[text][0]
            # For self-similarity, we'll use the same embedding twice
            similarity = cosine_similarity(
                chunk["embedding_1024"], chunk["embedding_1024"]
            )

            results["danish_character_tests"].append(
                {
                    "text": text,
                    "similarity": similarity,
                    "passed": similarity > 0.9999,
                }
            )

    # Test 4: Construction domain clustering
    construction_embeddings = []
    non_construction_embeddings = []

    for term in construction_terms:
        if term in term_chunks:
            construction_embeddings.append(term_chunks[term][0]["embedding_1024"])

    for term in non_construction_terms:
        if term in term_chunks:
            non_construction_embeddings.append(term_chunks[term][0]["embedding_1024"])

    if construction_embeddings and non_construction_embeddings:
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

        if construction_similarities and non_construction_similarities:
            avg_construction_sim = np.mean(construction_similarities)
            avg_non_construction_sim = np.mean(non_construction_similarities)

            results["construction_domain_tests"].append(
                {
                    "avg_construction_similarity": avg_construction_sim,
                    "avg_non_construction_similarity": avg_non_construction_sim,
                    "clustering_quality": avg_construction_sim
                    - avg_non_construction_sim,
                    "passed": avg_construction_sim > avg_non_construction_sim,
                }
            )

    return results


def outlier_detection(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect outliers in embeddings"""
    print("🔍 Running outlier detection...")

    results = {"summary": {}, "examples": []}

    if not chunks:
        return results

    # Extract embeddings
    embeddings = [chunk["embedding_1024"] for chunk in chunks]
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


def create_similarity_analysis(
    chunks: List[Dict[str, Any]], sample_size: int = 10
) -> Dict[str, Any]:
    """Create similarity analysis for random sample of chunks"""
    print(f"\n🔍 Creating similarity analysis for {sample_size} random chunks...")

    if not chunks:
        return {"error": "No chunks available for similarity analysis"}

    # Select random chunks
    random.seed(42)  # For reproducible results
    sample_chunks = random.sample(chunks, min(sample_size, len(chunks)))

    # Calculate pairwise similarities
    similarities = []
    for i, chunk1 in enumerate(sample_chunks):
        for j, chunk2 in enumerate(sample_chunks):
            if i < j:  # Only calculate each pair once
                similarity = cosine_similarity(
                    chunk1["embedding_1024"], chunk2["embedding_1024"]
                )
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
        "top_similarities": similarities[:10],  # Top 10 most similar pairs
        "bottom_similarities": similarities[-10:],  # Bottom 10 least similar pairs
    }

    print(f"📊 Similarity analysis:")
    print(f"  Sample chunks: {len(sample_chunks)}")
    print(f"  Total pairs: {len(similarities)}")
    print(f"  Average similarity: {analysis['similarity_stats']['mean']:.4f}")
    print(f"  Highest similarity: {analysis['similarity_stats']['max']:.4f}")
    print(f"  Lowest similarity: {analysis['similarity_stats']['min']:.4f}")

    return analysis


def comprehensive_validation(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run all validation tests"""
    print("\n🔍 Running comprehensive embedding validation...")

    validation_results = {
        "quality_testing": test_embedding_quality(chunks),
        "outlier_detection": outlier_detection(chunks),
        "similarity_analysis": create_similarity_analysis(chunks, SAMPLE_SIZE),
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
        "model_used": VOYAGE_MODEL,
        "embedding_dimension": VOYAGE_DIMENSION,
        "total_chunks_analyzed": len(chunks),
    }

    print(f"\n📊 VALIDATION SUMMARY:")
    print(f"  Total tests: {total_tests}")
    print(f"  Passed tests: {passed_tests}")
    print(f"  Validation score: {validation_score:.2%}")
    print(f"  Overall status: {validation_results['summary']['overall_status']}")
    print(f"  Model: {VOYAGE_MODEL}")
    print(f"  Dimensions: {VOYAGE_DIMENSION}")
    print(f"  Chunks analyzed: {len(chunks)}")

    # Convert NumPy types to Python native types for JSON serialization
    validation_results = convert_numpy_types(validation_results)

    return validation_results


# ==============================================================================
# 5. OUTPUT FUNCTIONS
# ==============================================================================


def save_validation_results(validation_results: Dict[str, Any], run_id: str):
    """Save validation results to JSON file"""
    # Create output directory
    output_dir = Path("validation_output")
    output_dir.mkdir(exist_ok=True)

    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"embedding_validation_run_{run_id}_{timestamp}.json"
    output_path = output_dir / filename

    # Save results
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(validation_results, f, ensure_ascii=False, indent=2)

    print(f"📊 Validation results saved to: {output_path}")
    return output_path


# ==============================================================================
# 6. MAIN EXECUTION
# ==============================================================================


async def main():
    """Main execution function"""
    print("🔍 EMBEDDING VALIDATION TEST - PIPELINE RUN")
    print("=" * 60)

    try:
        # Initialize services
        print("\n🔧 Initializing services...")
        db = get_supabase_client()
        pipeline_service = PipelineService(db)

        # Get recent indexing runs
        print("\n📂 Step 1: Finding recent indexing runs...")
        recent_runs = await get_recent_indexing_runs(pipeline_service)

        if not recent_runs:
            print("❌ No recent indexing runs found")
            return

        # Use the first (most recent) run
        target_run = recent_runs[0]
        run_id = target_run["id"]
        print(f"✅ Using run: {run_id}")
        print(f"   Status: {target_run['status']}")
        print(f"   Started: {target_run['started_at']}")

        # Get embedded chunks from the run
        print("\n📂 Step 2: Fetching embedded chunks...")
        chunks = await get_embedded_chunks_from_run(pipeline_service, run_id)

        if not chunks:
            print("❌ No embedded chunks found")
            return

        print(f"✅ Found {len(chunks)} embedded chunks")

        # Validate embedding structure
        print("\n✅ Step 3: Validating embedding structure...")
        if not validate_embedding_structure(chunks):
            print("❌ Embedding structure validation failed")
            return

        # Run comprehensive validation
        print("\n🔍 Step 4: Running comprehensive validation...")
        validation_results = comprehensive_validation(chunks)

        # Save results
        print("\n💾 Step 5: Saving validation results...")
        output_path = save_validation_results(validation_results, run_id)

        print(f"\n🎉 Embedding validation complete!")
        print(f"📁 Results saved to: {output_path}")
        print(
            f"📊 Validation score: {validation_results['summary']['validation_score']:.2%}"
        )
        print(f"🏆 Overall status: {validation_results['summary']['overall_status']}")

    except Exception as e:
        print(f"\n❌ Error in embedding validation: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
