#!/usr/bin/env python3
"""Test script for enrichment step implementation."""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from src.pipeline.indexing.steps.enrichment import EnrichmentStep
from src.pipeline.indexing.steps.metadata import MetadataStep
from src.pipeline.indexing.steps.partition import PartitionStep
from src.models.document import DocumentInput
from src.services.pipeline_service import PipelineService

# Load environment variables
load_dotenv()


async def test_enrichment_step():
    """Test the enrichment step with real metadata step output."""

    print("🧪 TESTING ENRICHMENT STEP IMPLEMENTATION")
    print("=" * 50)

    # Check environment
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ OPENROUTER_API_KEY not found in environment")
        print("💡 Please add your OpenRouter API key to .env file")
        return False

    # Initialize pipeline service
    pipeline_service = PipelineService()

    # Get latest indexing run with metadata step completed
    print("📊 Looking for indexing run with metadata step completed...")

    try:
        # Get all indexing runs
        runs = await pipeline_service.get_all_indexing_runs()

        # Find a run with metadata step completed
        target_run = None
        for run in runs:
            if (
                run.status == "completed"
                and "metadata" in run.step_results
                and run.step_results["metadata"]["status"] == "completed"
            ):
                target_run = run
                break

        if not target_run:
            print("❌ No completed indexing run with metadata step found")
            print("💡 Please run a document through partition and metadata steps first")
            return False

        print(f"✅ Found target run: {target_run.id}")
        print(f"📄 Document: {target_run.document_id}")

        # Get metadata step output
        metadata_result = target_run.step_results["metadata"]
        metadata_output = metadata_result["data"]

        print(f"📊 Metadata output contains:")
        print(f"   Text elements: {len(metadata_output.get('text_elements', []))}")
        print(f"   Table elements: {len(metadata_output.get('table_elements', []))}")
        print(f"   Extracted pages: {len(metadata_output.get('extracted_pages', {}))}")

        # Check if we have elements to enrich
        tables_to_enrich = len(metadata_output.get("table_elements", []))
        images_to_enrich = len(metadata_output.get("extracted_pages", {}))

        if tables_to_enrich == 0 and images_to_enrich == 0:
            print("⚠️ No tables or images found to enrich")
            print("💡 This is normal if the document doesn't contain tables or images")
            return True

        print(
            f"🎯 Elements to enrich: {tables_to_enrich} tables, {images_to_enrich} images"
        )

        # Initialize enrichment step
        config = {
            "vlm_model": "anthropic/claude-3-5-sonnet",
            "caption_language": "Danish",
            "max_text_context_length": 1500,
            "max_page_text_elements": 5,
        }

        enrichment_step = EnrichmentStep(config)

        print(f"\n🤖 Initializing VLM captioner with {config['vlm_model']}")
        print(f"📝 Caption language: {config['caption_language']}")

        # Execute enrichment step
        print(f"\n🚀 Executing enrichment step...")
        start_time = datetime.utcnow()

        result = await enrichment_step.execute(metadata_output)

        duration = (datetime.utcnow() - start_time).total_seconds()

        print(f"\n✅ Enrichment step completed in {duration:.2f} seconds")
        print(f"📊 Status: {result.status}")

        if result.status == "completed":
            print(f"\n📈 SUMMARY STATISTICS:")
            for key, value in result.summary_stats.items():
                print(f"   {key}: {value}")

            print(f"\n📋 SAMPLE OUTPUTS:")
            if result.sample_outputs.get("sample_tables"):
                print(
                    f"   Sample tables: {len(result.sample_outputs['sample_tables'])}"
                )
                for table in result.sample_outputs["sample_tables"]:
                    print(f"     - Table {table['id']}: {table['caption_words']} words")

            if result.sample_outputs.get("sample_images"):
                print(
                    f"   Sample images: {len(result.sample_outputs['sample_images'])}"
                )
                for image in result.sample_outputs["sample_images"]:
                    print(
                        f"     - Page {image['page']}: {image['caption_words']} words"
                    )

            # Check enriched data structure
            enriched_data = result.data

            print(f"\n🔍 ENRICHED DATA STRUCTURE:")
            print(f"   Text elements: {len(enriched_data.get('text_elements', []))}")
            print(f"   Table elements: {len(enriched_data.get('table_elements', []))}")
            print(
                f"   Extracted pages: {len(enriched_data.get('extracted_pages', {}))}"
            )

            # Check enrichment metadata
            tables_with_enrichment = sum(
                1
                for t in enriched_data.get("table_elements", [])
                if "enrichment_metadata" in t
            )
            images_with_enrichment = sum(
                1
                for p in enriched_data.get("extracted_pages", {}).values()
                if "enrichment_metadata" in p
            )

            print(f"   Tables with enrichment: {tables_with_enrichment}")
            print(f"   Images with enrichment: {images_with_enrichment}")

            # Show sample enrichment metadata
            if tables_with_enrichment > 0:
                sample_table = next(
                    t
                    for t in enriched_data.get("table_elements", [])
                    if "enrichment_metadata" in t
                )
                enrichment_meta = sample_table["enrichment_metadata"]
                print(f"\n📊 SAMPLE TABLE ENRICHMENT:")
                print(f"   VLM model: {enrichment_meta.get('vlm_model')}")
                print(
                    f"   HTML caption: {bool(enrichment_meta.get('table_html_caption'))}"
                )
                print(
                    f"   Image caption: {bool(enrichment_meta.get('table_image_caption'))}"
                )
                print(f"   Total words: {enrichment_meta.get('caption_word_count')}")
                print(
                    f"   Processing time: {enrichment_meta.get('processing_duration_seconds', 0):.2f}s"
                )

            if images_with_enrichment > 0:
                sample_image = next(
                    p
                    for p in enriched_data.get("extracted_pages", {}).values()
                    if "enrichment_metadata" in p
                )
                enrichment_meta = sample_image["enrichment_metadata"]
                print(f"\n🖼️ SAMPLE IMAGE ENRICHMENT:")
                print(f"   VLM model: {enrichment_meta.get('vlm_model')}")
                print(
                    f"   Full-page caption: {bool(enrichment_meta.get('full_page_image_caption'))}"
                )
                print(f"   Total words: {enrichment_meta.get('caption_word_count')}")
                print(
                    f"   Processing time: {enrichment_meta.get('processing_duration_seconds', 0):.2f}s"
                )

            print(f"\n🎉 Enrichment step test PASSED!")
            return True

        else:
            print(f"❌ Enrichment step failed: {result.error_message}")
            if result.error_details:
                print(f"   Error details: {result.error_details}")
            return False

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_enrichment_step_standalone():
    """Test enrichment step with mock data (for development)."""

    print("🧪 TESTING ENRICHMENT STEP WITH MOCK DATA")
    print("=" * 50)

    # Create mock metadata output
    mock_metadata_output = {
        "text_elements": [
            {
                "id": "1",
                "page": 1,
                "text": "1.2 Demonstrationsejendommen",
                "category": "Header",
                "metadata": {"filename": "test.pdf", "page_number": 1},
                "structural_metadata": {
                    "source_filename": "test.pdf",
                    "page_number": 1,
                    "content_type": "text",
                    "element_category": "Header",
                    "element_id": "1",
                    "has_numbers": True,
                    "text_complexity": "complex",
                    "section_title_inherited": "1.2 Demonstrationsejendommen",
                },
            }
        ],
        "table_elements": [
            {
                "id": "table_1",
                "category": "Table",
                "page": 2,
                "text": "Sample table content",
                "metadata": {
                    "page_number": 2,
                    "table_id": "table_1",
                    "text_as_html": "<table><tr><td>Header</td><td>Data</td></tr></table>",
                    "image_url": "https://example.com/table.png",  # Mock URL
                },
                "structural_metadata": {
                    "source_filename": "test.pdf",
                    "page_number": 2,
                    "content_type": "table",
                    "element_category": "Table",
                    "element_id": "table_1",
                },
            }
        ],
        "extracted_pages": {
            "1": {
                "url": "https://example.com/page1.png",  # Mock URL
                "storage_path": "extracted-pages/test/page1.png",
                "filename": "page1.png",
                "complexity": "complex",
                "structural_metadata": {
                    "source_filename": "test.pdf",
                    "page_number": 1,
                    "content_type": "full_page_with_images",
                    "element_category": "ExtractedPage",
                    "element_id": "image_1",
                    "image_filepath": "/path/to/page1.png",
                },
            }
        },
        "page_sections": {"1": "1.2 Demonstrationsejendommen"},
    }

    # Initialize enrichment step
    config = {
        "vlm_model": "anthropic/claude-3-5-sonnet",
        "caption_language": "Danish",
        "max_text_context_length": 1500,
        "max_page_text_elements": 5,
    }

    enrichment_step = EnrichmentStep(config)

    print(f"🤖 Testing with mock data:")
    print(f"   Text elements: {len(mock_metadata_output['text_elements'])}")
    print(f"   Table elements: {len(mock_metadata_output['table_elements'])}")
    print(f"   Extracted pages: {len(mock_metadata_output['extracted_pages'])}")

    # Execute enrichment step
    print(f"\n🚀 Executing enrichment step...")
    start_time = datetime.utcnow()

    result = await enrichment_step.execute(mock_metadata_output)

    duration = (datetime.utcnow() - start_time).total_seconds()

    print(f"\n✅ Enrichment step completed in {duration:.2f} seconds")
    print(f"📊 Status: {result.status}")

    if result.status == "completed":
        print(f"\n📈 SUMMARY STATISTICS:")
        for key, value in result.summary_stats.items():
            print(f"   {key}: {value}")

        print(f"\n🎉 Mock data test PASSED!")
        return True
    else:
        print(f"❌ Mock data test failed: {result.error_message}")
        return False


if __name__ == "__main__":
    # Run tests
    async def main():
        print("🚀 Starting enrichment step tests...\n")

        # Test 1: Standalone with mock data
        success1 = await test_enrichment_step_standalone()

        print("\n" + "=" * 60 + "\n")

        # Test 2: With real metadata step output
        success2 = await test_enrichment_step()

        print(f"\n📊 TEST RESULTS:")
        print(f"   Mock data test: {'✅ PASSED' if success1 else '❌ FAILED'}")
        print(f"   Real data test: {'✅ PASSED' if success2 else '❌ FAILED'}")

        if success1 and success2:
            print(f"\n🎉 All tests PASSED!")
            sys.exit(0)
        else:
            print(f"\n❌ Some tests FAILED!")
            sys.exit(1)

    asyncio.run(main())
