from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class UserProfile(BaseModel):
    """User profile model matching the user_profiles table"""

    id: UUID = Field(description="User ID from Supabase Auth")
    email: Optional[str] = Field(None, description="User email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Profile creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Profile last update timestamp"
    )

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class UserProfileCreate(BaseModel):
    """Model for creating a new user profile"""

    email: Optional[str] = None
    full_name: Optional[str] = None


class UserProfileUpdate(BaseModel):
    """Model for updating an existing user profile"""

    email: Optional[str] = None
    full_name: Optional[str] = None
