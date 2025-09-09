"""Structure generation step for wiki generation pipeline."""

import json
import logging
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings
from src.models import StepResult
from src.services.config_service import ConfigService
from src.services.storage_service import StorageService
from src.services.posthog_service import posthog_service
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError

from ...shared.base_step import PipelineStep

logger = logging.getLogger(__name__)


class StructureGenerationStep(PipelineStep):
    """Step 3: Generate wiki structure using LLM."""

    def __init__(
        self,
        config: dict[str, Any],
        storage_service: StorageService | None = None,
        progress_tracker=None,
        db_client=None,
    ):
        super().__init__(config, progress_tracker)
        self.storage_service = storage_service or StorageService()
        # Allow DI of db client; default to admin for pipeline safety
        self.supabase = db_client or get_supabase_admin_client()

        # Read generation settings from SoT (wiki.generation) with config fallback
        wiki_cfg = ConfigService().get_effective_config("wiki")
        gen_cfg = wiki_cfg.get("generation", {})
        defaults_cfg = ConfigService().get_effective_config("defaults")
        global_default_model = defaults_cfg.get("generation", {}).get("model", "google/gemini-2.5-flash-lite")
        self.model = gen_cfg.get("model", global_default_model)
        
        # Initialize LangChain OpenAI client with OpenRouter configuration
        try:
            settings = get_settings()
            self.openrouter_api_key = settings.openrouter_api_key
            if not self.openrouter_api_key:
                raise ValueError("OPENROUTER_API_KEY not found in environment variables")
            
            # Create LangChain ChatOpenAI client configured for OpenRouter
            self.llm_client = ChatOpenAI(
                model=self.model,
                openai_api_key=self.openrouter_api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                default_headers={"HTTP-Referer": "https://constructionrag.com"},
            )
        except Exception as e:
            logger.error(f"Failed to initialize LangChain ChatOpenAI client: {e}")
            raise
        self.language = config.get("language", "danish")
        self.max_tokens = config.get("structure_max_tokens", 6000)
        self.temperature = gen_cfg.get("temperature", config.get("temperature", 0.3))
        self.api_timeout = config.get("api_timeout_seconds", 30.0)

        # Add new config for testing limits
        self.max_pages = gen_cfg.get("max_pages", 10)  # Default to 10 if not specified
        self.queries_per_page = gen_cfg.get("queries_per_page", 8)  # Default to 8 if not specified

    async def execute(self, input_data: dict[str, Any]) -> StepResult:
        """Execute structure generation step."""
        start_time = datetime.utcnow()

        try:
            metadata = input_data["metadata"]
            project_overview = input_data["project_overview"]
            semantic_analysis = input_data.get("semantic_analysis", {})
            indexing_run_id = input_data.get("index_run_id")  # Get for analytics correlation
            logger.info(f"Starting structure generation for {metadata['total_documents']} documents")

            # Generate wiki structure using LLM
            wiki_structure = await self._generate_wiki_structure(project_overview, semantic_analysis, metadata, indexing_run_id)

            # Validate structure
            validated_structure = self._validate_wiki_structure(wiki_structure)

            # Create step result
            result = StepResult(
                step="structure_generation",
                status="completed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                summary_stats={
                    "total_pages": len(validated_structure.get("pages", [])),
                    "structure_title": validated_structure.get("title", "Unknown"),
                },
                sample_outputs={
                    "structure_title": validated_structure.get("title", "Unknown"),
                    "page_examples": [
                        page.get("title", "Unknown") for page in validated_structure.get("pages", [])[:3]
                    ],
                },
                data=validated_structure,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

            logger.info(f"Structure generation completed: {len(validated_structure.get('pages', []))} pages")
            return result

        except Exception as e:
            logger.error(f"Structure generation failed: {e}")
            raise AppError(
                "Structure generation failed",
                error_code=ErrorCode.EXTERNAL_API_ERROR,
                details={"reason": str(e)},
            ) from e

    async def validate_prerequisites_async(self, input_data: dict[str, Any]) -> bool:
        """Validate that input data meets step requirements."""
        required_fields = ["metadata", "project_overview", "semantic_analysis"]
        return all(field in input_data for field in required_fields)

    def estimate_duration(self, input_data: dict[str, Any]) -> int:
        """Estimate step duration in seconds."""
        return 60  # Structure generation typically takes less time than overview

    async def _generate_wiki_structure(
        self, project_overview: str, semantic_analysis: dict, metadata: dict[str, Any], indexing_run_id: str = None
    ) -> dict[str, Any]:
        """Generate wiki structure using LLM."""
        if not self.openrouter_api_key:
            raise ValueError("OpenRouter API key not configured")

        # Prepare prompt
        prompt = self._create_structure_prompt(project_overview, semantic_analysis, metadata)

        # Call LLM with analytics tracking
        response = await self._call_openrouter_api(prompt, max_tokens=3000, indexing_run_id=indexing_run_id)

        # Debug logging for LLM response
        logger.info(f"📋 [Wiki:Structure] LLM response received, length: {len(response)} chars")
        logger.debug(f"📋 [Wiki:Structure] Raw LLM response preview: {response[:500]}...")
        if len(response) > 500:
            logger.debug(f"📋 [Wiki:Structure] Raw LLM response end: ...{response[-200:]}")

        # Parse JSON response
        wiki_structure = self._parse_json_response(response)

        return wiki_structure

    def _create_structure_prompt(self, project_overview: str, semantic_analysis: dict, metadata: dict[str, Any]) -> str:
        """Create prompt for structure generation - exactly matching original."""
        # Prepare input data for LLM - exactly matching original
        cluster_summaries = semantic_analysis.get("cluster_summaries", [])

        # Prepare document list
        documents = metadata.get("documents", [])
        document_list = []
        for doc in documents:
            filename = doc.get("filename", f"document_{doc.get('id', 'unknown')[:8]}")
            file_size = doc.get("file_size", 0)
            page_count = doc.get("page_count", 0)
            document_list.append(f"- {filename} ({page_count} pages, {file_size:,} bytes)")

        # Prepare semantic clusters
        cluster_list = []
        for summary in cluster_summaries:
            cluster_id = summary.get("cluster_id", "unknown")
            cluster_name = summary.get("cluster_name", f"Cluster {cluster_id}")
            chunk_count = summary.get("chunk_count", 0)
            cluster_list.append(f"- Cluster {cluster_id} ({chunk_count} chunks): {cluster_name}")

        # Prepare section headers
        section_headers = metadata.get("section_headers_distribution", {})
        section_list = []
        for header, count in sorted(section_headers.items(), key=lambda x: x[1], reverse=True)[:10]:
            section_list.append(f"- {header}: {count} occurrences")

        # Create comprehensive English prompt for strategic wiki structure - exactly matching original
        prompt = f"""Analyze this construction project and create a wiki structure for it.

# Important context to consider when deciding which sections to create
1. The complete list of project documents:
{chr(10).join(document_list)}

2. The project overview/summary:
{project_overview}

3. Semantic analysis
{chr(10).join(cluster_list)}

## Section breakdown information
I want to create a wiki for this construction project. Determine the most logical structure for a wiki based on the project's documentation and content.

IMPORTANT: The wiki content will be generated in Danish language.

# Return output 
## Return output rules
- Create a maximum of {self.max_pages} wiki pages in total (including the overview page). Only create as many pages as you need to cover the project. 
- Make sure each output has EXACTLY 1 overview page titled "Projektoversigt" or "Project Overview" (depending on language), with the below queries (in Danish if the language specified is Danish and English if otherwise). Do NOT create multiple overview pages with similar names. 

project_overview_queries = [
    # Core project identity
    "project name title description overview summary purpose",
    "project type building type construction type facility type",
    "construction project scope objectives goals deliverables",
    "project purpose main objective vision function application use",
    "project scope construction scope building scope facility scope",
    "building elements structures installations systems components",
    "deliverables building parts materials equipment installations",
    
    # Key participants
    "contractor client owner developer architect engineer",
    "project team roles responsibilities stakeholders",
    "trade group discipline construction trade",
    
    # Project scale and type
    "project value budget cost estimate total contract",
    "square meters floor area size dimensions scope"
] 

- Make sure each page has a topic and EXACTLY {self.queries_per_page} associated queries that will help them retrieve relevant information for that topic. Like the previous queries for overview (in the language the document is, probably danish): 
- Each page should focus on a specific aspect of the construction project as described in the project overview & semantic analysis. It is often relevant to create subpages for different trade groups. 

## Return output format
Return your analysis in the following JSON format:

{{
 "title": "[Overall title for the wiki]",
 "description": "[Brief description of the construction project]",
 "pages": [
   {{
     "id": "page-1",
     "title": "[Page title]",
     "description": "[Brief description of what this page will cover]",
     "queries": [
       "query 1",
       "query 2",
       "query 3",
       "query 4"
     ],
     "relevance_score": "1-10",
     "topic_argumentation": "argumentation for why this was chosen"
   }}
 ]
}}

IMPORTANT FORMATTING INSTRUCTIONS:
- Return ONLY the valid JSON structure specified above
- DO NOT wrap the JSON in markdown code blocks (no ``` or ```json)
- DO NOT include any explanation text before or after the JSON
- Ensure the JSON is properly formatted and valid
- Start directly with {{ and end with }}
"""

        return prompt

    async def _call_openrouter_api(self, prompt: str, max_tokens: int = 6000, indexing_run_id: str = None) -> str:
        """Call OpenRouter API via LangChain ChatOpenAI with PostHog LangChain callback for analytics."""
        if not self.llm_client:
            raise Exception("LangChain ChatOpenAI client not configured")

        try:
            # Create message for LangChain
            message = HumanMessage(content=prompt)
            
            # Get PostHog callback for automatic LLM tracking
            posthog_callback = posthog_service.get_langchain_callback(
                pipeline_step="wiki_structure_generation",
                indexing_run_id=indexing_run_id,
                additional_properties={
                    "max_tokens": max_tokens,
                    "step_type": "structure_generation",
                    "model": self.model
                }
            )
            
            # Configure callbacks for the LangChain call
            callbacks = [posthog_callback] if posthog_callback else []
            
            # Make async call to LangChain ChatOpenAI with PostHog callback
            response = await self.llm_client.ainvoke(
                [message],
                config={"callbacks": callbacks} if callbacks else None
            )
            return response.content
            
        except Exception as e:
            logger.error(f"Exception during LangChain ChatOpenAI call: {e}")
            raise Exception(f"LangChain API error: {e}")

    def _parse_json_response(self, llm_response: str) -> dict[str, Any]:
        """Parse JSON response from LLM, handling markdown code blocks."""
        logger.debug(f"📋 [Wiki:Structure] Attempting to parse JSON response, length: {len(llm_response)}")
        
        # Handle completely empty response
        if not llm_response or not llm_response.strip():
            logger.error(f"📋 [Wiki:Structure] Empty LLM response received")
            raise ValueError("Empty response from LLM")
        
        original_response = llm_response
        
        try:
            # Try to parse directly first
            logger.debug(f"📋 [Wiki:Structure] Attempting direct JSON parse")
            result = json.loads(llm_response.strip())
            logger.info(f"📋 [Wiki:Structure] ✅ Direct JSON parse successful")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"📋 [Wiki:Structure] Direct JSON parse failed: {e}")

        import re

        # Strategy 1: Look for JSON code blocks with various patterns
        logger.debug(f"📋 [Wiki:Structure] Trying markdown code block extraction")
        patterns = [
            r"```json\s*\n?(.*?)\n?\s*```",  # ```json\n{...}\n```
            r"```\s*\n?(\{.*?\})\s*\n?```",  # ```\n{...}\n```  
            r"```(?:json)?\s*(\{.*?\})\s*```",  # Original pattern
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, llm_response, re.DOTALL)
            if match:
                try:
                    logger.debug(f"📋 [Wiki:Structure] Pattern {i+1} matched, attempting parse")
                    result = json.loads(match.group(1).strip())
                    logger.info(f"📋 [Wiki:Structure] ✅ Code block extraction successful with pattern {i+1}")
                    return result
                except json.JSONDecodeError as e:
                    logger.debug(f"📋 [Wiki:Structure] Pattern {i+1} matched but JSON parse failed: {e}")

        # Strategy 2: Manual cleanup approach
        logger.debug(f"📋 [Wiki:Structure] Trying manual cleanup approach")
        cleaned_response = llm_response.strip()
        
        # Remove various markdown prefixes/suffixes
        cleanup_pairs = [
            ("```json\n", "\n```"),
            ("```json", "```"),
            ("```\n", "\n```"),
            ("```", "```"),
        ]
        
        for start, end in cleanup_pairs:
            if cleaned_response.startswith(start) and cleaned_response.endswith(end):
                cleaned_response = cleaned_response[len(start):-len(end)].strip()
                logger.debug(f"📋 [Wiki:Structure] Removed markers: '{start}' and '{end}'")
                break

        try:
            logger.debug(f"📋 [Wiki:Structure] Attempting parse of cleaned response")
            result = json.loads(cleaned_response)
            logger.info(f"📋 [Wiki:Structure] ✅ Manual cleanup parse successful")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"📋 [Wiki:Structure] Manual cleanup parse failed: {e}")

        # Strategy 3: Find JSON-like content between curly braces (more permissive)
        logger.debug(f"📋 [Wiki:Structure] Trying brace pattern extraction")
        brace_pattern = r"(\{(?:[^{}]|{[^{}]*})*\})"
        matches = re.findall(brace_pattern, llm_response, re.DOTALL)
        
        for i, match in enumerate(matches):
            try:
                logger.debug(f"📋 [Wiki:Structure] Trying brace match {i+1}/{len(matches)}")
                result = json.loads(match.strip())
                logger.info(f"📋 [Wiki:Structure] ✅ Brace extraction successful with match {i+1}")
                return result
            except json.JSONDecodeError as e:
                logger.debug(f"📋 [Wiki:Structure] Brace match {i+1} parse failed: {e}")

        # Final failure with detailed logging
        logger.error(f"📋 [Wiki:Structure] ❌ All JSON parsing strategies failed")
        logger.error(f"📋 [Wiki:Structure] Response preview (first 300 chars): {original_response[:300]}")
        logger.error(f"📋 [Wiki:Structure] Response preview (last 300 chars): {original_response[-300:]}")
        
        raise ValueError(f"Failed to parse JSON response after trying all strategies. Response length: {len(original_response)}. Preview: {original_response[:200]}...")

    def _validate_wiki_structure(self, wiki_structure: dict[str, Any]) -> dict[str, Any]:
        """Validate and clean wiki structure."""
        if not isinstance(wiki_structure, dict):
            raise ValueError("Wiki structure must be a dictionary")

        if "pages" not in wiki_structure:
            raise ValueError("Wiki structure must contain 'pages' key")

        if not isinstance(wiki_structure["pages"], list):
            raise ValueError("Pages must be a list")

        if len(wiki_structure["pages"]) == 0:
            raise ValueError("Wiki structure must contain at least one page")

        # Validate each page
        validated_pages = []
        for i, page in enumerate(wiki_structure["pages"]):
            if not isinstance(page, dict):
                logger.warning(f"Skipping invalid page {i}: not a dictionary")
                continue

            # Ensure required fields
            page_id = page.get("id", f"page_{i + 1}")
            title = page.get("title", f"Page {i + 1}")
            description = page.get("description", "")
            relevance_score = page.get("relevance_score", 5)
            queries = page.get("queries", [])

            # Ensure queries is a list
            if not isinstance(queries, list):
                queries = []

            validated_page = {
                "id": page_id,
                "title": title,
                "description": description,
                "relevance_score": relevance_score,
                "queries": queries,
            }

            validated_pages.append(validated_page)

        # Ensure at least one overview page
        has_overview = any(
            "overview" in page["title"].lower() or "oversigt" in page["title"].lower() for page in validated_pages
        )
        if not has_overview:
            # Add a default overview page
            validated_pages.insert(
                0,
                {
                    "id": "page_overview",
                    "title": (
                        "Projektoversigt" if self.config.get("language", "danish") == "danish" else "Project Overview"
                    ),
                    "description": (
                        "Omfattende oversigt over projektet"
                        if self.config.get("language", "danish") == "danish"
                        else "Comprehensive project overview"
                    ),
                    "relevance_score": 10,
                    "queries": [
                        (
                            "projekt navn titel beskrivelse oversigt"
                            if self.config.get("language", "danish") == "danish"
                            else "project name title description overview"
                        ),
                        (
                            "byggeprojekt omfang målsætninger"
                            if self.config.get("language", "danish") == "danish"
                            else "construction project scope objectives goals"
                        ),
                    ],
                },
            )

        return {
            "title": wiki_structure.get("title", "Project Wiki"),
            "description": wiki_structure.get("description", ""),
            "pages": validated_pages,
        }
