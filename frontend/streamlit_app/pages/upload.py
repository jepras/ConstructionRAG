import logging

import requests
import streamlit as st
from utils.shared import get_backend_url

logger = logging.getLogger(__name__)


def show_upload_page():
    """Show the upload page"""
    st.markdown("## Upload Construction Documents")
    st.markdown("Upload your construction PDFs to start building your project knowledge base.")

    # Authentication optional for email uploads
    auth_manager = st.session_state.auth_manager

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
                    # Get backend URL and access token
                    backend_url = get_backend_url()
                    access_token = st.session_state.get("access_token")

                    # Prepare headers
                    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}

                    # Prepare files data for unified multi-file upload
                    files = []
                    for file in uploaded_files:
                        files.append(("files", (file.name, file.getvalue(), "application/pdf")))

                    # Prepare form data with email
                    data = {"email": email}

                    # Debug logging to verify what's being sent
                    logger.info(f"🔍 DEBUG: Number of files to upload: {len(files)}")
                    logger.info(f"🔍 DEBUG: File names being sent: {[f[1][0] for f in files]}")
                    logger.info(f"🔍 DEBUG: Field names being sent: {[f[0] for f in files]}")
                    logger.info(f"🔍 DEBUG: Data being sent: {data}")

                    # Log upload attempt
                    logger.info(f"📤 Uploading {len(uploaded_files)} files to email: {email}")

                    # Upload all files in single request to unified endpoint
                    response = requests.post(
                        f"{backend_url}/api/email-uploads",
                        files=files,
                        data=data,
                        headers=headers,
                        timeout=60,  # Increased timeout for multiple files
                    )

                    # Debug response
                    logger.info(f"🔍 DEBUG: Response status: {response.status_code}")
                    logger.info(f"🔍 DEBUG: Response text: {response.text}")

                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"✅ Successfully uploaded {len(uploaded_files)} files")

                        # Show upload result
                        st.success(f"✅ Successfully uploaded {len(uploaded_files)} files!")
                        if result.get("index_run_id"):
                            st.info(f"Index Run ID: {result['index_run_id']}")
                            st.info("💡 Use this ID to track progress in the Progress page")
                            st.session_state["last_index_run_id"] = result["index_run_id"]
                            st.markdown("Go to the Progress page and paste the run ID above to track status.")
                        if result.get("document_count"):
                            st.info(f"Document Count: {result['document_count']}")
                        if result.get("message"):
                            st.info(f"Status: {result['message']}")
                    else:
                        logger.error(f"❌ Upload failed: {response.status_code}")
                        st.error(f"❌ Failed to upload files: {response.text}")

                except Exception as e:
                    logger.error(f"❌ Upload process failed: {str(e)}")
                    st.error(f"❌ Upload process failed: {str(e)}")
