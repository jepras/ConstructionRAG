import os

import pytest


@pytest.fixture(scope="session")
def flat_app_fixture():
    # Importing main creates the FastAPI app with routers
    # Skip if env is not configured to avoid startup failures
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"):
        pytest.skip("Supabase env not configured")
    from src.main import app

    return app
