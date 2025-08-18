#!/usr/bin/env python3
"""
Embedding Quality Analysis for ConstructionRAG Pipeline
Tests existing embeddings for quality and performance issues
"""

import asyncio
import json
import time
import ast
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import httpx
from dotenv import load_dotenv
import os
import sys

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Load environment variables
load_dotenv()

from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings


class VoyageEmbeddingClient:
    """Client for Voyage AI embedding API"""
    
    def __init__(self, api_key: str, model: str = "voyage-multilingual-2"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.voyageai.com/v1/embeddings"
        self.dimensions = 1024
    
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text using Voyage AI"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": self.model, "input": [text]},
                )
                
                if response.status_code != 200:
                    raise Exception(f"Voyage API error: {response.status_code} - {response.text}")
                
                result = response.json()
                return result["data"][0]["embedding"]
        
        except Exception as e:
            print(f"Failed to generate embedding: {e}")
            raise


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    vec1_array = np.array(vec1)
    vec2_array = np.array(vec2)
    
    dot_product = np.dot(vec1_array, vec2_array)
    magnitude1 = np.linalg.norm(vec1_array)
    magnitude2 = np.linalg.norm(vec2_array)
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return float(dot_product / (magnitude1 * magnitude2))


async def fetch_chunks_from_indexing_run(run_id: str) -> List[Dict[str, Any]]:
    """Fetch all chunks from a specific indexing run"""
    print(f"📂 Fetching chunks from indexing run: {run_id}")
    
    db = get_supabase_admin_client()
    
    # Fetch chunks with embeddings (mimics current retrieval.py behavior)
    response = (
        db.table("document_chunks")
        .select("*")
        .eq("indexing_run_id", run_id)
        .not_.is_("embedding_1024", "null")
        .execute()
    )
    
    chunks = response.data
    print(f"✅ Found {len(chunks)} chunks with embeddings")
    
    # Parse embeddings from string format
    for chunk in chunks:
        embedding_str = chunk.get("embedding_1024")
        if embedding_str:
            try:
                # Parse string representation to list
                chunk["embedding_vector"] = ast.literal_eval(embedding_str)
            except (ValueError, SyntaxError) as e:
                print(f"⚠️ Failed to parse embedding for chunk {chunk['chunk_id']}: {e}")
                chunk["embedding_vector"] = None
    
    return chunks


async def analyze_query_similarity(
    query_text: str,
    chunks: List[Dict[str, Any]],
    voyage_client: VoyageEmbeddingClient
) -> Dict[str, Any]:
    """Analyze similarity between query and all chunks using Python cosine similarity"""
    
    print(f"\n🔍 Analyzing query: '{query_text}'")
    
    # Generate query embedding
    start_time = time.time()
    query_embedding = await voyage_client.get_embedding(query_text)
    embedding_time = (time.time() - start_time) * 1000
    print(f"✅ Query embedding generated in {embedding_time:.2f}ms")
    
    # Calculate similarities for all chunks (current pipeline method)
    start_time = time.time()
    similarities = []
    
    for chunk in chunks:
        if chunk.get("embedding_vector"):
            similarity = cosine_similarity(query_embedding, chunk["embedding_vector"])
            similarities.append({
                "chunk_id": chunk["chunk_id"],
                "similarity": similarity,
                "content": chunk["content"],
                "metadata": chunk.get("metadata", {}),
                "page_number": chunk.get("metadata", {}).get("page_number") if chunk.get("metadata") else None,
                "element_category": chunk.get("metadata", {}).get("element_category") if chunk.get("metadata") else None,
                "source_filename": chunk.get("metadata", {}).get("source_filename") if chunk.get("metadata") else None,
            })
    
    calculation_time = (time.time() - start_time) * 1000
    print(f"✅ Calculated {len(similarities)} similarities in {calculation_time:.2f}ms")
    
    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    
    # Calculate statistics
    similarity_scores = [s["similarity"] for s in similarities]
    stats = {
        "mean": float(np.mean(similarity_scores)),
        "median": float(np.median(similarity_scores)),
        "std": float(np.std(similarity_scores)),
        "min": float(np.min(similarity_scores)),
        "max": float(np.max(similarity_scores)),
        "percentile_25": float(np.percentile(similarity_scores, 25)),
        "percentile_75": float(np.percentile(similarity_scores, 75)),
        "above_0.7": sum(1 for s in similarity_scores if s > 0.7),
        "above_0.6": sum(1 for s in similarity_scores if s > 0.6),
        "above_0.5": sum(1 for s in similarity_scores if s > 0.5),
        "below_0.3": sum(1 for s in similarity_scores if s < 0.3),
    }
    
    # Get histogram data
    hist_counts, hist_bins = np.histogram(similarity_scores, bins=20, range=(0, 1))
    
    return {
        "query_text": query_text,
        "execution_time_ms": calculation_time,
        "embedding_time_ms": embedding_time,
        "chunks_processed": len(similarities),
        "top_10_results": similarities[:10],
        "bottom_5_results": similarities[-5:],
        "similarity_distribution": stats,
        "histogram_data": {
            "bins": hist_bins.tolist(),
            "counts": hist_counts.tolist()
        }
    }


