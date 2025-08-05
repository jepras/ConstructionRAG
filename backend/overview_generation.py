#!/usr/bin/env python3
"""
ConstructionRAG - Automatic Overview Generation

This script generates a DeepWiki-style overview based on an indexing run's documents and chunks.
Focused on Danish construction projects with configurable language support.

Usage:
    python overview_generation.py --index-run-id fb335387-d2ff-4b93-a730-7ce55eb2fe03
    python overview_generation.py --index-run-id <id> --language english --model anthropic/claude-3.5-sonnet
"""

import os
import sys
import asyncio
import json
import argparse
import time
import re
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID
from collections import defaultdict, Counter
from datetime import datetime
import numpy as np
import requests
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from config.database import get_supabase_admin_client
from models.pipeline import IndexingRun, StepResult


class OverviewGenerator:
    """Generate automatic project overviews from indexing runs."""
    
    def __init__(self, language: str = "danish", model: str = "google/gemini-2.0-flash-exp", skip_api_key_check: bool = False):
        self.language = language
        self.model = model
        self.supabase = get_supabase_admin_client()
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not skip_api_key_check and not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
    
    def fetch_indexing_run_data(self, index_run_id: str) -> Dict[str, Any]:
        """Fetch complete indexing run data including documents and chunks."""
        print(f"Henter data for indexing run: {index_run_id}")
        
        # Get indexing run
        indexing_run_response = self.supabase.table("indexing_runs").select("*").eq("id", index_run_id).execute()
        
        if not indexing_run_response.data:
            raise ValueError(f"No indexing run found with ID: {index_run_id}")
        
        indexing_run = indexing_run_response.data[0]
        
        # Get documents in this indexing run
        documents_response = self.supabase.table("indexing_run_documents").select(
            "document_id, documents(*)"
        ).eq("indexing_run_id", index_run_id).execute()
        
        documents = [item["documents"] for item in documents_response.data if item["documents"]]
        document_ids = [doc["id"] for doc in documents]
        
        if not document_ids:
            raise ValueError(f"No documents found for indexing run: {index_run_id}")
        
        # Get all chunks for these documents with embeddings
        chunks_response = self.supabase.table("document_chunks").select(
            "*, embedding_1024"
        ).in_("document_id", document_ids).execute()
        
        chunks = chunks_response.data
        
        print(f"Hentet data:")
        print(f"- Indexing run: {indexing_run['id']}")
        print(f"- Status: {indexing_run['status']}")
        print(f"- Dokumenter: {len(documents)}")
        print(f"- Chunks: {len(chunks)}")
        
        return {
            "indexing_run": indexing_run,
            "documents": documents,
            "chunks": chunks,
            "document_ids": document_ids
        }
    
    def analyze_content_structure(self, documents: List[Dict], chunks: List[Dict]) -> Dict[str, Any]:
        """Analyze document content to identify themes, sections, and structure."""
        print("Analyserer indholdsstruktur...")
        
        # Group chunks by document
        chunks_by_doc = defaultdict(list)
        for chunk in chunks:
            chunks_by_doc[chunk["document_id"]].append(chunk)
        
        # Analyze content patterns
        content_analysis = {
            "total_content_length": sum(len(chunk["content"]) for chunk in chunks),
            "avg_chunk_length": np.mean([len(chunk["content"]) for chunk in chunks]),
            "document_stats": {},
            "common_terms": [],
            "potential_sections": [],
            "timeline_indicators": [],
            "technical_terms": []
        }
        
        # Analyze each document
        all_content = []
        for doc in documents:
            doc_chunks = chunks_by_doc[doc["id"]]
            doc_content = " ".join([chunk["content"] for chunk in doc_chunks])
            all_content.append(doc_content)
            
            content_analysis["document_stats"][doc["filename"]] = {
                "chunks": len(doc_chunks),
                "content_length": len(doc_content),
                "avg_chunk_size": np.mean([len(chunk["content"]) for chunk in doc_chunks]) if doc_chunks else 0
            }
        
        # Extract common construction-related terms (simple approach)
        all_text = " ".join(all_content).lower()
        
        # Construction-specific Danish terms to look for
        construction_terms = [
            "byggeri", "entreprenør", "tidsplan", "sikkerhed", "arbejdsmiljø",
            "tegning", "specifikation", "materiale", "installation", "kvalitet",
            "inspektion", "godkendelse", "leverance", "montage", "aflevering",
            "byggetilladelse", "projektleder", "koordinator", "arbejdstilladelse"
        ]
        
        found_terms = [(term, all_text.count(term)) for term in construction_terms if term in all_text]
        found_terms.sort(key=lambda x: x[1], reverse=True)
        content_analysis["common_terms"] = found_terms[:10]
        
        # Look for section indicators
        section_patterns = [
            r"\d+\.\s*[A-ZÆØÅ][\w\s]{10,50}",  # Numbered sections
            r"[A-ZÆØÅ]{2,}\s*:?",  # All caps headers
            r"\b(INDHOLD|INDLEDNING|FORMÅL|SIKKERHED|TIDSPLAN|MATERIALE|KVALITET)\b"
        ]
        
        potential_sections = set()
        for pattern in section_patterns:
            matches = re.findall(pattern, all_text.upper())
            potential_sections.update(matches[:20])  # Limit to avoid noise
        
        content_analysis["potential_sections"] = list(potential_sections)[:15]
        
        # Look for timeline/date indicators
        date_patterns = [
            r"\b(\d{1,2}[\.\/\-]\d{1,2}[\.\/\-]\d{4})\b",  # Dates
            r"\b(uge\s*\d+)\b",  # Week numbers
            r"\b(\d+\s*dage?)\b",  # Days
            r"\b(deadline|frist|aflevering)\b"
        ]
        
        timeline_indicators = []
        for pattern in date_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            timeline_indicators.extend(matches[:5])
        
        content_analysis["timeline_indicators"] = timeline_indicators[:10]
        
        print(f"Fundet {len(content_analysis['common_terms'])} hyppige byggetermer")
        print(f"Identificeret {len(content_analysis['potential_sections'])} mulige sektioner")
        print(f"Fundet {len(content_analysis['timeline_indicators'])} tidsplan indikatorer")
        
        return content_analysis
    
    def semantic_sampling(self, chunks: List[Dict], n_samples: int = 20) -> List[Dict]:
        """Use semantic clustering to select representative chunks across the content space."""
        print(f"Anvender semantisk sampling for at vælge {n_samples} repræsentative chunks...")
        
        # Filter chunks that have embeddings
        chunks_with_embeddings = [
            chunk for chunk in chunks 
            if chunk.get("embedding_1024") is not None
        ]
        
        if len(chunks_with_embeddings) == 0:
            print("⚠️  Ingen embeddings fundet - falder tilbage til første chunks")
            return chunks[:n_samples]
        
        if len(chunks_with_embeddings) <= n_samples:
            print(f"Kun {len(chunks_with_embeddings)} chunks med embeddings - returnerer alle")
            return chunks_with_embeddings
        
        print(f"Fundet {len(chunks_with_embeddings)} chunks med embeddings")
        
        # Extract embeddings as numpy array (parse string format)
        embeddings = []
        for chunk in chunks_with_embeddings:
            embedding_str = chunk["embedding_1024"]
            if isinstance(embedding_str, str):
                # Parse string format like '[0.1,0.2,0.3]'
                embedding_str = embedding_str.strip('[]')
                embedding_values = [float(x.strip()) for x in embedding_str.split(',')]
                embeddings.append(embedding_values)
            else:
                # Already a list/array
                embeddings.append(embedding_str)
        
        embeddings = np.array(embeddings)
        
        # Determine optimal number of clusters (less than n_samples)
        n_clusters = min(10, max(3, n_samples // 3))  # 3-10 clusters
        
        print(f"Klyngedeling i {n_clusters} klynger...")
        
        # Perform k-means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        # Group chunks by cluster
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            clusters[label].append((i, chunks_with_embeddings[i]))
        
        print(f"Klynger dannet: {[(k, len(v)) for k, v in clusters.items()]}")
        
        # Select representative chunks from each cluster
        selected_chunks = []
        samples_per_cluster = n_samples // n_clusters
        remaining_samples = n_samples % n_clusters
        
        for cluster_id, cluster_chunks in clusters.items():
            # Number of samples from this cluster
            cluster_sample_size = samples_per_cluster
            if remaining_samples > 0:
                cluster_sample_size += 1
                remaining_samples -= 1
            
            if len(cluster_chunks) <= cluster_sample_size:
                # Take all chunks from small clusters
                selected_chunks.extend([chunk for _, chunk in cluster_chunks])
            else:
                # For larger clusters, select most central chunks
                cluster_indices = [i for i, _ in cluster_chunks]
                cluster_embeddings = embeddings[cluster_indices]
                
                # Find cluster centroid
                centroid = np.mean(cluster_embeddings, axis=0)
                
                # Calculate distances to centroid
                distances = cosine_similarity([centroid], cluster_embeddings)[0]
                
                # Select chunks closest to centroid (most representative)
                closest_indices = np.argsort(distances)[::-1][:cluster_sample_size]
                
                for idx in closest_indices:
                    selected_chunks.append(cluster_chunks[idx][1])
        
        print(f"Valgte {len(selected_chunks)} semantisk repræsentative chunks")
        
        # Add some metadata about the selection process
        cluster_info = {}
        for cluster_id, cluster_chunks in clusters.items():
            sample_chunk = cluster_chunks[0][1]
            cluster_info[f"cluster_{cluster_id}"] = {
                "size": len(cluster_chunks),
                "sample_content": sample_chunk["content"][:100] + "..."
            }
        
        print("Klynge temaer:")
        for cluster_id, info in cluster_info.items():
            print(f"  {cluster_id} ({info['size']} chunks): {info['sample_content']}")
        
        return selected_chunks
    
    def call_openrouter_api(self, prompt: str, max_tokens: int = 4000) -> str:
        """Call OpenRouter API with the given prompt."""
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://constructionrag.com",
            "X-Title": "ConstructionRAG Overview Generator"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def generate_project_overview(self, data: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate comprehensive project overview using LLM."""
        print("Genererer projektoversigt med LLM...")
        
        indexing_run = data["indexing_run"]
        documents = data["documents"]
        chunks = data["chunks"]
        
        # Use semantic sampling to select representative chunks
        representative_chunks = self.semantic_sampling(chunks, n_samples=20)
        
        # Prepare sample content for LLM with semantic context
        sample_content = []
        for chunk in representative_chunks:
            sample_content.append({
                "content": chunk["content"][:500],  # First 500 chars
                "page": chunk.get("page_number", "N/A"),
                "document_id": chunk["document_id"],
                "chunk_index": chunk.get("chunk_index", "N/A")
            })
        
        # Build document list with metadata
        doc_list = []
        for doc in documents:
            doc_chunks = [c for c in chunks if c["document_id"] == doc["id"]]
            doc_list.append({
                "filename": doc["filename"],
                "size": doc.get("file_size", 0),
                "chunks": len(doc_chunks),
                "pages": doc.get("page_count", "N/A")
            })
        
        language_instructions = {
            "danish": "Du er en dansk byggeingeniør og projektleder der skal lave en automatisk oversigt over et byggeprojekt baseret på uploadede dokumenter.",
            "english": "You are a Danish construction engineer and project manager who needs to create an automatic overview of a construction project based on uploaded documents."
        }
        
        section_names = {
            "danish": {
                "overview": "## Projektoversigt",
                "stats": "## Nøgletal", 
                "documents": "## Dokumentoversigt",
                "timeline": "## Projekttidslinje",
                "structure": "## Projektstruktur",
                "sections": "## Detaljerede Sektioner"
            },
            "english": {
                "overview": "## Project Overview",
                "stats": "## Key Statistics",
                "documents": "## Document Overview", 
                "timeline": "## Project Timeline",
                "structure": "## Project Structure",
                "sections": "## Detailed Sections"
            }
        }
        
        lang = self.language
        sections = section_names.get(lang, section_names["danish"])
        
        prompt = f"""
{language_instructions[lang]}

PROJEKTDATA:
- Antal dokumenter: {len(documents)}
- Total chunks: {len(chunks)} 
- Processeret: {indexing_run.get('completed_at', 'I gang')}
- Upload type: {indexing_run.get('upload_type', 'N/A')}

DOKUMENTER:
{json.dumps(doc_list, indent=2, ensure_ascii=False)}

INDHOLDSANALYSE:
- Hyppige byggetermer: {analysis['common_terms'][:5]}
- Mulige sektioner: {analysis['potential_sections'][:10]}
- Tidsplan indikatorer: {analysis['timeline_indicators'][:5]}

EKSEMPEL INDHOLD (første 20 chunks):
{json.dumps(sample_content[:5], indent=2, ensure_ascii=False)}

OPGAVE:
Lav en omfattende {"dansk" if lang == "danish" else "English"} oversigt over dette byggeprojekt i markdown format. Oversigten skal indeholde:

1. **{sections["overview"]}** - kort beskrivelse af projektet baseret på dokumenterne
2. **{sections["stats"]}** - statistik om dokumenter og indhold
3. **{sections["documents"]}** - tabel med alle dokumenter
4. **{sections["timeline"]}** - hvis der er tidsplan data, lav en mermaid gantt chart
5. **{sections["structure"]}** - mermaid diagram af dokumentrelationer hvis relevant
6. **{sections["sections"]}** - baseret på AI-detekterede emner (f.eks. Sikkerhed, Specifikationer, Tidsplan)

VIGTIGE KRAV:
- Skriv på {"dansk" if lang == "danish" else "English"}
- Fokusér på byggeprojekt-specifikke emner
- Brug mermaid diagrammer hvor relevant
- Lav en sammenfatning, ikke en genfortælling
- Identificér de vigtigste projektinformationer
- Brug markdown formatering korrekt

Start med markdown oversigten nu:
"""
        
        start_time = time.time()
        overview = self.call_openrouter_api(prompt, max_tokens=6000)
        end_time = time.time()
        
        print(f"LLM respons modtaget på {end_time - start_time:.1f} sekunder")
        return overview
    
    def save_overview_results(self, overview_markdown: str, index_run_id: str, analysis: Dict[str, Any]) -> str:
        """Save the generated overview and analysis data."""
        print("Gemmer resultater...")
        
        # Create output directory
        output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "internal", "overview_generation")
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(output_dir, f"overview_run_{timestamp}")
        os.makedirs(run_dir, exist_ok=True)
        
        # Save markdown overview
        markdown_path = os.path.join(run_dir, "project_overview.md")
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(overview_markdown)
        
        # Save analysis data
        analysis_path = os.path.join(run_dir, "content_analysis.json")
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
        
        # Save metadata
        metadata = {
            "index_run_id": index_run_id,
            "generated_at": datetime.now().isoformat(),
            "language": self.language,
            "model": self.model,
            "document_count": len(analysis.get("document_stats", {})),
            "total_content_length": analysis.get("total_content_length", 0)
        }
        
        metadata_path = os.path.join(run_dir, "generation_metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"Resultater gemt i: {run_dir}")
        print(f"- Markdown oversigt: {markdown_path}")
        print(f"- Indholdsanalyse: {analysis_path}")
        print(f"- Metadata: {metadata_path}")
        
        return run_dir
    
    def validate_overview_quality(self, overview: str) -> Dict[str, Any]:
        """Validate the generated overview for completeness and quality."""
        validation = {
            "has_project_overview": any(header in overview for header in ["## Projektoversigt", "# Projektoversigt", "## Project Overview"]),
            "has_document_table": "| " in overview and ("Dokument" in overview or "Document" in overview),
            "has_mermaid_diagram": "```mermaid" in overview,
            "has_sections": overview.count("##") >= 3,
            "is_target_language": any(word in overview.lower() for word in 
                                   (["byggeri", "projekt", "dokument", "oversigt"] if self.language == "danish" 
                                    else ["construction", "project", "document", "overview"])),
            "word_count": len(overview.split()),
            "character_count": len(overview),
            "markdown_headers": overview.count("#")
        }
        
        validation["quality_score"] = sum([
            validation["has_project_overview"],
            validation["has_document_table"],
            validation["has_mermaid_diagram"],
            validation["has_sections"],
            validation["is_target_language"]
        ]) / 5.0
        
        return validation
    
    def calculate_estimated_cost(self, analysis: Dict[str, Any], overview: str, representative_chunks: List[Dict]) -> Dict[str, float]:
        """Calculate estimated API costs."""
        # Rough token estimation (4 chars per token)
        sample_content_length = sum(len(chunk["content"][:500]) for chunk in representative_chunks)
        prompt_length = len(json.dumps(analysis)) + sample_content_length + 2000  # Base prompt
        
        estimated_input_tokens = prompt_length / 4
        estimated_output_tokens = len(overview) / 4
        
        # Gemini 2.0 Flash pricing via OpenRouter
        input_cost = estimated_input_tokens * 0.075 / 1000000  # $0.075 per 1M tokens
        output_cost = estimated_output_tokens * 0.30 / 1000000  # $0.30 per 1M tokens
        total_cost = input_cost + output_cost
        
        return {
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "input_cost_usd": input_cost,
            "output_cost_usd": output_cost,
            "total_cost_usd": total_cost
        }
    
    def generate_overview(self, index_run_id: str) -> str:
        """Main method to generate overview for an indexing run."""
        print(f"Starter oversigt generering for indexing run: {index_run_id}")
        print(f"Konfiguration: {self.language} sprog, {self.model} model")
        
        start_time = time.time()
        
        try:
            # 1. Fetch data
            data = self.fetch_indexing_run_data(index_run_id)
            
            # 2. Analyze content
            analysis = self.analyze_content_structure(data["documents"], data["chunks"])
            
            # 3. Generate overview
            overview_markdown = self.generate_project_overview(data, analysis)
            
            # 4. Validate quality
            validation = self.validate_overview_quality(overview_markdown)
            
            # 5. Calculate costs (using representative chunks for accurate estimation)
            representative_chunks = self.semantic_sampling(data["chunks"], n_samples=20)
            costs = self.calculate_estimated_cost(analysis, overview_markdown, representative_chunks)
            
            # 6. Save results
            output_dir = self.save_overview_results(overview_markdown, index_run_id, analysis)
            
            # 7. Print summary
            end_time = time.time()
            processing_time = end_time - start_time
            
            print("\n" + "="*60)
            print("PROCESSERINGSRESULTATER")
            print("="*60)
            print(f"Index Run ID: {index_run_id}")
            print(f"Dokumenter processeret: {len(data['documents'])}")
            print(f"Chunks analyseret: {len(data['chunks'])}")
            print(f"Total indhold: {analysis['total_content_length']:,} tegn")
            print(f"Behandlingstid: {processing_time:.1f} sekunder")
            print(f"Sprog: {self.language}")
            print(f"Model: {self.model}")
            
            print(f"\nKvalitetsvalidering:")
            for key, value in validation.items():
                if isinstance(value, bool):
                    status = "✓" if value else "✗"
                    print(f"  {status} {key}: {value}")
                elif key in ["word_count", "character_count", "markdown_headers"]:
                    print(f"    {key}: {value}")
            print(f"  Samlet kvalitetsscore: {validation['quality_score']:.1%}")
            
            print(f"\nEstimerede omkostninger:")
            print(f"  Input tokens: ~{costs['estimated_input_tokens']:,.0f}")
            print(f"  Output tokens: ~{costs['estimated_output_tokens']:,.0f}")
            print(f"  Estimeret pris: ~${costs['total_cost_usd']:.4f} USD")
            
            print(f"\nOutput gemt i: {output_dir}")
            
            # Show first few lines of generated overview
            print(f"\n" + "="*60)
            print("GENERERET OVERSIGT (første linjer):")
            print("="*60)
            overview_lines = overview_markdown.split('\n')
            for line in overview_lines[:10]:
                print(line)
            if len(overview_lines) > 10:
                print(f"... ({len(overview_lines) - 10} flere linjer)")
            
            return output_dir
            
        except Exception as e:
            print(f"Fejl under generering: {str(e)}")
            raise


def main():
    """Command line interface for overview generation."""
    parser = argparse.ArgumentParser(description="Generate automatic project overview from indexing run")
    parser.add_argument("--index-run-id", required=True, help="UUID of the indexing run")
    parser.add_argument("--language", default="danish", choices=["danish", "english"], help="Output language")
    parser.add_argument("--model", default="google/gemini-2.0-flash-exp", help="OpenRouter model to use")
    parser.add_argument("--test-sampling", action="store_true", help="Test semantic sampling without LLM call")
    
    args = parser.parse_args()
    
    try:
        if args.test_sampling:
            # Test mode - only test semantic sampling without LLM
            generator = OverviewGenerator(language=args.language, model=args.model)
            generator.openrouter_api_key = "test"  # Skip API key check for testing
            
            # Fetch data and test semantic sampling
            data = generator.fetch_indexing_run_data(args.index_run_id)
            analysis = generator.analyze_content_structure(data["documents"], data["chunks"])
            representative_chunks = generator.semantic_sampling(data["chunks"], n_samples=20)
            
            print(f"\n" + "="*60)
            print("SEMANTISK SAMPLING TEST RESULTATER")
            print("="*60)
            print(f"Original chunks: {len(data['chunks'])}")
            print(f"Valgte repræsentative chunks: {len(representative_chunks)}")
            
            print(f"\nRepræsentative chunk eksempler:")
            for i, chunk in enumerate(representative_chunks[:5]):
                print(f"\n{i+1}. Chunk {chunk.get('chunk_index', 'N/A')} fra dokument {chunk['document_id'][:8]}...")
                print(f"   Indhold: {chunk['content'][:150]}...")
                print(f"   Side: {chunk.get('page_number', 'N/A')}")
            
            print(f"\n✓ Semantisk sampling test gennemført!")
            
        else:
            # Normal mode - full generation
            generator = OverviewGenerator(language=args.language, model=args.model)
            output_dir = generator.generate_overview(args.index_run_id)
            print(f"\n✓ Oversigt genereret succesfuldt!")
            print(f"Tjek resultaterne i: {output_dir}")
        
    except Exception as e:
        print(f"✗ Fejl: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()