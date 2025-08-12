import streamlit as st


def display_document_status(documents):
    """Display document status overview with timing information in a compact format"""
    st.markdown("**Document Status:**")

    # Safety check: ensure documents is a list
    if not isinstance(documents, list):
        st.error("❌ Invalid document data format")
        st.info(f"Expected list, got: {type(documents).__name__}")
        return

    # Create a more compact display using columns
    for doc in documents:
        # Safety check: ensure doc is a dictionary
        if not isinstance(doc, dict):
            st.error(f"❌ Invalid document item format: {type(doc).__name__}")
            continue

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
        if current_step and current_step != "unknown" and doc.get("indexing_status") not in ["completed", "failed"]:
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🔄 **Currently:** {current_step}")

        # Add a small separator between documents
        st.markdown("---")


def display_timing_summary(documents):
    """Display timing summary for all documents"""
    st.markdown("⏱️ Processing Timeline")

    # Safety check: ensure documents is a list
    if not isinstance(documents, list):
        st.error("❌ Invalid document data format")
        st.info(f"Expected list, got: {type(documents).__name__}")
        return

    for doc in documents:
        # Safety check: ensure doc is a dictionary
        if not isinstance(doc, dict):
            st.error(f"❌ Invalid document item format: {type(doc).__name__}")
            continue

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
                        [s for s in step_timings.keys() if step_timings[s] > 0 and s != "EmbeddingStep"]
                    )
                    progress_pct = (completed_steps / total_steps) * 100
                    st.progress(progress_pct / 100)
                    st.markdown(f"**{progress_pct:.0f}% complete** ({completed_steps}/{total_steps} steps)")
            else:
                st.markdown("⏳ No timing data available yet")
                if current_step and current_step != "unknown":
                    st.info(f"🔄 Currently processing: {current_step}")


def display_step_results(documents, step_name, step_display_name, step_icon, step_description):
    """Display results for a specific pipeline step in a compact format"""
    with st.expander(f"{step_icon} {step_display_name}", expanded=True):
        st.markdown(f"**{step_description}:**")

        # Safety check: ensure documents is a list
        if not isinstance(documents, list):
            st.error("❌ Invalid document data format")
            st.info(f"Expected list, got: {type(documents).__name__}")
            return

        for doc in documents:
            # Safety check: ensure doc is a dictionary
            if not isinstance(doc, dict):
                st.error(f"❌ Invalid document item format: {type(doc).__name__}")
                continue

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
                    # Display section detection summary
                    display_section_detection_summary(documents, step_name)

                    # Show existing page sections data
                    sample_outputs = step_result.get("sample_outputs", {})
                    headers = sample_outputs.get("page_sections", {})
                    if headers:
                        st.markdown("**📄 Page Sections Detected:**")
                        for page_num, section_title in list(headers.items())[:5]:
                            st.markdown(f"• Page {page_num}: {section_title}")
                    else:
                        st.markdown("📄 No page sections detected")

                elif step_name == "EnrichmentStep":
                    # Display image and table grid
                    display_image_table_grid(documents, step_name)

                elif step_name == "ChunkingStep":
                    summary = step_result.get("summary_stats", {})
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"✂️ Total chunks: {summary.get('total_chunks_created', 'N/A')}")
                    with col2:
                        st.markdown(f"📏 Avg chunk size: {summary.get('average_chunk_size', 'N/A')} chars")

                # Add small separator between documents
                st.markdown("---")
            else:
                st.markdown(f"**{doc.get('filename', 'Unknown')}:** No {step_name.lower()} data")
                st.markdown("---")


