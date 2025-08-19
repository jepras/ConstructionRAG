#!/usr/bin/env python3
"""Test script for wiki generation with shared retrieval services."""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline.wiki_generation.orchestrator import WikiGenerationOrchestrator

# Set up logging with DEBUG level for wiki retrieval
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Set specific loggers to DEBUG for detailed output
logging.getLogger("src.pipeline.wiki_generation").setLevel(logging.DEBUG)
logging.getLogger("src.pipeline.shared").setLevel(logging.DEBUG)


async def test_wiki_generation():
    """Test wiki generation with hardcoded indexing run."""
    # Hardcoded indexing run for testing
    INDEX_RUN_ID = "8e6d54e6-890a-45bc-a294-3bd62a46f815"
    
    print("\n" + "="*80)
    print(f"🚀 Starting Wiki Generation Test")
    print(f"   Indexing Run ID: {INDEX_RUN_ID}")
    print(f"   Config: 4 pages max, 4 queries per page")
    print("="*80 + "\n")
    
    try:
        # Create orchestrator
        orchestrator = WikiGenerationOrchestrator()
        
        # Run wiki generation pipeline
        print("📝 Generating wiki pages...")
        result = await orchestrator.run_pipeline(
            index_run_id=INDEX_RUN_ID,
            upload_type="user_project"
        )
        
        # Display results
        print("\n" + "="*80)
        print("✅ Wiki Generation Completed Successfully!")
        print(f"   Wiki Run ID: {result.id}")
        print(f"   Status: {result.status}")
        print(f"   Pages Created: {len(result.pages_metadata) if result.pages_metadata else 0}")
        
        if result.pages_metadata:
            print("\n📚 Generated Pages:")
            for i, page in enumerate(result.pages_metadata, 1):
                # Handle both dict and object types
                if hasattr(page, 'title'):
                    title = page.title
                else:
                    title = page.get('title', 'Untitled')
                print(f"   {i}. {title}")
        
        print("="*80 + "\n")
        
        return result
        
    except Exception as e:
        print("\n" + "="*80)
        print(f"❌ Wiki Generation Failed!")
        print(f"   Error: {str(e)}")
        print("="*80 + "\n")
        
        import traceback
        traceback.print_exc()
        
        return None


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_wiki_generation())
    
    if result:
        print(f"🎉 Test completed successfully! Wiki ID: {result.id}")
        sys.exit(0)
    else:
        print("💥 Test failed!")
        sys.exit(1)