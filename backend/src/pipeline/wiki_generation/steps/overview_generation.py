"""Overview generation step for wiki generation pipeline."""

import ast
import logging
from datetime import datetime
from typing import Any

import numpy as np
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings
from src.models import StepResult

# Reuse the production Voyage client from the indexing pipeline
from src.pipeline.indexing.steps.embedding import VoyageEmbeddingClient
from src.services.config_service import ConfigService
from src.services.storage_service import StorageService
from src.services.posthog_service import posthog_service
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError

from ...shared.base_step import PipelineStep

logger = logging.getLogger(__name__)


class OverviewGenerationStep(PipelineStep):
    """Step 2: Generate project overview using vector search and LLM."""

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

        # Configure embedding client for queries from passed config (no fresh ConfigService calls)
        voyage_settings = get_settings()
        query_config = config.get("query", config)  # Fallback to root config if no query section
        self.query_embedding_model = query_config.get("embedding", {}).get("model", "voyage-multilingual-2")
        self.query_embedding_dims_expected = query_config.get("embedding", {}).get("dimensions", 1024)
        try:
            self.voyage_client = VoyageEmbeddingClient(
                api_key=voyage_settings.voyage_api_key,
                model=self.query_embedding_model,
            )

        except Exception as e:
            logger.warning(f"[Wiki:Overview] Failed to initialize VoyageEmbeddingClient: {e}")
            self.voyage_client = None

        # Use generation model from passed config (no fresh ConfigService calls)
        generation_config = config.get("generation", {})
        self.model = generation_config.get("model", "google/gemini-2.5-flash-lite")
        self.similarity_threshold = config.get("similarity_threshold", 0.15)
        self.max_chunks_per_query = config.get("max_chunks_per_query", 10)
        self.overview_query_count = config.get("overview_query_count", 12)
        self.max_chunks_in_prompt = config.get("max_chunks_in_prompt", 10)  # Reduced from 15
        self.content_preview_length = config.get("content_preview_length", 600)  # Reduced from 800
        self.api_timeout = config.get("api_timeout_seconds", 30.0)

        # Initialize LangChain OpenAI client with OpenRouter configuration - AFTER all attributes are set
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

    async def execute(self, input_data: dict[str, Any]) -> StepResult:
        """Execute overview generation step."""
        start_time = datetime.utcnow()

        try:
            metadata = input_data["metadata"]
            indexing_run_id = input_data.get("index_run_id")  # Get for analytics correlation
            print(
                f"🔍 [DEBUG] OverviewGenerationStep.execute() - Processing {metadata.get('total_documents', 0)} documents"
            )
            logger.info(f"Starting overview generation for {metadata['total_documents']} documents")

            # Generate overview queries
            overview_queries = self._generate_overview_queries(metadata)

            # Perform vector search for each query
            overview_data = await self._perform_vector_search(overview_queries, metadata)
            total_chunks = len(overview_data.get("retrieved_chunks", []))
            print(
                f"🔍 [DEBUG] OverviewGenerationStep.execute() - Vector search done. queries={len(overview_queries)}, total_chunks_retrieved={total_chunks}"
            )

            # Generate LLM overview
            project_overview = await self._generate_llm_overview(overview_data, metadata, indexing_run_id)

            # Create step result
            result = StepResult(
                step="overview_generation",
                status="completed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                summary_stats={
                    "queries_executed": len(overview_queries),
                    "total_chunks_retrieved": len(overview_data.get("retrieved_chunks", [])),
                    "overview_length": len(project_overview),
                },
                sample_outputs={
                    "overview_preview": (
                        project_overview[:500] + "..." if len(project_overview) > 500 else project_overview
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

            logger.info(f"Overview generation completed: {len(project_overview)} characters")
            return result

        except Exception as e:
            logger.error(f"Error during overview generation: {e}")
            logger.error(f"Overview generation failed: {e}")
            raise AppError(
                "Overview generation failed",
                error_code=ErrorCode.EXTERNAL_API_ERROR,
                details={"reason": str(e)},
            ) from e

    async def validate_prerequisites_async(self, input_data: dict[str, Any]) -> bool:
        """Validate that input data meets step requirements."""
        required_fields = ["metadata"]
        if not all(field in input_data for field in required_fields):
            return False

        metadata = input_data["metadata"]
        required_metadata_fields = ["total_documents", "chunks_with_embeddings"]
        return all(field in metadata for field in required_metadata_fields)

    def estimate_duration(self, input_data: dict[str, Any]) -> int:
        """Estimate step duration in seconds."""
        return 120  # Overview generation can take time due to multiple queries and LLM calls

    def _generate_overview_queries(self, metadata: dict[str, Any]) -> list[str]:
        """Generate overview queries based on metadata - exactly matching original."""
        language = self.config.get("language", "english")

        if language == "danish":
            # Standard overview queries in Danish - exactly matching original
            project_overview_queries = [
                # 1. Projektnavn, type, placering og hovedformål
                "projekt navn titel betegnelse projektbetegnelse",
                "projekttype bygningstype anlægstype konstruktionstype",
                "projektplacering lokation adresse byggeplads beliggenhed område",
                "projektformål hovedformål målsætning vision anvendelse funktion",
                # 2. Projektomfang, hvad der skal bygges/installeres/leveres
                "projektomfang bygningsomfang konstruktionsomfang anlægsomfang",
                "bygningselementer konstruktioner installationer systemer komponenter",
                "leverancer bygningsdele materialer udstyr installationer",
                "byggeri nybyggeri ombygning renovering tilbygning modernisering",
                "tekniske installationer",
                # 3. Faggrupper og fagområder
                "fagentreprenør faggruppe fagområde byggefag håndværk",
            ]
        else:  # English
            project_overview_queries = [
                # 1. Project name, type, location and main purpose
                "project name title designation project designation",
                "project type building type construction type facility type",
                "project location site address construction site area region",
                "project purpose main objective vision function application use",
                # 2. Project scope, what will be built/installed/delivered
                "project scope construction scope building scope facility scope",
                "building elements structures installations systems components",
                "deliverables building parts materials equipment installations",
                "construction new build renovation refurbishment extension modernization",
                "technical installations HVAC electrical ventilation cooling heating",
                "square meters floor area gross area net area building area",
                "floors height building height number floors levels stories",
                # 3. Trade groups and disciplines
                "trade contractor trade group discipline construction trade",
            ]

        return project_overview_queries

    async def _generate_query_embedding(self, query_text: str) -> list[float]:
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
        logger.info(f"[Wiki:Overview] Generated query embedding len={len(vector)} for text='{query_text[:50]}...'")
        return vector

    async def _vector_similarity_search(
        self, query_text: str, document_ids: list[str], top_k: int = None
    ) -> list[tuple[dict, float]]:
        """Perform real pgvector similarity search using Voyage embeddings - matches production pipeline."""
        if top_k is None:
            top_k = self.max_chunks_per_query

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
                print("⚠️  Ingen embeddings fundet for dokumenter")
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
                        similarity = self._cosine_similarity(query_embedding, chunk_embedding)

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

            print(f"  Fundet {len(results)} relevante unikke chunks (threshold: {self.similarity_threshold})")
            if results:
                avg_similarity = np.mean([score for _, score in results])
                print(f"  Gennemsnitlig similarity: {avg_similarity:.3f}")

            return results

        except Exception as e:
            print(f"⚠️  Vector search fejlede: {str(e)}")
            print("⚠️  Falder tilbage til tom resultat...")
            return []

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
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

    async def _perform_vector_search(self, queries: list[str], metadata: dict[str, Any]) -> dict[str, Any]:
        """Perform vector search for each query - exactly matching original implementation."""
        print("Trin 2: Forespørger vector database for projektoversigt")

        # Get document IDs for vector search
        document_ids = [doc["id"] for doc in metadata["documents"]]
        all_retrieved_chunks = []
        query_results = {}

        # Execute each query - exactly matching original
        for i, query in enumerate(queries[: self.overview_query_count]):
            print(f"  Query {i + 1}/{self.overview_query_count}: {query}")

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
                "avg_similarity": (np.mean([score for _, score in results]) if results else 0.0),
            }

            # Collect unique chunks
            for chunk, score in results:
                # Avoid duplicates
                chunk_id = chunk.get("id")
                if not any(existing.get("id") == chunk_id for existing in all_retrieved_chunks):
                    chunk_with_score = chunk.copy()
                    chunk_with_score["similarity_score"] = score
                    chunk_with_score["retrieved_by_query"] = query
                    all_retrieved_chunks.append(chunk_with_score)

        print(f"Samlet hentet {len(all_retrieved_chunks)} unikke chunks til projektoversigt")

        return {
            "retrieved_chunks": all_retrieved_chunks,
            "query_results": query_results,
            "total_unique_chunks": len(all_retrieved_chunks),
        }

    async def _find_similar_chunks(
        self, query_embedding: list[float], chunks_with_embeddings: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
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
        self, overview_data: dict[str, Any], metadata: dict[str, Any], indexing_run_id: str = None
    ) -> str:
        """Generate project overview using LLM."""
        if not self.openrouter_api_key:
            raise ValueError("OpenRouter API key not configured")

        # Prepare prompt
        prompt = self._create_overview_prompt(overview_data, metadata)

        # Call LLM with analytics tracking
        response = await self._call_openrouter_api(prompt, max_tokens=2000, indexing_run_id=indexing_run_id)

        return response

    def _create_overview_prompt(self, overview_data: dict[str, Any], metadata: dict[str, Any]) -> str:
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
            page_number = metadata_chunk.get("page_number", "N/A") if metadata_chunk else "N/A"

            similarity_score = chunk.get("similarity_score", 0.0)
            query = chunk.get("retrieved_by_query", "")

            # Debug: print first chunk details
            if i == 0:
                print(f"  Første chunk preview: {content[:100]}...")
                print(f"  Similarity: {similarity_score:.3f}, Page: {page_number}")

            excerpt = f"""
Uddrag {i + 1}:
Kilde: dokument_{document_id[:8]}:side_{page_number}
Relevans score: {similarity_score:.2f}
Hentet af query: "{query}"
Indhold: {content[:800]}..."""
            document_excerpts.append(excerpt)

        print(f"Genereret {len(document_excerpts)} dokumentudtrag til LLM")

        excerpts_text = "\n".join(document_excerpts)

        # Create language-aware prompt following plan guidelines
        language = self.config.get("language", "english")
        language_names = {
            "english": "English",
            "danish": "Danish",
        }
        output_language = language_names.get(language, "English")
        
        prompt = f"""Based on the construction project's document excerpts below, generate a brief 2-3 paragraph project overview that covers:

1. Project name, type, location and main purpose
2. Project scope, what will be built, installed and delivered in the project. Mention what the main focus is and what are secondary tasks.
3. Which trade groups and disciplines are most mentioned in the documents in prioritized order.

Use ONLY information that is explicitly found in the document excerpts.

Document excerpts:
{excerpts_text}

Output your response in {output_language}:"""

        return prompt

    async def _call_openrouter_api(self, prompt: str, max_tokens: int = 4000, indexing_run_id: str = None) -> str:
        """Call OpenRouter API via LangChain ChatOpenAI with PostHog LangChain callback for analytics."""
        print(
            f"🔍 [DEBUG] OverviewGenerationStep._call_openrouter_api() - LangChain client configured: {'✓' if self.llm_client else '✗'}"
        )

        if not self.llm_client:
            raise Exception("LangChain ChatOpenAI client not configured")

        try:
            # Create message for LangChain
            message = HumanMessage(content=prompt)

            # Get PostHog callback for automatic LLM tracking
            posthog_callback = posthog_service.get_langchain_callback(
                pipeline_step="wiki_overview_generation",
                indexing_run_id=indexing_run_id,
                additional_properties={
                    "max_tokens": max_tokens,
                    "step_type": "overview_generation",
                    "model": self.model,
                },
            )

            # Configure callbacks for the LangChain call
            callbacks = [posthog_callback] if posthog_callback else []

            # Make async call to LangChain ChatOpenAI with PostHog callback
            response = await self.llm_client.ainvoke([message], config={"callbacks": callbacks} if callbacks else None)
            content = response.content

            # Ensure proper UTF-8 encoding for all characters (Danish æøå, quotes, symbols, etc.)
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            elif isinstance(content, str):
                # Fix any double-encoding issues by re-encoding/decoding
                try:
                    content = content.encode("utf-8").decode("utf-8")
                except UnicodeError:
                    # If already properly encoded, keep as-is
                    pass

            print(
                f"🔍 [DEBUG] OverviewGenerationStep._call_openrouter_api() - API call successful, content length: {len(content)}"
            )
            return content

        except Exception as e:
            print(f"❌ [DEBUG] OverviewGenerationStep._call_openrouter_api() - LangChain API error: {e}")
            logger.error(f"Exception during LangChain ChatOpenAI call: {e}")
            raise
