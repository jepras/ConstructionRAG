#!/usr/bin/env python3
"""
Check specific document processing results
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


async def check_specific_document():
    """Check the specific document that failed"""

    print("🔍 Checking Specific Document Processing")
    print("=" * 50)

    try:
        # Get database client
        db = get_supabase_admin_client()

        # Check the document that only completed PartitionStep
        document_id = "dd7e2032-f894-47b7-9937-8d13172cd6ce"  # small-test-doc-test-project copy.pdf

        result = db.table("documents").select("*").eq("id", document_id).execute()

        if result.data:
            doc = result.data[0]
            print(f"\n📄 Document: {doc['filename']}")
            print(f"   ID: {doc['id']}")
            print(f"   Status: {doc['status']}")
            print(f"   Created: {doc['created_at']}")

            # Check step results
            if doc.get("step_results"):
                print(f"\n📋 Step Results:")
                for step_name, step_result in doc["step_results"].items():
                    print(f"\n   🔧 {step_name}:")
                    print(f"      Status: {step_result.get('status', 'unknown')}")
                    print(
                        f"      Duration: {step_result.get('duration_seconds', 'unknown')}s"
                    )

                    if step_result.get("error_message"):
                        print(f"      ❌ Error: {step_result['error_message']}")

                    if step_result.get("summary_stats"):
                        print(f"      📊 Summary: {step_result['summary_stats']}")
            else:
                print(f"\n❌ No step results found")

            # Check if there are any error messages
            if doc.get("error_message"):
                print(f"\n❌ Document Error: {doc['error_message']}")

    except Exception as e:
        print(f"❌ Error checking document: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_specific_document())
