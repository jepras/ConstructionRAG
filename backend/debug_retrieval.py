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


async def debug_retrieval():
    """Debug the retrieval step to understand duplicate results"""

    print("Debugging retrieval step...")

    config_dict = {
        "embedding_model": "voyage-multilingual-2",
        "dimensions": 1024,
        "similarity_metric": "cosine",
        "top_k": 5,  # Increased to see more results
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
    retriever = DocumentRetriever(config)

    # Test with one query
    query = "Hvad er principperne for regnvandshåndtering?"
    print(f"\n--- Testing Query: {query} ---")

    variations = QueryVariations(original=query)

    try:
        # Get raw results before filtering
        print("Getting raw search results...")
        query_embedding = await retriever.embed_query(query)
        raw_results = await retriever.search_pgvector(query_embedding)

        print(f"Raw results count: {len(raw_results)}")

        # Show first few raw results
        for i, result in enumerate(raw_results[:5]):
            print(f"  Raw Result {i+1}:")
            print(f"    ID: {result['id']}")
            print(f"    Content preview: {result['content'][:100]}...")
            print(f"    Similarity score: {result['similarity_score']}")
            print()

        # Now test the full search with filtering
        print("Testing full search with filtering...")
        results = await retriever.search(variations)

        print(f"Filtered results count: {len(results)}")

        # Show all results with more detail
        for i, result in enumerate(results):
            print(f"  Filtered Result {i+1}:")
            print(f"    ID: {result.chunk_id}")
            print(f"    Content: {result.content[:150]}...")
            print(f"    Similarity: {result.similarity_score:.3f}")
            print(f"    Source: {result.source_filename}")
            print(f"    Page: {result.page_number}")
            print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_retrieval())
