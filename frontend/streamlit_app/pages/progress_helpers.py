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
                    if embedding_result.get("started_at") and embedding_result.get(
                        "completed_at"
                    ):
                        st.markdown(
                            f"**Completed:** `{embedding_result['completed_at'][:19]}`"
                        )

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
                    st.markdown(
                        f"**Quality Score:** {quality_color} {quality_score:.2f}"
                    )
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
                        for i, sample in enumerate(
                            sample_outputs["sample_embeddings"][:3]
                        ):
                            st.markdown(f"**Sample {i+1}:**")
                            st.markdown(
                                f"• **Chunk ID:** `{sample.get('chunk_id', 'N/A')}`"
                            )
                            st.markdown(
                                f"• **Content:** {sample.get('content', 'N/A')}"
                            )
                            st.markdown(
                                f"• **Embedding:** {sample.get('embedding_preview', 'N/A')}"
                            )
                            if i < 2:  # Don't add separator after last item
                                st.markdown("---")

            else:
                st.markdown("No embedding data available")
        else:
            st.markdown("No embedding data available")


def display_section_detection_summary(documents, step_name):
    """Display enhanced section detection summary for metadata step"""
    if step_name != "MetadataStep":
        return

    # Collect section detection data from all documents
    all_detection_stats = []
    all_regex_patterns = {}

    for doc in documents:
        step_results = doc.get("step_results", {})
        step_result = step_results.get(step_name, {})

        if step_result and step_result.get("summary_stats"):
            summary_stats = step_result["summary_stats"]

            # Collect detection stats
            if "section_detection_stats" in summary_stats:
                all_detection_stats.append(
                    {
                        "filename": doc.get("filename", "Unknown"),
                        "stats": summary_stats["section_detection_stats"],
                    }
                )

            # Collect regex patterns (should be the same across all docs)
            if "regex_patterns_used" in summary_stats:
                all_regex_patterns = summary_stats["regex_patterns_used"]

    if not all_detection_stats:
        st.markdown("**📊 Section Detection Summary:**")
        st.info("No section detection data available")
        return

    # Aggregate stats across all documents
    total_elements = sum(
        stats["stats"]["total_elements_processed"] for stats in all_detection_stats
    )
    total_with_sections = sum(
        stats["stats"]["elements_with_section_titles"] for stats in all_detection_stats
    )

    # Aggregate detection breakdown
    detection_breakdown = {
        "category_based": sum(
            stats["stats"]["detection_breakdown"]["category_based_detected"]
            for stats in all_detection_stats
        ),
        "pattern_based": sum(
            stats["stats"]["detection_breakdown"]["pattern_based_detected"]
            for stats in all_detection_stats
        ),
        "inherited": sum(
            stats["stats"]["detection_breakdown"]["inherited_from_page"]
            for stats in all_detection_stats
        ),
    }

    # Aggregate filtering stats
    filtering_stats = {
        "diagram_contexts": sum(
            stats["stats"]["filtering_applied"]["diagram_contexts_filtered"]
            for stats in all_detection_stats
        ),
        "bullet_points": sum(
            stats["stats"]["filtering_applied"]["bullet_points_filtered"]
            for stats in all_detection_stats
        ),
        "truncated_text": sum(
            stats["stats"]["filtering_applied"]["truncated_text_filtered"]
            for stats in all_detection_stats
        ),
        "minor_elements": sum(
            stats["stats"]["filtering_applied"]["minor_elements_filtered"]
            for stats in all_detection_stats
        ),
    }

    # Collect sample detections and filtered items
    all_sample_detections = []
    all_sample_filtered = []

    for stats in all_detection_stats:
        all_sample_detections.extend(stats["stats"]["sample_detections"])
        all_sample_filtered.extend(stats["stats"]["sample_filtered"])

    # Display summary
    st.markdown("**📊 Section Detection Summary:**")

    # Detection methods used
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Elements", total_elements)
    with col2:
        st.metric("With Sections", total_with_sections)
    with col3:
        percentage = (
            (total_with_sections / total_elements * 100) if total_elements > 0 else 0
        )
        st.metric("Detection Rate", f"{percentage:.1f}%")

    # Detection breakdown
    st.markdown("**🔍 Detection Methods Used:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"✅ Category-based: {detection_breakdown['category_based']}")
    with col2:
        st.markdown(f"✅ Pattern-based: {detection_breakdown['pattern_based']}")
    with col3:
        st.markdown(f"✅ Inherited: {detection_breakdown['inherited']}")

    # Filtering applied
    st.markdown("**🚫 Filtering Applied:**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"❌ Diagram contexts: {filtering_stats['diagram_contexts']}")
    with col2:
        st.markdown(f"❌ Bullet points: {filtering_stats['bullet_points']}")
    with col3:
        st.markdown(f"❌ Truncated text: {filtering_stats['truncated_text']}")
    with col4:
        st.markdown(f"❌ Minor elements: {filtering_stats['minor_elements']}")

    # Regex patterns
    if all_regex_patterns:
        st.markdown("**📋 Regex Patterns Applied:**")
        with st.expander("View Regex Patterns", expanded=False):
            for pattern_name, pattern in all_regex_patterns.items():
                st.markdown(f"**{pattern_name}:**")
                st.code(pattern, language="regex")

    # Sample detections
    if all_sample_detections:
        st.markdown("**✅ Sample Detections:**")
        for detection in all_sample_detections[:3]:  # Show first 3
            method_icon = (
                "🏷️" if detection["detection_method"] == "category_based" else "🔍"
            )
            st.markdown(
                f"{method_icon} **{detection['text']}** ({detection['detection_method']}, {detection['confidence']})"
            )

    # Sample filtered items
    if all_sample_filtered:
        st.markdown("**❌ Sample Filtered Items:**")
        for filtered in all_sample_filtered[:3]:  # Show first 3
            st.markdown(
                f"🚫 **{filtered['text']}** (filtered: {filtered['filter_reason']})"
            )

    # Section header distribution overview
    st.markdown("**📑 Section Header Distribution:**")

    # Collect all section headers from all documents
    section_header_counts = {}

    for doc in documents:
        step_results = doc.get("step_results", {})
        step_result = step_results.get(step_name, {})

        if step_result and step_result.get("data"):
            data = step_result["data"]

            # Count section headers from all elements
            for element in data.get("text_elements", []):
                structural_meta = element.get("structural_metadata", {})

                # Check all possible section title fields
                section_title = (
                    structural_meta.get("section_title_inherited")
                    or structural_meta.get("section_title_pattern")
                    or structural_meta.get("section_title_category")
                )

                if section_title:
                    section_header_counts[section_title] = (
                        section_header_counts.get(section_title, 0) + 1
                    )

            # Also count from table elements
            for element in data.get("table_elements", []):
                structural_meta = element.get("structural_metadata", {})

                section_title = (
                    structural_meta.get("section_title_inherited")
                    or structural_meta.get("section_title_pattern")
                    or structural_meta.get("section_title_category")
                )

                if section_title:
                    section_header_counts[section_title] = (
                        section_header_counts.get(section_title, 0) + 1
                    )

    # Display section header distribution
    if section_header_counts:
        # Sort by count descending
        sorted_headers = sorted(
            section_header_counts.items(), key=lambda x: x[1], reverse=True
        )

        # Show all section headers with their counts
        for section_title, count in sorted_headers:
            st.markdown(f"• **{section_title}**: {count} elements")

        # Show summary
        total_unique_sections = len(section_header_counts)
        total_elements_with_sections = sum(section_header_counts.values())
        st.markdown(
            f"**📊 Summary:** {total_unique_sections} unique sections, {total_elements_with_sections} total elements with sections"
        )
    else:
        st.info("No section headers found in the processed elements")


def display_enhanced_chunking_results(documents, step_name):
    """Display enhanced chunking results with examples and quality metrics"""
    if step_name != "ChunkingStep":
        return

    # Collect chunking data from all documents
    all_chunking_data = []

    for doc in documents:
        step_results = doc.get("step_results", {})
        step_result = step_results.get(step_name, {})

        if step_result and step_result.get("summary_stats"):
            all_chunking_data.append(
                {
                    "filename": doc.get("filename", "Unknown"),
                    "summary_stats": step_result["summary_stats"],
                    "sample_outputs": step_result.get("sample_outputs", {}),
                }
            )

    if not all_chunking_data:
        st.info("No chunking data available")
        return

    # Display basic statistics
    st.markdown("**📊 Chunking Statistics:**")

    # Get first document for detailed analysis (for simplicity)
    first_doc = all_chunking_data[0]

    # Aggregate basic stats across all documents
    total_chunks = sum(
        data["summary_stats"].get("total_chunks_created", 0)
        for data in all_chunking_data
    )
    avg_chunk_size = (
        sum(
            data["summary_stats"].get("average_chunk_size", 0)
            for data in all_chunking_data
        )
        / len(all_chunking_data)
        if all_chunking_data
        else 0
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Chunks", total_chunks)
    with col2:
        st.metric("Avg Chunk Size", f"{avg_chunk_size:.0f} chars")
    with col3:
        st.metric("Documents Processed", len(all_chunking_data))
    with col4:
        very_small = first_doc["summary_stats"].get("very_small_chunks", 0)
        st.metric("Chunks < 150 chars", very_small, delta=None)
    with col5:
        very_large = first_doc["summary_stats"].get("very_large_chunks", 0)
        st.metric("Chunks > 750 chars", very_large, delta=None)

    # Display validation results
    st.markdown("**🔍 Validation Results:**")
    validation_results = all_chunking_data[0]["summary_stats"].get(
        "validation_results", {}
    )
    if validation_results:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Empty Chunks", validation_results.get("empty_chunks", 0))
        with col2:
            st.metric("Missing Metadata", validation_results.get("missing_metadata", 0))
        with col3:
            st.metric(
                "Missing Section Titles",
                validation_results.get("missing_section_title", 0),
            )

    # Display section headers distribution
    st.markdown("**📑 Section Headers Distribution:**")
    section_headers_distribution = first_doc["summary_stats"].get(
        "section_headers_distribution", {}
    )
    if section_headers_distribution:
        # Sort by count descending
        sorted_headers = sorted(
            section_headers_distribution.items(), key=lambda x: x[1], reverse=True
        )

        # Show top 10 section headers
        st.markdown("**Top Section Headers:**")
        for i, (header, count) in enumerate(sorted_headers[:10]):
            st.markdown(f"• **{header}**: {count} chunks")

        # Show total unique sections
        st.markdown(f"**Total unique sections:** {len(section_headers_distribution)}")

    # Display shortest and longest chunks
    st.markdown("**📏 Chunk Size Analysis:**")

    # Get shortest and longest chunks from first document (for simplicity)
    shortest_chunks = first_doc["summary_stats"].get("shortest_chunks", [])
    longest_chunks = first_doc["summary_stats"].get("longest_chunks", [])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🔽 Shortest Chunks:**")
        for i, chunk in enumerate(shortest_chunks[:3]):
            with st.expander(
                f"Chunk {i+1} ({chunk.get('size', 0)} chars) - {chunk.get('type', 'Unknown')}",
                expanded=False,
            ):
                st.markdown(f"**Page:** {chunk.get('page', 'Unknown')}")
                st.markdown(f"**Type:** {chunk.get('type', 'Unknown')}")
                st.markdown("**Full Content:**")
                st.text(chunk.get("content", "No content"))

    with col2:
        st.markdown("**🔼 Longest Chunks:**")
        for i, chunk in enumerate(longest_chunks[:3]):
            with st.expander(
                f"Chunk {i+1} ({chunk.get('size', 0)} chars) - {chunk.get('type', 'Unknown')}",
                expanded=False,
            ):
                st.markdown(f"**Page:** {chunk.get('page', 'Unknown')}")
                st.markdown(f"**Type:** {chunk.get('type', 'Unknown')}")
                st.markdown("**Full Content:**")
                st.text(chunk.get("content", "No content"))

    # Display chunk type distribution with examples (excluding list chunks)
    st.markdown("**📋 Chunk Type Distribution:**")
    chunk_type_examples = first_doc["summary_stats"].get("chunk_type_examples", {})
    chunk_type_distribution = first_doc["summary_stats"].get(
        "chunk_type_distribution", {}
    )

    for chunk_type, count in chunk_type_distribution.items():
        # Skip list chunks as they're shown in list grouping statistics
        if chunk_type.lower() == "list":
            continue

        with st.expander(f"{chunk_type} ({count} chunks)", expanded=False):
            examples = chunk_type_examples.get(chunk_type, [])
            for i, example in enumerate(examples[:2]):  # Show 2 examples per type
                st.markdown(f"**Example {i+1}:**")
                st.markdown(f"**Page:** {example.get('page_number', 'Unknown')}")
                st.markdown(f"**Section:** {example.get('section_title', 'Unknown')}")
                st.markdown(f"**Size:** {example.get('size', 0)} chars")
                st.markdown("**Content:**")
                st.text(example.get("content", "No content"))
                if i < len(examples[:2]) - 1:  # Don't add separator after last item
                    st.markdown("---")

    # Display list grouping statistics
    st.markdown("**📝 List Grouping Statistics:**")
    list_grouping_stats = first_doc["summary_stats"].get("list_grouping_stats", {})
    if list_grouping_stats:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Groups Created", list_grouping_stats.get("groups_created", 0))
        with col2:
            st.metric(
                "List Items Grouped",
                list_grouping_stats.get("total_list_items_grouped", 0),
            )
        with col3:
            success_rate = list_grouping_stats.get("grouping_success_rate", 0)
            st.metric("Success Rate", f"{success_rate}%")

        # Show list grouping examples
        group_examples = list_grouping_stats.get("group_examples", [])
        if group_examples:
            st.markdown("**📝 List Grouping Examples:**")
            for i, example in enumerate(group_examples[:2]):
                with st.expander(
                    f"Group Example {i+1} - {example.get('total_list_items', 0)} items",
                    expanded=False,
                ):
                    st.markdown(f"**Page:** {example.get('page_number', 'Unknown')}")
                    st.markdown(
                        f"**Section:** {example.get('section_title', 'Unknown')}"
                    )
                    st.markdown("**Narrative Text:**")
                    st.text(example.get("narrative_text", "No narrative text"))
                    st.markdown("**List Items:**")
                    for j, item in enumerate(example.get("list_items", [])):
                        st.markdown(f"• {item}")

    # Display noise filtering statistics
    st.markdown("**🚫 Noise Filtering Statistics:**")
    noise_filtering_stats = first_doc["summary_stats"].get("noise_filtering_stats", {})
    if noise_filtering_stats:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Elements", noise_filtering_stats.get("total_elements", 0))
        with col2:
            st.metric("Filtered Out", noise_filtering_stats.get("filtered_out", 0))
        with col3:
            filtered_by_length = noise_filtering_stats.get("filtered_by_length", 0)
            st.metric("Too Short", filtered_by_length)

        # Show filtered elements examples
        filtered_elements = noise_filtering_stats.get("filtered_elements", [])
        if filtered_elements:
            st.markdown("**🚫 Filtered Elements Examples:**")
            for i, filtered in enumerate(filtered_elements[:3]):
                with st.expander(
                    f"Filtered {i+1} - {filtered.get('category', 'Unknown')}",
                    expanded=False,
                ):
                    st.markdown(f"**Category:** {filtered.get('category', 'Unknown')}")
                    st.markdown(f"**Reason:** {filtered.get('reason', 'Unknown')}")
                    st.markdown("**Content:**")
                    st.text(filtered.get("content", "No content"))


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
