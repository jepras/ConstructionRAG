import streamlit as st
import requests
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json


class AuthManager:
    """Authentication manager for Streamlit frontend"""

    def __init__(self):
        self.base_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
        self.auth_url = f"{self.base_url}/api/auth"

    def sign_up(self, email: str, password: str) -> Dict[str, Any]:
        """Sign up a new user"""
        try:
            response = requests.post(
                f"{self.auth_url}/signup",
                json={"email": email, "password": password},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Sign up failed: {str(e)}")
            return {"success": False, "message": str(e)}

    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in an existing user"""
        try:
            response = requests.post(
                f"{self.auth_url}/signin",
                json={"email": email, "password": password},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()

            if result.get("success"):
                # Store auth data in session state
                st.session_state.authenticated = True
                st.session_state.user_id = result.get("user_id")
                st.session_state.email = result.get("email")
                st.session_state.access_token = result.get("access_token")
                st.session_state.refresh_token = result.get("refresh_token")
                st.session_state.token_expires_at = result.get("expires_at")

                # Store tokens in session state for persistence
                self._save_auth_data(result)

            return result
        except requests.exceptions.RequestException as e:
            st.error(f"Sign in failed: {str(e)}")
            return {"success": False, "message": str(e)}

    def sign_out(self) -> Dict[str, Any]:
        """Sign out the current user"""
        try:
            access_token = self._get_access_token()
            if not access_token:
                return {"success": True, "message": "Already signed out"}

            response = requests.post(
                f"{self.auth_url}/signout",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()

            # Clear session state
            self._clear_auth_data()

            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Sign out failed: {str(e)}")
            # Clear session state anyway
            self._clear_auth_data()
            return {"success": False, "message": str(e)}

    def reset_password(self, email: str) -> Dict[str, Any]:
        """Send password reset email"""
        try:
            response = requests.post(
                f"{self.auth_url}/reset-password",
                json={"email": email},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Password reset failed: {str(e)}")
            return {"success": False, "message": str(e)}

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user information"""
        try:
            access_token = self._get_access_token()
            if not access_token:
                return None

            response = requests.get(
                f"{self.auth_url}/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            # Token might be expired, try to refresh
            if self._refresh_token():
                return self.get_current_user()
            return None

    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        if not st.session_state.get("authenticated", False):
            return False

        # Check if token is expired
        expires_at = st.session_state.get("token_expires_at")
        if expires_at:
            try:
                expires_datetime = datetime.fromisoformat(
                    expires_at.replace("Z", "+00:00")
                )
                if datetime.now(expires_datetime.tzinfo) >= expires_datetime:
                    # Token expired, try to refresh
                    return self._refresh_token()
            except:
                pass

        return True

    def _get_access_token(self) -> Optional[str]:
        """Get current access token"""
        return st.session_state.get("access_token")

    def _refresh_token(self) -> bool:
        """Refresh access token"""
        try:
            refresh_token = st.session_state.get("refresh_token")
            if not refresh_token:
                return False

            response = requests.post(
                f"{self.auth_url}/refresh",
                json={"refresh_token": refresh_token},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()

            if result.get("success"):
                # Update session state with new tokens
                st.session_state.access_token = result.get("access_token")
                st.session_state.refresh_token = result.get("refresh_token")
                st.session_state.token_expires_at = result.get("expires_at")

                # Update stored auth data
                self._save_auth_data(result)
                return True

            return False
        except requests.exceptions.RequestException:
            # Refresh failed, clear auth data
            self._clear_auth_data()
            return False

    def _save_auth_data(self, auth_data: Dict[str, Any]):
        """Save authentication data to session state"""
        st.session_state.authenticated = True
        st.session_state.user_id = auth_data.get("user_id")
        st.session_state.email = auth_data.get("email")
        st.session_state.access_token = auth_data.get("access_token")
        st.session_state.refresh_token = auth_data.get("refresh_token")
        st.session_state.token_expires_at = auth_data.get("expires_at")

    def _clear_auth_data(self):
        """Clear authentication data from session state"""
        keys_to_clear = [
            "authenticated",
            "user_id",
            "email",
            "access_token",
            "refresh_token",
            "token_expires_at",
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]


# Global auth manager instance
@st.cache_resource
def get_auth_manager() -> AuthManager:
    """Get cached auth manager instance"""
    return AuthManager()


def init_auth():
    """Initialize authentication state"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "auth_manager" not in st.session_state:
        st.session_state.auth_manager = get_auth_manager()


def require_auth():
    """Decorator to require authentication for a page"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            init_auth()
            auth_manager = st.session_state.auth_manager

            if not auth_manager.is_authenticated():
                st.error("Please sign in to access this page.")
                st.stop()

            return func(*args, **kwargs)

        return wrapper

    return decorator
