import asyncio
import logging
import time
import os
from typing import Optional
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from pipeline.querying.models import QueryVariations
from pipeline.shared.base_step import PipelineStep
from src.config.settings import get_settings


logger = logging.getLogger(__name__)


class QueryProcessingConfig(BaseModel):
    """Configuration for query processing step"""

    provider: str = "openrouter"
    model: str = "openai/gpt-3.5-turbo"
    fallback_models: list[str] = ["anthropic/claude-3-haiku"]
    timeout_seconds: float = 1.0
    max_tokens: int = 200
    temperature: float = 0.1

    variations: dict = {
        "semantic_expansion": True,
        "hyde_document": True,
        "formal_variation": True,
        "parallel_generation": True,
    }


class QueryProcessor(PipelineStep):
    """Generate query variations to improve retrieval quality"""

    def __init__(self, config: QueryProcessingConfig):
        super().__init__(config.dict(), None)
        self.config = config

    async def process(self, query: str) -> QueryVariations:
        """Generate query variations in parallel"""

        logger.info(f"Processing query: {query[:50]}...")

        if self.config.variations.get("parallel_generation", True):
            # Generate variations in parallel
            tasks = {}

            if self.config.variations.get("semantic_expansion", True):
                tasks["semantic"] = self.generate_semantic_expansion(query)

            if self.config.variations.get("hyde_document", True):
                tasks["hyde"] = self.generate_hyde_document(query)

            if self.config.variations.get("formal_variation", True):
                tasks["formal"] = self.generate_formal_variation(query)

            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)

            # Create variations with results
            variations = QueryVariations(original=query)

            for i, (key, result) in enumerate(zip(tasks.keys(), results)):
                if isinstance(result, Exception):
                    logger.error(f"Error generating {key} variation: {result}")
                    # Use original query as fallback
                    if key == "semantic":
                        variations.semantic = query
                    elif key == "hyde":
                        variations.hyde = query
                    elif key == "formal":
                        variations.formal = query
                else:
                    if key == "semantic":
                        variations.semantic = result
                    elif key == "hyde":
                        variations.hyde = result
                    elif key == "formal":
                        variations.formal = result
        else:
            # Generate variations sequentially
            variations = QueryVariations(original=query)

            if self.config.variations.get("semantic_expansion", True):
                try:
                    variations.semantic = await self.generate_semantic_expansion(query)
                except Exception as e:
                    logger.error(f"Error generating semantic expansion: {e}")
                    variations.semantic = query

            if self.config.variations.get("hyde_document", True):
                try:
                    variations.hyde = await self.generate_hyde_document(query)
                except Exception as e:
                    logger.error(f"Error generating HyDE document: {e}")
                    variations.hyde = query

            if self.config.variations.get("formal_variation", True):
                try:
                    variations.formal = await self.generate_formal_variation(query)
                except Exception as e:
                    logger.error(f"Error generating formal variation: {e}")
                    variations.formal = query

        logger.info(f"Generated variations for query")
        return variations

    async def generate_semantic_expansion(self, query: str) -> str:
        """Generate semantic expansion of query"""
        try:
            client = self._get_openrouter_client()

            prompt = f"""Du er en ekspert på byggeri og installation. Giv mig 3-5 alternative måder at stille følgende spørgsmål på, som fokuserer på forskellige aspekter af problemet:

Originalt spørgsmål: "{query}"

Generer kun spørgsmålene, en per linje, uden nummerering eller ekstra tekst. Fokuser på:
- Tekniske detaljer
- Praktiske aspekter
- Sikkerhed og standarder
- Materialer og udstyr
- Installation og vedligeholdelse

Svar kun med spørgsmålene:"""

            response = await client.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()

        except Exception as e:
            logger.error(f"Error generating semantic expansion: {e}")
            return query  # Fallback to original query

    async def generate_hyde_document(self, query: str) -> str:
        """Generate hypothetical answer document"""
        try:
            client = self._get_openrouter_client()

            prompt = f"""Du er en byggeekspert der skal skrive et hypotetisk svar på følgende spørgsmål. Skriv et detaljeret, teknisk svar som om det var fra en byggehåndbog eller installationsguide:

Spørgsmål: "{query}"

Skriv et omfattende svar der inkluderer:
- Tekniske specifikationer
- Materialer og udstyr
- Installationsprocesser
- Sikkerhedsforanstaltninger
- Vedligeholdelseskrav
- Relevante standarder og koder

Svar på dansk og vær så detaljeret som muligt:"""

            response = await client.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()

        except Exception as e:
            logger.error(f"Error generating HyDE document: {e}")
            return query  # Fallback to original query

    async def generate_formal_variation(self, query: str) -> str:
        """Generate formal Danish construction query"""
        try:
            client = self._get_openrouter_client()

            prompt = f"""Omskriv følgende spørgsmål til et formelt, teknisk spørgsmål som en byggeingeniør ville stille:

Originalt spørgsmål: "{query}"

Gør spørgsmålet mere formelt og teknisk ved at:
- Bruge faglige termer
- Inkludere tekniske specifikationer
- Fokusere på standarder og koder
- Gøre det mere præcist og detaljeret

Svar kun med det omskrevne spørgsmål:"""

            response = await client.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()

        except Exception as e:
            logger.error(f"Error generating formal variation: {e}")
            return query  # Fallback to original query

    def _get_openrouter_client(self) -> ChatOpenAI:
        """Get OpenRouter client with proper configuration"""
        settings = get_settings()
        api_key = settings.openrouter_api_key

        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")

        return ChatOpenAI(
            model=self.config.model,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            default_headers={"HTTP-Referer": "http://localhost"},
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout=self.config.timeout_seconds * 1000,  # Convert to milliseconds
        )

    def select_best_variation(self, variations: QueryVariations) -> str:
        """Select the best variation for retrieval"""
        # For now, just return the original
        # TODO: Implement selection logic
        return variations.original

    async def execute(self, input_data: str) -> "StepResult":
        """Execute the query processing step"""
        from pipeline.shared.base_step import StepResult

        start_time = time.time()

        try:
            variations = await self.process(input_data)

            return StepResult(
                step="query_processing",
                status="completed",
                duration_seconds=time.time() - start_time,
                summary_stats={
                    "original_query": variations.original,
                    "variations_generated": 3,
                    "has_semantic": variations.semantic is not None,
                    "has_hyde": variations.hyde is not None,
                    "has_formal": variations.formal is not None,
                },
                sample_outputs={"variations": variations.dict()},
            )
        except Exception as e:
            return StepResult(
                step="query_processing",
                status="failed",
                duration_seconds=time.time() - start_time,
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
            )

    async def validate_prerequisites_async(self, input_data: str) -> bool:
        """Validate query processing prerequisites"""
        return isinstance(input_data, str) and len(input_data.strip()) > 0

    def estimate_duration(self, input_data: str) -> int:
        """Estimate query processing duration"""
        return 1  # 1 second for basic implementation
