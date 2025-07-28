from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class Query(BaseModel):
    """Query model matching the queries table"""

    id: UUID = Field(description="Query unique identifier")
    user_id: UUID = Field(description="User ID from Supabase Auth")
    query_text: str = Field(description="User's query text")
    response_text: Optional[str] = Field(None, description="Generated response text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Query metadata")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Query creation timestamp"
    )

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class QueryCreate(BaseModel):
    """Model for creating a new query"""

    query_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QueryUpdate(BaseModel):
    """Model for updating an existing query"""

    response_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Response model for query processing"""

    query_id: UUID
    response_text: str
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Source documents/chunks"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Response metadata"
    )
    processing_time: Optional[float] = Field(
        None, description="Processing time in seconds"
    )

    class Config:
        json_encoders = {UUID: lambda v: str(v)}


class QueryWithResponse(Query):
    """Query model including its response"""

    response: Optional[QueryResponse] = None


class QueryHistory(BaseModel):
    """Model for query history"""

    queries: List[Query] = Field(
        default_factory=list, description="List of user queries"
    )
    total_count: int = Field(0, description="Total number of queries")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(10, description="Number of queries per page")