def display_embedding_results(run_data):
    """Display embedding results from indexing run in a compact format"""
    with st.expander("🧠 Step 5: Embedding", expanded=True):
        st.markdown("**Embedding Results:**")

        # Safety check: ensure run_data is a dictionary
        if not isinstance(run_data, dict):
            st.error("❌ Invalid run data format")
            st.info(f"Expected dict, got: {type(run_data).__name__}")
            return

        if run_data.get("step_results"):
            embedding_result = run_data["step_results"].get("embedding", {})
            if embedding_result:
                status = embedding_result.get("status", "unknown")
                summary = embedding_result.get("summary_stats", {})
                data = embedding_result.get("data", {})
                sample_outputs = embedding_result.get("sample_outputs", {})

                # Basic status and timing
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Status:** `{status}`")
                with col2:
                    duration = embedding_result.get("duration_seconds", 0)
                    st.markdown(f"**Duration:** `{duration:.2f}s`")
                with col3:
                    if embedding_result.get("started_at") and embedding_result.get("completed_at"):
                        st.markdown(f"**Completed:** `{embedding_result['completed_at'][:19]}`")

                # Main metrics
                st.markdown("**📊 Processing Metrics:**")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Chunks Processed", summary.get("total_chunks", "N/A"))
                with col2:
                    st.metric(
                        "Embeddings Generated",
                        summary.get("embeddings_generated", "N/A"),
                    )
                with col3:
                    avg_time = summary.get("average_embedding_time", 0)
                    st.metric(
                        "Avg Time/Embedding",
                        f"{avg_time:.3f}s" if avg_time > 0 else "N/A",
                    )
                with col4:
                    batch_size = summary.get("batch_size_used", "N/A")
                    st.metric("Batch Size", batch_size)

                # Model and quality information
                st.markdown("**🔧 Model & Quality:**")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    model = summary.get("embedding_model", "N/A")
                    st.markdown(f"**Model:** {model}")
                with col2:
                    dimensions = summary.get("embedding_dimensions", "N/A")
                    st.markdown(f"**Dimensions:** {dimensions}")
                with col3:
                    quality_score = summary.get("quality_score", 0)
                    # Color code quality score
                    if quality_score >= 0.8:
                        quality_color = "🟢"
                    elif quality_score >= 0.6:
                        quality_color = "🟡"
                    else:
                        quality_color = "🔴"
                    st.markdown(f"**Quality Score:** {quality_color} {quality_score:.2f}")
                with col4:
                    zero_vectors = summary.get("zero_vectors", 0)
                    st.markdown(f"**Zero Vectors:** {zero_vectors}")

                # Quality details
                if data.get("embedding_quality"):
                    quality = data["embedding_quality"]
                    st.markdown("**📈 Quality Analysis:**")

                    # Embedding statistics
                    if quality.get("embedding_stats"):
                        stats = quality["embedding_stats"]
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.markdown(f"**Mean:** {stats.get('mean', 'N/A'):.6f}")
                        with col2:
                            st.markdown(f"**Std Dev:** {stats.get('std', 'N/A'):.6f}")
                        with col3:
                            st.markdown(f"**Min:** {stats.get('min', 'N/A'):.6f}")
                        with col4:
                            st.markdown(f"**Max:** {stats.get('max', 'N/A'):.6f}")

                    # Similarity analysis
                    if quality.get("similarity_analysis"):
                        similarity = quality["similarity_analysis"]
                        col1, col2 = st.columns(2)
                        with col1:
                            self_sim = similarity.get("self_similarity_check", 0)
                            st.markdown(f"**Self-Similarity:** {self_sim:.6f}")
                        with col2:
                            first_two = similarity.get("first_two_similarity", 0)
                            st.markdown(f"**First Two Similarity:** {first_two:.6f}")

                    # Duplicate analysis
                    duplicates = quality.get("duplicate_embeddings", 0)
                    if duplicates > 0:
                        st.warning(f"⚠️ Found {duplicates} duplicate embeddings")

                # Index verification
                if data.get("index_verification"):
                    verification = data["index_verification"]
                    st.markdown("**🔍 Index Verification:**")
                    col1, col2 = st.columns(2)
                    with col1:
                        index_status = verification.get("index_status", "unknown")
                        status_icon = "✅" if index_status == "verified" else "❌"
                        st.markdown(f"**Status:** {status_icon} {index_status}")
                    with col2:
                        embeddings_found = verification.get("embeddings_found", "N/A")
                        st.markdown(f"**Embeddings Found:** {embeddings_found}")

                # Sample embeddings
                if sample_outputs.get("sample_embeddings"):
                    st.markdown("**📋 Sample Embeddings:**")
                    with st.expander("View Sample Embeddings", expanded=False):
                        for i, sample in enumerate(sample_outputs["sample_embeddings"][:3]):
                            st.markdown(f"**Sample {i + 1}:**")
                            st.markdown(f"• **Chunk ID:** `{sample.get('chunk_id', 'N/A')}`")
                            st.markdown(f"• **Content:** {sample.get('content', 'N/A')}")
                            st.markdown(f"• **Embedding:** {sample.get('embedding_preview', 'N/A')}")
                            if i < 2:  # Don't add separator after last item
                                st.markdown("---")

            else:
                st.markdown("No embedding data available")
        else:
            st.markdown("No embedding data available")


