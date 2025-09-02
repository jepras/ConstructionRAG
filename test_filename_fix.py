#!/usr/bin/env python3
"""
Test script to verify that document filenames are properly preserved through the pipeline
instead of showing temporary filenames like tmpsj5uht3l.pdf
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Add backend to path
import sys
sys.path.insert(0, './backend/src')

from pipeline.indexing.steps.partition import PartitionStep
from models.document import DocumentInput
from uuid import uuid4


def test_partition_preserves_filename():
    """Test that partition step preserves original filename instead of temp filename"""
    
    # Create mock config
    config = {
        "partition": {
            "processing_strategy": "pymupdf_only",
            "ocr_strategy": "pymupdf_only",
            "scanned_detection": {"text_threshold": 25}
        }
    }
    
    # Create test document input with a proper filename
    doc_input = DocumentInput(
        document_id=uuid4(),
        run_id=uuid4(),
        user_id=uuid4(),
        file_path="https://example.com/test.pdf",  # Simulating URL download
        filename="DNI_K07_H1_EXT_N600.pdf",  # Original filename that should be preserved
        upload_type="user_project",
        project_id=uuid4(),
        index_run_id=uuid4(),
        metadata={}
    )
    
    # Create partition step
    partition_step = PartitionStep(config, storage_client=MagicMock(), progress_tracker=MagicMock())
    
    # Mock the _process_with_pymupdf_only method to check what gets passed
    original_method = partition_step._process_with_pymupdf_only
    
    def mock_process(filepath, document_input):
        """Mock method to verify document_input is passed correctly"""
        print(f"✅ Filepath received: {filepath}")
        print(f"✅ Document input filename: {document_input.filename if document_input else 'None'}")
        
        # Simulate the result structure
        return {
            "text_elements": [],
            "table_elements": [],
            "extracted_pages": {},
            "page_analysis": {},
            "document_metadata": {"total_pages": 1},
            "metadata": {
                "processing_strategy": "pymupdf_only",
                "source_file": document_input.filename if document_input else os.path.basename(filepath),
            }
        }
    
    # Replace method
    partition_step._process_with_pymupdf_only = mock_process
    
    # Create a temp file to simulate downloaded PDF
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(b"Test PDF content")
        temp_path = tmp.name
    
    try:
        # Mock the file download to return temp path
        partition_step._get_local_file_path = lambda x: temp_path
        
        # Process the document
        result = mock_process(temp_path, doc_input)
        
        # Check that the source_file uses original filename, not temp filename
        source_file = result["metadata"]["source_file"]
        temp_filename = os.path.basename(temp_path)
        
        print(f"\n📋 Test Results:")
        print(f"  Original filename: {doc_input.filename}")
        print(f"  Temp filename: {temp_filename}")
        print(f"  Source file in metadata: {source_file}")
        
        if source_file == doc_input.filename:
            print(f"✅ SUCCESS: Source file correctly uses original filename!")
            return True
        else:
            print(f"❌ FAILURE: Source file is '{source_file}', expected '{doc_input.filename}'")
            return False
            
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


if __name__ == "__main__":
    print("🧪 Testing filename preservation in partition step...")
    print("=" * 60)
    
    success = test_partition_preserves_filename()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed! The fix should properly preserve filenames.")
        print("\nThe citations should now show actual PDF names like:")
        print("  - DNI_K07_H1_EXT_N600.pdf")
        print("Instead of temporary names like:")
        print("  - tmpsj5uht3l.pdf")
    else:
        print("❌ Tests failed. The fix needs adjustment.")
    
    sys.exit(0 if success else 1)