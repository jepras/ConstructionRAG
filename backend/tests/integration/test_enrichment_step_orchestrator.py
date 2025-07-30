#!/usr/bin/env python3
"""
Integration test for enrichment step through orchestrator
"""

import asyncio
import os
import sys
import requests
import json
from uuid import UUID
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from config.database import get_supabase_admin_client
from pipeline.indexing.orchestrator import get_indexing_orchestrator
from pipeline.shared.models import DocumentInput
from services.pipeline_service import PipelineService


def debug_url_accessibility(url: str, description: str = ""):
    """Debug function to test URL accessibility"""
    print(f"\n🔍 Testing URL accessibility: {description}")
    print(f"   URL: {url}")

    try:
        # Test HEAD request first
        head_response = requests.head(url, timeout=10)
        print(f"   HEAD Status: {head_response.status_code}")
        print(
            f"   Content-Type: {head_response.headers.get('content-type', 'unknown')}"
        )
        print(
            f"   Content-Length: {head_response.headers.get('content-length', 'unknown')}"
        )

        # Test GET request for small content
        get_response = requests.get(url, timeout=10, stream=True)
        print(f"   GET Status: {get_response.status_code}")

        if get_response.status_code == 200:
            # Read first 100 bytes to verify it's an image
            content = next(get_response.iter_content(100))
            if content.startswith(b"\x89PNG\r\n\x1a\n"):  # PNG signature
                print(f"   ✅ Valid PNG image detected")
            elif content.startswith(b"\xff\xd8\xff"):  # JPEG signature
                print(f"   ✅ Valid JPEG image detected")
            else:
                print(f"   ⚠️  Unknown image format: {content[:10].hex()}")
        else:
            print(f"   ❌ GET request failed")

    except Exception as e:
        print(f"   ❌ Error testing URL: {e}")


