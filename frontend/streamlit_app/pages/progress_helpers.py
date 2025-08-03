import streamlit as st


def display_document_status(documents):
    """Display document status overview with timing information"""
    st.markdown("**Document Status:**")
    for doc in documents:
        status_icon = (
            "✅"
            if doc.get("indexing_status") == "completed"
            else ("❌" if doc.get("indexing_status") == "failed" else "🔄")
        )

        # Get timing information
        step_timings = doc.get("step_timings", {})
        total_time = doc.get("total_processing_time", 0)
        current_step = doc.get("current_step")

        # Display document status with timing
        timing_info = f" ({total_time:.1f}s)" if total_time > 0 else ""
        st.markdown(
            f"{status_icon} {doc.get('filename', 'Unknown')}: {doc.get('indexing_status', 'unknown')}{timing_info}"
        )

        # Show current step if processing
        if (
            current_step
            and current_step != "unknown"
            and doc.get("indexing_status") not in ["completed", "failed"]
        ):
            st.markdown(f"  🔄 Currently processing: {current_step}")


def display_timing_summary(documents):
    """Display timing summary for all documents"""
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
                    for step_name, duration in step_timings.items():
                        # Convert step names to readable format
                        readable_step = step_name.replace("Step", "").title()
                        st.markdown(f"• {readable_step}: {duration:.2f}s")

                with col2:
                    st.markdown("**Progress:**")
                    if current_step and current_step != "unknown":
                        st.info(f"🔄 Current: {current_step}")
                    else:
                        st.success("✅ All steps completed")

                    # Show progress percentage
                    total_steps = (
                        5  # partition, metadata, enrichment, chunking, embedding
                    )
                    completed_steps = len(
                        [s for s in step_timings.keys() if step_timings[s] > 0]
                    )
                    progress_pct = (completed_steps / total_steps) * 100
                    st.progress(progress_pct / 100)
                    st.markdown(
                        f"**{progress_pct:.0f}% complete** ({completed_steps}/{total_steps} steps)"
                    )
            else:
                st.markdown("⏳ No timing data available yet")
                if current_step and current_step != "unknown":
                    st.info(f"🔄 Currently processing: {current_step}")


def display_step_results(
    documents, step_name, step_display_name, step_icon, step_description
):
    """Display results for a specific pipeline step"""
    with st.expander(f"{step_icon} {step_display_name}", expanded=True):
        st.markdown(f"**{step_description}:**")
        for doc in documents:
            step_results = doc.get("step_results", {})
            step_result = step_results.get(step_name, {})
            step_timings = doc.get("step_timings", {})

            if step_result:
                status = step_result.get("status", "unknown")
                duration = step_timings.get(step_name, 0)

                st.markdown(f"**{doc.get('filename', 'Unknown')}:**")
                st.markdown(f"- Status: {status}")
                if duration > 0:
                    st.markdown(f"- Duration: {duration:.2f}s")

                # Display step-specific information
                if step_name == "PartitionStep":
                    summary = step_result.get("summary_stats", {})
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

                elif step_name == "MetadataStep":
                    sample_outputs = step_result.get("sample_outputs", {})
                    headers = sample_outputs.get("page_sections", {})
                    if headers:
                        section_titles = list(headers.values())[:5]
                        st.markdown("- Page sections: " + ", ".join(section_titles))
                    else:
                        st.markdown("- No page sections detected")

                elif step_name == "EnrichmentStep":
                    sample_outputs = step_result.get("sample_outputs", {})
                    captions = sample_outputs.get("sample_images", [])
                    if captions:
                        st.markdown(
                            f"- Sample image caption: {captions[0] if captions else 'None'}"
                        )
                    else:
                        st.markdown("- No image captions available")

                elif step_name == "ChunkingStep":
                    summary = step_result.get("summary_stats", {})
                    st.markdown(
                        f"- Total chunks: {summary.get('total_chunks_created', 'N/A')}"
                    )
                    st.markdown(
                        f"- Average chunk size: {summary.get('average_chunk_size', 'N/A')} characters"
                    )
            else:
                st.markdown(
                    f"**{doc.get('filename', 'Unknown')}:** No {step_name.lower()} data"
                )


def display_embedding_results(run_data):
    """Display embedding results from indexing run"""
    with st.expander("🧠 Step 5: Embedding", expanded=True):
        st.markdown("**Embedding Results:**")
        if run_data.get("step_results"):
            embedding_result = run_data["step_results"].get("EmbeddingStep", {})
            if embedding_result:
                status = embedding_result.get("status", "unknown")
                summary = embedding_result.get("summary_stats", {})
                st.markdown(f"- Status: {status}")
                st.markdown(
                    f"- Total embeddings: {summary.get('embeddings_created', 'N/A')}"
                )
                st.markdown(f"- Model used: {summary.get('model_used', 'N/A')}")
            else:
                st.markdown("No embedding data available")
        else:
            st.markdown("No embedding data available")
