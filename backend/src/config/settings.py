from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List, Union
import os


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Database (Supabase)
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None

    # AI/ML APIs
    openai_api_key: Optional[str] = None
    voyage_api_key: Optional[str] = None
    langchain_api_key: Optional[str] = None
    langchain_tracing_v2: Optional[str] = None
    langchain_project: Optional[str] = None

    # Application
    app_name: str = "ConstructionRAG"
    app_version: str = "1.0.0"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS - handle both string and list formats
    cors_origins: Union[str, List[str]] = ["*"]

    # File upload
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_file_types: Union[str, List[str]] = [".pdf"]

    # Pipeline configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_model: str = "voyage-large-2"
    embedding_dimensions: int = 1536

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("allowed_file_types", mode="before")
    @classmethod
    def parse_allowed_file_types(cls, v):
        if isinstance(v, str):
            return [ft.strip() for ft in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_database_url() -> str:
    """Get database URL for Supabase"""
    settings = get_settings()
    if not settings.supabase_url:
        raise ValueError("SUPABASE_URL environment variable is required")
    return settings.supabase_url


def get_supabase_keys() -> tuple[str, str]:
    """Get Supabase keys"""
    settings = get_settings()
    if not settings.supabase_anon_key or not settings.supabase_service_role_key:
        raise ValueError(
            "SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY environment variables are required"
        )
    return settings.supabase_anon_key, settings.supabase_service_role_key
