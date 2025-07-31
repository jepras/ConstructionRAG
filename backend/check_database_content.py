import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.config.database import get_supabase_client


async def check_database_content():
    """Check what's actually in the database"""

    print("Checking database content...")

    db = get_supabase_client()

    # Check documents table
    print("\n=== Documents Table ===")
    try:
        response = db.table("documents").select("*").limit(5).execute()
        documents = response.data
        print(f"✓ Found {len(documents)} documents")

        if documents:
            for doc in documents:
                print(
                    f"  Document: {doc.get('filename', 'Unknown')} - Status: {doc.get('status', 'Unknown')}"
                )
    except Exception as e:
        print(f"❌ Error checking documents: {e}")

    # Check document_chunks table
    print("\n=== Document Chunks Table ===")
    try:
        response = db.table("document_chunks").select("*").limit(5).execute()
        chunks = response.data
        print(f"✓ Found {len(chunks)} total document chunks")

        if chunks:
            print("\nSample chunks:")
            for i, chunk in enumerate(chunks[:3]):
                print(f"  Chunk {i+1}:")
                print(f"    ID: {chunk['id']}")
                print(f"    Content: {chunk['content'][:100]}...")
                print(f"    Document ID: {chunk.get('document_id')}")
                print(f"    Indexing Run ID: {chunk.get('indexing_run_id')}")
                print(
                    f"    Has embedding_1024: {chunk.get('embedding_1024') is not None}"
                )
                print(f"    Embedding model: {chunk.get('embedding_model')}")
                print()
    except Exception as e:
        print(f"❌ Error checking chunks: {e}")

    # Check indexing_runs table
    print("\n=== Indexing Runs Table ===")
    try:
        response = db.table("indexing_runs").select("*").limit(5).execute()
        runs = response.data
        print(f"✓ Found {len(runs)} indexing runs")

        if runs:
            for run in runs:
                print(
                    f"  Run: {run.get('id')} - Status: {run.get('status', 'Unknown')}"
                )
    except Exception as e:
        print(f"❌ Error checking indexing runs: {e}")

    # Check for chunks without embeddings
    print("\n=== Chunks Without Embeddings ===")
    try:
        response = (
            db.table("document_chunks")
            .select("*")
            .is_("embedding_1024", "null")
            .limit(5)
            .execute()
        )
        chunks_without_embeddings = response.data
        print(f"✓ Found {len(chunks_without_embeddings)} chunks without embeddings")

        if chunks_without_embeddings:
            print("These chunks need to be processed by the embedding step")
    except Exception as e:
        print(f"❌ Error checking chunks without embeddings: {e}")

    # Check for chunks with embeddings
    print("\n=== Chunks With Embeddings ===")
    try:
        response = (
            db.table("document_chunks")
            .select("*")
            .not_.is_("embedding_1024", "null")
            .limit(5)
            .execute()
        )
        chunks_with_embeddings = response.data
        print(f"✓ Found {len(chunks_with_embeddings)} chunks with embeddings")

        if chunks_with_embeddings:
            print("These chunks are ready for retrieval")
            for chunk in chunks_with_embeddings[:2]:
                print(f"  - {chunk.get('id')} - Model: {chunk.get('embedding_model')}")
    except Exception as e:
        print(f"❌ Error checking chunks with embeddings: {e}")


if __name__ == "__main__":
    asyncio.run(check_database_content())
