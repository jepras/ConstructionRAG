import streamlit as st
import os
import sys
from datetime import datetime

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


def main():
    """Main application"""

    # Debug logging for environment variables
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

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
                "Query Interface",
                "Settings",
            ],
            key="page_selector",
            index=[
                "Home",
                "Authentication",
                "Upload Documents",
                "Project Overview",
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
        show_home_page()
    elif page == "Authentication":
        from components import show_auth_page

        show_auth_page()
    elif page == "Upload Documents":
        show_upload_page()
    elif page == "Project Overview":
        show_overview_page()
    elif page == "Query Interface":
        show_query_page()
    elif page == "Settings":
        show_settings_page()


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
        logger.error(f"⏰ Timeout error: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"🔌 Connection error: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 Request error: {e}")
        return False
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        return False


def show_home_page():
    """Show the home page"""
    st.markdown("## Welcome to ConstructionRAG")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### What is ConstructionRAG?")
        st.markdown(
            """
        ConstructionRAG is an AI-powered system that:
        
        - **Processes construction documents** (PDFs, plans, specifications)
        - **Generates project overviews** automatically
        - **Answers complex questions** about your construction projects
        - **Organizes information** by building systems and project phases
        
        Think of it as a **DeepWiki for Construction Sites** - just like DeepWiki analyzes code repositories, 
        we analyze construction documentation to create comprehensive project knowledge bases.
        """
        )

    with col2:
        st.markdown("### Quick Start")
        st.markdown(
            """
        1. **Upload Documents** - Start by uploading your construction PDFs
        2. **Generate Overview** - Let AI create a project summary
        3. **Ask Questions** - Query your project knowledge base
        4. **Explore Systems** - Navigate by building systems (electrical, plumbing, etc.)
        """
        )

        if st.button("🚀 Get Started", type="primary"):
            st.session_state.current_page = "Upload Documents"
            st.rerun()


def show_upload_page():
    """Show the upload page"""
    st.markdown("## Upload Construction Documents")
    st.markdown(
        "Upload your construction PDFs to start building your project knowledge base."
    )

    # File uploader
    uploaded_files = st.file_uploader(
        "Choose PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        help="Select one or more PDF files to upload",
    )

    if uploaded_files:
        st.markdown(f"**Selected files:** {len(uploaded_files)}")

        # Show file details
        for file in uploaded_files:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"📄 {file.name}")
            with col2:
                st.write(f"{file.size / 1024 / 1024:.1f} MB")
            with col3:
                st.write("Ready to upload")

        # Upload button
        if st.button("📤 Upload and Process", type="primary"):
            with st.spinner("Uploading and processing documents..."):
                # TODO: Implement actual upload logic
                st.success("Documents uploaded successfully!")
                st.info(
                    "Processing will continue in the background. Check the Project Overview page for updates."
                )


def show_overview_page():
    """Show the project overview page"""
    st.markdown("## Project Overview")
    st.markdown(
        "View your construction project summary and navigate by building systems."
    )

    # Placeholder for project overview
    st.info(
        "No projects processed yet. Upload documents to generate project overviews."
    )

    # Example structure (will be populated with real data)
    st.markdown("### Building Systems")
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


def show_query_page():
    """Show the query interface page"""
    st.markdown("## Query Your Project")
    st.markdown(
        "Ask questions about your construction project and get AI-powered answers."
    )

    # Test Query API button
    st.markdown("### Test Backend Query API")
    if st.button("🧪 Test Query API", type="secondary"):
        import requests

        try:
            response = requests.post(
                "https://constructionrag-production.up.railway.app/api/query",
                json={"query": "What is this construction project about?"},
                timeout=10,
            )
            if response.status_code == 200:
                st.success("✅ Query API working!")
                st.json(response.json())
            else:
                st.error(f"❌ Query API error: {response.status_code}")
                st.text(f"Response: {response.text}")
        except Exception as e:
            st.error(f"❌ Query API failed: {str(e)}")

    st.markdown("---")

    # Query input
    query = st.text_area(
        "Ask a question about your construction project:",
        placeholder="e.g., What are the electrical requirements for the main building?",
        height=100,
    )

    if st.button("🔍 Search", type="primary"):
        if query:
            with st.spinner("Searching for answers..."):
                # TODO: Implement actual query logic
                st.info(
                    "Query functionality will be implemented once documents are processed."
                )
        else:
            st.warning("Please enter a question.")


def show_settings_page():
    """Show the settings page"""
    st.markdown("## Settings")
    st.markdown("Configure your ConstructionRAG application.")

    # Configuration options
    st.markdown("### Pipeline Configuration")

    col1, col2 = st.columns(2)

    with col1:
        chunk_size = st.slider("Chunk Size", 500, 2000, 1000, 100)
        chunk_overlap = st.slider("Chunk Overlap", 0, 500, 200, 50)

    with col2:
        embedding_model = st.selectbox(
            "Embedding Model",
            ["voyage-large-2", "text-embedding-ada-002", "all-MiniLM-L6-v2"],
        )
        similarity_threshold = st.slider("Similarity Threshold", 0.0, 1.0, 0.7, 0.05)

    if st.button("💾 Save Settings", type="primary"):
        st.success("Settings saved successfully!")


if __name__ == "__main__":
    main()
