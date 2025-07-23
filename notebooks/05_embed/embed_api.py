# ==============================================================================
# EMBEDDING PIPELINE - OPENAI API VERSION
# Generate embeddings using OpenAI's text-embedding-ada-002 API
# Simple, reliable, and works great with Danish text
# ==============================================================================

import os
import sys
import pickle
import json
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# --- OpenAI for Embeddings ---
from openai import OpenAI

# Load environment variables
load_dotenv()

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

# --- OpenAI Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# --- Model Configuration ---
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSION = 3072  # OpenAI text-embedding-3-large dimension

# --- Data Source Configuration ---
# Automatically find the most recent chunking run
CHUNKING_BASE_DIR = "../../data/internal/04_chunking"

# --- Path Configuration ---
OUTPUT_BASE_DIR = "../../data/internal/05_embedding"

# --- Create timestamped output directory ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CURRENT_RUN_DIR = Path(OUTPUT_BASE_DIR) / f"05_run_{timestamp}"

# --- Create directories ---
Path(OUTPUT_BASE_DIR).mkdir(parents=True, exist_ok=True)
CURRENT_RUN_DIR.mkdir(exist_ok=True)

print(f"🤖 OpenAI Embedding Model: {EMBEDDING_MODEL}")
print(f"📁 Output directory: {CURRENT_RUN_DIR}")
print(f"🔑 API Key: {'✅ Loaded' if OPENAI_API_KEY else '❌ Missing'}")


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


# ==============================================================================
# 3. OPENAI EMBEDDING FUNCTIONS
# ==============================================================================


def initialize_openai_client() -> OpenAI:
    """Initialize OpenAI client"""
    print(f"🔗 Initializing OpenAI client...")

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        # Test the connection with a simple embedding
        test_response = client.embeddings.create(
            model=EMBEDDING_MODEL, input="test sentence"
        )

        test_embedding = test_response.data[0].embedding
        actual_dim = len(test_embedding)

        print(f"✅ OpenAI client initialized successfully")
        print(f"📏 Embedding dimension: {actual_dim} (expected: {EMBEDDING_DIMENSION})")

        if actual_dim != EMBEDDING_DIMENSION:
            print(
                f"⚠️  Warning: Expected dimension {EMBEDDING_DIMENSION}, got {actual_dim}"
            )

        return client

    except Exception as e:
        print(f"❌ Error initializing OpenAI client: {e}")
        raise


