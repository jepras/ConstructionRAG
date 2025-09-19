"""Analyzer step for checklist analysis pipeline."""

import logging
from typing import Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


def create_llm_client(model_name: str) -> ChatOpenAI:
    """Create LangChain ChatOpenAI client configured for OpenRouter."""
    settings = get_settings()

    return ChatOpenAI(
        model=model_name,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={"HTTP-Referer": "https://specfinder.io"},
        temperature=0.1,
        max_tokens=4000,
        timeout=60000,  # 60 seconds in milliseconds
    )


async def call_llm(llm_client: ChatOpenAI, prompt: str) -> str:
    """Make async LLM call following existing patterns."""
    message = HumanMessage(content=prompt)
    response = await llm_client.ainvoke([message], config={"run_name": "analyzer"})
    return response.content


async def analyze_checklist_with_chunks(
    parsed_items: List[Dict[str, Any]], chunks: List[Dict[str, Any]], language: str, model_name: str
) -> str:
    """
    LLM2: Analyze retrieved chunks against original checklist.
    Returns raw analysis text.
    """
    try:
        llm_client = create_llm_client(model_name)

        # Format chunks for LLM with proper document citations (no excerpt numbers)
        formatted_chunks = []
        for i, chunk in enumerate(chunks[:50]):  # Limit to avoid token limits
            content = chunk.get("content", "")
            document_id = chunk.get("document_id", "unknown")

            # Extract page number from metadata
            metadata_chunk = chunk.get("metadata", {})
            page_number = metadata_chunk.get("page_number", "N/A") if metadata_chunk else "N/A"

            # Extract document name from metadata if available
            doc_name = (
                metadata_chunk.get("document_name", f"document_{document_id[:8]}")
                if metadata_chunk
                else f"document_{document_id[:8]}"
            )

            # Format with actual document reference instead of excerpt numbers
            formatted_chunk = f"""
From {doc_name}, Page {page_number}:
{content[:800]}..."""
            formatted_chunks.append(formatted_chunk)

        chunks_text = "\n".join(formatted_chunks)

        language_names = {"english": "English", "danish": "Danish"}
        output_language = language_names.get(language, "English")

        # Format parsed items for reference
        items_text = "\n".join([f"{item['number']}. {item['name']}: {item['description']}" for item in parsed_items])

        prompt = f"""Analyze the construction documents against this checklist.

You are a construction professional reviewing project documents to verify compliance with a checklist.

For each checklist item, provide a status:
- Status: FOUND/MISSING/PARTIALLY_FOUND
  - FOUND: Information is present and complete in the documents
  - MISSING: Required information is absent from the documents
  - PARTIALLY_FOUND: Information exists but presents potential risks or concerns. Information is unclear or requires further review. 

For each checklist item, provide also a description:
- A description of what was found or what is missing. If possible, provide the answer to the checklist item. 
- When citing sources, reference the actual document name and page number (e.g., "specifications.pdf, Page 12")

IMPORTANT: When referencing information, cite the specific document name and page number directly 
(e.g., "As specified in drawings.pdf, Page 5" or "According to manual.pdf, Page 23").
Do NOT use phrases like "Document Excerpt" or "Excerpt 1" - use the actual document names.

Write your analysis in {output_language} as detailed text. 
Structure your response by going through each checklist item in order.

Checklist Items to Analyze:
{items_text}

Retrieved Document Excerpts:
{chunks_text}

Be thorough and specific in your findings with proper document citations."""

        response = await call_llm(llm_client, prompt)
        logger.info(f"Analysis completed for {len(parsed_items)} checklist items")

        return response

    except Exception as e:
        logger.error(f"Error in checklist analysis: {e}")
        raise