def display_section_detection_summary(documents, step_name):
    """Display section detection summary for all documents in a compact format"""
    st.markdown("**📄 Section Detection Summary:**")

    # Safety check: ensure documents is a list
    if not isinstance(documents, list):
        st.error("❌ Invalid document data format")
        st.info(f"Expected list, got: {type(documents).__name__}")
        return

    # Collect section detection data from all documents
    section_data = {}
    for doc in documents:
        # Safety check: ensure doc is a dictionary
        if not isinstance(doc, dict):
            continue

        filename = doc.get("filename", "Unknown")
        step_results = doc.get("step_results", {})
        step_result = step_results.get(step_name, {})

        if step_result and step_result.get("status") == "completed":
            sample_outputs = step_result.get("sample_outputs", {})
            page_sections = sample_outputs.get("page_sections", {})

            if page_sections:
                section_data[filename] = page_sections

    if section_data:
        # Display summary in compact format
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📊 Summary:**")
            total_docs = len(section_data)
            total_sections = sum(len(sections) for sections in section_data.values())
            st.markdown(f"• Documents with sections: {total_docs}")
            st.markdown(f"• Total sections detected: {total_sections}")

        with col2:
            st.markdown("**📄 Sample Sections:**")
            # Show first few sections from first document
            first_doc = list(section_data.keys())[0]
            first_sections = list(section_data[first_doc].items())[:3]
            for page_num, section_title in first_sections:
                st.markdown(f"• Page {page_num}: {section_title}")

        # Show detailed breakdown in expander
        with st.expander("📋 Detailed Section Breakdown", expanded=False):
            for filename, sections in section_data.items():
                st.markdown(f"**{filename}:**")
                for page_num, section_title in sections.items():
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• Page {page_num}: {section_title}")
                st.markdown("---")
    else:
        st.info("📄 No section detection data available yet")


def display_enhanced_chunking_results(documents, step_name):
    """Display enhanced chunking results for all documents in a compact format"""
    st.markdown("**✂️ Enhanced Chunking Results:**")

    # Safety check: ensure documents is a list
    if not isinstance(documents, list):
        st.error("❌ Invalid document data format")
        st.info(f"Expected list, got: {type(documents).__name__}")
        return

    # Collect chunking data from all documents
    chunking_data = {}
    for doc in documents:
        # Safety check: ensure doc is a dictionary
        if not isinstance(doc, dict):
            continue

        filename = doc.get("filename", "Unknown")
        step_results = doc.get("step_results", {})
        step_result = step_results.get(step_name, {})

        if step_result and step_result.get("status") == "completed":
            chunking_data[filename] = step_result

    if chunking_data:
        # Display summary in compact format
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📊 Summary:**")
            total_docs = len(chunking_data)
            total_chunks = sum(
                data.get("summary_stats", {}).get("total_chunks_created", 0) for data in chunking_data.values()
            )
            st.markdown(f"• Documents processed: {total_docs}")
            st.markdown(f"• Total chunks created: {total_chunks}")

        with col2:
            st.markdown("**📏 Chunking Stats:**")
            avg_chunk_size = (
                sum(data.get("summary_stats", {}).get("average_chunk_size", 0) for data in chunking_data.values())
                / len(chunking_data)
                if chunking_data
                else 0
            )
            st.markdown(f"• Average chunk size: {avg_chunk_size:.0f} chars")

        # Show detailed breakdown in expander
        with st.expander("📋 Detailed Chunking Breakdown", expanded=False):
            for filename, data in chunking_data.items():
                st.markdown(f"**{filename}:**")
                summary = data.get("summary_stats", {})
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• Total chunks: {summary.get('total_chunks_created', 'N/A')}")
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• Avg size: {summary.get('average_chunk_size', 'N/A')} chars")
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• Min size: {summary.get('min_chunk_size', 'N/A')} chars")
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• Max size: {summary.get('max_chunk_size', 'N/A')} chars")
                st.markdown("---")
    else:
        st.info("✂️ No chunking data available yet")


