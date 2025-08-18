#!/usr/bin/env python3
"""
Test script to validate the critical priority pipeline improvements.

This script will:
1. Process the same Guldberg documents with the new chunking pipeline
2. Compare chunk statistics to identify improvements  
3. Test Danish similarity thresholds with sample queries
4. Measure performance improvements
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from uuid import uuid4

import sys
sys.path.append('/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/backend')

from src.pipeline.indexing.steps.chunking import IntelligentChunker
from src.pipeline.querying.steps.retrieval import DocumentRetriever, RetrievalConfig
from src.config.database import get_supabase_admin_client
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PipelineImprovementTester:
    """Test the pipeline improvements against the original problematic documents"""
    
    def __init__(self):
        self.db = get_supabase_admin_client()
        
        # Load pipeline configuration directly from JSON
        config_path = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/backend/src/config/pipeline/pipeline_config.json"
        with open(config_path) as f:
            self.pipeline_config = json.load(f)
        
        self.chunking_config = self.pipeline_config["indexing"]["chunking"]
        self.retrieval_config = RetrievalConfig(
            self.pipeline_config["query"]["retrieval"]
        )
        
        # Initialize chunkers for comparison
        self.old_chunker = IntelligentChunker({
            **self.chunking_config,
            "strategy": "element_based",  # Old behavior
            "min_chunk_size": None,       # Disabled merging
        })
        
        self.new_chunker = IntelligentChunker(self.chunking_config)  # New behavior
        
        # Original problematic indexing run ID from analysis
        self.original_run_id = "1ed7dc55-25ea-4b37-8f03-33d9f7aeeff8"
        
        # Test queries from the original analysis
        self.test_queries = [
            "Hvor skal føringsvejene være?",
            "Hvor skal der installeres AIA anlæg?",
            "Hvad er kravene til elektriske installationer?",
        ]

    async def run_comprehensive_test(self):
        """Run the complete test suite"""
        print("🚀 PIPELINE IMPROVEMENT VALIDATION TEST")
        print("=" * 60)
        
        results = {}
        
        # Test 1: Chunk Quality Comparison
        print("\n📊 TEST 1: Chunk Quality Analysis")
        results["chunk_comparison"] = await self.test_chunk_quality()
        
        # Test 2: Similarity Threshold Testing  
        print("\n🎯 TEST 2: Danish Similarity Thresholds")
        results["similarity_test"] = await self.test_similarity_thresholds()
        
        # Test 3: Performance Benchmarking
        print("\n⚡ TEST 3: Retrieval Performance")
        results["performance_test"] = await self.test_retrieval_performance()
        
        # Generate final report
        print("\n📋 FINAL REPORT")
        await self.generate_test_report(results)
        
        return results

    async def test_chunk_quality(self):
        """Compare chunk quality between old and new approaches"""
        print("Loading original partition data from problematic run...")
        
        # Get original partition data from database
        original_data = await self.load_original_partition_data()
        if not original_data:
            print("❌ Could not load original partition data")
            return {"error": "Could not load original data"}
        
        print(f"✅ Loaded partition data: {len(original_data.get('text_elements', []))} text elements")
        
        # Test old chunking approach
        print("\n🔄 Testing OLD chunking approach...")
        old_chunks, old_stats = self.old_chunker.create_final_chunks(
            original_data.get("text_elements", [])
        )
        old_analysis = self.old_chunker.analyze_chunks(old_chunks)
        
        # Test new chunking approach  
        print("🔄 Testing NEW chunking approach...")
        new_chunks, new_stats = self.new_chunker.create_final_chunks(
            original_data.get("text_elements", [])
        )
        new_analysis = self.new_chunker.analyze_chunks(new_chunks)
        
        # Compare results
        comparison = self.compare_chunk_analyses(old_analysis, new_analysis, old_stats, new_stats)
        
        # Print summary
        self.print_chunk_comparison(comparison)
        
        return {
            "old_analysis": old_analysis,
            "new_analysis": new_analysis, 
            "old_stats": old_stats,
            "new_stats": new_stats,
            "comparison": comparison
        }

    async def test_similarity_thresholds(self):
        """Test the adjusted Danish similarity thresholds"""
        print("Testing similarity thresholds with Danish construction queries...")
        
        # Create retriever with old thresholds
        old_config = RetrievalConfig({
            **self.retrieval_config.__dict__,
            "danish_thresholds": {"excellent": 0.70, "good": 0.55, "acceptable": 0.35, "minimum": 0.20}
        })
        old_retriever = DocumentRetriever(old_config, use_admin=True)
        
        # Create retriever with new thresholds  
        new_retriever = DocumentRetriever(self.retrieval_config, use_admin=True)
        
        results = {}
        
        for query in self.test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            
            # Test with old thresholds
            try:
                old_embedding = await old_retriever.embed_query(query)
                old_results = await old_retriever.search_pgvector(
                    old_embedding, self.original_run_id
                )
                old_count = len(old_results)
                old_max_sim = max([r.get("similarity_score", 0) for r in old_results]) if old_results else 0
            except Exception as e:
                print(f"❌ Old threshold test failed: {e}")
                old_count, old_max_sim = 0, 0
                
            # Test with new thresholds
            try:
                new_embedding = await new_retriever.embed_query(query) 
                new_results = await new_retriever.search_pgvector(
                    new_embedding, self.original_run_id
                )
                new_count = len(new_results)
                new_max_sim = max([r.get("similarity_score", 0) for r in new_results]) if new_results else 0
            except Exception as e:
                print(f"❌ New threshold test failed: {e}")
                new_count, new_max_sim = 0, 0
            
            results[query] = {
                "old_thresholds": {"count": old_count, "max_similarity": old_max_sim},
                "new_thresholds": {"count": new_count, "max_similarity": new_max_sim},
                "improvement": new_count - old_count
            }
            
            print(f"  📊 Old thresholds: {old_count} results, max sim: {old_max_sim:.3f}")
            print(f"  📊 New thresholds: {new_count} results, max sim: {new_max_sim:.3f}")
            print(f"  ➡️  Improvement: +{new_count - old_count} results")
        
        return results

    async def test_retrieval_performance(self):
        """Benchmark retrieval performance improvements"""
        print("Benchmarking retrieval performance...")
        
        retriever = DocumentRetriever(self.retrieval_config, use_admin=True)
        test_query = self.test_queries[0]
        
        # Get embedding once
        embedding = await retriever.embed_query(test_query)
        
        # Benchmark multiple search approaches
        results = {}
        iterations = 3
        
        # Test Python-based similarity (fallback method)
        print("🐌 Testing Python-based similarity...")
        python_times = []
        for i in range(iterations):
            start = time.time()
            python_results = await retriever._fallback_python_similarity(
                embedding, self.original_run_id
            )
            python_times.append(time.time() - start)
        
        results["python_similarity"] = {
            "avg_time": sum(python_times) / len(python_times),
            "result_count": len(python_results),
            "times": python_times
        }
        
        # Test new pgvector approach
        print("🚀 Testing pgvector HNSW approach...")
        pgvector_times = []
        for i in range(iterations):
            start = time.time()
            pgvector_results = await retriever.search_pgvector(
                embedding, self.original_run_id
            )
            pgvector_times.append(time.time() - start)
        
        results["pgvector_hnsw"] = {
            "avg_time": sum(pgvector_times) / len(pgvector_times),
            "result_count": len(pgvector_results),
            "times": pgvector_times
        }
        
        # Calculate improvement
        if results["python_similarity"]["avg_time"] > 0:
            speedup = results["python_similarity"]["avg_time"] / results["pgvector_hnsw"]["avg_time"]
            results["speedup"] = speedup
            print(f"⚡ Performance improvement: {speedup:.2f}x faster")
        
        return results

    async def load_original_partition_data(self):
        """Load the original partition data from the problematic indexing run"""
        try:
            # Query the indexing run from database
            response = self.db.table("indexing_runs").select("step_results").eq("id", self.original_run_id).execute()
            
            if not response.data:
                return None
                
            step_results = response.data[0]["step_results"]
            partition_result = step_results.get("partition", {})
            
            # Handle both dict and StepResult objects
            if isinstance(partition_result, dict):
                return partition_result.get("data", {})
            else:
                # It might be stored as JSON string
                if hasattr(partition_result, "data"):
                    return partition_result.data
                    
            return None
            
        except Exception as e:
            logger.error(f"Failed to load original partition data: {e}")
            return None

    def compare_chunk_analyses(self, old_analysis, new_analysis, old_stats, new_stats):
        """Compare the chunk analyses to identify improvements"""
        comparison = {}
        
        # Chunk count comparison
        comparison["chunk_count"] = {
            "old": old_analysis["total_chunks"],
            "new": new_analysis["total_chunks"],
            "change": new_analysis["total_chunks"] - old_analysis["total_chunks"]
        }
        
        # Size distribution comparison
        comparison["size_distribution"] = {
            "old": old_analysis["chunk_size_distribution"],
            "new": new_analysis["chunk_size_distribution"]
        }
        
        # Critical metric: very small chunks (<50 chars)
        old_tiny = len([c for c in old_analysis.get("shortest_chunks", []) if c["size"] < 50])
        new_tiny = len([c for c in new_analysis.get("shortest_chunks", []) if c["size"] < 50])
        
        comparison["tiny_chunks"] = {
            "old": old_tiny,
            "new": new_tiny,
            "reduction": old_tiny - new_tiny,
            "reduction_percent": ((old_tiny - new_tiny) / max(old_tiny, 1)) * 100
        }
        
        # Average chunk size
        comparison["avg_size"] = {
            "old": old_analysis["average_chars_per_chunk"],
            "new": new_analysis["average_chars_per_chunk"],
            "improvement": new_analysis["average_chars_per_chunk"] - old_analysis["average_chars_per_chunk"]
        }
        
        # Processing stats
        comparison["processing_stats"] = {
            "old": old_stats,
            "new": new_stats
        }
        
        return comparison

    def print_chunk_comparison(self, comparison):
        """Print a formatted comparison of chunk analyses"""
        print("\n📊 CHUNK QUALITY COMPARISON")
        print("-" * 40)
        
        # Chunk counts
        cc = comparison["chunk_count"]
        print(f"Total Chunks: {cc['old']} → {cc['new']} ({cc['change']:+d})")
        
        # Tiny chunks (the critical issue)
        tc = comparison["tiny_chunks"] 
        print(f"Tiny Chunks (<50 chars): {tc['old']} → {tc['new']} ({tc['reduction']:+d})")
        print(f"Tiny Chunk Reduction: {tc['reduction_percent']:.1f}%")
        
        # Average size
        avg = comparison["avg_size"]
        print(f"Average Size: {avg['old']:.0f} → {avg['new']:.0f} chars ({avg['improvement']:+.0f})")
        
        # Size distribution
        old_sizes = comparison["size_distribution"]["old"]
        new_sizes = comparison["size_distribution"]["new"] 
        print(f"Small chunks: {old_sizes['small']} → {new_sizes['small']}")
        print(f"Medium chunks: {old_sizes['medium']} → {new_sizes['medium']}")
        print(f"Large chunks: {old_sizes['large']} → {new_sizes['large']}")
        
        # Processing improvements
        new_stats = comparison["processing_stats"]["new"]
        if "splitting_stats" in new_stats and new_stats["splitting_stats"]["semantic_splitting_enabled"]:
            ss = new_stats["splitting_stats"]
            print(f"Semantic Splitting: {ss['elements_split']} elements split into {ss['total_new_chunks']} chunks")
        
        if "merging_stats" in new_stats and new_stats["merging_stats"]["merging_enabled"]:
            ms = new_stats["merging_stats"] 
            print(f"Chunk Merging: {ms['small_elements_found']} small elements merged into {ms['merge_groups_created']} groups")

    async def generate_test_report(self, results):
        """Generate a final test report"""
        print("=" * 60)
        
        # Chunk quality summary
        if "chunk_comparison" in results:
            comp = results["chunk_comparison"]["comparison"]
            tc_reduction = comp["tiny_chunks"]["reduction_percent"]
            print(f"✅ Tiny Chunk Reduction: {tc_reduction:.1f}% improvement")
            
        # Similarity threshold summary  
        if "similarity_test" in results:
            total_improvement = sum([
                r["improvement"] for r in results["similarity_test"].values()
            ])
            print(f"✅ Query Results: +{total_improvement} additional results across test queries")
            
        # Performance summary
        if "performance_test" in results and "speedup" in results["performance_test"]:
            speedup = results["performance_test"]["speedup"]
            print(f"✅ Retrieval Speed: {speedup:.2f}x faster with pgvector")
            
        print("=" * 60)
        print("🎉 PIPELINE IMPROVEMENT TEST COMPLETE!")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"pipeline_improvement_test_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        print(f"📄 Detailed results saved to: {output_file}")

async def main():
    """Main test execution"""
    tester = PipelineImprovementTester()
    
    try:
        results = await tester.run_comprehensive_test()
        return results
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(main())