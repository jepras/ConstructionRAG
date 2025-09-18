"""Structurer step for checklist analysis pipeline."""

import json
import logging
import re
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class ChecklistItemStatus(str, Enum):
    """Enum for checklist item status values."""
    FOUND = "found"
    MISSING = "missing"
    RISK = "risk"
    CONDITIONS = "conditions"
    PENDING_CLARIFICATION = "pending_clarification"


class ChecklistSourceReference(BaseModel):
    """Individual source reference for a checklist item."""
    document: str = Field(description="Document name (e.g., 'specifications.pdf')")
    page: int = Field(description="Page number in the document")
    excerpt: str | None = Field(default=None, description="Short relevant quote from this source")


class ChecklistItemResult(BaseModel):
    """Pydantic model for a single checklist item result."""
    item_number: str = Field(description="The item number (e.g., '1', '2', etc.)")
    item_name: str = Field(description="The name/title of the checklist item")
    status: ChecklistItemStatus = Field(description="The compliance status of the item")
    description: str = Field(description="Detailed description of findings for this item")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    sources: List[ChecklistSourceReference] = Field(default_factory=list, description="List of source references supporting this finding")


class ChecklistAnalysisStructuredResult(BaseModel):
    """Pydantic model for the complete checklist analysis result."""
    results: List[ChecklistItemResult] = Field(description="List of structured results for each checklist item")


