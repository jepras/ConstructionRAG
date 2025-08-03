import streamlit as st
import requests
import logging
from utils.shared import get_backend_url

logger = logging.getLogger(__name__)


def show_query_page():
    """Show the query interface page"""
    st.markdown("## Query Your Project")
    st.markdown(
        "Ask questions about your construction project and get AI-powered answers."
    )

    # Check authentication first
    from components import require_auth_decorator

    auth_manager = st.session_state.auth_manager

    if not auth_manager.is_authenticated():
        st.error("🔐 Please sign in to access the query interface.")
        st.info("Use the sidebar to navigate to the Authentication page.")
        return

    # Show user info
    user_info = auth_manager.get_current_user()
    if user_info and user_info.get("user"):
        user = user_info["user"]
        st.success(f"✅ Signed in as: {user.get('email', 'N/A')}")

    # Load available indexing runs
    try:
        backend_url = get_backend_url()
        access_token = st.session_state.get("access_token")

        if not access_token:
            st.error("❌ No access token found. Please sign in again.")
            return

        headers = {"Authorization": f"Bearer {access_token}"}

        # Get all indexing runs
        response = requests.get(
            f"{backend_url}/api/pipeline/indexing/runs", headers=headers, timeout=10
        )

        if response.status_code == 200:
            indexing_runs = response.json()

            # Show all runs for debugging (not just completed ones)
            all_runs = indexing_runs

            if all_runs:
                st.markdown("### 📄 Available Processed Documents")

                # Create dropdown for indexing run selection
                run_options = []
                for run in all_runs:
                    upload_type = run.get("upload_type", "unknown")
                    upload_id = run.get("upload_id", "N/A")
                    started_at = run.get("started_at", "Unknown")

                    # Format the display name
                    if upload_type == "email":
                        display_name = (
                            f"Email Upload ({upload_id[:8]}...) - {started_at[:10]}"
                        )
                    else:
                        display_name = f"Project Document - {started_at[:10]}"

                    run_options.append((display_name, run["id"]))

                if run_options:
                    selected_run_display, selected_run_id = st.selectbox(
                        "Choose a processed document to query:",
                        options=run_options,
                        format_func=lambda x: x[0],
                        help="Select a document that has been processed and is ready for querying",
                    )

                    st.success(f"✅ Selected: {selected_run_display}")

                    # Query input
                    st.markdown("---")
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
                                            "indexing_run_id": selected_run_id,
                                        },
                                        headers=headers,
                                        timeout=30,
                                    )

                                    if query_response.status_code == 200:
                                        result = query_response.json()
                                        st.success("✅ Answer found!")

                                        # Display the response
                                        st.markdown("### Answer:")
                                        st.write(
                                            result.get(
                                                "response", "No response received"
                                            )
                                        )

                                        # Display metadata if available
                                        if result.get("search_results"):
                                            st.markdown("### Sources:")
                                            for i, source in enumerate(
                                                result["search_results"],
                                                1,  # Show all sources, not just first 3
                                            ):
                                                # Extract source information
                                                content = source.get("content", "")
                                                page_number = source.get(
                                                    "page_number", "N/A"
                                                )
                                                source_filename = source.get(
                                                    "source_filename", "Unknown"
                                                )
                                                similarity_score = source.get(
                                                    "similarity_score", 0.0
                                                )

                                                # Determine content type based on metadata
                                                content_type = "Text"
                                                if (
                                                    source.get("metadata", {}).get(
                                                        "element_category"
                                                    )
                                                    == "ExtractedPage"
                                                ):
                                                    content_type = "Image"
                                                elif (
                                                    source.get("metadata", {}).get(
                                                        "element_category"
                                                    )
                                                    == "List"
                                                ):
                                                    content_type = "List"

                                                # Create a snippet (first line + next 50 chars)
                                                lines = content.split("\n")
                                                first_line = lines[0] if lines else ""
                                                snippet = first_line
                                                if len(content) > len(first_line) + 50:
                                                    snippet += (
                                                        " "
                                                        + content[
                                                            len(first_line) : len(
                                                                first_line
                                                            )
                                                            + 50
                                                        ].strip()
                                                        + "..."
                                                    )

                                                # Format similarity score as percentage
                                                similarity_percent = (
                                                    f"{similarity_score * 100:.1f}%"
                                                )

                                                # Calculate content length
                                                content_length = len(content)
                                                content_length_str = (
                                                    f"{content_length:,} chars"
                                                )

                                                # Create expandable source with summary
                                                with st.expander(
                                                    f"📄 **{page_number}** | **{content_type}** | **{similarity_percent}** | **{content_length_str}** | {snippet}",
                                                    expanded=False,
                                                ):
                                                    # Show full content
                                                    st.markdown("**Full Content:**")
                                                    st.text_area(
                                                        f"Source {i} Content",
                                                        value=content,
                                                        height=200,
                                                        key=f"source_content_{i}",
                                                        disabled=True,
                                                    )

                                        if result.get("performance_metrics"):
                                            st.markdown("### Performance:")
                                            st.json(result["performance_metrics"])

                                            # Display step timings if available
                                            if result.get("step_timings"):
                                                st.markdown("### Step Timings:")
                                                step_timings = result["step_timings"]
                                                for (
                                                    step,
                                                    duration,
                                                ) in step_timings.items():
                                                    st.text(
                                                        f"• {step.replace('_', ' ').title()}: {duration:.2f}s"
                                                    )

                                                # Calculate total from step timings
                                                total_steps = sum(step_timings.values())
                                                st.text(
                                                    f"• Total Pipeline Steps: {total_steps:.2f}s"
                                                )

                                                # Show overhead (difference between total and step sum)
                                                total_time = (
                                                    result["performance_metrics"].get(
                                                        "response_time_ms", 0
                                                    )
                                                    / 1000
                                                )
                                                overhead = total_time - total_steps
                                                if overhead > 0:
                                                    st.text(
                                                        f"• Overhead (DB, network, etc.): {overhead:.2f}s"
                                                    )

                                    else:
                                        st.error(
                                            f"❌ Query failed: {query_response.status_code}"
                                        )
                                        st.text(f"Response: {query_response.text}")

                                except Exception as e:
                                    st.error(f"❌ Query failed: {str(e)}")
                        else:
                            st.warning("Please enter a question.")
                else:
                    st.info("No completed indexing runs found.")
            else:
                st.info(
                    "📄 No processed documents found. Upload and process documents first."
                )

        else:
            st.error(f"❌ Failed to load indexing runs: {response.status_code}")

    except Exception as e:
        logger.error(f"❌ Error loading indexing runs: {str(e)}")
        st.error(f"❌ Error loading indexing runs: {str(e)}")

    # Test buttons for debugging
    st.markdown("---")
    st.markdown("### 🧪 Debug: Test APIs")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Test Indexing Runs API", type="secondary"):
            try:
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }

                response = requests.get(
                    f"{backend_url}/api/pipeline/indexing/runs",
                    headers=headers,
                    timeout=10,
                )

                if response.status_code == 200:
                    runs = response.json()
                    st.success(f"✅ Indexing Runs API working! Found {len(runs)} runs")
                    st.json(runs[:2])  # Show first 2 runs
                else:
                    st.error(f"❌ Indexing Runs API error: {response.status_code}")
                    st.text(f"Response: {response.text}")
            except Exception as e:
                st.error(f"❌ Indexing Runs API failed: {str(e)}")

    with col2:
        if st.button("Test Query API", type="secondary"):
            try:
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }

                response = requests.post(
                    f"{backend_url}/api/query/",
                    json={"query": "What is this construction project about?"},
                    headers=headers,
                    timeout=10,
                )

                if response.status_code == 200:
                    st.success("✅ Query API working!")
                    st.json(response.json())
                else:
                    st.error(f"❌ Query API error: {response.status_code}")
                    st.text(f"Response: {response.text}")
            except Exception as e:
                st.error(f"❌ Query API failed: {str(e)}")
