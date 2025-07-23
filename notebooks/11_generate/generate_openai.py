# ==============================================================================
# LLM RESPONSE GENERATION - CONSTRUCTION RAG PIPELINE
# Generate Danish answers using GPT-4-turbo with structured citations
# ==============================================================================

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field

# --- OpenAI for Response Generation ---
import openai

# --- Environment Variables ---
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

# --- API Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# --- Path Configuration ---
RETRIEVE_BASE_DIR = "../../data/internal/08_retrieve"
OUTPUT_BASE_DIR = "../../data/internal/11_generate"

# --- Create timestamped output directory ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CURRENT_RUN_DIR = Path(OUTPUT_BASE_DIR) / f"11_run_{timestamp}"
CURRENT_RUN_DIR.mkdir(parents=True, exist_ok=True)

# --- Load Configuration ---
config_path = Path(__file__).parent / "config" / "generation_config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# Extract configuration
OPENAI_CONFIG = config["openai_config"]
CONTEXT_CONFIG = config["context_management"]
CITATION_CONFIG = config["citation_format"]
OUTPUT_CONFIG = config["output_formats"]
TEST_QUERIES = config["test_queries"]
SEARCH_METHOD = config["search_method"]

print(f"🇩🇰 LLM Response Generation - Construction RAG Pipeline")
print(f"📁 Output directory: {CURRENT_RUN_DIR}")
print(f"🔑 Using OpenAI model: {OPENAI_CONFIG['model']}")
print(f"🔍 Search method: {SEARCH_METHOD}")
print(f"📝 Test queries: {len(TEST_QUERIES)} Danish construction queries")

# ==============================================================================
# 2. DATA MODELS
# ==============================================================================


class SearchResult(BaseModel):
    """Individual search result with metadata"""

    rank: int
    similarity_score: float
    content: str
    content_snippet: str
    metadata: Dict[str, Any]
    source_filename: str
    page_number: int
    element_category: str
    section_title_inherited: Optional[str] = None


class Citation(BaseModel):
    """Citation for a source used in the answer"""

    source: str
    page: int
    section: str
    content_snippet: str
    confidence: float
    similarity_score: float


class GeneratedResponse(BaseModel):
    """Complete generated response with citations"""

    query: str
    answer: str
    citations: List[Citation]
    metadata: Dict[str, Any]


class GenerationRequest(BaseModel):
    """Request for generating a response"""

    query: str
    search_method: str
    search_results: List[SearchResult]
    context_window: int
    max_tokens: int


class GenerationMetrics(BaseModel):
    """Performance metrics for generation"""

    total_queries: int
    average_response_time_ms: float
    average_confidence_score: float
    citation_accuracy: float
    model_performance: Dict[str, Any]


# ==============================================================================
# 3. CORE FUNCTIONS
# ==============================================================================


def get_latest_retrieve_run() -> Path:
    """Auto-detect the latest 08_retrieve run directory"""
    retrieve_base_dir = Path(RETRIEVE_BASE_DIR)

    if not retrieve_base_dir.exists():
        raise ValueError(f"08_retrieve directory not found: {retrieve_base_dir}")

    # Find all run directories
    run_dirs = [
        d
        for d in retrieve_base_dir.iterdir()
        if d.is_dir() and d.name.startswith("08_run_")
    ]

    if not run_dirs:
        raise ValueError(f"No 08_retrieve run directories found in {retrieve_base_dir}")

    # Sort by timestamp (newest first)
    latest_run = sorted(run_dirs, key=lambda x: x.name, reverse=True)[0]
    print(f"✅ Auto-detected latest retrieve run: {latest_run.name}")
    return latest_run


