import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.pipeline.querying.steps.retrieval import DocumentRetriever, RetrievalConfig
from src.pipeline.querying.steps.generation import ResponseGenerator, GenerationConfig
from src.pipeline.querying.models import QueryVariations


async def test_generation_step():
    """Test the generation step with retrieval results"""

    print("Testing Generation Step...")

    # Setup retrieval config
    retrieval_config_dict = {
        "embedding_model": "voyage-multilingual-2",
        "dimensions": 1024,
        "similarity_metric": "cosine",
        "top_k": 3,  # Reduced for testing
        "similarity_thresholds": {
            "excellent": 0.75,
            "good": 0.60,
            "acceptable": 0.40,
            "minimum": 0.25,
        },
        "danish_thresholds": {
            "excellent": 0.70,
            "good": 0.55,
            "acceptable": 0.35,
            "minimum": 0.20,
        },
    }

    # Setup generation config
    generation_config_dict = {
        "provider": "openrouter",
        "model": "anthropic/claude-3.5-sonnet",
        "fallback_models": ["openai/gpt-3.5-turbo"],
        "timeout_seconds": 10.0,
        "max_tokens": 500,  # Reduced for testing
        "temperature": 0.1,
        "response_format": {
            "include_citations": True,
            "include_confidence": True,
            "language": "danish",
        },
    }

    retrieval_config = RetrievalConfig(retrieval_config_dict)
    generation_config = GenerationConfig(**generation_config_dict)

    retriever = DocumentRetriever(retrieval_config)
    generator = ResponseGenerator(generation_config)

    # Test query
    query = "Hvad er principperne for regnvandshåndtering?"
    print(f"\n--- Testing Query: {query} ---")

    try:
        # Step 1: Retrieve documents
        print("1. Retrieving documents...")
        variations = QueryVariations(original=query)
        search_results = await retriever.search(variations)

        print(f"   Retrieved {len(search_results)} documents")
        for i, result in enumerate(search_results):
            print(
                f"   - Doc {i+1}: {result.content[:100]}... (similarity: {result.similarity_score:.3f})"
            )

        # Step 2: Generate response
        print("\n2. Generating response...")
        generation_result = await generator.execute(search_results)

        if generation_result.status == "completed":
            response = generation_result.data["response"]
            print(f"   ✓ Response generated successfully!")
            print(f"   Model used: {response['performance_metrics']['model_used']}")
            print(f"   Tokens used: {response['performance_metrics']['tokens_used']}")
            print(f"   Confidence: {response['performance_metrics']['confidence']:.3f}")
            print(f"   Quality: {response['quality_metrics']['relevance_score']:.3f}")

            print(f"\n--- GENERATED RESPONSE ---")
            print(response["response"])

            print(f"\n--- SOURCES ---")
            for i, result in enumerate(response["search_results"][:3]):
                print(
                    f"   Source {i+1}: {result['source_filename']} (page {result['page_number']})"
                )
                print(f"   Similarity: {result['similarity_score']:.3f}")
                print(f"   Content: {result['content'][:200]}...")
                print()

        else:
            print(f"   ❌ Generation failed: {generation_result.error_message}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_generation_step())
