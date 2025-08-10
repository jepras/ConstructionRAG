from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PartitionOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text_elements: list[dict[str, Any]] = Field(default_factory=list)
    table_elements: list[dict[str, Any]] = Field(default_factory=list)
    extracted_pages: dict[int, dict[str, Any]] = Field(default_factory=dict)
    page_analysis: dict[int, dict[str, Any]] = Field(default_factory=dict)
    document_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetadataOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text_elements: list[dict[str, Any]] = Field(default_factory=list)
    table_elements: list[dict[str, Any]] = Field(default_factory=list)
    extracted_pages: dict[int, dict[str, Any]] = Field(default_factory=dict)
    page_analysis: dict[int, dict[str, Any]] = Field(default_factory=dict)
    document_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    page_sections: dict[int, str] = Field(default_factory=dict)


class EnrichmentOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text_elements: list[dict[str, Any]] = Field(default_factory=list)
    table_elements: list[dict[str, Any]] = Field(default_factory=list)
    extracted_pages: dict[int, dict[str, Any]] = Field(default_factory=dict)
    page_analysis: dict[int, dict[str, Any]] = Field(default_factory=dict)
    document_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    page_sections: dict[int, str] = Field(default_factory=dict)


class ChunkingOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chunks: list[dict[str, Any]] = Field(default_factory=list)
    chunking_metadata: dict[str, Any] = Field(default_factory=dict)


class EmbeddingOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chunks_processed: int
    embeddings_generated: int
    embedding_model: str
    embedding_quality: dict[str, Any] = Field(default_factory=dict)
    index_verification: dict[str, Any] = Field(default_factory=dict)


# --- Adapters ---


def to_partition_output(data: dict[str, Any]) -> PartitionOutput:
    return PartitionOutput(**data)


def to_metadata_output(data: dict[str, Any]) -> MetadataOutput:
    return MetadataOutput(**data)


def to_enrichment_output(data: dict[str, Any]) -> EnrichmentOutput:
    return EnrichmentOutput(**data)


def to_chunking_output(data: dict[str, Any]) -> ChunkingOutput:
    # Some callers might pass under key 'chunks'
    if "chunks" in data and "chunking_metadata" in data:
        return ChunkingOutput(**data)
    # Accept direct list of chunks for flexibility
    if isinstance(data, list):
        return ChunkingOutput(chunks=data, chunking_metadata={})
    return ChunkingOutput(
        chunks=data.get("chunks", []),
        chunking_metadata=data.get("chunking_metadata", {}),
    )


def to_embedding_output(data: dict[str, Any]) -> EmbeddingOutput:
    return EmbeddingOutput(**data)