def load_search_results_from_run(
    run_folder: Path, method: str = "hybrid_60_40", query_identifier: str = None
) -> Dict[str, Any]:
    """Load search results from specific run folder"""
    search_results_dir = run_folder / "search_results"

    if not search_results_dir.exists():
        raise ValueError(f"Search results directory not found: {search_results_dir}")

    # Find the specific search result file
    if query_identifier:
        # Look for files matching the query identifier (try both with and without å/aa conversion)
        patterns = [
            f"{method}_{query_identifier}*.json",
            f"{method}_{query_identifier.replace('aa', 'å')}*.json",
            f"{method}_{query_identifier.replace('å', 'aa')}*.json",
        ]
        matching_files = []
        for pattern in patterns:
            matching_files.extend(list(search_results_dir.glob(pattern)))
            if matching_files:
                break
    else:
        # Load all files for the method
        pattern = f"{method}_*.json"
        matching_files = list(search_results_dir.glob(pattern))

    if not matching_files:
        raise ValueError(f"No search result files found for method: {method}")

    # Load the first matching file
    result_file = matching_files[0]
    print(f"📄 Loading search results from: {result_file.name}")

    with open(result_file, "r", encoding="utf-8") as f:
        search_response = json.load(f)

    return search_response


def convert_to_search_results(search_response: Dict[str, Any]) -> List[SearchResult]:
    """Convert search response to SearchResult objects"""
    search_results = []

    for result_data in search_response.get("results", []):
        # Extract section title from metadata
        metadata = result_data.get("metadata", {})
        section_title = metadata.get("section_title_inherited", "Unknown")

        search_result = SearchResult(
            rank=result_data["rank"],
            similarity_score=result_data["similarity_score"],
            content=result_data["content"],
            content_snippet=result_data["content_snippet"],
            metadata=metadata,
            source_filename=result_data["source_filename"],
            page_number=result_data["page_number"],
            element_category=result_data["element_category"],
            section_title_inherited=section_title,
        )
        search_results.append(search_result)

    return search_results


def filter_relevant_results(
    search_results: List[SearchResult], min_threshold: float = 0.5
) -> List[SearchResult]:
    """Filter results based on similarity threshold"""
    relevant_results = [
        result for result in search_results if result.similarity_score >= min_threshold
    ]

    # If we have too few relevant results, include some lower-scoring ones
    if len(relevant_results) < 3:
        # Include top 8 results regardless of threshold
        relevant_results = search_results[:8]

    return relevant_results


def format_context_for_llm(search_results: List[SearchResult]) -> str:
    """Format search results for LLM context"""
    formatted_results = []

    for i, result in enumerate(search_results, 1):
        formatted_result = f"""
Result {i} (Relevance Score: {result.similarity_score:.3f}):
Source: {result.source_filename}
Page: {result.page_number}
Section: {result.section_title_inherited or 'Unknown'}

Content:
{result.content}

---
"""
        formatted_results.append(formatted_result)

    return "\n".join(formatted_results)


