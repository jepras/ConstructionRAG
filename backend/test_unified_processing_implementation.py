#!/usr/bin/env python3
"""
Test the unified processing implementation
"""

import requests
import time
from pathlib import Path


def test_unified_processing_implementation():
    """Test the unified processing implementation"""

    # Path to the PDFs
    pdf_folder = Path("../data/external/construction_pdfs/multiple-pdf-project")

    # Get all PDF files
    pdf_files = list(pdf_folder.glob("*.pdf"))

    if not pdf_files:
        print("❌ No PDF files found")
        return False

    print(f"📁 Found {len(pdf_files)} PDF files")

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

    print(f"\n🚀 Testing Unified Processing Implementation")

    try:
        # Make the request
        response = requests.post(api_url, files=files, data=data)

        # Close file handles
        for _, (_, file_handle, _) in files:
            file_handle.close()

        if response.status_code == 200:
            response_data = response.json()
            upload_id = response_data.get("upload_id")
            print(f"✅ Upload successful! Upload ID: {upload_id}")

            # Monitor for a few minutes
            print("🔍 Monitoring processing...")
            for i in range(18):  # 3 minutes
                time.sleep(10)
                status_response = requests.get(
                    f"http://localhost:8000/api/email-uploads/{upload_id}"
                )
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(
                        f"   {i+1}/18: Overall={status_data.get('status')}, Index Run={status_data.get('index_run_status')}"
                    )

                    if status_data.get("status") in [
                        "completed",
                        "failed",
                        "completed_with_errors",
                    ]:
                        print(f"🎯 Final status: {status_data}")

                        # Check individual document statuses
                        individual_uploads = status_data.get("individual_uploads", [])
                        print(f"📊 Individual Document Statuses:")
                        for upload in individual_uploads:
                            print(f"   - {upload['filename']}: {upload['status']}")

                        return True
                else:
                    print(f"   {i+1}/18: HTTP {status_response.status_code}")

            print("⏰ Monitoring timeout")
            return True

        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing Unified Processing Implementation")
    print("=" * 60)

    success = test_unified_processing_implementation()

    print("\n" + "=" * 60)
    if success:
        print("✅ Test completed!")
    else:
        print("❌ Test failed!")
