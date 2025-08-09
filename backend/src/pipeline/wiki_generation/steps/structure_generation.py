"""Structure generation step for wiki generation pipeline."""

import json
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from ...shared.base_step import PipelineStep
from src.models import StepResult
from src.services.storage_service import StorageService
from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class StructureGenerationStep(PipelineStep):
    """Step 3: Generate wiki structure using LLM."""

    def __init__(
        self,
        config: Dict[str, Any],
        storage_service: Optional[StorageService] = None,
        progress_tracker=None,
    ):
        print("🔍 [DEBUG] StructureGenerationStep.__init__() - Starting initialization")
        super().__init__(config, progress_tracker)
        self.storage_service = storage_service or StorageService()
        self.supabase = get_supabase_admin_client()

        print(
            "🔍 [DEBUG] StructureGenerationStep.__init__() - Loading OpenRouter API key from settings"
        )
        # Load OpenRouter API key from settings
        try:
            settings = get_settings()
            print(
                f"🔍 [DEBUG] StructureGenerationStep.__init__() - Settings loaded: {type(settings)}"
            )
            self.openrouter_api_key = settings.openrouter_api_key
            print(
                f"🔍 [DEBUG] StructureGenerationStep.__init__() - OpenRouter API key: {'✓' if self.openrouter_api_key else '✗'}"
            )
            if self.openrouter_api_key:
                print(
                    f"🔍 [DEBUG] StructureGenerationStep.__init__() - API key preview: {self.openrouter_api_key[:10]}...{self.openrouter_api_key[-4:]}"
                )
            if not self.openrouter_api_key:
                print(
                    "❌ [DEBUG] StructureGenerationStep.__init__() - OpenRouter API key not found!"
                )
                raise ValueError(
                    "OPENROUTER_API_KEY not found in environment variables"
                )
        except Exception as e:
            print(
                f"❌ [DEBUG] StructureGenerationStep.__init__() - Error loading OpenRouter API key: {e}"
            )
            raise

        self.model = config.get("model", "google/gemini-2.5-flash")
        self.language = config.get("language", "danish")
        self.max_tokens = config.get(
            "structure_max_tokens", 6000
        )  # Increased from 3000
        self.temperature = config.get("temperature", 0.3)
        self.api_timeout = config.get("api_timeout_seconds", 30.0)
        print(
            "🔍 [DEBUG] StructureGenerationStep.__init__() - Initialization completed successfully"
        )

    async def execute(self, input_data: Dict[str, Any]) -> StepResult:
        """Execute structure generation step."""
        start_time = datetime.utcnow()

        try:
            metadata = input_data["metadata"]
            project_overview = input_data["project_overview"]
            semantic_analysis = input_data.get("semantic_analysis", {})
            logger.info(
                f"Starting structure generation for {metadata['total_documents']} documents"
            )

            # Generate wiki structure using LLM
            wiki_structure = await self._generate_wiki_structure(
                project_overview, semantic_analysis, metadata
            )

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
                        page.get("title", "Unknown")
                        for page in validated_structure.get("pages", [])[:3]
                    ],
                },
                data=validated_structure,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

            logger.info(
                f"Structure generation completed: {len(validated_structure.get('pages', []))} pages"
            )
            return result

        except Exception as e:
            logger.error(f"Structure generation failed: {e}")
            return StepResult(
                step="structure_generation",
                status="failed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

    async def validate_prerequisites_async(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data meets step requirements."""
        required_fields = ["metadata", "project_overview", "semantic_analysis"]
        return all(field in input_data for field in required_fields)

    def estimate_duration(self, input_data: Dict[str, Any]) -> int:
        """Estimate step duration in seconds."""
        return 60  # Structure generation typically takes less time than overview

    async def _generate_wiki_structure(
        self, project_overview: str, semantic_analysis: Dict, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate wiki structure using LLM."""
        if not self.openrouter_api_key:
            raise ValueError("OpenRouter API key not configured")

        # Prepare prompt
        prompt = self._create_structure_prompt(project_overview, semantic_analysis, metadata)

        # Call LLM
        response = await self._call_openrouter_api(prompt, max_tokens=3000)

        # Parse JSON response
        wiki_structure = self._parse_json_response(response)

        return wiki_structure

    def _create_structure_prompt(
        self, project_overview: str, semantic_analysis: Dict, metadata: Dict[str, Any]
    ) -> str:
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
            document_list.append(
                f"- {filename} ({page_count} pages, {file_size:,} bytes)"
            )

        # Prepare semantic clusters
        cluster_list = []
        for summary in cluster_summaries:
            cluster_id = summary.get("cluster_id", "unknown")
            cluster_name = summary.get("cluster_name", f"Cluster {cluster_id}")
            chunk_count = summary.get("chunk_count", 0)
            cluster_list.append(
                f"- Cluster {cluster_id} ({chunk_count} chunks): {cluster_name}"
            )

        # Prepare section headers
        section_headers = metadata.get("section_headers_distribution", {})
        section_list = []
        for header, count in sorted(
            section_headers.items(), key=lambda x: x[1], reverse=True
        )[:10]:
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

4. Sections detected
{chr(10).join(section_list) if section_list else "No sections detected"}

Use the project overview & semantic analysis most in your considerations.

## Section breakdown information
I want to create a wiki for this construction project. Determine the most logical structure for a wiki based on the project's documentation and content.

IMPORTANT: The wiki content will be generated in Danish language.

# Return output 
## Return output rules
- Make sure each output has EXACTLY 1 overview page titled "Projektoversigt" or "Project Overview" (depending on language). Do NOT create multiple overview pages with similar names. 

- Make sure each page has a topic and 6-10 associated queries that will help them retrieve relevant information for that topic. Like this for overview (in the language the document is, probably danish): 

project_overview_queries = [
    # Core project identity
    "project name title description overview summary purpose",
    "construction project scope objectives goals deliverables",
    "project location site address building development",
    
    # Key participants
    "contractor client owner developer architect engineer",
    "project team roles responsibilities stakeholders",
    
    # Timeline and phases
    "project schedule timeline milestones phases construction stages",
    "start date completion date project duration",
    
    # Project scale and type
    "project value budget cost estimate total contract",
    "building type residential commercial industrial infrastructure",
    "square meters floor area size dimensions scope"
] 

- OPTIONAL: If a page is closely related to another page, then store that in related_pages.

- Each page should focus on a specific aspect of the construction project (e.g., project phases, safety requirements, material specifications)

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
     "proposed_queries": [
       "[]"
     ],
     "related_pages": [
       "[]"
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

Your proposed tests for step 5 seems good. Please output the json that step outputs so i can check it as well."""

        return prompt

    async def _call_openrouter_api(self, prompt: str, max_tokens: int = 6000) -> str:
        """Call OpenRouter API with the given prompt."""
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://constructionrag.com",
            "X-Title": "ConstructionRAG Wiki Generator",
        }

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": self.config.get("temperature", 0.3),
        }

        try:
            import requests

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=self.api_timeout,  # Add timeout
            )

            if response.status_code != 200:
                raise Exception(
                    f"OpenRouter API error: {response.status_code} - {response.text}"
                )

            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            raise Exception(
                f"OpenRouter API request timed out after {self.api_timeout} seconds"
            )
        except Exception as e:
            raise Exception(f"OpenRouter API error: {e}")

    def _parse_json_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse JSON response from LLM, handling markdown code blocks."""
        try:
            # Try to parse directly first
            return json.loads(llm_response.strip())
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re

            # Look for JSON code blocks
            json_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
            match = re.search(json_pattern, llm_response, re.DOTALL)

            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

            # Try to find JSON-like content between curly braces
            brace_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
            match = re.search(brace_pattern, llm_response, re.DOTALL)

            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

            # If all else fails, try to clean up the response and parse
            cleaned_response = llm_response.strip()
            # Remove common prefixes/suffixes
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            try:
                return json.loads(cleaned_response.strip())
            except json.JSONDecodeError:
                raise ValueError(
                    f"Failed to parse JSON response: {llm_response[:200]}..."
                )

    def _validate_wiki_structure(
        self, wiki_structure: Dict[str, Any]
    ) -> Dict[str, Any]:
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
            page_id = page.get("id", f"page_{i+1}")
            title = page.get("title", f"Page {i+1}")
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
            "overview" in page["title"].lower() or "oversigt" in page["title"].lower()
            for page in validated_pages
        )
        if not has_overview:
            # Add a default overview page
            validated_pages.insert(
                0,
                {
                    "id": "page_overview",
                    "title": (
                        "Projektoversigt"
                        if self.config.get("language", "danish") == "danish"
                        else "Project Overview"
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
