import os
from pathlib import Path

import pytest

# Load backend/.env so os.getenv-based skips and clients see Supabase env
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except Exception:
    # If python-dotenv is not installed, proceed; tests that require env will skip
    pass


@pytest.fixture(scope="session")
def flat_app_fixture():
    # Importing main creates the FastAPI app with routers
    # Skip if env is not configured to avoid startup failures
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"):
        pytest.skip("Supabase env not configured")
    from src.main import app

    return app