def display_image_table_grid(documents, step_name):
    """Display image and table grid for all documents in a compact format"""
    st.markdown("**🖼️ Image and Table Grid:**")

    # Safety check: ensure documents is a list
    if not isinstance(documents, list):
        st.error("❌ Invalid document data format")
        st.info(f"Expected list, got: {type(documents).__name__}")
        return

    # Collect image and table data from all documents
    image_data = {}
    table_data = {}

    for doc in documents:
        # Safety check: ensure doc is a dictionary
        if not isinstance(doc, dict):
            continue

        filename = doc.get("filename", "Unknown")
        step_results = doc.get("step_results", {})
        step_result = step_results.get(step_name, {})

        if step_result and step_result.get("status") == "completed":
            sample_outputs = step_result.get("sample_outputs", {})

            # Collect images
            images = sample_outputs.get("images", [])
            if images:
                image_data[filename] = images

            # Collect tables
            tables = sample_outputs.get("tables", [])
            if tables:
                table_data[filename] = tables

    # Display images
    if image_data:
        st.markdown("**🖼️ Images Detected:**")
        total_images = sum(len(images) for images in image_data.values())
        st.info(f"Found {total_images} images across {len(image_data)} documents")

        # Show first few images from first document
        first_doc = list(image_data.keys())[0]
        first_images = image_data[first_doc][:3]  # Show first 3 images

        for i, image in enumerate(first_images):
            with st.expander(f"Image {i + 1} - {image.get('page_number', 'Unknown')}", expanded=False):
                st.markdown(f"**Page:** {image.get('page_number', 'Unknown')}")
                st.markdown(f"**Caption:** {image.get('caption', 'No caption')}")
                st.markdown(f"**Type:** {image.get('type', 'Unknown')}")

                # Try to display image if base64 data is available
                if image.get("base64_data"):
                    try:
                        import base64
                        import io

                        from PIL import Image

                        img_data = base64.b64decode(image["base64_data"])
                        img = Image.open(io.BytesIO(img_data))
                        st.image(img, caption=f"Page {image.get('page_number', 'Unknown')}", use_column_width=True)
                    except Exception as e:
                        st.warning(f"Could not display image: {str(e)}")
                else:
                    st.info("No image data available for display")
    else:
        st.info("🖼️ No images detected yet")

    # Display tables
    if table_data:
        st.markdown("**📊 Tables Detected:**")
        total_tables = sum(len(tables) for tables in table_data.values())
        st.info(f"Found {total_tables} tables across {len(table_data)} documents")

        # Show first few tables from first document
        first_doc = list(table_data.keys())[0]
        first_tables = table_data[first_doc][:2]  # Show first 2 tables

        for i, table in enumerate(first_tables):
            with st.expander(f"Table {i + 1} - {table.get('page_number', 'Unknown')}", expanded=False):
                st.markdown(f"**Page:** {table.get('page_number', 'Unknown')}")
                st.markdown(f"**Caption:** {table.get('caption', 'No caption')}")
                st.markdown(f"**Rows:** {table.get('row_count', 'Unknown')}")
                st.markdown(f"**Columns:** {table.get('column_count', 'Unknown')}")

                # Try to display table data if available
                if table.get("data"):
                    try:
                        import pandas as pd

                        df = pd.DataFrame(table["data"])
                        st.dataframe(df, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Could not display table: {str(e)}")
                        st.text(
                            str(table["data"][:200]) + "..." if len(str(table["data"])) > 200 else str(table["data"])
                        )
                else:
                    st.info("No table data available for display")
    else:
        st.info("📊 No tables detected yet")
