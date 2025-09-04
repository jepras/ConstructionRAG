#!/usr/bin/env python3
"""
Working version of wiki generation pipeline test with all improvements.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import logging

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings
from src.services.config_service import ConfigService
from src.services.storage_service import StorageService
from src.pipeline.wiki_generation.steps import (
    MetadataCollectionStep,
    OverviewGenerationStep,
    StructureGenerationStep,
    PageContentRetrievalStep,
    MarkdownGenerationStep,
)
from src.pipeline.wiki_generation.models import (
    to_metadata_output,
    to_overview_output,
    to_structure_output,
    to_page_contents_output,
    to_markdown_output,
)

# ==================== CONFIGURATION ====================
INDEXING_RUN_ID = "163b73e6-637d-4096-a199-dce1122999d5"
OVERVIEW_QUERY_COUNT = 12
MAX_WIKI_PAGES = 3
QUERIES_PER_PAGE = 3
TOP_K_RETRIEVAL = 5

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WikiTestWorking:
    """Working version of wiki test with all improvements."""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()
        self.storage_service = StorageService()
        self.config_service = ConfigService()
        self.output_dir = None
        self.all_queries_executed = []
        
    def create_output_directory(self) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = Path(f"analysis/wiki-test-output/{timestamp}")
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir
        logger.info(f"📁 Created output directory: {output_dir}")
        return output_dir
    
    def save_json(self, filename: str, data: Any):
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"💾 Saved: {filename}")
    
    def get_test_config(self) -> Dict[str, Any]:
        wiki_config = self.config_service.get_effective_config("wiki")
        wiki_config["overview_query_count"] = OVERVIEW_QUERY_COUNT
        wiki_config["generation"]["max_pages"] = MAX_WIKI_PAGES
        wiki_config["generation"]["queries_per_page"] = QUERIES_PER_PAGE
        wiki_config["retrieval"]["top_k"] = TOP_K_RETRIEVAL
        
        logger.info(f"⚙️ Test configuration:")
        logger.info(f"  - Overview queries: {OVERVIEW_QUERY_COUNT}")
        logger.info(f"  - Max pages: {MAX_WIKI_PAGES}")
        logger.info(f"  - Queries per page: {QUERIES_PER_PAGE}")
        logger.info(f"  - Top K retrieval: {TOP_K_RETRIEVAL}")
        
        return wiki_config
    
    async def run(self):
        """Run the enhanced test pipeline."""
        self.create_output_directory()
        config = self.get_test_config()
        
        steps_completed = {"metadata": False, "overview": False, "clustering": False, 
                          "structure": False, "retrieval": False, "markdown": False}
        
        # Initialize variables
        metadata = {}
        project_overview = ""
        wiki_structure = {}
        page_contents = {}
        generated_pages = {}
        
        # ============= STEP 1: METADATA COLLECTION =============
        logger.info("\n" + "="*60)
        logger.info("STEP 1: Metadata Collection")
        logger.info("="*60)
        
        try:
            metadata_step = MetadataCollectionStep(config=config, storage_service=self.storage_service, db_client=self.supabase)
            metadata_result = await metadata_step.execute({"index_run_id": INDEXING_RUN_ID})
            
            if metadata_result.status == "failed":
                raise Exception(f"Metadata collection failed: {metadata_result.error_message}")
            
            metadata = to_metadata_output(metadata_result.data).model_dump(exclude_none=True)
            metadata_summary = {
                "indexing_run_id": metadata.get("indexing_run_id"),
                "total_documents": metadata.get("total_documents"),
                "total_chunks": metadata.get("total_chunks"),
                "document_filenames": metadata.get("document_filenames", [])
            }
            self.save_json("01_metadata_summary.json", metadata_summary)
            logger.info(f"✅ Collected metadata: {metadata.get('total_documents', 0)} documents, {metadata.get('total_chunks', 0)} chunks")
            steps_completed["metadata"] = True
            
        except Exception as e:
            logger.error(f"❌ STEP 1 FAILED: {e}")
            metadata = {"indexing_run_id": INDEXING_RUN_ID, "total_documents": 0, "total_chunks": 0, "documents": [], "document_filenames": []}

        # ============= STEP 2: OVERVIEW GENERATION =============
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Overview Generation (with vector search)")
        logger.info("="*60)
        
        try:
            overview_step = OverviewGenerationStep(config=config, storage_service=self.storage_service, db_client=self.supabase)
            overview_result = await overview_step.execute({"metadata": metadata})
            
            if overview_result.status == "failed":
                raise Exception(f"Overview generation failed: {overview_result.error_message}")
            
            overview_data = overview_result.data
            project_overview = to_overview_output(overview_data).project_overview
            
            # Extract queries using CORRECT field names
            overview_queries = overview_data.get("overview_queries", [])
            overview_data_nested = overview_data.get("overview_data", {})
            retrieved_chunks = overview_data_nested.get("retrieved_chunks", [])
            query_results = overview_data_nested.get("query_results", {})
            
            # Track each query with detailed results
            for query in overview_queries:
                query_info = query_results.get(query, {})
                chunk_count = query_info.get("results_count", 0)
                avg_similarity = query_info.get("avg_similarity", 0.0)
                
                self.all_queries_executed.append({
                    "step": "overview_generation",
                    "query": query,
                    "results_count": chunk_count,
                    "avg_similarity": avg_similarity,
                    "chunks": query_info.get("chunks", [])[:3]
                })
            
            self.save_json("02_project_overview.json", {
                "project_overview": project_overview,
                "queries_executed": len(overview_queries),
                "chunks_retrieved": len(retrieved_chunks),
                "query_results_summary": {
                    query: {
                        "results_count": results.get("results_count", 0),
                        "avg_similarity": results.get("avg_similarity", 0.0)
                    } for query, results in query_results.items()
                }
            })
            
            logger.info(f"✅ Generated project overview using {len(overview_queries)} queries")
            logger.info(f"   Retrieved {len(retrieved_chunks)} chunks total")
            
            for query, results in query_results.items():
                logger.info(f"   Query '{query[:50]}...': {results.get('results_count', 0)} chunks, avg_sim={results.get('avg_similarity', 0.0):.3f}")
            
            steps_completed["overview"] = True
            
        except Exception as e:
            logger.error(f"❌ STEP 2 FAILED: {e}")
            project_overview = f"Overview generation failed: {str(e)}"

        # ============= STEP 3: SKIP SEMANTIC CLUSTERING =============
        logger.info("\n" + "="*60)
        logger.info("STEP 3: Semantic Clustering (SKIPPED)")
        logger.info("="*60)
        
        semantic_analysis = None  # No semantic analysis - rely on project overview only
        self.save_json("03_semantic_clusters_skipped.json", {"note": "Semantic clustering was skipped - structure generation will rely on project overview only"})
        logger.info("⚠️ Skipped semantic clustering - structure generation will use project overview only")
        steps_completed["clustering"] = True

        # ============= STEP 4: STRUCTURE GENERATION =============
        logger.info("\n" + "="*60)
        logger.info("STEP 4: Structure Generation")
        logger.info("="*60)
        
        try:
            structure_step = StructureGenerationStep(config=config, storage_service=self.storage_service, db_client=self.supabase)
            structure_result = await structure_step.execute({
                "metadata": metadata,
                "project_overview": project_overview,
                "semantic_analysis": semantic_analysis
            })
            
            if structure_result.status == "failed":
                raise Exception(f"Structure generation failed: {structure_result.error_message}")
            
            wiki_structure = to_structure_output(structure_result.data).wiki_structure
            self.save_json("04_wiki_structure.json", wiki_structure)
            logger.info(f"✅ Generated wiki structure with {len(wiki_structure.get('pages', []))} pages")
            
            for page in wiki_structure.get("pages", []):
                logger.info(f"   - {page.get('title', 'Untitled')}")
            
            steps_completed["structure"] = True
            
        except Exception as e:
            logger.error(f"❌ STEP 4 FAILED: {e}")
            wiki_structure = {"pages": []}

        # ============= STEP 5: PAGE CONTENT RETRIEVAL =============
        logger.info("\n" + "="*60)
        logger.info("STEP 5: Page Content Retrieval")
        logger.info("="*60)
        
        try:
            retrieval_step = PageContentRetrievalStep(config=config, storage_service=self.storage_service, db_client=self.supabase)
            retrieval_result = await retrieval_step.execute({"metadata": metadata, "wiki_structure": wiki_structure})
            
            if retrieval_result.status == "failed":
                raise Exception(f"Page content retrieval failed: {retrieval_result.error_message}")
            
            page_contents = to_page_contents_output(retrieval_result.data).page_contents
            
            # Enhanced tracking with detailed chunk information
            page_query_details = {}
            total_page_chunks = 0
            
            for page in wiki_structure.get("pages", []):
                page_id = page.get("id")
                page_title = page.get("title", "Unknown")
                queries = page.get("queries", [])
                
                if page_id in page_contents:
                    page_data = page_contents[page_id]
                    chunks_retrieved = page_data.get("retrieved_chunks", [])
                    source_documents = page_data.get("source_documents", {})
                    total_page_chunks += len(chunks_retrieved)
                    
                    # Group chunks by query for detailed tracking
                    chunks_by_query = {}
                    for chunk in chunks_retrieved:
                        chunk_query = chunk.get("query", "unknown")
                        if chunk_query not in chunks_by_query:
                            chunks_by_query[chunk_query] = []
                        chunks_by_query[chunk_query].append(chunk)
                    
                    # Calculate statistics per query
                    query_stats = {}
                    for query in queries:
                        query_chunks = chunks_by_query.get(query, [])
                        similarities = [chunk.get("similarity_score", 0) for chunk in query_chunks]
                        
                        query_stats[query] = {
                            "chunks_count": len(query_chunks),
                            "avg_similarity": sum(similarities) / len(similarities) if similarities else 0.0,
                            "max_similarity": max(similarities) if similarities else 0.0,
                            "min_similarity": min(similarities) if similarities else 0.0
                        }
                        
                        # Track in global queries list
                        self.all_queries_executed.append({
                            "step": "page_content_retrieval",
                            "page": page_title,
                            "query": query,
                            "results_count": len(query_chunks),
                            "avg_similarity": query_stats[query]["avg_similarity"],
                            "max_similarity": query_stats[query]["max_similarity"]
                        })
                    
                    page_query_details[page_id] = {
                        "title": page_title,
                        "queries": queries,
                        "total_chunks": len(chunks_retrieved),
                        "source_documents": len(source_documents),
                        "query_statistics": query_stats
                    }
                    
                    logger.info(f"   📄 {page_title}: {len(chunks_retrieved)} chunks from {len(queries)} queries")
                    for query, stats in query_stats.items():
                        logger.info(f"      '{query[:40]}...': {stats['chunks_count']} chunks, avg_sim={stats['avg_similarity']:.3f}")
                        
                else:
                    logger.warning(f"   ⚠️ No content retrieved for page: {page_title}")
            
            self.save_json("05_page_contents.json", page_query_details)
            logger.info(f"✅ Retrieved {total_page_chunks} chunks for {len(page_contents)} pages")
            steps_completed["retrieval"] = True
            
        except Exception as e:
            logger.error(f"❌ STEP 5 FAILED: {e}")

        # ============= STEP 6: MARKDOWN GENERATION =============
        logger.info("\n" + "="*60)
        logger.info("STEP 6: Markdown Generation")
        logger.info("="*60)
        
        try:
            markdown_step = MarkdownGenerationStep(config=config, storage_service=self.storage_service, db_client=self.supabase)
            markdown_result = await markdown_step.execute({"metadata": metadata, "wiki_structure": wiki_structure, "page_contents": page_contents})
            
            if markdown_result.status == "failed":
                raise Exception(f"Markdown generation failed: {markdown_result.error_message}")
            
            generated_pages = to_markdown_output(markdown_result.data).generated_pages
            
            pages_dir = self.output_dir / "06_generated_pages"
            pages_dir.mkdir(exist_ok=True)
            
            for i, (page_id, page_data) in enumerate(generated_pages.items(), 1):
                page_file = pages_dir / f"page-{i}.md"
                with open(page_file, 'w', encoding='utf-8') as f:
                    f.write(page_data["markdown_content"])
                logger.info(f"   💾 Saved: {page_data['title']}")
            
            logger.info(f"✅ Generated {len(generated_pages)} markdown pages")
            steps_completed["markdown"] = True
            
        except Exception as e:
            logger.error(f"❌ STEP 6 FAILED: {e}")

        # ============= GENERATE HTML ANALYSIS =============
        try:
            self.generate_query_analysis_html()
        except Exception as e:
            logger.error(f"❌ HTML generation failed: {e}")

        # ============= GENERATE SUMMARY =============
        summary = {
            "run_timestamp": datetime.now().isoformat(),
            "indexing_run_id": INDEXING_RUN_ID,
            "configuration": {
                "overview_query_count": OVERVIEW_QUERY_COUNT,
                "max_wiki_pages": MAX_WIKI_PAGES,
                "queries_per_page": QUERIES_PER_PAGE,
                "top_k_retrieval": TOP_K_RETRIEVAL
            },
            "steps_completed": steps_completed,
            "results": {
                "documents_processed": metadata.get("total_documents", 0),
                "total_chunks": metadata.get("total_chunks", 0),
                "wiki_pages_generated": len(generated_pages),
                "total_queries_executed": len(self.all_queries_executed),
                "overview_queries": len([q for q in self.all_queries_executed if q["step"] == "overview_generation"]),
                "page_retrieval_queries": len([q for q in self.all_queries_executed if q["step"] == "page_content_retrieval"])
            },
            "output_directory": str(self.output_dir)
        }
        self.save_json("summary.json", summary)
        
        logger.info("\n" + "="*80)
        completed_steps = sum(steps_completed.values())
        total_steps = len(steps_completed)
        if completed_steps == total_steps:
            logger.info("✅ PIPELINE TEST COMPLETED SUCCESSFULLY")
        else:
            logger.info(f"⚠️ PIPELINE TEST PARTIALLY COMPLETED ({completed_steps}/{total_steps} steps)")
        logger.info("="*80)
        logger.info(f"📁 All outputs saved to: {self.output_dir}")
        logger.info(f"📊 Total queries executed: {len(self.all_queries_executed)}")
        logger.info(f"📄 Wiki pages generated: {len(generated_pages)}")
        logger.info(f"🔍 View query analysis: {self.output_dir}/query_analysis.html")
        logger.info(f"📋 Steps completed: {', '.join([step for step, completed in steps_completed.items() if completed])}")
        
        if completed_steps < total_steps:
            failed_steps = [step for step, completed in steps_completed.items() if not completed]
            logger.warning(f"⚠️ Steps that failed: {', '.join(failed_steps)}")

    def generate_query_analysis_html(self):
        """Generate comprehensive HTML analysis with expandable chunk details."""
        
        overview_queries = [q for q in self.all_queries_executed if q["step"] == "overview_generation"]
        page_queries = [q for q in self.all_queries_executed if q["step"] == "page_content_retrieval"]
        
        overview_avg_sim = sum(q.get("avg_similarity", 0) for q in overview_queries) / len(overview_queries) if overview_queries else 0
        page_avg_sim = sum(q.get("avg_similarity", 0) for q in page_queries) / len(page_queries) if page_queries else 0
        total_chunks = sum(q.get("results_count", 0) for q in self.all_queries_executed)
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wiki Generation Query Analysis - Interactive Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 1400px; margin: 0 auto; padding: 20px; background: #f8f9fa; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; border-top: 4px solid #3498db; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #2980b9; display: block; }}
        .stat-label {{ color: #7f8c8d; font-size: 14px; margin-top: 5px; }}
        .query-group {{ background: white; padding: 25px; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .query-item {{ border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; background: #f8f9fa; border-radius: 0 6px 6px 0; cursor: pointer; transition: all 0.3s ease; }}
        .query-item:hover {{ background: #e8f4f8; border-left-color: #2980b9; transform: translateX(2px); }}
        .query-text {{ font-weight: bold; color: #2c3e50; margin-bottom: 8px; font-size: 16px; }}
        .query-stats {{ display: flex; gap: 15px; margin: 8px 0; flex-wrap: wrap; }}
        .stat-badge {{ background: #ecf0f1; padding: 4px 8px; border-radius: 4px; font-size: 12px; color: #34495e; }}
        .stat-badge.results {{ background: #e8f5e8; color: #27ae60; }}
        .stat-badge.similarity {{ background: #fff3cd; color: #856404; }}
        .step-badge {{ padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; text-transform: uppercase; }}
        .step-overview {{ background: #3498db; color: white; }}
        .step-retrieval {{ background: #e74c3c; color: white; }}
        .page-title {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 20px; margin: -25px -25px 20px -25px; border-radius: 8px 8px 0 0; font-size: 18px; font-weight: bold; }}
        .expand-icon {{ float: right; transition: transform 0.3s ease; font-size: 14px; color: #7f8c8d; }}
        .expand-icon.expanded {{ transform: rotate(180deg); }}
        .chunks-details {{ display: none; margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6; }}
        .chunk-item {{ background: white; margin: 8px 0; padding: 12px; border-radius: 6px; border-left: 3px solid #27ae60; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .chunk-header {{ display: flex; justify-content: between; align-items: center; margin-bottom: 8px; }}
        .chunk-similarity {{ background: #27ae60; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }}
        .chunk-meta {{ color: #6c757d; font-size: 12px; margin-left: auto; }}
        .chunk-content {{ font-size: 14px; line-height: 1.5; color: #495057; background: #f8f9fa; padding: 10px; border-radius: 4px; white-space: pre-wrap; }}
        .chunk-source {{ color: #6c757d; font-size: 11px; margin-top: 8px; font-style: italic; }}
        .no-chunks {{ color: #6c757d; font-style: italic; padding: 10px; text-align: center; }}
    </style>
    <script>
        function toggleChunks(element) {{
            const details = element.nextElementSibling;
            const icon = element.querySelector('.expand-icon');
            
            if (details.style.display === 'none' || details.style.display === '') {{
                details.style.display = 'block';
                icon.classList.add('expanded');
                icon.textContent = '▼';
            }} else {{
                details.style.display = 'none';
                icon.classList.remove('expanded');
                icon.textContent = '▶';
            }}
        }}
    </script>
</head>
<body>
    <h1>🔍 Wiki Generation Query Analysis - Interactive Report</h1>
    
    <div class="summary">
        <div class="stat-card">
            <span class="stat-value">{len(self.all_queries_executed)}</span>
            <div class="stat-label">Total Queries Executed</div>
        </div>
        <div class="stat-card">
            <span class="stat-value">{total_chunks}</span>
            <div class="stat-label">Total Chunks Retrieved</div>
        </div>
        <div class="stat-card">
            <span class="stat-value">{len(overview_queries)}</span>
            <div class="stat-label">Overview Queries</div>
        </div>
        <div class="stat-card">
            <span class="stat-value">{len(page_queries)}</span>
            <div class="stat-label">Page Retrieval Queries</div>
        </div>
        <div class="stat-card">
            <span class="stat-value">{overview_avg_sim:.3f}</span>
            <div class="stat-label">Avg Overview Similarity</div>
        </div>
        <div class="stat-card">
            <span class="stat-value">{page_avg_sim:.3f}</span>
            <div class="stat-label">Avg Page Similarity</div>
        </div>
    </div>
    
    <h2>🎯 Overview Generation Queries</h2>"""

        # Overview queries with expandable chunks
        for i, query in enumerate(overview_queries, 1):
            chunks = query.get("chunks", [])
            html_content += f"""
    <div class="query-group">
        <div class="query-item" onclick="toggleChunks(this)">
            <div class="query-text">
                Query {i}: {query['query']}
                <span class="expand-icon">▶</span>
            </div>
            <div class="query-stats">
                <span class="step-badge step-overview">Overview Generation</span>
                <span class="stat-badge results">📊 {query.get('results_count', 0)} chunks</span>
                <span class="stat-badge similarity">🎯 Avg: {query.get('avg_similarity', 0):.3f}</span>
                <span class="stat-badge" style="background: #e3f2fd; color: #1976d2;">👆 Click to expand chunks</span>
            </div>
        </div>
        <div class="chunks-details">"""
            
            if chunks:
                for j, chunk in enumerate(chunks, 1):
                    content_preview = chunk.get('content_preview', '')
                    similarity = chunk.get('similarity_score', 0)
                    chunk_id = chunk.get('chunk_id', 'unknown')
                    
                    html_content += f"""
            <div class="chunk-item">
                <div class="chunk-header">
                    <span class="chunk-similarity">Sim: {similarity:.3f}</span>
                    <span class="chunk-meta">Chunk {j} of {len(chunks)}</span>
                </div>
                <div class="chunk-content">{content_preview}</div>
                <div class="chunk-source">Source: {chunk_id}</div>
            </div>"""
            else:
                html_content += '<div class="no-chunks">No chunk details available for this query</div>'
                
            html_content += """
        </div>
    </div>"""

        html_content += """
    <h2>📄 Page Content Retrieval Queries</h2>"""
        
        # Load page content details from saved JSON for chunk display
        try:
            page_contents_file = self.output_dir / "05_page_contents.json"
            if page_contents_file.exists():
                with open(page_contents_file, 'r') as f:
                    page_contents_data = json.load(f)
            else:
                page_contents_data = {}
        except:
            page_contents_data = {}
        
        # Group page queries by page
        pages = {}
        for query in page_queries:
            page = query.get("page", "Unknown")
            if page not in pages:
                pages[page] = []
            pages[page].append(query)
        
        for page_title, queries in pages.items():
            page_total_chunks = sum(q.get('results_count', 0) for q in queries)
            page_avg_sim = sum(q.get('avg_similarity', 0) for q in queries) / len(queries) if queries else 0
            
            # Find page data in saved JSON
            page_data = None
            for page_id, data in page_contents_data.items():
                if data.get('title') == page_title:
                    page_data = data
                    break
            
            html_content += f"""
    <div class="query-group">
        <div class="page-title">
            📋 {page_title} 
            <span style="font-size: 14px; opacity: 0.9;">({len(queries)} queries, {page_total_chunks} chunks, avg sim: {page_avg_sim:.3f})</span>
        </div>"""
            
            for i, query in enumerate(queries, 1):
                query_text = query['query']
                
                # Get chunks for this specific query from page data
                query_chunks = []
                if page_data and 'query_statistics' in page_data:
                    query_stats = page_data['query_statistics'].get(query_text, {})
                    query_chunks = query_stats.get('top_chunks', [])
                
                html_content += f"""
        <div class="query-item" onclick="toggleChunks(this)">
            <div class="query-text">
                Query {i}: {query['query']}
                <span class="expand-icon">▶</span>
            </div>
            <div class="query-stats">
                <span class="step-badge step-retrieval">Page Retrieval</span>
                <span class="stat-badge results">📊 {query.get('results_count', 0)} chunks</span>
                <span class="stat-badge similarity">🎯 Avg: {query.get('avg_similarity', 0):.3f}</span>
                <span class="stat-badge similarity">📈 Max: {query.get('max_similarity', 0):.3f}</span>
                <span class="stat-badge" style="background: #e3f2fd; color: #1976d2;">👆 Click to expand chunks</span>
            </div>
        </div>
        <div class="chunks-details">"""
                
                if query_chunks:
                    for j, chunk in enumerate(query_chunks, 1):
                        content_preview = chunk.get('content_preview', '')
                        similarity = chunk.get('similarity_score', 0)
                        document_id = chunk.get('document_id', 'unknown')
                        metadata = chunk.get('metadata', {})
                        page_number = metadata.get('page_number', 'N/A')
                        
                        html_content += f"""
            <div class="chunk-item">
                <div class="chunk-header">
                    <span class="chunk-similarity">Sim: {similarity:.3f}</span>
                    <span class="chunk-meta">Chunk {j} of {len(query_chunks)} | Page: {page_number}</span>
                </div>
                <div class="chunk-content">{content_preview}</div>
                <div class="chunk-source">Document: {document_id}</div>
            </div>"""
                else:
                    html_content += f'<div class="no-chunks">No detailed chunk information available for this query (retrieved {query.get("results_count", 0)} chunks)</div>'
                
                html_content += """
        </div>"""
            
            html_content += """
    </div>"""
        
        html_content += f"""
    <div style="margin-top: 40px; padding: 20px; background: white; border-radius: 8px; text-align: center; color: #7f8c8d;">
        Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M:%S")}<br>
        <small>Wiki Generation Pipeline Analysis Report - Click queries to expand chunk details</small>
    </div>
</body>
</html>"""
        
        html_file = self.output_dir / "query_analysis.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info("💾 Saved interactive query analysis HTML with expandable chunks")


async def main():
    runner = WikiTestWorking()
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())