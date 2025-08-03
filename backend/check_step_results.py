#!/usr/bin/env python3
"""
Check step results in the database for recent documents
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


async def check_step_results():
    """Check step results for recent documents"""

    try:
        db = get_supabase_admin_client()

        # Get recent documents with step results
        result = (
            db.table("documents")
            .select("*")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        if result.data:
            print("📋 Recent Documents Step Results:")
            print("=" * 60)

            for i, doc in enumerate(result.data, 1):
                print(f"\n📄 Document {i}: {doc['filename']}")
                print(f"   ID: {doc['id']}")
                print(f"   indexing_status: {doc.get('indexing_status', 'N/A')}")
                print(f"   upload_type: {doc.get('upload_type', 'N/A')}")

                step_results = doc.get("step_results", {})
                if step_results:
                    print(f"   Step Results:")
                    for step_name, step_data in step_results.items():
                        status = step_data.get("status", "unknown")
                        print(f"     - {step_name}: {status}")
                else:
                    print(f"   Step Results: None")

        else:
            print("❌ No documents found")

    except Exception as e:
        print(f"❌ Error checking step results: {e}")


if __name__ == "__main__":
    asyncio.run(check_step_results())
