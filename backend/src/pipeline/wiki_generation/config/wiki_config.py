"""Configuration for wiki generation pipeline."""

from typing import Any  # noqa: F401
from pydantic import BaseModel, Field


class WikiConfig(BaseModel):
    """Configuration for wiki generation pipeline."""

    # Language settings
    language: str = Field("danish", description="Wiki language")
    model: str = Field("google/gemini-2.5-flash", description="LLM model to use")

    # Wiki structure targets
    min_pages: int = Field(2, description="Minimum number of pages to generate")
    max_pages: int = Field(4, description="Maximum number of pages to generate")
    min_queries_per_page: int = Field(
        3, description="Minimum number of queries to generate per page"
    )
    max_queries_per_page: int = Field(
        5, description="Maximum number of queries to generate per page"
    )

    # Vector search settings
    similarity_threshold: float = Field(
        0.3, description="Similarity threshold for vector search"
    )
    max_chunks_per_query: int = Field(
        10, description="Maximum chunks to return per query"
    )
    overview_query_count: int = Field(
        12, description="Number of overview queries to use"
    )

    # Semantic clustering settings
    min_clusters: int = Field(4, description="Minimum number of semantic clusters")
    max_clusters: int = Field(10, description="Maximum number of semantic clusters")
    random_seed: int = Field(42, description="Random seed for clustering")

    # LLM generation settings
    overview_max_tokens: int = Field(
        4000, description="Maximum tokens for overview generation"
    )
    structure_max_tokens: int = Field(
        6000, description="Maximum tokens for structure generation"
    )
    page_max_tokens: int = Field(8000, description="Maximum tokens for page generation")
    temperature: float = Field(0.3, description="Temperature for LLM generation")

    # Timeout settings
    api_timeout_seconds: float = Field(30.0, description="API timeout in seconds")

    # Content limits to prevent oversized prompts
    max_chunks_in_prompt: int = Field(
        10, description="Maximum chunks to include in prompts (reduced from 15)"
    )
    content_preview_length: int = Field(
        600, description="Length of content previews (reduced from 800)"
    )
    save_intermediate_results: bool = Field(
        True, description="Save intermediate results"
    )

    # Storage settings
    bucket_name: str = Field("pipeline-assets", description="Storage bucket name")

    class Config:
        """Pydantic configuration."""

        extra = "forbid"
