#!/usr/bin/env python3
"""
Test the unified processing method with multiple PDFs (simple version without DB)
"""

import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.pipeline.indexing.orchestrator import get_indexing_orchestrator
from src.pipeline.shared.models import DocumentInput, UploadType

async def test_unified_processing_simple():
    """Test the unified processing method with multiple PDFs (simple version)"""
    
    print("🧪 Testing Unified Processing Method (Simple)")
    print("=" * 60)
    
    # Test with multiple PDFs
    pdf_folder = Path("../data/external/construction_pdfs/multiple-pdf-project")
    pdf_files = list(pdf_folder.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found")
        return
    
    print(f"📄 Found {len(pdf_files)} PDF files:")
    for pdf in pdf_files:
        print(f"   - {pdf.name}")
    
    # Create document inputs for all PDFs
    document_inputs = []
    for i, pdf in enumerate(pdf_files):
        document_input = DocumentInput(
            document_id=UUID(f"00000000-0000-0000-0000-{i+1:012d}"),  # Unique ID for each
            run_id=UUID("00000000-0000-0000-0000-000000000002"),  # Same run ID
            user_id=None,
            file_path=str(pdf.absolute()),  # Use local file path
            filename=pdf.name,
            upload_type=UploadType.EMAIL,
            upload_id="unified-test",
            index_run_id=UUID("00000000-0000-0000-0000-000000000003"),
            metadata={"email": "unified@test.com"},
        )
        document_inputs.append(document_input)
    
    try:
        # Initialize orchestrator with test storage to avoid DB operations
        print("\n🔧 Initializing orchestrator with test storage...")
        from src.pipeline.indexing.orchestrator import IndexingOrchestrator
        orchestrator = IndexingOrchestrator(use_test_storage=True)
        
        # Initialize steps
        print("🔧 Initializing pipeline steps...")
        await orchestrator.initialize_steps(document_inputs[0].user_id)
        
        # Test the individual steps processing (this is the core logic we want to test)
        print(f"\n🚀 Testing individual steps processing with {len(document_inputs)} documents...")
        
        # Create a simple progress tracker
        from src.pipeline.shared.progress_tracker import ProgressTracker
        progress_tracker = ProgressTracker(document_inputs[0].index_run_id, None)
        
        # Test the core processing logic
        document_results = await orchestrator._process_documents_individual_steps(
            document_inputs, document_inputs[0].index_run_id, progress_tracker
        )
        
        # Check results
        failed_document_ids = [
            doc_id for doc_id, result in document_results.items() if not result
        ]
        successful_document_ids = [
            doc_id for doc_id, result in document_results.items() if result
        ]
        
        print(f"\n📊 Results:")
        print(f"   Successful documents: {len(successful_document_ids)}")
        print(f"   Failed documents: {len(failed_document_ids)}")
        
        if successful_document_ids:
            print("✅ Individual steps processing completed successfully!")
            print(f"   Successful: {successful_document_ids}")
        else:
            print("❌ All documents failed during individual steps processing")
        
        if failed_document_ids:
            print(f"   Failed: {failed_document_ids}")
        
    except Exception as e:
        print(f"❌ Error during unified processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_unified_processing_simple()) 