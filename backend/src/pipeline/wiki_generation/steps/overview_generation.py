"""Overview generation step for wiki generation pipeline."""

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


class OverviewGenerationStep(PipelineStep):
    """Step 2: Generate project overview using vector search and LLM."""

    def __init__(
        self,
        config: Dict[str, Any],
        storage_service: Optional[StorageService] = None,
        progress_tracker=None,
    ):
        print("🔍 [DEBUG] OverviewGenerationStep.__init__() - Starting initialization")
        super().__init__(config, progress_tracker)
        self.storage_service = storage_service or StorageService()
        self.supabase = get_supabase_admin_client()

        print(
            "🔍 [DEBUG] OverviewGenerationStep.__init__() - Loading OpenRouter API key from settings"
        )
        # Load OpenRouter API key from settings
        try:
            settings = get_settings()
            print(
                f"🔍 [DEBUG] OverviewGenerationStep.__init__() - Settings loaded: {type(settings)}"
            )
            self.openrouter_api_key = settings.openrouter_api_key
            print(
                f"🔍 [DEBUG] OverviewGenerationStep.__init__() - OpenRouter API key: {'✓' if self.openrouter_api_key else '✗'}"
            )
            if self.openrouter_api_key:
                print(
                    f"🔍 [DEBUG] OverviewGenerationStep.__init__() - API key preview: {self.openrouter_api_key[:10]}...{self.openrouter_api_key[-4:]}"
                )
            if not self.openrouter_api_key:
                print(
                    "❌ [DEBUG] OverviewGenerationStep.__init__() - OpenRouter API key not found!"
                )
                raise ValueError(
                    "OPENROUTER_API_KEY not found in environment variables"
                )
        except Exception as e:
            print(
                f"❌ [DEBUG] OverviewGenerationStep.__init__() - Error loading OpenRouter API key: {e}"
            )
            raise

        self.model = config.get("model", "google/gemini-2.5-flash")
        self.similarity_threshold = config.get("similarity_threshold", 0.3)
        self.max_chunks_per_query = config.get("max_chunks_per_query", 10)
        self.overview_query_count = config.get("overview_query_count", 12)
        self.max_chunks_in_prompt = config.get(
            "max_chunks_in_prompt", 10
        )  # Reduced from 15
        self.content_preview_length = config.get(
            "content_preview_length", 600
        )  # Reduced from 800
        self.api_timeout = config.get("api_timeout_seconds", 30.0)
        print(
            "🔍 [DEBUG] OverviewGenerationStep.__init__() - Initialization completed successfully"
        )

    async def execute(self, input_data: Dict[str, Any]) -> StepResult:
        """Execute overview generation step."""
        print("🔍 [DEBUG] OverviewGenerationStep.execute() - Starting execution")
        start_time = datetime.utcnow()

        try:
            metadata = input_data["metadata"]
            print(
                f"🔍 [DEBUG] OverviewGenerationStep.execute() - Processing {metadata.get('total_documents', 0)} documents"
            )
            logger.info(
                f"Starting overview generation for {metadata['total_documents']} documents"
            )

            # Generate overview queries
            print(
                "🔍 [DEBUG] OverviewGenerationStep.execute() - Generating overview queries"
            )
            overview_queries = self._generate_overview_queries(metadata)

            # Perform vector search for each query
            print(
                "🔍 [DEBUG] OverviewGenerationStep.execute() - Performing vector search"
            )
            overview_data = await self._perform_vector_search(
                overview_queries, metadata
            )

            # Generate LLM overview
            print(
                "🔍 [DEBUG] OverviewGenerationStep.execute() - Generating LLM overview"
            )
            project_overview = await self._generate_llm_overview(
                overview_data, metadata
            )

            # Create step result
            result = StepResult(
                step="overview_generation",
                status="completed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                summary_stats={
                    "queries_executed": len(overview_queries),
                    "total_chunks_retrieved": sum(
                        len(data.get("chunks", [])) for data in overview_data.values()
                    ),
                    "overview_length": len(project_overview),
                },
                sample_outputs={
                    "overview_preview": (
                        project_overview[:500] + "..."
                        if len(project_overview) > 500
                        else project_overview
                    ),
                    "query_examples": list(overview_queries.keys())[:3],
                },
                data={
                    "overview_queries": overview_queries,
                    "overview_data": overview_data,
                    "project_overview": project_overview,
                },
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

            print(
                "🔍 [DEBUG] OverviewGenerationStep.execute() - Execution completed successfully"
            )
            logger.info(
                f"Overview generation completed: {len(project_overview)} characters"
            )
            return result

        except Exception as e:
            print(
                f"❌ [DEBUG] OverviewGenerationStep.execute() - Error during execution: {e}"
            )
            logger.error(f"Overview generation failed: {e}")
            return StepResult(
                step="overview_generation",
                status="failed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

    async def validate_prerequisites_async(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data meets step requirements."""
        required_fields = ["metadata"]
        if not all(field in input_data for field in required_fields):
            return False

        metadata = input_data["metadata"]
        required_metadata_fields = ["total_documents", "chunks_with_embeddings"]
        return all(field in metadata for field in required_metadata_fields)

    def estimate_duration(self, input_data: Dict[str, Any]) -> int:
        """Estimate step duration in seconds."""
        return 120  # Overview generation can take time due to multiple queries and LLM calls

    def _generate_overview_queries(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        """Generate overview queries based on metadata."""
        language = self.config.get("language", "danish")

        if language == "danish":
            queries = {
                "projekt_identitet": "projekt navn titel beskrivelse oversigt",
                "byggeprojekt_omfang": "byggeprojekt omfang målsætninger",
                "projekt_lokation": "projekt lokation byggeplads adresse",
                "nøgleinteressenter": "entreprenør klient ejer udvikler",
                "projektteam": "projektteam roller ansvar",
                "projektplan": "projektplan tidsplan milepæle faser",
                "startdato": "startdato færdiggørelsesdato",
                "projektværdi": "projektværdi budget omkostningsoverslag",
                "bygningstype": "bygningstype bolig erhverv industri",
                "kvadratmeter": "kvadratmeter etageareal størrelse",
                "tekniske_specifikationer": "tekniske specifikationer krav standarder",
                "sikkerhed": "sikkerhed brandsikkerhed arbejdssikkerhed",
            }
        else:  # English
            queries = {
                "project_identity": "project name title description overview",
                "construction_scope": "construction project scope objectives goals",
                "project_location": "project location site address building",
                "key_stakeholders": "contractor client owner developer",
                "project_team": "project team roles responsibilities",
                "project_schedule": "project schedule timeline milestones phases",
                "start_date": "start date completion date duration",
                "project_value": "project value budget cost estimate",
                "building_type": "building type residential commercial industrial",
                "square_meters": "square meters floor area size dimensions",
                "technical_specifications": "technical specifications requirements standards",
                "safety": "safety fire safety work safety",
            }

        return queries

    async def _perform_vector_search(
        self, queries: Dict[str, str], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform vector search for each query."""
        overview_data = {}
        chunks_with_embeddings = metadata["chunks_with_embeddings"]

        for query_name, query_text in queries.items():
            logger.info(f"Processing query: {query_name} - {query_text}")

            # Generate embedding for query (simplified - in production you'd use Voyage AI)
            query_embedding = await self._generate_query_embedding(query_text)

            # Perform similarity search
            similar_chunks = await self._find_similar_chunks(
                query_embedding, chunks_with_embeddings
            )

            overview_data[query_name] = {
                "query": query_text,
                "chunks": similar_chunks,
                "chunk_count": len(similar_chunks),
            }

        return overview_data

    async def _generate_query_embedding(self, query_text: str) -> List[float]:
        """Generate embedding for query text."""
        # This is a simplified implementation
        # In production, you'd use Voyage AI or similar service
        import hashlib
        import random

        # Create a deterministic "embedding" based on query text
        # This is just for demonstration - replace with actual embedding service
        hash_obj = hashlib.md5(query_text.encode())
        hash_hex = hash_obj.hexdigest()

        # Convert hash to list of floats (1024 dimensions)
        random.seed(int(hash_hex[:8], 16))
        embedding = [random.uniform(-1, 1) for _ in range(1024)]

        return embedding

    async def _find_similar_chunks(
        self, query_embedding: List[float], chunks_with_embeddings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find similar chunks using cosine similarity."""
        similar_chunks = []

        for chunk in chunks_with_embeddings:
            chunk_embedding = chunk.get("embedding_1024")
            if not chunk_embedding:
                continue

            # Parse embedding if it's a string
            if isinstance(chunk_embedding, str):
                try:
                    import ast

                    chunk_embedding = ast.literal_eval(chunk_embedding)
                except:
                    continue

            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_embedding, chunk_embedding)

            if similarity >= self.similarity_threshold:
                chunk_with_similarity = {
                    **chunk,
                    "similarity_score": similarity,
                }
                similar_chunks.append(chunk_with_similarity)

        # Sort by similarity score and limit results
        similar_chunks.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar_chunks[: self.max_chunks_per_query]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def _generate_llm_overview(
        self, overview_data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> str:
        """Generate project overview using LLM."""
        if not self.openrouter_api_key:
            raise ValueError("OpenRouter API key not configured")

        # Prepare prompt
        prompt = self._create_overview_prompt(overview_data, metadata)

        # Call LLM
        response = await self._call_openrouter_api(prompt, max_tokens=2000)

        return response

    def _create_overview_prompt(
        self, overview_data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> str:
        """Create prompt for overview generation."""
        language = self.config.get("language", "danish")

        if language == "danish":
            prompt = f"""Du er en ekspert byggeprojektanalytiker. Baseret på følgende data, generer en omfattende projektoversigt for et byggeprojekt.

PROJEKT DATA:
- Antal dokumenter: {metadata['total_documents']}
- Antal tekstsegmenter: {metadata['total_chunks']}
- Antal sider analyseret: {metadata['total_pages_analyzed']}
- Billeder behandlet: {metadata['images_processed']}
- Tabeller behandlet: {metadata['tables_processed']}

DOKUMENT FILNAVNE:
{', '.join(metadata['document_filenames'])}

SEKTIONSOVERSIGT:
{json.dumps(metadata['section_headers_distribution'], indent=2, ensure_ascii=False)}

RETRIEVED INHOLD:
"""
        else:  # English
            prompt = f"""You are an expert construction project analyst. Based on the following data, generate a comprehensive project overview for a construction project.

PROJECT DATA:
- Number of documents: {metadata['total_documents']}
- Number of text segments: {metadata['total_chunks']}
- Pages analyzed: {metadata['total_pages_analyzed']}
- Images processed: {metadata['images_processed']}
- Tables processed: {metadata['tables_processed']}

DOCUMENT FILENAMES:
{', '.join(metadata['document_filenames'])}

SECTION OVERVIEW:
{json.dumps(metadata['section_headers_distribution'], indent=2, ensure_ascii=False)}

RETRIEVED CONTENT:
"""

        # Add retrieved content for each query
        for query_name, query_data in overview_data.items():
            chunks = query_data.get("chunks", [])
            if chunks:
                prompt += f"\n{query_name.upper()}:\n"
                # Limit chunks per query and content length based on config
                max_chunks_per_query = min(
                    3, self.max_chunks_in_prompt // len(overview_data)
                )
                for chunk in chunks[:max_chunks_per_query]:
                    content = chunk.get("content", "")[: self.content_preview_length]
                    prompt += f"- {content}...\n"

        if language == "danish":
            prompt += """

OPGAVE:
Generer en omfattende, professionel projektoversigt på dansk som ville være nyttig for byggeprojektets interessenter. Fokuser på:
1. Projektets identitet og formål
2. Nøgleinteressenter og roller
3. Projektomfang og leverancer
4. Tidsplan og milepæle
5. Tekniske specifikationer og krav
6. Sikkerhed og kvalitet

Svar på dansk og brug professionel byggesprog."""
        else:
            prompt += """

TASK:
Generate a comprehensive, professional project overview in English that would be useful for the construction project's stakeholders. Focus on:
1. Project identity and purpose
2. Key stakeholders and roles
3. Project scope and deliverables
4. Timeline and milestones
5. Technical specifications and requirements
6. Safety and quality

Answer in English and use professional construction terminology."""

        return prompt

    async def _call_openrouter_api(self, prompt: str, max_tokens: int = 4000) -> str:
        """Call OpenRouter API with the given prompt."""
        print(
            "🔍 [DEBUG] OverviewGenerationStep._call_openrouter_api() - Starting API call"
        )
        print(
            f"🔍 [DEBUG] OverviewGenerationStep._call_openrouter_api() - OpenRouter API key: {'✓' if self.openrouter_api_key else '✗'}"
        )

        if not self.openrouter_api_key:
            print(
                "❌ [DEBUG] OverviewGenerationStep._call_openrouter_api() - OpenRouter API key not configured!"
            )
            raise Exception("OpenRouter API key not configured")

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

        print(
            f"🔍 [DEBUG] OverviewGenerationStep._call_openrouter_api() - Making request to OpenRouter API"
        )
        print(
            f"🔍 [DEBUG] OverviewGenerationStep._call_openrouter_api() - Model: {self.model}"
        )
        print(
            f"🔍 [DEBUG] OverviewGenerationStep._call_openrouter_api() - Max tokens: {max_tokens}"
        )
        print(
            f"🔍 [DEBUG] OverviewGenerationStep._call_openrouter_api() - Timeout: {self.api_timeout}s"
        )

        try:
            import requests

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=self.api_timeout,  # Add timeout
            )
            print(
                f"🔍 [DEBUG] OverviewGenerationStep._call_openrouter_api() - Response status: {response.status_code}"
            )

            if response.status_code != 200:
                print(
                    f"❌ [DEBUG] OverviewGenerationStep._call_openrouter_api() - API error: {response.status_code} - {response.text}"
                )
                raise Exception(
                    f"OpenRouter API error: {response.status_code} - {response.text}"
                )

            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(
                f"🔍 [DEBUG] OverviewGenerationStep._call_openrouter_api() - API call successful, content length: {len(content)}"
            )
            return content

        except requests.exceptions.Timeout:
            print(
                f"❌ [DEBUG] OverviewGenerationStep._call_openrouter_api() - Request timed out after {self.api_timeout}s"
            )
            raise Exception(
                f"OpenRouter API request timed out after {self.api_timeout} seconds"
            )
        except Exception as e:
            print(
                f"❌ [DEBUG] OverviewGenerationStep._call_openrouter_api() - Exception during API call: {e}"
            )
            raise
