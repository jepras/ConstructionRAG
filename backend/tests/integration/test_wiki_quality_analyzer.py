"""
Wiki Quality Analyzer - Tests and evaluates the quality of existing wiki generation runs.

This test suite can be run on any existing wiki run to evaluate:
- Semantic coherence of pages
- Content coverage vs source documents  
- Structure quality (navigation, hierarchy)
- Citation accuracy
- Language consistency
"""

import asyncio
import json
import re
import statistics
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pytest
import httpx

from src.config.database import get_supabase_admin_client


class WikiQualityAnalyzer:
    """Analyzes quality metrics for wiki generation runs"""
    
    def __init__(self):
        self.db = get_supabase_admin_client()
        self.api_base = "http://localhost:8000/api"  # Adjust if needed
        self.metrics = {}
        
    async def analyze_wiki_run(self, wiki_run_id: str) -> Dict[str, Any]:
        """
        Main entry point to analyze a wiki run's quality.
        Returns comprehensive quality metrics.
        """
        print(f"\n{'='*60}")
        print(f"📊 WIKI QUALITY ANALYSIS")
        print(f"Wiki Run ID: {wiki_run_id}")
        print(f"{'='*60}\n")
        
        # Fetch wiki data
        wiki_data = await self._fetch_wiki_data(wiki_run_id)
        
        if not wiki_data:
            raise ValueError(f"Wiki run {wiki_run_id} not found or has no content")
        
        # Run quality assessments
        coherence_metrics = await self._analyze_semantic_coherence(wiki_data)
        coverage_metrics = await self._analyze_content_coverage(wiki_data)
        structure_metrics = await self._analyze_structure_quality(wiki_data)
        citation_metrics = await self._analyze_citation_quality(wiki_data)
        language_metrics = await self._analyze_language_consistency(wiki_data)
        
        # Calculate overall quality score
        overall_score = self._calculate_overall_score({
            "coherence": coherence_metrics,
            "coverage": coverage_metrics,
            "structure": structure_metrics,
            "citations": citation_metrics,
            "language": language_metrics
        })
        
        # Compile final report
        report = {
            "wiki_run_id": wiki_run_id,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "semantic_coherence": coherence_metrics,
                "content_coverage": coverage_metrics,
                "structure_quality": structure_metrics,
                "citation_accuracy": citation_metrics,
                "language_consistency": language_metrics
            },
            "overall_quality_score": overall_score,
            "recommendations": self._generate_recommendations(overall_score)
        }
        
        # Print summary
        self._print_analysis_summary(report)
        
        return report
    
    async def _fetch_wiki_data(self, wiki_run_id: str) -> Dict[str, Any]:
        """Fetch all wiki pages and metadata for a run"""
        print("📥 Fetching wiki data...")
        
        # Get wiki run details from database
        wiki_run = self.db.table("wiki_generation_runs").select("*").eq("id", wiki_run_id).execute()
        if not wiki_run.data:
            return None
            
        wiki_run_data = wiki_run.data[0]
        
        # Get pages metadata from wiki run
        pages_metadata = wiki_run_data.get("pages_metadata", [])
        
        # Fetch actual page content for each page
        pages = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for page_meta in pages_metadata:
                # Try to fetch from storage URL directly first
                storage_url = page_meta.get("storage_url")
                if storage_url:
                    try:
                        response = await client.get(storage_url)
                        if response.status_code == 200:
                            pages.append({
                                "page_name": page_meta.get("title", page_meta.get("filename", "")),
                                "content": response.text,
                                "metadata": page_meta
                            })
                            continue
                    except Exception:
                        pass  # Fall back to API method
                
                # Fall back to API method
                page_name = page_meta.get("filename", "").replace(".md", "")
                try:
                    response = await client.get(
                        f"{self.api_base}/wiki/runs/{wiki_run_id}/pages/{page_name}"
                    )
                    if response.status_code == 200:
                        page_data = response.json()
                        pages.append({
                            "page_name": page_meta.get("title", page_name),
                            "content": page_data.get("content", ""),
                            "metadata": page_meta
                        })
                except Exception as e:
                    print(f"  ⚠️ Could not fetch page {page_name}: {e}")
        
        # Get indexing run details for source documents
        indexing_run_id = wiki_run_data.get("indexing_run_id")
        indexing_run = self.db.table("indexing_runs").select("*").eq("id", indexing_run_id).execute() if indexing_run_id else None
        
        # Get source documents
        documents = self.db.table("documents").select("*").eq("index_run_id", indexing_run_id).execute() if indexing_run_id else None
        
        # Get chunks for coverage analysis - skip for now as chunks table doesn't exist
        chunks = None  # self.db.table("chunks").select("id, content, metadata").eq("index_run_id", indexing_run_id).limit(100).execute() if indexing_run_id else None
        
        print(f"  ✓ Found {len(pages)} wiki pages")
        print(f"  ✓ Found {len(documents.data) if documents and documents.data else 0} source documents")
        print(f"  ✓ Retrieved {len(chunks.data) if chunks and chunks.data else 0} sample chunks for analysis")
        
        return {
            "wiki_run": wiki_run_data,
            "pages": pages,
            "indexing_run": indexing_run.data[0] if indexing_run and indexing_run.data else None,
            "documents": documents.data if documents and documents.data else [],
            "chunks": chunks.data if chunks and chunks.data else []
        }
    
    async def _analyze_semantic_coherence(self, wiki_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze semantic coherence within and between pages"""
        print("\n🔍 Analyzing Semantic Coherence...")
        
        pages = wiki_data["pages"]
        coherence_scores = []
        
        for page in pages:
            content = page.get("content", "")
            
            # Check internal coherence (sections relate to page topic)
            sections = content.split("\n## ")
            if len(sections) > 1:
                # Simple coherence: ratio of sections that contain page title keywords
                page_title = page.get("page_name", "").lower()
                title_words = set(page_title.replace("_", " ").split())
                
                relevant_sections = sum(
                    1 for section in sections[1:]  # Skip first (intro)
                    if any(word in section.lower() for word in title_words)
                )
                
                coherence_score = relevant_sections / len(sections[1:]) if sections[1:] else 0
                coherence_scores.append(coherence_score)
        
        avg_coherence = statistics.mean(coherence_scores) if coherence_scores else 0
        
        # Check cross-page coherence (navigation references exist)
        cross_references = 0
        broken_references = 0
        page_names = {p["page_name"] for p in pages}
        
        for page in pages:
            content = page.get("content", "")
            # Find markdown links [text](link)
            import re
            links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content)
            
            for link_text, link_url in links:
                if link_url.startswith("#"):  # Internal wiki link
                    referenced_page = link_url[1:]  # Remove #
                    if referenced_page in page_names:
                        cross_references += 1
                    else:
                        broken_references += 1
        
        metrics = {
            "average_page_coherence": round(avg_coherence, 3),
            "cross_page_references": cross_references,
            "broken_references": broken_references,
            "coherence_rating": self._rate_score(avg_coherence),
            "details": {
                "pages_analyzed": len(pages),
                "average_sections_per_page": round(
                    statistics.mean([len(p.get("content", "").split("\n## ")) for p in pages]), 1
                )
            }
        }
        
        print(f"  ✓ Average coherence: {metrics['average_page_coherence']}")
        print(f"  ✓ Cross-references: {metrics['cross_page_references']}")
        print(f"  ✓ Rating: {metrics['coherence_rating']}")
        
        return metrics
    
    async def _analyze_content_coverage(self, wiki_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how well the wiki covers source document content"""
        print("\n📚 Analyzing Content Coverage...")
        
        pages = wiki_data["pages"]
        chunks = wiki_data.get("chunks", [])
        documents = wiki_data["documents"]
        
        # Calculate coverage metrics
        total_wiki_content = sum(len(p.get("content", "")) for p in pages)
        total_source_content = sum(len(c.get("content", "")) for c in chunks) * 10 if chunks else total_wiki_content * 5  # Estimate full corpus
        
        # Check document representation
        wiki_text = " ".join(p.get("content", "") for p in pages).lower()
        
        # Document coverage: which source docs are referenced
        docs_referenced = set()
        for doc in documents:
            doc_name = doc.get("filename", "").lower()
            if doc_name and doc_name in wiki_text:
                docs_referenced.add(doc_name)
        
        doc_coverage_ratio = len(docs_referenced) / len(documents) if documents else 0
        
        # Key terms coverage (sample from chunks or extract from wiki)
        chunk_terms = set()
        if chunks:
            for chunk in chunks[:50]:  # Sample first 50 chunks
                content = chunk.get("content", "")
                # Extract key terms (simple: words > 8 chars, likely domain-specific)
                words = re.findall(r'\b[a-zA-ZæøåÆØÅ]{8,}\b', content)
                chunk_terms.update(word.lower() for word in words[:5])  # Top 5 long words per chunk
        else:
            # Extract key terms from wiki pages themselves as a proxy
            for page in pages[:5]:
                content = page.get("content", "")[:1000]  # Sample first 1000 chars
                words = re.findall(r'\b[a-zA-ZæøåÆØÅ]{8,}\b', content)
                chunk_terms.update(word.lower() for word in words[:10])
        
        covered_terms = sum(1 for term in chunk_terms if term in wiki_text) if chunk_terms else len(chunk_terms)
        term_coverage_ratio = covered_terms / len(chunk_terms) if chunk_terms else 1.0
        
        metrics = {
            "document_coverage_ratio": round(doc_coverage_ratio, 3),
            "term_coverage_ratio": round(term_coverage_ratio, 3),
            "content_compression_ratio": round(total_wiki_content / total_source_content, 3),
            "coverage_rating": self._rate_score((doc_coverage_ratio + term_coverage_ratio) / 2),
            "details": {
                "documents_referenced": len(docs_referenced),
                "total_documents": len(documents),
                "key_terms_covered": covered_terms,
                "total_key_terms": len(chunk_terms),
                "wiki_size_chars": total_wiki_content
            }
        }
        
        print(f"  ✓ Document coverage: {metrics['document_coverage_ratio']:.1%}")
        print(f"  ✓ Term coverage: {metrics['term_coverage_ratio']:.1%}")
        print(f"  ✓ Rating: {metrics['coverage_rating']}")
        
        return metrics
    
    async def _analyze_structure_quality(self, wiki_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze wiki structure and navigation quality"""
        print("\n🏗️ Analyzing Structure Quality...")
        
        pages = wiki_data["pages"]
        
        # Analyze hierarchy and organization
        page_depths = []
        page_lengths = []
        
        for page in pages:
            content = page.get("content", "")
            page_lengths.append(len(content))
            
            # Count heading levels to determine depth
            h2_count = content.count("\n## ")
            h3_count = content.count("\n### ")
            depth_score = 1 if h2_count > 0 else 0
            depth_score += 0.5 if h3_count > 0 else 0
            page_depths.append(depth_score)
        
        # Check for table of contents or overview page
        has_toc = any("overview" in p.get("page_name", "").lower() or 
                     "index" in p.get("page_name", "").lower() or
                     "indhold" in p.get("page_name", "").lower()  # Danish for "contents"
                     for p in pages)
        
        # Balance check: standard deviation of page lengths
        length_balance = 1 - (statistics.stdev(page_lengths) / statistics.mean(page_lengths) 
                              if len(page_lengths) > 1 and statistics.mean(page_lengths) > 0 else 1)
        
        metrics = {
            "average_page_depth": round(statistics.mean(page_depths) if page_depths else 0, 2),
            "has_table_of_contents": has_toc,
            "page_count": len(pages),
            "length_balance_score": round(max(0, length_balance), 3),
            "structure_rating": self._rate_score(
                (statistics.mean(page_depths) / 1.5 if page_depths else 0) * 0.5 +
                (1 if has_toc else 0) * 0.3 +
                length_balance * 0.2
            ),
            "details": {
                "shortest_page": min(page_lengths) if page_lengths else 0,
                "longest_page": max(page_lengths) if page_lengths else 0,
                "average_page_length": round(statistics.mean(page_lengths) if page_lengths else 0)
            }
        }
        
        print(f"  ✓ Page count: {metrics['page_count']}")
        print(f"  ✓ Average depth: {metrics['average_page_depth']}")
        print(f"  ✓ Has TOC: {metrics['has_table_of_contents']}")
        print(f"  ✓ Rating: {metrics['structure_rating']}")
        
        return metrics
    
    async def _analyze_citation_quality(self, wiki_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze citation accuracy and completeness"""
        print("\n📝 Analyzing Citation Quality...")
        
        pages = wiki_data["pages"]
        documents = wiki_data["documents"]
        
        # Count citations
        total_citations = 0
        citation_formats = {"bracket": 0, "footnote": 0, "inline": 0}
        
        import re
        for page in pages:
            content = page.get("content", "")
            
            # Check different citation patterns
            bracket_citations = re.findall(r'\[[\d,\s]+\]', content)
            footnote_citations = re.findall(r'\[\^[\d]+\]', content)
            inline_citations = re.findall(r'\([^)]*\d{4}[^)]*\)', content)  # (Author, 2024) style
            
            citation_formats["bracket"] += len(bracket_citations)
            citation_formats["footnote"] += len(footnote_citations)  
            citation_formats["inline"] += len(inline_citations)
            
            total_citations += sum([len(bracket_citations), len(footnote_citations), len(inline_citations)])
        
        # Check if citations reference actual documents
        doc_names = {doc.get("filename", "").lower() for doc in documents}
        wiki_text = " ".join(p.get("content", "") for p in pages).lower()
        
        cited_docs = sum(1 for doc_name in doc_names if doc_name in wiki_text)
        
        citations_per_page = total_citations / len(pages) if pages else 0
        citation_coverage = cited_docs / len(documents) if documents else 0
        
        metrics = {
            "total_citations": total_citations,
            "citations_per_page": round(citations_per_page, 1),
            "citation_coverage_ratio": round(citation_coverage, 3),
            "dominant_citation_style": max(citation_formats, key=citation_formats.get) if total_citations > 0 else "none",
            "citation_rating": self._rate_score(min(1.0, citations_per_page / 5) * 0.7 + citation_coverage * 0.3),
            "details": {
                "citation_formats": citation_formats,
                "documents_cited": cited_docs,
                "total_source_documents": len(documents)
            }
        }
        
        print(f"  ✓ Total citations: {metrics['total_citations']}")
        print(f"  ✓ Citations/page: {metrics['citations_per_page']}")
        print(f"  ✓ Rating: {metrics['citation_rating']}")
        
        return metrics
    
    async def _analyze_language_consistency(self, wiki_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze language consistency and quality"""
        print("\n🌍 Analyzing Language Consistency...")
        
        pages = wiki_data["pages"]
        
        # Language detection patterns
        danish_indicators = ["og", "er", "af", "til", "på", "med", "for", "som", "har", "kan", "skal", "være", "denne", "deres"]
        english_indicators = ["the", "and", "is", "of", "to", "in", "with", "for", "that", "has", "can", "be", "this", "their"]
        
        language_scores = {"danish": 0, "english": 0, "mixed": 0}
        
        for page in pages:
            content = page.get("content", "").lower()
            words = content.split()[:200]  # Sample first 200 words
            
            danish_count = sum(1 for word in words if word in danish_indicators)
            english_count = sum(1 for word in words if word in english_indicators)
            
            if danish_count > english_count * 2:
                language_scores["danish"] += 1
            elif english_count > danish_count * 2:
                language_scores["english"] += 1
            else:
                language_scores["mixed"] += 1
        
        # Determine primary language
        primary_language = max(language_scores, key=language_scores.get)
        consistency_ratio = language_scores[primary_language] / len(pages) if pages else 0
        
        # Check for formatting consistency
        formatting_checks = {
            "has_headers": 0,
            "has_lists": 0,
            "has_code_blocks": 0,
            "has_tables": 0
        }
        
        for page in pages:
            content = page.get("content", "")
            if "## " in content or "### " in content:
                formatting_checks["has_headers"] += 1
            if "\n- " in content or "\n* " in content or "\n1. " in content:
                formatting_checks["has_lists"] += 1
            if "```" in content:
                formatting_checks["has_code_blocks"] += 1
            if "\n|" in content:
                formatting_checks["has_tables"] += 1
        
        avg_formatting_features = statistics.mean([
            v/len(pages) for v in formatting_checks.values()
        ]) if pages else 0
        
        metrics = {
            "primary_language": primary_language,
            "language_consistency_ratio": round(consistency_ratio, 3),
            "formatting_richness_score": round(avg_formatting_features, 3),
            "language_rating": self._rate_score(consistency_ratio * 0.7 + avg_formatting_features * 0.3),
            "details": {
                "language_distribution": language_scores,
                "formatting_features": {k: f"{v}/{len(pages)}" for k, v in formatting_checks.items()}
            }
        }
        
        print(f"  ✓ Primary language: {metrics['primary_language']}")
        print(f"  ✓ Consistency: {metrics['language_consistency_ratio']:.1%}")
        print(f"  ✓ Rating: {metrics['language_rating']}")
        
        return metrics
    
    def _calculate_overall_score(self, all_metrics: Dict[str, Dict]) -> Dict[str, Any]:
        """Calculate weighted overall quality score"""
        
        weights = {
            "coherence": 0.25,
            "coverage": 0.30,
            "structure": 0.20,
            "citations": 0.15,
            "language": 0.10
        }
        
        scores = {}
        for category, metrics in all_metrics.items():
            # Extract numeric rating (convert from text if needed)
            rating = metrics.get(f"{category.rstrip('s')}_rating", "")
            if rating == "Excellent":
                scores[category] = 1.0
            elif rating == "Good":
                scores[category] = 0.75
            elif rating == "Fair":
                scores[category] = 0.5
            elif rating == "Poor":
                scores[category] = 0.25
            else:
                scores[category] = 0
        
        weighted_score = sum(scores[cat] * weights[cat] for cat in weights)
        
        return {
            "overall_score": round(weighted_score, 3),
            "overall_rating": self._rate_score(weighted_score),
            "category_scores": scores,
            "weights_used": weights
        }
    
    def _rate_score(self, score: float) -> str:
        """Convert numeric score to rating"""
        if score >= 0.8:
            return "Excellent"
        elif score >= 0.6:
            return "Good"
        elif score >= 0.4:
            return "Fair"
        else:
            return "Poor"
    
    def _generate_recommendations(self, overall_score: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations based on scores"""
        recommendations = []
        scores = overall_score["category_scores"]
        
        if scores.get("coherence", 0) < 0.6:
            recommendations.append("Improve semantic coherence by ensuring sections relate closely to page topics")
        
        if scores.get("coverage", 0) < 0.6:
            recommendations.append("Increase content coverage by including more source document references")
        
        if scores.get("structure", 0) < 0.6:
            recommendations.append("Enhance structure with better hierarchy and a table of contents")
        
        if scores.get("citations", 0) < 0.6:
            recommendations.append("Add more citations to support claims and reference source materials")
        
        if scores.get("language", 0) < 0.6:
            recommendations.append("Improve language consistency across all wiki pages")
        
        if not recommendations:
            recommendations.append("Wiki quality is good. Consider minor refinements for perfection.")
        
        return recommendations
    
    def _print_analysis_summary(self, report: Dict[str, Any]):
        """Print formatted analysis summary"""
        print(f"\n{'='*60}")
        print("📊 ANALYSIS SUMMARY")
        print(f"{'='*60}")
        
        overall = report["overall_quality_score"]
        print(f"\n🏆 Overall Quality Score: {overall['overall_score']:.1%} ({overall['overall_rating']})")
        
        print("\n📈 Category Scores:")
        for category, score in overall["category_scores"].items():
            print(f"  • {category.capitalize()}: {score:.1%}")
        
        print("\n💡 Recommendations:")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"  {i}. {rec}")
        
        print(f"\n{'='*60}\n")


# Test function
@pytest.mark.asyncio
async def test_wiki_quality_analysis():
    """Test the wiki quality analyzer on a specific wiki run"""
    
    analyzer = WikiQualityAnalyzer()
    
    # Wiki run ID to analyze
    wiki_run_id = "518863ff-5c94-48d8-a7f9-a5473d930b7e"
    
    try:
        # Run analysis
        report = await analyzer.analyze_wiki_run(wiki_run_id)
        
        # Save report to file
        report_file = f"wiki_quality_report_{wiki_run_id[:8]}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 Full report saved to: {report_file}")
        
        # Assertions for test
        assert report is not None
        assert "overall_quality_score" in report
        assert report["overall_quality_score"]["overall_score"] >= 0
        assert report["overall_quality_score"]["overall_score"] <= 1
        
        # Check all metrics are present
        assert "semantic_coherence" in report["metrics"]
        assert "content_coverage" in report["metrics"]
        assert "structure_quality" in report["metrics"]
        assert "citation_accuracy" in report["metrics"]
        assert "language_consistency" in report["metrics"]
        
        print("\n✅ Wiki quality analysis completed successfully!")
        
        return report
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        raise


if __name__ == "__main__":
    # Run the analyzer directly
    import asyncio
    
    async def main():
        analyzer = WikiQualityAnalyzer()
        wiki_run_id = "518863ff-5c94-48d8-a7f9-a5473d930b7e"
        report = await analyzer.analyze_wiki_run(wiki_run_id)
        
        # Save report
        report_file = f"wiki_quality_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Report saved to: {report_file}")
    
    asyncio.run(main())