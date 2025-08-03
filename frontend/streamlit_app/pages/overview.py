import streamlit as st
import requests
import logging
from utils.shared import get_backend_url

logger = logging.getLogger(__name__)


def show_overview_page():
    """Show the project overview page"""
    st.markdown("## Project Overview")
    st.markdown(
        "View your construction project summary and navigate by building systems."
    )

    # Check authentication first
    auth_manager = st.session_state.auth_manager

    if not auth_manager.is_authenticated():
        st.error("🔐 Please sign in to view project overview.")
        st.info("Use the sidebar to navigate to the Authentication page.")
        return

    # Show user info
    user_info = auth_manager.get_current_user()
    if user_info and user_info.get("user"):
        user = user_info["user"]
        st.success(f"✅ Signed in as: {user.get('email', 'N/A')}")

    # Load documents from API
    try:
        backend_url = get_backend_url()
        access_token = st.session_state.get("access_token")

        if not access_token:
            st.error("❌ No access token found. Please sign in again.")
            return

        headers = {"Authorization": f"Bearer {access_token}"}

        # Get user's documents (using email uploads for now)
        response = requests.get(
            f"{backend_url}/api/email-uploads", headers=headers, timeout=10
        )

        if response.status_code == 200:
            documents = response.json()

            if documents:
                st.markdown("### 📄 Uploaded Documents")

                for doc in documents:
                    with st.expander(f"📄 {doc.get('filename', 'Unknown')}"):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.write(f"**Status:** {doc.get('status', 'Unknown')}")
                        with col2:
                            st.write(
                                f"**Size:** {doc.get('file_size', 0) / 1024 / 1024:.1f} MB"
                            )
                        with col3:
                            st.write(
                                f"**Uploaded:** {doc.get('created_at', 'Unknown')}"
                            )

                        # Show processing results if available
                        if doc.get("processing_results"):
                            st.json(doc["processing_results"])
            else:
                st.info(
                    "📄 No documents uploaded yet. Upload documents to get started."
                )
        else:
            st.error(f"❌ Failed to load documents: {response.status_code}")

    except Exception as e:
        logger.error(f"❌ Error loading project overview: {str(e)}")
        st.error(f"❌ Error loading project overview: {str(e)}")

    # Placeholder for building systems (will be implemented later)
    st.markdown("### 🏗️ Building Systems")
    st.info("Building systems analysis will be available once documents are processed.")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("#### Electrical")
        st.markdown("📊 **Status:** Not processed")

    with col2:
        st.markdown("#### Plumbing")
        st.markdown("📊 **Status:** Not processed")

    with col3:
        st.markdown("#### HVAC")
        st.markdown("📊 **Status:** Not processed")

    with col4:
        st.markdown("#### Structural")
        st.markdown("📊 **Status:** Not processed")
