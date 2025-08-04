import streamlit as st
import requests
import base64
from PIL import Image
import io
import random


def display_document_status(documents):
    """Display document status overview with timing information in a compact format"""
    st.markdown("**Document Status:**")

    # Create a more compact display using columns
    for doc in documents:
        status_icon = (
            "✅"
            if doc.get("indexing_status") == "completed"
            else ("❌" if doc.get("indexing_status") == "failed" else "🔄")
        )

        # Get timing information
        total_time = doc.get("total_processing_time", 0)
        current_step = doc.get("current_step")

        # Create a compact row with filename, status, and timing
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            st.markdown(f"{status_icon} **{doc.get('filename', 'Unknown')}**")

        with col2:
            status_text = doc.get("indexing_status", "unknown")
            st.markdown(f"`{status_text}`")

        with col3:
            timing_info = f"{total_time:.1f}s" if total_time > 0 else "N/A"
            st.markdown(f"`{timing_info}`")

        # Show current step if processing (compact format)
        if (
            current_step
            and current_step != "unknown"
            and doc.get("indexing_status") not in ["completed", "failed"]
        ):
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🔄 **Currently:** {current_step}")

        # Add a small separator between documents
        st.markdown("---")


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
                    total_steps = 4  # partition, metadata, enrichment, chunking (embedding handled separately)
                    completed_steps = len(
                        [
                            s
                            for s in step_timings.keys()
                            if step_timings[s] > 0 and s != "EmbeddingStep"
                        ]
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
    """Display results for a specific pipeline step in a compact format"""
    with st.expander(f"{step_icon} {step_display_name}", expanded=True):
        st.markdown(f"**{step_description}:**")
        for doc in documents:
            step_results = doc.get("step_results", {})
            step_result = step_results.get(step_name, {})
            step_timings = doc.get("step_timings", {})

            if step_result:
                status = step_result.get("status", "unknown")
                duration = step_timings.get(step_name, 0)

                # Compact header with filename, status, and duration on same line
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{doc.get('filename', 'Unknown')}:**")
                with col2:
                    st.markdown(f"Status: `{status}`")
                with col3:
                    if duration > 0:
                        st.markdown(f"Duration: `{duration:.2f}s`")

                # Display step-specific information in compact format
                if step_name == "PartitionStep":
                    summary = step_result.get("summary_stats", {})
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(
                            f"📄 Text elements: {summary.get('text_elements', 'N/A')} | 📊 Tables: {summary.get('table_elements', 'N/A')}"
                        )
                    with col2:
                        st.markdown(
                            f"📖 Pages analyzed: {summary.get('pages_analyzed', 'N/A')} | 📄 Extracted: {summary.get('extracted_pages', 'N/A')}"
                        )

                elif step_name == "MetadataStep":
                    sample_outputs = step_result.get("sample_outputs", {})
                    headers = sample_outputs.get("page_sections", {})
                    if headers:
                        section_titles = list(headers.values())[:5]
                        st.markdown(f"🏷️ Page sections: {', '.join(section_titles)}")
                    else:
                        st.markdown("🏷️ No page sections detected")

                elif step_name == "EnrichmentStep":
                    # Display image and table grid
                    display_image_table_grid(documents, step_name)

                elif step_name == "ChunkingStep":
                    summary = step_result.get("summary_stats", {})
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(
                            f"✂️ Total chunks: {summary.get('total_chunks_created', 'N/A')}"
                        )
                    with col2:
                        st.markdown(
                            f"📏 Avg chunk size: {summary.get('average_chunk_size', 'N/A')} chars"
                        )

                # Add small separator between documents
                st.markdown("---")
            else:
                st.markdown(
                    f"**{doc.get('filename', 'Unknown')}:** No {step_name.lower()} data"
                )
                st.markdown("---")


def display_embedding_results(run_data):
    """Display embedding results from indexing run in a compact format"""
    with st.expander("🧠 Step 5: Embedding", expanded=True):
        st.markdown("**Embedding Results:**")
        if run_data.get("step_results"):
            embedding_result = run_data["step_results"].get("EmbeddingStep", {})
            if embedding_result:
                status = embedding_result.get("status", "unknown")
                summary = embedding_result.get("summary_stats", {})

                # Compact display with columns
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"Status: `{status}`")
                with col2:
                    st.markdown(
                        f"Embeddings: {summary.get('embeddings_created', 'N/A')}"
                    )
                with col3:
                    st.markdown(f"Model: {summary.get('model_used', 'N/A')}")
            else:
                st.markdown("No embedding data available")
        else:
            st.markdown("No embedding data available")