def generate_danish_response(
    query: str, search_results: List[SearchResult]
) -> GeneratedResponse:
    """Generate Danish response using GPT-4-turbo"""
    start_time = time.time()

    # Filter relevant results
    relevant_results = filter_relevant_results(
        search_results, CONTEXT_CONFIG["min_similarity_threshold"]
    )

    # Format context for LLM
    formatted_context = format_context_for_llm(
        relevant_results[: CONTEXT_CONFIG["max_results_to_consider"]]
    )

    # Create system prompt
    system_prompt = f"""
Du er en ekspert assistent inden for byggeri og entreprenørarbejde. Svar på spørgsmål baseret KUN på de leverede søgeresultater.

VIGTIGE REGLER:
1. Brug kun søgeresultater der er relevante for spørgsmålet
2. Citer ALLE kilder du bruger i dit svar
3. Hvis ingen resultater er relevante, sig "Jeg kunne ikke finde specifik information om [spørgsmål] i de tilgængelige byggedokumenter"
4. Inkluder tillidsniveau for hver citation (0.0-1.0)
5. Formater citationer som: [Kilde: filnavn.pdf, Side X, Afsnit "Y"]
6. Svar på DANSK
7. Returner svaret i JSON format med følgende struktur:
   {{
     "answer": "dit svar her",
     "citations": [
       {{
         "source": "filnavn.pdf",
         "page": 5,
         "section": "Afsnit titel",
         "content_snippet": "relevant tekst...",
         "confidence": 0.95,
         "similarity_score": 0.994
       }}
     ]
   }}

Søgeresultaterne er rangeret efter relevans (højere scores = mere relevante).
"""

    # Create user prompt
    user_prompt = f"""
Spørgsmål: {query}

Tilgængelige søgeresultater (rangeret efter relevans):
{formatted_context}

Svar på spørgsmålet ved kun at bruge de relevante søgeresultater. Citer alle kilder der bruges.
"""

    try:
        # Generate response
        response = openai.chat.completions.create(
            model=OPENAI_CONFIG["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=OPENAI_CONFIG["temperature"],
            max_tokens=OPENAI_CONFIG["max_tokens"],
            response_format={"type": "json_object"},
        )

        # Parse response
        response_content = response.choices[0].message.content
        response_data = json.loads(response_content)

        # Extract answer and citations
        answer = response_data.get("answer", "")
        citations_data = response_data.get("citations", [])

        # Convert citations to Citation objects
        citations = []
        for citation_data in citations_data:
            citation = Citation(
                source=citation_data.get("source", ""),
                page=citation_data.get("page", 0),
                section=citation_data.get("section", ""),
                content_snippet=citation_data.get("content_snippet", ""),
                confidence=citation_data.get("confidence", 0.0),
                similarity_score=citation_data.get("similarity_score", 0.0),
            )
            citations.append(citation)

        # Calculate generation time
        generation_time = (time.time() - start_time) * 1000

        # Create metadata
        metadata = {
            "search_method": SEARCH_METHOD,
            "results_considered": len(relevant_results),
            "results_cited": len(citations),
            "generation_time_ms": generation_time,
            "tokens_used": (
                response.usage.total_tokens if hasattr(response, "usage") else 0
            ),
            "model_used": OPENAI_CONFIG["model"],
        }

        return GeneratedResponse(
            query=query, answer=answer, citations=citations, metadata=metadata
        )

    except Exception as e:
        print(f"❌ Error generating response: {e}")

        # Return fallback response
        fallback_answer = f"Jeg kunne ikke generere et svar på spørgsmålet '{query}' på grund af en teknisk fejl. Prøv venligst igen senere."

        return GeneratedResponse(
            query=query,
            answer=fallback_answer,
            citations=[],
            metadata={
                "search_method": SEARCH_METHOD,
                "results_considered": len(relevant_results),
                "results_cited": 0,
                "generation_time_ms": (time.time() - start_time) * 1000,
                "tokens_used": 0,
                "model_used": OPENAI_CONFIG["model"],
                "error": str(e),
            },
        )


def create_html_response(generated_response: GeneratedResponse) -> str:
    """Create HTML formatted response for easy reading"""

    # Format citations
    citations_html = ""
    for i, citation in enumerate(generated_response.citations, 1):
        confidence_color = (
            "green"
            if citation.confidence > 0.7
            else "orange" if citation.confidence > 0.4 else "red"
        )
        citations_html += f"""
        <div style="margin: 10px 0; padding: 10px; border-left: 4px solid {confidence_color}; background-color: #f8f9fa;">
            <strong>Kilde {i}:</strong> {citation.source}<br>
            <strong>Side:</strong> {citation.page}<br>
            <strong>Afsnit:</strong> {citation.section}<br>
            <strong>Tillid:</strong> <span style="color: {confidence_color};">{citation.confidence:.2f}</span><br>
            <strong>Relevans Score:</strong> {citation.similarity_score:.3f}<br>
            <strong>Indhold:</strong> {citation.content_snippet[:200]}...
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>RAG Response - {generated_response.query}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            .query {{ background-color: #e6f3ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            .answer {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .citations {{ margin-top: 20px; }}
            .metadata {{ background-color: #f1f3f4; padding: 10px; border-radius: 5px; font-size: 12px; color: #666; }}
            .confidence-high {{ color: #28a745; }}
            .confidence-medium {{ color: #ffc107; }}
            .confidence-low {{ color: #dc3545; }}
        </style>
    </head>
    <body>
        <h1>🇩🇰 RAG Response - Byggeri</h1>
        
        <div class="query">
            <h2>Spørgsmål:</h2>
            <p><strong>{generated_response.query}</strong></p>
        </div>
        
        <div class="answer">
            <h2>Svar:</h2>
            <p>{generated_response.answer}</p>
        </div>
        
        <div class="citations">
            <h2>Kilder ({len(generated_response.citations)}):</h2>
            {citations_html if generated_response.citations else '<p><em>Ingen kilder citeret</em></p>'}
        </div>
        
        <div class="metadata">
            <h3>Metadata:</h3>
            <p><strong>Søgemetode:</strong> {generated_response.metadata.get('search_method', 'Unknown')}</p>
            <p><strong>Resultater overvejet:</strong> {generated_response.metadata.get('results_considered', 0)}</p>
            <p><strong>Kilder citeret:</strong> {generated_response.metadata.get('results_cited', 0)}</p>
            <p><strong>Genereringstid:</strong> {generated_response.metadata.get('generation_time_ms', 0):.0f}ms</p>
            <p><strong>Tokens brugt:</strong> {generated_response.metadata.get('tokens_used', 0)}</p>
            <p><strong>Model:</strong> {generated_response.metadata.get('model_used', 'Unknown')}</p>
        </div>
    </body>
    </html>
    """

    return html


def save_generated_response(
    generated_response: GeneratedResponse, query_identifier: str
):
    """Save generated response in both JSON and HTML formats"""

    # Save JSON response
    json_path = (
        CURRENT_RUN_DIR
        / "generated_responses"
        / f"{SEARCH_METHOD}_{query_identifier}_response.json"
    )
    json_path.parent.mkdir(exist_ok=True)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(generated_response.model_dump(), f, indent=2, ensure_ascii=False)

    # Save HTML response
    html_content = create_html_response(generated_response)
    html_path = (
        CURRENT_RUN_DIR
        / "generated_responses"
        / f"{SEARCH_METHOD}_{query_identifier}_response.html"
    )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"💾 Response saved: {json_path.name}")
    print(f"💾 HTML saved: {html_path.name}")

    return json_path, html_path


