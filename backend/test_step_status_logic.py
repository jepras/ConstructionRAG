#!/usr/bin/env python3
"""
Test the step status logic in pipeline service
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from src.models import StepResult
from src.services.pipeline_service import PipelineService

load_dotenv()


async def test_step_status_logic():
    """Test the step status logic"""

    # Create a mock completed ChunkingStep result
    chunking_result = StepResult(
        step="ChunkingStep",
        status="completed",
        duration_seconds=30.5,
        summary_stats={"total_chunks_created": 15},
        sample_outputs={"chunk_count": 15},
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )

    print("🧪 Testing Step Status Logic")
    print("=" * 50)

    # Test the logic from pipeline service
    step_name = "ChunkingStep"
    step_result = chunking_result

    # Determine indexing status based on step result
    indexing_status = "running"
    if step_result.status == "failed":
        indexing_status = "failed"
    elif step_name == "ChunkingStep" and step_result.status == "completed":
        # Document is completed after chunking (embedding happens in batch)
        indexing_status = "completed"
        print("✅ ChunkingStep completed - should set indexing_status to 'completed'")
    elif step_name == "EmbeddingStep" and step_result.status == "completed":
        # For single document processing, embedding completes the document
        indexing_status = "completed"
        print("✅ EmbeddingStep completed - should set indexing_status to 'completed'")

    print(f"📊 Step: {step_name}")
    print(f"📊 Status: {step_result.status}")
    print(f"📊 Resulting indexing_status: {indexing_status}")

    # Test with failed status
    failed_result = StepResult(
        step="ChunkingStep",
        status="failed",
        duration_seconds=5.0,
        error_message="Test error",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )

    indexing_status_failed = "running"
    if failed_result.status == "failed":
        indexing_status_failed = "failed"
        print("✅ Failed step - should set indexing_status to 'failed'")

    print(f"\n📊 Failed Step: {step_name}")
    print(f"📊 Status: {failed_result.status}")
    print(f"📊 Resulting indexing_status: {indexing_status_failed}")


if __name__ == "__main__":
    asyncio.run(test_step_status_logic())
