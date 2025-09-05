"""Test that bbox data is preserved through the entire pipeline"""

import pytest
from uuid import uuid4
from src.pipeline.querying.steps.retrieval import DocumentRetriever, RetrievalConfig
from src.pipeline.querying.models import QueryVariations, SearchResult


@pytest.mark.asyncio
async def test_bbox_preservation_in_retrieval():
    """Test that bbox data from metadata is correctly extracted to SearchResult for different element types"""
    
    # Mock search results with bbox in metadata for different element types
    mock_search_results = [
        {
            "id": str(uuid4()),
            "content": "Test content with text element bbox",
            "metadata": {
                "source_filename": "test.pdf",
                "page_number": 1,
                "bbox": [72.024, 795.456, 1093.035, 806.496],  # Text element bbox
                "element_category": "NarrativeText"
            },
            "similarity_score": 0.95,
            "document_id": str(uuid4()),
            "indexing_run_id": str(uuid4())
        },
        {
            "id": str(uuid4()),
            "content": "Type: Table\n\nSummary: |Col1|Col2|Col3|\n|---|---|---|\n|Data1|Data2|Data3|",
            "metadata": {
                "source_filename": "test.pdf",
                "page_number": 2,
                "bbox": [100.5, 200.0, 500.0, 350.5],  # Table bbox coordinates
                "element_category": "Table"
            },
            "similarity_score": 0.90,
            "document_id": str(uuid4()),
            "indexing_run_id": str(uuid4())
        },
        {
            "id": str(uuid4()),
            "content": "Type: Image\n\nSummary: Construction diagram showing building layout",
            "metadata": {
                "source_filename": "test.pdf",
                "page_number": 3,
                "bbox": [0, 0, 595, 842],  # Full page bbox for image
                "element_category": "Image"
            },
            "similarity_score": 0.85,
            "document_id": str(uuid4()),
            "indexing_run_id": str(uuid4())
        },
        {
            "id": str(uuid4()),
            "content": "Test without bbox",
            "metadata": {
                "source_filename": "test2.pdf",
                "page_number": 4,
                # No bbox field here
                "element_category": "UncategorizedText"
            },
            "similarity_score": 0.75,
            "document_id": str(uuid4()),
            "indexing_run_id": str(uuid4())
        }
    ]
    
    # Create retriever
    config = RetrievalConfig({
        "embedding_model": "voyage-multilingual-2",
        "dimensions": 1024,
        "top_k": 15
    })
    retriever = DocumentRetriever(config, db_client=None, use_admin=False)
    
    # Convert to SearchResult objects
    search_results = retriever.convert_to_search_results(mock_search_results)
    
    # Verify results
    assert len(search_results) == 4
    
    # Text element with bbox
    assert search_results[0].bbox == [72.024, 795.456, 1093.035, 806.496]
    assert search_results[0].metadata["bbox"] == [72.024, 795.456, 1093.035, 806.496]
    assert search_results[0].metadata["element_category"] == "NarrativeText"
    
    # Table with bbox
    assert search_results[1].bbox == [100.5, 200.0, 500.0, 350.5]
    assert search_results[1].metadata["bbox"] == [100.5, 200.0, 500.0, 350.5]
    assert search_results[1].metadata["element_category"] == "Table"
    assert "Type: Table" in search_results[1].content
    
    # Full-page image with full page bbox
    assert search_results[2].bbox == [0, 0, 595, 842]
    assert search_results[2].metadata["bbox"] == [0, 0, 595, 842]
    assert search_results[2].metadata["element_category"] == "Image"
    assert "Type: Image" in search_results[2].content
    
    # Element without bbox
    assert search_results[3].bbox is None
    assert "bbox" not in search_results[3].metadata
    
    # Verify all other fields are preserved
    assert search_results[0].content == "Test content with text element bbox"
    assert search_results[0].source_filename == "test.pdf"
    assert search_results[0].page_number == 1
    assert search_results[0].similarity_score == 0.95
    
    print("✅ Bbox preservation test passed for text, table, and image elements!")


@pytest.mark.asyncio 
async def test_bbox_in_full_pipeline():
    """Test bbox preservation through actual retrieval (requires database)"""
    
    # This test would require a database with actual chunks containing bbox data
    # For now, we'll mark it as a placeholder for future integration testing
    
    # TODO: Add full integration test when we have test data with bbox coordinates
    pass


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_bbox_preservation_in_retrieval())