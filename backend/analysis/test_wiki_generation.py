#!/usr/bin/env python3
"""
Test script for wiki generation pipeline WITHOUT semantic clustering.
Focuses on the actual data retrieval and query tracking as originally planned.
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
sys.path.insert(0, str(Path(__file__).parent))

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
OVERVIEW_QUERY_COUNT = 12  # Number of queries for overview
MAX_WIKI_PAGES = 3  # Generate 3 pages
QUERIES_PER_PAGE = 3  # 3 queries per page
TOP_K_RETRIEVAL = 5  # 5 results per query

# ========================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WikiTestWithoutClustering:
    """Test runner that skips clustering and focuses on actual retrieval."""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()
        self.storage_service = StorageService()
        self.config_service = ConfigService()
        self.output_dir = None
        self.all_queries_executed = []  # Track ALL queries
        
    def create_output_directory(self) -> Path:
        """Create timestamped output directory."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = Path(f"analysis/wiki-test-output/{timestamp}")
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir
        logger.info(f"📁 Created output directory: {output_dir}")
        return output_dir
    
    def save_json(self, filename: str, data: Any):
        """Save data as JSON to output directory."""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"💾 Saved: {filename}")
    
    def get_test_config(self) -> Dict[str, Any]:
        """Get modified configuration for testing."""
        wiki_config = self.config_service.get_effective_config("wiki")
        
        # Override with our test parameters
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
        """Run the test pipeline without clustering."""
        try:
            self.create_output_directory()
            config = self.get_test_config()
            
            # ============= STEP 1: METADATA COLLECTION =============
            logger.info("\n" + "="*60)
            logger.info("STEP 1: Metadata Collection")
            logger.info("="*60)
            
            metadata_step = MetadataCollectionStep(
                config=config,
                storage_service=self.storage_service,
                db_client=self.supabase
            )
            
            metadata_result = await metadata_step.execute({
                "index_run_id": INDEXING_RUN_ID
            })
            
            if metadata_result.status == "failed":
                raise Exception(f"Metadata collection failed: {metadata_result.error_message}")
            
            metadata = to_metadata_output(metadata_result.data).model_dump(exclude_none=True)
            
            # Save metadata summary
            metadata_summary = {
                "indexing_run_id": metadata.get("indexing_run_id"),
                "total_documents": metadata.get("total_documents"),
                "total_chunks": metadata.get("total_chunks"),
                "document_filenames": metadata.get("document_filenames", [])
            }
            self.save_json("01_metadata_summary.json", metadata_summary)
            logger.info(f"✅ Collected metadata: {metadata.get('total_documents', 0)} documents, {metadata.get('total_chunks', 0)} chunks")
            
            # ============= STEP 2: OVERVIEW GENERATION (WITH ACTUAL RETRIEVAL) =============
            logger.info("\n" + "="*60)
            logger.info("STEP 2: Overview Generation (with vector search)")
            logger.info("="*60)
            
            overview_step = OverviewGenerationStep(
                config=config,
                storage_service=self.storage_service,
                db_client=self.supabase
            )
            
            overview_result = await overview_step.execute({
                "metadata": metadata
            })
            
            if overview_result.status == "failed":
                raise Exception(f"Overview generation failed: {overview_result.error_message}")
            
            overview_data = overview_result.data
            project_overview = to_overview_output(overview_data).project_overview
            
            # Track overview queries
            queries_used = overview_data.get("queries_used", [])
            retrieved_chunks = overview_data.get("retrieved_chunks", [])
            
            for query in queries_used:
                self.all_queries_executed.append({
                    "step": "overview_generation",
                    "query": query,
                    "results_count": len(retrieved_chunks) // len(queries_used) if queries_used else 0
                })
            
            self.save_json("02_project_overview.json", {
                "project_overview": project_overview,
                "queries_executed": len(queries_used),
                "chunks_retrieved": len(retrieved_chunks),
                "sample_chunks": retrieved_chunks[:3] if retrieved_chunks else []
            })
            logger.info(f"✅ Generated project overview using {len(queries_used)} queries")
            logger.info(f"   Retrieved {len(retrieved_chunks)} chunks total")
            
            # ============= STEP 3: SKIP SEMANTIC CLUSTERING =============
            logger.info("\n" + "="*60)
            logger.info("STEP 3: Semantic Clustering (SKIPPED)")
            logger.info("="*60)
            
            # Create mock semantic analysis with realistic cluster names
            semantic_analysis = {
                "clusters": {},
                "cluster_summaries": [
                    {"cluster_id": 0, "cluster_name": "El-installationer", "chunk_count": 50},
                    {"cluster_id": 1, "cluster_name": "VVS og ventilation", "chunk_count": 45},
                    {"cluster_id": 2, "cluster_name": "Projektadministration", "chunk_count": 40},
                    {"cluster_id": 3, "cluster_name": "Sikkerhedsforhold", "chunk_count": 35}
                ],
                "n_clusters": 4
            }
            self.save_json("03_semantic_clusters_skipped.json", {
                "note": "Semantic clustering was skipped",
                "mock_clusters": semantic_analysis["cluster_summaries"]
            })
            logger.info("⚠️ Skipped semantic clustering (using mock data)")
            
            # ============= STEP 4: STRUCTURE GENERATION =============
            logger.info("\n" + "="*60)
            logger.info("STEP 4: Structure Generation")
            logger.info("="*60)
            
            structure_step = StructureGenerationStep(
                config=config,
                storage_service=self.storage_service,
                db_client=self.supabase
            )
            
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
            
            # Log the page titles
            for page in wiki_structure.get("pages", []):
                logger.info(f"   - {page.get('title', 'Untitled')}")
            
            # ============= STEP 5: PAGE CONTENT RETRIEVAL =============
            logger.info("\n" + "="*60)
            logger.info("STEP 5: Page Content Retrieval")
            logger.info("="*60)
            
            retrieval_step = PageContentRetrievalStep(
                config=config,
                storage_service=self.storage_service,
                db_client=self.supabase
            )
            
            retrieval_result = await retrieval_step.execute({
                "metadata": metadata,
                "wiki_structure": wiki_structure
            })
            
            if retrieval_result.status == "failed":
                raise Exception(f"Page content retrieval failed: {retrieval_result.error_message}")
            
            page_contents = to_page_contents_output(retrieval_result.data).page_contents
            
            # Track page retrieval queries
            page_query_details = {}
            for page in wiki_structure.get("pages", []):
                page_id = page.get("id")
                page_title = page.get("title", "Unknown")
                queries = page.get("queries", [])
                
                if page_id in page_contents:
                    chunks_retrieved = page_contents[page_id].get("retrieved_chunks", [])
                    chunks_per_query = len(chunks_retrieved) // len(queries) if queries else 0
                    
                    page_query_details[page_id] = {
                        "title": page_title,
                        "queries": queries,
                        "total_chunks": len(chunks_retrieved),
                        "chunks_per_query": chunks_per_query,
                        "sample_chunks": chunks_retrieved[:2] if chunks_retrieved else []
                    }
                    
                    # Track each query
                    for query in queries:
                        self.all_queries_executed.append({
                            "step": "page_content_retrieval",
                            "page": page_title,
                            "query": query,
                            "results_count": chunks_per_query
                        })
            
            self.save_json("05_page_contents.json", page_query_details)
            
            total_chunks = sum(len(pc.get("retrieved_chunks", [])) for pc in page_contents.values())
            logger.info(f"✅ Retrieved {total_chunks} chunks for {len(page_contents)} pages")
            
            # ============= STEP 6: MARKDOWN GENERATION =============
            logger.info("\n" + "="*60)
            logger.info("STEP 6: Markdown Generation")
            logger.info("="*60)
            
            markdown_step = MarkdownGenerationStep(
                config=config,
                storage_service=self.storage_service,
                db_client=self.supabase
            )
            
            markdown_result = await markdown_step.execute({
                "metadata": metadata,
                "wiki_structure": wiki_structure,
                "page_contents": page_contents
            })
            
            if markdown_result.status == "failed":
                raise Exception(f"Markdown generation failed: {markdown_result.error_message}")
            
            generated_pages = to_markdown_output(markdown_result.data).generated_pages
            
            # Save generated pages
            pages_dir = self.output_dir / "06_generated_pages"
            pages_dir.mkdir(exist_ok=True)
            
            for i, (page_id, page_data) in enumerate(generated_pages.items(), 1):
                page_file = pages_dir / f"page-{i}.md"
                with open(page_file, 'w', encoding='utf-8') as f:
                    f.write(page_data["markdown_content"])
                logger.info(f"   💾 Saved: {page_data['title']}")
            
            logger.info(f"✅ Generated {len(generated_pages)} markdown pages")
            
            # ============= GENERATE QUERY ANALYSIS HTML =============
            self.generate_query_analysis_html()
            
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
            
            logger.info("\n" + "="*60)
            logger.info("✅ PIPELINE TEST COMPLETED SUCCESSFULLY")
            logger.info("="*60)
            logger.info(f"📁 All outputs saved to: {self.output_dir}")
            logger.info(f"📊 Total queries executed: {len(self.all_queries_executed)}")
            logger.info(f"📄 Wiki pages generated: {len(generated_pages)}")
            logger.info(f"🔍 View query analysis: {self.output_dir}/query_analysis.html")
            
        except Exception as e:
            logger.error(f"❌ Pipeline test failed: {e}", exc_info=True)
            raise
    
    def generate_query_analysis_html(self):
        """Generate HTML page showing all queries and their results."""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wiki Generation Query Analysis</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .summary {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .summary-stat {
            display: inline-block;
            margin-right: 30px;
            padding: 10px 15px;
            background: #ecf0f1;
            border-radius: 4px;
        }
        .summary-stat strong {
            color: #2980b9;
            display: block;
            font-size: 24px;
        }
        .query-group {
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .query-item {
            border-left: 3px solid #3498db;
            padding: 10px;
            margin: 10px 0;
            background: #f8f9fa;
        }
        .query-text {
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .query-meta {
            font-size: 12px;
            color: #7f8c8d;
        }
        .page-badge {
            display: inline-block;
            padding: 2px 8px;
            background: #9b59b6;
            color: white;
            border-radius: 3px;
            font-size: 11px;
            margin-left: 10px;
        }
        .step-overview { background: #3498db; }
        .step-retrieval { background: #e74c3c; }
    </style>
</head>
<body>
    <h1>Wiki Generation Query Analysis</h1>
    
    <div class="summary">
        <h2>Summary Statistics</h2>
        <div class="summary-stat">
            <strong>""" + str(len(self.all_queries_executed)) + """</strong>
            Total Queries
        </div>
        <div class="summary-stat">
            <strong>""" + str(len([q for q in self.all_queries_executed if q["step"] == "overview_generation"])) + """</strong>
            Overview Queries
        </div>
        <div class="summary-stat">
            <strong>""" + str(len([q for q in self.all_queries_executed if q["step"] == "page_content_retrieval"])) + """</strong>
            Page Queries
        </div>
    </div>
    
    <h2>Overview Generation Queries</h2>
    <div class="query-group">
"""
        
        # Overview queries
        overview_queries = [q for q in self.all_queries_executed if q["step"] == "overview_generation"]
        for i, query in enumerate(overview_queries, 1):
            html_content += f"""
        <div class="query-item">
            <div class="query-text">Query {i}: {query['query']}</div>
            <div class="query-meta">
                <span class="step-overview">Overview Generation</span>
                Retrieved approximately {query.get('results_count', 0)} chunks
            </div>
        </div>
"""
        
        html_content += """
    </div>
    
    <h2>Page Content Retrieval Queries</h2>
"""
        
        # Group queries by page
        page_queries = [q for q in self.all_queries_executed if q["step"] == "page_content_retrieval"]
        pages = {}
        for query in page_queries:
            page = query.get("page", "Unknown")
            if page not in pages:
                pages[page] = []
            pages[page].append(query)
        
        for page_title, queries in pages.items():
            html_content += f"""
    <div class="query-group">
        <h3>{page_title}</h3>
"""
            for query in queries:
                html_content += f"""
        <div class="query-item">
            <div class="query-text">{query['query']}</div>
            <div class="query-meta">
                <span class="step-retrieval">Page Retrieval</span>
                Retrieved approximately {query.get('results_count', 0)} chunks
            </div>
        </div>
"""
            html_content += """
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        html_file = self.output_dir / "query_analysis.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info("💾 Saved query analysis HTML")


async def main():
    """Main entry point."""
    runner = WikiTestWithoutClustering()
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())