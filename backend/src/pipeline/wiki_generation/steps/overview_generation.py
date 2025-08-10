"""Overview generation step for wiki generation pipeline."""

import json
import ast
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging
import numpy as np

from ...shared.base_step import PipelineStep
from src.models import StepResult
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError
from src.services.storage_service import StorageService
from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings
from src.services.config_service import ConfigService

# Reuse the production Voyage client from the indexing pipeline
from src.pipeline.indexing.steps.embedding import VoyageEmbeddingClient

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

        # Configure embedding client for queries via SoT (align with retrieval)
        voyage_settings = get_settings()
        sot_query = ConfigService().get_effective_config("query")
        self.query_embedding_model = sot_query.get("embedding", {}).get(
            "model", "voyage-multilingual-2"
        )
        self.query_embedding_dims_expected = sot_query.get("embedding", {}).get(
            "dimensions", 1024
        )
        try:
            self.voyage_client = VoyageEmbeddingClient(
                api_key=voyage_settings.voyage_api_key,
                model=self.query_embedding_model,
            )
            logger.info(
                f"[Wiki:Overview] Using query embedding model='{self.query_embedding_model}', expected_dims={self.query_embedding_dims_expected}"
            )
        except Exception as e:
            logger.warning(
                f"[Wiki:Overview] Failed to initialize VoyageEmbeddingClient: {e}"
            )
            self.voyage_client = None

        # Generation model from SoT wiki generation section
        wiki_cfg = ConfigService().get_effective_config("wiki")
        self.model = wiki_cfg.get("generation", {}).get(
            "model", config.get("model", "google/gemini-2.5-flash")
        )
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
            print(
                f"🔍 [DEBUG] OverviewGenerationStep.execute() - Overview queries generated: {len(overview_queries)}"
            )

            # Perform vector search for each query
            print(
                "🔍 [DEBUG] OverviewGenerationStep.execute() - Performing vector search"
            )
            overview_data = await self._perform_vector_search(
                overview_queries, metadata
            )
            total_chunks = len(overview_data.get("retrieved_chunks", []))
            print(
                f"🔍 [DEBUG] OverviewGenerationStep.execute() - Vector search done. queries={len(overview_queries)}, total_chunks_retrieved={total_chunks}"
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
                    "total_chunks_retrieved": len(
                        overview_data.get("retrieved_chunks", [])
                    ),
                    "overview_length": len(project_overview),
                },
                sample_outputs={
                    "overview_preview": (
                        project_overview[:500] + "..."
                        if len(project_overview) > 500
                        else project_overview
                    ),
                    "query_examples": overview_queries[:3],
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
            raise AppError(
                "Overview generation failed",
                error_code=ErrorCode.EXTERNAL_API_ERROR,
                details={"reason": str(e)},
            ) from e

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

    def _generate_overview_queries(self, metadata: Dict[str, Any]) -> List[str]:
        """Generate overview queries based on metadata - exactly matching original."""
        language = self.config.get("language", "danish")

        if language == "danish":
            # Standard overview queries in Danish - exactly matching original
            project_overview_queries = [
                # Grundlæggende projektidentitet
                "projekt navn titel beskrivelse oversigt sammendrag formål",
                "byggeprojekt omfang målsætninger mål leverancer",
                "projekt lokation byggeplads adresse bygning udvikling",
                # Nøgledeltagere
                "entreprenør klient ejer udvikler arkitekt ingeniør",
                "projektteam roller ansvar interessenter",
                # Tidsplan og faser
                "projektplan tidsplan milepæle faser byggefaser etaper",
                "startdato færdiggørelsesdato projektvarighed",
                # Projektomfang og type
                "projektværdi budget omkostningsoverslag samlet kontrakt",
                "bygningstype bolig erhverv industri infrastruktur",
                "kvadratmeter etageareal størrelse dimensioner omfang",
            ]
        else:  # English
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
                "square meters floor area size dimensions scope",
            ]

        return project_overview_queries

    async def _generate_query_embedding(self, query_text: str) -> List[float]:
        """Generate embedding for query text using Voyage (same as document embeddings)."""
        if not self.voyage_client:
            raise ValueError("Voyage client not initialized for query embeddings")
        embeddings = await self.voyage_client.get_embeddings([query_text])
        vector = embeddings[0] if embeddings else []
        # Diagnostics
        if len(vector) != self.query_embedding_dims_expected:
            logger.warning(
                f"[Wiki:Overview] Query embedding dims mismatch: got {len(vector)}, expected {self.query_embedding_dims_expected}"
            )
        logger.info(
            f"[Wiki:Overview] Generated query embedding len={len(vector)} for text='{query_text[:50]}...'"
        )
        return vector

    async def _vector_similarity_search(
        self, query_text: str, document_ids: List[str], top_k: int = None
    ) -> List[Tuple[Dict, float]]:
        """Perform real pgvector similarity search using Voyage embeddings - matches production pipeline."""
        if top_k is None:
            top_k = self.max_chunks_per_query

        print(f"🔍 Real pgvector search for: '{query_text[:60]}...'")

        try:
            # Generate embedding for query using Voyage API
            query_embedding = await self._generate_query_embedding(query_text)

            # Get all chunks with embeddings for the specified documents
            query = (
                self.supabase.table("document_chunks")
                .select("id,document_id,content,metadata,embedding_1024")
                .in_("document_id", document_ids)
                .not_.is_("embedding_1024", "null")
            )

            response = query.execute()

            if not response.data:
                print(f"⚠️  Ingen embeddings fundet for dokumenter")
                return []

            # Calculate cosine similarity with each chunk - using production pipeline approach
            results_with_scores = []
            for chunk in response.data:
                # Parse chunk embedding using ast.literal_eval like production pipeline
                embedding_str = chunk["embedding_1024"]
                try:
                    chunk_embedding = ast.literal_eval(embedding_str)

                    # Ensure it's a list of floats
                    if isinstance(chunk_embedding, list):
                        chunk_embedding = [float(x) for x in chunk_embedding]

                        # Calculate cosine similarity
                        similarity = self._cosine_similarity(
                            query_embedding, chunk_embedding
                        )

                        # Convert to distance for sorting (like production pipeline)
                        distance = 1 - similarity

                        results_with_scores.append(
                            {
                                "chunk": chunk,
                                "similarity": similarity,
                                "distance": distance,
                            }
                        )
                    else:
                        print(f"⚠️  Invalid embedding format for chunk {chunk['id']}")
                        continue

                except (ValueError, SyntaxError) as e:
                    print(f"⚠️  Failed to parse embedding for chunk {chunk['id']}: {e}")
                    continue

            # Sort by distance (lowest first, highest similarity)
            results_with_scores.sort(key=lambda x: x["distance"])

            # Deduplicate based on content like production pipeline
            seen_content = set()
            unique_results = []

            for result in results_with_scores:
                # Create content hash for deduplication (first 200 chars)
                content_hash = result["chunk"]["content"][:200]

                if content_hash not in seen_content:
                    seen_content.add(content_hash)

                    # Only include if above threshold
                    if result["similarity"] >= self.similarity_threshold:
                        unique_results.append((result["chunk"], result["similarity"]))

                    # Stop when we have enough unique results
                    if len(unique_results) >= top_k * 2:
                        break

            # Final results sorted by similarity (highest first)
            unique_results.sort(key=lambda x: x[1], reverse=True)
            results = unique_results[:top_k]

            print(
                f"  Fundet {len(results)} relevante unikke chunks (threshold: {self.similarity_threshold})"
            )
            if results:
                avg_similarity = np.mean([score for _, score in results])
                print(f"  Gennemsnitlig similarity: {avg_similarity:.3f}")

            return results

        except Exception as e:
            print(f"⚠️  Vector search fejlede: {str(e)}")
            print(f"⚠️  Falder tilbage til tom resultat...")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)

            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(np.clip(similarity, -1.0, 1.0))  # Ensure [-1, 1] range

        except Exception as e:
            print(f"Error calculating cosine similarity: {e}")
            return 0.0

    async def _perform_vector_search(
        self, queries: List[str], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform vector search for each query - exactly matching original implementation."""
        print(f"Trin 2: Forespørger vector database for projektoversigt")

        # Get document IDs for vector search
        document_ids = [doc["id"] for doc in metadata["documents"]]
        all_retrieved_chunks = []
        query_results = {}

        # Execute each query - exactly matching original
        for i, query in enumerate(queries[: self.overview_query_count]):
            print(f"  Query {i+1}/{self.overview_query_count}: {query}")

            results = await self._vector_similarity_search(query, document_ids)
            query_results[query] = {
                "results_count": len(results),
                "chunks": [
                    {
                        "chunk_id": chunk.get("id"),
                        "similarity_score": score,
                        "content_preview": chunk.get("content", "")[:100] + "...",
                    }
                    for chunk, score in results
                ],
                "avg_similarity": (
                    np.mean([score for _, score in results]) if results else 0.0
                ),
            }

            # Collect unique chunks
            for chunk, score in results:
                # Avoid duplicates
                chunk_id = chunk.get("id")
                if not any(
                    existing.get("id") == chunk_id for existing in all_retrieved_chunks
                ):
                    chunk_with_score = chunk.copy()
                    chunk_with_score["similarity_score"] = score
                    chunk_with_score["retrieved_by_query"] = query
                    all_retrieved_chunks.append(chunk_with_score)

        print(
            f"Samlet hentet {len(all_retrieved_chunks)} unikke chunks til projektoversigt"
        )

        return {
            "retrieved_chunks": all_retrieved_chunks,
            "query_results": query_results,
            "total_unique_chunks": len(all_retrieved_chunks),
        }

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
                    chunk_embedding = ast.literal_eval(chunk_embedding)
                except Exception:
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
        """Create prompt for overview generation - exactly matching original."""
        retrieved_chunks = overview_data["retrieved_chunks"]

        print(f"Forbereder {len(retrieved_chunks)} chunks til LLM (bruger første 15)")

        # Prepare document excerpts for LLM - exactly matching original
        document_excerpts = []
        for i, chunk in enumerate(retrieved_chunks[:15]):  # Limit to avoid token limits
            content = chunk.get("content", "")
            document_id = chunk.get("document_id", "unknown")

            # Extract page number from metadata more reliably
            metadata_chunk = chunk.get("metadata", {})
            page_number = (
                metadata_chunk.get("page_number", "N/A") if metadata_chunk else "N/A"
            )

            similarity_score = chunk.get("similarity_score", 0.0)
            query = chunk.get("retrieved_by_query", "")

            # Debug: print first chunk details
            if i == 0:
                print(f"  Første chunk preview: {content[:100]}...")
                print(f"  Similarity: {similarity_score:.3f}, Page: {page_number}")

            excerpt = f"""
Uddrag {i+1}:
Kilde: dokument_{document_id[:8]}:side_{page_number}
Relevans score: {similarity_score:.2f}
Hentet af query: "{query}"
Indhold: {content[:800]}..."""
            document_excerpts.append(excerpt)

        print(f"Genereret {len(document_excerpts)} dokumentudtrag til LLM")

        excerpts_text = "\n".join(document_excerpts)

        # Create prompt in Danish - exactly matching original
        prompt = f"""Baseret på byggeprojektets dokumentudtog nedenfor, generer en kort 2-3 afsnit projektoversigt der dækker:

1. Projektnavn, type, placering og hovedformål
2. Nøgleinteressenter (klient, entreprenør, arkitekt osv.) og projekttidslinje  
3. Projektomfang, budget og vigtige leverancer

Brug KUN information der eksplicit findes i dokumentudtragene. Citér kilder ved hjælp af (Kilde: filnavn:side). Hvis kritisk information mangler, nævn kort hvad der ikke er tilgængeligt.

Dokumentudtrag:
{excerpts_text}

Generer projektoversigten på dansk:"""

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
            "🔍 [DEBUG] OverviewGenerationStep._call_openrouter_api() - Making request to OpenRouter API"
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