def clean_result_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and validate a single result item."""
    valid_statuses = ["found", "missing", "risk", "conditions", "pending_clarification"]
    
    # Ensure status is valid
    status = item.get("status", "").lower()
    if status not in valid_statuses:
        status = "missing"
    
    # Ensure confidence score is valid
    confidence_score = item.get("confidence_score")
    if confidence_score is not None:
        try:
            score = float(confidence_score)
            confidence_score = max(0.0, min(1.0, score))
        except (ValueError, TypeError):
            confidence_score = None
    
    # Clean string fields
    def clean_string(value):
        if value is None or (isinstance(value, str) and value.lower() in ["null", "none", ""]):
            return None
        return str(value) if value is not None else None
    
    # Ensure page number is valid
    source_page = item.get("source_page")
    if source_page is not None:
        try:
            source_page = int(source_page)
        except (ValueError, TypeError):
            source_page = None
    
    return {
        "item_number": str(item.get("item_number", "1")),
        "item_name": clean_string(item.get("item_name", "Unknown")),
        "status": status,
        "description": clean_string(item.get("description", "No description available")),
        "confidence_score": confidence_score,
        "source_document": clean_string(item.get("source_document")),
        "source_page": source_page,
        "source_excerpt": clean_string(item.get("source_excerpt"))
    }


def create_fallback_results(parsed_items: List[Dict[str, Any]], error_msg: str) -> List[Dict[str, Any]]:
    """Create fallback results when parsing fails."""
    fallback_results = []
    for item in parsed_items:
        fallback_results.append({
            "item_number": item.get("number", "1"),
            "item_name": item.get("name", "Unknown"),
            "status": "pending_clarification",
            "description": error_msg,
            "confidence_score": 0.0,
            "source_document": None,
            "source_page": None,
            "source_excerpt": None
        })
    return fallback_results


def create_llm_client(model_name: str) -> ChatOpenAI:
    """Create LangChain ChatOpenAI client configured for OpenRouter."""
    settings = get_settings()
    
    return ChatOpenAI(
        model=model_name,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={"HTTP-Referer": "https://specfinder.io"},
        temperature=0.1,
        max_tokens=8000,  # Increased for structured output
        timeout=60000,  # 60 seconds in milliseconds
    )


async def call_llm(llm_client: ChatOpenAI, prompt: str) -> str:
    """Make async LLM call following existing patterns."""
    message = HumanMessage(content=prompt)
    response = await llm_client.ainvoke([message])
    return response.content


async def structure_analysis_output(
    raw_analysis: str,
    parsed_items: List[Dict[str, Any]],
    language: str,
    model_name: str
) -> List[Dict[str, Any]]:
    """
    LLM3: Convert raw analysis to structured format using LangChain structured output.
    Returns list of structured results for database storage.
    """
    try:
        # First try LangChain's structured output approach (recommended for 2024)
        try:
            structured_results = await _structure_with_langchain_structured_output(
                raw_analysis, parsed_items, language, model_name
            )
            logger.info(f"✅ LangChain structured output successful for {len(structured_results)} items")
            return structured_results
        except Exception as e:
            logger.warning(f"LangChain structured output failed: {e}")
            
        # Fallback to robust JSON parsing (based on wiki generation patterns)
        try:
            json_results = await _structure_with_robust_json_parsing(
                raw_analysis, parsed_items, language, model_name
            )
            logger.info(f"✅ Robust JSON parsing successful for {len(json_results)} items")
            return json_results
        except Exception as e:
            logger.warning(f"Robust JSON parsing failed: {e}")
            
        # Final fallback
        logger.error("All structuring approaches failed. Creating fallback structure.")
        return create_fallback_results(parsed_items, "Analysis could not be structured properly. Please review raw output.")
                
    except Exception as e:
        logger.error(f"Error structuring analysis output: {e}")
        return create_fallback_results(parsed_items, f"Error during structuring: {str(e)}")


async def _structure_with_langchain_structured_output(
    raw_analysis: str,
    parsed_items: List[Dict[str, Any]],
    language: str,
    model_name: str
) -> List[Dict[str, Any]]:
    """Use LangChain's with_structured_output for reliable JSON generation."""
    
    llm_client = create_llm_client(model_name)
    
    # Use LangChain's structured output feature (prevents JSON truncation/malformation)
    structured_llm = llm_client.with_structured_output(ChecklistAnalysisStructuredResult)
    
    language_names = {"english": "English", "danish": "Danish"}
    output_language = language_names.get(language, "English")
    
    items_list = "\n".join([f"{i['number']}. {i['name']}" for i in parsed_items])
    
    prompt = f"""Analyze and structure the following checklist analysis results.

You are a construction professional formatting detailed analysis results into a standardized database structure.

CRITICAL: Write ALL text content (item_name, description, excerpt fields) in {output_language}. 
The output language is {output_language} - use this language for all descriptive text.

ORIGINAL CHECKLIST ITEMS ({len(parsed_items)} items):
{items_list}

RAW ANALYSIS TO STRUCTURE:
{raw_analysis}

For each of the {len(parsed_items)} checklist items above, create a structured result entry with:
- item_number: The number from the original list (e.g., "1", "2", etc.)
- item_name: The exact name from the original checklist (in {output_language})
- status: Based on the analysis, use exactly one of: found, missing, risk, conditions, pending_clarification
- description: Clean summary of the key findings WITHOUT document citations (those go in sources) - WRITE IN {output_language}
- confidence_score: 0.0 to 1.0 based on how confident you are in the finding
- sources: Array of source references that support this finding

SOURCES ARRAY FORMAT:
sources: [
  {{"document": "specifications.pdf", "page": 12, "excerpt": "Short relevant quote in {output_language}"}},
  {{"document": "manual.pdf", "page": 25, "excerpt": "Another supporting quote in {output_language}"}}
]

CITATION EXTRACTION EXAMPLES:
- If analysis mentions "As specified in drawings.pdf, Page 5" and "According to manual.pdf, Page 23"
  → Include both sources in the array
- Extract ALL document references mentioned for each item, not just the primary one
- Each source should have: document name, page number, and a short supporting excerpt (in {output_language})

DESCRIPTION FIELD: Keep descriptions clean and factual WITHOUT citations. All citation info goes in the sources array.
LANGUAGE REQUIREMENT: Write all text content (descriptions, excerpts) in {output_language}.

IMPORTANT: You MUST include ALL {len(parsed_items)} items from the original checklist, even if not explicitly mentioned in the analysis."""

    # Call the structured LLM
    result = await structured_llm.ainvoke([HumanMessage(content=prompt)])
    
    # Convert Pydantic objects to dictionaries for database storage
    structured_results = []
    for item_result in result.results:
        # Convert multiple sources to individual fields for database compatibility
        # For now, take the first/primary source for the single-source fields
        primary_source = item_result.sources[0] if item_result.sources else None
        
        structured_results.append({
            "item_number": item_result.item_number,
            "item_name": item_result.item_name,
            "status": item_result.status.value,  # Extract enum value
            "description": item_result.description,
            "confidence_score": item_result.confidence_score,
            # Primary source fields (for backward compatibility)
            "source_document": primary_source.document if primary_source else None,
            "source_page": primary_source.page if primary_source else None,
            "source_excerpt": primary_source.excerpt if primary_source else None,
            # All sources as JSON array (for frontend use)
            "all_sources": [
                {
                    "document": src.document,
                    "page": src.page,
                    "excerpt": src.excerpt
                } for src in item_result.sources
            ] if item_result.sources else []
        })
    
    return structured_results


async def _structure_with_robust_json_parsing(
    raw_analysis: str,
    parsed_items: List[Dict[str, Any]],
    language: str,
    model_name: str
) -> List[Dict[str, Any]]:
    """Fallback using robust JSON parsing patterns from wiki generation."""
    
    llm_client = create_llm_client(model_name)
    
    language_names = {"english": "English", "danish": "Danish"}
    output_language = language_names.get(language, "English")
    items_list = "\n".join([f"{i['number']}. {i['name']}" for i in parsed_items])
    
    prompt = f"""Convert the raw analysis into a JSON array. Output ONLY valid JSON, no markdown or explanations.

CRITICAL LANGUAGE REQUIREMENT: Write ALL text content in {output_language}. 
Use {output_language} for all descriptive fields (item_name, description, excerpt).

CHECKLIST ITEMS ({len(parsed_items)} items):
{items_list}

RAW ANALYSIS:
{raw_analysis}

Output a JSON array with this exact structure (no markdown, no extra text):
[
  {{
    "item_number": "1",
    "item_name": "Wood species and grade specification (in {output_language})",
    "status": "found",
    "description": "Clean summary without citations (in {output_language})",
    "confidence_score": 0.9,
    "sources": [
      {{"document": "specifications.pdf", "page": 12, "excerpt": "Supporting quote in {output_language}"}},
      {{"document": "drawings.pdf", "page": 5, "excerpt": "Additional reference in {output_language}"}}
    ]
  }}
]

SOURCES ARRAY RULES:
- Include ALL document references found in the analysis for each item
- Each source needs: document name, page number (integer), excerpt (short quote in {output_language})
- description: Clean findings summary WITHOUT document references (in {output_language})
- Multiple sources per item are encouraged when available

Status values: found, missing, risk, conditions, pending_clarification
Include ALL {len(parsed_items)} items.
IMPORTANT: Write ALL text content in {output_language}."""

    response = await call_llm(llm_client, prompt)
    logger.info(f"LLM3 Raw response: {response[:500]}...")
    
    # Use robust JSON parsing from wiki generation
    return _parse_json_with_wiki_patterns(response, parsed_items)


