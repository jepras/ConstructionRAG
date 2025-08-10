from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class MetadataCollectionOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    indexing_run_id: str
    total_documents: int
    total_chunks: int
    total_pages_analyzed: int = 0
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    chunks: List[Dict[str, Any]] = Field(default_factory=list)
    chunks_with_embeddings: List[Dict[str, Any]] = Field(default_factory=list)
    section_headers_distribution: Dict[str, int] = Field(default_factory=dict)
    images_processed: int = 0
    tables_processed: int = 0
    document_filenames: List[str] = Field(default_factory=list)
    document_ids: List[str] = Field(default_factory=list)
    upload_type: str | None = None
    user_id: str | None = None
    project_id: str | None = None


class OverviewGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    project_overview: Dict[str, Any]


class SemanticClusteringOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    clusters: Dict[str, Any] | None = None
    semantic_analysis: Dict[str, Any] | None = None


class StructureGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    wiki_structure: Dict[str, Any]


class PageContentRetrievalOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    page_contents: Dict[str, Any]


class MarkdownGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    generated_pages: Dict[str, Any]


# --- Adapters ---


def to_metadata_output(data: Dict[str, Any]) -> MetadataCollectionOutput:
    return MetadataCollectionOutput(**data)


def to_overview_output(data: Dict[str, Any]) -> OverviewGenerationOutput:
    # Some steps may store under 'project_overview'
    if "project_overview" in data:
        return OverviewGenerationOutput(project_overview=data["project_overview"])
    return OverviewGenerationOutput(project_overview=data)


def to_semantic_output(data: Dict[str, Any]) -> SemanticClusteringOutput:
    return SemanticClusteringOutput(**data)


def to_structure_output(data: Dict[str, Any]) -> StructureGenerationOutput:
    if "wiki_structure" in data:
        return StructureGenerationOutput(wiki_structure=data["wiki_structure"])
    return StructureGenerationOutput(wiki_structure=data)


def to_page_contents_output(data: Dict[str, Any]) -> PageContentRetrievalOutput:
    if "page_contents" in data:
        return PageContentRetrievalOutput(page_contents=data["page_contents"])
    return PageContentRetrievalOutput(page_contents=data)


def to_markdown_output(data: Dict[str, Any]) -> MarkdownGenerationOutput:
    if "generated_pages" in data:
        return MarkdownGenerationOutput(generated_pages=data["generated_pages"])
    return MarkdownGenerationOutput(generated_pages=data)
