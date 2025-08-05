import streamlit as st
import requests
import logging
from datetime import datetime
from utils.shared import get_backend_url

logger = logging.getLogger(__name__)


def _get_auth_headers():
    """Get authentication headers for API requests"""
    access_token = st.session_state.get("access_token")
    if not access_token:
        return None
    return {"Authorization": f"Bearer {access_token}"}


def _check_authentication():
    """Check if user is authenticated"""
    if (
        not st.session_state.get("auth_manager")
        or not st.session_state.auth_manager.is_authenticated()
    ):
        st.error("🔐 Please sign in to view overview.")
        return False
    return True


def _format_run_label(run):
    """Format a run into a readable label for the dropdown"""
    upload_type = run.get("upload_type", "unknown")
    status = run.get("status", "unknown")
    started_at = run.get("started_at", "")

    if started_at:
        try:
            dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except:
            date_str = started_at[:19]
    else:
        date_str = "No start time"

    return f"{upload_type.title()} - {status.title()} ({date_str}) - {run['id']}"


def render_run_selection(backend_url):
    """Render the run selection dropdown and return the selected run ID"""
    headers = _get_auth_headers()
    if not headers:
        st.error("❌ No access token found. Please sign in again.")
        return None

    try:
        # Get recent indexing runs (last 5)
        logger.info("🔍 Fetching recent indexing runs...")
        runs_response = requests.get(
            f"{backend_url}/api/pipeline/indexing/runs", headers=headers
        )

        if runs_response.status_code == 200:
            runs = runs_response.json()
            logger.info(f"📊 Found {len(runs)} indexing runs")

            if runs:
                # Create dropdown for recent runs
                run_options = {"-- Select from recent runs --": None}
                for run in runs:
                    label = _format_run_label(run)
                    run_options[label] = run["id"]

                # Auto-select the latest run (first in the list since they're sorted by latest first)
                selected_run_label = st.selectbox(
                    "Recent runs:",
                    list(run_options.keys()),
                    index=1,  # Start with the first actual run (index 1) instead of placeholder (index 0)
                )

                if (
                    selected_run_label
                    and selected_run_label != "-- Select from recent runs --"
                ):
                    run_id_input = run_options[selected_run_label]
                    logger.info(f"🎯 Selected run ID: {run_id_input}")
                else:
                    # If somehow the placeholder is selected, default to the first run
                    first_run_label = list(run_options.keys())[
                        1
                    ]  # Skip the placeholder
                    run_id_input = run_options[first_run_label]
                    logger.info(f"🎯 Auto-selected latest run ID: {run_id_input}")

                return run_id_input
            else:
                st.info("📭 No recent indexing runs found.")
                return None
        else:
            st.warning(
                f"⚠️ Could not load recent runs (status: {runs_response.status_code})"
            )
            st.info("💡 You can still enter a run ID manually above.")
            return None
    except Exception as e:
        st.warning(f"⚠️ Could not load recent runs: {str(e)}")
        st.info("💡 You can still enter a run ID manually above.")
        return None


def render_progress_metrics(progress_info):
    """Render the progress metrics in a two-column layout"""
    st.markdown("##### 📈 Progress Summary")
    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Documents Processed",
            f"{progress_info.get('documents_processed', 0)}/{progress_info.get('total_documents', 0)}",
        )
        st.metric(
            "Document Progress",
            f"{progress_info.get('documents_percentage', 0):.1f}%",
        )

    with col2:
        st.metric(
            "Run Steps Completed",
            f"{progress_info.get('run_steps_completed', 0)}/{progress_info.get('total_run_steps', 0)}",
        )
        st.metric(
            "Run Steps Progress",
            f"{progress_info.get('run_steps_percentage', 0):.1f}%",
        )


