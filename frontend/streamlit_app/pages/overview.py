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
            else:
                st.info("📭 No recent indexing runs found.")
                run_id_input = None
        else:
            st.warning(
                f"⚠️ Could not load recent runs (status: {runs_response.status_code})"
            )
            st.info("💡 You can still enter a run ID manually above.")
            run_id_input = None
    except Exception as e:
        st.warning(f"⚠️ Could not load recent runs: {str(e)}")
        st.info("💡 You can still enter a run ID manually above.")
        run_id_input = None

    # Show selected run info and tabs
    if run_id_input:

        # Tab section with Overview, Query, Wiki, Documents
        tab_overview, tab_query, tab_wiki, tab_documents, tab_config = st.tabs(
            ["Overview", "Query", "Wiki", "Documents", "Config"]
        )

        with tab_overview:
            st.markdown("### 📄 Overview")

            try:
                # Get indexing run progress and step results
                logger.info(f"📊 Fetching progress data for run ID: {run_id_input}")
                progress_response = requests.get(
                    f"{backend_url}/api/pipeline/indexing/runs/{run_id_input}/progress",
                    headers=headers,
                )

                logger.info(
                    f"📡 Progress API response status: {progress_response.status_code}"
                )

                if progress_response.status_code == 200:
                    progress_data = progress_response.json()
                    logger.info(f"📊 Progress data loaded: {len(progress_data)} fields")

                    # Display progress information
                    progress_info = progress_data.get("progress", {})
                    if progress_info:
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

                    # Display run status
                    st.markdown("##### 📋 Run Status")
                    status_info = {
                        "Status": progress_data.get("status", "unknown"),
                        "Upload Type": progress_data.get("upload_type", "unknown"),
                        "Started At": progress_data.get("started_at", "N/A"),
                        "Completed At": progress_data.get("completed_at", "N/A"),
                    }
                    if progress_data.get("error_message"):
                        status_info["Error Message"] = progress_data.get(
                            "error_message"
                        )

                    st.json(status_info)

                    # Display step results if available
                    step_results = progress_data.get("step_results", {})
                    if step_results:
                        st.markdown("##### 🔧 Step Results")
                        st.json(step_results)

                elif progress_response.status_code == 404:
                    st.info("No progress data found for this indexing run.")
                    logger.warning(
                        f"⚠️ No progress data found for run ID: {run_id_input}"
                    )
                else:
                    st.error(
                        f"Failed to load progress data: {progress_response.status_code}"
                    )
                    st.error(f"Response: {progress_response.text}")
                    logger.error(
                        f"❌ Progress API failed: {progress_response.status_code} - {progress_response.text}"
                    )

            except Exception as e:
                st.error(f"Error loading progress data: {str(e)}")
                logger.error(f"❌ Error in overview tab: {e}")

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
            st.markdown("### 📄 Documents")

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
                        for i, document in enumerate(documents):
                            doc_id = document.get("id")
                            doc_name = document.get("filename", f"Document {doc_id}")
                            step_results = document.get("step_results", {})

                            logger.info(f"📄 Document {i+1}: {doc_name} (ID: {doc_id})")
                            logger.info(
                                f"📄 Document step_results keys: {list(step_results.keys())}"
                            )

                            with st.expander(f"📄 {doc_name}"):
                                (
                                    subtab_partition,
                                    subtab_metadata,
                                    subtab_enrich,
                                    subtab_chunk,
                                ) = st.tabs(
                                    ["Partition", "Metadata", "Enrich", "Chunk"]
                                )

                                with subtab_partition:
                                    # Get partition step results (using correct key)
                                    partition_results = step_results.get(
                                        "PartitionStep", {}
                                    )

                                    if partition_results:
                                        logger.info(
                                            f"🧩 Partition results for {doc_name}: {len(partition_results)} fields"
                                        )

                                        # Display summary stats if available
                                        summary_stats = partition_results.get(
                                            "summary_stats", {}
                                        )

                                        if summary_stats:
                                            logger.info(
                                                f"📊 Summary stats for {doc_name}: {len(summary_stats)} fields"
                                            )
                                            st.markdown("##### Summary Stats")
                                            st.json(summary_stats)
                                        else:
                                            st.info(
                                                "No summary stats available for partition step"
                                            )
                                            logger.warning(
                                                f"⚠️ No summary_stats found in partition results for {doc_name}"
                                            )

                                        # Full data in expander
                                        with st.expander("📋 Full Partition Data"):
                                            st.json(partition_results)
                                    else:
                                        st.info(
                                            "Partitioning details and results will appear here."
                                        )
                                        logger.warning(
                                            f"⚠️ No partition results found for {doc_name}"
                                        )

                                with subtab_metadata:
                                    # Get metadata step results (using correct key)
                                    metadata_results = step_results.get(
                                        "MetadataStep", {}
                                    )

                                    if metadata_results:
                                        logger.info(
                                            f"📋 Metadata results for {doc_name}: {len(metadata_results)} fields"
                                        )

                                        # Display summary stats if available
                                        summary_stats = metadata_results.get(
                                            "summary_stats", {}
                                        )

                                        if summary_stats:
                                            st.markdown("##### Summary Stats")
                                            st.json(summary_stats)
                                        else:
                                            st.info(
                                                "No summary stats available for metadata step"
                                            )

                                        # Full data in expander
                                        with st.expander("📋 Full Metadata Data"):
                                            st.json(metadata_results)
                                    else:
                                        st.info(
                                            "Metadata details and results will appear here."
                                        )

                                with subtab_enrich:
                                    # Get enrich step results (using correct key)
                                    enrich_results = step_results.get(
                                        "EnrichmentStep", {}
                                    )

                                    if enrich_results:
                                        logger.info(
                                            f"✨ Enrich results for {doc_name}: {len(enrich_results)} fields"
                                        )

                                        # Display summary stats if available
                                        summary_stats = enrich_results.get(
                                            "summary_stats", {}
                                        )

                                        if summary_stats:
                                            st.markdown("##### Summary Stats")
                                            st.json(summary_stats)
                                        else:
                                            st.info(
                                                "No summary stats available for enrichment step"
                                            )

                                        # Full data in expander
                                        with st.expander("📋 Full Enrichment Data"):
                                            st.json(enrich_results)
                                    else:
                                        st.info(
                                            "Enrichment details and results will appear here."
                                        )

                                with subtab_chunk:
                                    # Get chunk step results (using correct key)
                                    chunk_results = step_results.get("ChunkingStep", {})

                                    if chunk_results:
                                        logger.info(
                                            f"📦 Chunk results for {doc_name}: {len(chunk_results)} fields"
                                        )

                                        # Display summary stats if available
                                        summary_stats = chunk_results.get(
                                            "summary_stats", {}
                                        )

                                        if summary_stats:
                                            st.markdown("##### Summary Stats")
                                            st.json(summary_stats)
                                        else:
                                            st.info(
                                                "No summary stats available for chunking step"
                                            )

                                        # Full data in expander
                                        with st.expander("📋 Full Chunking Data"):
                                            st.json(chunk_results)
                                    else:
                                        st.info(
                                            "Chunking details and results will appear here."
                                        )
                    else:
                        st.info("No documents found for this indexing run.")
                        logger.warning(
                            f"⚠️ No documents found for run ID: {run_id_input}"
                        )
                else:
                    st.error(
                        f"Failed to load documents: {documents_response.status_code}"
                    )
                    st.error(f"Response: {documents_response.text}")
                    logger.error(
                        f"❌ Documents API failed: {documents_response.status_code} - {documents_response.text}"
                    )

            except Exception as e:
                st.error(f"Error loading documents: {str(e)}")
                logger.error(f"❌ Error in documents tab: {e}")

        with tab_config:
            st.markdown("### ⚙️ Pipeline Configuration")

            try:
                # Get pipeline configuration for this indexing run
                logger.info(f"⚙️ Fetching pipeline status for run ID: {run_id_input}")
                status_response = requests.get(
                    f"{backend_url}/api/pipeline/indexing/runs/{run_id_input}/status",
                    headers=headers,
                )

                logger.info(
                    f"📡 Status API response status: {status_response.status_code}"
                )

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
                    st.error(
                        f"Failed to load status data: {status_response.status_code}"
                    )
                    st.error(f"Response: {status_response.text}")
                    logger.error(
                        f"❌ Status API failed: {status_response.status_code} - {status_response.text}"
                    )

            except Exception as e:
                st.error(f"Error loading status data: {str(e)}")
                logger.error(f"❌ Error in config tab: {e}")