def validate_embedding_quality(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate the quality of embeddings"""
    
    print("\n🔍 Validating embedding quality...")
    
    results = {
        "dimension_check": {
            "expected": 1024,
            "all_correct": True,
            "failures": []
        },
        "zero_vectors": {
            "count": 0,
            "chunk_ids": []
        },
        "norm_distribution": {},
        "parsing_errors": {
            "count": 0,
            "chunk_ids": []
        }
    }
    
    # Check dimensions and collect valid embeddings
    valid_embeddings = []
    for chunk in chunks:
        embedding = chunk.get("embedding_vector")
        
        if embedding is None:
            results["parsing_errors"]["count"] += 1
            results["parsing_errors"]["chunk_ids"].append(chunk["chunk_id"])
            continue
            
        if len(embedding) != 1024:
            results["dimension_check"]["all_correct"] = False
            results["dimension_check"]["failures"].append({
                "chunk_id": chunk["chunk_id"],
                "actual_dimension": len(embedding)
            })
            continue
        
        # Check for zero vectors
        if all(v == 0 for v in embedding):
            results["zero_vectors"]["count"] += 1
            results["zero_vectors"]["chunk_ids"].append(chunk["chunk_id"])
            continue
        
        valid_embeddings.append(embedding)
    
    # Calculate norm statistics
    if valid_embeddings:
        embeddings_array = np.array(valid_embeddings)
        norms = np.linalg.norm(embeddings_array, axis=1)
        
        results["norm_distribution"] = {
            "mean": float(np.mean(norms)),
            "std": float(np.std(norms)),
            "min": float(np.min(norms)),
            "max": float(np.max(norms)),
            "percentile_25": float(np.percentile(norms, 25)),
            "percentile_75": float(np.percentile(norms, 75))
        }
        
        # Find outliers (more than 2.5 std from mean)
        norm_mean = np.mean(norms)
        norm_std = np.std(norms)
        outliers = []
        
        for i, norm in enumerate(norms):
            if abs(norm - norm_mean) > 2.5 * norm_std:
                outliers.append({
                    "chunk_index": i,
                    "norm": float(norm),
                    "deviation": float(abs(norm - norm_mean) / norm_std)
                })
        
        results["norm_distribution"]["outliers"] = outliers
        results["norm_distribution"]["outlier_count"] = len(outliers)
    
    # Summary
    results["summary"] = {
        "total_chunks": len(chunks),
        "valid_embeddings": len(valid_embeddings),
        "invalid_embeddings": len(chunks) - len(valid_embeddings),
        "quality_score": len(valid_embeddings) / len(chunks) if chunks else 0
    }
    
    print(f"✅ Validation complete: {len(valid_embeddings)}/{len(chunks)} valid embeddings")
    
    return results


async def test_self_similarity(chunks: List[Dict[str, Any]], voyage_client: VoyageEmbeddingClient, sample_size: int = 5) -> Dict[str, Any]:
    """Test if re-embedding the same content produces similar embeddings"""
    
    print(f"\n🔍 Testing self-similarity with {sample_size} samples...")
    
    # Sample random chunks
    import random
    random.seed(42)  # For reproducibility
    sample_chunks = random.sample([c for c in chunks if c.get("embedding_vector")], min(sample_size, len(chunks)))
    
    results = []
    for chunk in sample_chunks:
        # Re-embed the content
        try:
            new_embedding = await voyage_client.get_embedding(chunk["content"])
            similarity = cosine_similarity(chunk["embedding_vector"], new_embedding)
            
            results.append({
                "chunk_id": chunk["chunk_id"],
                "content_preview": chunk["content"][:100] + "..." if len(chunk["content"]) > 100 else chunk["content"],
                "similarity": similarity
            })
            print(f"  Chunk {chunk['chunk_id']}: similarity = {similarity:.4f}")
        except Exception as e:
            print(f"  ⚠️ Failed to re-embed chunk {chunk['chunk_id']}: {e}")
    
    if results:
        avg_similarity = np.mean([r["similarity"] for r in results])
        status = "PASS" if avg_similarity > 0.95 else "WARNING" if avg_similarity > 0.90 else "FAIL"
    else:
        avg_similarity = 0
        status = "ERROR"
    
    return {
        "samples_tested": len(results),
        "results": results,
        "average_similarity": float(avg_similarity),
        "status": status
    }


def create_similarity_histogram(query_results: List[Dict[str, Any]], output_dir: Path):
    """Create histogram visualizations of similarity distributions"""
    
    print("\n📊 Creating similarity histograms...")
    
    fig, axes = plt.subplots(1, len(query_results), figsize=(6 * len(query_results), 5))
    
    if len(query_results) == 1:
        axes = [axes]
    
    for idx, result in enumerate(query_results):
        ax = axes[idx]
        
        # Get histogram data
        bins = result["histogram_data"]["bins"]
        counts = result["histogram_data"]["counts"]
        
        # Create bar chart
        bin_centers = [(bins[i] + bins[i+1])/2 for i in range(len(bins)-1)]
        ax.bar(bin_centers, counts, width=0.04, alpha=0.7, color='blue', edgecolor='black')
        
        # Add statistics lines
        stats = result["similarity_distribution"]
        ax.axvline(stats["mean"], color='red', linestyle='--', label=f'Mean: {stats["mean"]:.3f}')
        ax.axvline(stats["median"], color='green', linestyle='--', label=f'Median: {stats["median"]:.3f}')
        
        # Formatting
        ax.set_xlabel('Cosine Similarity')
        ax.set_ylabel('Number of Chunks')
        ax.set_title(f'Query: "{result["query_text"][:40]}..."')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Add text box with statistics
        textstr = f'Max: {stats["max"]:.3f}\n'
        textstr += f'Above 0.7: {stats["above_0.7"]}\n'
        textstr += f'Above 0.6: {stats["above_0.6"]}\n'
        textstr += f'Above 0.5: {stats["above_0.5"]}'
        
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=props)
    
    plt.tight_layout()
    
    # Save figure
    output_path = output_dir / "similarity_histograms.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Saved histogram to {output_path}")
    
    plt.close()


async def main():
    """Main execution function"""
    
    print("=" * 60)
    print("EMBEDDING QUALITY ANALYSIS")
    print("=" * 60)
    
    # Configuration
    INDEXING_RUN_ID = "1ed7dc55-25ea-4b37-8f03-33d9f7aeeff8"
    QUERIES = [
        "Hvor skal føringsvejene være?",
        "Hvor skal der installeres AIA anlæg?"
    ]
    
    # Create output directory
    output_dir = Path("embedding_analysis_output")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize Voyage client
    settings = get_settings()
    voyage_client = VoyageEmbeddingClient(
        api_key=settings.voyage_api_key,
        model="voyage-multilingual-2"
    )
    
    # Fetch chunks from database
    chunks = await fetch_chunks_from_indexing_run(INDEXING_RUN_ID)
    
    if not chunks:
        print("❌ No chunks found for the specified indexing run")
        return
    
    # Initialize results
    results = {
        "test_metadata": {
            "indexing_run_id": INDEXING_RUN_ID,
            "total_chunks": len(chunks),
            "timestamp": datetime.now().isoformat(),
            "voyage_model": "voyage-multilingual-2",
            "embedding_dimensions": 1024
        },
        "queries": [],
        "embedding_quality_validation": None,
        "self_similarity_test": None
    }
    
    # Analyze each query
    for query in QUERIES:
        query_result = await analyze_query_similarity(query, chunks, voyage_client)
        results["queries"].append(query_result)
    
    # Validate embedding quality
    results["embedding_quality_validation"] = validate_embedding_quality(chunks)
    
    # Test self-similarity
    results["self_similarity_test"] = await test_self_similarity(chunks, voyage_client, sample_size=5)
    
    # Create visualizations
    create_similarity_histogram(results["queries"], output_dir)
    
    # Performance comparison estimate
    results["performance_comparison"] = {
        "current_method": "Python cosine similarity on all chunks",
        "current_total_time_ms": sum(q["execution_time_ms"] for q in results["queries"]),
        "pgvector_hnsw_estimate": {
            "method": "HNSW index with <=> operator",
            "estimated_time_ms": 30,
            "potential_speedup": sum(q["execution_time_ms"] for q in results["queries"]) / 30,
            "note": "Index exists but not currently used in retrieval.py"
        }
    }
    
    # Save results to JSON
    output_file = output_dir / f"embedding_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Analysis complete! Results saved to {output_file}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for query_result in results["queries"]:
        print(f"\nQuery: '{query_result['query_text']}'")
        print(f"  Max similarity: {query_result['similarity_distribution']['max']:.3f}")
        print(f"  Mean similarity: {query_result['similarity_distribution']['mean']:.3f}")
        print(f"  Chunks above 0.6: {query_result['similarity_distribution']['above_0.6']}/{len(chunks)}")
        print(f"  Processing time: {query_result['execution_time_ms']:.2f}ms")
        
        if query_result['top_10_results']:
            print(f"\n  Top result (similarity: {query_result['top_10_results'][0]['similarity']:.3f}):")
            print(f"    Content: {query_result['top_10_results'][0]['content'][:200]}...")
            print(f"    Page: {query_result['top_10_results'][0]['page_number']}")
    
    print(f"\nEmbedding Quality:")
    print(f"  Valid embeddings: {results['embedding_quality_validation']['summary']['valid_embeddings']}/{len(chunks)}")
    print(f"  Self-similarity: {results['self_similarity_test']['average_similarity']:.4f} ({results['self_similarity_test']['status']})")
    
    print(f"\nPerformance:")
    print(f"  Current method: {results['performance_comparison']['current_total_time_ms']:.2f}ms")
    print(f"  Potential with HNSW: ~{results['performance_comparison']['pgvector_hnsw_estimate']['estimated_time_ms']}ms")
    print(f"  Potential speedup: {results['performance_comparison']['pgvector_hnsw_estimate']['potential_speedup']:.1f}x")


if __name__ == "__main__":
    asyncio.run(main())