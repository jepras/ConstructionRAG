from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MetadataCollectionOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    indexing_run_id: str
    total_documents: int
    total_chunks: int
    total_pages_analyzed: int = 0
    documents: list[dict[str, Any]] = Field(default_factory=list)
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    chunks_with_embeddings: list[dict[str, Any]] = Field(default_factory=list)
    section_headers_distribution: dict[str, int] = Field(default_factory=dict)
    images_processed: int = 0
    tables_processed: int = 0
    document_filenames: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    upload_type: str | None = None
    user_id: str | None = None
    project_id: str | None = None


class OverviewGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    project_overview: str


class SemanticClusteringOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    clusters: dict[int, Any] | None = None
    cluster_summaries: list[dict[str, Any]] | None = None
    n_clusters: int | None = None


class StructureGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    wiki_structure: dict[str, Any]


class PageContentRetrievalOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    page_contents: dict[str, Any]


class MarkdownGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    generated_pages: dict[str, Any]


# --- Adapters ---


def to_metadata_output(data: dict[str, Any]) -> MetadataCollectionOutput:
    return MetadataCollectionOutput(**data)


def to_overview_output(data: dict[str, Any]) -> OverviewGenerationOutput:
    # Some steps may store under 'project_overview'
    if "project_overview" in data:
        return OverviewGenerationOutput(project_overview=data["project_overview"])
    return OverviewGenerationOutput(project_overview=data)


def to_semantic_output(data: dict[str, Any]) -> SemanticClusteringOutput:
    return SemanticClusteringOutput(**data)


def to_structure_output(data: dict[str, Any]) -> StructureGenerationOutput:
    if "wiki_structure" in data:
        return StructureGenerationOutput(wiki_structure=data["wiki_structure"])
    return StructureGenerationOutput(wiki_structure=data)


def to_page_contents_output(data: dict[str, Any]) -> PageContentRetrievalOutput:
    if "page_contents" in data:
        return PageContentRetrievalOutput(page_contents=data["page_contents"])
    return PageContentRetrievalOutput(page_contents=data)


def to_markdown_output(data: dict[str, Any]) -> MarkdownGenerationOutput:
    if "generated_pages" in data:
        return MarkdownGenerationOutput(generated_pages=data["generated_pages"])
    return MarkdownGenerationOutput(generated_pages=data)