def test_query_generation(
    query: str, search_results: List[SearchResult]
) -> GeneratedResponse:
    """Test response generation for a single query"""
    print(f"\n{'='*60}")
    print(f"🔍 GENERATING RESPONSE FOR: '{query}'")
    print(f"{'='*60}")

    # Generate response
    generated_response = generate_danish_response(query, search_results)

    # Print summary
    print(f"📝 Answer length: {len(generated_response.answer)} characters")
    print(f"📚 Citations: {len(generated_response.citations)}")
    print(
        f"⏱️  Generation time: {generated_response.metadata['generation_time_ms']:.0f}ms"
    )

    if generated_response.citations:
        avg_confidence = sum(c.confidence for c in generated_response.citations) / len(
            generated_response.citations
        )
        print(f"🎯 Average confidence: {avg_confidence:.2f}")

    return generated_response


def create_generation_summary(
    generated_responses: List[GeneratedResponse],
) -> Dict[str, Any]:
    """Create summary of all generated responses"""

    total_queries = len(generated_responses)
    total_generation_time = sum(
        r.metadata.get("generation_time_ms", 0) for r in generated_responses
    )
    total_citations = sum(len(r.citations) for r in generated_responses)
    total_tokens = sum(r.metadata.get("tokens_used", 0) for r in generated_responses)

    # Calculate average confidence
    all_confidences = []
    for response in generated_responses:
        for citation in response.citations:
            all_confidences.append(citation.confidence)

    avg_confidence = (
        sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
    )

    summary = {
        "total_queries": total_queries,
        "average_response_time_ms": (
            total_generation_time / total_queries if total_queries > 0 else 0
        ),
        "average_confidence_score": avg_confidence,
        "total_citations": total_citations,
        "average_citations_per_response": (
            total_citations / total_queries if total_queries > 0 else 0
        ),
        "total_tokens_used": total_tokens,
        "average_tokens_per_response": (
            total_tokens / total_queries if total_queries > 0 else 0
        ),
        "search_method_used": SEARCH_METHOD,
        "model_used": OPENAI_CONFIG["model"],
        "generation_timestamp": datetime.now().isoformat(),
    }

    return summary


