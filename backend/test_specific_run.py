#!/usr/bin/env python3
"""Test the specific indexing run ID mentioned by the user"""

import asyncio
import json
from uuid import UUID
from src.config.database import get_supabase_admin_client


async def test_specific_run():
    """Test the specific indexing run ID"""
    print("🔍 Testing specific indexing run...")

    db = get_supabase_admin_client()

    # The specific indexing run ID from the user
    index_run_id = "f28d9649-6ac7-4f9e-90b6-79ab6265b5d0"
    print(f"Testing with index run ID: {index_run_id}")

    try:
        # 1. Check if the indexing run exists
        print(f"\n📊 Checking if indexing run exists...")
        run_result = (
            db.table("indexing_runs").select("*").eq("id", index_run_id).execute()
        )
        print(f"Indexing run found: {len(run_result.data) > 0}")
        if run_result.data:
            run = run_result.data[0]
            print(f"  Status: {run.get('status')}")
            print(f"  Upload type: {run.get('upload_type')}")

        # 2. Check junction table
        print(f"\n🔗 Checking junction table...")
        junction_result = (
            db.table("indexing_run_documents")
            .select("document_id")
            .eq("indexing_run_id", index_run_id)
            .execute()
        )
        print(f"Junction records found: {len(junction_result.data)}")

        if junction_result.data:
            document_ids = [row["document_id"] for row in junction_result.data]
            print(f"Document IDs: {document_ids}")

            # 3. Get documents
            print(f"\n📄 Getting documents...")
            documents_result = (
                db.table("documents").select("*").in_("id", document_ids).execute()
            )
            print(f"Documents found: {len(documents_result.data)}")

            if documents_result.data:
                for i, doc in enumerate(documents_result.data):
                    print(f"\n📄 Document {i+1}:")
                    print(f"  ID: {doc.get('id')}")
                    print(f"  Filename: {doc.get('filename')}")
                    print(f"  Status: {doc.get('indexing_status')}")

                    step_results = doc.get("step_results", {})
                    print(f"  Step results: {list(step_results.keys())}")
                    print(f"  Step results count: {len(step_results)}")

                    # Check specific steps
                    for step_name, step_data in step_results.items():
                        if isinstance(step_data, dict):
                            print(f"    {step_name}:")
                            print(f"      Status: {step_data.get('status')}")
                            print(f"      Keys: {list(step_data.keys())}")

                            # Check summary_stats
                            if "summary_stats" in step_data:
                                summary = step_data["summary_stats"]
                                print(f"      Summary stats: {summary}")

                            # Check sample_outputs
                            if "sample_outputs" in step_data:
                                sample_outputs = step_data["sample_outputs"]
                                print(
                                    f"      Sample outputs keys: {list(sample_outputs.keys())}"
                                )
                        else:
                            print(f"    {step_name}: {type(step_data)}")
            else:
                print("❌ No documents retrieved")
        else:
            print("❌ No junction records found")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        print(f"❌ Full traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(test_specific_run())
