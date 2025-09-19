"""Query generator step for checklist analysis pipeline."""

import json
import logging
import re
from typing import Dict, Any

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
        max_tokens=2000,
        timeout=30000,  # 30 seconds in milliseconds
    )


async def call_llm(llm_client: ChatOpenAI, prompt: str) -> str:
    """Make async LLM call following existing patterns."""
    message = HumanMessage(content=prompt)
    response = await llm_client.ainvoke([message], config={"run_name": "query_generator"})
    return response.content


async def generate_queries_from_checklist(checklist_content: str, language: str, model_name: str) -> Dict[str, Any]:
    """
    LLM1: Parse checklist and generate search queries.

    Returns:
    {
        "items": [{"number": "1.1", "name": "...", "description": "..."}],
        "queries": ["query1", "query2", ...]
    }
    """
    try:
        llm_client = create_llm_client(model_name)

        language_names = {"english": "English", "danish": "Danish"}
        output_language = language_names.get(language, "English")

        prompt = f"""Parse this construction checklist and generate search queries.

For each checklist item, create 1-3 specific search queries that would find relevant information in construction documents.

Focus on creating queries that would retrieve:
- Technical specifications
- Requirements and standards
- Installation details
- Safety and compliance information
- Material properties and requirements
- Quality control measures

Checklist:
{checklist_content}

Output in {output_language} as JSON:
{{
    "items": [
        {{"number": "1", "name": "Item name", "description": "What to look for"}},
        {{"number": "2", "name": "Another item", "description": "What to verify"}},
        ...
    ],
    "queries": [
        "specific search query 1",
        "specific search query 2",
        "specific search query 3",
        ...
    ]
}}

Ensure:
- Item numbers match the checklist structure (can be simple numbers like 1, 2, 3 or nested like 1.1, 1.2)
- Queries are specific enough to find relevant technical information
- Queries are broad enough to catch related content
- If it is a simple item, just create 1 query. If it is a broader item, then generate 3 queries. 
- Output is valid JSON"""

        response = await call_llm(llm_client, prompt)
        logger.info(f"Query generation completed for checklist with {len(checklist_content)} chars")

        try:
            # Try to parse as JSON directly
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback: extract JSON from response
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                logger.error("Failed to parse LLM response as JSON")
                # Return a minimal valid structure
                return {
                    "items": [{"number": "1", "name": "Checklist", "description": checklist_content[:200]}],
                    "queries": [checklist_content[:100]],
                }

    except Exception as e:
        logger.error(f"Error in query generation: {e}")
        raise
