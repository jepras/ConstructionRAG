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
    client_default = resolver.get_client(user_id=None)
    assert client_default is not None
    client_trusted = resolver.get_client(trusted=True)
    assert client_trusted is not None
