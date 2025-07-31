import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
from src.pipeline.querying.models import QueryRequest


async def test_complete_query_pipeline():
    """Test the complete query pipeline end-to-end"""

    print("🚀 Testing Complete Query Pipeline...")

    # Initialize the orchestrator
    orchestrator = QueryPipelineOrchestrator()

    # Test queries
    test_queries = [
        "Hvad er principperne for regnvandshåndtering?",
        "Hvad koster en normal sag ift. en vanskelig sag?",
        "Hvad omfatter arbejdet?",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"📝 Test Query {i}: {query}")
        print(f"{'='*60}")

        try:
            # Create query request
            request = QueryRequest(query=query, user_id="test-user-123")

            # Process the query through the complete pipeline
            print("🔄 Processing query through pipeline...")
            response = await orchestrator.process_query(request)

            # Display results
            print(f"✅ Pipeline completed successfully!")
            print(f"📊 Performance Metrics:")
            print(f"   - Model used: {response.performance_metrics['model_used']}")
            print(f"   - Tokens used: {response.performance_metrics['tokens_used']}")
            print(f"   - Confidence: {response.performance_metrics['confidence']:.3f}")
            print(f"   - Sources: {response.performance_metrics['sources_count']}")

            print(f"📈 Quality Metrics:")
            print(f"   - Relevance: {response.quality_metrics.relevance_score:.3f}")
            print(f"   - Confidence: {response.quality_metrics.confidence}")
            print(f"   - Top similarity: {response.quality_metrics.top_similarity:.3f}")
            print(f"   - Result count: {response.quality_metrics.result_count}")

            print(f"\n💬 Generated Response:")
            print(f"{response.response}")

            print(f"\n📚 Sources:")
            for j, result in enumerate(response.search_results[:3], 1):
                print(f"   {j}. {result.source_filename} (page {result.page_number})")
                print(f"      Similarity: {result.similarity_score:.3f}")
                print(f"      Content: {result.content[:150]}...")
                print()

        except Exception as e:
            print(f"❌ Error processing query: {e}")
            import traceback

            traceback.print_exc()

    # Test pipeline metrics
    print(f"\n{'='*60}")
    print("📊 Pipeline Metrics")
    print(f"{'='*60}")

    try:
        metrics = await orchestrator.get_pipeline_metrics()
        print(f"Total queries: {metrics.get('total_queries', 0)}")
        print(f"Successful queries: {metrics.get('successful_queries', 0)}")
        print(f"Average response time: {metrics.get('avg_response_time_ms', 0)}ms")
        print(f"Success rate: {metrics.get('success_rate', 0):.1%}")

        if "recent_queries" in metrics:
            print(f"\nRecent queries:")
            for query in metrics["recent_queries"][:5]:
                print(
                    f"  - {query['query']} ({query['status']}) - {query['response_time_ms']}ms"
                )

    except Exception as e:
        print(f"❌ Error getting metrics: {e}")


if __name__ == "__main__":
    asyncio.run(test_complete_query_pipeline())
