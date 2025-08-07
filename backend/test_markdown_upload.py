#!/usr/bin/env python3
"""
Test script to verify markdown file uploads to Supabase Storage.
This tests the same functionality used in the wiki generation pipeline.
"""

import asyncio
import tempfile
import os
from uuid import uuid4
from pathlib import Path

# Add src to path
import sys

sys.path.append("src")

from src.services.storage_service import StorageService, UploadType
from src.config.database import get_supabase_admin_client


async def test_markdown_upload():
    """Test markdown file upload functionality."""
    print("🧪 Testing markdown file upload to Supabase Storage...")

    # Initialize storage service and orchestrator
    storage_service = StorageService()
    from src.pipeline.wiki_generation.orchestrator import WikiGenerationOrchestrator

    orchestrator = WikiGenerationOrchestrator()

    # Test data
    test_content = """# Test Markdown File

This is a test markdown file to verify upload functionality.

## Features
- Danish characters: æ, ø, å
- Special characters: é, è, ê, ë
- Normal text: Hello World

## Code Example
```python
def hello_world():
    print("Hello, World!")
```

## Conclusion
This should work with our updated bucket configuration.
"""

    # Test titles with Danish characters (these will be sanitized)
    test_titles = [
        "Normal Title",
        "Nøgleinteressenter og Roller",  # Danish characters
        "Projekt øversigt med ændringer",  # More Danish characters
        "Étude sur l'évaluation",  # French characters
        "Test File With Special Chars !@#$%^&*()",  # Special characters
    ]

    # Create a test wiki run ID
    test_wiki_run_id = str(uuid4())
    test_index_run_id = "668ecac8-beb5-4f94-94d6-eee8c771044d"  # Use existing index run

    print(f"📁 Test wiki run ID: {test_wiki_run_id}")
    print(f"📁 Test index run ID: {test_index_run_id}")

    results = []

    for title in test_titles:
        # Sanitize the filename
        sanitized_filename = orchestrator._sanitize_filename(title) + ".md"
        print(f"\n🔍 Testing title: '{title}'")
        print(f"   Sanitized filename: '{sanitized_filename}'")

        try:
            # Test the upload
            upload_result = await storage_service.upload_wiki_page(
                file_path=None,  # We'll pass content directly
                filename=sanitized_filename,
                wiki_run_id=test_wiki_run_id,
                upload_type=UploadType.EMAIL,
                index_run_id=test_index_run_id,
                content=test_content,
            )

            print(f"✅ Success! Uploaded: {sanitized_filename}")
            print(f"   Storage path: {upload_result['storage_path']}")
            print(
                f"   URL: {upload_result['url'][:100] if len(upload_result['url']) > 100 else upload_result['url']}..."
            )

            results.append(
                {
                    "title": title,
                    "filename": sanitized_filename,
                    "status": "success",
                    "storage_path": upload_result["storage_path"],
                    "url": upload_result["url"],
                }
            )

        except Exception as e:
            print(f"❌ Failed to upload {sanitized_filename}: {e}")
            results.append(
                {
                    "title": title,
                    "filename": sanitized_filename,
                    "status": "failed",
                    "error": str(e),
                }
            )

    # Print summary
    print(f"\n📊 Test Summary:")
    print(f"Total files tested: {len(test_titles)}")
    successful = len([r for r in results if r["status"] == "success"])
    failed = len([r for r in results if r["status"] == "failed"])
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")

    if failed > 0:
        print(f"\n❌ Failed uploads:")
        for result in results:
            if result["status"] == "failed":
                print(f"  - {result['filename']}: {result['error']}")

    return results


async def test_filename_sanitization():
    """Test the filename sanitization function."""
    print("\n🧪 Testing filename sanitization...")

    # Import the orchestrator to test the sanitization function
    from src.pipeline.wiki_generation.orchestrator import WikiGenerationOrchestrator

    orchestrator = WikiGenerationOrchestrator()

    test_titles = [
        "Normal Title",
        "Nøgleinteressenter og Roller",  # Danish characters
        "Projekt øversigt med ændringer",  # More Danish characters
        "Étude sur l'évaluation",  # French characters
        "Test File With Special Chars !@#$%^&*()",  # Special characters
        "File with spaces and-dashes",
        "File with multiple   spaces",
        "File with trailing spaces ",
        " File with leading spaces",
    ]

    print("Original Title -> Sanitized Filename:")
    for title in test_titles:
        sanitized = orchestrator._sanitize_filename(title)
        print(f"  '{title}' -> '{sanitized}.md'")


async def main():
    """Main test function."""
    print("🚀 Starting markdown upload tests...")

    # Test filename sanitization first
    await test_filename_sanitization()

    # Test actual uploads
    results = await test_markdown_upload()

    print(f"\n🎉 Test completed!")

    # Return results for potential further analysis
    return results


if __name__ == "__main__":
    # Run the test
    asyncio.run(main())
