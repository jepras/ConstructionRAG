#!/usr/bin/env python3
"""
Compare different normalization and fusion methods for hybrid search
"""

import json
from pathlib import Path
from typing import Dict, Any


def load_results(run_dir: str) -> Dict[str, Any]:
    """Load results from a specific run directory"""
    results_file = Path(
        f"../../data/internal/08_retrieve/{run_dir}/query_retrieval_reports.json"
    )
    if results_file.exists():
        with open(results_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def compare_methods():
    """Compare min-max normalization vs RRF fusion"""

    # Load results from both runs
    minmax_results = load_results("08_run_20250723_140906")  # Min-max normalization
    rrf_results = load_results("08_run_20250723_141006")  # RRF fusion

    print("🔍 COMPARISON: Min-Max Normalization vs RRF Fusion")
    print("=" * 60)

    for query_name in [
        "regnvand",
        "omkostninger for opmåling og beregning",
        "projekt information",
    ]:
        print(f"\n📝 Query: '{query_name}'")
        print("-" * 40)

        if query_name in minmax_results and query_name in rrf_results:
            minmax_data = minmax_results[query_name]
            rrf_data = rrf_results[query_name]

            # Compare best combinations
            minmax_best = minmax_data.get("best_combination", "N/A")
            rrf_best = rrf_data.get("best_combination", "N/A")
            minmax_score = minmax_data.get("best_similarity_score", 0)
            rrf_score = rrf_data.get("best_similarity_score", 0)

            print(f"Min-Max Best: {minmax_best} (score: {minmax_score:.3f})")
            print(f"RRF Best:     {rrf_best} (score: {rrf_score:.3f})")

            # Compare hybrid results for the same query variation
            for variation in [
                "original",
                "semantic_expansion",
                "hyde_document",
                "formal_variation",
            ]:
                minmax_key = f"{variation}_hybrid_60_40"
                rrf_key = f"{variation}_hybrid_60_40"

                if (
                    minmax_key in minmax_data["matrix_results"]
                    and rrf_key in rrf_data["matrix_results"]
                ):
                    minmax_hybrid = minmax_data["matrix_results"][minmax_key]
                    rrf_hybrid = rrf_data["matrix_results"][rrf_key]

                    minmax_avg = minmax_hybrid.get("avg_top_3_similarity", 0)
                    rrf_avg = rrf_hybrid.get("avg_top_3_similarity", 0)

                    print(f"  {variation} hybrid (60/40):")
                    print(f"    Min-Max: {minmax_avg:.3f}")
                    print(f"    RRF:     {rrf_avg:.3f}")
                    print(f"    Diff:    {minmax_avg - rrf_avg:+.3f}")

    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)

    # Overall comparison
    minmax_avg = 0.755  # From the output
    rrf_avg = 0.287  # From the output

    print(f"Min-Max Normalization Average Similarity: {minmax_avg:.3f}")
    print(f"RRF Fusion Average Similarity:            {rrf_avg:.3f}")
    print(f"Difference:                               {minmax_avg - rrf_avg:+.3f}")

    print("\n💡 Key Insights:")
    print("• Min-Max normalization preserves score magnitudes and relationships")
    print("• RRF fusion focuses on ranking order, ignoring actual score values")
    print("• Min-Max typically gives higher average scores due to normalization")
    print("• RRF is more robust to outliers and different score distributions")
    print("• Both methods can be effective depending on the use case")


if __name__ == "__main__":
    compare_methods()
