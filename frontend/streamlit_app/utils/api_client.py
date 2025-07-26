import requests
import os
from typing import Optional, Dict, Any, List
import streamlit as st


class APIClient:
    """API client for communicating with the backend"""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv(
            "BACKEND_API_URL", "http://localhost:8000"
        )
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to the API"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API request failed: {str(e)}")
            return {"error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Check backend health"""
        return self._make_request("GET", "/health")

    def upload_document(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Upload a document"""
        files = {"file": (filename, file_data, "application/pdf")}
        return self._make_request("POST", "/api/documents/upload", files=files)

    def get_documents(self) -> List[Dict[str, Any]]:
        """Get list of documents"""
        response = self._make_request("GET", "/api/documents")
        return response.get("documents", [])

    def get_document_status(self, document_id: str) -> Dict[str, Any]:
        """Get document processing status"""
        return self._make_request("GET", f"/api/documents/{document_id}/status")

    def query_documents(self, query: str) -> Dict[str, Any]:
        """Query documents"""
        data = {"query": query}
        return self._make_request("POST", "/api/query", json=data)

    def get_pipeline_status(self, job_id: str) -> Dict[str, Any]:
        """Get pipeline processing status"""
        return self._make_request("GET", f"/api/pipeline/status/{job_id}")


# Global API client instance
@st.cache_resource
def get_api_client() -> APIClient:
    """Get cached API client instance"""
    return APIClient()
