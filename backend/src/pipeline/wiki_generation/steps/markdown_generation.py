"""Markdown generation step for wiki generation pipeline."""

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


class MarkdownGenerationStep(PipelineStep):
    """Step 5: Generate markdown content for wiki pages."""

    def __init__(
        self,
        config: Dict[str, Any],
        storage_service: Optional[StorageService] = None,
        progress_tracker=None,
    ):
        print("🔍 [DEBUG] MarkdownGenerationStep.__init__() - Starting initialization")
        super().__init__(config, progress_tracker)
        self.storage_service = storage_service or StorageService()
        self.supabase = get_supabase_admin_client()

        print(
            "🔍 [DEBUG] MarkdownGenerationStep.__init__() - Loading OpenRouter API key from settings"
        )
        # Load OpenRouter API key from settings
        try:
            settings = get_settings()
            print(
                f"🔍 [DEBUG] MarkdownGenerationStep.__init__() - Settings loaded: {type(settings)}"
            )
            self.openrouter_api_key = settings.openrouter_api_key
            print(
                f"🔍 [DEBUG] MarkdownGenerationStep.__init__() - OpenRouter API key: {'✓' if self.openrouter_api_key else '✗'}"
            )
            if self.openrouter_api_key:
                print(
                    f"🔍 [DEBUG] MarkdownGenerationStep.__init__() - API key preview: {self.openrouter_api_key[:10]}...{self.openrouter_api_key[-4:]}"
                )
            if not self.openrouter_api_key:
                print(
                    "❌ [DEBUG] MarkdownGenerationStep.__init__() - OpenRouter API key not found!"
                )
                raise ValueError(
                    "OPENROUTER_API_KEY not found in environment variables"
                )
        except Exception as e:
            print(
                f"❌ [DEBUG] MarkdownGenerationStep.__init__() - Error loading OpenRouter API key: {e}"
            )
            raise

        self.model = config.get("model", "google/gemini-2.5-flash")
        self.language = config.get("language", "danish")
        self.max_tokens = config.get("page_max_tokens", 8000)  # Increased from 4000
        self.temperature = config.get("temperature", 0.3)
        self.api_timeout = config.get("api_timeout_seconds", 30.0)
        print(
            "🔍 [DEBUG] MarkdownGenerationStep.__init__() - Initialization completed successfully"
        )

    async def execute(self, input_data: Dict[str, Any]) -> StepResult:
        """Execute markdown generation step."""
        start_time = datetime.utcnow()

        try:
            metadata = input_data["metadata"]
            wiki_structure = input_data["wiki_structure"]
            page_contents = input_data["page_contents"]
            logger.info(
                f"Starting markdown generation for {len(wiki_structure['pages'])} pages"
            )

            # Generate markdown for each page
            generated_pages = {}
            total_content_length = 0

            for page in wiki_structure["pages"]:
                page_id = page["id"]
                page_title = page["title"]
                page_description = page.get("description", "")

                logger.info(f"Generating markdown for page: {page_title}")

                # Get content for this page
                page_content = page_contents.get(page_id, {})

                # Generate markdown
                markdown_content = await self._generate_page_markdown(
                    page, page_content, metadata
                )

                generated_pages[page_id] = {
                    "title": page_title,
                    "description": page_description,
                    "markdown_content": markdown_content,
                    "content_length": len(markdown_content),
                }

                total_content_length += len(markdown_content)

            # Create step result
            result = StepResult(
                step="markdown_generation",
                status="completed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                summary_stats={
                    "total_pages": len(wiki_structure["pages"]),
                    "total_content_length": total_content_length,
                    "average_content_length": (
                        total_content_length // len(wiki_structure["pages"])
                        if wiki_structure["pages"]
                        else 0
                    ),
                },
                sample_outputs={
                    "page_examples": [
                        page["title"] for page in wiki_structure["pages"][:3]
                    ],
                    "content_previews": {
                        page_id: content["markdown_content"][:200] + "..."
                        for page_id, content in list(generated_pages.items())[:2]
                    },
                },
                data=generated_pages,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

            logger.info(
                f"Markdown generation completed: {total_content_length} characters generated"
            )
            return result

        except Exception as e:
            logger.error(f"Markdown generation failed: {e}")
            return StepResult(
                step="markdown_generation",
                status="failed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

    async def validate_prerequisites_async(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data meets step requirements."""
        required_fields = ["metadata", "wiki_structure", "page_contents"]
        return all(field in input_data for field in required_fields)

    def estimate_duration(self, input_data: Dict[str, Any]) -> int:
        """Estimate step duration in seconds."""
        wiki_structure = input_data.get("wiki_structure", {})
        num_pages = len(wiki_structure.get("pages", []))
        return num_pages * 60  # 60 seconds per page for LLM generation

    async def _generate_page_markdown(
        self,
        page: Dict[str, Any],
        page_content: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> str:
        """Generate markdown content for a specific page."""
        if not self.openrouter_api_key:
            raise ValueError("OpenRouter API key not configured")

        # Prepare prompt
        prompt = self._create_markdown_prompt(page, page_content, metadata)

        # Call LLM
        response = await self._call_openrouter_api(prompt, max_tokens=4000)

        return response

    def _create_markdown_prompt(
        self,
        page: Dict[str, Any],
        page_content: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> str:
        """Create prompt for markdown generation."""
        language = self.config.get("language", "danish")

        page_title = page["title"]
        page_description = page.get("description", "")
        queries = page.get("queries", [])

        retrieved_chunks = page_content.get("retrieved_chunks", [])
        source_documents = page_content.get("source_documents", {})

        if language == "danish":
            prompt = f"""Du er en ekspert byggeprojektanalytiker og tekniskskriver. Generer en omfattende, professionel markdown-wiki side baseret på følgende data.

SIDE INFORMATION:
- Titel: {page_title}
- Beskrivelse: {page_description}
- Relevante forespørgsler: {', '.join(queries)}

PROJEKT DATA:
- Antal dokumenter: {metadata['total_documents']}
- Antal tekstsegmenter: {metadata['total_chunks']}
- Antal sider analyseret: {metadata['total_pages_analyzed']}

KILDE DOKUMENTER:
{', '.join([doc.get('filename', 'Unknown') for doc in source_documents.values()])}

RETRIEVED INHOLD:
"""
        else:  # English
            prompt = f"""You are an expert construction project analyst and technical writer. Generate a comprehensive, professional markdown wiki page based on the following data.

PAGE INFORMATION:
- Title: {page_title}
- Description: {page_description}
- Relevant queries: {', '.join(queries)}

PROJECT DATA:
- Number of documents: {metadata['total_documents']}
- Number of text segments: {metadata['total_chunks']}
- Pages analyzed: {metadata['total_pages_analyzed']}

SOURCE DOCUMENTS:
{', '.join([doc.get('filename', 'Unknown') for doc in source_documents.values()])}

RETRIEVED CONTENT:
"""

        # Add retrieved content
        for i, chunk in enumerate(retrieved_chunks[:15]):  # Limit to 15 chunks
            content = chunk.get("content", "")
            metadata_info = chunk.get("metadata", {})
            similarity_score = chunk.get("similarity_score", 0)

            # Truncate content if too long
            if len(content) > 300:
                content = content[:300] + "..."

            prompt += f"\n--- Chunk {i+1} (Similarity: {similarity_score:.3f}) ---\n"
            prompt += f"Source: {metadata_info.get('source_filename', 'Unknown')}\n"
            prompt += f"Page: {metadata_info.get('page_number', 'Unknown')}\n"
            prompt += f"Content: {content}\n"

        if language == "danish":
            prompt += f"""

OPGAVE:
Generer en omfattende, professionel markdown-wiki side for "{page_title}". Siden skal være nyttig for byggeprojektets interessenter og skal indeholde:

KRITERIER:
1. Brug markdown-formatering (overskrifter, lister, tabeller, kodeblokke)
2. Fokuser på professionelle, strategiske aspekter - IKKE tekniske detaljer
3. Brug dansk byggesprog og terminologi
4. Inkluder relevante citater fra kildedokumenterne
5. Organiser indholdet logisk med overskrifter og underoverskrifter
6. Brug Mermaid-diagrammer for at visualisere processer eller strukturer (kun vertikale diagrammer)
7. Inkluder en oversigt over kildedokumenterne
8. Gør siden læsbar og professionel

STRUKTUR:
- Start med en kort introduktion
- Organiser indholdet i logiske sektioner
- Brug overskrifter (##, ###) for at strukturere indholdet
- Inkluder relevante citater og referencer
- Afslut med en opsummering eller næste skridt

VIKTIGT: Returner KUN markdown-indhold - ingen yderligere tekst eller forklaringer."""
        else:
            prompt += f"""

TASK:
Generate a comprehensive, professional markdown wiki page for "{page_title}". The page should be useful for the construction project's stakeholders and should include:

CRITERIA:
1. Use markdown formatting (headings, lists, tables, code blocks)
2. Focus on professional, strategic aspects - NOT technical details
3. Use English construction terminology
4. Include relevant citations from source documents
5. Organize content logically with headings and subheadings
6. Use Mermaid diagrams to visualize processes or structures (vertical diagrams only)
7. Include an overview of source documents
8. Make the page readable and professional

STRUCTURE:
- Start with a brief introduction
- Organize content in logical sections
- Use headings (##, ###) to structure content
- Include relevant citations and references
- End with a summary or next steps

IMPORTANT: Return ONLY markdown content - no additional text or explanations."""

        return prompt

    async def _call_openrouter_api(self, prompt: str, max_tokens: int = 8000) -> str:
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
