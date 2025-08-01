#!/usr/bin/env python3
"""
Simple test script to verify the new storage structure is working
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from uuid import UUID

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.services.storage_service import StorageService, UploadType


async def test_storage_structure():
    """Test the new storage structure methods."""
    print("🧪 Testing New Storage Structure")
    print("=" * 50)

    try:
        # Create test storage service
        storage = StorageService.create_test_storage()
        print("✅ Created test storage service")

        # Test data
        test_user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        test_project_id = UUID("123e4567-e89b-12d3-a456-426614174001")
        test_index_run_id = UUID("123e4567-e89b-12d3-a456-426614174002")
        test_document_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        test_upload_id = "test-upload-123"

        # Test 1: Create storage structure for user project
        print("\n1. Testing user project storage structure...")
        success = await storage.create_storage_structure(
            upload_type=UploadType.USER_PROJECT,
            user_id=test_user_id,
            project_id=test_project_id,
            index_run_id=test_index_run_id,
        )
        print(f"   ✅ Storage structure created: {success}")

        # Test 2: Create storage structure for email upload
        print("\n2. Testing email upload storage structure...")
        success = await storage.create_storage_structure(
            upload_type=UploadType.EMAIL,
            upload_id=test_upload_id,
        )
        print(f"   ✅ Email storage structure created: {success}")

        # Test 3: List files to see the structure
        print("\n3. Listing files in test bucket...")
        files = await storage.list_files("")
        print(f"   📁 Found {len(files)} files/folders in bucket")

        # Test 4: List user project structure
        print("\n4. Listing user project structure...")
        user_path = f"users/{test_user_id}/projects/{test_project_id}/index-runs/{test_index_run_id}"
        user_files = await storage.list_files(user_path)
        print(f"   📁 Found {len(user_files)} files in user project")

        # Test 5: List email upload structure
        print("\n5. Listing email upload structure...")
        email_path = f"email-uploads/{test_upload_id}"
        email_files = await storage.list_files(email_path)
        print(f"   📁 Found {len(email_files)} files in email upload")

        print("\n🎉 Storage structure test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Storage structure test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_storage_structure())
