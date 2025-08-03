#!/usr/bin/env python3
"""
Check processing results in the database
"""

import asyncio
import os
import sys
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.config.database import get_supabase_admin_client


async def check_processing_results():
    """Check the database for processing results and errors"""

    print("🔍 Checking Processing Results in Database")
    print("=" * 50)

    try:
        # Get database client
        db = get_supabase_admin_client()

        # Check recent indexing runs
        print("\n📊 Recent Indexing Runs:")
        result = (
            db.table("indexing_runs")
            .select("*")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        if result.data:
            for run in result.data:
                print(f"\n   Index Run ID: {run['id']}")
                print(f"   Status: {run['status']}")
                print(f"   Upload Type: {run['upload_type']}")
                print(f"   Upload ID: {run['upload_id']}")
                print(f"   Created: {run['created_at']}")
                if run.get("error_message"):
                    print(f"   ❌ Error: {run['error_message']}")
                if run.get("step_results"):
                    print(f"   📋 Step Results: {len(run['step_results'])} steps")

        # Check recent documents
        print(f"\n📄 Recent Documents:")
        result = (
            db.table("documents")
            .select("*")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        if result.data:
            for doc in result.data:
                print(f"\n   Document ID: {doc['id']}")
                print(f"   Filename: {doc['filename']}")
                print(f"   Status: {doc['status']}")
                print(f"   Created: {doc['created_at']}")
                if doc.get("error_message"):
                    print(f"   ❌ Error: {doc['error_message']}")
                if doc.get("step_results"):
                    print(f"   📋 Step Results: {list(doc['step_results'].keys())}")
                if doc.get("metadata"):
                    print(f"   📋 Metadata: {list(doc['metadata'].keys())}")

        # Check email uploads
        print(f"\n📧 Recent Email Uploads:")
        result = (
            db.table("email_uploads")
            .select("*")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        if result.data:
            for upload in result.data:
                print(f"\n   Upload ID: {upload['id']}")
                print(f"   Email: {upload['email']}")
                print(f"   Filename: {upload['filename']}")
                print(f"   Status: {upload['status']}")
                print(f"   Created: {upload['created_at']}")
                if upload.get("error_message"):
                    print(f"   ❌ Error: {upload['error_message']}")

    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_processing_results())
