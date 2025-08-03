import streamlit as st
import requests
import logging
from utils.shared import get_backend_url

logger = logging.getLogger(__name__)


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
