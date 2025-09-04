"""
Baseline Danish query test for retrieval system refactoring.

This test captures the current behavior of the query pipeline with Danish construction queries
to ensure no regression when extracting shared retrieval components.

Test query: "Hvad er kravene til brandsikkerhed i tagkonstruktioner?"
(What are the requirements for fire safety in roof constructions?)

Enhanced version that uses actual retrieval logic and exports results to CSV.

You can run different queries for that specific indexing run in several ways:

  🚀 Method 1: Using the convenience function (Recommended)

  python -c "
  import asyncio
  import sys
  sys.path.append('.')
  from tests.integration.test_danish_query_baseline import run_query_with_indexing_run

  # Run your query
  asyncio.run(run_query_with_indexing_run(
      'YOUR_QUERY_HERE',
      '163b73e6-637d-4096-a199-dce1122999d5'
  ))
  "

  Example:
  python -c "
  import asyncio
  import sys
  sys.path.append('.')
  from tests.integration.test_danish_query_baseline import run_query_with_indexing_run

  asyncio.run(run_query_with_indexing_run(
      'Hvilke materialer bruges til isolering?',
      '163b73e6-637d-4096-a199-dce1122999d5'
  ))
  "

  🔄 Method 2: Run multiple queries at once

  python -c "
  import asyncio
  import sys
  sys.path.append('.')
  from tests.integration.test_danish_query_baseline import run_query_with_indexing_run

  async def run_multiple():
      queries = [
          'Hvad er kravene til ventilation?',
          'Hvilke materialer bruges til isolering?',
          'Hvad er standarder for el-installation?',
          'Hvordan håndteres brandkrav?',
          'Hvilke sikkerhedskrav skal opfyldes?'
      ]

      run_id = '163b73e6-637d-4096-a199-dce1122999d5'

      for query in queries:
          print(f'\n--- Running: {query} ---')
          await run_query_with_indexing_run(query, run_id)

  asyncio.run(run_multiple())
  "
"""

import asyncio
import csv
from datetime import datetime
from pathlib import Path

import pytest

from src.config.database import get_supabase_admin_client
from src.pipeline.querying.models import QueryRequest, QueryResponse, QueryVariations
from src.pipeline.querying.orchestrator import QueryPipelineOrchestrator
from src.pipeline.querying.steps.retrieval import DocumentRetriever, RetrievalConfig
from src.services.config_service import ConfigService


