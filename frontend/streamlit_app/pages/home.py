import streamlit as st


def show_home_page():
    """Show the home page"""
    st.markdown("## Welcome to ConstructionRAG")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### What is ConstructionRAG?")
        st.markdown(
            """
        ConstructionRAG is an AI-powered system that:
        
        - **Processes construction documents** (PDFs, plans, specifications)
        - **Generates project overviews** automatically
        - **Answers complex questions** about your construction projects
        - **Organizes information** by building systems and project phases
        
        Think of it as a **DeepWiki for Construction Sites** - just like DeepWiki analyzes code repositories, 
        we analyze construction documentation to create comprehensive project knowledge bases.
        """
        )

    with col2:
        st.markdown("### Quick Start")
        st.markdown(
            """
        1. **Upload Documents** - Start by uploading your construction PDFs
        2. **Generate Overview** - Let AI create a project summary
        3. **Ask Questions** - Query your project knowledge base
        4. **Explore Systems** - Navigate by building systems (electrical, plumbing, etc.)
        """
        )

        if st.button("🚀 Get Started", type="primary"):
            st.info("Use the sidebar navigation to upload documents and get started!")
