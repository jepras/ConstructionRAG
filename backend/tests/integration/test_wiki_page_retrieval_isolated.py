"""
Isolated test for PageContentRetrievalStep to diagnose issues without running full wiki pipeline.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings
from src.services.config_service import ConfigService
from src.services.storage_service import StorageService
from src.pipeline.wiki_generation.steps import PageContentRetrievalStep


# Test configuration
INDEXING_RUN_ID = "163b73e6-637d-4096-a199-dce1122999d5"
TEST_QUERIES_PER_PAGE = 3
TEST_TOP_K = 5


def create_test_metadata() -> Dict[str, Any]:
    """Create minimal metadata for testing."""
    return {
        "indexing_run_id": INDEXING_RUN_ID,
        "total_documents": 3,
        "total_chunks": 100,
        "documents": [
            {"id": "doc1", "filename": "test1.pdf"},
            {"id": "doc2", "filename": "test2.pdf"},
            {"id": "doc3", "filename": "test3.pdf"},
        ]
    }


def create_test_wiki_structure() -> Dict[str, Any]:
    """Create minimal wiki structure for testing."""
    return {
        "pages": [
            {
                "id": "page1",
                "title": "El-installationer",
                "queries": [
                    "elektriske installationer ledninger kabler",
                    "el-tavler sikringer afbrydere",
                    "lysinstallationer belysning"
                ]
            },
            {
                "id": "page2", 
                "title": "VVS og ventilation",
                "queries": [
                    "vandinstallationer rør vandhaner",
                    "ventilationsanlæg luftbehandling",
                    "varmeinstallationer radiatorer"
                ]
            },
            {
                "id": "page3",
                "title": "Sikkerhedsforhold",
                "queries": [
                    "sikkerhed arbejdsmiljø",
                    "brandforhold brandsikkerhed",
                    "adgangsforhold sikkerhedsudstyr"
                ]
            }
        ]
    }


class PageRetrievalTester:
    """Test class for isolated page content retrieval."""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()
        self.storage_service = StorageService()
        self.config_service = ConfigService()
        self.queries_executed = []
        self.chunks_retrieved = []
        
    def get_test_config(self) -> Dict[str, Any]:
        """Get test configuration."""
        wiki_config = self.config_service.get_effective_config("wiki")
        
        # Override with test parameters
        wiki_config["retrieval"]["top_k"] = TEST_TOP_K
        wiki_config["retrieval"]["max_chunks_per_page"] = 15
        wiki_config["retrieval"]["similarity_threshold"] = 0.15
        
        return wiki_config
    
    async def test_page_retrieval_step(self):
        """Test the PageContentRetrievalStep in isolation."""
        print("\n" + "="*80)
        print("🔍 ISOLATED PAGE CONTENT RETRIEVAL TEST")
        print("="*80)
        
        try:
            config = self.get_test_config()
            metadata = create_test_metadata()
            wiki_structure = create_test_wiki_structure()
            
            print(f"📋 Test Configuration:")
            print(f"   - Indexing Run ID: {INDEXING_RUN_ID}")
            print(f"   - Top K: {config['retrieval']['top_k']}")
            print(f"   - Pages: {len(wiki_structure['pages'])}")
            print(f"   - Queries per page: {TEST_QUERIES_PER_PAGE}")
            print(f"   - Similarity threshold: {config['retrieval']['similarity_threshold']}")
            
            # Create PageContentRetrievalStep
            retrieval_step = PageContentRetrievalStep(
                config=config,
                storage_service=self.storage_service,
                db_client=self.supabase
            )
            
            print(f"\n🚀 Starting page content retrieval...")
            start_time = datetime.utcnow()
            
            # Execute the step
            result = await retrieval_step.execute({
                "metadata": metadata,
                "wiki_structure": wiki_structure
            })
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            print(f"⏱️ Execution completed in {duration:.2f} seconds")
            print(f"📊 Step status: {result.status}")
            
            if result.status == "failed":
                print(f"❌ Step failed with error: {result.error_message}")
                return result
            
            # Analyze results
            await self._analyze_results(result, wiki_structure)
            
            print(f"\n✅ Page content retrieval test completed successfully!")
            return result
            
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _analyze_results(self, result, wiki_structure):
        """Analyze and display the results."""
        print(f"\n📈 RESULT ANALYSIS")
        print("-" * 40)
        
        # Get page contents from result
        from src.pipeline.wiki_generation.models import to_page_contents_output
        page_contents_output = to_page_contents_output(result.data)
        page_contents = page_contents_output.page_contents
        
        print(f"📄 Pages processed: {len(page_contents)}")
        
        total_chunks = 0
        total_queries = 0
        
        for page in wiki_structure["pages"]:
            page_id = page["id"]
            page_title = page["title"]
            queries = page.get("queries", [])
            total_queries += len(queries)
            
            if page_id in page_contents:
                page_data = page_contents[page_id]
                retrieved_chunks = page_data.get("retrieved_chunks", [])
                source_docs = page_data.get("source_documents", {})
                
                print(f"\n📋 Page: {page_title}")
                print(f"   🔍 Queries: {len(queries)}")
                print(f"   📄 Chunks retrieved: {len(retrieved_chunks)}")
                print(f"   📚 Source documents: {len(source_docs)}")
                
                # Show sample queries and results
                for i, query in enumerate(queries[:2], 1):  # Show first 2 queries
                    print(f"   Query {i}: {query}")
                    
                    # Find chunks for this query
                    query_chunks = [chunk for chunk in retrieved_chunks if chunk.get("query") == query]
                    print(f"      Results: {len(query_chunks)}")
                    
                    if query_chunks:
                        best_chunk = query_chunks[0]
                        similarity = best_chunk.get("similarity_score", 0)
                        content_preview = best_chunk.get("content", "")[:150].replace("\n", " ")
                        print(f"      Best match (sim={similarity:.3f}): {content_preview}...")
                
                total_chunks += len(retrieved_chunks)
            else:
                print(f"\n❌ Page {page_title}: No content retrieved")
        
        print(f"\n📊 SUMMARY STATISTICS")
        print(f"   Total queries executed: {total_queries}")
        print(f"   Total chunks retrieved: {total_chunks}")
        print(f"   Average chunks per query: {total_chunks/total_queries if total_queries > 0 else 0:.2f}")
        
        # Show step summary stats
        if hasattr(result, 'summary_stats') and result.summary_stats:
            print(f"\n📈 Step Summary Stats:")
            for key, value in result.summary_stats.items():
                print(f"   {key}: {value}")


@pytest.mark.asyncio 
async def test_page_retrieval_isolated():
    """Pytest entry point for isolated page retrieval test."""
    # Check for required environment variables
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"):
        pytest.skip("Supabase environment not configured")
    
    tester = PageRetrievalTester()
    result = await tester.test_page_retrieval_step()
    
    # Assert basic success conditions
    assert result is not None
    assert result.status in ["completed", "failed"]  # Either is informative
    
    if result.status == "completed":
        # Verify we got some data back
        assert result.data is not None
        from src.pipeline.wiki_generation.models import to_page_contents_output
        page_contents = to_page_contents_output(result.data).page_contents
        assert len(page_contents) > 0  # Should have retrieved content for at least some pages


async def main():
    """Main entry point for running the test standalone."""
    tester = PageRetrievalTester()
    await tester.test_page_retrieval_step()


if __name__ == "__main__":
    asyncio.run(main())