def render_overview_tab(run_id_input, backend_url):
    """Render the overview tab with progress data and run status"""

    headers = _get_auth_headers()
    if not headers:
        return

    try:
        # Get indexing run progress and step results
        logger.info(f"📊 Fetching progress data for run ID: {run_id_input}")
        progress_response = requests.get(
            f"{backend_url}/api/pipeline/indexing/runs/{run_id_input}/progress",
            headers=headers,
        )

        logger.info(f"📡 Progress API response status: {progress_response.status_code}")

        if progress_response.status_code == 200:
            progress_data = progress_response.json()
            logger.info(f"📊 Progress data loaded: {len(progress_data)} fields")

            # Display progress information
            progress_info = progress_data.get("progress", {})
            if progress_info:
                render_progress_metrics(progress_info)

            # Display run status
            st.markdown("##### 📋 Run Status")
            status_info = {
                "Status": progress_data.get("status", "unknown"),
                "Upload Type": progress_data.get("upload_type", "unknown"),
                "Started At": progress_data.get("started_at", "N/A"),
                "Completed At": progress_data.get("completed_at", "N/A"),
            }
            if progress_data.get("error_message"):
                status_info["Error Message"] = progress_data.get("error_message")

            st.json(status_info)

            # Display step results if available
            step_results = progress_data.get("step_results", {})
            if step_results:
                st.markdown("##### 🔧 Step Results")
                st.json(step_results)

        elif progress_response.status_code == 404:
            st.info("No progress data found for this indexing run.")
            logger.warning(f"⚠️ No progress data found for run ID: {run_id_input}")
        else:
            st.error(f"Failed to load progress data: {progress_response.status_code}")
            st.error(f"Response: {progress_response.text}")
            logger.error(
                f"❌ Progress API failed: {progress_response.status_code} - {progress_response.text}"
            )

    except Exception as e:
        st.error(f"Error loading progress data: {str(e)}")
        logger.error(f"❌ Error in overview tab: {e}")


def render_document_step_tab(step_results, step_name, step_key, doc_name):
    """Render a single document step tab with summary stats and full data"""
    step_results_data = step_results.get(step_key, {})

    if step_results_data:
        logger.info(
            f"📋 {step_name} results for {doc_name}: {len(step_results_data)} fields"
        )

        # Display summary stats if available
        summary_stats = step_results_data.get("summary_stats", {})

        if summary_stats:
            st.markdown("##### Summary Stats")
            st.json(summary_stats)
        else:
            st.info(f"No summary stats available for {step_name.lower()} step")

        # Full data in expander
        with st.expander(f"📋 Full {step_name} Data"):
            st.json(step_results_data)
    else:
        st.info(f"{step_name} details and results will appear here.")


def render_document_details(document, backend_url):
    """Render the details for a single document with all its step tabs"""
    doc_id = document.get("id")
    doc_name = document.get("filename", f"Document {doc_id}")
    step_results = document.get("step_results", {})

    logger.info(f"📄 Document: {doc_name} (ID: {doc_id})")
    logger.info(f"📄 Document step_results keys: {list(step_results.keys())}")

    with st.expander(f"📄 {doc_name}"):
        (
            subtab_partition,
            subtab_metadata,
            subtab_enrich,
            subtab_chunk,
        ) = st.tabs(["Partition", "Metadata", "Enrich", "Chunk"])

        with subtab_partition:
            render_document_step_tab(
                step_results, "Partition", "PartitionStep", doc_name
            )

        with subtab_metadata:
            render_document_step_tab(step_results, "Metadata", "MetadataStep", doc_name)

        with subtab_enrich:
            render_document_step_tab(
                step_results, "Enrichment", "EnrichmentStep", doc_name
            )

        with subtab_chunk:
            render_document_step_tab(step_results, "Chunking", "ChunkingStep", doc_name)


def render_documents_tab(run_id_input, backend_url):
    """Render the documents tab with all documents and their details"""
    st.markdown("### 📄 Documents")

    headers = _get_auth_headers()
    if not headers:
        return

    try:
        # Get documents for this indexing run
        logger.info(f"📄 Fetching documents for run ID: {run_id_input}")
        documents_response = requests.get(
            f"{backend_url}/api/documents/by-index-run/{run_id_input}",
            headers=headers,
        )

        logger.info(
            f"📡 Documents API response status: {documents_response.status_code}"
        )

        if documents_response.status_code == 200:
            documents = documents_response.json()
            logger.info(f"📄 Found {len(documents)} documents")

            if documents:
                for document in documents:
                    render_document_details(document, backend_url)
            else:
                st.info("No documents found for this indexing run.")
                logger.warning(f"⚠️ No documents found for run ID: {run_id_input}")
        else:
            st.error(f"Failed to load documents: {documents_response.status_code}")
            st.error(f"Response: {documents_response.text}")
            logger.error(
                f"❌ Documents API failed: {documents_response.status_code} - {documents_response.text}"
            )

    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")
        logger.error(f"❌ Error in documents tab: {e}")