def generate_embeddings_openai(
    client: OpenAI, chunks: List[Dict[str, Any]], batch_size: int = 100
) -> List[List[float]]:
    """Generate embeddings using OpenAI API in batches"""
    print(f"🔗 Generating embeddings for {len(chunks)} chunks using OpenAI API...")

    # Extract content from chunks
    contents = [chunk["content"] for chunk in chunks]

    # Generate embeddings in batches
    all_embeddings = []
    total_batches = (len(contents) + batch_size - 1) // batch_size

    for i in range(0, len(contents), batch_size):
        batch_num = (i // batch_size) + 1
        batch_contents = contents[i : i + batch_size]

        print(
            f"📦 Processing batch {batch_num}/{total_batches} ({len(batch_contents)} chunks)"
        )

        try:
            # Create embeddings using OpenAI API
            response = client.embeddings.create(
                model=EMBEDDING_MODEL, input=batch_contents
            )

            # Extract embeddings from response
            batch_embeddings = [data.embedding for data in response.data]
            all_embeddings.extend(batch_embeddings)

            print(f"✅ Batch {batch_num} completed")

        except Exception as e:
            print(f"❌ Error processing batch {batch_num}: {e}")
            raise

    print(f"✅ Generated {len(all_embeddings)} embeddings")
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
        if len(embedding) != EMBEDDING_DIMENSION:
            print(
                f"❌ Chunk {i}: embedding dimension {len(embedding)} != expected {EMBEDDING_DIMENSION}"
            )
            return False

    # Check for zero vectors
    zero_vectors = sum(1 for emb in embeddings if all(val == 0 for val in emb))
    if zero_vectors > 0:
        print(f"⚠️  Warning: {zero_vectors} zero vectors found")

    print(f"✅ Basic embeddings validation passed")
    return True


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    a_array = np.array(a)
    b_array = np.array(b)
    return np.dot(a_array, b_array) / (
        np.linalg.norm(a_array) * np.linalg.norm(b_array)
    )


def similarity_testing(
    client: OpenAI, embeddings: List[List[float]], chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Test semantic similarity of embeddings"""
    print("🔍 Running similarity testing...")

    results = {"summary": {}, "examples": []}

    # Test 1: Self-similarity (identical content should have identical embeddings)
    test_text = "test sætning for validering"
    test_embedding1 = (
        client.embeddings.create(model=EMBEDDING_MODEL, input=[test_text])
        .data[0]
        .embedding
    )
    test_embedding2 = (
        client.embeddings.create(model=EMBEDDING_MODEL, input=[test_text])
        .data[0]
        .embedding
    )

    self_similarity = cosine_similarity(test_embedding1, test_embedding2)
    self_passed = self_similarity > 0.9999

    # Test 2: Similar content (construction-related terms should be similar)
    similar_pairs = [
        ("renovering af tag", "tagrenovering"),
        ("byggeprojekt", "konstruktionsprojekt"),
        ("facade", "udvendig væg"),
        ("fundament", "grundmur"),
        ("vindue", "vinduesparti"),
    ]

    similar_results = []
    for text1, text2 in similar_pairs:
        emb1 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[text1])
            .data[0]
            .embedding
        )
        emb2 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[text2])
            .data[0]
            .embedding
        )
        similarity = cosine_similarity(emb1, emb2)
        similar_results.append(
            {
                "text1": text1,
                "text2": text2,
                "similarity": similarity,
                "passed": similarity > 0.7,
            }
        )

    # Test 3: Different content (unrelated terms should be less similar)
    different_pairs = [
        ("renovering", "madlavning"),
        ("tag", "biler"),
        ("fundament", "musik"),
        ("vindue", "sport"),
    ]

    different_results = []
    for text1, text2 in different_pairs:
        emb1 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[text1])
            .data[0]
            .embedding
        )
        emb2 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[text2])
            .data[0]
            .embedding
        )
        similarity = cosine_similarity(emb1, emb2)
        different_results.append(
            {
                "text1": text1,
                "text2": text2,
                "similarity": similarity,
                "passed": similarity < 0.5,
            }
        )

    # Summary
    similar_passed = sum(1 for t in similar_results if t["passed"])
    different_passed = sum(1 for t in different_results if t["passed"])

    results["summary"] = {
        "self_similarity_passed": self_passed,
        "similar_content_passed": similar_passed,
        "similar_content_total": len(similar_results),
        "different_content_passed": different_passed,
        "different_content_total": len(different_results),
        "overall_similarity_score": (similar_passed + different_passed)
        / (len(similar_results) + len(different_results)),
    }

    # Examples (worst performing tests)
    examples = []

    # Add worst similar content test
    worst_similar = min(similar_results, key=lambda x: x["similarity"])
    examples.append(
        {
            "type": "similar_content",
            "text1": worst_similar["text1"],
            "text2": worst_similar["text2"],
            "similarity": worst_similar["similarity"],
            "passed": worst_similar["passed"],
        }
    )

    # Add worst different content test
    worst_different = max(different_results, key=lambda x: x["similarity"])
    examples.append(
        {
            "type": "different_content",
            "text1": worst_different["text1"],
            "text2": worst_different["text2"],
            "similarity": worst_different["similarity"],
            "passed": worst_different["passed"],
        }
    )

    results["examples"] = examples

    # Print results
    print(f"✅ Self-similarity: {'PASS' if self_passed else 'FAIL'}")
    print(f"✅ Similar content: {similar_passed}/{len(similar_results)} passed")
    print(f"✅ Different content: {different_passed}/{len(different_results)} passed")
    print(
        f"📊 Overall similarity score: {results['summary']['overall_similarity_score']:.1%}"
    )

    return results


def cross_validation_testing(
    client: OpenAI, chunks: List[Dict[str, Any]], sample_size: int = 5
) -> Dict[str, Any]:
    """Test embedding consistency across multiple runs"""
    print("🔄 Running cross-validation testing...")

    results = {"re_embedding_tests": [], "batch_consistency_tests": []}

    # Test 1: Re-embedding consistency
    sample_chunks = chunks[:sample_size]
    for i, chunk in enumerate(sample_chunks):
        content = chunk["content"]

        # Generate embedding twice
        emb1 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[content])
            .data[0]
            .embedding
        )
        emb2 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[content])
            .data[0]
            .embedding
        )

        similarity = cosine_similarity(emb1, emb2)
        results["re_embedding_tests"].append(
            {
                "chunk_id": chunk["chunk_id"],
                "similarity": similarity,
                "passed": similarity > 0.9999,
            }
        )

    # Test 2: Batch consistency (same content in different batch contexts)
    test_content = "test indhold for batch konsistens"
    batch1 = [test_content] + ["dummy content"] * 4
    batch2 = ["dummy content"] * 4 + [test_content]

    emb1 = (
        client.embeddings.create(model=EMBEDDING_MODEL, input=batch1).data[0].embedding
    )
    emb2 = (
        client.embeddings.create(model=EMBEDDING_MODEL, input=batch2).data[-1].embedding
    )

    batch_similarity = cosine_similarity(emb1, emb2)
    results["batch_consistency_tests"].append(
        {
            "test_content": test_content,
            "similarity": batch_similarity,
            "passed": batch_similarity > 0.9999,
        }
    )

    # Print results
    print(
        f"✅ Re-embedding tests: {sum(1 for t in results['re_embedding_tests'] if t['passed'])}/{len(results['re_embedding_tests'])} passed"
    )
    print(
        f"✅ Batch consistency tests: {sum(1 for t in results['batch_consistency_tests'] if t['passed'])}/{len(results['batch_consistency_tests'])} passed"
    )

    return results


def danish_language_validation(client: OpenAI) -> Dict[str, Any]:
    """Test Danish language handling in embeddings"""
    print("🇩🇰 Running Danish language validation...")

    results = {
        "danish_character_tests": [],
        "compound_word_tests": [],
        "technical_term_tests": [],
        "grammar_tests": [],
    }

    # Test 1: Danish characters (æ, ø, å)
    danish_chars = [
        ("æblemost", "æblemost"),  # Should be identical
        ("økologi", "økologi"),
        ("åbning", "åbning"),
    ]

    for text1, text2 in danish_chars:
        emb1 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[text1])
            .data[0]
            .embedding
        )
        emb2 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[text2])
            .data[0]
            .embedding
        )
        similarity = cosine_similarity(emb1, emb2)
        results["danish_character_tests"].append(
            {"text": text1, "similarity": similarity, "passed": similarity > 0.9999}
        )

    # Test 2: Danish compound words
    compound_pairs = [
        ("byggeprojekt", "bygge projekt"),  # Should be similar
        ("tagrenovering", "tag renovering"),
        ("facadepuds", "facade puds"),
        ("vindueskarm", "vindue skarm"),
    ]

    for compound, separated in compound_pairs:
        emb1 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[compound])
            .data[0]
            .embedding
        )
        emb2 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[separated])
            .data[0]
            .embedding
        )
        similarity = cosine_similarity(emb1, emb2)
        results["compound_word_tests"].append(
            {
                "compound": compound,
                "separated": separated,
                "similarity": similarity,
                "passed": similarity > 0.7,
            }
        )

    # Test 3: Danish construction technical terms
    technical_terms = [
        ("renovering", "renovering"),  # Self-similarity
        ("fundament", "grundmur"),  # Synonyms
        ("tag", "tagkonstruktion"),  # Related terms
        ("facade", "udvendig væg"),  # Related terms
    ]

    for term1, term2 in technical_terms:
        emb1 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[term1])
            .data[0]
            .embedding
        )
        emb2 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[term2])
            .data[0]
            .embedding
        )
        similarity = cosine_similarity(emb1, emb2)
        results["technical_term_tests"].append(
            {
                "term1": term1,
                "term2": term2,
                "similarity": similarity,
                "passed": similarity > 0.6,
            }
        )

    # Test 4: Danish grammar variations
    grammar_pairs = [
        ("renovering", "renoveringer"),  # Singular vs plural
        ("bygge", "bygger"),  # Infinitive vs present
        ("taget", "tage"),  # Past vs infinitive
    ]

    for form1, form2 in grammar_pairs:
        emb1 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[form1])
            .data[0]
            .embedding
        )
        emb2 = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[form2])
            .data[0]
            .embedding
        )
        similarity = cosine_similarity(emb1, emb2)
        results["grammar_tests"].append(
            {
                "form1": form1,
                "form2": form2,
                "similarity": similarity,
                "passed": similarity > 0.6,
            }
        )

    # Print results
    print(
        f"✅ Danish character tests: {sum(1 for t in results['danish_character_tests'] if t['passed'])}/{len(results['danish_character_tests'])} passed"
    )
    print(
        f"✅ Compound word tests: {sum(1 for t in results['compound_word_tests'] if t['passed'])}/{len(results['compound_word_tests'])} passed"
    )
    print(
        f"✅ Technical term tests: {sum(1 for t in results['technical_term_tests'] if t['passed'])}/{len(results['technical_term_tests'])} passed"
    )
    print(
        f"✅ Grammar tests: {sum(1 for t in results['grammar_tests'] if t['passed'])}/{len(results['grammar_tests'])} passed"
    )

    return results


def domain_validation(client: OpenAI, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Test construction domain-specific embedding quality"""
    print("🏗️ Running construction domain validation...")

    results = {
        "construction_term_clustering": [],
        "document_structure_tests": [],
        "metadata_correlation_tests": [],
    }

    # Test 1: Construction terms should cluster together
    construction_terms = [
        "renovering",
        "tag",
        "facade",
        "fundament",
        "vindue",
        "dør",
        "isolering",
    ]
    non_construction_terms = [
        "madlavning",
        "musik",
        "sport",
        "biler",
        "rejser",
        "kunst",
        "videnskab",
    ]

    # Get embeddings for construction terms
    construction_embeddings = []
    for term in construction_terms:
        emb = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[term])
            .data[0]
            .embedding
        )
        construction_embeddings.append(emb)

    # Get embeddings for non-construction terms
    non_construction_embeddings = []
    for term in non_construction_terms:
        emb = (
            client.embeddings.create(model=EMBEDDING_MODEL, input=[term])
            .data[0]
            .embedding
        )
        non_construction_embeddings.append(emb)

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

    results["construction_term_clustering"].append(
        {
            "avg_construction_similarity": avg_construction_sim,
            "avg_non_construction_similarity": avg_non_construction_sim,
            "clustering_quality": avg_construction_sim - avg_non_construction_sim,
            "passed": avg_construction_sim > avg_non_construction_sim,
        }
    )

    # Test 2: Document structure correlation (similar sections should be similar)
    if len(chunks) >= 10:
        # Group chunks by section title
        section_groups = {}
        for chunk in chunks[:20]:  # Sample first 20 chunks
            section = chunk["metadata"].get("section_title_inherited", "unknown")
            if section not in section_groups:
                section_groups[section] = []
            section_groups[section].append(chunk)

        # Test similarity within sections
        section_similarities = []
        for section, section_chunks in section_groups.items():
            if len(section_chunks) >= 2:
                # Get embeddings for this section
                section_contents = [
                    chunk["content"] for chunk in section_chunks[:3]
                ]  # Max 3 per section
                section_embeddings = []
                for content in section_contents:
                    emb = (
                        client.embeddings.create(model=EMBEDDING_MODEL, input=[content])
                        .data[0]
                        .embedding
                    )
                    section_embeddings.append(emb)

                # Calculate average similarity within section
                section_sims = []
                for i in range(len(section_embeddings)):
                    for j in range(i + 1, len(section_embeddings)):
                        sim = cosine_similarity(
                            section_embeddings[i], section_embeddings[j]
                        )
                        section_sims.append(sim)

                if section_sims:
                    avg_section_sim = np.mean(section_sims)
                    section_similarities.append(avg_section_sim)

        if section_similarities:
            avg_section_similarity = np.mean(section_similarities)
            results["document_structure_tests"].append(
                {
                    "avg_section_similarity": avg_section_similarity,
                    "passed": avg_section_similarity
                    > 0.3,  # Should have some similarity within sections
                }
            )

    # Print results
    print(
        f"✅ Construction term clustering: {sum(1 for t in results['construction_term_clustering'] if t['passed'])}/{len(results['construction_term_clustering'])} passed"
    )
    print(
        f"✅ Document structure tests: {sum(1 for t in results['document_structure_tests'] if t['passed'])}/{len(results['document_structure_tests'])} passed"
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

    # Find outliers (more than 2.5 standard deviations from mean - more conservative)
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

    # Test 2: Statistical outliers using IQR method (more robust)
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


def comprehensive_validation(
    client: OpenAI, embeddings: List[List[float]], chunks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Run all validation tests"""
    print("\n🔍 Running comprehensive embedding validation...")

    validation_results = {
        "similarity_testing": similarity_testing(client, embeddings, chunks),
        "cross_validation": cross_validation_testing(client, chunks),
        "danish_validation": danish_language_validation(client),
        "domain_validation": domain_validation(client, chunks),
        "outlier_detection": outlier_detection(embeddings, chunks),
    }

    # Calculate overall validation score
    total_tests = 0
    passed_tests = 0

    # Count tests from each validation type
    for test_type, results in validation_results.items():
        if test_type == "outlier_detection":
            # Outlier detection doesn't have pass/fail, just reports findings
            continue

        for test_category, test_results in results.items():
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
# 4. OUTPUT FUNCTIONS
# ==============================================================================


def create_embedded_chunks(
    chunks: List[Dict[str, Any]], embeddings: List[List[float]]
) -> List[Dict[str, Any]]:
    """Combine chunks with their embeddings"""
    embedded_chunks = []

    for chunk, embedding in zip(chunks, embeddings):
        embedded_chunk = chunk.copy()
        embedded_chunk["embedding"] = embedding
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
    print(f"\n=== OPENAI EMBEDDING SUMMARY ===")
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


# ==============================================================================
# 5. MAIN EXECUTION
# ==============================================================================


def main():
    """Main execution function"""
    print("🤖 EMBEDDING PIPELINE - OPENAI API VERSION")
    print("=" * 60)

    try:
        # Step 1: Find and load chunks
        print("\n📂 Step 1: Loading chunks from latest chunking run...")
        latest_run = find_latest_chunking_run()
        chunks = load_chunks_from_run(latest_run)

        # Step 2: Validate chunk structure
        print("\n✅ Step 2: Validating chunk structure...")
        if not validate_chunk_structure(chunks):
            raise ValueError("Chunk validation failed")

        # Step 3: Initialize OpenAI client
        print("\n🔗 Step 3: Initializing OpenAI client...")
        client = initialize_openai_client()

        # Step 4: Generate embeddings
        print("\n🔗 Step 4: Generating embeddings...")
        embeddings = generate_embeddings_openai(client, chunks)

        # Step 5: Validate embeddings
        print("\n✅ Step 5: Validating embeddings...")
        if not validate_embeddings(embeddings, chunks):
            raise ValueError("Embedding validation failed")

        # Step 5.5: Comprehensive validation
        print("\n🔍 Step 5.5: Running comprehensive validation...")
        validation_results = comprehensive_validation(client, embeddings, chunks)

        # Save validation results
        validation_path = CURRENT_RUN_DIR / "embedding_validation.json"
        with open(validation_path, "w") as f:
            json.dump(validation_results, f, indent=2)
        print(f"📊 Validation results saved to: {validation_path}")

        # Step 6: Combine chunks with embeddings
        print("\n🔗 Step 6: Combining chunks with embeddings...")
        embedded_chunks = create_embedded_chunks(chunks, embeddings)

        # Step 7: Save results
        print("\n💾 Step 7: Saving embedded chunks...")
        save_embedded_chunks(embedded_chunks, "embedded_chunks_openai")

        # Step 8: Generate and save analysis
        print("\n📊 Step 8: Generating analysis...")
        analysis = analyze_embeddings(embedded_chunks)
        save_analysis(analysis)

        # Step 9: Print summary
        print_summary(analysis)

        print(f"\n🎉 OpenAI embedding pipeline complete!")
        print(f"📁 Output directory: {CURRENT_RUN_DIR}")
        print(f"📄 Embedded chunks: {len(embedded_chunks)} chunks with embeddings")
        print(f"🤖 Model used: {EMBEDDING_MODEL}")
        print(f"💰 Cost: ~${len(chunks) * 0.0001:.4f} (estimated)")

    except Exception as e:
        print(f"\n❌ Error in embedding pipeline: {e}")
        raise


if __name__ == "__main__":
    main()
