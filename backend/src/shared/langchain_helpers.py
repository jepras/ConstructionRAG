"""Shared LangChain utilities for consistent tracing and LLM client creation."""

import logging
from typing import Optional, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


def create_llm_client(model_name: str, max_tokens: int = 4000, temperature: float = 0.1) -> ChatOpenAI:
    """
    Create standardized LangChain ChatOpenAI client configured for OpenRouter.
    
    Used across all pipeline steps for consistent configuration and tracing.
    """
    settings = get_settings()
    
    return ChatOpenAI(
        model=model_name,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={"HTTP-Referer": "https://specfinder.io"},
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
    message = HumanMessage(content=prompt)
    
    # Build config with run name and optional metadata
    config = {"run_name": run_name}
    if metadata:
        config["metadata"] = metadata
    
    response = await llm_client.ainvoke([message], config=config)
    return response.content


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
        config["metadata"] = metadata
        
    response = await structured_llm.ainvoke([message], config=config)
    return response