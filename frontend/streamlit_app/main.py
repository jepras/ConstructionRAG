import streamlit as st
import os
import sys
import logging
import requests
from datetime import datetime
from utils.auth_utils import init_auth

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

    # Check authentication first
    auth_manager = st.session_state.auth_manager

    if not auth_manager.is_authenticated():
        st.error("🔐 Please sign in to upload documents.")
        st.info("Use the sidebar to navigate to the Authentication page.")
        return

    # Show user info
    user_info = auth_manager.get_current_user()
    if user_info and user_info.get("user"):
        user = user_info["user"]
        st.success(f"✅ Signed in as: {user.get('email', 'N/A')}")

    # Email input field
    email = st.text_input(
        "Email Address",
        value=user.get("email", "") if user_info and user_info.get("user") else "",
        help="Enter the email address for processing notifications",
        placeholder="your.email@example.com",
    )

    if not email:
        st.warning("⚠️ Please enter an email address to continue.")
        return

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
                try:
                    # Check authentication
                    if not st.session_state.get("authenticated", False):
                        st.error("🔐 Please sign in to upload documents.")
                        return

                    # Get backend URL and access token
                    backend_url = get_backend_url()
                    access_token = st.session_state.get("access_token")

                    if not access_token:
                        st.error("❌ No access token found. Please sign in again.")
                        return

                    # Prepare headers
                    headers = {"Authorization": f"Bearer {access_token}"}

                    # Upload each file
                    uploaded_count = 0
                    for file in uploaded_files:
                        try:
                            # Prepare file data
                            files = {
                                "file": (file.name, file.getvalue(), "application/pdf")
                            }

                            # Prepare form data with email
                            data = {"email": email}

                            # Log upload attempt
                            logger.info(
                                f"📤 Uploading file: {file.name} ({file.size} bytes) to email: {email}"
                            )

                            # Upload to email-uploads endpoint
                            response = requests.post(
                                f"{backend_url}/api/email-uploads",
                                files=files,
                                data=data,
                                headers=headers,
                                timeout=30,
                            )

                            if response.status_code == 200:
                                result = response.json()
                                logger.info(
                                    f"✅ File uploaded successfully: {file.name}"
                                )
                                uploaded_count += 1

                                # Show upload result
                                st.success(f"✅ {file.name} uploaded successfully!")
                                if result.get("upload_id"):
                                    st.info(f"Upload ID: {result['upload_id']}")
                            else:
                                logger.error(
                                    f"❌ Upload failed for {file.name}: {response.status_code}"
                                )
                                st.error(
                                    f"❌ Failed to upload {file.name}: {response.text}"
                                )

                        except Exception as e:
                            logger.error(f"❌ Error uploading {file.name}: {str(e)}")
                            st.error(f"❌ Error uploading {file.name}: {str(e)}")

                    # Show final results
                    if uploaded_count > 0:
                        st.success(
                            f"🎉 Successfully uploaded {uploaded_count} out of {len(uploaded_files)} files!"
                        )
                        st.info(
                            "Processing will continue in the background. Check the Project Overview page for updates."
                        )
                    else:
                        st.error("❌ No files were uploaded successfully.")

                except Exception as e:
                    logger.error(f"❌ Upload process failed: {str(e)}")
                    st.error(f"❌ Upload process failed: {str(e)}")


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


