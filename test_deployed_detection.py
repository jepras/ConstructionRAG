#!/usr/bin/env python3
"""Test the deployed vector drawing detection"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from src.pipeline.indexing.steps.partition import PartitionStep
from src.pipeline.indexing.models import (
    PartitionStepInput,
    DocumentMetadata
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

async def test_vector_detection():
    """Test vector drawing detection on the floor plan PDF"""
    
    # Initialize the partition step
    partition_step = PartitionStep()
    
    # Test PDF path
    pdf_path = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/small-complicated/DNI_K07_H1_ETX_N400 Belysningsplan st. og 1sal.pdf"
    
    # Create input
    input_data = PartitionStepInput(
        documents=[
            DocumentMetadata(
                id="test-doc",
                filename=os.path.basename(pdf_path),
                file_path=pdf_path,
                upload_type="test",
                indexing_run_id="test-run"
            )
        ],
        indexing_run_id="test-run"
    )
    
    print(f"Testing: {os.path.basename(pdf_path)}")
    print("=" * 80)
    
    # Run partition step - this will use the stage1_pymupdf_analysis internally
    result = await partition_step.run(input_data)
    
    # Check if vector drawings were detected
    for doc in result.documents:
        if doc.metadata and "page_analysis" in doc.metadata:
            print(f"\nDocument: {doc.filename}")
            for page_num, analysis in doc.metadata["page_analysis"].items():
                if analysis.get("has_vector_drawings", False):
                    print(f"  ✅ Page {page_num}: VECTOR DRAWING DETECTED")
                    print(f"     - Drawing items: {analysis.get('drawing_items', 0):,}")
                    print(f"     - Complexity: {analysis.get('complexity', 'unknown')}")
                    print(f"     - Needs extraction: {analysis.get('needs_extraction', False)}")
                elif analysis.get("drawing_items", 0) > 0:
                    print(f"  ⏭️ Page {page_num}: {analysis.get('drawing_items', 0):,} drawing items (below threshold)")
    
    return result

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_vector_detection())