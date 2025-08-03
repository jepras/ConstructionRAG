#!/usr/bin/env python3
"""
Check detailed step results for the most recent document
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.config.database import get_supabase_admin_client


async def check_step_details():
    """Check detailed step results for the most recent document"""

    print("🔍 Checking Detailed Step Results")
    print("=" * 50)

    try:
        # Get database client
        db = get_supabase_admin_client()

        # Get the most recent document
        result = (
            db.table("documents")
            .select("*")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            print("❌ No documents found")
            return

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

                # Show sample outputs for debugging
                if step_result.get("sample_outputs"):
                    print(
                        f"      📄 Sample Outputs: {list(step_result['sample_outputs'].keys())}"
                    )
        else:
            print(f"\n❌ No step results found")

        # Check metadata
        if doc.get("metadata"):
            print(f"\n📋 Metadata: {list(doc['metadata'].keys())}")

        # Check if there are any error messages
        if doc.get("error_message"):
            print(f"\n❌ Document Error: {doc['error_message']}")

    except Exception as e:
        print(f"❌ Error checking step details: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_step_details())