def show_query_page():
    """Show the query interface page"""
    st.markdown("## Query Your Project")
    st.markdown(
        "Ask questions about your construction project and get AI-powered answers."
    )

    # Check authentication first
    from components import require_auth_decorator

    auth_manager = st.session_state.auth_manager

    if not auth_manager.is_authenticated():
        st.error("🔐 Please sign in to access the query interface.")
        st.info("Use the sidebar to navigate to the Authentication page.")
        return

    # Show user info
    user_info = auth_manager.get_current_user()
    if user_info and user_info.get("user"):
        user = user_info["user"]
        st.success(f"✅ Signed in as: {user.get('email', 'N/A')}")

    # Load available indexing runs
    try:
        backend_url = get_backend_url()
        access_token = st.session_state.get("access_token")

        if not access_token:
            st.error("❌ No access token found. Please sign in again.")
            return

        headers = {"Authorization": f"Bearer {access_token}"}

        # Get all indexing runs
        response = requests.get(
            f"{backend_url}/api/pipeline/indexing/runs", headers=headers, timeout=10
        )

        if response.status_code == 200:
            indexing_runs = response.json()

            # Show all runs for debugging (not just completed ones)
            all_runs = indexing_runs

            if all_runs:
                st.markdown("### 📄 Available Processed Documents")

                # Create dropdown for indexing run selection
                run_options = []
                for run in all_runs:
                    upload_type = run.get("upload_type", "unknown")
                    upload_id = run.get("upload_id", "N/A")
                    started_at = run.get("started_at", "Unknown")

                    # Format the display name
                    if upload_type == "email":
                        display_name = (
                            f"Email Upload ({upload_id[:8]}...) - {started_at[:10]}"
                        )
                    else:
                        display_name = f"Project Document - {started_at[:10]}"

                    run_options.append((display_name, run["id"]))

                if run_options:
                    selected_run_display, selected_run_id = st.selectbox(
                        "Choose a processed document to query:",
                        options=run_options,
                        format_func=lambda x: x[0],
                        help="Select a document that has been processed and is ready for querying",
                    )

                    st.success(f"✅ Selected: {selected_run_display}")

                    # Query input
                    st.markdown("---")
                    query = st.text_area(
                        "Ask a question about this document:",
                        placeholder="e.g., What are the electrical requirements for the main building?",
                        height=100,
                    )

                    if st.button("🔍 Search", type="primary"):
                        if query:
                            with st.spinner("Searching for answers..."):
                                try:
                                    # Make query request with indexing run ID
                                    query_response = requests.post(
                                        f"{backend_url}/api/query/",
                                        json={
                                            "query": query,
                                            "indexing_run_id": selected_run_id,
                                        },
                                        headers=headers,
                                        timeout=30,
                                    )

                                    if query_response.status_code == 200:
                                        result = query_response.json()
                                        st.success("✅ Answer found!")

                                        # Display the response
                                        st.markdown("### Answer:")
                                        st.write(
                                            result.get(
                                                "response", "No response received"
                                            )
                                        )

                                        # Display metadata if available
                                        if result.get("search_results"):
                                            st.markdown("### Sources:")
                                            for i, source in enumerate(
                                                result["search_results"][:3], 1
                                            ):
                                                st.markdown(
                                                    f"**Source {i}:** {source.get('content', '')[:200]}..."
                                                )

                                        if result.get("performance_metrics"):
                                            st.markdown("### Performance:")
                                            st.json(result["performance_metrics"])

                                    else:
                                        st.error(
                                            f"❌ Query failed: {query_response.status_code}"
                                        )
                                        st.text(f"Response: {query_response.text}")

                                except Exception as e:
                                    st.error(f"❌ Query failed: {str(e)}")
                        else:
                            st.warning("Please enter a question.")
                else:
                    st.info("No completed indexing runs found.")
            else:
                st.info(
                    "📄 No processed documents found. Upload and process documents first."
                )

        else:
            st.error(f"❌ Failed to load indexing runs: {response.status_code}")

    except Exception as e:
        logger.error(f"❌ Error loading indexing runs: {str(e)}")
        st.error(f"❌ Error loading indexing runs: {str(e)}")

    # Test buttons for debugging
    st.markdown("---")
    st.markdown("### 🧪 Debug: Test APIs")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Test Indexing Runs API", type="secondary"):
            try:
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }

                response = requests.get(
                    f"{backend_url}/api/pipeline/indexing/runs",
                    headers=headers,
                    timeout=10,
                )

                if response.status_code == 200:
                    runs = response.json()
                    st.success(f"✅ Indexing Runs API working! Found {len(runs)} runs")
                    st.json(runs[:2])  # Show first 2 runs
                else:
                    st.error(f"❌ Indexing Runs API error: {response.status_code}")
                    st.text(f"Response: {response.text}")
            except Exception as e:
                st.error(f"❌ Indexing Runs API failed: {str(e)}")

    with col2:
        if st.button("Test Query API", type="secondary"):
            try:
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }

                response = requests.post(
                    f"{backend_url}/api/query/",
                    json={"query": "What is this construction project about?"},
                    headers=headers,
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
