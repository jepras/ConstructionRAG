from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.constants import ANONYMOUS_USER_ID, ANONYMOUS_USERNAME


class UserProfile(BaseModel):
    """User profile model matching the user_profiles table"""

    id: UUID = Field(description="User ID from Supabase Auth")
    username: str = Field(description="User's unique username")
    email: str | None = Field(None, description="User email address")
    full_name: str | None = Field(None, description="User's full name")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Profile creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Profile last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class UserContext(BaseModel):
    """Unified user context for authentication handling"""

    id: str = Field(description="User ID (UUID string)")
    username: str = Field(description="Username for URL generation")
    email: Optional[str] = Field(None, description="User email address")
    is_authenticated: bool = Field(False, description="Whether user is authenticated")

    @classmethod
    def anonymous(cls) -> "UserContext":
        """Create anonymous user context"""
        return cls(
            id=ANONYMOUS_USER_ID,
            username=ANONYMOUS_USERNAME,
            is_authenticated=False
        )

    @classmethod
    def authenticated(cls, user_id: str, username: str, email: str) -> "UserContext":
        """Create authenticated user context"""
        return cls(
            id=user_id,
            username=username,
            email=email,
            is_authenticated=True
        )

    @property
    def isAuthenticated(self) -> bool:
        """Check if user is authenticated (not anonymous)"""
        return self.is_authenticated and self.id != ANONYMOUS_USER_ID


class UserProfileCreate(BaseModel):
    """Model for creating a new user profile"""

    username: str = Field(description="User's unique username")
    email: str | None = None
    full_name: str | None = None


class UserProfileUpdate(BaseModel):
    """Model for updating an existing user profile"""

    username: str | None = None
    email: str | None = None
    full_name: str | None = None
