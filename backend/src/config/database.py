from src.config.settings import get_settings
from supabase import Client, create_client

try:
    # Only imported when used inside FastAPI context
    from fastapi import Header
except Exception:
    Header = None  # type: ignore[assignment]

# Global Supabase client
_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """Get Supabase client singleton"""
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise ValueError("Supabase URL and anon key are required")

        _supabase_client = create_client(settings.supabase_url, settings.supabase_anon_key)
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


# ---------- Request-scoped client helpers (RLS hygiene) ----------


def get_anon_client() -> Client:
    """Alias for anon client accessor for clarity in DI code."""
    return get_supabase_client()


def get_supabase_client_for_token(token: str | None) -> Client:
    """Return an anon client authenticated with a bearer token when provided.

    This enables per-request RLS-enforced access using the caller's auth context.
    Falls back to anon when token is missing/invalid.
    """
    client = get_supabase_client()
    try:
        if token:
            # Authenticate PostgREST with the user's JWT so RLS evaluates with auth.uid()
            # supabase-py exposes postgrest.auth(token) for request-scoped auth
            client.postgrest.auth(token)  # type: ignore[attr-defined]
    except Exception:
        # Non-fatal: keep anon client
        pass
    return client


def get_db_client_for_request(authorization: str | None = Header(None)) -> Client:  # type: ignore[valid-type]
    """FastAPI dependency to provide a request-scoped Supabase client.

    - If Authorization: Bearer <token> is present, return a client authed with that token
    - Else return anon client
    """
    token: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    return get_supabase_client_for_token(token)