def save_generation_summary(summary: Dict[str, Any]):
    """Save generation summary"""
    summary_path = CURRENT_RUN_DIR / "generation_summary.json"

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"📊 Generation summary saved to: {summary_path}")


def print_generation_summary(summary: Dict[str, Any]):
    """Print generation summary"""
    print(f"\n{'='*80}")
    print(f"🎯 GENERATION SUMMARY")
    print(f"{'='*80}")

    print(f"📝 Total queries processed: {summary['total_queries']}")
    print(f"⏱️  Average response time: {summary['average_response_time_ms']:.0f}ms")
    print(f"🎯 Average confidence score: {summary['average_confidence_score']:.2f}")
    print(f"📚 Total citations: {summary['total_citations']}")
    print(
        f"📚 Average citations per response: {summary['average_citations_per_response']:.1f}"
    )
    print(f"🔤 Total tokens used: {summary['total_tokens_used']}")
    print(
        f"🔤 Average tokens per response: {summary['average_tokens_per_response']:.0f}"
    )
    print(f"🔍 Search method: {summary['search_method_used']}")
    print(f"🤖 Model: {summary['model_used']}")


# ==============================================================================
# 4. MAIN EXECUTION
# ==============================================================================


def main():
    """Main execution function"""
    print("🇩🇰 LLM RESPONSE GENERATION PIPELINE")
    print("=" * 60)

    try:
        # Step 1: Auto-detect latest retrieve run
        print("\n🔗 Step 1: Auto-detecting latest retrieve run...")
        retrieve_run_dir = get_latest_retrieve_run()
        print(f"✅ Using retrieve run: {retrieve_run_dir.name}")

        # Step 2: Generate responses for each test query
        print(f"\n🔍 Step 2: Generating Danish responses...")
        generated_responses = []

        for query in TEST_QUERIES:
            print(f"\n📝 Processing query: '{query}'")

            # Create query identifier - use the same logic as step 8
            query_identifier = (
                query.replace(" ", "_")
                .replace("æ", "ae")
                .replace("ø", "oe")
                .replace("å", "aa")
            )
            if len(query_identifier) > 30:
                query_identifier = query_identifier[:30]

            try:
                # Load search results
                search_response = load_search_results_from_run(
                    retrieve_run_dir, SEARCH_METHOD, query_identifier
                )
                search_results = convert_to_search_results(search_response)

                # Generate response
                generated_response = test_query_generation(query, search_results)
                generated_responses.append(generated_response)

                # Save response
                save_generated_response(generated_response, query_identifier)

            except Exception as e:
                print(f"❌ Error processing query '{query}': {e}")
                continue

        # Step 3: Create and save summary
        print(f"\n📊 Step 3: Creating generation summary...")
        summary = create_generation_summary(generated_responses)
        save_generation_summary(summary)
        print_generation_summary(summary)

        print(f"\n🎉 LLM Response Generation Complete!")
        print(f"📁 Output directory: {CURRENT_RUN_DIR}")
        print(f"📝 Queries processed: {len(generated_responses)}")
        print(f"🇩🇰 All responses generated in Danish")
        print(f"📚 Total citations: {summary['total_citations']}")

    except Exception as e:
        print(f"\n❌ Error in LLM response generation pipeline: {e}")
        raise


if __name__ == "__main__":
    main()
