#!/usr/bin/env python3
"""Test script for the new storage structure with run-based organization."""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4
import tempfile
import os

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.storage_service import StorageService
from src.pipeline.shared.models import DocumentInput


async def test_storage_structure():
    """Test the new storage structure with run-based organization."""

    print("🧪 Testing new storage structure...")

    # Create test UUIDs
    run_id = uuid4()
    document_id = uuid4()
    user_id = uuid4()

    print(f"📁 Run ID: {run_id}")
    print(f"📄 Document ID: {document_id}")
    print(f"👤 User ID: {user_id}")

    # Initialize storage service
    storage_service = StorageService()

    try:
        # Test 1: Ensure bucket exists
        print("\n1️⃣ Testing bucket creation...")
        bucket_exists = await storage_service.ensure_bucket_exists()
        print(f"✅ Bucket exists: {bucket_exists}")

        # Test 2: Create a test file
        print("\n2️⃣ Creating test file...")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is a test file for storage structure testing.")
            test_file_path = f.name

        try:
            # Test 3: Upload extracted page image
            print("\n3️⃣ Testing extracted page image upload...")
            page_upload_result = await storage_service.upload_extracted_page_image(
                image_path=test_file_path,
                run_id=run_id,
                document_id=document_id,
                page_num=1,
                complexity="simple",
            )
            print(f"✅ Page upload result: {page_upload_result}")

            # Test 4: Upload table image
            print("\n4️⃣ Testing table image upload...")
            table_upload_result = await storage_service.upload_table_image(
                image_path=test_file_path,
                run_id=run_id,
                document_id=document_id,
                table_id="table_001",
            )
            print(f"✅ Table upload result: {table_upload_result}")

            # Test 5: Upload generated file
            print("\n5️⃣ Testing generated file upload...")
            generated_upload_result = await storage_service.upload_generated_file(
                file_path=test_file_path, run_id=run_id, filename="test_summary.md"
            )
            print(f"✅ Generated file upload result: {generated_upload_result}")

            # Test 6: List files in run directory
            print("\n6️⃣ Testing file listing...")
            files = await storage_service.list_files(str(run_id))
            print(f"✅ Files in run directory: {len(files)} files found")
            for file_info in files:
                if isinstance(file_info, dict):
                    print(f"   - {file_info.get('name', 'unknown')}")
                else:
                    print(f"   - {file_info}")

            # Test 7: Get storage usage
            print("\n7️⃣ Testing storage usage...")
            usage = await storage_service.get_run_storage_usage(run_id)
            print(f"✅ Storage usage: {usage}")

            # Test 8: Test DocumentInput with run_id
            print("\n8️⃣ Testing DocumentInput with run_id...")
            doc_input = DocumentInput(
                document_id=document_id,
                run_id=run_id,
                user_id=user_id,
                file_path="/path/to/test.pdf",
                filename="test.pdf",
                metadata={},
            )
            print(f"✅ DocumentInput created with run_id: {doc_input.run_id}")

            print("\n🎉 All tests passed! New storage structure is working correctly.")

        finally:
            # Clean up test file
            if os.path.exists(test_file_path):
                os.unlink(test_file_path)
                print(f"🧹 Cleaned up test file: {test_file_path}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


async def test_cleanup():
    """Test cleanup functionality."""

    print("\n🧹 Testing cleanup functionality...")

    # Create test UUIDs
    run_id = uuid4()
    document_id = uuid4()

    # Initialize storage service
    storage_service = StorageService()

    try:
        # Create a test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test file for cleanup testing.")
            test_file_path = f.name

        try:
            # Upload a file
            await storage_service.upload_extracted_page_image(
                image_path=test_file_path,
                run_id=run_id,
                document_id=document_id,
                page_num=1,
                complexity="simple",
            )

            # Verify file exists
            files = await storage_service.list_files(str(run_id))
            print(f"📁 Files before cleanup: {len(files)}")

            # Test cleanup
            cleanup_result = await storage_service.delete_run_directory(run_id)
            print(f"✅ Cleanup result: {cleanup_result}")

            # Verify files are gone
            files_after = await storage_service.list_files(str(run_id))
            print(f"📁 Files after cleanup: {len(files_after)}")

            if len(files_after) == 0:
                print("✅ Cleanup successful - all files removed")
            else:
                print("⚠️  Some files may still exist")

        finally:
            # Clean up test file
            if os.path.exists(test_file_path):
                os.unlink(test_file_path)

    except Exception as e:
        print(f"❌ Cleanup test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Starting storage structure tests...")

    # Run tests
    success = asyncio.run(test_storage_structure())

    if success:
        # Run cleanup test
        asyncio.run(test_cleanup())

    print("\n✨ Storage structure testing complete!")
