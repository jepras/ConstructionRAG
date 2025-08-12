import streamlit as st


def show_settings_page():
    """Show the settings page"""
    st.markdown("## Settings")
    st.markdown("Configure your ConstructionRAG application.")

    # Configuration options
    st.markdown("### Pipeline Configuration")

    col1, col2 = st.columns(2)

    with col1:
        chunk_size = st.slider("Chunk Size", 500, 2000, 1000, 100)
        chunk_overlap = st.slider("Chunk Overlap", 0, 500, 200, 50)

    with col2:
        embedding_model = st.selectbox(
            "Embedding Model",
            ["voyage-large-2", "text-embedding-ada-002", "all-MiniLM-L6-v2"],
        )
        similarity_threshold = st.slider("Similarity Threshold", 0.0, 1.0, 0.7, 0.05)

    if st.button("💾 Save Settings", type="primary"):
        st.success("Settings saved successfully!")
