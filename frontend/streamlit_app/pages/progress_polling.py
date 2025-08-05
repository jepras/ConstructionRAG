import streamlit as st
import requests
import time
from datetime import datetime
from utils.shared import get_backend_url


def show_progress_polling_page():
    """Simple polling page for tracking indexing run progress"""
    st.markdown("## 📊 Indexing Run Progress Tracker")
    st.markdown("Enter an index run ID to track its progress in real-time.")

    # Check authentication
    if (
        not st.session_state.get("auth_manager")
        or not st.session_state.auth_manager.is_authenticated()
    ):
        st.error("🔐 Please sign in to view progress.")
        return

    # Get backend URL and access token
    backend_url = get_backend_url()
    access_token = st.session_state.get("access_token")

    if not access_token:
        st.error("❌ No access token found. Please sign in again.")
        return

    headers = {"Authorization": f"Bearer {access_token}"}

    # Input section
    st.subheader("🔍 Select Indexing Run")

    # Option 1: Manual input
    run_id_input = st.text_input(
        "Enter Index Run ID:",
        placeholder="e.g., eb49c989-af0a-4ff9-83e2-84347bb9aa9c",
        help="Enter the index run ID you want to track",
    )

    # Option 2: Get recent runs (optional)
    st.markdown("---")
    st.markdown("**Or select from recent runs:**")

    try:
        # Get recent indexing runs (last 5)
        runs_response = requests.get(
            f"{backend_url}/api/pipeline/indexing/runs", headers=headers
        )

        if runs_response.status_code == 200:
            runs = runs_response.json()

            if runs:
                # Create dropdown for recent runs
                run_options = {"-- Select from recent runs --": None}
                for run in runs:
                    # Create a readable label
                    upload_type = run.get("upload_type", "unknown")
                    status = run.get("status", "unknown")
                    started_at = run.get("started_at", "")

                    if started_at:
                        try:
                            dt = datetime.fromisoformat(
                                started_at.replace("Z", "+00:00")
                            )
                            date_str = dt.strftime("%Y-%m-%d %H:%M")
                        except:
                            date_str = started_at[:19]
                    else:
                        date_str = "No start time"

                    label = f"{upload_type.title()} - {status.title()} ({date_str}) - {run['id']}"
                    run_options[label] = run["id"]

                selected_run_label = st.selectbox(
                    "Recent runs:",
                    list(run_options.keys()),
                    index=0,
                )

                if (
                    selected_run_label
                    and selected_run_label != "-- Select from recent runs --"
                ):
                    run_id_input = run_options[selected_run_label]
            else:
                st.info("📭 No recent indexing runs found.")
        else:
            st.warning(
                f"⚠️ Could not load recent runs (status: {runs_response.status_code})"
            )
            st.info("💡 You can still enter a run ID manually above.")
    except Exception as e:
        st.warning(f"⚠️ Could not load recent runs: {str(e)}")
        st.info("💡 You can still enter a run ID manually above.")

    # Progress tracking section
    if run_id_input:
        st.markdown("---")
        st.subheader("📈 Progress Tracking")

        # Create containers for progress display
        progress_container = st.container()
        status_container = st.container()
        details_container = st.container()

        # Add a button to start/stop polling
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            start_polling = st.button("🔄 Start Polling", key="start_polling")

        with col2:
            stop_polling = st.button("⏹️ Stop Polling", key="stop_polling")

        with col3:
            st.markdown("*Polling will automatically stop when processing completes*")

        # Initialize session state for polling
        if "polling_active" not in st.session_state:
            st.session_state.polling_active = False

        if start_polling:
            st.session_state.polling_active = True

        if stop_polling:
            st.session_state.polling_active = False

        # Polling logic
        if st.session_state.polling_active:
            try:
                # Call our enhanced progress endpoint
                progress_response = requests.get(
                    f"{backend_url}/api/pipeline/indexing/runs/{run_id_input}/progress",
                    headers=headers,
                )

                if progress_response.status_code == 200:
                    data = progress_response.json()

                    # Display overall progress
                    with progress_container:
                        st.markdown("### 📊 Overall Progress")

                        # Progress bars
                        col1, col2 = st.columns(2)

                        with col1:
                            doc_progress = data["progress"]["documents_percentage"]
                            st.progress(doc_progress / 100)
                            st.write(
                                f"📄 Documents: {data['progress']['documents_processed']}/{data['progress']['total_documents']} ({doc_progress:.1f}%)"
                            )

                        with col2:
                            run_progress = data["progress"]["run_steps_percentage"]
                            st.progress(run_progress / 100)
                            st.write(
                                f"🔄 Run Steps: {data['progress']['run_steps_completed']}/{data['progress']['total_run_steps']} ({run_progress:.1f}%)"
                            )

                        # Status indicator
                        status = data["status"]
                        if status == "completed":
                            st.success("✅ Processing completed successfully!")
                            st.session_state.polling_active = False
                        elif status == "failed":
                            st.error(
                                f"❌ Processing failed: {data.get('error_message', 'Unknown error')}"
                            )
                            st.session_state.polling_active = False
                        elif status == "running":
                            st.info("🔄 Processing in progress...")
                        else:
                            st.warning(f"⚠️ Status: {status}")

                    # Display document details
                    with status_container:
                        st.markdown("### 📄 Document Status")

                        if data["document_status"]:
                            for doc_id, doc_status in data["document_status"].items():
                                with st.expander(f"📋 {doc_status['filename']}"):
                                    col1, col2, col3 = st.columns(3)

                                    with col1:
                                        st.write(
                                            f"**Status:** {doc_status['current_step']}"
                                        )

                                    with col2:
                                        st.write(
                                            f"**Progress:** {doc_status['progress_percentage']:.1f}%"
                                        )

                                    with col3:
                                        st.write(
                                            f"**Steps:** {doc_status['completed_steps']}/{doc_status['total_steps']}"
                                        )

                                    # Show step results if available
                                    if doc_status["step_results"]:
                                        st.markdown("**Step Results:**")
                                        for step_name, step_data in doc_status[
                                            "step_results"
                                        ].items():
                                            if step_data.get("status") == "completed":
                                                st.write(
                                                    f"✅ {step_name}: {step_data.get('duration_seconds', 0):.1f}s"
                                                )
                                            elif step_data.get("status") == "failed":
                                                st.write(
                                                    f"❌ {step_name}: {step_data.get('error_message', 'Unknown error')}"
                                                )
                                            else:
                                                st.write(
                                                    f"🔄 {step_name}: {step_data.get('status', 'unknown')}"
                                                )
                        else:
                            st.info("No document status available")

                    # Display run details
                    with details_container:
                        st.markdown("### 🔧 Run Details")

                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Run ID:** {data['run_id']}")
                            st.write(f"**Upload Type:** {data['upload_type']}")
                            st.write(
                                f"**Started:** {data['started_at'][:19] if data['started_at'] else 'N/A'}"
                            )

                        with col2:
                            st.write(f"**Status:** {data['status']}")
                            st.write(
                                f"**Completed:** {data['completed_at'][:19] if data['completed_at'] else 'N/A'}"
                            )
                            if data.get("error_message"):
                                st.write(f"**Error:** {data['error_message']}")

                    # Auto-refresh
                    time.sleep(3)
                    st.rerun()

                elif progress_response.status_code == 404:
                    st.error("❌ Indexing run not found. Please check the run ID.")
                    st.session_state.polling_active = False
                else:
                    st.error(
                        f"❌ Error loading progress: {progress_response.status_code}"
                    )
                    st.error(f"Response: {progress_response.text}")
                    st.session_state.polling_active = False

            except Exception as e:
                st.error(f"❌ Error during polling: {str(e)}")
                st.session_state.polling_active = False
        else:
            st.info("Click 'Start Polling' to begin tracking progress")

    # Instructions
    st.markdown("---")
    st.markdown("### 📖 Instructions")
    st.markdown(
        """
    1. **Enter a Run ID**: Paste the index run ID you want to track
    2. **Or Select Recent**: Choose from your recent indexing runs
    3. **Start Polling**: Click the button to begin real-time tracking
    4. **Monitor Progress**: Watch the progress bars and document status
    5. **Auto-Stop**: Polling automatically stops when processing completes
    
    **Run IDs** are provided when you upload documents or can be found in the main progress page.
    """
    )


# Main function to run the page
if __name__ == "__main__":
    show_progress_polling_page()
