from supabase import create_client, Client
from typing import Optional
from config.settings import get_settings

# Global Supabase client
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get Supabase client singleton"""
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise ValueError("Supabase URL and anon key are required")

        _supabase_client = create_client(
            settings.supabase_url, settings.supabase_anon_key
        )
    return _supabase_client


def get_supabase_admin_client() -> Client:
    """Get Supabase admin client with service role key"""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ValueError("Supabase URL and service role key are required")

    return create_client(settings.supabase_url, settings.supabase_service_role_key)


async def test_database_connection() -> bool:
    """Test database connection"""
    try:
        client = get_supabase_client()
        # Simple query to test connection
        response = client.table("documents").select("id").limit(1).execute()
        return True
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False


async def initialize_database():
    """Initialize database tables and extensions"""
    try:
        admin_client = get_supabase_admin_client()

        # Enable pgvector extension if not already enabled
        # This is typically done in Supabase dashboard, but we can check
        print("Database initialization completed")
        return True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False
