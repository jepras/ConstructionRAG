from __future__ import annotations

import os

import pytest

from src.services.storage_client_resolver import StorageClientResolver


@pytest.mark.skipif(
    not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
    reason="Supabase admin env not set",
)
def test_storage_client_resolver_returns_client():
    resolver = StorageClientResolver()
    client = resolver.get_client(user_id=None)
    assert client is not None
