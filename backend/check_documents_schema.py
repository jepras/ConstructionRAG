#!/usr/bin/env python3
"""
Check documents table schema to see if indexing_status field exists
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from src.config.database import get_supabase_admin_client

load_dotenv()


async def check_documents_schema():
    """Check if indexing_status field exists in documents table"""

    try:
        db = get_supabase_admin_client()

        # Get a sample document to see the current schema
        result = db.table("documents").select("*").limit(1).execute()

        if result.data:
            document = result.data[0]
            print("📋 Current documents table schema:")
            print("=" * 50)
            for key, value in document.items():
                print(f"  {key}: {type(value).__name__} = {value}")

            # Check specifically for indexing_status
            if "indexing_status" in document:
                print(
                    f"\n✅ indexing_status field exists: {document['indexing_status']}"
                )
            else:
                print(f"\n❌ indexing_status field does NOT exist")

            # Check for upload_type
            if "upload_type" in document:
                print(f"📝 upload_type field exists: {document['upload_type']}")
            else:
                print(f"❌ upload_type field does NOT exist")

        else:
            print("❌ No documents found in table")

    except Exception as e:
        print(f"❌ Error checking schema: {e}")


if __name__ == "__main__":
    asyncio.run(check_documents_schema())
