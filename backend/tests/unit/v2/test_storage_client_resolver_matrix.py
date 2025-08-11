import os

import pytest

from src.services.storage_client_resolver import StorageClientResolver


@pytest.mark.skipif(
    not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY") and os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
    reason="Supabase env not set",
)
def test_resolver_returns_admin_for_trusted_ops():
    resolver = StorageClientResolver()
    admin_client = resolver.get_client(trusted=True)
    assert admin_client is not None

    ensure_bucket = resolver.get_client(trusted=True, operation="ensure_bucket")
    assert ensure_bucket is not None

    delete_client = resolver.get_client(trusted=True, operation="delete")
    assert delete_client is not None


@pytest.mark.skipif(
    not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY") and os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
    reason="Supabase env not set",
)
def test_resolver_prefers_anon_for_user_scoped():
    resolver = StorageClientResolver()
    anon_for_public = resolver.get_client(access_level="public")
    assert anon_for_public is not None

    anon_for_user = resolver.get_client(user_id="user-1")
    assert anon_for_user is not None
