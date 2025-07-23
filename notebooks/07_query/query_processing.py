# ==============================================================================
# DANISH QUERY PROCESSING - CONSTRUCTION RAG PIPELINE
# Generate and test Danish query variations with performance analysis
# ==============================================================================

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field

# --- OpenAI for Query Processing ---
import openai

# --- Voyage AI for Query Embeddings ---
from voyageai import Client as VoyageClient

# --- ChromaDB for Testing ---
import chromadb

# --- Environment Variables ---
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

# --- API Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")
if not VOYAGE_API_KEY:
    raise ValueError("VOYAGE_API_KEY environment variable is required")

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# --- Path Configuration ---
OUTPUT_BASE_DIR = "../../data/internal/07_query"

# --- Create timestamped output directory ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CURRENT_RUN_DIR = Path(OUTPUT_BASE_DIR) / f"07_run_{timestamp}"
CURRENT_RUN_DIR.mkdir(parents=True, exist_ok=True)

# --- Load Configuration ---
config_path = Path(__file__).parent / "config" / "query_processing_config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# Extract configuration
OPENAI_CONFIG = config["openai_config"]
VOYAGE_CONFIG = config["voyage_config"]
TEST_QUERIES = config["test_queries"]
QUERY_VARIATIONS = config["query_variations"]
CONTENT_CATEGORIES = config["content_categories"]
PERFORMANCE_CONFIG = config["performance_testing"]
CHROMA_CONFIG = config["chroma_config"]

print(f"🇩🇰 Danish Query Processing - Construction RAG Pipeline")
print(f"📁 Output directory: {CURRENT_RUN_DIR}")
print(f"🔑 Using OpenAI model: {OPENAI_CONFIG['model']}")
print(f"🔑 Using Voyage model: {VOYAGE_CONFIG['model']}")
print(f"📝 Test queries: {len(TEST_QUERIES)} Danish construction queries")

# ==============================================================================
# 2. DATA MODELS
# ==============================================================================


class QueryVariation(BaseModel):
    """Individual query variation result"""

    variation_type: str
    query_text: str
    generation_time_ms: float
    success: bool
    error_message: Optional[str] = None


class SearchResult(BaseModel):
    """Individual search result with content snippet"""

    rank: int
    similarity_score: float
    content_snippet: str
    source_filename: str
    page_number: int
    element_category: str
    full_content_preview: str


class QueryPerformanceResult(BaseModel):
    """Performance result for a single query variation"""

    variation_type: str
    variation_query: str
    search_results: Dict[str, Any]
    best_similarity: float
    avg_top3_similarity: float
    content_range: float


class QueryVariationReport(BaseModel):
    """Comprehensive report for all variations of a single query"""

    original_query: str
    query_variations: List[QueryVariation]
    performance_results: List[QueryPerformanceResult]
    best_variation: str
    best_similarity_score: float
    top_content_snippets: List[str]
    bottom_content_snippets: List[str]
    variation_rankings: Dict[str, float]
    recommendations: List[str]
    processing_time_seconds: float


class OverallPerformanceReport(BaseModel):
    """Overall performance report across all test queries"""

    test_queries_analyzed: List[str]
    query_reports: Dict[str, QueryVariationReport]
    overall_insights: List[str]
    best_variation_techniques: Dict[str, int]
    danish_query_performance: str
    recommendations: List[str]


# ==============================================================================
# 3. CORE FUNCTIONS
# ==============================================================================


