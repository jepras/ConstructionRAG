import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.config.database import get_supabase_admin_client


async def test_production_db():
    """Test connection to production database and check for data"""

    print("Testing production database connection...")

    # Check environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

    print(f"Supabase URL: {supabase_url}")
    print(f"Anon Key: {supabase_anon_key[:20]}..." if supabase_anon_key else "None")

    if not supabase_url or not supabase_anon_key:
        print("❌ Missing Supabase credentials")
        return

    try:
        db = get_supabase_admin_client()
        print("✓ Successfully created Supabase admin client")

        # Test connection with a simple query
        print("\n=== Testing Connection ===")
        response = db.table("document_chunks").select("count", count="exact").execute()
        print(f"✓ Connection successful - Total chunks: {response.count}")

        # Check for chunks with embeddings
        print("\n=== Checking for Chunks with Embeddings ===")
        response = (
            db.table("document_chunks")
            .select("count", count="exact")
            .not_.is_("embedding_1024", "null")
            .execute()
        )
        print(f"✓ Chunks with embeddings: {response.count}")

        if response.count > 0:
            # Get a sample chunk with embedding
            sample_response = (
                db.table("document_chunks")
                .select("id,content,metadata,embedding_model")
                .not_.is_("embedding_1024", "null")
                .limit(1)
                .execute()
            )
            if sample_response.data:
                chunk = sample_response.data[0]
                print(f"✓ Sample chunk found:")
                print(f"  ID: {chunk['id']}")
                print(f"  Content: {chunk['content'][:100]}...")
                print(f"  Embedding model: {chunk.get('embedding_model')}")

                # Test the retrieval step with this data
                print("\n=== Testing Retrieval Step ===")
                from src.pipeline.querying.steps.retrieval import (
                    DocumentRetriever,
                    RetrievalConfig,
                )
                from src.pipeline.querying.models import QueryVariations

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
                retriever = DocumentRetriever(config)

                # Test with the specific queries you mentioned
                test_queries = [
                    "Hvad er principperne for regnvandshåndtering?",
                    "Hvad koster en normal sag ift. en vanskelig sag?",
                    "Hvad omfatter arbejdet?",
                ]

                for query in test_queries:
                    print(f"\n--- Testing Query: {query} ---")
                    variations = QueryVariations(original=query)

                    try:
                        results = await retriever.search(variations)
                        print(f"✓ Retrieved {len(results)} results")

                        for i, result in enumerate(results[:2]):
                            print(f"  Result {i+1}:")
                            print(f"    Content: {result.content[:150]}...")
                            print(f"    Similarity: {result.similarity_score:.3f}")
                            print(f"    Source: {result.source_filename}")
                            print()

                    except Exception as e:
                        print(f"❌ Search failed: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_production_db())
