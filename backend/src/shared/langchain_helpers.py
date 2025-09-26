"""Shared LangChain utilities for consistent tracing and LLM client creation."""

import logging
from typing import Optional, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from src.config.settings import get_settings
from src.constants import ANONYMOUS_USER_ID

logger = logging.getLogger(__name__)


def create_llm_client(model_name: str, max_tokens: int = 4000, temperature: float = 0.1) -> ChatOpenAI:
    """
    Create standardized LangChain ChatOpenAI client configured for OpenRouter.

    Used across all pipeline steps for consistent configuration and tracing.
    """
    settings = get_settings()

    # OpenRouter requires both HTTP-Referer and X-Title headers
    return ChatOpenAI(
        model=model_name,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://specfinder.io",
            "X-Title": "Construction RAG"
        },
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=60000,  # 60 seconds in milliseconds
    )


async def call_llm_with_tracing(
    llm_client: ChatOpenAI,
    prompt: str,
    run_name: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Make async LLM call with standardized tracing configuration.

    Args:
        llm_client: Configured ChatOpenAI client
        prompt: The prompt to send to the LLM
        run_name: Name for the LangSmith trace (e.g., "overview_generator", "structurer")
        metadata: Optional metadata to include in the trace

    Returns:
        The LLM response content
    """
    import os

    # Check if LangSmith tracing is enabled
    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"

    logger.info(f"[LangChain] call_llm_with_tracing - run_name: {run_name}")
    logger.info(f"[LangChain] LangSmith tracing enabled: {tracing_enabled}")
    logger.info(f"[LangChain] Original metadata: {metadata}")

    message = HumanMessage(content=prompt)

    # Build config with run name and optional metadata
    config = {"run_name": run_name}

    # Only add metadata if tracing is enabled and we have metadata
    if tracing_enabled and metadata:
        # Filter out anonymous user data that external services don't recognize
        filtered_metadata = _filter_anonymous_user_metadata(metadata)
        logger.info(f"[LangChain] Filtered metadata: {filtered_metadata}")
        if filtered_metadata:
            config["metadata"] = filtered_metadata
    elif not tracing_enabled:
        logger.info("[LangChain] Skipping metadata since tracing is disabled")

    try:
        response = await llm_client.ainvoke([message], config=config)
        logger.info(f"[LangChain] LLM call successful for {run_name}")
        return response.content
    except Exception as e:
        logger.error(f"[LangChain] LLM call failed for {run_name}: {e}")
        raise


def create_structured_llm_with_tracing(
    model_name: str, 
    response_model,
    max_tokens: int = 8000,
    temperature: float = 0.1
):
    """
    Create LangChain structured output LLM client for consistent tracing.
    
    Args:
        model_name: The model to use (e.g., "google/gemini-2.5-flash-lite")
        response_model: Pydantic model for structured output
        max_tokens: Maximum tokens for the response
        temperature: Temperature for the LLM
        
    Returns:
        Structured LLM client configured for tracing
    """
    llm_client = create_llm_client(model_name, max_tokens, temperature)
    return llm_client.with_structured_output(response_model)


async def call_structured_llm_with_tracing(
    structured_llm,
    prompt: str,
    run_name: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Make async structured LLM call with standardized tracing.

    Args:
        structured_llm: LLM client configured with structured output
        prompt: The prompt to send to the LLM
        run_name: Name for the LangSmith trace
        metadata: Optional metadata to include in the trace

    Returns:
        The structured response object
    """
    message = HumanMessage(content=prompt)

    # Build config with run name and optional metadata
    config = {"run_name": run_name}
    if metadata:
        # Filter out anonymous user data that external services don't recognize
        filtered_metadata = _filter_anonymous_user_metadata(metadata)
        if filtered_metadata:
            config["metadata"] = filtered_metadata

    response = await structured_llm.ainvoke([message], config=config)
    return response


def _filter_anonymous_user_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out anonymous user data from metadata to prevent external service conflicts.

    Args:
        metadata: Original metadata dictionary

    Returns:
        Filtered metadata without anonymous user references
    """
    if not metadata:
        return metadata

    filtered = metadata.copy()

    # Remove or replace anonymous user-specific fields that cause external service conflicts
    fields_to_filter = ['user_id', 'userId', 'user', 'account_id', 'accountId']

    for field in fields_to_filter:
        if field in filtered and filtered[field] == ANONYMOUS_USER_ID:
            # Replace with generic identifier or remove entirely
            filtered[field] = "anonymous_session"
            logger.debug(f"Filtered anonymous user ID from tracing metadata field: {field}")

    # Also handle nested user objects
    if 'user' in filtered and isinstance(filtered['user'], dict):
        user_obj = filtered['user']
        if user_obj.get('id') == ANONYMOUS_USER_ID:
            filtered['user'] = {
                **user_obj,
                'id': 'anonymous_session',
                'type': 'anonymous'
            }
            logger.debug("Filtered anonymous user object from tracing metadata")

    return filtered