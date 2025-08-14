"""Markdown generation step for wiki generation pipeline."""

import logging
from datetime import datetime
from typing import Any

from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings
from src.models import StepResult
from src.services.config_service import ConfigService
from src.services.storage_service import StorageService
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError

from ...shared.base_step import PipelineStep

logger = logging.getLogger(__name__)


class MarkdownGenerationStep(PipelineStep):
    """Step 5: Generate markdown content for wiki pages."""

    def __init__(
        self,
        config: dict[str, Any],
        storage_service: StorageService | None = None,
        progress_tracker=None,
        db_client=None,
    ):
        print("🔍 [DEBUG] MarkdownGenerationStep.__init__() - Starting initialization")
        super().__init__(config, progress_tracker)
        self.storage_service = storage_service or StorageService()
        # Allow DI of db client; default to admin for pipeline safety
        self.supabase = db_client or get_supabase_admin_client()

        # Load OpenRouter API key from settings
        try:
            settings = get_settings()

            self.openrouter_api_key = settings.openrouter_api_key
            print(
                f"🔍 [DEBUG] MarkdownGenerationStep.__init__() - OpenRouter API key: {'✓' if self.openrouter_api_key else '✗'}"
            )
            if self.openrouter_api_key:
                print(
                    f"🔍 [DEBUG] MarkdownGenerationStep.__init__() - API key preview: {self.openrouter_api_key[:10]}...{self.openrouter_api_key[-4:]}"
                )
            if not self.openrouter_api_key:
                raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        except Exception as e:
            print(f"❌ [DEBUG] MarkdownGenerationStep.__init__() - Error loading OpenRouter API key: {e}")
            raise

        wiki_cfg = ConfigService().get_effective_config("wiki")
        gen_cfg = wiki_cfg.get("generation", {})
        self.model = gen_cfg.get("model", config.get("model", "google/gemini-2.5-flash"))
        self.language = config.get("language", "danish")
        self.max_tokens = config.get("page_max_tokens", 8000)  # Increased from 4000
        self.temperature = gen_cfg.get("temperature", config.get("temperature", 0.3))
        self.api_timeout = config.get("api_timeout_seconds", 30.0)

    async def execute(self, input_data: dict[str, Any]) -> StepResult:
        """Execute markdown generation step."""
        start_time = datetime.utcnow()

        try:
            metadata = input_data["metadata"]
            wiki_structure = input_data["wiki_structure"]
            page_contents = input_data["page_contents"]
            logger.info(f"Starting markdown generation for {len(wiki_structure['pages'])} pages")

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
                markdown_content = await self._generate_page_markdown(page, page_content, metadata)

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
                        total_content_length // len(wiki_structure["pages"]) if wiki_structure["pages"] else 0
                    ),
                },
                sample_outputs={
                    "page_examples": [page["title"] for page in wiki_structure["pages"][:3]],
                    "content_previews": {
                        page_id: content["markdown_content"][:200] + "..."
                        for page_id, content in list(generated_pages.items())[:2]
                    },
                },
                data=generated_pages,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

            logger.info(f"Markdown generation completed: {total_content_length} characters generated")
            return result

        except Exception as e:
            logger.error(f"Markdown generation failed: {e}")
            raise AppError(
                "Markdown generation failed",
                error_code=ErrorCode.EXTERNAL_API_ERROR,
                details={"reason": str(e)},
            ) from e

    async def validate_prerequisites_async(self, input_data: dict[str, Any]) -> bool:
        """Validate that input data meets step requirements."""
        required_fields = ["metadata", "wiki_structure", "page_contents"]
        return all(field in input_data for field in required_fields)

    def estimate_duration(self, input_data: dict[str, Any]) -> int:
        """Estimate step duration in seconds."""
        wiki_structure = input_data.get("wiki_structure", {})
        num_pages = len(wiki_structure.get("pages", []))
        return num_pages * 60  # 60 seconds per page for LLM generation

    async def _generate_page_markdown(
        self,
        page: dict[str, Any],
        page_content: dict[str, Any],
        metadata: dict[str, Any],
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
        page: dict[str, Any],
        page_content: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str:
        """Create prompt for markdown generation - exactly matching original."""
        page_title = page.get("title", "Unknown Page")
        page_description = page.get("description", "")

        print(f"    Generating markdown for: {page_title}")

        # Prepare document excerpts from retrieved chunks
        retrieved_chunks = page_content.get("retrieved_chunks", [])
        source_docs = page_content.get("source_documents", {})

        # Limit to top chunks to avoid token overflow
        top_chunks = sorted(retrieved_chunks, key=lambda x: x.get("similarity_score", 0), reverse=True)[:20]

        # Create document excerpts with source attribution
        document_excerpts = []
        source_counter = 1
        source_map = {}  # Map document_id to footnote number

        for chunk in top_chunks:
            content = chunk.get("content", "")
            doc_id = chunk.get("document_id", "unknown")
            metadata_chunk = chunk.get("metadata", {})
            page_number = metadata_chunk.get("page_number", "N/A") if metadata_chunk else "N/A"
            similarity = chunk.get("similarity_score", 0.0)

            # Create source reference
            if doc_id not in source_map:
                source_map[doc_id] = source_counter
                source_counter += 1

            source_ref = source_map[doc_id]

            excerpt = f"""
Excerpt {len(document_excerpts) + 1}:
Source: [Document {source_ref}, page {page_number}]
Relevance: {similarity:.3f}
Content: {content[:600]}..."""
            document_excerpts.append(excerpt)

        # Create source footnotes
        footnotes = []
        for doc_id, ref_num in source_map.items():
            # Find document info from metadata
            doc_info = None
            for doc in metadata.get("documents", []):
                if doc.get("id") == doc_id:
                    doc_info = doc
                    break

            filename = doc_info.get("filename", f"document_{doc_id[:8]}") if doc_info else f"document_{doc_id[:8]}"
            footnotes.append(f"[{ref_num}] {filename}")

        excerpts_text = "\n".join(document_excerpts[:12])  # Limit excerpts to avoid token overflow
        footnotes_text = "\n".join(footnotes)

        # Create comprehensive English prompt for markdown generation - exactly matching original
        prompt = f"""You are an expert construction project analyst and technical writer.

Your task is to generate a comprehensive and accurate construction project wiki page in Markdown format about a specific aspect, system, or component within a given construction project.

You will be given:

1. The "[PAGE_TITLE]" for the page you need to create and [PAGE_DESCRIPTION].

2. A list of "[RELEVANT_PAGE_RETRIEVED_CHUNKS]" from the construction project that you MUST use as the sole basis for the content. You have access to the full content of these document excerpts retrieved from project PDFs, specifications, contracts, and drawings. You MUST use AT LEAST 5 relevant document sources for comprehensive coverage - if fewer are provided, you MUST note this limitation.

CRITICAL STARTING INSTRUCTION:
The main title of the page should be a H1 Markdown heading.

Based ONLY on the content of the [RELEVANT_PAGE_RETRIEVED_CHUNKS]:

1. **Introduction:** Start with a concise introduction (1-2 paragraphs) explaining the purpose, scope, and high-level overview of "{page_title}" within the context of the overall construction project. Immediately after this, provide a table of the sections on this page with name of section and a short description of each section.

2. **Detailed Sections:** Break down "{page_title}" into logical sections using H2 (`##`) and H3 (`###`) Markdown headings. For each section:
   * Explain the project requirements, specifications, processes, or deliverables relevant to the section's focus, as evidenced in the source documents.
   * Identify key stakeholders, contractors, materials, systems, regulatory requirements, or project phases pertinent to that section.
   * Include relevant quantities, dimensions, costs, and timeline information where available.

3. **Mermaid Diagrams:**
   * EXTENSIVELY use Mermaid diagrams (e.g., `flowchart TD`, `sequenceDiagram`, `gantt`, `graph TD`, `Entity Relationship`, `Block`, `Git`, `Pie`, `Sankey`, `Timeline`) to visually represent project workflows, construction sequences, stakeholder relationships, and process flows found in the source documents.
   * Ensure diagrams are accurate and directly derived from information in the `[RELEVANT_PAGE_RETRIEVED_CHUNKS]`.
   * Provide a brief explanation before or after each diagram to give context.
   * CRITICAL: All diagrams MUST follow strict syntax rules:
     - Use "graph TD" (top-down) directive for flow diagrams (NEVER "graph LR")
     - Node IDs must be simple letters/numbers (A, B, C1, D2, etc.)
     - Node labels must be enclosed in square brackets: A[Label Text]
     - Question/decision nodes use curly braces: B{{Decision?}}
     - Connections use simple arrows: A --> B (NEVER use complex arrows)
     - Maximum node label width should be 3-4 words
     - NO special characters in node IDs (avoid spaces, hyphens, underscores in IDs)
     - Each line must end with semicolon: A[Start] --> B[Process];
     - Example: 
       graph TD
           A[Start] --> B{{Decision?}};
           B --> C[Option 1];
           B --> D[Option 2];
     - For sequence diagrams:
       - Start with "sequenceDiagram" directive on its own line
       - Define ALL participants at the beginning (Client, Contractor, Architect, Engineer, Inspector, etc.)
       - Use descriptive but concise participant names
       - Use the correct arrow types:
         - ->> for submissions/requests
         - -->> for approvals/responses  
         - -x for rejections/failures
       - Include activation boxes using +/- notation
       - Add notes for clarification using "Note over" or "Note right of"
     - For Gantt charts:
       - Use "gantt" directive
       - Include project phases, milestones, and dependencies
       - Show timeline relationships and critical path activities

4. **Tables:**
   * Use Markdown tables to summarize information such as:
     * Key project requirements, specifications, and acceptance criteria
     * Material quantities, types, suppliers, and delivery schedules
     * Contractor responsibilities, deliverables, and completion dates
     * Regulatory requirements, permits, inspections, and compliance deadlines
     * Cost breakdowns, budget allocations, and payment milestones
     * Quality standards, testing procedures, and documentation requirements
     * Safety protocols, risk assessments, and mitigation measures

5. **Document Excerpts (ENTIRELY OPTIONAL):**
   * Include short, relevant excerpts directly from the `[RELEVANT_DOCUMENT_EXCERPTS]` to illustrate key project requirements, specifications, or contractual terms.
   * Ensure excerpts are well-formatted within Markdown quote blocks.
   * Use excerpts to support technical specifications, quality requirements, or critical project constraints.

6. **Source Citations (EXTREMELY IMPORTANT):**
   * For EVERY piece of significant information, explanation, diagram, table entry, or document excerpt, you MUST cite the specific source document(s) and relevant page numbers or sections from which the information was derived.
   * Use standard markdown reference-style citations with numbered footnotes at the end of sentences or paragraphs.
   * Format citations as: The project budget is €2.5 million[1][p. 5-7] where [1] links to the footnote reference. and [p. 5-7] links to the page number.
   * Place all footnote definitions on a new line each at the bottom of each section on the page using the format:
     [1]: contract.pdf, page 5-7
     [2]: specifications.pdf, section 3.2  
     [3]: drawings.dwg, sheet A1
     [4]: safety_plan.pdf, section 4.2
     [5]: material_specs.xlsx, concrete_sheet

   For multiple sources supporting one claim, use: Construction will begin in March 2024[1][2][3]
   IMPORTANT: You MUST cite AT LEAST 5 different source documents throughout the wiki page to ensure comprehensive coverage when available.

7. **Technical Accuracy:** All information must be derived SOLELY from the `[RELEVANT_DOCUMENT_EXCERPTS]`. Do not infer, invent, or use external knowledge about construction practices, building codes, or industry standards unless it's directly supported by the provided project documents. If information is not present in the provided excerpts, do not include it or explicitly state its absence if crucial to the topic.

8. **Construction Professional Language:** Use clear, professional, and concise technical language suitable for project managers, contractors, architects, engineers, inspectors, and other construction professionals working on or learning about the project. Use correct construction and engineering terminology, including Danish construction terms when they appear in the source documents.

9. **Image/table summaries:** If some of the sources you retrieve are tables and images, then list them in a table format like below: 

| Drawing | Area | Description |
| :--- | :--- | :--- |
| `112727-01_K07_H1_EK_61.101` | Basement | Shows location of main panel (HT) and main cross-field (HX). |
| `112727-01_K07_H1_E0_61.102` | Ground floor | Routing paths in common areas, café and multi-room. |

10. **Conclusion/Summary:** End with a brief summary paragraph if appropriate for "{page_title}", reiterating the key aspects covered, critical deadlines, major deliverables, and their significance within the overall construction project. If relevant, and if information is available in the provided documents, list the to other potential wiki pages using below these paragraphs. 

IMPORTANT: Generate the content in Danish language.

Remember:
- Ground every claim in the provided project document excerpts
- Prioritize accuracy and direct representation of the project's actual requirements, specifications, and constraints
- Structure the document logically for easy understanding by construction professionals
- Include specific quantities, dates, costs, and technical specifications when available in the documents
- Focus on practical project information that can guide construction activities
- Highlight critical path items, regulatory requirements, and quality control measures
- Emphasize safety requirements and compliance obligations throughout

PAGE_TITLE: {page_title}
PAGE_DESCRIPTION: {page_description}
RELEVANT_PAGE_RETRIEVED_CHUNKS:
{excerpts_text}

RELEVANT_DOCUMENT_EXCERPTS:
{footnotes_text}

Generate the comprehensive markdown wiki page:"""

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
                raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            raise Exception(f"OpenRouter API request timed out after {self.api_timeout} seconds")
        except Exception as e:
            raise Exception(f"OpenRouter API error: {e}")
