"""Integration test for embedding step orchestrator."""

import asyncio
import sys
import os
from uuid import UUID
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from pipeline.indexing.orchestrator import get_indexing_orchestrator
from pipeline.shared.progress_tracker import ProgressTracker
from services.pipeline_service import PipelineService
from config.database import get_supabase_client
from models import PipelineStatus


async def test_embedding_step_orchestrator():
    """Test the embedding step with real data from a previous run."""

    # Use the same run ID from the chunking test
    existing_run_id = "b1758e7b-4e9f-4afd-8d2b-8adc43f872ec"
    document_id = "550e8400-e29b-41d4-a716-446655440000"  # Test document ID

    print(f"🧪 Testing embedding step with run ID: {existing_run_id}")
    print(f"📄 Document ID: {document_id}")

    try:
        # Initialize database and services
        db = get_supabase_client()
        pipeline_service = PipelineService(db)

        # Get the existing indexing run
        indexing_run = await pipeline_service.get_indexing_run(UUID(existing_run_id))
        if not indexing_run:
            print(f"❌ Indexing run {existing_run_id} not found")
            return False

        print(f"✅ Found indexing run: {indexing_run.id}")
        print(f"   Status: {indexing_run.status}")
        print(f"   Started: {indexing_run.started_at}")

        # Get chunking step result to see what data we have
        chunking_result = await pipeline_service.get_step_result(
            UUID(existing_run_id), "chunking"
        )
        if not chunking_result:
            print("❌ No chunking step result found")
            return False

        print(f"✅ Found chunking step result:")
        print(f"   Status: {chunking_result.status}")
        print(f"   Duration: {chunking_result.duration_seconds:.2f} seconds")

        if chunking_result.status != "completed":
            print("❌ Chunking step not completed, cannot test embedding")
            return False

        chunks = chunking_result.data.get("chunks", [])
        print(f"✅ Found {len(chunks)} chunks from chunking step")

        # Initialize orchestrator
        print("🔧 Initializing orchestrator...")
        orchestrator = await get_indexing_orchestrator(db=db)

        # Initialize steps (this is required to set up the embedding_step)
        user_id = "123e4567-e89b-12d3-a456-426614174000"  # Test user ID
        await orchestrator.initialize_steps(user_id=UUID(user_id))
        print("✅ Steps initialized")

        # Check if embedding step was initialized
        if orchestrator.embedding_step is None:
            print("❌ Embedding step is None - initialization failed")
            return False
        else:
            print("✅ Embedding step initialized successfully")

        # Test embedding step directly
        print("\n🚀 Testing embedding step...")
        embedding_result = await orchestrator.embedding_step.execute(
            chunking_result, UUID(existing_run_id), UUID(document_id)
        )

        # Check result
        if embedding_result.status == "completed":
            print("✅ Embedding step completed successfully")
            print(f"   Duration: {embedding_result.duration_seconds:.2f} seconds")

            # Show summary stats
            summary = embedding_result.summary_stats
            print(f"   Chunks processed: {summary.get('chunks_processed', 0)}")
            print(f"   Embeddings generated: {summary.get('embeddings_generated', 0)}")
            print(
                f"   Average time per chunk: {summary.get('average_embedding_time', 0):.3f}s"
            )

            # Show sample outputs
            if embedding_result.sample_outputs:
                print("   Sample outputs:")
                for key, value in embedding_result.sample_outputs.items():
                    if isinstance(value, dict) and "embedding_preview" in value:
                        print(f"     - {key}: {value['embedding_preview']}")
                        print(f"       Content: {value['content_preview']}")

            # Verify embeddings were stored in database
            print("\n🔍 Verifying database storage...")
            chunks_with_embeddings = (
                await orchestrator.embedding_step.get_chunks_for_embedding(
                    UUID(existing_run_id), UUID(document_id)
                )
            )

            chunks_with_embeddings = [
                c for c in chunks_with_embeddings if c.get("embedding") is not None
            ]
            print(f"   Chunks with embeddings in DB: {len(chunks_with_embeddings)}")

            if chunks_with_embeddings:
                sample_chunk = chunks_with_embeddings[0]
                embedding = sample_chunk.get("embedding", [])
                print(f"   Sample embedding dimensions: {len(embedding)}")
                print(f"   Embedding model: {sample_chunk.get('embedding_model')}")
                print(
                    f"   Embedding provider: {sample_chunk.get('embedding_provider')}"
                )

            return True
        else:
            print(f"❌ Embedding step failed: {embedding_result.status}")
            if embedding_result.error:
                print(f"   Error: {embedding_result.error}")
            return False

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_embedding_step_orchestrator())
    if success:
        print("\n🎉 Embedding step integration test successful!")
    else:
        print("\n❌ Embedding step integration test failed!")
        sys.exit(1)
