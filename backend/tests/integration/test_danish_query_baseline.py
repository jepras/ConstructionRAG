"""
Baseline Danish query test for retrieval system refactoring.

This test captures the current behavior of the query pipeline with Danish construction queries
to ensure no regression when extracting shared retrieval components.

Test query: "Hvad er kravene til brandsikkerhed i tagkonstruktioner?"
(What are the requirements for fire safety in roof constructions?)
"""

import pytest
import json
import asyncio
from datetime import datetime
from typing import Dict, Any

from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
from src.pipeline.querying.models import QueryRequest, QueryResponse


class TestDanishQueryBaseline:
    """Baseline test to capture current Danish query behavior"""

    @pytest.fixture
    def test_query(self) -> str:
        """Danish construction query for testing"""
        return "Hvad er kravene til brandsikkerhed i tagkonstruktioner?"

    @pytest.fixture
    def orchestrator(self) -> QueryPipelineOrchestrator:
        """Query pipeline orchestrator"""
        return QueryPipelineOrchestrator()

    @pytest.mark.asyncio
    async def test_danish_query_baseline_behavior(self, orchestrator, test_query):
        """
        Capture baseline behavior for Danish query processing.
        
        This test documents the current behavior and will be used to validate
        that refactoring doesn't break Danish language processing.
        """
        print(f"\n🧪 BASELINE TEST: Testing Danish query: '{test_query}'")
        
        # Create request
        request = QueryRequest(
            query=test_query,
            user_id="baseline-test-user"
        )
        
        # Record start time
        start_time = datetime.utcnow()
        
        # Execute pipeline
        response = await orchestrator.process_query(request)
        
        # Record end time
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Validate response structure
        assert isinstance(response, QueryResponse)
        assert isinstance(response.response, str)
        assert isinstance(response.search_results, list)
        assert isinstance(response.performance_metrics, dict)
        
        # Document baseline behavior
        baseline_results = {
            "test_metadata": {
                "query": test_query,
                "test_timestamp": datetime.utcnow().isoformat(),
                "response_time_ms": response_time_ms
            },
            "response_analysis": {
                "response_length": len(response.response),
                "response_preview": response.response[:200] + "..." if len(response.response) > 200 else response.response,
                "has_danish_text": self._contains_danish_text(response.response),
                "has_citations": "[" in response.response and "]" in response.response
            },
            "retrieval_analysis": {
                "results_count": len(response.search_results),
                "similarity_scores": [result.similarity_score for result in response.search_results],
                "top_similarity": max([result.similarity_score for result in response.search_results]) if response.search_results else 0.0,
                "avg_similarity": sum([result.similarity_score for result in response.search_results]) / len(response.search_results) if response.search_results else 0.0,
                "source_files": list(set([result.source_filename for result in response.search_results])),
                "content_preview": [result.content[:100] + "..." for result in response.search_results[:3]]
            },
            "performance_metrics": response.performance_metrics,
            "quality_metrics": response.quality_metrics.model_dump(exclude_none=True) if response.quality_metrics else None,
            "step_timings": getattr(response, 'step_timings', {})
        }
        
        # Print detailed baseline results
        print(f"\n📊 BASELINE RESULTS:")
        print(f"   Response time: {response_time_ms}ms")
        print(f"   Retrieved chunks: {len(response.search_results)}")
        print(f"   Top similarity: {baseline_results['retrieval_analysis']['top_similarity']:.4f}")
        print(f"   Avg similarity: {baseline_results['retrieval_analysis']['avg_similarity']:.4f}")
        print(f"   Source files: {len(baseline_results['retrieval_analysis']['source_files'])}")
        print(f"   Response length: {len(response.response)} chars")
        print(f"   Contains Danish: {baseline_results['response_analysis']['has_danish_text']}")
        print(f"   Has citations: {baseline_results['response_analysis']['has_citations']}")
        
        # Print response preview
        print(f"\n📝 RESPONSE PREVIEW:")
        print(f"   '{response.response[:300]}...'")
        
        # Print similarity scores
        if response.search_results:
            print(f"\n🔍 SIMILARITY SCORES:")
            for i, result in enumerate(response.search_results[:5], 1):
                print(f"   {i}: {result.similarity_score:.4f} - {result.source_filename} (page {result.page_number})")
        
        # Store baseline for comparison (optional - could save to file for later comparison)
        self.baseline_results = baseline_results
        
        # Core assertions to ensure basic functionality
        assert len(response.search_results) > 0, "Should retrieve at least some results"
        assert response.response.strip() != "", "Should generate a non-empty response"
        assert baseline_results['retrieval_analysis']['top_similarity'] > 0.2, "Should find reasonably similar content"
        assert baseline_results['response_analysis']['has_danish_text'], "Response should contain Danish text"
        
        print(f"\n✅ BASELINE TEST COMPLETED - Results captured for comparison")
        
        return baseline_results

    @pytest.mark.asyncio 
    async def test_danish_query_retrieval_details(self, orchestrator, test_query):
        """
        Detailed test of retrieval step for Danish queries.
        
        This test focuses specifically on the retrieval behavior to ensure
        pgvector search and Danish similarity thresholds work correctly.
        """
        print(f"\n🔍 RETRIEVAL DETAILS TEST: Testing retrieval for: '{test_query}'")
        
        # Access the retriever directly to test retrieval behavior
        retriever = orchestrator.retriever
        
        # Test embedding generation for Danish text
        query_embedding = await retriever.embed_query(test_query)
        
        # Validate embedding properties
        assert len(query_embedding) == 1024, f"Expected 1024 dimensions, got {len(query_embedding)}"
        assert all(isinstance(x, (int, float)) for x in query_embedding), "Embedding should contain only numbers"
        
        # Test query variations processing
        query_processor = orchestrator.query_processor
        variations_result = await query_processor.execute(test_query)
        
        assert variations_result.status == "completed", f"Query processing failed: {variations_result.error_message}"
        
        # Test retrieval with variations
        from src.pipeline.querying.models import to_query_variations
        variations = to_query_variations(variations_result.sample_outputs)
        
        retrieval_result = await retriever.execute(variations)
        
        assert retrieval_result.status == "completed", f"Retrieval failed: {retrieval_result.error_message}"
        
        # Document retrieval behavior
        from src.pipeline.querying.models import to_search_results
        search_results = to_search_results(retrieval_result.sample_outputs)
        
        print(f"\n📊 RETRIEVAL ANALYSIS:")
        print(f"   Embedding dimensions: {len(query_embedding)}")
        print(f"   Query variations: {len([v for v in [variations.semantic, variations.hyde, variations.formal] if v])}")
        print(f"   Retrieved results: {len(search_results)}")
        
        if search_results:
            similarities = [r.similarity_score for r in search_results]
            print(f"   Similarity range: {min(similarities):.4f} - {max(similarities):.4f}")
            print(f"   Above 0.5: {len([s for s in similarities if s > 0.5])}")
            print(f"   Above 0.3: {len([s for s in similarities if s > 0.3])}")
        
        # Validate retrieval meets Danish language expectations
        assert len(search_results) > 0, "Should retrieve results for Danish query"
        assert max([r.similarity_score for r in search_results]) > 0.25, "Should find reasonably similar content with Danish thresholds"
        
        print(f"✅ RETRIEVAL DETAILS TEST COMPLETED")
        
        return {
            "embedding_dims": len(query_embedding),
            "variations_count": len([v for v in [variations.semantic, variations.hyde, variations.formal] if v]),
            "results_count": len(search_results),
            "similarity_scores": [r.similarity_score for r in search_results]
        }

    def _contains_danish_text(self, text: str) -> bool:
        """Check if text contains Danish-specific characters or words"""
        danish_indicators = [
            'æ', 'ø', 'å', 'Æ', 'Ø', 'Å',  # Danish letters
            'og', 'er', 'til', 'for', 'med', 'på', 'af', 'ikke',  # Common Danish words
            'skal', 'kan', 'vil', 'må', 'bør'  # Danish modal verbs
        ]
        return any(indicator in text for indicator in danish_indicators)


if __name__ == "__main__":
    """Run baseline test directly"""
    import asyncio
    import os
    from dotenv import load_dotenv
    
    # Load environment
    load_dotenv()
    
    async def run_baseline():
        test = TestDanishQueryBaseline()
        orchestrator = QueryPipelineOrchestrator()
        query = "Hvad er kravene til brandsikkerhed i tagkonstruktioner?"
        
        print("🧪 Running Danish Query Baseline Test...")
        baseline = await test.test_danish_query_baseline_behavior(orchestrator, query)
        
        print("\n🔍 Running Retrieval Details Test...")
        retrieval_details = await test.test_danish_query_retrieval_details(orchestrator, query)
        
        print("\n📋 COMPLETE BASELINE CAPTURED ✅")
        return baseline, retrieval_details
    
    if __name__ == "__main__":
        asyncio.run(run_baseline())