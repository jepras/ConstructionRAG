"""Structure generation step for wiki generation pipeline."""

import asyncio
import json
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from uuid import UUID

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
            logger.info(
                f"Starting structure generation for {metadata['total_documents']} documents"
            )

            # Generate wiki structure using LLM
            wiki_structure = await self._generate_wiki_structure(
                project_overview, metadata
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
        required_fields = ["metadata", "project_overview"]
        return all(field in input_data for field in required_fields)

    def estimate_duration(self, input_data: Dict[str, Any]) -> int:
        """Estimate step duration in seconds."""
        return 60  # Structure generation typically takes less time than overview

    async def _generate_wiki_structure(
        self, project_overview: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate wiki structure using LLM."""
        if not self.openrouter_api_key:
            raise ValueError("OpenRouter API key not configured")

        # Prepare prompt
        prompt = self._create_structure_prompt(project_overview, metadata)

        # Call LLM
        response = await self._call_openrouter_api(prompt, max_tokens=3000)

        # Parse JSON response
        wiki_structure = self._parse_json_response(response)

        return wiki_structure

    def _create_structure_prompt(
        self, project_overview: str, metadata: Dict[str, Any]
    ) -> str:
        """Create prompt for structure generation."""
        language = self.config.get("language", "danish")

        if language == "danish":
            prompt = f"""Du er en ekspert byggeprojektanalytiker og wiki-struktureringsspecialist. Baseret på følgende projektoversigt og metadata, opret en strategisk wiki-struktur for et byggeprojekt.

PROJEKT OVERSIGT:
{project_overview}

PROJEKT METADATA:
- Antal dokumenter: {metadata['total_documents']}
- Antal tekstsegmenter: {metadata['total_chunks']}
- Antal sider analyseret: {metadata['total_pages_analyzed']}
- Billeder behandlet: {metadata['images_processed']}
- Tabeller behandlet: {metadata['tables_processed']}

DOKUMENT FILNAVNE:
{', '.join(metadata['document_filenames'])}

SEKTIONSOVERSIGT:
{json.dumps(metadata['section_headers_distribution'], indent=2, ensure_ascii=False)}

OPGAVE:
Opret en strategisk wiki-struktur med 4-8 sider der fokuserer på byggeprojektets professionelle aspekter. Strukturen skal være nyttig for byggeprojektets interessenter (entreprenører, arkitekter, ingeniører, klienter).

KRITERIER:
1. Mindst 1 "oversigt" side
2. Hver side skal have 6-10 relevante forespørgsler
3. Fokuser på strategiske, professionelle aspekter - IKKE tekniske detaljer
4. Sider skal være logisk organiserede og overlappende
5. Brug danske titler og beskrivelser

RETURNER OUTPUT:
Returner din analyse i følgende JSON-format:

{{
  "title": "Projektnavn - Projektwiki",
  "description": "Kort beskrivelse af wiki'en",
  "pages": [
    {{
      "id": "page_1",
      "title": "Projektoversigt",
      "description": "Omfattende oversigt over projektet",
      "relevance_score": 10,
      "queries": [
        "projekt navn titel beskrivelse oversigt",
        "byggeprojekt omfang målsætninger",
        "projekt lokation byggeplads adresse",
        "projektværdi budget omkostningsoverslag",
        "bygningstype bolig erhverv industri",
        "kvadratmeter etageareal størrelse"
      ]
    }},
    {{
      "id": "page_2", 
      "title": "Nøgleinteressenter og Organisation",
      "description": "Projektets interessenter og organisatoriske struktur",
      "relevance_score": 9,
      "queries": [
        "entreprenør klient ejer udvikler",
        "projektteam roller ansvar",
        "organisationsstruktur hierarki",
        "kommunikation rapportering",
        "beslutningsprocesser godkendelser",
        "kontraktforhold ansvarsfordeling"
      ]
    }}
  ]
}}

VIKTIGT: Returner KUN JSON - ingen yderligere tekst eller forklaringer."""
        else:  # English
            prompt = f"""You are an expert construction project analyst and wiki structure specialist. Based on the following project overview and metadata, create a strategic wiki structure for a construction project.

PROJECT OVERVIEW:
{project_overview}

PROJECT METADATA:
- Number of documents: {metadata['total_documents']}
- Number of text segments: {metadata['total_chunks']}
- Pages analyzed: {metadata['total_pages_analyzed']}
- Images processed: {metadata['images_processed']}
- Tables processed: {metadata['tables_processed']}

DOCUMENT FILENAMES:
{', '.join(metadata['document_filenames'])}

SECTION OVERVIEW:
{json.dumps(metadata['section_headers_distribution'], indent=2, ensure_ascii=False)}

TASK:
Create a strategic wiki structure with 4-8 pages that focuses on the construction project's professional aspects. The structure should be useful for the construction project's stakeholders (contractors, architects, engineers, clients).

CRITERIA:
1. At least 1 "overview" page
2. Each page should have 6-10 relevant queries
3. Focus on strategic, professional aspects - NOT technical details
4. Pages should be logically organized and overlapping
5. Use English titles and descriptions

RETURN OUTPUT:
Return your analysis in the following JSON format:

{{
  "title": "Project Name - Project Wiki",
  "description": "Brief description of the wiki",
  "pages": [
    {{
      "id": "page_1",
      "title": "Project Overview",
      "description": "Comprehensive project overview",
      "relevance_score": 10,
      "queries": [
        "project name title description overview",
        "construction project scope objectives goals",
        "project location site address building",
        "project value budget cost estimate",
        "building type residential commercial industrial",
        "square meters floor area size dimensions"
      ]
    }},
    {{
      "id": "page_2",
      "title": "Key Stakeholders and Organization", 
      "description": "Project stakeholders and organizational structure",
      "relevance_score": 9,
      "queries": [
        "contractor client owner developer",
        "project team roles responsibilities",
        "organizational structure hierarchy",
        "communication reporting",
        "decision processes approvals",
        "contractual relationships responsibility allocation"
      ]
    }}
  ]
}}

IMPORTANT: Return ONLY JSON - no additional text or explanations."""

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
            "overview" in page["title"].lower() for page in validated_pages
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
