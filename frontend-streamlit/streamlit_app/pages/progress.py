import logging
from datetime import datetime

import requests
import streamlit as st
from utils.shared import get_backend_url

from .progress_helpers import (
    display_document_status,
    display_embedding_results,
    display_enhanced_chunking_results,
    display_step_results,
    display_timing_summary,
)

logger = logging.getLogger(__name__)


def show_progress_page():
    """Show the progress tracking page - SIMPLIFIED VERSION"""
    st.markdown("## 📊 Indexing Run Progress")
    st.markdown("Track the progress of your document processing runs.")

    # Authentication optional in v2
    auth_manager = st.session_state.auth_manager
    user_info = auth_manager.get_current_user()
    if user_info and user_info.get("user"):
        user = user_info["user"]
        st.info(f"Signed in as: {user.get('email', 'N/A')}")

    try:
        # Get backend URL and access token
        backend_url = get_backend_url()
        access_token = st.session_state.get("access_token")

        headers = {"Authorization": f"Bearer {access_token}"} if access_token else None

        # Get all indexing runs (only if authenticated)
        runs = []
        if headers:
            runs_response = requests.get(f"{backend_url}/api/indexing-runs", headers=headers)
            if runs_response.status_code != 200:
                st.error(f"❌ Failed to load indexing runs: {runs_response.status_code}")
                st.error(f"Response: {runs_response.text}")
                return
            runs = runs_response.json()

        if not runs and not st.session_state.get("last_index_run_id"):
            st.info("📭 No indexing runs found. You can still paste a run ID from the Upload page.")

        # Create dropdown for run selection
        st.subheader("Select Indexing Run")

        # Format run options for dropdown
        run_options = {"-- Select an indexing run --": None}
        for run in runs:
            # Create a readable label
            upload_type = run.get("upload_type", "unknown")
            status = run.get("status", "unknown")
            started_at = run.get("started_at", "")
            if started_at:
                try:
                    # Parse and format the date
                    dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = started_at[:19]  # Just take first 19 chars if parsing fails
            else:
                date_str = "No start time"

            label = f"{upload_type.title()} - {status.title()} ({date_str})"
            run_options[label] = run["id"]

        selected_run_label = st.selectbox(
            "Choose an indexing run:",
            list(run_options.keys()) if runs else ["-- Enter a run ID below --"],
            index=0,
            help="Select an indexing run to view its progress",
        )

        run_id = None
        if runs and selected_run_label and selected_run_label != "-- Select an indexing run --":
            run_id = run_options[selected_run_label]
        else:
            run_id = st.text_input("Or paste an Index Run ID", value=st.session_state.get("last_index_run_id", ""))

            # Get detailed status for selected run
            status_response = requests.get(f"{backend_url}/api/indexing-runs/{run_id}", headers=headers)

            if status_response.status_code == 200:
                run_data = status_response.json()

                # Display run information
                st.subheader("📋 Run Information")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(
                        f"<small><strong>Status:</strong> {run_data['status'].title()}</small>",
                        unsafe_allow_html=True,
                    )
                with col2:
                    if run_data.get("started_at"):
                        st.markdown(
                            f"<small><strong>Started:</strong> {run_data['started_at'][:19]}</small>",
                            unsafe_allow_html=True,
                        )
                with col3:
                    if run_data.get("completed_at"):
                        st.markdown(
                            f"<small><strong>Completed:</strong> {run_data['completed_at'][:19]}</small>",
                            unsafe_allow_html=True,
                        )

                # Show error if any
                if run_data.get("error_message"):
                    st.error(f"❌ Error: {run_data['error_message']}")

                # Get documents for this indexing run (unified approach)
                # Use flat documents listing for email runs when anonymous later; keep existing for now
                # For v2, anonymous flow can list docs by index_run_id if it's an email upload
                if headers:
                    documents_response = requests.get(
                        f"{backend_url}/api/documents?index_run_id={run_id}", headers=headers
                    )
                else:
                    documents_response = requests.get(f"{backend_url}/api/documents?index_run_id={run_id}")

                if documents_response.status_code == 200:
                    response_data = documents_response.json()

                    # Handle v2 API response structure: {"documents": [...], "total_count": X, "has_more": false}
                    if isinstance(response_data, dict) and "documents" in response_data:
                        documents = response_data["documents"]
                    else:
                        # Fallback: assume direct array response (v1 style)
                        documents = response_data if isinstance(response_data, list) else []

                    if documents:
                        # Display document progress (unified for all upload types)
                        st.subheader("📄 Document Progress Overview")
                        display_document_status(documents)
                        display_timing_summary(documents)

                        # Display step-by-step results (unified for all upload types)
                        st.subheader("🔧 Pipeline Steps")

                        # Define step configurations
                        steps_config = [
                            ("PartitionStep", "Step 1: Partition", "📄", "Summary"),
                            (
                                "MetadataStep",
                                "Step 2: Metadata",
                                "🏷️",
                                "Page Sections Detected",
                            ),
                            (
                                "EnrichmentStep",
                                "Step 3: Enrichment",
                                "🔍",
                                "Image Captions",
                            ),
                            (
                                "ChunkingStep",
                                "Step 4: Chunking",
                                "✂️",
                                "Chunking Statistics",
                            ),
                        ]

                        # Display each step
                        for (
                            step_name,
                            step_display,
                            step_icon,
                            step_description,
                        ) in steps_config:
                            display_step_results(
                                documents,
                                step_name,
                                step_display,
                                step_icon,
                                step_description,
                            )

                        # Display enhanced chunking results (from documents)
                        display_enhanced_chunking_results(documents, "ChunkingStep")

                        # Display embedding results (from indexing run)
                        display_embedding_results(run_data)
                    else:
                        st.info("No documents found for this indexing run")
                elif documents_response.status_code == 401:
                    st.warning("⚠️ Access denied. This run may require authentication or may not be an email upload.")
                    st.info("💡 Email uploads can be viewed anonymously. Project uploads require signing in.")
                else:
                    st.error(f"Failed to load documents: {documents_response.status_code}")
                    st.error(f"Response: {documents_response.text}")

            elif status_response.status_code == 401:
                st.error("❌ Access denied. This run may require authentication or may not be an email upload.")
                st.info("💡 Email uploads can be viewed anonymously. Project uploads require signing in.")
            else:
                st.error(f"❌ Failed to load run status: {status_response.status_code}")
                st.error(f"Response: {status_response.text}")

    except Exception as e:
        logger.error(f"❌ Error in progress page: {str(e)}")
        st.error(f"❌ Error in progress page: {str(e)}")
