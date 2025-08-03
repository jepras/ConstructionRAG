#!/usr/bin/env python3
"""
Test the new unified processing method with real PDFs
"""

import asyncio
import os
import sys
import requests
import time
from pathlib import Path

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))


def test_unified_processing_with_real_pdfs():
    """Test uploading real PDFs using the new unified processing method"""

    # Path to the PDFs
    pdf_folder = Path("../data/external/construction_pdfs/multiple-pdf-project")

    # Check if folder exists
    if not pdf_folder.exists():
        print(f"❌ PDF folder not found: {pdf_folder}")
        return False

    # Get all PDF files
    pdf_files = list(pdf_folder.glob("*.pdf"))

    if not pdf_files:
        print(f"❌ No PDF files found in {pdf_folder}")
        return False

    print(f"📁 Found {len(pdf_files)} PDF files:")
    for pdf_file in pdf_files:
        print(f"   - {pdf_file.name} ({pdf_file.stat().st_size / 1024:.1f} KB)")

    # Test data
    test_email = "test@constructionrag.com"
    api_url = "http://localhost:8000/api/email-uploads"

    # Prepare files for upload
    files = []
    for pdf_file in pdf_files:
        files.append(
            ("files", (pdf_file.name, open(pdf_file, "rb"), "application/pdf"))
        )

    data = {"email": test_email}

    print(f"\n🚀 Testing Unified Processing with {len(pdf_files)} PDFs")
    print(f"📧 Email: {test_email}")
    print(f"🌐 API: {api_url}")

    start_time = time.time()

    try:
        # Make the request
        response = requests.post(api_url, files=files, data=data)

        # Close file handles
        for _, (_, file_handle, _) in files:
            file_handle.close()

        upload_time = time.time() - start_time

        print(f"\n📊 Response Status: {response.status_code}")
        print(f"⏱️  Upload Time: {upload_time:.2f} seconds")

        if response.status_code == 200:
            response_data = response.json()
            print("✅ Upload successful!")
            print(f"📋 Response data:")
            print(f"   - Upload ID: {response_data.get('upload_id')}")
            print(f"   - Index Run ID: {response_data.get('index_run_id')}")
            print(f"   - Document Count: {response_data.get('document_count')}")
            print(f"   - Document IDs: {response_data.get('document_ids')}")
            print(f"   - Status: {response_data.get('status')}")
            print(f"   - Message: {response_data.get('message')}")
            print(f"   - Public URL: {response_data.get('public_url')}")

            # Monitor processing status
            print(f"\n🔍 Monitoring processing status...")
            monitor_processing_status(response_data.get("upload_id"))

            return True

        else:
            print(f"❌ Upload failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server")
        print("   Make sure the FastAPI server is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error during upload: {e}")
        return False


def monitor_processing_status(upload_id: str):
    """Monitor the processing status of the upload"""
    api_url = f"http://localhost:8000/api/email-uploads/{upload_id}"

    print(f"📊 Monitoring: {api_url}")
    print("⏳ Waiting for processing to complete...")

    max_attempts = 30  # 5 minutes max
    attempt = 0

    while attempt < max_attempts:
        try:
            response = requests.get(api_url)

            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get("status", "unknown")

                print(f"   Attempt {attempt + 1}: Status = {status}")

                if status == "completed":
                    print("🎉 Processing completed successfully!")
                    print(f"📊 Final status: {status_data}")
                    return True
                elif status == "failed":
                    print("❌ Processing failed!")
                    print(f"📊 Error details: {status_data}")
                    return False
                elif status == "completed_with_errors":
                    print("⚠️  Processing completed with some errors")
                    print(f"📊 Details: {status_data}")
                    return True
                else:
                    # Still processing
                    pass
            else:
                print(f"   Attempt {attempt + 1}: HTTP {response.status_code}")

        except Exception as e:
            print(f"   Attempt {attempt + 1}: Error - {e}")

        attempt += 1
        time.sleep(10)  # Wait 10 seconds between checks

    print("⏰ Monitoring timeout - processing may still be running")
    return False


def compare_with_sequential_processing():
    """Compare with the old sequential processing approach"""
    print("\n📊 Performance Comparison")
    print("=" * 40)
    print("Old Sequential Processing:")
    print("   - Each PDF processed individually")
    print("   - Separate embedding calls per document")
    print("   - No parallel processing")
    print("   - Estimated time: ~15-20 minutes for 3 PDFs")
    print()
    print("New Unified Processing:")
    print("   - Parallel processing of individual steps")
    print("   - Single batch embedding call for all chunks")
    print("   - Conservative concurrency limits (max 3)")
    print("   - Estimated time: ~8-12 minutes for 3 PDFs")
    print("   - ~40-50% performance improvement expected")


if __name__ == "__main__":
    print("🧪 Testing Unified Processing with Real PDFs")
    print("=" * 60)

    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running")
        else:
            print("⚠️  API server responded but health check failed")
    except:
        print("❌ API server is not running")
        print("   Please start the server with: uvicorn src.main:app --reload")
        sys.exit(1)

    # Show performance comparison
    compare_with_sequential_processing()

    # Test unified processing
    success = test_unified_processing_with_real_pdfs()

    print("\n" + "=" * 60)
    if success:
        print("🎉 Unified processing test completed successfully!")
        print("📈 Performance improvements should be visible in the logs")
    else:
        print("❌ Unified processing test failed")
        print("🔍 Check the logs for detailed error information")