async def test_enrichment_step_orchestrator():
    """Test enrichment step through orchestrator"""
    try:
        # Configuration - using fresh run ID with working signed URLs
        existing_run_id = "cddd7b49-ed55-438b-9b23-3e9c3a229453"
        document_id = "550e8400-e29b-41d4-a716-446655440000"
        user_id = "123e4567-e89b-12d3-a456-426614174000"

        print(f"✅ Using fresh enrichment test run: {existing_run_id}")

        # Get orchestrator with admin client
        db = get_supabase_admin_client()

        # Create PipelineService with admin client
        pipeline_service = PipelineService(use_admin_client=True)

        from pipeline.indexing.orchestrator import IndexingOrchestrator

        orchestrator = IndexingOrchestrator(
            db=db,
            pipeline_service=pipeline_service,
        )

        print("✅ Orchestrator initialized")

        # Initialize steps
        await orchestrator.initialize_steps(user_id=UUID(user_id))
        print("✅ Steps initialized")

        # Load existing run data to get metadata step results
        print(f"📥 Loading data from run: {existing_run_id}")
        existing_run = await pipeline_service.get_indexing_run(UUID(existing_run_id))
        if not existing_run:
            print(f"❌ Run {existing_run_id} not found")
            return False

        if "metadata" not in existing_run.step_results:
            print(f"❌ Run {existing_run_id} does not have metadata step results")
            return False

        metadata_result = existing_run.step_results["metadata"]
        if metadata_result.status != "completed":
            print(f"❌ Metadata step not completed for run {existing_run_id}")
            return False

        print(f"✅ Found metadata step results for run {existing_run_id}")

        # DEBUG: Analyze metadata structure and image URLs
        print(f"\n🔍 DEBUGGING: Analyzing metadata structure...")
        metadata_data = metadata_result.data

        # Check table elements
        table_elements = metadata_data.get("table_elements", [])
        print(f"   Table elements found: {len(table_elements)}")

        for i, table in enumerate(table_elements[:3]):  # Check first 3 tables
            print(f"\n   Table {i+1}:")
            print(f"     ID: {table.get('id', 'unknown')}")
            print(
                f"     Page: {table.get('structural_metadata', {}).get('page_number', 'unknown')}"
            )

            # Check for image URL
            image_url = table.get("metadata", {}).get("image_url")
            if image_url:
                print(f"     Image URL: {image_url}")
                debug_url_accessibility(image_url, f"Table {i+1} image")
            else:
                print(f"     ❌ No image URL found")

            # Check for HTML content
            html_content = table.get("metadata", {}).get("text_as_html", "")
            if html_content:
                print(f"     HTML content: {len(html_content)} chars")
            else:
                print(f"     ❌ No HTML content found")

        # Check extracted pages
        extracted_pages = metadata_data.get("extracted_pages", {})
        print(f"\n   Extracted pages found: {len(extracted_pages)}")

        for page_num, page_info in list(extracted_pages.items())[
            :3
        ]:  # Check first 3 pages
            print(f"\n   Page {page_num}:")
            print(
                f"     Page number: {page_info.get('structural_metadata', {}).get('page_number', 'unknown')}"
            )

            # Check for image URL
            image_url = page_info.get("url")
            if image_url:
                print(f"     Image URL: {image_url}")
                debug_url_accessibility(image_url, f"Page {page_num} image")
            else:
                print(f"     ❌ No image URL found")

        # Test the known working URL
        print(f"\n🔍 DEBUGGING: Testing known working URL...")
        working_url = "https://lvvykzddbyrxcxgiahuo.supabase.co/storage/v1/object/sign/pipeline-assets/20d0d6ed-008b-44c2-b085-54b5332f3a89/processing/550e8400-e29b-41d4-a716-446655440000/extracted-pages/test-with-little-variety_page01_complex_c2aec69b.png?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV80NjAyNDhhZS0xM2UxLTQwNjUtOTY0Mi1jNjAzYWI2N2I1ZGMiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJwaXBlbGluZS1hc3NldHMvMjBkMGQ2ZWQtMDA4Yi00NGMyLWIwODUtNTRiNTMzMmYzYTg5L3Byb2Nlc3NpbmcvNTUwZTg0MDAtZTI5Yi00MWQ0LWE3MTYtNDQ2NjU1NDQwMDAwL2V4dHJhY3RlZC1wYWdlcy90ZXN0LXdpdGgtbGl0dGxlLXZhcmlldHlfcGFnZTAxX2NvbXBsZXhfYzJhZWM2OWIucG5nIiwiaWF0IjoxNzUzODc1MTY2LCJleHAiOjE3NTQ0Nzk5NjZ9.OLpUxR-apNLb-N5zDKpqUBBugl24cjTDyaHWspu3hRg"
        debug_url_accessibility(working_url, "Known working URL")

        # Run only the enrichment step
        print("\n🚀 Running enrichment step...")
        try:
            # Execute enrichment step with metadata output data
            enrichment_result = await orchestrator.enrichment_step.execute(
                metadata_result
            )

            # Store the result
            await pipeline_service.store_step_result(
                indexing_run_id=UUID(existing_run_id),
                step_name="enrichment",
                step_result=enrichment_result,
            )

            print("✅ Enrichment step completed successfully")
            print(f"   Status: {enrichment_result.status}")
            print(f"   Duration: {enrichment_result.duration_seconds:.2f} seconds")

            # Display results
            if enrichment_result.summary_stats:
                print(f"\n📊 Summary Statistics:")
                stats = enrichment_result.summary_stats
                print(f"   Tables processed: {stats.get('tables_processed', 0)}")
                print(f"   Images processed: {stats.get('images_processed', 0)}")
                print(f"   Total caption words: {stats.get('total_caption_words', 0)}")
                print(f"   VLM model: {stats.get('vlm_model', 'unknown')}")
                print(
                    f"   Caption language: {stats.get('caption_language', 'unknown')}"
                )

            if enrichment_result.sample_outputs:
                print(f"\n📋 Sample Outputs:")
                sample_tables = enrichment_result.sample_outputs.get(
                    "sample_tables", []
                )
                sample_images = enrichment_result.sample_outputs.get(
                    "sample_images", []
                )

                if sample_tables:
                    print(f"   Sample tables: {len(sample_tables)}")
                    for table in sample_tables:
                        print(
                            f"     - Table {table['id']}: {table['caption_words']} words"
                        )

                if sample_images:
                    print(f"   Sample images: {len(sample_images)}")
                    for image in sample_images:
                        print(
                            f"     - Page {image['page']}: {image['caption_words']} words"
                        )

            # DEBUG: Analyze enrichment results
            if enrichment_result.data:
                print(f"\n🔍 DEBUGGING: Analyzing enrichment results...")
                data = enrichment_result.data

                # Check table enrichment
                tables_with_enrichment = []
                for table in data.get("table_elements", []):
                    if "enrichment_metadata" in table:
                        enrichment = table["enrichment_metadata"]
                        tables_with_enrichment.append(
                            {
                                "id": table.get("id"),
                                "html_caption": bool(
                                    enrichment.get("table_html_caption")
                                ),
                                "image_caption": bool(
                                    enrichment.get("table_image_caption")
                                ),
                                "error": enrichment.get("vlm_processing_error"),
                                "processed": enrichment.get("vlm_processed", False),
                            }
                        )

                print(f"   Tables with enrichment: {len(tables_with_enrichment)}")
                for table in tables_with_enrichment[:3]:
                    print(
                        f"     - Table {table['id']}: HTML={table['html_caption']}, Image={table['image_caption']}, Processed={table['processed']}"
                    )
                    if table["error"]:
                        print(f"       Error: {table['error']}")

                # Check image enrichment
                images_with_enrichment = []
                for page_info in data.get("extracted_pages", {}).values():
                    if "enrichment_metadata" in page_info:
                        enrichment = page_info["enrichment_metadata"]
                        images_with_enrichment.append(
                            {
                                "page": page_info.get("structural_metadata", {}).get(
                                    "page_number"
                                ),
                                "has_caption": bool(
                                    enrichment.get("full_page_image_caption")
                                ),
                                "error": enrichment.get("vlm_processing_error"),
                                "processed": enrichment.get("vlm_processed", False),
                            }
                        )

                print(f"   Images with enrichment: {len(images_with_enrichment)}")
                for image in images_with_enrichment[:3]:
                    print(
                        f"     - Page {image['page']}: Caption={image['has_caption']}, Processed={image['processed']}"
                    )
                    if image["error"]:
                        print(f"       Error: {image['error']}")

            return True

        except Exception as e:
            print(f"❌ Enrichment step failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_enrichment_step_orchestrator())
    if success:
        print("\n✅ Enrichment step orchestrator test successful!")
    else:
        print("\n❌ Enrichment step orchestrator test failed!")
        sys.exit(1)
