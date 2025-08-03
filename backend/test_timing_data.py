#!/usr/bin/env python3
"""Test script to check timing data in the database"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from src.config.database import get_supabase_client
from src.models.document import Document
from src.models.pipeline import IndexingRun


async def check_timing_data():
    """Check what timing data exists in the database"""
    print("🔍 Checking timing data in the database...")

    # Initialize Supabase client
    supabase = get_supabase_client()

    # Test database connection
    print("\n🔗 Testing database connection...")
    try:
        # Try to get table info
        tables_result = (
            supabase.table("documents").select("count", count="exact").execute()
        )
        print(f"✅ Database connection successful")
        print(f"📊 Documents table count: {tables_result.count}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return

    # Get all documents
    print("\n📄 Checking documents...")
    try:
        documents_result = supabase.table("documents").select("*").execute()

        if not documents_result.data:
            print("❌ No documents found in database")

            # Check if there are any tables with document-like data
            print("\n🔍 Checking for other tables...")
            try:
                # Try indexing_runs table
                runs_result = supabase.table("indexing_runs").select("*").execute()
                print(
                    f"📊 Indexing runs found: {len(runs_result.data) if runs_result.data else 0}"
                )

                # Try email_uploads table
                emails_result = supabase.table("email_uploads").select("*").execute()
                print(
                    f"📧 Email uploads found: {len(emails_result.data) if emails_result.data else 0}"
                )

                # Check email_uploads for your specific document
                if emails_result.data:
                    print(f"\n📧 Email uploads details:")
                    for i, email_data in enumerate(emails_result.data[:5]):
                        print(
                            f"  {i+1}. {email_data.get('filename', 'Unknown')} - Status: {email_data.get('status', 'Unknown')}"
                        )

                        # Check processing_results for timing data
                        processing_results = email_data.get("processing_results")
                        if processing_results:
                            print(f"     📊 Processing results found!")
                            if isinstance(processing_results, dict):
                                print(
                                    f"     🔍 Keys: {list(processing_results.keys())}"
                                )
                                # Look for timing-related keys
                                timing_keys = [
                                    k
                                    for k in processing_results.keys()
                                    if "time" in k.lower() or "duration" in k.lower()
                                ]
                                if timing_keys:
                                    print(f"     ⏱️  Timing keys found: {timing_keys}")
                                else:
                                    print(f"     ❌ No timing keys found")
                            else:
                                print(
                                    f"     📄 Processing results type: {type(processing_results)}"
                                )
                        else:
                            print(f"     ❌ No processing results")

                        if "test-with-little-variety.pdf" in email_data.get(
                            "filename", ""
                        ):
                            print(f"     ✅ Found your document!")
                            if processing_results:
                                print(
                                    f"     📊 Full processing results: {json.dumps(processing_results, indent=2)[:500]}..."
                                )

                # Try projects table
                projects_result = supabase.table("projects").select("*").execute()
                print(
                    f"📁 Projects found: {len(projects_result.data) if projects_result.data else 0}"
                )

            except Exception as e:
                print(f"❌ Error checking other tables: {e}")

            return

        print(f"✅ Found {len(documents_result.data)} documents")

        for i, doc_data in enumerate(
            documents_result.data[:5]
        ):  # Check first 5 documents
            print(f"\n--- Document {i+1}: {doc_data.get('filename', 'Unknown')} ---")

            # Create Document model to test computed properties
            try:
                doc = Document(**doc_data)

                print(f"  📊 Step results keys: {list(doc.step_results.keys())}")
                print(f"  ⏱️  Step timings: {doc.step_timings}")
                print(f"  🕐 Total processing time: {doc.total_processing_time:.2f}s")
                print(f"  🔄 Current step: {doc.current_step}")

                # Check raw step_results data
                if doc.step_results:
                    print(f"  🔍 Raw step_results structure:")
                    for step_name, step_data in doc.step_results.items():
                        if isinstance(step_data, dict):
                            print(f"    {step_name}: {list(step_data.keys())}")
                            if "duration_seconds" in step_data:
                                print(
                                    f"      ✅ duration_seconds: {step_data['duration_seconds']}"
                                )
                            else:
                                print(f"      ❌ No duration_seconds found")
                        else:
                            print(f"    {step_name}: {type(step_data)}")
                else:
                    print(f"  ❌ No step_results data")

            except Exception as e:
                print(f"  ❌ Error creating Document model: {e}")

    except Exception as e:
        print(f"❌ Error querying documents: {e}")

    # Get all indexing runs
    print("\n🏃 Checking indexing runs...")
    try:
        runs_result = supabase.table("indexing_runs").select("*").execute()

        if not runs_result.data:
            print("❌ No indexing runs found in database")
            return

        print(f"✅ Found {len(runs_result.data)} indexing runs")

        for i, run_data in enumerate(runs_result.data[:3]):  # Check first 3 runs
            print(
                f"\n--- Indexing Run {i+1}: {run_data.get('upload_type', 'Unknown')} ---"
            )

            try:
                run = IndexingRun(**run_data)

                print(f"  📊 Step results keys: {list(run.step_results.keys())}")
                print(f"  ⏱️  Step timings: {run.step_timings}")
                print(f"  🕐 Total processing time: {run.total_processing_time:.2f}s")

                # Check raw step_results data
                if run.step_results:
                    print(f"  🔍 Raw step_results structure:")
                    for step_name, step_data in run.step_results.items():
                        if hasattr(step_data, "duration_seconds"):
                            print(
                                f"    {step_name}: ✅ duration_seconds: {step_data.duration_seconds}"
                            )
                        elif (
                            isinstance(step_data, dict)
                            and "duration_seconds" in step_data
                        ):
                            print(
                                f"    {step_name}: ✅ duration_seconds: {step_data['duration_seconds']}"
                            )
                        else:
                            print(f"    {step_name}: ❌ No duration_seconds found")
                else:
                    print(f"  ❌ No step_results data")

            except Exception as e:
                print(f"  ❌ Error creating IndexingRun model: {e}")

    except Exception as e:
        print(f"❌ Error querying indexing runs: {e}")


if __name__ == "__main__":
    asyncio.run(check_timing_data())
