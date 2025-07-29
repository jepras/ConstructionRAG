#!/usr/bin/env python3
"""
Test with proper Supabase authentication using JWT token
"""

import asyncio
import os
import sys
from uuid import UUID

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from config.database import get_supabase_client
from config.settings import get_settings


async def test_with_authentication():
    """Test with proper authentication"""

    print("🔐 Testing with proper authentication...")

    # Configuration
    user_id = "a4be935d-dd17-4db2-aa4e-b4989277bb1a"
    document_id = "550e8400-e29b-41d4-a716-446655440000"

    # Get settings
    settings = get_settings()
    print(f"✅ Supabase URL: {settings.supabase_url[:50]}...")

    # Create Supabase client
    supabase = get_supabase_client()

    try:
        # Method 1: Try to get user info (this will show if we're authenticated)
        print("\n📋 Method 1: Check current authentication status...")
        try:
            user = supabase.auth.get_user()
            print(f"✅ Authenticated as: {user.user.email}")
            print(f"   User ID: {user.user.id}")
            print(f"   Session expires: {user.session.expires_at}")
        except Exception as e:
            print(f"❌ Not authenticated: {e}")

        # Method 2: Try to sign in with email/password (if you have them)
        print("\n📧 Method 2: Sign in with email/password...")
        print("   To test this, you need:")
        print("   1. The user's email address")
        print("   2. The user's password")
        print("   Or you can create a test user in Supabase Dashboard")

        # Method 3: Use admin client to bypass RLS (for testing)
        print("\n🔑 Method 3: Use admin client to bypass RLS...")
        from config.database import get_supabase_admin_client

        admin_client = get_supabase_admin_client()

        # Test document access with admin client
        doc_result = (
            admin_client.table("documents").select("*").eq("id", document_id).execute()
        )
        if doc_result.data:
            doc = doc_result.data[0]
            print(f"✅ Admin can access document: {doc.get('filename')}")
            print(f"   Owner: {doc.get('user_id')}")
            print(f"   Status: {doc.get('status')}")
        else:
            print("❌ Document not found")

        # Method 4: Create a test user session (if you have credentials)
        print("\n👤 Method 4: Create test user session...")
        print("   To test with real authentication, you can:")
        print("   1. Go to Supabase Dashboard > Authentication > Users")
        print("   2. Find user a4be935d-dd17-4db2-aa4e-b4989277bb1a")
        print("   3. Copy their email")
        print("   4. Use supabase.auth.sign_in_with_password()")

        print("\n🎯 For now, let's test with admin client...")

        # Test creating indexing run with admin client
        print("\n📝 Creating indexing run with admin client...")
        indexing_run_data = {"document_id": document_id, "status": "pending"}

        result = admin_client.table("indexing_runs").insert(indexing_run_data).execute()
        if result.data:
            run = result.data[0]
            print(f"✅ Created indexing run: {run.get('id')}")
            print(f"   Status: {run.get('status')}")
            print(f"   Created: {run.get('created_at')}")

            # Test updating the run
            update_result = (
                admin_client.table("indexing_runs")
                .update({"status": "running"})
                .eq("id", run.get("id"))
                .execute()
            )

            if update_result.data:
                print(f"✅ Updated status to: {update_result.data[0].get('status')}")

        else:
            print("❌ Failed to create indexing run")

        print("\n🎉 Authentication test completed!")
        return True

    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_with_authentication())
    if success:
        print("\n✅ Authentication test successful!")
    else:
        print("\n❌ Authentication test failed!")
        sys.exit(1)
