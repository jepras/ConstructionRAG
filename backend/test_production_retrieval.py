#!/usr/bin/env python
"""
Production-exact retrieval comparison tool.
Tests HNSW vs Python similarity exactly as implemented in production.

Usage:
    python test_production_retrieval.py "Your query here" [--run-id RUN_ID]
"""

import asyncio
import sys
import argparse
import logging
import ast
import math
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_supabase_admin_client
from src.pipeline.shared.embedding_service import VoyageEmbeddingService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ProductionRetrievalTester:
    """Test production retrieval methods exactly as implemented"""
    
    def __init__(self, indexing_run_id: Optional[str] = None):
        self.db = get_supabase_admin_client()
        self.indexing_run_id = indexing_run_id
        self.embedding_service = VoyageEmbeddingService()
    
    async def test_hnsw_exact(self, query: str, top_k: int = 15) -> List[Dict[str, Any]]:
        """
        Test HNSW search exactly as in production RetrievalCore.search_pgvector_hnsw
        but without thresholds or post-processing
        """
        logger.info("🔍 Testing HNSW (production exact)...")
        
        # Generate embedding exactly as production
        query_embedding = await self.embedding_service.get_embedding(query)
        
        # Validate embedding dimensions
        if not self.embedding_service.validate_embedding(query_embedding):
            logger.warning(
                f"Query embedding dimension mismatch: got {len(query_embedding)}, "
                f"expected {self.embedding_service.expected_dimensions}"
            )
        
        try:
            # Prepare RPC parameters exactly as production
            rpc_params = {
                'query_embedding': query_embedding,
                'match_threshold': 0.0,  # No threshold
                'match_count': top_k,     # Get exactly top_k results
            }
            
            # Add indexing run filter if specified
            if self.indexing_run_id:
                rpc_params['indexing_run_id_filter'] = self.indexing_run_id
                logger.info(f"🔍 Filtering to indexing run: {self.indexing_run_id}")
            
            # Execute HNSW search using exact production RPC
            hnsw_start = datetime.utcnow()
            response = self.db.rpc('match_chunks', rpc_params).execute()
            hnsw_duration = (datetime.utcnow() - hnsw_start).total_seconds() * 1000
            
            results = response.data if response.data else []
            logger.info(f"🔍 HNSW search completed in {hnsw_duration:.1f}ms - {len(results)} results")
            
            # Calculate similarity scores for each result
            formatted_results = []
            for result in results:
                # Calculate actual cosine similarity
                chunk_embedding = self._parse_embedding(result.get("embedding_1024"))
                if chunk_embedding:
                    similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                else:
                    similarity = 0.0
                
                formatted_results.append({
                    "id": result["id"],
                    "content": result["content"],
                    "metadata": result.get("metadata", {}),
                    "similarity_score": similarity,
                    "document_id": result.get("document_id"),
                    "indexing_run_id": result.get("indexing_run_id")
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"🔍 HNSW search failed: {e}")
            return []
    
    async def test_python_similarity_exact(self, query: str, top_k: int = 15) -> List[Dict[str, Any]]:
        """
        Test Python similarity exactly as in production RetrievalCore.search_pgvector_fallback
        but without thresholds or post-processing
        """
        logger.info("🐍 Testing Python similarity (production exact)...")
        
        # Generate embedding exactly as production
        query_embedding = await self.embedding_service.get_embedding(query)
        
        # Build query exactly as production
        query_builder = (
            self.db.table("document_chunks")
            .select("id,content,metadata,embedding_1024,document_id,indexing_run_id")
            .not_.is_("embedding_1024", "null")
        )
        
        # Apply filters exactly as production
        if self.indexing_run_id:
            query_builder = query_builder.eq("indexing_run_id", self.indexing_run_id)
        
        # Execute query
        python_start = datetime.utcnow()
        response = query_builder.execute()
        chunks = response.data
        
        results_with_scores = []
        
        # Calculate similarities in Python exactly as production
        for chunk in chunks:
            if chunk.get("embedding_1024"):
                chunk_embedding = self._parse_embedding(chunk["embedding_1024"])
                if chunk_embedding:
                    similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                    
                    results_with_scores.append({
                        "id": chunk["id"],
                        "content": chunk["content"],
                        "metadata": chunk["metadata"],
                        "similarity_score": similarity,
                        "document_id": chunk.get("document_id"),
                        "indexing_run_id": chunk.get("indexing_run_id")
                    })
        
        # Sort by similarity (highest first) exactly as production
        results_with_scores.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        python_duration = (datetime.utcnow() - python_start).total_seconds() * 1000
        logger.info(f"🐍 Python similarity completed in {python_duration:.1f}ms - {len(results_with_scores[:top_k])} results")
        
        # Return top results
        return results_with_scores[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity exactly as in production SimilarityService
        """
        if len(vec1) != len(vec2):
            logger.warning(f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}")
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
    
    def _parse_embedding(self, embedding_str: str) -> Optional[List[float]]:
        """
        Parse embedding string exactly as in production RetrievalCore
        """
        if not embedding_str:
            return None
        
        try:
            # Handle both string and list formats
            if isinstance(embedding_str, str):
                embedding = ast.literal_eval(embedding_str)
            else:
                embedding = embedding_str
            
            # Ensure it's a list of floats
            if isinstance(embedding, list):
                return [float(x) for x in embedding]
            else:
                return None
                
        except (ValueError, SyntaxError) as e:
            logger.warning(f"Failed to parse embedding: {e}")
            return None
    
    def generate_html_comparison(
        self,
        query: str,
        hnsw_results: List[Dict[str, Any]],
        python_results: List[Dict[str, Any]],
        output_file: str = None
    ) -> str:
        """Generate HTML file with side-by-side comparison"""
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"retrieval_comparison_{timestamp}.html"
        
        # Create HTML content
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Retrieval Method Comparison</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .query-info {{
            background-color: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .timestamp {{
            color: #666;
            font-size: 0.9em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            padding: 12px;
            text-align: left;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #ddd;
            vertical-align: top;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .rank {{
            font-weight: bold;
            color: #4CAF50;
            width: 50px;
        }}
        .content {{
            max-width: 45%;
            word-wrap: break-word;
            white-space: pre-wrap;
            font-size: 0.9em;
            line-height: 1.4;
        }}
        .score {{
            font-weight: bold;
            color: #2196F3;
            display: inline-block;
            background-color: #e3f2fd;
            padding: 2px 6px;
            border-radius: 3px;
            margin-bottom: 8px;
        }}
        .metadata {{
            font-size: 0.8em;
            color: #666;
            margin-top: 8px;
        }}
        .match {{
            background-color: #fff3cd;
        }}
        .no-results {{
            color: #999;
            font-style: italic;
        }}
        .stats {{
            margin-top: 20px;
            padding: 15px;
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <h1>🔍 Retrieval Method Comparison</h1>
    
    <div class="query-info">
        <strong>Query:</strong> {query}<br>
        <span class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span><br>
        <span class="timestamp">Indexing Run ID: {self.indexing_run_id or 'All runs'}</span>
    </div>
    
    <table>
        <thead>
            <tr>
                <th style="width: 50px;">Rank</th>
                <th style="width: 50%;">HNSW Search</th>
                <th style="width: 50%;">Python Similarity</th>
            </tr>
        </thead>
        <tbody>
"""
        
        # Determine max rows
        max_rows = max(len(hnsw_results), len(python_results))
        
        # Create comparison rows
        for i in range(max_rows):
            rank = i + 1
            hnsw_result = hnsw_results[i] if i < len(hnsw_results) else None
            python_result = python_results[i] if i < len(python_results) else None
            
            # Check if both results are the same chunk
            is_match = (hnsw_result and python_result and 
                       hnsw_result.get('id') == python_result.get('id'))
            
            row_class = 'match' if is_match else ''
            
            html_content += f'            <tr class="{row_class}">\n'
            html_content += f'                <td class="rank">{rank}</td>\n'
            
            # HNSW column
            html_content += '                <td class="content">\n'
            if hnsw_result:
                score = hnsw_result.get('similarity_score', 0)
                content = hnsw_result.get('content', '')
                metadata = hnsw_result.get('metadata', {})
                doc_id = hnsw_result.get('document_id', '')
                chunk_id = hnsw_result.get('id', '')
                
                html_content += f'                    <div class="score">Score: {score:.4f}</div>\n'
                html_content += f'                    {self._escape_html(content)}\n'
                html_content += f'                    <div class="metadata">\n'
                html_content += f'                        <strong>Chunk ID:</strong> {chunk_id}<br>\n'
                html_content += f'                        <strong>Document:</strong> {doc_id}<br>\n'
                if metadata.get('source_filename'):
                    html_content += f'                        <strong>Source:</strong> {metadata.get("source_filename")}<br>\n'
                if metadata.get('page_number'):
                    html_content += f'                        <strong>Page:</strong> {metadata.get("page_number")}\n'
                html_content += '                    </div>\n'
            else:
                html_content += '                    <span class="no-results">No result</span>\n'
            html_content += '                </td>\n'
            
            # Python column
            html_content += '                <td class="content">\n'
            if python_result:
                score = python_result.get('similarity_score', 0)
                content = python_result.get('content', '')
                metadata = python_result.get('metadata', {})
                doc_id = python_result.get('document_id', '')
                chunk_id = python_result.get('id', '')
                
                html_content += f'                    <div class="score">Score: {score:.4f}</div>\n'
                html_content += f'                    {self._escape_html(content)}\n'
                html_content += f'                    <div class="metadata">\n'
                html_content += f'                        <strong>Chunk ID:</strong> {chunk_id}<br>\n'
                html_content += f'                        <strong>Document:</strong> {doc_id}<br>\n'
                if metadata.get('source_filename'):
                    html_content += f'                        <strong>Source:</strong> {metadata.get("source_filename")}<br>\n'
                if metadata.get('page_number'):
                    html_content += f'                        <strong>Page:</strong> {metadata.get("page_number")}\n'
                html_content += '                    </div>\n'
            else:
                html_content += '                    <span class="no-results">No result</span>\n'
            html_content += '                </td>\n'
            
            html_content += '            </tr>\n'
        
        html_content += """
        </tbody>
    </table>
    
    <div class="stats">
        <h2>Statistics</h2>
"""
        
        # Calculate statistics
        hnsw_ids = {r['id'] for r in hnsw_results}
        python_ids = {r['id'] for r in python_results}
        common_ids = hnsw_ids & python_ids
        
        html_content += f"""
        <strong>HNSW Results:</strong> {len(hnsw_results)}<br>
        <strong>Python Results:</strong> {len(python_results)}<br>
        <strong>Common Results:</strong> {len(common_ids)} ({len(common_ids)/max(1, min(len(hnsw_results), len(python_results)))*100:.1f}%)<br>
        <strong>HNSW-only Results:</strong> {len(hnsw_ids - python_ids)}<br>
        <strong>Python-only Results:</strong> {len(python_ids - hnsw_ids)}<br>
"""
        
        if hnsw_results:
            avg_hnsw_score = sum(r['similarity_score'] for r in hnsw_results) / len(hnsw_results)
            html_content += f"<strong>HNSW Avg Score:</strong> {avg_hnsw_score:.4f}<br>"
        
        if python_results:
            avg_python_score = sum(r['similarity_score'] for r in python_results) / len(python_results)
            html_content += f"<strong>Python Avg Score:</strong> {avg_python_score:.4f}<br>"
        
        html_content += """
    </div>
</body>
</html>
"""
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_file
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#39;'))


async def main():
    parser = argparse.ArgumentParser(description='Test production retrieval methods')
    parser.add_argument('query', help='Query to test')
    parser.add_argument('--run-id', help='Indexing run ID to filter results')
    parser.add_argument('--top-k', type=int, default=15, help='Number of results to retrieve (default: 15)')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = ProductionRetrievalTester(indexing_run_id=args.run_id)
    
    print(f"\n{'='*60}")
    print("PRODUCTION RETRIEVAL COMPARISON TEST")
    print(f"{'='*60}")
    print(f"Query: {args.query}")
    print(f"Indexing Run ID: {args.run_id or 'All runs'}")
    print(f"Top K: {args.top_k}")
    print(f"{'='*60}\n")
    
    # Run both retrieval methods
    print("Running HNSW search...")
    hnsw_results = await tester.test_hnsw_exact(args.query, args.top_k)
    
    print("Running Python similarity search...")
    python_results = await tester.test_python_similarity_exact(args.query, args.top_k)
    
    # Generate HTML comparison
    output_file = tester.generate_html_comparison(args.query, hnsw_results, python_results)
    
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"HNSW Results: {len(hnsw_results)}")
    print(f"Python Results: {len(python_results)}")
    
    # Show top result from each
    if hnsw_results:
        print(f"\nTop HNSW Result:")
        print(f"  Score: {hnsw_results[0]['similarity_score']:.4f}")
        print(f"  Content: {hnsw_results[0]['content'][:100]}...")
    
    if python_results:
        print(f"\nTop Python Result:")
        print(f"  Score: {python_results[0]['similarity_score']:.4f}")
        print(f"  Content: {python_results[0]['content'][:100]}...")
    
    print(f"\n✅ HTML comparison saved to: {output_file}")
    print(f"   Open in browser: file://{Path(output_file).absolute()}")


if __name__ == "__main__":
    asyncio.run(main())