import sys
from pathlib import Path

# Ensure backend/src is on sys.path for absolute imports like `from src...`
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Compatibility shim for httpx>=0.28 with FastAPI/Starlette TestClient
try:
    import asyncio

    import fastapi.testclient as fastapi_testclient  # type: ignore
    import httpx  # type: ignore

    if hasattr(httpx, "ASGITransport"):

        class CompatibleTestClient:  # simple wrapper providing sync API over AsyncClient
            def __init__(self, app, base_url: str = "http://testserver", **kwargs):  # noqa: D401
                self._transport = httpx.ASGITransport(app=app)
                self._client = httpx.AsyncClient(transport=self._transport, base_url=base_url, **kwargs)

            def _run(self, coro):
                try:
                    return asyncio.run(coro)
                except RuntimeError:
                    # Fallback for already running event loop in some environments
                    loop = asyncio.new_event_loop()
                    try:
                        return loop.run_until_complete(coro)
                    finally:
                        loop.close()

            def request(self, method: str, url: str, **kwargs):
                return self._run(self._client.request(method, url, **kwargs))

            def get(self, url: str, **kwargs):
                return self.request("GET", url, **kwargs)

            def post(self, url: str, **kwargs):
                return self.request("POST", url, **kwargs)

            def put(self, url: str, **kwargs):
                return self.request("PUT", url, **kwargs)

            def delete(self, url: str, **kwargs):
                return self.request("DELETE", url, **kwargs)

            def close(self) -> None:
                self._run(self._client.aclose())

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                self.close()

        fastapi_testclient.TestClient = CompatibleTestClient  # type: ignore[assignment]
except Exception:
    # Best-effort shim; fall back silently
    pass
