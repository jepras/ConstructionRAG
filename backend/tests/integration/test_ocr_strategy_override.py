#!/usr/bin/env python3
"""
Test script to verify OCR strategy override works correctly.
This test will:
1. Show current config
2. Test with default (auto) strategy
3. Test with explicit hybrid_ocr_images strategy
4. Test with explicit pymupdf_only strategy
"""

import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pipeline.indexing.steps.partition import PartitionStep
from src.pipeline.shared.models import DocumentInput
from src.services.config_service import ConfigService

# Test PDF path - architectural drawing with vector graphics
TEST_PDF = "/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/small-complicated/DNI_K07_H1_ETX_N400 Belysningsplan st. og 1sal.pdf"


async def test_ocr_strategy(strategy: str = "auto"):
    """Test partition step with specific OCR strategy"""
    
    print(f"\n{'='*60}")
    print(f"Testing OCR Strategy: {strategy}")
    print(f"{'='*60}")
    
    # Load config and override OCR strategy
    config_service = ConfigService()
    config = config_service.get_effective_config("indexing")
    partition_config = config.get("partition", {})
    
    # Override the strategy
    original_strategy = partition_config.get("ocr_strategy", "auto")
    partition_config["ocr_strategy"] = strategy
    
    print(f"Original strategy: {original_strategy}")
    print(f"Override strategy: {strategy}")
    
    # Create partition step with modified config
    partition_step = PartitionStep(partition_config)
    
    # Create test document input with valid UUIDs
    from uuid import uuid4
    
    doc_input = DocumentInput(
        document_id=str(uuid4()),
        filename=Path(TEST_PDF).name,
        file_path=TEST_PDF,
        run_id=str(uuid4()),
        index_run_id=str(uuid4()),
        upload_type="email",
        user_id=None,
        project_id=None
    )
    
    # Run partition step and measure time
    start_time = datetime.now()
    
    try:
        result = await partition_step.execute(doc_input)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Extract results
        strategy_used = result.data.get("metadata", {}).get("processing_strategy", "unknown")
        was_forced = result.data.get("metadata", {}).get("forced_strategy", False)
        text_elements = result.summary_stats.get("text_elements", 0)
        table_elements = result.summary_stats.get("table_elements", 0)
        extracted_pages = result.summary_stats.get("extracted_pages", 0)
        
        print(f"\n✅ Success!")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Strategy used: {strategy_used}")
        print(f"Was forced: {was_forced}")
        print(f"Text elements: {text_elements}")
        print(f"Table elements: {table_elements}")  
        print(f"Extracted pages: {extracted_pages}")
        
        # Show detection info if available
        hybrid_detection = result.data.get("metadata", {}).get("hybrid_detection")
        if hybrid_detection:
            print(f"\nDocument Detection:")
            print(f"  - Is scanned: {hybrid_detection.get('is_likely_scanned', False)}")
            print(f"  - Confidence: {hybrid_detection.get('detection_confidence', 0):.2f}")
            print(f"  - Avg text/page: {hybrid_detection.get('avg_text_per_page', 0):.0f}")
        
        return {
            "strategy_requested": strategy,
            "strategy_used": strategy_used,
            "was_forced": was_forced,
            "duration": duration,
            "text_elements": text_elements,
            "success": True
        }
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {
            "strategy_requested": strategy,
            "error": str(e),
            "success": False
        }


async def main():
    """Run tests with different OCR strategies"""
    
    print("\n" + "="*60)
    print("OCR STRATEGY OVERRIDE TEST")
    print("="*60)
    
    # Check if test PDF exists
    if not Path(TEST_PDF).exists():
        print(f"\n⚠️  Test PDF not found: {TEST_PDF}")
        print("Please update TEST_PDF path in the script to point to a valid PDF file")
        
        # Try to find a PDF in the test data directory
        test_data_dir = Path("tests/test_data")
        if test_data_dir.exists():
            pdfs = list(test_data_dir.glob("*.pdf"))
            if pdfs:
                print(f"\nFound PDFs in test_data directory:")
                for pdf in pdfs[:5]:
                    print(f"  - {pdf}")
        return
    
    # Load and show current config
    config_service = ConfigService()
    config = config_service.get_effective_config("indexing")
    current_strategy = config.get("partition", {}).get("ocr_strategy", "auto")
    
    print(f"\nCurrent config OCR strategy: {current_strategy}")
    print(f"Test PDF: {TEST_PDF}")
    
    # Test different strategies
    results = []
    
    # Test 1: Auto (default)
    result = await test_ocr_strategy("auto")
    results.append(result)
    
    # Test 2: Force PyMuPDF only
    result = await test_ocr_strategy("pymupdf_only")
    results.append(result)
    
    # Test 3: Force hybrid OCR (if Unstructured is available)
    result = await test_ocr_strategy("hybrid_ocr_images")
    results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    print(f"\n{'Strategy':<20} {'Used':<20} {'Forced':<8} {'Duration':<10} {'Status'}")
    print("-"*70)
    
    for r in results:
        if r["success"]:
            status = "✅ Success"
            used = r.get("strategy_used", "N/A")
            forced = "Yes" if r.get("was_forced") else "No"
            duration = f"{r.get('duration', 0):.2f}s"
        else:
            status = "❌ Failed"
            used = "N/A"
            forced = "N/A"
            duration = "N/A"
        
        print(f"{r['strategy_requested']:<20} {used:<20} {forced:<8} {duration:<10} {status}")
    
    # Performance comparison
    successful_results = [r for r in results if r.get("success")]
    if len(successful_results) > 1:
        print(f"\n{'='*60}")
        print("PERFORMANCE COMPARISON")
        print(f"{'='*60}")
        
        base_result = next((r for r in successful_results if r["strategy_requested"] == "pymupdf_only"), successful_results[0])
        base_duration = base_result["duration"]
        
        for r in successful_results:
            if r["strategy_requested"] != base_result["strategy_requested"]:
                speedup = base_duration / r["duration"] if r["duration"] > 0 else 0
                diff = r["duration"] - base_duration
                print(f"\n{r['strategy_requested']} vs {base_result['strategy_requested']}:")
                print(f"  - Time difference: {diff:+.2f}s")
                print(f"  - Speed factor: {speedup:.2f}x")


if __name__ == "__main__":
    asyncio.run(main())