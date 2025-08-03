#!/usr/bin/env python3
"""Quick test to debug data retrieval"""

import asyncio
import json
from uuid import UUID
from src.config.database import get_supabase_admin_client


async def test_data_retrieval():
    """Test data retrieval from database"""
    print("🔍 Testing data retrieval...")

    db = get_supabase_admin_client()

    # 1. Check if any documents have step results
    print("\n📄 Checking for documents with step results...")
    documents_result = db.table("documents").select("*").execute()
    print(f"Total documents: {len(documents_result.data)}")

    docs_with_step_results = []
    for doc in documents_result.data:
        step_results = doc.get("step_results", {})
        if step_results and len(step_results) > 0:
            docs_with_step_results.append(doc)

    print(f"Documents with step results: {len(docs_with_step_results)}")

    if docs_with_step_results:
        doc = docs_with_step_results[0]
        print(f"\n✅ Found document with step results:")
        print(f"  ID: {doc.get('id')}")
        print(f"  Filename: {doc.get('filename')}")
        print(f"  Index run ID: {doc.get('index_run_id')}")
        print(f"  Step results: {list(doc.get('step_results', {}).keys())}")

        # Check if this document is in the junction table
        doc_id = doc.get("id")
        print(f"\n🔗 Checking if document {doc_id} is in junction table...")
        junction_result = (
            db.table("indexing_run_documents")
            .select("*")
            .eq("document_id", doc_id)
            .execute()
        )
        print(f"Found {len(junction_result.data)} junction records for this document")

        if junction_result.data:
            for record in junction_result.data:
                print(f"  - indexing_run_id: {record.get('indexing_run_id')}")

                # Test getting documents for this indexing run
                index_run_id = record.get("indexing_run_id")
                print(
                    f"\n📄 Testing junction table lookup for index run {index_run_id}..."
                )
                junction_docs = (
                    db.table("indexing_run_documents")
                    .select("document_id")
                    .eq("indexing_run_id", index_run_id)
                    .execute()
                )
                print(f"Found {len(junction_docs.data)} documents for this index run")

                if junction_docs.data:
                    doc_ids = [row["document_id"] for row in junction_docs.data]
                    print(f"Document IDs: {doc_ids}")

                    # Get the actual documents
                    docs_via_junction = (
                        db.table("documents").select("*").in_("id", doc_ids).execute()
                    )
                    print(
                        f"Retrieved {len(docs_via_junction.data)} documents via junction table"
                    )

                    for doc_via_junction in docs_via_junction.data:
                        step_results = doc_via_junction.get("step_results", {})
                        print(
                            f"  - {doc_via_junction.get('filename')}: {len(step_results)} step results"
                        )
                        if step_results:
                            print(f"    Steps: {list(step_results.keys())}")
        else:
            print("❌ Document not found in junction table")

            # Test the old approach (using index_run_id field)
            print(f"\n🔍 Testing old approach (index_run_id field)...")
            if doc.get("index_run_id"):
                old_approach = (
                    db.table("documents")
                    .select("*")
                    .eq("index_run_id", doc.get("index_run_id"))
                    .execute()
                )
                print(
                    f"Found {len(old_approach.data)} documents via index_run_id field"
                )
            else:
                print("Document has no index_run_id field")


if __name__ == "__main__":
    asyncio.run(test_data_retrieval())
