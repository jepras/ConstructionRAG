import streamlit as st
import requests
import logging
from datetime import datetime
from utils.shared import get_backend_url

logger = logging.getLogger(__name__)


def show_progress_page():
    """Show the progress tracking page"""
    st.markdown("## 📊 Indexing Run Progress")
    st.markdown("Track the progress of your document processing runs.")

    # Check authentication first
    auth_manager = st.session_state.auth_manager

    if not auth_manager.is_authenticated():
        st.error("🔐 Please sign in to view progress.")
        st.info("Use the sidebar to navigate to the Authentication page.")
        return

    # Show user info
    user_info = auth_manager.get_current_user()
    if user_info and user_info.get("user"):
        user = user_info["user"]
        st.success(f"✅ Signed in as: {user.get('email', 'N/A')}")

    try:
        # Get backend URL and access token
        backend_url = get_backend_url()
        access_token = st.session_state.get("access_token")

        if not access_token:
            st.error("❌ No access token found. Please sign in again.")
            return

        # Prepare headers
        headers = {"Authorization": f"Bearer {access_token}"}

        # Get all indexing runs
        runs_response = requests.get(
            f"{backend_url}/api/pipeline/indexing/runs", headers=headers
        )

        if runs_response.status_code != 200:
            st.error(f"❌ Failed to load indexing runs: {runs_response.status_code}")
            st.error(f"Response: {runs_response.text}")
            return

        runs = runs_response.json()

        if not runs:
            st.info(
                "📭 No indexing runs found. Upload some documents to see progress here."
            )
            return

        # Create dropdown for run selection
        st.subheader("Select Indexing Run")

        # Format run options for dropdown
        run_options = {}
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
                    date_str = started_at[
                        :19
                    ]  # Just take first 19 chars if parsing fails
            else:
                date_str = "No start time"

            label = f"{upload_type.title()} - {status.title()} ({date_str})"
            run_options[label] = run["id"]

        selected_run_label = st.selectbox(
            "Choose an indexing run:",
            list(run_options.keys()),
            help="Select an indexing run to view its progress",
        )

        if selected_run_label:
            run_id = run_options[selected_run_label]

            # Get detailed status for selected run
            status_response = requests.get(
                f"{backend_url}/api/pipeline/indexing/runs/{run_id}/status",
                headers=headers,
            )

            if status_response.status_code == 200:
                run_data = status_response.json()

                # Display run information with smaller font
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

                # Get documents for this indexing run to show step results
                st.subheader("📄 Document Progress Overview")

                # For email uploads, get documents by indexing run to show detailed step results
                if run_data.get("upload_type") == "email" and run_data.get("upload_id"):
                    # Get documents for this indexing run (same as project uploads)
                    documents_response = requests.get(
                        f"{backend_url}/api/documents/by-index-run/{run_id}",
                        headers=headers,
                    )

                    if documents_response.status_code == 200:
                        documents = documents_response.json()

                        # Show document status overview
                        if documents:
                            st.markdown("**Document Status:**")
                            for doc in documents:
                                status_icon = (
                                    "✅"
                                    if doc.get("indexing_status") == "completed"
                                    else (
                                        "❌"
                                        if doc.get("indexing_status") == "failed"
                                        else "🔄"
                                    )
                                )

                                # Get timing information
                                step_timings = doc.get("step_timings", {})
                                total_time = doc.get("total_processing_time", 0)
                                current_step = doc.get("current_step")

                                # Display document status with timing
                                timing_info = (
                                    f" ({total_time:.1f}s)" if total_time > 0 else ""
                                )
                                st.markdown(
                                    f"{status_icon} {doc.get('filename', 'Unknown')}: {doc.get('indexing_status', 'unknown')}{timing_info}"
                                )

                                # Show current step if processing
                                if (
                                    current_step
                                    and current_step != "unknown"
                                    and doc.get("indexing_status")
                                    not in ["completed", "failed"]
                                ):
                                    st.markdown(
                                        f"  🔄 Currently processing: {current_step}"
                                    )

                            # Add timing summary section
                            st.subheader("⏱️ Processing Timeline")
                            for doc in documents:
                                step_timings = doc.get("step_timings", {})
                                total_time = doc.get("total_processing_time", 0)
                                current_step = doc.get("current_step")

                                with st.expander(
                                    f"📊 {doc.get('filename', 'Unknown')} - {total_time:.1f}s total",
                                    expanded=False,
                                ):
                                    if step_timings:
                                        # Create timing breakdown
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.markdown("**Step Timings:**")
                                            for (
                                                step_name,
                                                duration,
                                            ) in step_timings.items():
                                                # Convert step names to readable format
                                                readable_step = step_name.replace(
                                                    "Step", ""
                                                ).title()
                                                st.markdown(
                                                    f"• {readable_step}: {duration:.2f}s"
                                                )

                                        with col2:
                                            st.markdown("**Progress:**")
                                            if (
                                                current_step
                                                and current_step != "unknown"
                                            ):
                                                st.info(f"🔄 Current: {current_step}")
                                            else:
                                                st.success("✅ All steps completed")

                                            # Show progress percentage
                                            total_steps = 5  # partition, metadata, enrichment, chunking, embedding
                                            completed_steps = len(
                                                [
                                                    s
                                                    for s in step_timings.keys()
                                                    if step_timings[s] > 0
                                                ]
                                            )
                                            progress_pct = (
                                                completed_steps / total_steps
                                            ) * 100
                                            st.progress(progress_pct / 100)
                                            st.markdown(
                                                f"**{progress_pct:.0f}% complete** ({completed_steps}/{total_steps} steps)"
                                            )
                                    else:
                                        st.markdown("⏳ No timing data available yet")
                                        if current_step and current_step != "unknown":
                                            st.info(
                                                f"🔄 Currently processing: {current_step}"
                                            )

                            # Show step-by-step results from documents
                            st.subheader("🔧 Pipeline Steps")

                            # Step 1: Partition
                            with st.expander("📄 Step 1: Partition", expanded=True):
                                st.markdown("**Summary:**")
                                for doc in documents:
                                    step_results = doc.get("step_results", {})
                                    partition_result = step_results.get(
                                        "PartitionStep", {}
                                    )
                                    step_timings = doc.get("step_timings", {})

                                    if partition_result:
                                        status = partition_result.get(
                                            "status", "unknown"
                                        )
                                        summary = partition_result.get(
                                            "summary_stats", {}
                                        )
                                        duration = step_timings.get("PartitionStep", 0)

                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:**"
                                        )
                                        st.markdown(f"- Status: {status}")
                                        if duration > 0:
                                            st.markdown(f"- Duration: {duration:.2f}s")
                                        st.markdown(
                                            f"- Text elements: {summary.get('text_elements', 'N/A')}"
                                        )
                                        st.markdown(
                                            f"- Pages analyzed: {summary.get('pages_analyzed', 'N/A')}"
                                        )
                                        st.markdown(
                                            f"- Tables detected: {summary.get('table_elements', 'N/A')}"
                                        )
                                        st.markdown(
                                            f"- Extracted pages: {summary.get('extracted_pages', 'N/A')}"
                                        )
                                    else:
                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:** No partition data"
                                        )

                            # Step 2: Metadata
                            with st.expander("🏷️ Step 2: Metadata", expanded=True):
                                st.markdown("**Page Sections Detected:**")
                                for doc in documents:
                                    step_results = doc.get("step_results", {})
                                    metadata_result = step_results.get(
                                        "MetadataStep", {}
                                    )
                                    step_timings = doc.get("step_timings", {})

                                    if metadata_result:
                                        status = metadata_result.get(
                                            "status", "unknown"
                                        )
                                        sample_outputs = metadata_result.get(
                                            "sample_outputs", {}
                                        )
                                        headers = sample_outputs.get(
                                            "page_sections", {}
                                        )
                                        duration = step_timings.get("MetadataStep", 0)

                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:**"
                                        )
                                        st.markdown(f"- Status: {status}")
                                        if duration > 0:
                                            st.markdown(f"- Duration: {duration:.2f}s")
                                        if headers:
                                            # Get first 5 section titles from the dictionary
                                            section_titles = list(headers.values())[:5]
                                            st.markdown(
                                                "- Page sections: "
                                                + ", ".join(section_titles)
                                            )  # Show first 5 headers
                                        else:
                                            st.markdown("- No page sections detected")
                                    else:
                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:** No metadata data"
                                        )

                            # Step 3: Enrichment
                            with st.expander("🔍 Step 3: Enrichment", expanded=True):
                                st.markdown("**Image Captions:**")
                                for doc in documents:
                                    step_results = doc.get("step_results", {})
                                    enrichment_result = step_results.get(
                                        "EnrichmentStep", {}
                                    )
                                    step_timings = doc.get("step_timings", {})

                                    if enrichment_result:
                                        status = enrichment_result.get(
                                            "status", "unknown"
                                        )
                                        sample_outputs = enrichment_result.get(
                                            "sample_outputs", {}
                                        )
                                        captions = sample_outputs.get(
                                            "sample_images", []
                                        )
                                        duration = step_timings.get("EnrichmentStep", 0)

                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:**"
                                        )
                                        st.markdown(f"- Status: {status}")
                                        if duration > 0:
                                            st.markdown(f"- Duration: {duration:.2f}s")
                                        if captions:
                                            st.markdown(
                                                f"- Sample image caption: {captions[0] if captions else 'None'}"
                                            )
                                        else:
                                            st.markdown("- No image captions available")
                                    else:
                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:** No enrichment data"
                                        )

                            # Step 4: Chunking
                            with st.expander("✂️ Step 4: Chunking", expanded=True):
                                st.markdown("**Chunking Statistics:**")
                                for doc in documents:
                                    step_results = doc.get("step_results", {})
                                    chunking_result = step_results.get(
                                        "ChunkingStep", {}
                                    )
                                    step_timings = doc.get("step_timings", {})

                                    if chunking_result:
                                        status = chunking_result.get(
                                            "status", "unknown"
                                        )
                                        summary = chunking_result.get(
                                            "summary_stats", {}
                                        )
                                        duration = step_timings.get("ChunkingStep", 0)

                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:**"
                                        )
                                        st.markdown(f"- Status: {status}")
                                        if duration > 0:
                                            st.markdown(f"- Duration: {duration:.2f}s")
                                        st.markdown(
                                            f"- Total chunks: {summary.get('total_chunks_created', 'N/A')}"
                                        )
                                        st.markdown(
                                            f"- Average chunk size: {summary.get('average_chunk_size', 'N/A')} characters"
                                        )
                                    else:
                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:** No chunking data"
                                        )

                            # Step 5: Embedding (from indexing run)
                            with st.expander("🧠 Step 5: Embedding", expanded=True):
                                st.markdown("**Embedding Results:**")
                                if run_data.get("step_results"):
                                    embedding_result = run_data["step_results"].get(
                                        "EmbeddingStep", {}
                                    )
                                    if embedding_result:
                                        status = embedding_result.get(
                                            "status", "unknown"
                                        )
                                        summary = embedding_result.get(
                                            "summary_stats", {}
                                        )
                                        st.markdown(f"- Status: {status}")
                                        st.markdown(
                                            f"- Total embeddings: {summary.get('embeddings_created', 'N/A')}"
                                        )
                                        st.markdown(
                                            f"- Model used: {summary.get('model_used', 'N/A')}"
                                        )
                                    else:
                                        st.markdown("No embedding data available")
                                else:
                                    st.markdown("No embedding data available")
                        else:
                            st.info("No documents found for this indexing run")
                    else:
                        st.error(
                            f"Failed to load documents: {documents_response.status_code}"
                        )

                # For project uploads, use the new documents endpoint
                else:
                    # Get documents for this indexing run
                    documents_response = requests.get(
                        f"{backend_url}/api/documents/by-index-run/{run_id}",
                        headers=headers,
                    )

                    if documents_response.status_code == 200:
                        documents = documents_response.json()

                        # Show document status overview
                        if documents:
                            st.markdown("**Document Status:**")
                            for doc in documents:
                                status_icon = (
                                    "✅"
                                    if doc.get("indexing_status") == "completed"
                                    else (
                                        "❌"
                                        if doc.get("indexing_status") == "failed"
                                        else "🔄"
                                    )
                                )

                                # Get timing information
                                step_timings = doc.get("step_timings", {})
                                total_time = doc.get("total_processing_time", 0)
                                current_step = doc.get("current_step")

                                # Display document status with timing
                                timing_info = (
                                    f" ({total_time:.1f}s)" if total_time > 0 else ""
                                )
                                st.markdown(
                                    f"{status_icon} {doc.get('filename', 'Unknown')}: {doc.get('indexing_status', 'unknown')}{timing_info}"
                                )

                                # Show current step if processing
                                if (
                                    current_step
                                    and current_step != "unknown"
                                    and doc.get("indexing_status")
                                    not in ["completed", "failed"]
                                ):
                                    st.markdown(
                                        f"  🔄 Currently processing: {current_step}"
                                    )

                            # Add timing summary section
                            st.subheader("⏱️ Processing Timeline")
                            for doc in documents:
                                step_timings = doc.get("step_timings", {})
                                total_time = doc.get("total_processing_time", 0)
                                current_step = doc.get("current_step")

                                with st.expander(
                                    f"📊 {doc.get('filename', 'Unknown')} - {total_time:.1f}s total",
                                    expanded=False,
                                ):
                                    if step_timings:
                                        # Create timing breakdown
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.markdown("**Step Timings:**")
                                            for (
                                                step_name,
                                                duration,
                                            ) in step_timings.items():
                                                # Convert step names to readable format
                                                readable_step = step_name.replace(
                                                    "Step", ""
                                                ).title()
                                                st.markdown(
                                                    f"• {readable_step}: {duration:.2f}s"
                                                )

                                        with col2:
                                            st.markdown("**Progress:**")
                                            if (
                                                current_step
                                                and current_step != "unknown"
                                            ):
                                                st.info(f"🔄 Current: {current_step}")
                                            else:
                                                st.success("✅ All steps completed")

                                            # Show progress percentage
                                            total_steps = 5  # partition, metadata, enrichment, chunking, embedding
                                            completed_steps = len(
                                                [
                                                    s
                                                    for s in step_timings.keys()
                                                    if step_timings[s] > 0
                                                ]
                                            )
                                            progress_pct = (
                                                completed_steps / total_steps
                                            ) * 100
                                            st.progress(progress_pct / 100)
                                            st.markdown(
                                                f"**{progress_pct:.0f}% complete** ({completed_steps}/{total_steps} steps)"
                                            )
                                    else:
                                        st.markdown("⏳ No timing data available yet")
                                        if current_step and current_step != "unknown":
                                            st.info(
                                                f"🔄 Currently processing: {current_step}"
                                            )

                            # Show step-by-step results from documents
                            st.subheader("🔧 Pipeline Steps")

                            # Step 1: Partition
                            with st.expander("📄 Step 1: Partition", expanded=True):
                                st.markdown("**Summary:**")
                                for doc in documents:
                                    step_results = doc.get("step_results", {})
                                    partition_result = step_results.get(
                                        "PartitionStep", {}
                                    )
                                    step_timings = doc.get("step_timings", {})

                                    if partition_result:
                                        status = partition_result.get(
                                            "status", "unknown"
                                        )
                                        summary = partition_result.get(
                                            "summary_stats", {}
                                        )
                                        duration = step_timings.get("PartitionStep", 0)

                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:**"
                                        )
                                        st.markdown(f"- Status: {status}")
                                        if duration > 0:
                                            st.markdown(f"- Duration: {duration:.2f}s")
                                        st.markdown(
                                            f"- Text elements: {summary.get('text_elements', 'N/A')}"
                                        )
                                        st.markdown(
                                            f"- Pages analyzed: {summary.get('pages_analyzed', 'N/A')}"
                                        )
                                        st.markdown(
                                            f"- Tables detected: {summary.get('table_elements', 'N/A')}"
                                        )
                                        st.markdown(
                                            f"- Extracted pages: {summary.get('extracted_pages', 'N/A')}"
                                        )
                                    else:
                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:** No partition data"
                                        )

                            # Step 2: Metadata
                            with st.expander("🏷️ Step 2: Metadata", expanded=True):
                                st.markdown("**Page Sections Detected:**")
                                for doc in documents:
                                    step_results = doc.get("step_results", {})
                                    metadata_result = step_results.get(
                                        "MetadataStep", {}
                                    )
                                    step_timings = doc.get("step_timings", {})

                                    if metadata_result:
                                        status = metadata_result.get(
                                            "status", "unknown"
                                        )
                                        sample_outputs = metadata_result.get(
                                            "sample_outputs", {}
                                        )
                                        headers = sample_outputs.get(
                                            "page_sections", {}
                                        )
                                        duration = step_timings.get("MetadataStep", 0)

                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:**"
                                        )
                                        st.markdown(f"- Status: {status}")
                                        if duration > 0:
                                            st.markdown(f"- Duration: {duration:.2f}s")
                                        if headers:
                                            # Get first 5 section titles from the dictionary
                                            section_titles = list(headers.values())[:5]
                                            st.markdown(
                                                "- Page sections: "
                                                + ", ".join(section_titles)
                                            )  # Show first 5 headers
                                        else:
                                            st.markdown("- No page sections detected")
                                    else:
                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:** No metadata data"
                                        )

                            # Step 3: Enrichment
                            with st.expander("🔍 Step 3: Enrichment", expanded=True):
                                st.markdown("**Image Captions:**")
                                for doc in documents:
                                    step_results = doc.get("step_results", {})
                                    enrichment_result = step_results.get(
                                        "EnrichmentStep", {}
                                    )
                                    step_timings = doc.get("step_timings", {})

                                    if enrichment_result:
                                        status = enrichment_result.get(
                                            "status", "unknown"
                                        )
                                        sample_outputs = enrichment_result.get(
                                            "sample_outputs", {}
                                        )
                                        captions = sample_outputs.get(
                                            "sample_images", []
                                        )
                                        duration = step_timings.get("EnrichmentStep", 0)

                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:**"
                                        )
                                        st.markdown(f"- Status: {status}")
                                        if duration > 0:
                                            st.markdown(f"- Duration: {duration:.2f}s")
                                        if captions:
                                            st.markdown(
                                                f"- Sample image caption: {captions[0] if captions else 'None'}"
                                            )
                                        else:
                                            st.markdown("- No image captions available")
                                    else:
                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:** No enrichment data"
                                        )

                            # Step 4: Chunking
                            with st.expander("✂️ Step 4: Chunking", expanded=True):
                                st.markdown("**Chunking Statistics:**")
                                for doc in documents:
                                    step_results = doc.get("step_results", {})
                                    chunking_result = step_results.get(
                                        "ChunkingStep", {}
                                    )
                                    step_timings = doc.get("step_timings", {})

                                    if chunking_result:
                                        status = chunking_result.get(
                                            "status", "unknown"
                                        )
                                        summary = chunking_result.get(
                                            "summary_stats", {}
                                        )
                                        duration = step_timings.get("ChunkingStep", 0)

                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:**"
                                        )
                                        st.markdown(f"- Status: {status}")
                                        if duration > 0:
                                            st.markdown(f"- Duration: {duration:.2f}s")
                                        st.markdown(
                                            f"- Total chunks: {summary.get('total_chunks_created', 'N/A')}"
                                        )
                                        st.markdown(
                                            f"- Average chunk size: {summary.get('average_chunk_size', 'N/A')} characters"
                                        )
                                    else:
                                        st.markdown(
                                            f"**{doc.get('filename', 'Unknown')}:** No chunking data"
                                        )

                            # Step 5: Embedding (from indexing run)
                            with st.expander("🧠 Step 5: Embedding", expanded=True):
                                st.markdown("**Embedding Results:**")
                                if run_data.get("step_results"):
                                    embedding_result = run_data["step_results"].get(
                                        "EmbeddingStep", {}
                                    )
                                    if embedding_result:
                                        status = embedding_result.get(
                                            "status", "unknown"
                                        )
                                        summary = embedding_result.get(
                                            "summary_stats", {}
                                        )
                                        st.markdown(f"- Status: {status}")
                                        st.markdown(
                                            f"- Total embeddings: {summary.get('embeddings_created', 'N/A')}"
                                        )
                                        st.markdown(
                                            f"- Model used: {summary.get('model_used', 'N/A')}"
                                        )
                                    else:
                                        st.markdown("No embedding data available")
                                else:
                                    st.markdown("No embedding data available")
                        else:
                            st.info("No documents found for this indexing run")
                    else:
                        st.error(
                            f"Failed to load documents: {documents_response.status_code}"
                        )

                # Show pipeline configuration at the bottom
                if run_data.get("pipeline_config"):
                    st.subheader("⚙️ Pipeline Configuration")
                    with st.expander("View Configuration"):
                        st.json(run_data["pipeline_config"])

                # Auto-refresh section
                st.subheader("🔄 Refresh")
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("Refresh Progress", type="primary"):
                        st.rerun()
                with col2:
                    st.info(
                        "Click 'Refresh Progress' to get the latest status updates."
                    )

            else:
                st.error(f"❌ Failed to get run status: {status_response.status_code}")
                st.error(f"Response: {status_response.text}")

    except Exception as e:
        st.error(f"❌ Error loading progress: {str(e)}")
        st.exception(e)