def _parse_json_with_wiki_patterns(llm_response: str, parsed_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse JSON using the robust patterns from wiki generation step."""
    original_response = llm_response
    
    try:
        # Try direct parse first
        result = json.loads(llm_response.strip())
        if isinstance(result, list):
            return [clean_result_item(item) for item in result if isinstance(item, dict)]
    except json.JSONDecodeError as e:
        logger.debug(f"Direct JSON parse failed: {e}")

    # Strategy 1: Markdown code block extraction (multiple patterns)
    patterns = [
        r"```json\s*\n?(.*?)\n?\s*```",  # ```json\n{...}\n```
        r"```\s*\n?(\[.*?\])\s*\n?```",  # ```\n[...]\n```
        r"```(?:json)?\s*(\[.*?\])\s*```",  # Original pattern
    ]

    for i, pattern in enumerate(patterns):
        match = re.search(pattern, llm_response, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1).strip())
                if isinstance(result, list):
                    logger.info(f"✅ Code block extraction successful with pattern {i + 1}")
                    return [clean_result_item(item) for item in result if isinstance(item, dict)]
            except json.JSONDecodeError as e:
                logger.debug(f"Pattern {i + 1} matched but JSON parse failed: {e}")

    # Strategy 2: Manual cleanup approach
    cleaned_response = llm_response.strip()
    cleanup_pairs = [
        ("```json\n", "\n```"),
        ("```json", "```"),
        ("```\n", "\n```"),
        ("```", "```"),
    ]

    for start, end in cleanup_pairs:
        if cleaned_response.startswith(start) and cleaned_response.endswith(end):
            cleaned_response = cleaned_response[len(start) : -len(end)].strip()
            break

    try:
        result = json.loads(cleaned_response)
        if isinstance(result, list):
            logger.info(f"✅ Manual cleanup parse successful")
            return [clean_result_item(item) for item in result if isinstance(item, dict)]
    except json.JSONDecodeError as e:
        logger.debug(f"Manual cleanup parse failed: {e}")

    # Strategy 3: Try to fix incomplete JSON by adding missing closing brackets
    try:
        # Look for JSON that starts properly but may be truncated
        start_match = re.search(r'\[', llm_response)
        if start_match:
            json_start = llm_response[start_match.start():]
            
            # Count opening and closing brackets to fix incomplete JSON
            open_braces = json_start.count('{')
            close_braces = json_start.count('}')
            open_brackets = json_start.count('[')
            close_brackets = json_start.count(']')
            
            # Try to complete the JSON if it appears truncated
            completed_json = json_start
            if open_braces > close_braces:
                completed_json += '"}' * (open_braces - close_braces)
            if open_brackets > close_brackets:
                completed_json += ']' * (open_brackets - close_brackets)
            
            result = json.loads(completed_json)
            if isinstance(result, list):
                logger.info(f"✅ JSON completion successful")
                return [clean_result_item(item) for item in result if isinstance(item, dict)]
                
    except Exception as e:
        logger.debug(f"JSON completion failed: {e}")

    # Strategy 4: Extract individual JSON objects and build array
    try:
        # Look for individual complete JSON objects
        object_pattern = r'\{\s*"item_number"[\s\S]*?\}\s*(?=,|\]|$)'
        matches = re.findall(object_pattern, llm_response)
        
        if matches:
            valid_objects = []
            for match in matches:
                try:
                    obj = json.loads(match.strip().rstrip(','))
                    if isinstance(obj, dict) and 'item_number' in obj:
                        valid_objects.append(clean_result_item(obj))
                except json.JSONDecodeError:
                    continue
                    
            if valid_objects:
                logger.info(f"✅ Individual object extraction successful: {len(valid_objects)} objects")
                return valid_objects
                
    except Exception as e:
        logger.debug(f"Individual object extraction failed: {e}")

    # Final failure
    logger.error(f"❌ All JSON parsing strategies failed")
    logger.error(f"Response preview (first 300 chars): {original_response[:300]}")
    logger.error(f"Response preview (last 300 chars): {original_response[-300:]}")
    
    raise ValueError(f"Failed to parse JSON response after all strategies. Length: {len(original_response)}")