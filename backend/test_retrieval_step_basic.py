import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.pipeline.querying.steps.retrieval import DocumentRetriever, RetrievalConfig
from src.pipeline.querying.models import QueryVariations


async def test_retrieval_step_basic():
    """Test basic retrieval step functionality"""

    print("Testing retrieval step...")

    # Check if required environment variables are available
    if not os.getenv("VOYAGE_API_KEY"):
        print("❌ VOYAGE_API_KEY not found in environment")
        print("💡 Please add your Voyage API key to .env file")
        return

    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"):
        print("❌ Supabase credentials not found in environment")
        print("💡 Please add SUPABASE_URL and SUPABASE_ANON_KEY to .env file")
        return

    # Create config
    config_dict = {
        "embedding_model": "voyage-multilingual-2",
        "dimensions": 1024,
        "similarity_metric": "cosine",
        "top_k": 3,
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

    config = RetrievalConfig(config_dict)

    # Create retriever
    retriever = DocumentRetriever(config)

    # Test query variations
    test_variations = QueryVariations(
        original="Hvordan installerer jeg en varmepumpe?",
        semantic="Hvilke tekniske specifikationer skal jeg være opmærksom på ved installation af en varmepumpe?",
        hyde="For at installere en varmepumpe korrekt og effektivt, er det vigtigt at følge en række tekniske specifikationer...",
        formal="Hvordan udføres installationen af en luft-til-vand varmepumpe i overensstemmelse med gældende bygningsregler?",
    )

    print(f"Testing with query: {test_variations.original}")
    print("Searching documents...")

    # Test validation
    is_valid = await retriever.validate_prerequisites_async(test_variations)
    print(f"✓ Validation passed: {is_valid}")

    if not is_valid:
        print("❌ Validation failed")
        return

    # Test search
    try:
        results = await retriever.search(test_variations)

        print(f"✓ Retrieved {len(results)} results")

        for i, result in enumerate(results[:2]):  # Show first 2 results
            print(f"  Result {i+1}:")
            print(f"    Content: {result.content[:100]}...")
            print(f"    Similarity: {result.similarity_score:.3f}")
            print(f"    Source: {result.source_filename}")
            print(f"    Page: {result.page_number}")
            print()

        print("✓ All retrieval tests passed!")

    except Exception as e:
        print(f"❌ Search failed: {e}")
        return


if __name__ == "__main__":
    asyncio.run(test_retrieval_step_basic())
