import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.config.database import get_supabase_admin_client


async def check_embedding_dimensions():
    """Check the actual embedding dimensions in the database"""

    print("Checking embedding dimensions in production database...")

    try:
        db = get_supabase_admin_client()

        # Get a sample chunk with embedding
        response = (
            db.table("document_chunks")
            .select("embedding_1024,embedding_model")
            .not_.is_("embedding_1024", "null")
            .limit(1)
            .execute()
        )

        if response.data:
            chunk = response.data[0]
            embedding = chunk["embedding_1024"]
            model = chunk.get("embedding_model", "unknown")

            print(f"✓ Found embedding with model: {model}")
            print(f"✓ Embedding type: {type(embedding)}")
            print(f"✓ Embedding length: {len(embedding) if embedding else 'None'}")
            print(f"✓ First few values: {embedding[:5] if embedding else 'None'}")

            # Check if it's a list of floats
            if embedding and isinstance(embedding, list):
                print(
                    f"✓ All values are floats: {all(isinstance(x, (int, float)) for x in embedding[:10])}"
                )

        else:
            print("❌ No embeddings found")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(check_embedding_dimensions())
