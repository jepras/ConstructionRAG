#!/usr/bin/env python3
"""
Test the unified processing method with multiple PDFs
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

async def test_unified_processing():
    """Test the unified processing method with multiple PDFs"""
    
    print("🧪 Testing Unified Processing Method")
    print("=" * 50)
    
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
        # Initialize orchestrator
        print("\n🔧 Initializing orchestrator...")
        orchestrator = await get_indexing_orchestrator()
        
        # Initialize steps
        print("🔧 Initializing pipeline steps...")
        await orchestrator.initialize_steps(document_inputs[0].user_id)
        
        # Test unified processing
        print(f"\n🚀 Testing unified processing with {len(document_inputs)} documents...")
        success = await orchestrator.process_documents(document_inputs)
        
        if success:
            print("✅ Unified processing completed successfully!")
        else:
            print("❌ Unified processing failed!")
        
    except Exception as e:
        print(f"❌ Error during unified processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_unified_processing()) 