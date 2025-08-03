import streamlit as st
import os
import sys
import logging
import requests
from datetime import datetime
from utils.auth_utils import init_auth

# Import page modules
from pages import home, progress, upload, overview, query, settings

logger = logging.getLogger(__name__)


def get_backend_url() -> str:
    """Get backend URL based on environment"""
    backend_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
    logger.info(f"🔗 Using backend URL: {backend_url}")
    return backend_url


# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Page configuration
st.set_page_config(
    page_title="ConstructionRAG",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 3rem;
    }
    .status-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
</style>
""",
    unsafe_allow_html=True,
)


def check_backend_status():
    """Check if backend is accessible"""
    try:
        import requests
        import logging

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        backend_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
        logger.info(f"🔍 Checking backend status...")
        logger.info(f"📡 Backend URL: {backend_url}")

        # Log the full health check URL
        health_url = f"{backend_url}/health"
        logger.info(f"🏥 Health check URL: {health_url}")

        # Make the request with detailed logging
        logger.info(f"📤 Sending GET request to {health_url}")
        response = requests.get(health_url, timeout=10)

        logger.info(f"📥 Response status: {response.status_code}")
        logger.info(f"📥 Response headers: {dict(response.headers)}")
        logger.info(f"📥 Response content: {response.text[:200]}...")

        if response.status_code == 200:
            logger.info(f"✅ Backend is healthy!")
            return True
        else:
            logger.error(f"❌ Backend returned status {response.status_code}")
            return False

    except requests.exceptions.Timeout as e:
        logger.error(f"⏰ Backend timeout: {str(e)}")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"🔌 Backend connection error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error checking backend: {str(e)}")
        return False


def main():
    """Main application"""

    # Initialize authentication state ONCE at the start
    init_auth()

    # Debug logging for environment variables
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Debug authentication state
    auth_manager = st.session_state.auth_manager
    logger.info(
        f"🔐 Auth initialized - Authenticated: {auth_manager.is_authenticated()}"
    )
    logger.info(f"🔐 Session state keys: {list(st.session_state.keys())}")

    logger.info("🚀 Starting ConstructionRAG Streamlit app...")
    logger.info(f"🌍 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"🔗 Backend URL: {os.getenv('BACKEND_API_URL', 'Not configured')}")
    logger.info(f"📁 Working directory: {os.getcwd()}")

    # Header
    st.markdown(
        '<h1 class="main-header">🏗️ ConstructionRAG</h1>', unsafe_allow_html=True
    )
    st.markdown(
        '<p class="sub-header">AI-powered construction document processing and Q&A system</p>',
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:
        st.title("Navigation")

        # Initialize session state for page selection
        if "current_page" not in st.session_state:
            st.session_state.current_page = "Home"

        page = st.selectbox(
            "Choose a page",
            [
                "Home",
                "Authentication",
                "Upload Documents",
                "Project Overview",
                "Progress Tracking",
                "Query Interface",
                "Settings",
            ],
            key="page_selector",
            index=[
                "Home",
                "Authentication",
                "Upload Documents",
                "Project Overview",
                "Progress Tracking",
                "Query Interface",
                "Settings",
            ].index(st.session_state.current_page),
        )

        # Update session state when page changes
        st.session_state.current_page = page

        st.markdown("---")
        st.markdown("### Status")

        # Authentication status
        from components import show_auth_status

        show_auth_status()

        st.markdown("---")

        # Backend connection status
        backend_status = check_backend_status()
        if backend_status:
            st.success("✅ Backend Connected")
        else:
            st.error("❌ Backend Disconnected")

        st.markdown("---")
        st.markdown("### Environment")
        st.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
        st.info(f"Backend URL: {os.getenv('BACKEND_API_URL', 'Not configured')}")

    # Main content based on page selection
    if page == "Home":
        home.show_home_page()
    elif page == "Authentication":
        from components import show_auth_page

        show_auth_page()
    elif page == "Upload Documents":
        upload.show_upload_page()
    elif page == "Project Overview":
        overview.show_overview_page()
    elif page == "Progress Tracking":
        progress.show_progress_page()
    elif page == "Query Interface":
        query.show_query_page()
    elif page == "Settings":
        settings.show_settings_page()


if __name__ == "__main__":
    main()
