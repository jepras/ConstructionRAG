import os
from typing import Any

import requests
import streamlit as st


class APIClient:
    """API client for communicating with the backend"""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.getenv("BACKEND_API_URL", "http://localhost:8000")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

    def _make_request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make HTTP request to the API"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API request failed: {str(e)}")
            return {"error": str(e)}

    def health_check(self) -> dict[str, Any]:
        """Check backend health"""
        return self._make_request("GET", "/health")

    def upload_document(
        self, file_data: bytes, filename: str, email: str | None = None, project_id: str | None = None
    ) -> dict[str, Any]:
        """Upload a single PDF using v2 /api/uploads."""
        files = [("files", (filename, file_data, "application/pdf"))]
        data: dict[str, Any] = {}
        if email:
            data["email"] = email
        if project_id:
            data["project_id"] = project_id
        return self._make_request("POST", "/api/uploads", files=files, data=data)

    def get_documents(
        self, project_id: str | None = None, index_run_id: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List documents (v2). Optionally scope by project_id or index_run_id."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if project_id:
            params["project_id"] = project_id
        if index_run_id:
            params["index_run_id"] = index_run_id
        response = self._make_request("GET", "/api/documents", params=params)
        return response.get("documents", [])

    def get_document(
        self, document_id: str, project_id: str | None = None, index_run_id: str | None = None
    ) -> dict[str, Any]:
        """Get single document (v2). Requires either project_id (auth flow) or index_run_id (anon email flow)."""
        params: dict[str, Any] = {}
        if project_id:
            params["project_id"] = project_id
        if index_run_id:
            params["index_run_id"] = index_run_id
        return self._make_request("GET", f"/api/documents/{document_id}", params=params)

    def get_document_status(self, document_id: str) -> dict[str, Any]:
        """Deprecated in v2; use get_document(...)."""
        st.warning("get_document_status is deprecated in v2; use get_document with project_id or index_run_id.")
        return {"error": "deprecated"}

    def query(self, query: str, indexing_run_id: str | None = None) -> dict[str, Any]:
        """Execute a query (v2)."""
        payload: dict[str, Any] = {"query": query}
        if indexing_run_id:
            payload["indexing_run_id"] = indexing_run_id
        return self._make_request("POST", "/api/queries", json=payload)

    def list_indexing_runs(
        self, project_id: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List indexing runs (v2)."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if project_id:
            params["project_id"] = project_id
        return self._make_request("GET", "/api/indexing-runs", params=params) or []

    def get_indexing_run(self, run_id: str) -> dict[str, Any]:
        """Get a single indexing run (v2)."""
        return self._make_request("GET", f"/api/indexing-runs/{run_id}")

    def get_indexing_run_progress(self, run_id: str) -> dict[str, Any]:
        """Get indexing run progress (v2)."""
        return self._make_request("GET", f"/api/indexing-runs/{run_id}/progress")

    def get_pipeline_status(self, job_id: str) -> dict[str, Any]:
        """Deprecated alias for get_indexing_run (v2)."""
        st.warning("get_pipeline_status is deprecated in v2; use get_indexing_run or get_indexing_run_progress.")
        return self.get_indexing_run(job_id)


# Global API client instance
@st.cache_resource
def get_api_client() -> APIClient:
    """Get cached API client instance"""
    return APIClient()
