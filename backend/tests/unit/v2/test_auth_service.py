import os

import pytest

# Skip entire module if Supabase env is not configured to avoid import-time client initialization
if not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY")):
    pytest.skip("Supabase env not configured; skipping auth tests", allow_module_level=True)

from src.services.auth_service import auth_service, get_current_user
from src.utils.exceptions import AuthenticationError


@pytest.mark.skipif(
    not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY")),
    reason="Supabase env not set",
)
@pytest.mark.asyncio
async def test_get_current_user_invalid_token_returns_auth_error():
    class Creds:
        def __init__(self, token: str) -> None:
            self.scheme = "Bearer"
            self.credentials = token

    creds = Creds(token="invalid.token.value")
    with pytest.raises(AuthenticationError):
        await get_current_user(creds)  # type: ignore[arg-type]


@pytest.mark.skipif(
    not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY")),
    reason="Supabase env not set",
)
@pytest.mark.asyncio
async def test_get_current_user_optional_allows_none():
    # Directly exercise service: invalid token should yield None from service level
    user = await auth_service.get_current_user("invalid")
    assert user is None
