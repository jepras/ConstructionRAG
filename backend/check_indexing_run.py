#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.database import get_supabase_admin_client


def check_indexing_run():
    """Check the specific indexing run and related data"""

    print("🔍 Checking indexing run status...")

    try:
        db = get_supabase_admin_client()

        # Check the new indexing run
        run_id = "ecc0b844-015b-4bf7-9376-81877be98449"

        print(f"📊 Checking indexing run: {run_id}")
        run_result = db.table("indexing_runs").select("*").eq("id", run_id).execute()

        if run_result.data:
            run = run_result.data[0]
            print(f"✅ Indexing run found:")
            print(f"   Status: {run.get('status')}")
            print(f"   Project ID: {run.get('project_id')}")
            print(f"   Created at: {run.get('created_at')}")
            print(f"   Updated at: {run.get('updated_at')}")
        else:
            print(f"❌ Indexing run not found!")

        # Check documents for this run
        print(f"\n📄 Checking documents for run: {run_id}")
        docs_result = (
            db.table("documents").select("*").eq("index_run_id", run_id).execute()
        )

        if docs_result.data:
            print(f"✅ Found {len(docs_result.data)} documents:")
            for doc in docs_result.data:
                print(f"   - {doc.get('filename')} (ID: {doc.get('id')})")
                print(f"     Status: {doc.get('indexing_status')}")
                print(f"     Upload type: {doc.get('upload_type')}")
        else:
            print(f"❌ No documents found for this run!")

        # Check indexing_run_documents junction table
        print(f"\n🔗 Checking indexing_run_documents junction table:")
        junction_result = (
            db.table("indexing_run_documents")
            .select("*")
            .eq("indexing_run_id", run_id)
            .execute()
        )

        if junction_result.data:
            print(f"✅ Found {len(junction_result.data)} junction records:")
            for junction in junction_result.data:
                print(f"   - Document ID: {junction.get('document_id')}")
                print(f"     Status: {junction.get('status')}")
        else:
            print(f"❌ No junction records found!")

        # Check if documents exist but aren't linked
        print(f"\n🔍 Checking for orphaned documents:")
        all_docs = db.table("documents").select("*").execute()
        orphaned = [
            doc
            for doc in all_docs.data
            if doc.get("index_run_id") == run_id
            and doc.get("id")
            not in [j.get("document_id") for j in junction_result.data]
        ]

        if orphaned:
            print(f"⚠️  Found {len(orphaned)} documents that should be linked:")
            for doc in orphaned:
                print(f"   - {doc.get('filename')} (ID: {doc.get('id')})")
        else:
            print(f"✅ No orphaned documents found")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    check_indexing_run()
