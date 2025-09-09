import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from pydantic import BaseModel

from ...shared.base_step import PipelineStep, StepResult
from ..models import (
    SearchResult,
    QueryResponse,
    QualityMetrics,
    ResponseQuality,
    QualityDecision,
)
from src.config.settings import get_settings
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError

logger = logging.getLogger(__name__)


class GenerationConfig(BaseModel):
    """Configuration for the generation step"""

    provider: str = "openrouter"
    model: str  # must be provided by orchestrator (SoT)
    fallback_models: List[str] = [
        "anthropic/claude-3.5-haiku",
        "meta-llama/llama-3.1-8b-instruct",
    ]
    timeout_seconds: float = 30.0
    max_tokens: int = 1000
    temperature: float = 0.1
    response_format: Dict[str, Any] = {
        "include_citations": True,
        "include_confidence": True,
        "language": "danish",
    }


class ResponseGenerator(PipelineStep):
    """Generates comprehensive responses based on retrieved documents"""

    def __init__(self, config: GenerationConfig):
        super().__init__("ResponseGenerator")
        self.config = config
        self.settings = get_settings()

        # Log which model is configured to be used
        logger.info(f"🤖 ResponseGenerator initialized with primary model: {self.config.model}")
        logger.info(f"🤖 Fallback models configured: {self.config.fallback_models}")

    async def execute(self, input_data: tuple[str, List[SearchResult]]) -> StepResult:
        """Execute the generation step"""
        start_time = datetime.utcnow()

        # Unpack the query and search results
        query, search_results = input_data

        try:
            logger.info(
                f"Generating response for query: '{query[:100]}...' with {len(search_results)} retrieved documents"
            )

            # Generate the response
            response = await self.generate_response(query, search_results)

            # Calculate quality metrics
            quality_metrics = await self.calculate_quality_metrics(search_results, response)

            return StepResult(
                step=self.get_step_name(),
                status="completed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                summary_stats={
                    "model_used": response.performance_metrics["model_used"],
                    "tokens_used": response.performance_metrics["tokens_used"],
                    "confidence": response.performance_metrics["confidence"],
                },
                sample_outputs={
                    "response_preview": response.response[:200] + "...",
                    "sources_count": len(response.search_results),
                    "response": response.model_dump(exclude_none=True),
                },
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error in generation step: {e}")
            raise AppError(
                "Generation failed",
                error_code=ErrorCode.EXTERNAL_API_ERROR,
                details={"reason": str(e)},
            ) from e

    async def generate_response(self, query: str, search_results: List[SearchResult]) -> QueryResponse:
        """Generate a comprehensive response based on retrieved documents"""

        if not search_results:
            return QueryResponse(
                response="Beklager, jeg kunne ikke finde relevant information til dit spørgsmål.",
                search_results=[],
                performance_metrics={
                    "model_used": "none",
                    "tokens_used": 0,
                    "confidence": 0.0,
                    "sources_count": 0,
                },
                quality_metrics=QualityMetrics(
                    relevance_score=0.0,
                    confidence="low",
                    top_similarity=0.0,
                    result_count=0,
                ),
            )

        # Prepare context from search results
        context = self._prepare_context(search_results)

        # Generate the response using OpenRouter
        response_text, model_used, tokens_used = await self._call_openrouter(query, context)

        # Extract sources from search results
        sources = [
            {
                "content": result.content[:200] + "...",
                "source": result.source_filename,
                "page": result.page_number,
                "similarity": result.similarity_score,
            }
            for result in search_results  # Use all search results, not just top 3
        ]

        # Calculate confidence based on similarity scores
        confidence = self._calculate_confidence(search_results)

        # Calculate quality metrics
        quality_metrics = await self.calculate_quality_metrics(search_results, None)

        return QueryResponse(
            response=response_text,
            search_results=search_results,
            performance_metrics={
                "model_used": model_used,
                "tokens_used": tokens_used,
                "confidence": confidence,
                "sources_count": len(search_results),  # Use actual number of search results
            },
            quality_metrics=quality_metrics,
        )

    def _prepare_context(self, search_results: List[SearchResult]) -> str:
        """Prepare context from search results for the LLM"""

        context_parts = []

        # Log the search results metadata for debugging
        logger.info(f"📄 Preparing context from {len(search_results)} search results:")
        for i, result in enumerate(search_results, 1):
            logger.info(
                f"📄 Result {i}: filename='{result.source_filename}', page={result.page_number}, similarity={result.similarity_score:.3f}"
            )

            context_parts.append(
                f"Dokumenter fra {result.source_filename}, side {result.page_number}:\n{result.content}\n"
            )

        logger.info(f"📄 Final context length: {len(''.join(context_parts))} characters")
        return "\n".join(context_parts)

    async def _call_openrouter(self, query: str, context: str) -> tuple[str, str, int]:
        """Call OpenRouter API to generate response"""

        # Prepare the prompt
        prompt = self._create_prompt(query, context)

        # Try primary model first, then fallbacks
        models_to_try = [self.config.model] + self.config.fallback_models

        logger.info(f"🤖 Attempting to use models in order: {models_to_try}")
        logger.info(f"🤖 Primary model from config: {self.config.model}")

        for i, model in enumerate(models_to_try):
            try:
                logger.info(f"🤖 Trying model {i + 1}/{len(models_to_try)}: {model}")
                response_text, tokens_used = await self._make_openrouter_request(model, prompt)
                logger.info(f"✅ Successfully used model: {model} (tokens: {tokens_used})")
                return response_text, model, tokens_used
            except Exception as e:
                logger.warning(f"❌ Failed with model {model}: {e}")
                continue

        # If all models fail, return a fallback response
        logger.error("All OpenRouter models failed")
        return (
            "Beklager, jeg kunne ikke generere et svar lige nu. Prøv venligst igen senere.",
            "fallback",
            0,
        )

    def _create_prompt(self, query: str, context: str) -> str:
        """Create the prompt for the LLM"""

        prompt = f"""Du er en ekspert på dansk byggeri og konstruktion. Du skal besvare følgende spørgsmål baseret på den kontekst du får leveret:

SPØRGSMÅL:
{query}

KONTEKST:
{context}

Vurder baseret på spørgsmålet om du skal give et længere detaljeret svar eller et kort svar på få sætninger. 

VIGTIGT!
- Hvis du ikke har fået nok kontekst til at svare på spørgsmål, så gør brugere opmærksom på dette og forsøg ikke at svar på spørgsmålet! I stedet skriv KUN: "Jeg har ikke nok informationer til at svare på dit spørgsmål"
- Hvis du vurderer at du har et godt kort svar, så skriv kun det korte svar. 

INSTRUKTIONER:
- Svar på dansk
- Vær præcis og faktuel
- Citer relevante dele af kilderne når det er relevant - brug nummererede referencer som [1], [2] osv.
- Tilføj en "Referencer:" sektion til sidst i dit svar med nummererede kilder i formatet:
  [1] dokumentnavn.pdf, side X
  [2] andet-dokument.pdf, side Y
- Hold svaret under 500 ord
- Lav gerne mange korte afsnit for at gøre det nemt at læse.
- Formater dit svar i normal tekst format - ikke noget markdown.

SVAR:"""

        # Log the prompt components to see what's being sent
        logger.info(f"💬 Created prompt with {len(prompt)} characters")
        logger.info(f"💬 Query: {query}")
        logger.info(f"💬 Context preview (first 500 chars): {context[:500]}...")

        return prompt

    async def _make_openrouter_request(self, model: str, prompt: str) -> tuple[str, int]:
        """Make a request to OpenRouter API"""

        if not self.settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://construction-rag.com",
            "X-Title": "Construction RAG",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            tokens_used = data["usage"]["total_tokens"]

            return content, tokens_used

    def _calculate_confidence(self, search_results: List[SearchResult]) -> float:
        """Calculate confidence based on similarity scores"""

        if not search_results:
            return 0.0

        # Use the average of top 3 similarity scores
        top_scores = [result.similarity_score for result in search_results[:3]]
        avg_score = sum(top_scores) / len(top_scores)

        # Normalize to 0-1 range
        return min(avg_score, 1.0)

    async def calculate_quality_metrics(
        self, search_results: List[SearchResult], response: Optional[QueryResponse]
    ) -> QualityMetrics:
        """Calculate quality metrics for the response"""

        if not search_results:
            return QualityMetrics(
                relevance_score=0.0,
                confidence="low",
                top_similarity=0.0,
                result_count=0,
            )

        # Calculate relevance based on similarity scores
        relevance = self._calculate_confidence(search_results)

        # Calculate completeness based on number and diversity of sources
        completeness = min(len(search_results) / 5.0, 1.0)  # Normalize to 0-1

        # For now, assume accuracy based on relevance (in a real system, this would be more sophisticated)
        accuracy = relevance * 0.9  # Slightly lower than relevance

        # Overall quality is a weighted average
        overall_quality = relevance * 0.4 + completeness * 0.3 + accuracy * 0.3

        # Map to the correct QualityMetrics fields
        return QualityMetrics(
            relevance_score=overall_quality,
            confidence=("good" if overall_quality > 0.6 else "acceptable" if overall_quality > 0.4 else "low"),
            top_similarity=relevance,
            result_count=len(search_results),
        )

    async def validate_prerequisites_async(self, input_data: tuple[str, List[SearchResult]]) -> bool:
        """Validate that we have the required inputs"""
        query, search_results = input_data
        return self.settings.OPENROUTER_API_KEY is not None and len(search_results) > 0

    def estimate_duration(self, input_data: tuple[str, List[SearchResult]]) -> int:
        """Estimate the duration of this step in seconds"""
        query, search_results = input_data
        # Base time for API call + processing
        base_time = 3

        # Add time based on number of documents to process
        doc_time = len(search_results) * 0.5

        return int(base_time + doc_time)
