from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserProfile(BaseModel):
    """User profile model matching the user_profiles table"""

    id: UUID = Field(description="User ID from Supabase Auth")
    email: str | None = Field(None, description="User email address")
    full_name: str | None = Field(None, description="User's full name")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Profile creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Profile last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class UserProfileCreate(BaseModel):
    """Model for creating a new user profile"""

    email: str | None = None
    full_name: str | None = None


class UserProfileUpdate(BaseModel):
    """Model for updating an existing user profile"""

    email: str | None = None
    full_name: str | None = None