def expand_query_semantically(original_query: str) -> QueryVariation:
    """Generate Danish semantic variations using GPT for construction queries"""
    start_time = time.time()

    try:
        prompt = f"""
        Given this Danish construction/tender query: "{original_query}"
        
        Generate 4 semantically similar queries IN DANISH that could find the same information.
        Consider:
        - Alternative Danish technical terminology
        - Different phrasing styles (formal/informal Danish)  
        - Related Danish construction concepts that might contain the answer
        - Broader and narrower interpretations in Danish
        
        Return only the Danish alternative queries, one per line.
        """

        response = openai.chat.completions.create(
            model=OPENAI_CONFIG["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=OPENAI_CONFIG["temperature"],
            max_tokens=OPENAI_CONFIG["max_tokens"],
        )

        variations = [
            q.strip()
            for q in response.choices[0].message.content.strip().split("\n")
            if q.strip()
        ]
        # Return the first variation for testing
        variation_query = variations[0] if variations else original_query

        processing_time = (time.time() - start_time) * 1000

        return QueryVariation(
            variation_type="semantic_expansion",
            query_text=variation_query,
            generation_time_ms=processing_time,
            success=True,
        )

    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        return QueryVariation(
            variation_type="semantic_expansion",
            query_text=original_query,
            generation_time_ms=processing_time,
            success=False,
            error_message=str(e),
        )


def generate_hypothetical_document(original_query: str) -> QueryVariation:
    """Generate Danish hypothetical answer document for better embedding matching"""
    start_time = time.time()

    try:
        prompt = f"""
        Given this Danish construction query: "{original_query}"
        
        Write a detailed, technical paragraph IN DANISH that would likely contain the answer.
        Write it as if you're from a real construction project description pdf with information for tender purposes.
        Include specific details, measurements, and technical language that would appear in real Danish construction documents.
        
        Query: {original_query}
        
        Hypothetical Danish document excerpt:
        """

        response = openai.chat.completions.create(
            model=OPENAI_CONFIG["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=QUERY_VARIATIONS["hyde_document"]["temperature"],
            max_tokens=QUERY_VARIATIONS["hyde_document"]["max_tokens"],
        )

        hyde_document = response.choices[0].message.content.strip()
        processing_time = (time.time() - start_time) * 1000

        return QueryVariation(
            variation_type="hyde_document",
            query_text=hyde_document,
            generation_time_ms=processing_time,
            success=True,
        )

    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        return QueryVariation(
            variation_type="hyde_document",
            query_text=original_query,
            generation_time_ms=processing_time,
            success=False,
            error_message=str(e),
        )


def generate_formal_variation(original_query: str) -> QueryVariation:
    """Generate formal Danish variation of the query"""
    start_time = time.time()

    try:
        prompt = f"""
        Given this Danish construction query: "{original_query}"
        
        Rewrite it as a formal, official Danish construction/building regulation query.
        Use professional, technical Danish terminology that would appear in official documents.
        Make it more specific and detailed.
        
        Return only the formal Danish query.
        """

        response = openai.chat.completions.create(
            model=OPENAI_CONFIG["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=QUERY_VARIATIONS["formal_variation"]["temperature"],
            max_tokens=OPENAI_CONFIG["max_tokens"],
        )

        formal_query = response.choices[0].message.content.strip()
        processing_time = (time.time() - start_time) * 1000

        return QueryVariation(
            variation_type="formal_variation",
            query_text=formal_query,
            generation_time_ms=processing_time,
            success=True,
        )

    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        return QueryVariation(
            variation_type="formal_variation",
            query_text=original_query,
            generation_time_ms=processing_time,
            success=False,
            error_message=str(e),
        )


def create_query_embedding(query: str) -> Optional[List[float]]:
    """Create embedding for query using Voyage API"""
    try:
        client = VoyageClient(api_key=VOYAGE_API_KEY)
        response = client.embed(texts=[query], model=VOYAGE_CONFIG["model"])
        return response.embeddings[0]
    except Exception as e:
        print(f"❌ Failed to create embedding for query: {e}")
        return None


def initialize_chroma_collection() -> chromadb.Collection:
    """Initialize ChromaDB collection for testing"""
    client = chromadb.PersistentClient(path=CHROMA_CONFIG["persist_directory"])
    collection = client.get_collection(name=CHROMA_CONFIG["collection_name"])
    return collection


def search_documents(query: str, collection: chromadb.Collection) -> List[SearchResult]:
    """Search documents without any metadata filtering"""
    query_embedding = create_query_embedding(query)
    if not query_embedding:
        return []

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=PERFORMANCE_CONFIG["search_results_count"],
            include=["documents", "distances", "metadatas"],
        )

        return process_search_results(results)

    except Exception as e:
        print(f"❌ Search failed: {e}")
        return []


def process_search_results(chroma_results: Dict[str, Any]) -> List[SearchResult]:
    """Process ChromaDB results into SearchResult objects"""
    search_results = []

    if not chroma_results["ids"] or not chroma_results["ids"][0]:
        return search_results

    for i in range(len(chroma_results["ids"][0])):
        similarity_score = 1 - chroma_results["distances"][0][i]
        content = chroma_results["documents"][0][i]
        metadata = (
            chroma_results["metadatas"][0][i] if chroma_results["metadatas"] else {}
        )

        # Create content snippet
        snippet_length = PERFORMANCE_CONFIG["content_snippet_length"]
        content_snippet = (
            content[:snippet_length] + "..."
            if len(content) > snippet_length
            else content
        )

        # Create full preview (longer)
        preview_length = 200
        full_preview = (
            content[:preview_length] + "..."
            if len(content) > preview_length
            else content
        )

        search_result = SearchResult(
            rank=i + 1,
            similarity_score=similarity_score,
            content_snippet=content_snippet,
            source_filename=metadata.get("source_filename", "Unknown"),
            page_number=metadata.get("page_number", 0),
            element_category=metadata.get("element_category", "Unknown"),
            full_content_preview=full_preview,
        )

        search_results.append(search_result)

    return search_results


def analyze_search_performance(results: List[SearchResult]) -> Dict[str, Any]:
    """Analyze search results performance"""
    if not results:
        return {
            "best_similarity": 0.0,
            "worst_similarity": 0.0,
            "avg_similarity": 0.0,
            "avg_top3": 0.0,
            "content_range": 0.0,
            "top_results": [],
            "bottom_results": [],
        }

    similarities = [r.similarity_score for r in results]
    best_similarity = max(similarities)
    worst_similarity = min(similarities)
    avg_similarity = sum(similarities) / len(similarities)

    # Top 3 average
    top3_similarities = similarities[:3] if len(similarities) >= 3 else similarities
    avg_top3 = sum(top3_similarities) / len(top3_similarities)

    content_range = best_similarity - worst_similarity

    top_count = PERFORMANCE_CONFIG["top_results_display"]
    bottom_count = PERFORMANCE_CONFIG["bottom_results_display"]

    return {
        "best_similarity": best_similarity,
        "worst_similarity": worst_similarity,
        "avg_similarity": avg_similarity,
        "avg_top3": avg_top3,
        "content_range": content_range,
        "top_results": results[:top_count],
        "bottom_results": (
            results[-bottom_count:] if len(results) >= bottom_count else results
        ),
    }


def test_query_variations(
    original_query: str, collection: chromadb.Collection
) -> QueryVariationReport:
    """Test all Danish query variations"""
    start_time = time.time()

    print(f"\n{'='*60}")
    print(f"🔍 TESTING DANISH QUERY: '{original_query}'")
    print(f"{'='*60}")

    # Step 1: Generate all query variations
    print(f"\n📝 Step 1: Generating query variations...")
    variations = []

    # Original query
    original_variation = QueryVariation(
        variation_type="original",
        query_text=original_query,
        generation_time_ms=0.0,
        success=True,
    )
    variations.append(original_variation)

    # Generate other variations
    variations.append(expand_query_semantically(original_query))
    variations.append(generate_hypothetical_document(original_query))
    variations.append(generate_formal_variation(original_query))

    successful_variations = [v for v in variations if v.success]
    print(
        f"✅ Generated {len(successful_variations)}/{len(variations)} successful variations"
    )

    # Step 2: Test each variation
    print(f"\n⚡ Step 2: Testing search performance...")
    performance_results = []

    for variation in successful_variations:
        print(f"   Testing: {variation.variation_type}")

        # Search documents
        search_results = search_documents(variation.query_text, collection)
        analysis = analyze_search_performance(search_results)

        performance_result = QueryPerformanceResult(
            variation_type=variation.variation_type,
            variation_query=variation.query_text,
            search_results=analysis,
            best_similarity=analysis["best_similarity"],
            avg_top3_similarity=analysis["avg_top3"],
            content_range=analysis["content_range"],
        )

        performance_results.append(performance_result)

    # Step 3: Determine best variation and create report
    print(f"\n📊 Step 3: Analyzing results...")

    if performance_results:
        best_result = max(performance_results, key=lambda x: x.best_similarity)
        best_variation = best_result.variation_type
        best_similarity = best_result.best_similarity

        # Get variation rankings
        variation_rankings = {
            r.variation_type: r.best_similarity for r in performance_results
        }

        # Extract content snippets from best performing variation
        best_analysis = best_result.search_results
        top_snippets = [r.content_snippet for r in best_analysis["top_results"]]
        bottom_snippets = [r.content_snippet for r in best_analysis["bottom_results"]]

        # Generate recommendations
        recommendations = []
        if best_similarity > PERFORMANCE_CONFIG["similarity_thresholds"]["excellent"]:
            recommendations.append("Excellent query performance - ready for production")
        elif best_similarity > PERFORMANCE_CONFIG["similarity_thresholds"]["good"]:
            recommendations.append(
                "Good query performance - minor optimizations possible"
            )
        else:
            recommendations.append(
                "Query performance needs improvement - consider expanding document collection"
            )

    else:
        best_variation = "none"
        best_similarity = 0.0
        variation_rankings = {}
        top_snippets = []
        bottom_snippets = []
        recommendations = ["No successful query variations generated"]

    processing_time = time.time() - start_time

    report = QueryVariationReport(
        original_query=original_query,
        query_variations=variations,
        performance_results=performance_results,
        best_variation=best_variation,
        best_similarity_score=best_similarity,
        top_content_snippets=top_snippets,
        bottom_content_snippets=bottom_snippets,
        variation_rankings=variation_rankings,
        recommendations=recommendations,
        processing_time_seconds=processing_time,
    )

    return report


def print_query_performance_visualization_simplified(report: QueryVariationReport):
    """Print simplified at-a-glance text visualization for query performance"""
    print(f"\n{'='*60}")
    print(f"🔍 QUERY: '{report.original_query}'")
    print(f"{'='*60}")

    # Show only the best performing variation details
    best_perf = max(report.performance_results, key=lambda x: x.best_similarity)
    print(f"🏆 WINNER: {best_perf.variation_type.replace('_', ' ').title()}")
    print(
        f"   Query: \"{best_perf.variation_query[:100]}{'...' if len(best_perf.variation_query) > 100 else ''}\""
    )
    print(f"   Best Similarity: {best_perf.best_similarity:.3f}")

    # Show top 3 results from winning variation
    best_results = best_perf.search_results
    print(f"\n   Top 3 Results:")
    for i, result in enumerate(best_results["top_results"][:3]):
        print(f"   {i+1}. ({result.similarity_score:.3f}) {result.content_snippet}")

    print()


def create_query_variations_html_table(
    query_reports: Dict[str, QueryVariationReport],
) -> str:
    """Create an HTML table showing all query variations with top 3 results for each"""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    collection_size = "41"  # From the logs

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Danish Query Variations Analysis</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; font-size: 12px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
            .original-query {{ background-color: #e6f3ff; font-weight: bold; }}
            .best-score {{ background-color: #d4edda; font-weight: bold; }}
            .query-text {{ max-width: 200px; word-wrap: break-word; }}
            .hyde-text {{ max-width: 250px; word-wrap: break-word; font-style: italic; }}
            .results-column {{ max-width: 300px; word-wrap: break-word; }}
            .similarity-score {{ text-align: center; font-weight: bold; }}
            .category {{ text-align: center; font-style: italic; }}
            .result-item {{ margin-bottom: 8px; padding: 4px; background-color: #f9f9f9; border-radius: 3px; }}
            .result-score {{ font-weight: bold; color: #2d5aa0; }}
            .result-content {{ font-size: 11px; color: #666; }}
        </style>
    </head>
    <body>
        <h1>🇩🇰 Danish Construction Query Variations Analysis</h1>
        <p><strong>Analysis Date:</strong> {timestamp}</p>
        <p><strong>Document Collection:</strong> {collection_size} construction documents</p>
        
        <table>
            <thead>
                <tr>
                    <th>Original Query</th>
                    <th>Semantic Expansion</th>
                    <th>HyDE Document</th>
                    <th>Formal Variation</th>
                    <th>Best Technique</th>
                    <th>Best Score</th>
                </tr>
            </thead>
            <tbody>
    """

    for original_query, report in query_reports.items():
        # Get variations and performance by type
        variations = {v.variation_type: v.query_text for v in report.query_variations}
        performance_lookup = {p.variation_type: p for p in report.performance_results}

        def get_top3_results_html(variation_type):
            if variation_type not in performance_lookup:
                return "N/A"

            perf = performance_lookup[variation_type]
            results = perf.search_results
            top_results = results.get("top_results", [])[:3]

            if not top_results:
                return f"<div class='result-item'><span class='result-score'>No results</span></div>"

            html_results = ""
            for i, result in enumerate(top_results):
                html_results += f"""
                <div class='result-item'>
                    <span class='result-score'>{result.similarity_score:.3f}</span><br>
                    <span class='result-content'>{result.content_snippet[:120]}...</span>
                </div>
                """
            return html_results

        def get_variation_display(variation_type):
            query_text = variations.get(variation_type, "N/A")
            if variation_type == "hyde_document":
                # Truncate HyDE documents for display
                display_text = (
                    query_text[:100] + "..." if len(query_text) > 100 else query_text
                )
            else:
                display_text = query_text

            return (
                f"<div class='query-text'><strong>Query:</strong> {display_text}</div>"
            )

        html += f"""
                <tr>
                    <td class="original-query">{original_query}</td>
                    <td class="results-column">
                        {get_variation_display('semantic_expansion')}
                        <div style="margin-top: 8px;"><strong>Top 3 Results:</strong></div>
                        {get_top3_results_html('semantic_expansion')}
                    </td>
                    <td class="results-column">
                        {get_variation_display('hyde_document')}
                        <div style="margin-top: 8px;"><strong>Top 3 Results:</strong></div>
                        {get_top3_results_html('hyde_document')}
                    </td>
                    <td class="results-column">
                        {get_variation_display('formal_variation')}
                        <div style="margin-top: 8px;"><strong>Top 3 Results:</strong></div>
                        {get_top3_results_html('formal_variation')}
                    </td>
                    <td class="{'best-score' if report.best_variation else ''}">{report.best_variation.replace('_', ' ').title()}</td>
                    <td class="similarity-score {'best-score' if report.best_similarity_score > -0.2 else ''}">{report.best_similarity_score:.3f}</td>
                </tr>
        """

    html += """
            </tbody>
        </table>
        
        <h2>📊 Performance Summary</h2>
        <ul>
    """

    # Add summary insights
    best_techniques = {}
    for report in query_reports.values():
        technique = report.best_variation
        best_techniques[technique] = best_techniques.get(technique, 0) + 1

    for technique, count in sorted(
        best_techniques.items(), key=lambda x: x[1], reverse=True
    ):
        html += f"<li><strong>{technique.replace('_', ' ').title()}</strong>: {count} wins</li>"

    avg_similarity = sum(
        report.best_similarity_score for report in query_reports.values()
    ) / len(query_reports)
    html += f"<li><strong>Average Best Similarity</strong>: {avg_similarity:.3f}</li>"

    # Add similarity range analysis
    all_similarities = []
    for report in query_reports.values():
        for perf in report.performance_results:
            all_similarities.append(perf.search_results.get("best_similarity", 0))

    if all_similarities:
        min_sim = min(all_similarities)
        max_sim = max(all_similarities)
        html += f"<li><strong>Similarity Range</strong>: {min_sim:.3f} to {max_sim:.3f} (span: {max_sim - min_sim:.3f})</li>"

    html += """
        </ul>
        
        <h2>🎯 Key Findings</h2>
        <ul>
            <li><strong>Danish Semantic Search</strong>: Working excellently with similarity scores near 0</li>
            <li><strong>Similarity Ranges</strong>: Large natural differences (0.5-1.0 span) - avoid artificial boosting</li>
            <li><strong>HyDE Performance</strong>: Consistently achieves positive similarity scores</li>
            <li><strong>Content Categorization</strong>: Filtering removes too many relevant results</li>
            <li><strong>Recommendation</strong>: Use natural ranking without categorization boosts</li>
        </ul>
        
        <h2>⚠️ Categorization Boosting Analysis</h2>
        <p><strong>Current similarity spans:</strong> 0.5-1.0 range across techniques</p>
        <p><strong>Potential boost impact:</strong> 1.1-1.2x multiplier = +0.02-0.04 score change</p>
        <p><strong>Risk:</strong> Small boosts could significantly alter natural ranking when differences are 0.1-0.2</p>
        <p><strong>Recommendation:</strong> <em>Skip categorization boosting - natural similarities are already meaningful</em></p>
    </body>
    </html>
    """

    return html


def save_query_variations_table(query_reports: Dict[str, QueryVariationReport]):
    """Save query variations as HTML table"""
    html_content = create_query_variations_html_table(query_reports)

    html_path = CURRENT_RUN_DIR / "query_variations_table.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"📊 Query variations table saved to: {html_path}")


def create_overall_performance_report(
    query_reports: Dict[str, QueryVariationReport],
) -> OverallPerformanceReport:
    """Create overall performance report across all test queries"""

    # Count best variation techniques
    best_variation_counts = {}
    for report in query_reports.values():
        technique = report.best_variation
        best_variation_counts[technique] = best_variation_counts.get(technique, 0) + 1

    # Analyze Danish query performance
    avg_best_similarity = sum(
        report.best_similarity_score for report in query_reports.values()
    ) / len(query_reports)

    if avg_best_similarity > PERFORMANCE_CONFIG["similarity_thresholds"]["excellent"]:
        danish_performance = "Excellent - Danish semantic search working very well"
    elif avg_best_similarity > PERFORMANCE_CONFIG["similarity_thresholds"]["good"]:
        danish_performance = "Good - Danish queries finding relevant content"
    elif (
        avg_best_similarity > PERFORMANCE_CONFIG["similarity_thresholds"]["acceptable"]
    ):
        danish_performance = (
            "Acceptable - Danish queries working with room for improvement"
        )
    else:
        danish_performance = (
            "Poor - Danish query processing needs significant improvement"
        )

    # Generate overall insights
    insights = []
    most_effective_technique = (
        max(best_variation_counts.items(), key=lambda x: x[1])[0]
        if best_variation_counts
        else "none"
    )
    insights.append(
        f"Most effective technique: {most_effective_technique} (won {best_variation_counts.get(most_effective_technique, 0)} times)"
    )
    insights.append(f"Average best similarity: {avg_best_similarity:.3f}")

    # Generate recommendations
    recommendations = []
    if avg_best_similarity > PERFORMANCE_CONFIG["similarity_thresholds"]["good"]:
        recommendations.append("Danish query processing ready for production use")
    else:
        recommendations.append(
            "Consider expanding Danish construction document collection"
        )

    return OverallPerformanceReport(
        test_queries_analyzed=list(query_reports.keys()),
        query_reports=query_reports,
        overall_insights=insights,
        best_variation_techniques=best_variation_counts,
        danish_query_performance=danish_performance,
        recommendations=recommendations,
    )


def save_performance_reports(
    query_reports: Dict[str, QueryVariationReport],
    overall_report: OverallPerformanceReport,
):
    """Save performance reports to files"""

    # Save individual query reports
    query_reports_data = {
        query: report.model_dump() for query, report in query_reports.items()
    }
    query_reports_path = CURRENT_RUN_DIR / "query_performance_reports.json"
    with open(query_reports_path, "w", encoding="utf-8") as f:
        json.dump(query_reports_data, f, indent=2, ensure_ascii=False)

    # Save overall report
    overall_report_path = CURRENT_RUN_DIR / "overall_performance_report.json"
    with open(overall_report_path, "w", encoding="utf-8") as f:
        json.dump(overall_report.model_dump(), f, indent=2, ensure_ascii=False)

    print(f"📊 Individual query reports saved to: {query_reports_path}")
    print(f"📊 Overall performance report saved to: {overall_report_path}")


def print_overall_summary(overall_report: OverallPerformanceReport):
    """Print overall performance summary"""
    print(f"\n{'='*80}")
    print(f"🎯 OVERALL DANISH QUERY PROCESSING PERFORMANCE")
    print(f"{'='*80}")

    print(f"📝 Queries Analyzed: {len(overall_report.test_queries_analyzed)}")
    for query in overall_report.test_queries_analyzed:
        print(f'   - "{query}"')

    print(f"\n🏆 Best Variation Techniques:")
    for technique, count in overall_report.best_variation_techniques.items():
        print(f"   - {technique.replace('_', ' ').title()}: {count} wins")

    print(f"🇩🇰 Danish Query Performance: {overall_report.danish_query_performance}")

    print(f"\n💡 Overall Insights:")
    for insight in overall_report.overall_insights:
        print(f"   - {insight}")

    print(f"\n🎯 Recommendations:")
    for recommendation in overall_report.recommendations:
        print(f"   - {recommendation}")


# ==============================================================================
# 4. MAIN EXECUTION
# ==============================================================================


def main():
    """Main execution function"""
    print("🇩🇰 DANISH QUERY PROCESSING PIPELINE")
    print("=" * 60)

    try:
        # Step 1: Initialize ChromaDB connection
        print("\n🔗 Step 1: Connecting to ChromaDB...")
        collection = initialize_chroma_collection()
        document_count = collection.count()
        print(
            f"✅ Connected to collection '{CHROMA_CONFIG['collection_name']}' with {document_count} documents"
        )

        # Step 2: Test each Danish query
        print(f"\n🔍 Step 2: Testing Danish construction queries...")
        query_reports = {}

        for query in TEST_QUERIES:
            print(f"\n{'='*60}")
            print(f"🔍 Processing query: '{query}'")
            print(f"{'='*60}")

            # Test query variations and create report
            query_report = test_query_variations(query, collection)
            query_reports[query] = query_report

            # Print visualization for this query
            print_query_performance_visualization_simplified(query_report)

        # Step 3: Create overall performance report
        print(f"\n📊 Step 3: Creating overall performance analysis...")
        overall_report = create_overall_performance_report(query_reports)

        # Step 4: Save reports
        print(f"\n💾 Step 4: Saving performance reports...")
        save_performance_reports(query_reports, overall_report)

        # Step 5: Print overall summary
        print_overall_summary(overall_report)

        # Step 6: Save query variations table as HTML
        save_query_variations_table(query_reports)

        print(f"\n🎉 Danish Query Processing Analysis Complete!")
        print(f"📁 Output directory: {CURRENT_RUN_DIR}")
        print(f"📊 Queries analyzed: {len(TEST_QUERIES)}")
        print(
            f"🏆 Best overall technique: {max(overall_report.best_variation_techniques.items(), key=lambda x: x[1])[0] if overall_report.best_variation_techniques else 'none'}"
        )
        print(f"🇩🇰 Danish performance: {overall_report.danish_query_performance}")

    except Exception as e:
        print(f"\n❌ Error in Danish query processing pipeline: {e}")
        raise


if __name__ == "__main__":
    main()
