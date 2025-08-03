import os
from pathlib import Path


def get_backend_url() -> str:
    """Get the backend URL from environment or default"""
    # Try to load backend .env file if it exists
    backend_env_path = Path(__file__).parent.parent.parent / "backend" / ".env"
    if backend_env_path.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(backend_env_path)
        except ImportError:
            pass  # dotenv not available, continue with environment variables

    backend_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
    return backend_url
