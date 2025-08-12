from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Query(BaseModel):
    """Query model matching the queries table"""

    id: UUID = Field(description="Query unique identifier")
    user_id: UUID = Field(description="User ID from Supabase Auth")
    query_text: str = Field(description="User's query text")
    response_text: str | None = Field(None, description="Generated response text")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Query metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Query creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class QueryCreate(BaseModel):
    """Model for creating a new query"""

    query_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryUpdate(BaseModel):
    """Model for updating an existing query"""

    response_text: str | None = None
    metadata: dict[str, Any] | None = None


class QueryResponse(BaseModel):
    """Response model for query processing"""

    query_id: UUID
    response_text: str
    sources: list[dict[str, Any]] = Field(default_factory=list, description="Source documents/chunks")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Response metadata")
    processing_time: float | None = Field(None, description="Processing time in seconds")

    model_config = ConfigDict()


class QueryWithResponse(Query):
    """Query model including its response"""

    response: QueryResponse | None = None


class QueryHistory(BaseModel):
    """Model for query history"""

    queries: list[Query] = Field(default_factory=list, description="List of user queries")
    total_count: int = Field(0, description="Total number of queries")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(10, description="Number of queries per page")
