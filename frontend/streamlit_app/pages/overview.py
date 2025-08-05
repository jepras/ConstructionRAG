import streamlit as st
import requests
import logging
from datetime import datetime
from utils.shared import get_backend_url

logger = logging.getLogger(__name__)


def show_overview_page():
    """Show the project overview page"""
    st.markdown("## Project Overview")

    # Check authentication
    if (
        not st.session_state.get("auth_manager")
        or not st.session_state.auth_manager.is_authenticated()
    ):
        st.error("🔐 Please sign in to view overview.")
        return

    # Get backend URL and access token
    backend_url = get_backend_url()
    access_token = st.session_state.get("access_token")

    if not access_token:
        st.error("❌ No access token found. Please sign in again.")
        return

    headers = {"Authorization": f"Bearer {access_token}"}

    # Index run selection section
    st.subheader("🔍 Select Indexing Run")

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

    # Show selected run info (for now, just display the ID)
    if run_id_input:
        st.info(f"Selected Run ID: {run_id_input}")

        # INSERT_YOUR_CODE
        # Tab section with Overview, Query, Wiki, Documents
        tab_overview, tab_query, tab_wiki, tab_documents = st.tabs(
            ["Overview", "Query", "Wiki", "Documents"]
        )

        with tab_overview:
            st.markdown("### 📄 Overview")
            st.info(
                "This section will provide a summary and key statistics for the selected indexing run."
            )
            # You can add more overview content here, e.g., summary stats, progress, etc.

        with tab_query:
            st.markdown("### 🔍 Query")
            st.info(
                "This section will allow you to run queries against the indexed data for this run."
            )
            # You can add query UI/components here.

        with tab_wiki:
            st.markdown("### 📚 Wiki")
            st.info(
                "This section will show extracted wiki/knowledge base content from the documents."
            )
            # You can add wiki-related content here.

        with tab_documents:
            # INSERT_YOUR_CODE

            # Example: For each document, show an expander with sub-tabs for Partition, Enrich, Chunk, Embed
            # (Replace with actual document list if available)
            document_names = [
                "Document 1",
                "Document 2",
            ]  # Placeholder, replace with actual document names if available

            for doc_name in document_names:
                with st.expander(doc_name):
                    subtab_partition, subtab_enrich, subtab_chunk, subtab_embed = (
                        st.tabs(["Partition", "Enrich", "Chunk", "Embed"])
                    )

                    with subtab_partition:
                        st.markdown(f"#### 🧩 Partition for {doc_name}")
                        st.info("Partitioning details and results will appear here.")
                    # INSERT_YOUR_CODE
                    # Placeholder for summary_stats JSON display
                    st.markdown("##### Summary Stats (JSON Preview)")
                    # Replace the following with the actual summary_stats dict when available
                    example_summary_stats = {
                        "num_pages": 12,
                        "num_chunks": 87,
                        "section_headers_distribution": {
                            "Introduction": 5,
                            "Methods": 10,
                            "Results": 8,
                        },
                        "shortest_chunks": [
                            {
                                "page": 1,
                                "size": 120,
                                "type": "paragraph",
                                "content": "Short chunk example...",
                            }
                        ],
                        "longest_chunks": [
                            {
                                "page": 2,
                                "size": 1200,
                                "type": "section",
                                "content": "Long chunk example...",
                            }
                        ],
                        "chunk_type_distribution": {
                            "paragraph": 60,
                            "section": 20,
                            "list": 7,
                        },
                        # ... more fields as needed
                    }
                    st.json(example_summary_stats)

                    with subtab_enrich:
                        st.markdown(f"#### ✨ Enrich for {doc_name}")
                        st.info("Enrichment details and results will appear here.")

                    with subtab_chunk:
                        st.markdown(f"#### 📦 Chunk for {doc_name}")
                        st.info("Chunking details and results will appear here.")

                    with subtab_embed:
                        st.markdown(f"#### 🧠 Embed for {doc_name}")
                        st.info("Embedding details and results will appear here.")
            # You can add document listing/details here.
