#!/usr/bin/env python
"""
Comprehensive retrieval testing tool for optimizing the RAG system.

Usage:
    python test_retrieval_optimization.py "Your query here" [--run-id RUN_ID] [--method METHOD]
    
Methods:
    - hnsw: HNSW index search (default)
    - ivfflat: IVFFlat/Python fallback
    - hybrid: 80% semantic + 20% keyword
    - rerank: Semantic search with reranking
    - hyde: Hypothetical Document Embedding
    - all: Test all methods
"""

import asyncio
import csv
import sys
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_supabase_admin_client
from src.pipeline.shared.retrieval_core import RetrievalCore
from src.pipeline.shared.retrieval_config import SharedRetrievalConfig
from src.pipeline.shared.embedding_service import VoyageEmbeddingService
from src.pipeline.shared.similarity_service import SimilarityService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RetrievalTester:
    """Test various retrieval strategies"""
    
    def __init__(self, indexing_run_id: Optional[str] = None):
        self.db = get_supabase_admin_client()
        self.indexing_run_id = indexing_run_id
        self.embedding_service = VoyageEmbeddingService()
        
        # Create config with no thresholds for testing
        self.config = SharedRetrievalConfig(
            top_k=30,  # Always get top 30
            similarity_thresholds={
                "excellent": 0.0,
                "good": 0.0, 
                "acceptable": 0.0,
                "minimum": 0.0  # No threshold filtering
            },
            danish_thresholds={
                "excellent": 0.0,
                "good": 0.0,
                "acceptable": 0.0,
                "minimum": 0.0  # No threshold filtering
            }
        )
        
        self.retrieval_core = RetrievalCore(self.config, self.db, self.embedding_service)
        self.similarity_service = SimilarityService(self.config)
    
    async def test_hnsw(self, query: str) -> List[Dict[str, Any]]:
        """Test HNSW index search"""
        logger.info("🔍 Testing HNSW retrieval...")
        
        # Generate embedding
        query_embedding = await self.retrieval_core.generate_query_embedding(query)
        
        # Search with HNSW (no threshold)
        results = await self.retrieval_core.search_pgvector_hnsw(
            query_embedding=query_embedding,
            indexing_run_id=self.indexing_run_id,
            similarity_threshold=0.0  # No threshold
        )
        
        # Limit to top 30
        return results[:30]
    
    async def test_ivfflat(self, query: str) -> List[Dict[str, Any]]:
        """Test IVFFlat/Python fallback search"""
        logger.info("🐍 Testing IVFFlat/Python retrieval...")
        
        # Generate embedding
        query_embedding = await self.retrieval_core.generate_query_embedding(query)
        
        # Use Python fallback (which mimics IVFFlat behavior)
        results = await self.retrieval_core.search_pgvector_fallback(
            query_embedding=query_embedding,
            indexing_run_id=self.indexing_run_id
        )
        
        # Limit to top 30
        return results[:30]
    
    async def test_hybrid_search(self, query: str, semantic_weight: float = 0.8) -> List[Dict[str, Any]]:
        """Test hybrid search (semantic + keyword)"""
        logger.info(f"🔄 Testing hybrid search (semantic: {semantic_weight*100}%, keyword: {(1-semantic_weight)*100}%)...")
        
        # Generate embedding for semantic search
        query_embedding = await self.retrieval_core.generate_query_embedding(query)
        
        # Get semantic results
        semantic_results = await self.retrieval_core.search_pgvector_hnsw(
            query_embedding=query_embedding,
            indexing_run_id=self.indexing_run_id,
            similarity_threshold=0.0
        )
        
        # Perform keyword search
        keyword_results = await self._keyword_search(query)
        
        # Combine and rerank results
        combined_results = self._combine_results(
            semantic_results[:50],  # Get more for merging
            keyword_results[:50],
            semantic_weight=semantic_weight
        )
        
        return combined_results[:30]
    
    async def _keyword_search(self, query: str) -> List[Dict[str, Any]]:
        """Perform keyword-based search using full-text search"""
        logger.info("📝 Performing keyword search...")
        
        # Split query into words for better matching
        search_terms = query.lower().split()
        
        # Build the query with OR conditions for each term
        query_conditions = " | ".join(search_terms)
        
        try:
            # Use Supabase full-text search on content
            response = self.db.table("document_chunks").select(
                "id,content,metadata,embedding_1024,document_id,indexing_run_id"
            ).text_search("content", query_conditions)
            
            if self.indexing_run_id:
                response = response.eq("indexing_run_id", self.indexing_run_id)
            
            response = response.limit(50).execute()
            
            results = []
            for chunk in response.data:
                # Calculate a simple keyword relevance score
                content_lower = chunk["content"].lower()
                keyword_score = sum(1 for term in search_terms if term in content_lower) / len(search_terms)
                
                results.append({
                    "id": chunk["id"],
                    "content": chunk["content"],
                    "metadata": chunk.get("metadata", {}),
                    "similarity_score": keyword_score,  # Use keyword relevance as score
                    "document_id": chunk.get("document_id"),
                    "indexing_run_id": chunk.get("indexing_run_id"),
                    "search_type": "keyword"
                })
            
            # Sort by keyword score
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    def _combine_results(
        self, 
        semantic_results: List[Dict], 
        keyword_results: List[Dict],
        semantic_weight: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Combine semantic and keyword results with weighted scoring"""
        combined = {}
        keyword_weight = 1 - semantic_weight
        
        # Add semantic results
        for i, result in enumerate(semantic_results):
            chunk_id = result["id"]
            # Use rank-based scoring: 1.0 for first, decreasing linearly
            rank_score = 1.0 - (i / len(semantic_results))
            combined[chunk_id] = {
                **result,
                "semantic_score": result["similarity_score"],
                "semantic_rank_score": rank_score,
                "keyword_score": 0,
                "keyword_rank_score": 0,
                "combined_score": semantic_weight * rank_score
            }
        
        # Add/update with keyword results
        for i, result in enumerate(keyword_results):
            chunk_id = result["id"]
            rank_score = 1.0 - (i / len(keyword_results))
            
            if chunk_id in combined:
                # Update existing entry
                combined[chunk_id]["keyword_score"] = result["similarity_score"]
                combined[chunk_id]["keyword_rank_score"] = rank_score
                combined[chunk_id]["combined_score"] = (
                    semantic_weight * combined[chunk_id]["semantic_rank_score"] +
                    keyword_weight * rank_score
                )
            else:
                # Add new entry from keyword search
                combined[chunk_id] = {
                    **result,
                    "semantic_score": 0,
                    "semantic_rank_score": 0,
                    "keyword_score": result["similarity_score"],
                    "keyword_rank_score": rank_score,
                    "combined_score": keyword_weight * rank_score
                }
        
        # Convert to list and sort by combined score
        results = list(combined.values())
        results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        return results
    
    async def test_with_reranking(self, query: str) -> List[Dict[str, Any]]:
        """Test semantic search with cross-encoder reranking"""
        logger.info("🎯 Testing with reranking...")
        
        # Get initial results (top 50 for reranking)
        query_embedding = await self.retrieval_core.generate_query_embedding(query)
        initial_results = await self.retrieval_core.search_pgvector_hnsw(
            query_embedding=query_embedding,
            indexing_run_id=self.indexing_run_id,
            similarity_threshold=0.0
        )
        
        # Take top 50 for reranking
        candidates = initial_results[:50]
        
        # Simple reranking based on query terms overlap
        reranked = self._simple_rerank(query, candidates)
        
        return reranked[:30]
    
    def _simple_rerank(self, query: str, candidates: List[Dict]) -> List[Dict]:
        """Simple reranking based on query term overlap"""
        query_terms = set(query.lower().split())
        
        for candidate in candidates:
            content_terms = set(candidate["content"].lower().split())
            # Calculate Jaccard similarity
            overlap = len(query_terms & content_terms)
            union = len(query_terms | content_terms)
            rerank_score = overlap / union if union > 0 else 0
            
            # Combine with original similarity
            candidate["rerank_score"] = rerank_score
            candidate["final_score"] = (
                0.7 * candidate["similarity_score"] + 
                0.3 * rerank_score
            )
        
        # Sort by final score
        candidates.sort(key=lambda x: x["final_score"], reverse=True)
        return candidates
    
    async def test_hyde(self, query: str) -> List[Dict[str, Any]]:
        """Test Hypothetical Document Embedding (HyDE)"""
        logger.info("📄 Testing HyDE retrieval...")
        
        # Generate a hypothetical answer
        hypothetical = self._generate_hypothetical_answer(query)
        logger.info(f"Generated hypothetical: {hypothetical[:100]}...")
        
        # Embed the hypothetical answer
        hyde_embedding = await self.retrieval_core.generate_query_embedding(hypothetical)
        
        # Search with HyDE embedding
        results = await self.retrieval_core.search_pgvector_hnsw(
            query_embedding=hyde_embedding,
            indexing_run_id=self.indexing_run_id,
            similarity_threshold=0.0
        )
        
        return results[:30]
    
    def _generate_hypothetical_answer(self, query: str) -> str:
        """Generate a simple hypothetical answer for HyDE"""
        # Simple template-based generation (in production, use LLM)
        templates = {
            "hvad": f"Dette dokument beskriver {query}. Det indeholder detaljerede oplysninger om emnet.",
            "hvordan": f"For at udføre {query}, skal man følge disse trin i byggeprojektet.",
            "hvornår": f"Tidsplanen for {query} er specificeret i projektdokumentationen.",
            "hvor": f"Placeringen for {query} er angivet i de tekniske tegninger.",
        }
        
        # Default template
        default = f"Dette afsnit omhandler {query} i forhold til byggeprojektet. Det indeholder relevante specifikationer, krav og retningslinjer."
        
        # Simple keyword matching
        for keyword, template in templates.items():
            if keyword in query.lower():
                return template
        
        return default
    
    def save_results_to_csv(
        self, 
        results: Dict[str, List[Dict]], 
        query: str,
        output_dir: str = "retrieval_test_results"
    ):
        """Save results to CSV files"""
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save each method's results
        for method, method_results in results.items():
            filename = output_path / f"{timestamp}_{method}_results.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'rank', 'chunk_id', 'similarity_score', 'document_id', 
                    'source_filename', 'page_number', 'content_preview'
                ]
                
                # Add extra fields for hybrid search
                if method == 'hybrid':
                    fieldnames.extend(['semantic_score', 'keyword_score', 'combined_score'])
                elif method == 'rerank':
                    fieldnames.extend(['rerank_score', 'final_score'])
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, result in enumerate(method_results, 1):
                    row = {
                        'rank': i,
                        'chunk_id': result.get('id'),
                        'similarity_score': f"{result.get('similarity_score', 0):.4f}",
                        'document_id': result.get('document_id', ''),
                        'source_filename': result.get('metadata', {}).get('source_filename', ''),
                        'page_number': result.get('metadata', {}).get('page_number', ''),
                        'content_preview': result.get('content', '')[:200].replace('\n', ' ')
                    }
                    
                    # Add method-specific fields
                    if method == 'hybrid':
                        row['semantic_score'] = f"{result.get('semantic_score', 0):.4f}"
                        row['keyword_score'] = f"{result.get('keyword_score', 0):.4f}"
                        row['combined_score'] = f"{result.get('combined_score', 0):.4f}"
                    elif method == 'rerank':
                        row['rerank_score'] = f"{result.get('rerank_score', 0):.4f}"
                        row['final_score'] = f"{result.get('final_score', 0):.4f}"
                    
                    writer.writerow(row)
            
            logger.info(f"✅ Saved {method} results to {filename}")
        
        # Save summary
        summary_file = output_path / f"{timestamp}_summary.json"
        summary = {
            "query": query,
            "timestamp": timestamp,
            "indexing_run_id": self.indexing_run_id,
            "methods_tested": list(results.keys()),
            "results_count": {method: len(res) for method, res in results.items()},
            "top_results": {
                method: {
                    "top_1": res[0]["content"][:100] if res else None,
                    "top_1_score": res[0].get("similarity_score", 0) if res else 0
                }
                for method, res in results.items()
            }
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Summary saved to {summary_file}")
        
        return output_path


async def main():
    parser = argparse.ArgumentParser(description='Test retrieval strategies for RAG optimization')
    parser.add_argument('query', help='Query to test')
    parser.add_argument('--run-id', help='Indexing run ID to filter results')
    parser.add_argument('--method', 
                       choices=['hnsw', 'ivfflat', 'hybrid', 'rerank', 'hyde', 'all'],
                       default='all',
                       help='Retrieval method to test')
    parser.add_argument('--semantic-weight', type=float, default=0.8,
                       help='Weight for semantic search in hybrid mode (0-1)')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = RetrievalTester(indexing_run_id=args.run_id)
    
    results = {}
    
    # Run selected tests
    if args.method == 'all' or args.method == 'hnsw':
        results['hnsw'] = await tester.test_hnsw(args.query)
        logger.info(f"HNSW found {len(results['hnsw'])} results")
    
    if args.method == 'all' or args.method == 'ivfflat':
        results['ivfflat'] = await tester.test_ivfflat(args.query)
        logger.info(f"IVFFlat found {len(results['ivfflat'])} results")
    
    if args.method == 'all' or args.method == 'hybrid':
        results['hybrid'] = await tester.test_hybrid_search(args.query, args.semantic_weight)
        logger.info(f"Hybrid found {len(results['hybrid'])} results")
    
    if args.method == 'all' or args.method == 'rerank':
        results['rerank'] = await tester.test_with_reranking(args.query)
        logger.info(f"Reranking found {len(results['rerank'])} results")
    
    if args.method == 'all' or args.method == 'hyde':
        results['hyde'] = await tester.test_hyde(args.query)
        logger.info(f"HyDE found {len(results['hyde'])} results")
    
    # Save results
    output_path = tester.save_results_to_csv(results, args.query)
    
    # Print summary
    print("\n" + "="*60)
    print("RETRIEVAL TEST SUMMARY")
    print("="*60)
    print(f"Query: {args.query}")
    print(f"Indexing Run ID: {args.run_id or 'All runs'}")
    print(f"Results saved to: {output_path}")
    print("\nTop result from each method:")
    
    for method, method_results in results.items():
        if method_results:
            top_result = method_results[0]
            print(f"\n{method.upper()}:")
            print(f"  Score: {top_result.get('similarity_score', 0):.4f}")
            print(f"  Source: {top_result.get('metadata', {}).get('source_filename', 'Unknown')}")
            print(f"  Content: {top_result['content'][:100]}...")


if __name__ == "__main__":
    asyncio.run(main())