def render_config_tab(run_id_input, backend_url):
    """Render the config tab with pipeline configuration and run status"""
    st.markdown("### ⚙️ Pipeline Configuration")

    headers = _get_auth_headers()
    if not headers:
        return

    try:
        # Get pipeline configuration for this indexing run
        logger.info(f"⚙️ Fetching pipeline status for run ID: {run_id_input}")
        status_response = requests.get(
            f"{backend_url}/api/pipeline/indexing/runs/{run_id_input}/status",
            headers=headers,
        )

        logger.info(f"📡 Status API response status: {status_response.status_code}")

        if status_response.status_code == 200:
            status_data = status_response.json()
            logger.info(f"⚙️ Status data loaded: {len(status_data)} fields")

            # Display pipeline configuration if available
            pipeline_config = status_data.get("pipeline_config", {})
            if pipeline_config:
                st.markdown("##### Pipeline Configuration")
                st.json(pipeline_config)
            else:
                st.info("No pipeline configuration found in status data.")

            # Display other status information
            st.markdown("##### 📋 Run Status Details")
            status_info = {
                "ID": status_data.get("id", "N/A"),
                "Upload Type": status_data.get("upload_type", "N/A"),
                "Project ID": status_data.get("project_id", "N/A"),
                "Status": status_data.get("status", "N/A"),
                "Started At": status_data.get("started_at", "N/A"),
                "Completed At": status_data.get("completed_at", "N/A"),
            }
            if status_data.get("error_message"):
                status_info["Error Message"] = status_data.get("error_message")

            st.json(status_info)

        elif status_response.status_code == 404:
            st.info("No status data found for this indexing run.")
            logger.warning(f"⚠️ No status data found for run ID: {run_id_input}")
        else:
            st.error(f"Failed to load status data: {status_response.status_code}")
            st.error(f"Response: {status_response.text}")
            logger.error(
                f"❌ Status API failed: {status_response.status_code} - {status_response.text}"
            )

    except Exception as e:
        st.error(f"Error loading status data: {str(e)}")
        logger.error(f"❌ Error in config tab: {e}")


def render_query_tab(run_id_input, backend_url):
    """Render the query tab with minimal query interface"""
    st.markdown("### 🔍 Query")

    headers = _get_auth_headers()
    if not headers:
        return

    # Query input
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
                            "indexing_run_id": run_id_input,
                        },
                        headers=headers,
                        timeout=30,
                    )

                    if query_response.status_code == 200:
                        result = query_response.json()
                        st.success("✅ Answer found!")

                        # Display the response
                        st.markdown("### Answer:")
                        st.write(result.get("response", "No response received"))

                        # Display sources if available
                        if result.get("search_results"):
                            st.markdown("### Sources:")
                            for i, source in enumerate(result["search_results"], 1):
                                content = source.get("content", "")
                                page_number = source.get("page_number", "N/A")
                                source_filename = source.get(
                                    "source_filename", "Unknown"
                                )
                                similarity_score = source.get("similarity_score", 0.0)

                                # Create a snippet (first line + next 50 chars)
                                lines = content.split("\n")
                                first_line = lines[0] if lines else ""
                                snippet = first_line
                                if len(content) > len(first_line) + 50:
                                    snippet += (
                                        " "
                                        + content[
                                            len(first_line) : len(first_line) + 50
                                        ].strip()
                                        + "..."
                                    )

                                # Format similarity score as percentage
                                similarity_percent = f"{similarity_score * 100:.1f}%"

                                # Create expandable source
                                with st.expander(
                                    f"📄 Page {page_number} | {similarity_percent} | {snippet}",
                                    expanded=False,
                                ):
                                    st.markdown("**Full Content:**")
                                    st.text_area(
                                        f"Source {i} Content",
                                        value=content,
                                        height=200,
                                        key=f"source_content_{i}",
                                        disabled=True,
                                    )

                    else:
                        st.error(f"❌ Query failed: {query_response.status_code}")
                        st.text(f"Response: {query_response.text}")

                except Exception as e:
                    st.error(f"❌ Query failed: {str(e)}")
        else:
            st.warning("Please enter a question.")


def show_overview_page():
    """Show the project overview page - main orchestrator function"""
    st.markdown("## Project Overview")

    # Check authentication
    if not _check_authentication():
        return

    # Get backend URL
    backend_url = get_backend_url()

    # Render run selection and get selected run ID
    run_id_input = render_run_selection(backend_url)

    # Show selected run info and tabs
    if run_id_input:
        # Tab section with Overview, Query, Wiki, Documents, Config
        tab_overview, tab_query, tab_wiki, tab_documents, tab_config = st.tabs(
            ["Overview", "Query", "Wiki", "Documents", "Config"]
        )

        with tab_overview:
            render_overview_tab(run_id_input, backend_url)

        with tab_query:
            render_query_tab(run_id_input, backend_url)

        with tab_wiki:
            st.markdown("### 📚 Wiki")
            st.info(
                "This section will show extracted wiki/knowledge base content from the documents."
            )
            # You can add wiki-related content here.

        with tab_documents:
            render_documents_tab(run_id_input, backend_url)

        with tab_config:
            render_config_tab(run_id_input, backend_url)
