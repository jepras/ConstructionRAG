import pytest

from src.pipeline.indexing.models import (
    to_partition_output,
    to_metadata_output,
    to_enrichment_output,
    to_chunking_output,
    to_embedding_output,
)


def test_partition_output_adapter_accepts_typical_data():
    data = {
        "text_elements": [
            {"id": "t1", "page": 1, "text": "Hello", "metadata": {"page_number": 1}},
        ],
        "table_elements": [
            {
                "id": "tab1",
                "page": 1,
                "text": "a|b",
                "metadata": {"page_number": 1},
            }
        ],
        "extracted_pages": {1: {"filename": "p1.png", "width": 100, "height": 100}},
        "page_analysis": {1: {"image_count": 2, "table_count": 0}},
        "document_metadata": {"total_pages": 2},
        "metadata": {"processing_strategy": "pymupdf_only"},
    }
    out = to_partition_output(data)
    assert out.text_elements and out.table_elements
    assert 1 in out.extracted_pages
    assert out.document_metadata["total_pages"] == 2


def test_metadata_output_adapter_accepts_page_sections():
    data = {
        "text_elements": [],
        "table_elements": [],
        "extracted_pages": {},
        "page_analysis": {},
        "document_metadata": {},
        "metadata": {},
        "page_sections": {1: "1. Introduction"},
    }
    out = to_metadata_output(data)
    assert out.page_sections == {1: "1. Introduction"}


def test_enrichment_output_adapter_preserves_structure():
    data = {
        "text_elements": [],
        "table_elements": [
            {
                "id": "tab1",
                "structural_metadata": {"page_number": 1},
                "enrichment_metadata": {"table_image_caption": "caption"},
            }
        ],
        "extracted_pages": {
            1: {
                "structural_metadata": {"page_number": 1},
                "enrichment_metadata": {"full_page_image_caption": "cap"},
            }
        },
        "page_analysis": {},
        "document_metadata": {},
        "metadata": {},
        "page_sections": {},
    }
    out = to_enrichment_output(data)
    assert (
        out.table_elements[0]["enrichment_metadata"]["table_image_caption"] == "caption"
    )
    assert (
        out.extracted_pages[1]["enrichment_metadata"]["full_page_image_caption"]
        == "cap"
    )


def test_chunking_output_adapter_accepts_dict_and_list():
    # Dict form
    dict_data = {
        "chunks": [
            {"chunk_id": "c1", "content": "x", "metadata": {"page_number": 1}},
        ],
        "chunking_metadata": {"total_chunks": 1},
    }
    out_dict = to_chunking_output(dict_data)
    assert out_dict.chunks and out_dict.chunking_metadata["total_chunks"] == 1

    # List form (flexibility)
    list_data = [
        {"chunk_id": "c2", "content": "y", "metadata": {"page_number": 2}},
    ]
    out_list = to_chunking_output(list_data)
    assert out_list.chunks and out_list.chunking_metadata == {}


def test_embedding_output_adapter_accepts_metrics():
    data = {
        "chunks_processed": 10,
        "embeddings_generated": 10,
        "embedding_model": "voyage-multilingual-2",
        "embedding_quality": {"quality_score": 0.95},
        "index_verification": {"index_status": "verified"},
    }
    out = to_embedding_output(data)
    assert out.chunks_processed == 10
    assert out.embeddings_generated == 10
    assert out.embedding_model == "voyage-multilingual-2"
    assert out.embedding_quality["quality_score"] == 0.95
    assert out.index_verification["index_status"] == "verified"
