#!/usr/bin/env python3
"""
Test the multi-document project upload endpoint
"""

import asyncio
import os
import sys
import requests
import time
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()


async def test_project_multi_upload():
    """Test the multi-document project upload endpoint"""

    print("🧪 Testing Multi-Document Project Upload")
    print("=" * 60)

    # Find the test PDFs
    pdf_folder = Path("../data/external/construction_pdfs/multiple-pdf-project")
    pdf_files = []

    # Look for the test PDFs
    test_pdfs = ["copy-test-with-little-variety.pdf", "test-with-little-variety.pdf"]

    for pdf_name in test_pdfs:
        pdf_path = pdf_folder / pdf_name
        if pdf_path.exists():
            pdf_files.append(pdf_path)
            print(f"✅ Found: {pdf_name}")
        else:
            print(f"❌ Not found: {pdf_name}")

    if not pdf_files:
        print("❌ No PDF files found for testing")
        return

    print(f"\n📄 Testing with {len(pdf_files)} PDF files:")
    for pdf_file in pdf_files:
        print(f"   - {pdf_file.name}")

    # For testing, we'll need to create a project first or use an existing one
    # For now, let's assume we have a test project ID
    # In a real scenario, you'd create a project first

    # You would need to:
    # 1. Create a project first via the projects API
    # 2. Get the project ID
    # 3. Use that project ID for the upload test

    # For this test, we'll use a placeholder project ID
    # In practice, you'd get this from creating a project
    test_project_id = "test-project-id"  # This would be a real UUID

    print(f"\n🚀 Testing Multi-Document Project Upload...")
    print(f"   📤 Uploading to project: {test_project_id}")

    # Prepare the upload
    files = []
    for pdf_path in pdf_files:
        files.append(
            ("files", (pdf_path.name, open(pdf_path, "rb"), "application/pdf"))
        )

    # Make the request
    response = requests.post(
        f"http://localhost:8000/api/projects/{test_project_id}/documents/multi",
        files=files,
        # Note: In a real test, you'd need authentication
        # headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Upload successful!")
        print(f"      Project ID: {result['project_id']}")
        print(f"      Index Run ID: {result['index_run_id']}")
        print(f"      Document Count: {result['document_count']}")
        print(f"      Document IDs: {result['document_ids']}")
        print(f"      Status: {result['status']}")
        print(f"      Message: {result['message']}")

        # Monitor the processing
        index_run_id = result["index_run_id"]
        print(f"   🔍 Monitoring processing for index run: {index_run_id}")

        for attempt in range(30):  # Wait up to 5 minutes
            time.sleep(10)

            # In a real implementation, you'd have an endpoint to check index run status
            # For now, we'll just show the attempt
            print(f"      Still processing... (attempt {attempt + 1}/30)")

            # You could add a status check endpoint here:
            # status_response = requests.get(f"http://localhost:8000/api/projects/{test_project_id}/index-runs/{index_run_id}")
            # if status_response.status_code == 200:
            #     status_data = status_response.json()
            #     status = status_data.get('status', 'unknown')
            #     print(f"      Status: {status}")
            #
            #     if status == "completed":
            #         print("   ✅ Processing completed successfully!")
            #         break
            #     elif status == "failed":
            #         print("   ❌ Processing failed!")
            #         break
        else:
            print("   ⏰ Monitoring timeout after 30 attempts")
    else:
        print(f"   ❌ Upload failed: {response.status_code}")
        print(f"      Response: {response.text}")


if __name__ == "__main__":
    asyncio.run(test_project_multi_upload())
