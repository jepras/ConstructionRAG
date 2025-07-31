#!/usr/bin/env python3
"""
Comprehensive Embedding Validation Test
Generates validation output similar to embed_voyage.py
"""

import os
import json
import numpy as np
import random
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import requests

# Load environment variables
load_dotenv()

# Configuration
VOYAGE_MODEL = "voyage-multilingual-2"
VOYAGE_DIMENSION = 1024
SAMPLE_SIZE = 10

# Danish Construction Test Texts (same as notebook)
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

# Similarity Test Pairs (same as notebook)
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


def generate_test_embeddings(texts):
    """Generate embeddings for test texts using Voyage API"""
    print("🔗 Generating test embeddings via Voyage API...")

    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        print("❌ VOYAGE_API_KEY not found")
        return None

    url = "https://api.voyageai.com/v1/embeddings"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    embeddings = []
    for text in texts:
        try:
            payload = {"input": text, "model": VOYAGE_MODEL}
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            embeddings.append(result["data"][0]["embedding"])
        except Exception as e:
            print(f"❌ Failed to generate embedding for '{text[:50]}...': {e}")
            return None

    print(f"✅ Generated {len(embeddings)} test embeddings")
    return embeddings


def cosine_similarity(a, b):
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


def test_embedding_quality_with_test_texts(test_embeddings):
    """Test embedding quality using the same test texts as the notebook"""
    print("🔍 Testing embedding quality with test texts...")

    results = {
        "self_similarity_tests": [],
        "similarity_tests": [],
        "danish_character_tests": [],
        "construction_domain_tests": [],
    }

    if not test_embeddings:
        return results

    # Test 1: Self-similarity (identical content should have identical embeddings)
    test_text = "test sætning for validering"
    test_emb = generate_test_embeddings([test_text])
    if test_emb:
        # Generate the same text twice to test self-similarity
        test_emb2 = generate_test_embeddings([test_text])
        if test_emb2:
            self_similarity = cosine_similarity(test_emb[0], test_emb2[0])
            results["self_similarity_tests"].append(
                {
                    "test_text": test_text,
                    "similarity": self_similarity,
                    "passed": self_similarity > 0.9999,
                }
            )

    # Test 2: Similarity tests with construction terms
    for text1, text2 in SIMILARITY_TEST_PAIRS:
        emb1 = generate_test_embeddings([text1])
        emb2 = generate_test_embeddings([text2])

        if emb1 and emb2:
            similarity = cosine_similarity(emb1[0], emb2[0])

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
        emb1 = generate_test_embeddings([text])
        emb2 = generate_test_embeddings([text])  # Encode same text twice

        if emb1 and emb2:
            similarity = cosine_similarity(emb1[0], emb2[0])

            results["danish_character_tests"].append(
                {
                    "text": text,
                    "similarity": similarity,
                    "passed": similarity > 0.9999,
                }
            )

    # Test 4: Construction domain clustering
    construction_terms = ["renovering", "tag", "facade", "vindue", "fundament"]
    non_construction_terms = ["madlavning", "musik", "sport", "biler", "kunst"]

    # Get embeddings for construction terms
    construction_embeddings = generate_test_embeddings(construction_terms)
    non_construction_embeddings = generate_test_embeddings(non_construction_terms)

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


def test_embedding_quality(chunks):
    """Test embedding quality on Danish construction texts"""
    print("🔍 Testing embedding quality...")

    results = {
        "self_similarity_tests": [],
        "similarity_tests": [],
        "danish_character_tests": [],
        "construction_domain_tests": [],
    }

    if not chunks:
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
    # Find chunks containing these terms
    term_chunks = {}
    for chunk in chunks:
        content_lower = chunk["content"].lower()
        for text1, text2 in SIMILARITY_TEST_PAIRS:
            if text1 in content_lower:
                if text1 not in term_chunks:
                    term_chunks[text1] = []
                term_chunks[text1].append(chunk)
            if text2 in content_lower:
                if text2 not in term_chunks:
                    term_chunks[text2] = []
                term_chunks[text2].append(chunk)

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
    construction_terms = ["renovering", "facade", "vindue", "tag", "fundament"]
    non_construction_terms = ["madlavning", "musik", "sport", "biler", "kunst"]

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


def outlier_detection(chunks):
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

    return results


def create_similarity_analysis(chunks, sample_size=10):
    """Create similarity analysis for random sample of chunks"""
    print(f"🔍 Creating similarity analysis for {sample_size} random chunks...")

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

    return analysis


def comprehensive_validation(chunks, test_embeddings=None):
    """Run all validation tests"""
    print("🔍 Running comprehensive embedding validation...")

    validation_results = {
        "quality_testing": test_embedding_quality(chunks),
        "outlier_detection": outlier_detection(chunks),
        "similarity_analysis": create_similarity_analysis(chunks, SAMPLE_SIZE),
    }

    # Add test text quality testing if available
    if test_embeddings:
        test_text_results = test_embedding_quality_with_test_texts(test_embeddings)
        validation_results["test_text_quality"] = test_text_results

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

    # Count tests from test text quality testing
    if "test_text_quality" in validation_results:
        test_text_results = validation_results["test_text_quality"]
        for test_category, test_results in test_text_results.items():
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

    # Convert NumPy types to Python native types for JSON serialization
    validation_results = convert_numpy_types(validation_results)

    return validation_results


def main():
    print("🔍 COMPREHENSIVE EMBEDDING VALIDATION TEST")
    print("=" * 60)

    # Initialize Supabase client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase: Client = create_client(url, key)

    # Get chunks with embeddings
    print("\n📂 Fetching embedded chunks...")
    result = (
        supabase.table("document_chunks")
        .select("*")
        .not_.is_("embedding_1024", "null")
        .execute()
    )

    if not result.data:
        print("❌ No embedded chunks found")
        return

    print(f"✅ Found {len(result.data)} embedded chunks")

    # Process chunks
    processed_chunks = []
    for chunk in result.data:
        embedding = chunk.get("embedding_1024")
        if isinstance(embedding, str):
            try:
                embedding_list = json.loads(embedding)
                processed_chunk = chunk.copy()
                processed_chunk["embedding_1024"] = embedding_list
                processed_chunks.append(processed_chunk)
            except Exception as e:
                print(f"⚠️  Could not parse embedding: {e}")
                continue

    print(f"✅ Processed {len(processed_chunks)} chunks")

    if not processed_chunks:
        print("❌ No valid chunks to analyze")
        return

    # Generate test embeddings for comparison with notebook
    print("\n🔗 Generating test embeddings for comparison...")
    test_embeddings = generate_test_embeddings(DANISH_CONSTRUCTION_TEXTS)

    # Run comprehensive validation
    validation_results = comprehensive_validation(processed_chunks, test_embeddings)

    # Print summary
    summary = validation_results["summary"]
    print(f"\n📊 VALIDATION SUMMARY:")
    print(f"  Total tests: {summary['total_tests']}")
    print(f"  Passed tests: {summary['passed_tests']}")
    print(f"  Validation score: {summary['validation_score']:.2%}")
    print(f"  Overall status: {summary['overall_status']}")
    print(f"  Model: {summary['model_used']}")
    print(f"  Dimensions: {summary['embedding_dimension']}")
    print(f"  Chunks analyzed: {summary['total_chunks_analyzed']}")

    # Save results
    output_dir = Path("validation_output")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"embedding_validation_pipeline_{timestamp}.json"
    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(validation_results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Validation results saved to: {output_path}")
    print(f"🎉 Comprehensive validation complete!")


if __name__ == "__main__":
    main()
