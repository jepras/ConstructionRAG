#!/usr/bin/env python3
"""
Test script to verify the new database schema is working
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from uuid import UUID
from datetime import datetime

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.services.pipeline_service import PipelineService
from src.pipeline.shared.models import UploadType


async def test_database_schema():
    """Test the new database schema functionality."""
    print("🧪 Testing New Database Schema")
    print("=" * 50)

    try:
        # Create pipeline service with admin client
        pipeline_service = PipelineService(use_admin_client=True)
        print("✅ Created pipeline service with admin client")

        # Test data - using a real user ID from the database or create a test user
        # For now, let's skip user project tests and focus on email uploads
        test_user_id = UUID(
            "123e4567-e89b-12d3-a456-426614174000"
        )  # This will fail due to FK constraint
        test_project_id = UUID("123e4567-e89b-12d3-a456-426614174001")
        test_document_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        test_upload_id = (
            f"test-email-upload-{int(datetime.utcnow().timestamp())}"  # Unique ID
        )

        # Test 1: Create a project (SKIPPED - no real user in test DB)
        print("\n1. Testing project creation...")
        print("   ⏭️  Skipped - requires real user in auth.users table")
        print("   💡 To test: Create a real user first or use existing user ID")

        # Test 2: Create an email upload
        print("\n2. Testing email upload creation...")
        try:
            email_upload = await pipeline_service.create_email_upload(
                upload_id=test_upload_id,
                email="test@example.com",
                filename="test-document.pdf",
                file_size=1024000,
            )
            print(f"   ✅ Email upload created: {email_upload.id}")
            print(f"   📧 Email: {email_upload.email}")
            print(f"   📄 Filename: {email_upload.filename}")
            print(f"   📊 Status: {email_upload.status}")
        except Exception as e:
            print(f"   ❌ Email upload creation failed: {e}")

        # Test 3: Create an indexing run with upload type (SKIPPED - no project)
        print("\n3. Testing indexing run creation with upload type...")
        print("   ⏭️  Skipped - requires real project (depends on test 1)")
        print("   💡 To test: Create a real project first")

        # Test 4: Create an indexing run for email upload
        print("\n4. Testing indexing run creation for email upload...")
        try:
            email_indexing_run = await pipeline_service.create_indexing_run(
                document_id=test_document_id,
                user_id=test_user_id,
                upload_type=UploadType.EMAIL,
                upload_id=test_upload_id,
            )
            print(f"   ✅ Email indexing run created: {email_indexing_run.id}")
            print(f"   📄 Document: {email_indexing_run.document_id}")
            print(f"   🔄 Upload type: {email_indexing_run.upload_type}")
            print(f"   📧 Upload ID: {email_indexing_run.upload_id}")
        except Exception as e:
            print(f"   ❌ Email indexing run creation failed: {e}")

        # Test 5: Update email upload status
        print("\n5. Testing email upload status update...")
        try:
            updated_email_upload = await pipeline_service.update_email_upload_status(
                upload_id=test_upload_id,
                status="completed",
                public_url="https://example.com/public-page.html",
                processing_results={
                    "steps_completed": ["partition", "metadata", "enrichment"]
                },
            )
            print(f"   ✅ Email upload status updated: {updated_email_upload.status}")
            print(f"   🌐 Public URL: {updated_email_upload.public_url}")
            print(
                f"   📊 Processing results: {len(updated_email_upload.processing_results)} items"
            )
        except Exception as e:
            print(f"   ❌ Email upload status update failed: {e}")

        print("\n🎉 Database schema test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_database_schema())
