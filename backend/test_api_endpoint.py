#!/usr/bin/env python3
"""
Test the API endpoint with new text-based PDFs
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


async def test_api_endpoint():
    """Test the API endpoint with new text-based PDFs"""

    print("🧪 Testing Multiple PDF Upload Only")
    print("=" * 60)

    # Find the new text-based PDFs
    pdf_folder = Path("../data/external/construction_pdfs/multiple-pdf-project")
    pdf_files = []

    # Look for the new PDFs in multiple-pdf-project folder - use copies of working PDF
    new_pdfs = ["copy-test-with-little-variety.pdf", "test-with-little-variety.pdf"]

    for pdf_name in new_pdfs:
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
    for pdf in pdf_files:
        print(f"   - {pdf.name}")

    # Test multiple PDF upload only
    if len(pdf_files) > 1:
        print(f"\n🚀 Testing Multiple PDF Upload...")
        await test_multiple_pdf_upload(pdf_files)
    else:
        print("❌ Need at least 2 PDFs for multiple upload test")


async def test_single_pdf_upload(pdf_path: Path):
    """Test uploading a single PDF"""
    try:
        print(f"   📤 Uploading: {pdf_path.name}")

        # Prepare the upload
        files = {"files": (pdf_path.name, open(pdf_path, "rb"), "application/pdf")}
        data = {"email": "test@example.com"}

        # Make the request
        response = requests.post(
            "http://localhost:8000/api/email-uploads", files=files, data=data
        )

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Upload successful!")
            print(f"      Upload ID: {result['upload_id']}")
            print(f"      Index Run ID: {result['index_run_id']}")
            print(f"      Document Count: {result['document_count']}")
            print(f"      Status: {result['status']}")

            # Monitor the processing
            await monitor_processing(result["upload_id"])
        else:
            print(f"   ❌ Upload failed: {response.status_code}")
            print(f"      Response: {response.text}")

    except Exception as e:
        print(f"   ❌ Error during upload: {e}")


async def test_multiple_pdf_upload(pdf_files: list):
    """Test uploading multiple PDFs"""
    try:
        print(f"   📤 Uploading {len(pdf_files)} PDFs...")

        # Prepare the upload
        files = []
        for pdf_path in pdf_files:
            files.append(
                ("files", (pdf_path.name, open(pdf_path, "rb"), "application/pdf"))
            )

        data = {"email": "test@example.com"}

        # Make the request
        response = requests.post(
            "http://localhost:8000/api/email-uploads", files=files, data=data
        )

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Upload successful!")
            print(f"      Upload ID: {result['upload_id']}")
            print(f"      Index Run ID: {result['index_run_id']}")
            print(f"      Document Count: {result['document_count']}")
            print(f"      Document IDs: {result['document_ids']}")
            print(f"      Status: {result['status']}")

            # Monitor the processing
            await monitor_processing(result["upload_id"])
        else:
            print(f"   ❌ Upload failed: {response.status_code}")
            print(f"      Response: {response.text}")

    except Exception as e:
        print(f"   ❌ Error during upload: {e}")


async def monitor_processing(upload_id: str):
    """Monitor the processing status"""
    print(f"   🔍 Monitoring processing for upload: {upload_id}")

    max_attempts = 30  # 5 minutes max
    attempt = 0

    while attempt < max_attempts:
        try:
            response = requests.get(
                f"http://localhost:8000/api/email-uploads/{upload_id}"
            )

            if response.status_code == 200:
                result = response.json()
                status = result.get("status", "unknown")

                print(f"      Status: {status}")

                if status == "completed":
                    print(f"   ✅ Processing completed successfully!")
                    if "individual_uploads" in result:
                        print(f"      Individual results:")
                        for upload in result["individual_uploads"]:
                            print(f"        - {upload['filename']}: {upload['status']}")
                    return
                elif status == "failed":
                    print(f"   ❌ Processing failed!")
                    return
                elif status == "processing":
                    print(
                        f"      Still processing... (attempt {attempt + 1}/{max_attempts})"
                    )
                else:
                    print(f"      Status: {status}")
            else:
                print(f"      ❌ Failed to get status: {response.status_code}")

        except Exception as e:
            print(f"      ❌ Error checking status: {e}")

        attempt += 1
        await asyncio.sleep(10)  # Wait 10 seconds between checks

    print(f"   ⏰ Monitoring timeout after {max_attempts} attempts")


if __name__ == "__main__":
    asyncio.run(test_api_endpoint())
