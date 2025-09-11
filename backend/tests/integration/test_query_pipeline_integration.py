import pytest

from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
from src.pipeline.querying.models import QueryRequest, QueryResponse


@pytest.mark.asyncio
async def test_query_pipeline_end_to_end_smoke(monkeypatch):
    orchestrator = QueryPipelineOrchestrator()

    # Build a minimal valid request
    req = QueryRequest(query="Hvad er standardafstand for spær?", user_id="test-user")

    # Execute the pipeline
    resp = await orchestrator.process_query(req)

    # Basic shape assertions (response model)
    assert isinstance(resp, QueryResponse)
    assert isinstance(resp.response, str)
    assert isinstance(resp.search_results, list)
    assert isinstance(resp.performance_metrics, dict)


"""
Integration test for the complete query pipeline.

This test verifies the end-to-end functionality of the query pipeline:
1. Query Processing (semantic expansion, HyDE, formal variations)
2. Document Retrieval (vector search with deduplication)
3. Response Generation (LLM response with quality metrics)
4. Pipeline Orchestration (coordination and error handling)
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
from src.pipeline.querying.models import QueryRequest


class TestQueryPipelineIntegration:
    """Integration test suite for the complete query pipeline"""

    def __init__(self):
        self.orchestrator = QueryPipelineOrchestrator()
        self.test_results = []

    async def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Query Pipeline Integration Tests...")
        print("=" * 80)

        # Test queries covering different aspects of construction
        test_cases = [
            {
                "name": "Rainwater Handling Principles",
                "query": "Hvad er principperne for regnvandshåndtering?",
                "expected_topics": ["regnvand", "taghave", "system", "håndtering"],
            },
            {
                "name": "Cost Comparison Analysis",
                "query": "Hvad koster en normal sag ift. en vanskelig sag?",
                "expected_topics": ["pris", "sag", "kost", "vanskelig", "normal"],
            },
            {
                "name": "Work Scope Definition",
                "query": "Hvad omfatter arbejdet?",
                "expected_topics": ["arbejde", "omfang", "renovering", "tag", "facade"],
            },
            {
                "name": "Technical Specifications",
                "query": "Hvad er de tekniske specifikationer for taget?",
                "expected_topics": [
                    "tekniske",
                    "specifikationer",
                    "tag",
                    "konstruktion",
                ],
            },
            {
                "name": "Safety Standards",
                "query": "Hvilke sikkerhedsstandarder skal følges?",
                "expected_topics": ["sikkerhed", "standarder", "koder", "regler"],
            },
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 Test Case {i}: {test_case['name']}")
            print(f"Query: {test_case['query']}")
            print("-" * 60)

            result = await self._run_single_test(test_case)
            self.test_results.append(result)

        # Run performance tests
        await self._run_performance_tests()

        # Generate test report
        self._generate_test_report()

    async def _run_single_test(self, test_case: dict) -> dict:
        """Run a single test case"""
        start_time = asyncio.get_running_loop().time()

        try:
            # Create query request
            request = QueryRequest(
                query=test_case["query"], user_id="integration-test-user"
            )

            # Process through pipeline
            response = await self.orchestrator.process_query(request)

            # Calculate test duration
            duration = (asyncio.get_running_loop().time() - start_time) * 1000

            # Analyze response quality
            quality_score = self._analyze_response_quality(response, test_case)

            # Print results
            print(f"✅ Pipeline completed successfully!")
            print(f"📊 Performance Metrics:")
            print(f"   - Duration: {duration:.0f}ms")
            print(f"   - Model: {response.performance_metrics['model_used']}")
            print(f"   - Tokens: {response.performance_metrics['tokens_used']}")
            print(f"   - Confidence: {response.performance_metrics['confidence']:.3f}")
            print(f"   - Sources: {response.performance_metrics['sources_count']}")

            print(f"📈 Quality Metrics:")
            print(f"   - Relevance: {response.quality_metrics.relevance_score:.3f}")
            print(f"   - Confidence: {response.quality_metrics.confidence}")
            print(f"   - Quality Score: {quality_score:.3f}")

            print(f"\n💬 Response Preview:")
            print(f"{response.response[:200]}...")

            print(f"\n📚 Top Sources:")
            for j, result in enumerate(response.search_results[:2], 1):
                print(f"   {j}. {result.source_filename} (page {result.page_number})")
                print(f"      Similarity: {result.similarity_score:.3f}")

            return {
                "test_case": test_case,
                "success": True,
                "duration_ms": duration,
                "quality_score": quality_score,
                "response": response,
                "error": None,
            }

        except Exception as e:
            duration = (asyncio.get_running_loop().time() - start_time) * 1000
            print(f"❌ Test failed: {e}")

            return {
                "test_case": test_case,
                "success": False,
                "duration_ms": duration,
                "quality_score": 0.0,
                "response": None,
                "error": str(e),
            }

    def _analyze_response_quality(self, response, test_case: dict) -> float:
        """Analyze the quality of the response"""
        if not response or not response.response:
            return 0.0

        # Check if response contains expected topics
        response_lower = response.response.lower()
        expected_topics = test_case["expected_topics"]

        topic_matches = sum(
            1 for topic in expected_topics if topic.lower() in response_lower
        )
        topic_score = topic_matches / len(expected_topics) if expected_topics else 0.0

        # Combine with existing quality metrics
        existing_quality = response.quality_metrics.relevance_score
        confidence_score = response.performance_metrics.get("confidence", 0.0)

        # Weighted average
        final_score = (
            topic_score * 0.4 + existing_quality * 0.4 + confidence_score * 0.2
        )

        return min(final_score, 1.0)

    async def _run_performance_tests(self):
        """Run performance and stress tests"""
        print(f"\n{'='*80}")
        print("📊 Performance Tests")
        print(f"{'='*80}")

        try:
            # Get pipeline metrics
            metrics = await self.orchestrator.get_pipeline_metrics()

            print(f"Pipeline Performance Metrics:")
            print(f"   - Total queries: {metrics.get('total_queries', 0)}")
            print(f"   - Successful queries: {metrics.get('successful_queries', 0)}")
            print(
                f"   - Average response time: {metrics.get('avg_response_time_ms', 0)}ms"
            )
            print(f"   - Success rate: {metrics.get('success_rate', 0):.1%}")

            if "recent_queries" in metrics:
                print(f"\nRecent queries:")
                for query in metrics["recent_queries"][:5]:
                    print(
                        f"   - {query['query']} ({query['status']}) - {query['response_time_ms']}ms"
                    )

        except Exception as e:
            print(f"❌ Error getting performance metrics: {e}")

    def _generate_test_report(self):
        """Generate a comprehensive test report"""
        print(f"\n{'='*80}")
        print("📋 Integration Test Report")
        print(f"{'='*80}")

        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - successful_tests

        # Calculate average metrics
        successful_results = [r for r in self.test_results if r["success"]]
        avg_duration = (
            sum(r["duration_ms"] for r in successful_results) / len(successful_results)
            if successful_results
            else 0
        )
        avg_quality = (
            sum(r["quality_score"] for r in successful_results)
            / len(successful_results)
            if successful_results
            else 0
        )

        print(f"Test Summary:")
        print(f"   - Total tests: {total_tests}")
        print(f"   - Successful: {successful_tests}")
        print(f"   - Failed: {failed_tests}")
        print(f"   - Success rate: {successful_tests/total_tests:.1%}")

        print(f"\nPerformance Summary:")
        print(f"   - Average duration: {avg_duration:.0f}ms")
        print(f"   - Average quality score: {avg_quality:.3f}")

        print(f"\nDetailed Results:")
        for i, result in enumerate(self.test_results, 1):
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"   {i}. {result['test_case']['name']}: {status}")
            if result["success"]:
                print(
                    f"      Duration: {result['duration_ms']:.0f}ms, Quality: {result['quality_score']:.3f}"
                )
            else:
                print(f"      Error: {result['error']}")

        # Overall assessment
        if successful_tests == total_tests and avg_quality > 0.6:
            print(f"\n🎉 All tests passed! Query pipeline is working correctly.")
        elif successful_tests >= total_tests * 0.8:
            print(f"\n⚠️  Most tests passed. Some issues need attention.")
        else:
            print(f"\n❌ Multiple test failures. Pipeline needs debugging.")


async def main():
    """Main test runner"""
    test_suite = TestQueryPipelineIntegration()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