def display_image_table_grid(documents, step_name):
    """Display up to 5 random images and 5 random tables in a grid format"""
    if step_name != "EnrichmentStep":
        return

    # Collect all images and tables from all documents
    all_images = []
    all_tables = []

    for doc in documents:
        step_results = doc.get("step_results", {})
        step_result = step_results.get(step_name, {})

        if step_result and step_result.get("data"):
            data = step_result["data"]

            # Collect table images
            for table in data.get("table_elements", []):
                if "enrichment_metadata" in table and table.get("metadata", {}).get(
                    "image_url"
                ):
                    # Handle URL that might be a dictionary or string
                    url = table["metadata"]["image_url"]
                    if isinstance(url, dict):
                        # Extract URL from dictionary (try both signedURL and signedUrl keys)
                        url = (
                            url.get("signedURL")
                            or url.get("signedUrl")
                            or url.get("url")
                        )

                    if url:
                        enrichment_meta = table.get("enrichment_metadata", {})
                        caption = enrichment_meta.get(
                            "table_image_caption", "No caption available"
                        )
                        prompt = enrichment_meta.get("prompt_used")
                        prompt_template = enrichment_meta.get("prompt_template")

                        all_tables.append(
                            {
                                "url": url,
                                "caption": caption,
                                "prompt": prompt,
                                "prompt_template": prompt_template,
                                "id": table.get("id", "Unknown"),
                                "filename": doc.get("filename", "Unknown"),
                            }
                        )

            # Collect page images
            for page_info in data.get("extracted_pages", {}).values():
                if "enrichment_metadata" in page_info and page_info.get("url"):
                    # Handle URL that might be a dictionary or string
                    url = page_info["url"]
                    if isinstance(url, dict):
                        # Extract URL from dictionary (try both signedURL and signedUrl keys)
                        url = (
                            url.get("signedURL")
                            or url.get("signedUrl")
                            or url.get("url")
                        )

                    if url:
                        enrichment_meta = page_info.get("enrichment_metadata", {})
                        caption = enrichment_meta.get(
                            "full_page_image_caption", "No caption available"
                        )
                        prompt = enrichment_meta.get("prompt_used")
                        prompt_template = enrichment_meta.get("prompt_template")

                        all_images.append(
                            {
                                "url": url,
                                "caption": caption,
                                "prompt": prompt,
                                "prompt_template": prompt_template,
                                "page": page_info.get("structural_metadata", {}).get(
                                    "page_number", "Unknown"
                                ),
                                "filename": doc.get("filename", "Unknown"),
                            }
                        )

    # Select random samples (up to 5 each)
    selected_tables = (
        random.sample(all_tables, min(5, len(all_tables))) if all_tables else []
    )
    selected_images = (
        random.sample(all_images, min(5, len(all_images))) if all_images else []
    )

    # Display tables grid
    if selected_tables:
        st.markdown("**📊 Sample Tables:**")
        for table in selected_tables:
            col1, col2 = st.columns([1, 2])  # Image takes 1/3, caption takes 2/3
            with col1:
                try:
                    # Fetch and display image
                    response = requests.get(table["url"])
                    if response.status_code == 200:
                        image = Image.open(io.BytesIO(response.content))

                        # Create expander for full-size image
                        with st.expander(
                            f"📊 Table {table['id']} - Click to view full size",
                            expanded=False,
                        ):
                            st.image(
                                image,
                                caption=f"Table {table['id']} from {table['filename']}",
                            )

                        # Show thumbnail
                        st.image(
                            image,
                            width=200,
                            caption=f"Table {table['id']} from {table['filename']} (click expander above for full size)",
                        )

                        # Show prompt if available (underneath the image)
                        if table.get("prompt"):
                            with st.expander("🔍 View Prompt Used", expanded=False):
                                st.markdown(
                                    "**Prompt Template:** "
                                    + table.get("prompt_template", "Unknown")
                                )
                                st.markdown("**Full Prompt:**")
                                st.code(table["prompt"], language="text")
                    else:
                        st.markdown(f"❌ Could not load table image: {table['id']}")
                except Exception as e:
                    st.markdown(f"❌ Error loading table image: {e}")

            with col2:
                st.markdown(f"**Table {table['id']} from {table['filename']}**")
                st.markdown(f"**Caption:** {table['caption']}")

            st.markdown("---")  # Separator between tables

    # Display images grid
    if selected_images:
        st.markdown("**🖼️ Sample Page Images:**")
        for image_data in selected_images:
            col1, col2 = st.columns([1, 2])  # Image takes 1/3, caption takes 2/3
            with col1:
                try:
                    # Fetch and display image
                    response = requests.get(image_data["url"])
                    if response.status_code == 200:
                        image = Image.open(io.BytesIO(response.content))

                        # Create expander for full-size image
                        with st.expander(
                            f"🖼️ Page {image_data['page']} - Click to view full size",
                            expanded=False,
                        ):
                            st.image(
                                image,
                                caption=f"Page {image_data['page']} from {image_data['filename']}",
                            )

                        # Show thumbnail
                        st.image(
                            image,
                            width=200,
                            caption=f"Page {image_data['page']} from {image_data['filename']} (click expander above for full size)",
                        )

                        # Show prompt if available (underneath the image)
                        if image_data.get("prompt"):
                            with st.expander("🔍 View Prompt Used", expanded=False):
                                st.markdown(
                                    "**Prompt Template:** "
                                    + image_data.get("prompt_template", "Unknown")
                                )
                                st.markdown("**Full Prompt:**")
                                st.code(image_data["prompt"], language="text")
                    else:
                        st.markdown(
                            f"❌ Could not load page image: Page {image_data['page']}"
                        )
                except Exception as e:
                    st.markdown(f"❌ Error loading page image: {e}")

            with col2:
                st.markdown(
                    f"**Page {image_data['page']} from {image_data['filename']}**"
                )
                st.markdown(f"**Caption:** {image_data['caption']}")

            st.markdown("---")  # Separator between images