class TestDanishQueryBaseline:
    """Baseline test to capture current Danish query behavior"""

    @pytest.fixture
    def test_query(self) -> str:
        """Danish construction query for testing"""
        return "Hvad er kravene til brandsikkerhed i tagkonstruktioner?"

    @pytest.fixture
    def orchestrator(self) -> QueryPipelineOrchestrator:
        """Query pipeline orchestrator"""
        return QueryPipelineOrchestrator()

    @pytest.mark.asyncio
    async def test_danish_query_baseline_behavior(self, orchestrator, test_query):
        """
        Capture baseline behavior for Danish query processing.

        This test documents the current behavior and will be used to validate
        that refactoring doesn't break Danish language processing.
        """
        print(f"\n🧪 BASELINE TEST: Testing Danish query: '{test_query}'")

        # Create request
        request = QueryRequest(query=test_query, user_id="baseline-test-user")

        # Record start time
        start_time = datetime.utcnow()

        # Execute pipeline
        response = await orchestrator.process_query(request)

        # Record end time
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Validate response structure
        assert isinstance(response, QueryResponse)
        assert isinstance(response.response, str)
        assert isinstance(response.search_results, list)
        assert isinstance(response.performance_metrics, dict)

        # Document baseline behavior
        baseline_results = {
            "test_metadata": {
                "query": test_query,
                "test_timestamp": datetime.utcnow().isoformat(),
                "response_time_ms": response_time_ms,
            },
            "response_analysis": {
                "response_length": len(response.response),
                "response_preview": response.response[:200] + "..."
                if len(response.response) > 200
                else response.response,
                "has_danish_text": self._contains_danish_text(response.response),
                "has_citations": "[" in response.response and "]" in response.response,
            },
            "retrieval_analysis": {
                "results_count": len(response.search_results),
                "similarity_scores": [result.similarity_score for result in response.search_results],
                "top_similarity": max([result.similarity_score for result in response.search_results])
                if response.search_results
                else 0.0,
                "avg_similarity": sum([result.similarity_score for result in response.search_results])
                / len(response.search_results)
                if response.search_results
                else 0.0,
                "source_files": list(set([result.source_filename for result in response.search_results])),
                "content_preview": [result.content[:100] + "..." for result in response.search_results[:3]],
            },
            "performance_metrics": response.performance_metrics,
            "quality_metrics": response.quality_metrics.model_dump(exclude_none=True)
            if response.quality_metrics
            else None,
            "step_timings": getattr(response, "step_timings", {}),
        }

        # Print detailed baseline results
        print("\n📊 BASELINE RESULTS:")
        print(f"   Response time: {response_time_ms}ms")
        print(f"   Retrieved chunks: {len(response.search_results)}")
        print(f"   Top similarity: {baseline_results['retrieval_analysis']['top_similarity']:.4f}")
        print(f"   Avg similarity: {baseline_results['retrieval_analysis']['avg_similarity']:.4f}")
        print(f"   Source files: {len(baseline_results['retrieval_analysis']['source_files'])}")
        print(f"   Response length: {len(response.response)} chars")
        print(f"   Contains Danish: {baseline_results['response_analysis']['has_danish_text']}")
        print(f"   Has citations: {baseline_results['response_analysis']['has_citations']}")

        # Print response preview
        print("\n📝 RESPONSE PREVIEW:")
        print(f"   '{response.response[:300]}...'")

        # Print similarity scores
        if response.search_results:
            print("\n🔍 SIMILARITY SCORES:")
            for i, result in enumerate(response.search_results[:5], 1):
                print(f"   {i}: {result.similarity_score:.4f} - {result.source_filename} (page {result.page_number})")

        # Store baseline for comparison (optional - could save to file for later comparison)
        self.baseline_results = baseline_results

        # Core assertions to ensure basic functionality
        assert len(response.search_results) > 0, "Should retrieve at least some results"
        assert response.response.strip() != "", "Should generate a non-empty response"
        assert baseline_results["retrieval_analysis"]["top_similarity"] > 0.2, "Should find reasonably similar content"
        assert baseline_results["response_analysis"]["has_danish_text"], "Response should contain Danish text"

        print("\n✅ BASELINE TEST COMPLETED - Results captured for comparison")

        return baseline_results

    @pytest.mark.asyncio
    async def test_danish_query_retrieval_details(self, orchestrator, test_query):
        """
        Detailed test of retrieval step for Danish queries.

        This test focuses specifically on the retrieval behavior to ensure
        pgvector search and Danish similarity thresholds work correctly.
        """
        print(f"\n🔍 RETRIEVAL DETAILS TEST: Testing retrieval for: '{test_query}'")

        # Access the retriever directly to test retrieval behavior
        retriever = orchestrator.retriever

        # Test embedding generation for Danish text
        query_embedding = await retriever.embed_query(test_query)

        # Validate embedding properties
        assert len(query_embedding) == 1024, f"Expected 1024 dimensions, got {len(query_embedding)}"
        assert all(isinstance(x, (int, float)) for x in query_embedding), "Embedding should contain only numbers"

        # Test query variations processing
        query_processor = orchestrator.query_processor
        variations_result = await query_processor.execute(test_query)

        assert variations_result.status == "completed", f"Query processing failed: {variations_result.error_message}"

        # Test retrieval with variations
        from src.pipeline.querying.models import to_query_variations

        variations = to_query_variations(variations_result.sample_outputs)

        retrieval_result = await retriever.execute(variations)

        assert retrieval_result.status == "completed", f"Retrieval failed: {retrieval_result.error_message}"

        # Document retrieval behavior
        from src.pipeline.querying.models import to_search_results

        search_results = to_search_results(retrieval_result.sample_outputs)

        print("\n📊 RETRIEVAL ANALYSIS:")
        print(f"   Embedding dimensions: {len(query_embedding)}")
        print(
            f"   Query variations: {len([v for v in [variations.semantic, variations.hyde, variations.formal] if v])}"
        )
        print(f"   Retrieved results: {len(search_results)}")

        if search_results:
            similarities = [r.similarity_score for r in search_results]
            print(f"   Similarity range: {min(similarities):.4f} - {max(similarities):.4f}")
            print(f"   Above 0.5: {len([s for s in similarities if s > 0.5])}")
            print(f"   Above 0.3: {len([s for s in similarities if s > 0.3])}")

        # Validate retrieval meets Danish language expectations
        assert len(search_results) > 0, "Should retrieve results for Danish query"
        assert max([r.similarity_score for r in search_results]) > 0.25, (
            "Should find reasonably similar content with Danish thresholds"
        )

        print("✅ RETRIEVAL DETAILS TEST COMPLETED")

        return {
            "embedding_dims": len(query_embedding),
            "variations_count": len([v for v in [variations.semantic, variations.hyde, variations.formal] if v]),
            "results_count": len(search_results),
            "similarity_scores": [r.similarity_score for r in search_results],
        }

    @pytest.mark.asyncio
    async def test_direct_retrieval_with_csv_export(self, test_query, indexing_run_id: str = None):
        """
        Test direct retrieval using actual DocumentRetriever logic and export to CSV.

        This test uses the same retrieval logic as the production pipeline
        and exports the top 10 results with similarity scores to a CSV file.

        Args:
            test_query: The query to test
            indexing_run_id: Optional indexing run ID to restrict search to specific documents
        """
        search_scope = f"indexing run {indexing_run_id[:8]}..." if indexing_run_id else "all indexing runs"
        print(f"\n📊 DIRECT RETRIEVAL + CSV EXPORT: Testing query: '{test_query}'")
        print(f"🎯 Search scope: {search_scope}")

        # Load pipeline configuration like production
        config_service = ConfigService()
        query_config = config_service.get_effective_config("query")
        retrieval_config_data = query_config.get("retrieval", {})

        # Create retrieval config using production settings
        retrieval_config = RetrievalConfig(retrieval_config_data)

        # Initialize DocumentRetriever with production config
        retriever = DocumentRetriever(retrieval_config)

        print("🔧 RETRIEVAL CONFIG:")
        print(f"   Model: {retrieval_config.embedding_model}")
        print(f"   Dimensions: {retrieval_config.dimensions}")
        print(f"   Top K: {retrieval_config.top_k}")
        print(f"   Similarity metric: {retrieval_config.similarity_metric}")

        # Create query variations (using original query for all variations to match production)
        query_variations = QueryVariations(
            original=test_query,
            semantic=test_query,  # In production, this would be generated by query processor
            hyde=test_query,  # In production, this would be generated by query processor
            formal=test_query,  # In production, this would be generated by query processor
        )

        # Record start time
        start_time = datetime.utcnow()

        # Execute retrieval step directly using production logic
        step_result = await retriever.execute(
            input_data=query_variations,
            indexing_run_id=indexing_run_id,  # Use specified indexing run or None for all
            allowed_document_ids=None,  # No document restrictions
        )

        # Record end time
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        # Validate step result
        assert step_result.status == "completed", f"Retrieval failed: {step_result.error_message}"

        # Extract search results from step result
        search_results_data = step_result.sample_outputs.get("search_results", [])

        print("\n📊 RETRIEVAL RESULTS:")
        print(f"   Response time: {response_time_ms}ms")
        print(f"   Retrieved results: {len(search_results_data)}")
        print(f"   Step duration: {step_result.duration_seconds:.2f}s")

        if search_results_data:
            similarities = [r["similarity_score"] for r in search_results_data]
            print(f"   Top similarity: {max(similarities):.4f}")
            print(f"   Average similarity: {sum(similarities) / len(similarities):.4f}")
            print(f"   Similarity range: {min(similarities):.4f} - {max(similarities):.4f}")

        # Export top 10 results to CSV
        csv_filename = await self._export_results_to_csv(
            test_query, search_results_data[:10], response_time_ms, step_result, indexing_run_id
        )

        print("\n💾 RESULTS EXPORTED TO MASTER LOG:")
        print(f"   CSV file: {csv_filename}")
        print(f"   Query added as new row with {len(search_results_data)} chunks in columns")

        # Print top 5 results for console verification
        print("\n🔍 TOP 5 RESULTS:")
        for i, result in enumerate(search_results_data[:5], 1):
            source = result.get("source_filename", "unknown")
            page = result.get("page_number", "N/A")
            similarity = result["similarity_score"]
            content_preview = result["content"][:100].replace("\n", " ").strip()
            print(f"   {i}: {similarity:.4f} - {source} (p.{page})")
            print(f"      '{content_preview}...'")

        # Validate results meet expectations
        assert len(search_results_data) > 0, "Should retrieve results for Danish query"
        assert max(similarities) > 0.2, "Should find reasonably similar content"

        print("✅ DIRECT RETRIEVAL TEST + CSV EXPORT COMPLETED")

        return {
            "query": test_query,
            "results_count": len(search_results_data),
            "response_time_ms": response_time_ms,
            "top_similarity": max(similarities) if similarities else 0.0,
            "avg_similarity": sum(similarities) / len(similarities) if similarities else 0.0,
            "csv_file": csv_filename,
            "step_result": step_result,
        }

    async def _export_results_to_csv(
        self, query: str, results: list[dict], response_time_ms: int, step_result, indexing_run_id: str = None
    ) -> str:
        """Export retrieval results to master CSV log file where each row is a query"""

        # Create output directory
        output_dir = Path("tests/output")
        output_dir.mkdir(exist_ok=True)

        # Master CSV log filename (fixed name, not timestamped)
        csv_filename = output_dir / "danish_query_master_log.csv"

        # Determine maximum number of columns needed (top 10 results)
        max_results = 10

        # Create dynamic fieldnames for results
        fieldnames = [
            "timestamp",
            "query",
            "indexing_run_id",
            "response_time_ms",
            "step_duration_s",
            "total_results_count",
            "status",
        ]

        # Add columns for each result (chunk_1, chunk_2, etc.)
        for i in range(1, max_results + 1):
            fieldnames.extend([f"chunk_{i}_similarity", f"chunk_{i}_source", f"chunk_{i}_page", f"chunk_{i}_content"])

        # Check if file exists to determine if we need header
        file_exists = csv_filename.exists()

        # Prepare row data
        row_data = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "indexing_run_id": indexing_run_id if indexing_run_id else "ALL_RUNS",
            "response_time_ms": response_time_ms,
            "step_duration_s": f"{step_result.duration_seconds:.2f}",
            "total_results_count": len(results),
            "status": step_result.status,
        }

        # Add result data for each chunk
        for i, result in enumerate(results[:max_results], 1):
            # Clean content for CSV (remove newlines and quotes)
            content = result["content"].replace("\n", " ").replace("\r", " ").replace('"', "'").strip()

            # Add similarity score and content to the cell
            similarity = result["similarity_score"]
            source = result.get("source_filename", "unknown")
            page = result.get("page_number", "N/A")

            # Format: "similarity_score | content"
            content_with_similarity = f"{similarity:.6f} | {content}"

            row_data[f"chunk_{i}_similarity"] = f"{similarity:.6f}"
            row_data[f"chunk_{i}_source"] = source
            row_data[f"chunk_{i}_page"] = page
            row_data[f"chunk_{i}_content"] = content_with_similarity

        # Fill empty columns for unused result slots
        for i in range(len(results) + 1, max_results + 1):
            row_data[f"chunk_{i}_similarity"] = ""
            row_data[f"chunk_{i}_source"] = ""
            row_data[f"chunk_{i}_page"] = ""
            row_data[f"chunk_{i}_content"] = ""

        # Write to CSV (append mode)
        with open(csv_filename, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header only if file is new
            if not file_exists:
                writer.writeheader()

            # Write the query row
            writer.writerow(row_data)

        return str(csv_filename)

    def _contains_danish_text(self, text: str) -> bool:
        """Check if text contains Danish-specific characters or words"""
        danish_indicators = [
            "æ",
            "ø",
            "å",
            "Æ",
            "Ø",
            "Å",  # Danish letters
            "og",
            "er",
            "til",
            "for",
            "med",
            "på",
            "af",
            "ikke",  # Common Danish words
            "skal",
            "kan",
            "vil",
            "må",
            "bør",  # Danish modal verbs
        ]
        return any(indicator in text for indicator in danish_indicators)


if __name__ == "__main__":
    """Run baseline test directly"""
    import asyncio

    from dotenv import load_dotenv

    # Load environment
    load_dotenv()

    async def run_baseline():
        test = TestDanishQueryBaseline()
        orchestrator = QueryPipelineOrchestrator()
        query = "Hvad er kravene til brandsikkerhed i tagkonstruktioner?"

        print("🧪 Running Danish Query Baseline Test...")
        baseline = await test.test_danish_query_baseline_behavior(orchestrator, query)

        print("\n🔍 Running Retrieval Details Test...")
        retrieval_details = await test.test_danish_query_retrieval_details(orchestrator, query)

        print("\n📊 Running Direct Retrieval + CSV Export Test...")
        csv_results = await test.test_direct_retrieval_with_csv_export(query)

        print("\n📋 COMPLETE BASELINE CAPTURED ✅")
        print(f"CSV Export: {csv_results['csv_file']}")
        return baseline, retrieval_details, csv_results

    async def run_multiple_queries_to_master_log(indexing_run_id: str = None):
        """Run multiple different queries to build up the master log for comparison

        Args:
            indexing_run_id: Optional indexing run ID to restrict search to specific documents
        """
        test = TestDanishQueryBaseline()

        # Test queries for comparison
        queries = [
            "Hvad er kravene til brandsikkerhed i tagkonstruktioner?",
            "Hvilke materialer bruges til tagkonstruktioner?",
            "Hvad er standardafstand for spær?",
            "Hvordan håndteres regnvand på taget?",
            "Hvilke isoleringsmaterialer anbefales?",
        ]

        search_scope = f"indexing run {indexing_run_id[:8]}..." if indexing_run_id else "all indexing runs"
        print("🚀 Running Multiple Queries to Build Master Log...")
        print(f"🎯 Search scope: {search_scope}")
        print(f"Will run {len(queries)} different queries to demonstrate query comparison")

        csv_file = None
        for i, query in enumerate(queries, 1):
            print(f"\n📝 Query {i}/{len(queries)}: {query}")
            try:
                result = await test.test_direct_retrieval_with_csv_export(query, indexing_run_id)
                csv_file = result["csv_file"]
                print(f"   ✅ Added to master log: {result['results_count']} chunks")
            except Exception as e:
                print(f"   ❌ Failed: {e}")

        print("\n📊 MASTER LOG COMPLETE")
        print(f"CSV file: {csv_file}")
        print(f"You can now compare {len(queries)} queries and their retrieved chunks!")

        return csv_file


async def list_available_indexing_runs():
    """List available indexing runs to help choose which one to query against"""
    supabase = get_supabase_admin_client()

    print("🗂️  Available Indexing Runs:")
    print("=" * 80)

    try:
        # Get indexing runs with their status and basic info
        response = (
            supabase.table("indexing_runs")
            .select("id, status, started_at, completed_at")
            .order("started_at", desc=True)
            .limit(20)
            .execute()
        )

        if not response.data:
            print("No indexing runs found.")
            return []

        runs = []
        for i, run in enumerate(response.data, 1):
            run_id = run["id"]
            status = run["status"]
            started = run.get("started_at", "Unknown")[:19] if run.get("started_at") else "Unknown"
            completed = run.get("completed_at", "In progress")[:19] if run.get("completed_at") else "In progress"

            # Format status with emoji
            status_emoji = {"completed": "✅", "processing": "🔄", "failed": "❌", "pending": "⏳"}.get(
                status.lower(), "❓"
            )

            print(f"{i:2d}. {status_emoji} {run_id}")
            print(f"    Status: {status}")
            print(f"    Started: {started}")
            print(f"    Completed: {completed}")
            print()

            runs.append(run_id)

        print("💡 To use a specific run, copy the ID and pass it to test_direct_retrieval_with_csv_export()")
        print(f"💡 Example: await test.test_direct_retrieval_with_csv_export('your query', '{runs[0]}')")

        return runs

    except Exception as e:
        print(f"❌ Error fetching indexing runs: {e}")
        return []


async def run_query_with_indexing_run(query: str, indexing_run_id: str):
    """Convenience method to run a single query against a specific indexing run"""
    test = TestDanishQueryBaseline()

    print("🔍 Running query against specific indexing run:")
    print(f"   Query: {query}")
    print(f"   Indexing Run: {indexing_run_id}")

    try:
        result = await test.test_direct_retrieval_with_csv_export(query, indexing_run_id)
        print(f"   ✅ Success: {result['results_count']} chunks retrieved")
        return result
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return None

    if __name__ == "__main__":
        asyncio.run(run_baseline())
