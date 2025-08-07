#!/usr/bin/env python3
"""
ConstructionRAG - Advanced Markdown Wiki Generation

This script generates comprehensive multi-page wiki documentation from construction project data
using a sophisticated 7-step RAG approach with semantic clustering, strategic page planning,
and professional markdown generation.

7-Step Pipeline:
1. SUPABASE TABLES - Collect project metadata and document chunks
2. VECTOR QUERIES - Retrieve relevant content for project overview
3. OVERVIEW LLM - Generate comprehensive project overview
4. SEMANTIC CLUSTERING - Identify topics with LLM-based naming
5. STRUCTURE LLM - Create strategic wiki page structure (not just clusters)
6. PAGE QUERIES - Retrieve specific content for each planned page
7. PAGE LLM - Generate professional markdown pages with diagrams and citations

Usage:
    # Generate first 4 steps only (analysis + overview)
    python markdown_generation_overview.py --index-run-id 668ecac8-beb5-4f94-94d6-eee8c771044d

    # Generate complete 7-step wiki with markdown pages
    python markdown_generation_overview.py --index-run-id <id> --complete

    # With custom language and model
    python markdown_generation_overview.py --index-run-id <id> --complete --language danish --model google/gemini-2.5-flash
"""

import os
import sys
import json
import argparse
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID
from collections import defaultdict
from datetime import datetime
import numpy as np
import requests
import httpx
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from config.database import get_supabase_admin_client

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


class VoyageEmbeddingClient:
    """Client for Voyage AI embedding API - same as query pipeline"""

    def __init__(self, api_key: str, model: str = "voyage-multilingual-2"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.voyageai.com/v1/embeddings"
        self.dimensions = 1024  # voyage-multilingual-2 dimensions

    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text using Voyage AI"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": self.model, "input": [text]},
                )

                if response.status_code != 200:
                    raise Exception(
                        f"Voyage API error: {response.status_code} - {response.text}"
                    )

                result = response.json()
                return result["data"][0]["embedding"]

        except Exception as e:
            print(f"Failed to generate embedding: {e}")
            raise


class MarkdownWikiGenerator:
    """Generate comprehensive wiki documentation using 3-step RAG approach."""

    def __init__(
        self, language: str = "danish", model: str = "google/gemini-2.5-flash"
    ):
        self.language = language
        self.model = model
        self.supabase = get_supabase_admin_client()
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env file")

        # Initialize Voyage client for real vector search
        voyage_api_key = os.getenv("VOYAGE_API_KEY")
        if not voyage_api_key:
            raise ValueError(
                "VOYAGE_API_KEY not found in .env file - needed for real vector similarity search"
            )

        self.voyage_client = VoyageEmbeddingClient(
            api_key=voyage_api_key, model="voyage-multilingual-2"
        )

        # Load configuration
        self.config = self.load_config()

        print(f"Initialiseret MarkdownWikiGenerator:")
        print(f"- Sprog: {self.language}")
        print(f"- Model: {self.model}")
        print(f"- API Key: {'✓' if self.openrouter_api_key else '✗'}")
        print(f"- Similarity threshold: {self.config['similarity_threshold']}")

        # Debug API key loading
        if self.openrouter_api_key:
            print(
                f"- API Key preview: {self.openrouter_api_key[:10]}...{self.openrouter_api_key[-4:]}"
            )

    def load_config(self) -> Dict[str, Any]:
        """Load configuration settings."""
        return {
            "similarity_threshold": 0.3,  # Lower threshold for testing - more permissive
            "max_chunks_per_query": 10,  # Maximum chunks to return per query
            "overview_query_count": 12,  # Number of overview queries to use
            "semantic_clusters": {"min_clusters": 4, "max_clusters": 10},
        }

    def fetch_project_metadata(self, index_run_id: str) -> Dict[str, Any]:
        """Step 1: SUPABASE TABLES - Collect metadata about the project."""
        print(f"Trin 1: Henter projektmetadata for indexing run: {index_run_id}")

        # Get indexing run with step results
        indexing_run_response = (
            self.supabase.table("indexing_runs")
            .select("*")
            .eq("id", index_run_id)
            .execute()
        )

        if not indexing_run_response.data:
            raise ValueError(f"Ingen indexing run fundet med ID: {index_run_id}")

        indexing_run = indexing_run_response.data[0]
        step_results = indexing_run.get("step_results", {})

        # Get documents
        documents_response = (
            self.supabase.table("indexing_run_documents")
            .select("document_id, documents(*)")
            .eq("indexing_run_id", index_run_id)
            .execute()
        )

        documents = [
            item["documents"] for item in documents_response.data if item["documents"]
        ]
        document_ids = [doc["id"] for doc in documents]

        # Get chunks with embeddings (but don't store embeddings in output)
        chunks_response = (
            self.supabase.table("document_chunks")
            .select("id, document_id, content, metadata, embedding_1024")
            .in_("document_id", document_ids)
            .execute()
        )

        # Store chunks without embeddings for output, but keep embeddings for processing
        chunks = []
        chunks_with_embeddings = []
        for chunk_data in chunks_response.data:
            # Clean chunk for output (no embeddings)
            # Extract page_number from metadata if available
            metadata = chunk_data.get("metadata", {})
            page_number = metadata.get("page_number", "N/A")

            clean_chunk = {
                "id": chunk_data.get("id"),
                "document_id": chunk_data.get("document_id"),
                "content": chunk_data.get("content", ""),
                "page_number": page_number,
                "metadata": metadata,
            }
            chunks.append(clean_chunk)

            # Keep original with embeddings for processing
            chunks_with_embeddings.append(chunk_data)

        # Extract metadata from step results
        metadata = {
            "indexing_run_id": index_run_id,
            "total_documents": len(documents),
            "total_chunks": len(chunks),
            "documents": documents,
            "chunks": chunks,  # Clean chunks without embeddings for output
            "chunks_with_embeddings": chunks_with_embeddings,  # For processing only
        }

        # Extract pages analyzed (sum from all documents)
        total_pages = sum(
            doc.get("page_count", 0) for doc in documents if doc.get("page_count")
        )
        metadata["total_pages_analyzed"] = total_pages

        # Extract from chunking step
        chunking_data = step_results.get("chunking", {}).get("data", {})
        if chunking_data:
            summary_stats = chunking_data.get("summary_stats", {})
            metadata["section_headers_distribution"] = summary_stats.get(
                "section_headers_distribution", {}
            )
        else:
            metadata["section_headers_distribution"] = {}

        # Extract from enrichment step
        enrichment_data = step_results.get("enrichment", {}).get("data", {})
        if enrichment_data:
            enrich_summary = enrichment_data.get("summary_stats", {})
            metadata["images_processed"] = enrich_summary.get("images_captioned", 0)
            metadata["tables_processed"] = enrich_summary.get("tables_captioned", 0)
        else:
            metadata["images_processed"] = 0
            metadata["tables_processed"] = 0

        print(f"Projektmetadata hentet:")
        print(f"- Dokumenter: {metadata['total_documents']}")
        print(f"- Sider analyseret: {metadata['total_pages_analyzed']}")
        print(f"- Chunks oprettet: {metadata['total_chunks']}")
        print(f"- Billeder behandlet: {metadata['images_processed']}")
        print(f"- Tabeller behandlet: {metadata['tables_processed']}")
        print(f"- Sektioner fundet: {len(metadata['section_headers_distribution'])}")

        return metadata

    async def vector_similarity_search(
        self, query_text: str, document_ids: List[str], top_k: int = None
    ) -> List[Tuple[Dict, float]]:
        """Perform real pgvector similarity search using Voyage embeddings - matches production pipeline."""
        if top_k is None:
            top_k = self.config["max_chunks_per_query"]

        print(f"🔍 Real pgvector search for: '{query_text[:60]}...'")

        try:
            # Generate embedding for query using Voyage API
            query_embedding = await self.voyage_client.get_embedding(query_text)

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
                    import ast

                    chunk_embedding = ast.literal_eval(embedding_str)

                    # Ensure it's a list of floats
                    if isinstance(chunk_embedding, list):
                        chunk_embedding = [float(x) for x in chunk_embedding]

                        # Calculate cosine similarity
                        similarity = self.cosine_similarity(
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
                    if result["similarity"] >= self.config["similarity_threshold"]:
                        unique_results.append((result["chunk"], result["similarity"]))

                    # Stop when we have enough unique results
                    if len(unique_results) >= top_k * 2:
                        break

            # Final results sorted by similarity (highest first)
            unique_results.sort(key=lambda x: x[1], reverse=True)
            results = unique_results[:top_k]

            print(
                f"  Fundet {len(results)} relevante unikke chunks (threshold: {self.config['similarity_threshold']})"
            )
            if results:
                avg_similarity = np.mean([score for _, score in results])
                print(f"  Gennemsnitlig similarity: {avg_similarity:.3f}")

            return results

        except Exception as e:
            print(f"⚠️  Vector search fejlede: {str(e)}")
            print(f"⚠️  Falder tilbage til tom resultat...")
            return []

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
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

    async def query_project_overview(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2: QUERY TO VECTOR DB - Send queries to retrieve overall project description."""
        print(f"Trin 2: Forespørger vector database for projektoversigt")

        # Standard overview queries in Danish
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

        # Get document IDs for vector search
        document_ids = [doc["id"] for doc in metadata["documents"]]
        all_retrieved_chunks = []
        query_results = {}

        # Execute each query
        for i, query in enumerate(
            project_overview_queries[: self.config["overview_query_count"]]
        ):
            print(f"  Query {i+1}/{self.config['overview_query_count']}: {query}")

            results = await self.vector_similarity_search(query, document_ids)
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

    def call_openrouter_api(self, prompt: str, max_tokens: int = 4000) -> str:
        """Call OpenRouter API with the given prompt."""
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
            "temperature": 0.3,
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data
        )

        if response.status_code != 200:
            raise Exception(
                f"OpenRouter API fejl: {response.status_code} - {response.text}"
            )

        result = response.json()
        return result["choices"][0]["message"]["content"]

    def generate_project_overview_llm(self, overview_data: Dict[str, Any]) -> str:
        """Step 3: OVERVIEW LLM CALL - Create project overview based on vector DB results."""
        print(f"Trin 3: Genererer projektoversigt med LLM")

        retrieved_chunks = overview_data["retrieved_chunks"]

        print(f"Forbereder {len(retrieved_chunks)} chunks til LLM (bruger første 15)")

        # Prepare document excerpts for LLM
        document_excerpts = []
        for i, chunk in enumerate(retrieved_chunks[:15]):  # Limit to avoid token limits
            content = chunk.get("content", "")
            document_id = chunk.get("document_id", "unknown")

            # Extract page number from metadata more reliably
            metadata = chunk.get("metadata", {})
            page_number = metadata.get("page_number", "N/A") if metadata else "N/A"

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
Indhold: {content[:800]}...
"""
            document_excerpts.append(excerpt)

        print(f"Genereret {len(document_excerpts)} dokumentudtrag til LLM")

        excerpts_text = "\n".join(document_excerpts)

        # Create prompt in Danish
        prompt = f"""Baseret på byggeprojektets dokumentudtog nedenfor, generer en kort 2-3 afsnit projektoversigt der dækker:

1. Projektnavn, type, placering og hovedformål
2. Nøgleinteressenter (klient, entreprenør, arkitekt osv.) og projekttidslinje  
3. Projektomfang, budget og vigtige leverancer

Brug KUN information der eksplicit findes i dokumentudtragene. Citér kilder ved hjælp af (Kilde: filnavn:side). Hvis kritisk information mangler, nævn kort hvad der ikke er tilgængeligt.

Dokumentudtrag:
{excerpts_text}

Generer projektoversigten på dansk:"""

        try:
            start_time = time.time()
            overview_content = self.call_openrouter_api(prompt, max_tokens=2000)
            end_time = time.time()

            print(
                f"LLM projektoversigt genereret på {end_time - start_time:.1f} sekunder"
            )
            print(f"Oversigt længde: {len(overview_content)} tegn")

            return overview_content

        except Exception as e:
            print(f"⚠️  LLM kald fejlede: {str(e)}")
            print(f"⚠️  Fortsætter med dummy indhold til test...")

            # Return dummy content for testing purposes
            dummy_overview = f"""# Projektoversigt (Test Mode)

**Projektnavn:** Baseret på de {len(retrieved_chunks)} hentede dokumentudtrag

**Projekttype:** Byggeprojekt med fokus på tekniske installationer

**Information hentet:**
- {len(retrieved_chunks)} relevante chunks blev fundet
- Dokumentudtrag fra {len(set(chunk.get('document_id', '') for chunk in retrieved_chunks))} forskellige dokumenter
- Gennemsnitlig relevans score: {np.mean([chunk.get('similarity_score', 0) for chunk in retrieved_chunks]):.2f}

**Bemærk:** Dette er test indhold da LLM API'et ikke er tilgængeligt."""

            return dummy_overview

    def generate_cluster_names_llm(
        self, cluster_summaries: List[Dict[str, Any]]
    ) -> Dict[int, str]:
        """Generate meaningful cluster names using LLM based on cluster content samples."""
        print(
            f"🤖 Genererer klyngenavne med LLM for {len(cluster_summaries)} klynger..."
        )

        # Prepare cluster samples for LLM
        cluster_samples = []
        for summary in cluster_summaries:
            cluster_id = summary["cluster_id"]
            sample_content = summary.get("sample_content", [])

            # Combine sample content into a representative text
            combined_sample = " | ".join(sample_content)
            cluster_samples.append(
                {
                    "cluster_id": cluster_id,
                    "sample_text": combined_sample[
                        :800
                    ],  # Limit to avoid token overflow
                }
            )

        # Create prompt for LLM to generate names
        samples_text = "\n".join(
            [
                f"Klynge {item['cluster_id']}: {item['sample_text']}"
                for item in cluster_samples
            ]
        )

        prompt = f"""Baseret på følgende dokumentindhold fra en byggeprojekt-database, generer korte, beskrivende navne for hver klynge.

Navnene skal være:
- Korte og præcise (2-4 ord)
- Beskrivende for klyngens indhold
- Professionelle og faglige
- På dansk
- Unikke (ingen gentagelser)

Dokumentklynger:
{samples_text}

Generer navne i følgende format:
Klynge 0: [Navn]
Klynge 1: [Navn]
...

Svar kun med navnene i det specificerede format."""

        try:
            start_time = time.time()
            llm_response = self.call_openrouter_api(prompt, max_tokens=500)
            end_time = time.time()

            print(f"LLM klyngenavne genereret på {end_time - start_time:.1f} sekunder")

            # Parse the response to extract cluster names
            cluster_names = {}
            for line in llm_response.strip().split("\n"):
                if ":" in line and "Klynge" in line:
                    try:
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            cluster_part = parts[0].strip()
                            name_part = parts[1].strip()

                            # Extract cluster ID from "Klynge X" format
                            cluster_id = int(cluster_part.split()[-1])
                            cluster_names[cluster_id] = name_part

                    except (ValueError, IndexError) as e:
                        print(f"⚠️  Kunne ikke parse linje: '{line}' - {e}")
                        continue

            print(f"Parset {len(cluster_names)} klyngenavne fra LLM respons")

            # Fallback for missing names
            for summary in cluster_summaries:
                cluster_id = summary["cluster_id"]
                if cluster_id not in cluster_names:
                    fallback_name = f"Temaområde {cluster_id}"
                    cluster_names[cluster_id] = fallback_name
                    print(
                        f"  Bruger fallback navn for klynge {cluster_id}: {fallback_name}"
                    )

            return cluster_names

        except Exception as e:
            print(f"⚠️  LLM klyngenavn generering fejlede: {str(e)}")
            print(f"⚠️  Falder tilbage til generiske navne...")

            # Fallback to generic names
            generic_names = [
                "Tekniske Specifikationer",
                "Projektdokumentation",
                "Bygningskomponenter",
                "Systeminstallationer",
                "Udførselsdetaljer",
                "Drifts- og Vedligehold",
                "Kvalitetssikring",
                "Sikkerhedsforhold",
            ]

            cluster_names = {}
            for i, summary in enumerate(cluster_summaries):
                cluster_id = summary["cluster_id"]
                if i < len(generic_names):
                    cluster_names[cluster_id] = generic_names[i]
                else:
                    cluster_names[cluster_id] = f"Temaområde {cluster_id}"

            return cluster_names

    def semantic_clustering(self, chunks: List[Dict]) -> Dict[str, Any]:
        """Step 4: SEMANTIC ANALYSIS - Perform semantic clustering and LLM-based naming to identify 4-10 main topics."""
        print(
            f"Trin 4: Udfører semantisk clustering og LLM navngivning for emneidentifikation..."
        )

        # Filter chunks with embeddings
        chunks_with_embeddings = [
            chunk for chunk in chunks if chunk.get("embedding_1024") is not None
        ]

        if len(chunks_with_embeddings) == 0:
            print("⚠️  Ingen embeddings fundet - kan ikke lave clustering")
            return {"clusters": [], "cluster_summaries": []}

        print(f"Fundet {len(chunks_with_embeddings)} chunks med embeddings")

        # Parse embeddings
        embeddings = []
        for chunk in chunks_with_embeddings:
            embedding_str = chunk["embedding_1024"]
            if isinstance(embedding_str, str):
                embedding_str = embedding_str.strip("[]")
                embedding_values = [float(x.strip()) for x in embedding_str.split(",")]
                embeddings.append(embedding_values)
            else:
                embeddings.append(embedding_str)

        embeddings = np.array(embeddings)

        # Determine number of clusters
        n_chunks = len(chunks_with_embeddings)
        n_clusters = min(
            self.config["semantic_clusters"]["max_clusters"],
            max(self.config["semantic_clusters"]["min_clusters"], n_chunks // 20),
        )

        print(f"Klyngedeling i {n_clusters} klynger...")

        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)

        # Group chunks by cluster
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            clusters[label].append(chunks_with_embeddings[i])

        # Create initial cluster summaries with sample content (without names yet)
        cluster_summaries = []
        for cluster_id, cluster_chunks in clusters.items():
            # Sample content for summary
            sample_content = []
            for chunk in cluster_chunks[:3]:  # First 3 chunks as samples
                content_preview = chunk.get("content", "")[:150]
                sample_content.append(content_preview)

            cluster_summary = {
                "cluster_id": int(cluster_id),  # Convert numpy int32 to Python int
                "chunk_count": len(cluster_chunks),
                "sample_content": sample_content,
                "representative_content": " | ".join(sample_content),
            }
            cluster_summaries.append(cluster_summary)

        # Generate cluster names using LLM
        cluster_names = self.generate_cluster_names_llm(cluster_summaries)

        # Add the generated names to summaries
        for summary in cluster_summaries:
            cluster_id = summary["cluster_id"]
            summary["cluster_name"] = cluster_names.get(
                cluster_id, f"Temaområde {cluster_id}"
            )

        print(f"Klynger oprettet:")
        for summary in cluster_summaries:
            print(
                f"  {summary['cluster_name']} ({summary['chunk_count']} chunks): {summary['representative_content'][:100]}..."
            )

        # Convert clusters dict to have int keys instead of numpy int32
        clusters_dict = {}
        for cluster_id, cluster_chunks in clusters.items():
            clusters_dict[int(cluster_id)] = cluster_chunks

        return {
            "clusters": clusters_dict,
            "cluster_summaries": cluster_summaries,
            "n_clusters": n_clusters,
        }

    def save_intermediate_results(
        self, index_run_id: str, step_name: str, data: Dict[str, Any]
    ) -> str:
        """Save intermediate results for debugging and analysis."""
        output_dir = os.path.join(
            os.path.dirname(__file__), "..", "data", "internal", "wiki_generation"
        )
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(output_dir, f"wiki_run_{timestamp}")
        os.makedirs(run_dir, exist_ok=True)

        step_file = os.path.join(run_dir, f"{step_name}.json")
        with open(step_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        print(f"  💾 {step_name} resultater gemt i: {step_file}")
        return run_dir

    def clean_results_for_saving(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Clean results to remove large data before saving - AGGRESSIVE cleaning."""
        clean_results = results.copy()

        # Clean metadata section - remove all large data structures
        if "metadata" in clean_results:
            metadata = clean_results["metadata"].copy()

            # Replace documents list with just summary
            if "documents" in metadata:
                documents = metadata["documents"]
                metadata["documents"] = {
                    "count": len(documents),
                    "filenames": [
                        doc.get("filename", "unknown") for doc in documents[:3]
                    ]
                    + (["..."] if len(documents) > 3 else []),
                    "total_file_size": sum(
                        doc.get("file_size", 0)
                        for doc in documents
                        if doc.get("file_size")
                    ),
                }

            # Replace chunks with minimal summary only
            if "chunks" in metadata:
                chunks = metadata["chunks"]
                metadata["chunks"] = {
                    "total_chunks": len(chunks),
                    "sample_chunk_ids": [chunk.get("id") for chunk in chunks[:3]],
                    "avg_content_length": (
                        sum(len(chunk.get("content", "")) for chunk in chunks[:10])
                        // min(10, len(chunks))
                        if chunks
                        else 0
                    ),
                }

            # Remove chunks_with_embeddings entirely - this contains large embeddings
            if "chunks_with_embeddings" in metadata:
                del metadata["chunks_with_embeddings"]

            clean_results["metadata"] = metadata

        # Clean overview query results - keep structure but limit content severely
        if "overview_queries" in clean_results:
            query_data = clean_results["overview_queries"].copy()

            # Replace retrieved_chunks with minimal summary
            if "retrieved_chunks" in query_data:
                chunks = query_data["retrieved_chunks"]
                query_data["retrieved_chunks"] = {
                    "count": len(chunks),
                    "top_similarities": [
                        chunk.get("similarity_score", 0) for chunk in chunks[:5]
                    ],
                    "sample_sources": [
                        f"doc_{chunk.get('document_id', 'unknown')[:8]}"
                        for chunk in chunks[:3]
                    ],
                }

            # Keep query_results but clean them
            if "query_results" in query_data:
                query_results = query_data["query_results"]
                cleaned_query_results = {}
                for query, result in query_results.items():
                    cleaned_query_results[query[:50] + "..."] = {
                        "results_count": result.get("results_count", 0),
                        "avg_similarity": result.get("avg_similarity", 0.0),
                    }
                query_data["query_results"] = cleaned_query_results

            clean_results["overview_queries"] = query_data

        # Clean semantic analysis - remove full cluster data
        if "semantic_analysis" in clean_results:
            semantic_data = clean_results["semantic_analysis"].copy()

            # Remove full clusters data - keep only summaries
            if "clusters" in semantic_data:
                del semantic_data["clusters"]

            # Clean cluster summaries - remove sample content
            if "cluster_summaries" in semantic_data:
                cleaned_summaries = []
                for summary in semantic_data["cluster_summaries"]:
                    cleaned_summaries.append(
                        {
                            "cluster_id": summary.get("cluster_id"),
                            "cluster_name": summary.get("cluster_name"),
                            "chunk_count": summary.get("chunk_count"),
                            "sample_preview": (
                                summary.get("representative_content", "")[:100] + "..."
                                if summary.get("representative_content")
                                else ""
                            ),
                        }
                    )
                semantic_data["cluster_summaries"] = cleaned_summaries

            clean_results["semantic_analysis"] = semantic_data

        return clean_results

    def generate_wiki_structure_llm(
        self, project_overview: str, semantic_analysis: Dict, metadata: Dict
    ) -> Dict:
        """Step 5: STRUCTURE LLM CALL - Create strategic wiki structure based on holistic project analysis."""
        print(f"Step 5: Generating strategic wiki structure with LLM...")

        # Prepare input data for LLM
        cluster_summaries = semantic_analysis.get("cluster_summaries", [])

        # Prepare document list
        documents = metadata.get("documents", [])
        document_list = []
        for doc in documents:
            filename = doc.get("filename", f"document_{doc.get('id', 'unknown')[:8]}")
            file_size = doc.get("file_size", 0)
            page_count = doc.get("page_count", 0)
            document_list.append(
                f"- {filename} ({page_count} pages, {file_size:,} bytes)"
            )

        # Prepare semantic clusters
        cluster_list = []
        for summary in cluster_summaries:
            cluster_id = summary.get("cluster_id", "unknown")
            cluster_name = summary.get("cluster_name", f"Cluster {cluster_id}")
            chunk_count = summary.get("chunk_count", 0)
            cluster_list.append(
                f"- Cluster {cluster_id} ({chunk_count} chunks): {cluster_name}"
            )

        # Prepare section headers
        section_headers = metadata.get("section_headers_distribution", {})
        section_list = []
        for header, count in sorted(
            section_headers.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            section_list.append(f"- {header}: {count} occurrences")

        # Create comprehensive English prompt for strategic wiki structure
        prompt = f"""Analyze this construction project and create a wiki structure for it.

# Important context to consider when deciding which sections to create
1. The complete list of project documents:
{chr(10).join(document_list)}

2. The project overview/summary:
{project_overview}

3. Semantic analysis
{chr(10).join(cluster_list)}

4. Sections detected
{chr(10).join(section_list) if section_list else "No sections detected"}

Use the project overview & semantic analysis most in your considerations.

## Section breakdown information
I want to create a wiki for this construction project. Determine the most logical structure for a wiki based on the project's documentation and content.

IMPORTANT: The wiki content will be generated in Danish language.

# Return output 
## Return output rules
- Make sure each output at least have 1 "overview" page. 

- Make sure each page has a topic and 6-10 associated queries that will help them retrieve relevant information for that topic. Like this for overview (in the language the document is, probably danish): 

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
    "square meters floor area size dimensions scope"
] 

- OPTIONAL: If a page is closely related to another page, then store that in related_pages.

- Each page should focus on a specific aspect of the construction project (e.g., project phases, safety requirements, material specifications)

## Return output format
Return your analysis in the following JSON format:

{{
 "title": "[Overall title for the wiki]",
 "description": "[Brief description of the construction project]",
 "pages": [
   {{
     "id": "page-1",
     "title": "[Page title]",
     "description": "[Brief description of what this page will cover]",
     "proposed_queries": [
       "[]"
     ],
     "related_pages": [
       "[]"
     ],
     "relevance_score": "1-10",
     "topic_argumentation": "argumentation for why this was chosen"
   }}
 ]
}}

IMPORTANT FORMATTING INSTRUCTIONS:
- Return ONLY the valid JSON structure specified above
- DO NOT wrap the JSON in markdown code blocks (no ``` or ```json)
- DO NOT include any explanation text before or after the JSON
- Ensure the JSON is properly formatted and valid
- Start directly with {{ and end with }}

Your proposed tests for step 5 seems good. Please output the json that step outputs so i can check it as well."""

        try:
            start_time = time.time()
            llm_response = self.call_openrouter_api(prompt, max_tokens=3000)
            end_time = time.time()

            print(
                f"LLM wiki structure generated in {end_time - start_time:.1f} seconds"
            )

            # Robust JSON parsing with markdown fence stripping
            wiki_structure = self._parse_json_response(llm_response)

            # Validate structure
            if not isinstance(wiki_structure, dict) or "pages" not in wiki_structure:
                raise ValueError("Invalid JSON structure - missing 'pages' key")

            pages = wiki_structure.get("pages", [])
            if not isinstance(pages, list) or len(pages) == 0:
                raise ValueError("No pages found in structure")

            print(f"Wiki structure parsed successfully:")
            print(f"  Title: {wiki_structure.get('title', 'N/A')}")
            print(f"  Number of pages: {len(pages)}")

            for i, page in enumerate(pages[:3]):  # Show first 3 pages
                print(
                    f"    Page {i+1}: {page.get('title', 'N/A')} (score: {page.get('relevance_score', 'N/A')})"
                )

            return wiki_structure

        except Exception as e:
            print(f"⚠️  LLM structure generation failed: {str(e)}")
            print(f"⚠️  Falling back to simple structure based on clusters...")

            # Fallback structure based on semantic clusters
            fallback_pages = []
            for i, summary in enumerate(cluster_summaries[:5]):  # Top 5 clusters
                cluster_id = summary.get("cluster_id", i)
                cluster_name = summary.get("cluster_name", f"Topic Area {cluster_id}")

                # Generate simple queries based on cluster name
                base_query = (
                    cluster_name.lower().replace(" and ", " ").replace(" & ", " ")
                )
                fallback_queries = [
                    base_query,
                    f"{base_query} specifications requirements",
                    f"{base_query} installation implementation",
                    f"{base_query} control approval",
                    f"{base_query} documentation drawings",
                ]

                fallback_page = {
                    "id": f"page-{cluster_id}",
                    "title": cluster_name,
                    "description": f"Comprehensive information about {cluster_name.lower()} in the project",
                    "proposed_queries": fallback_queries,
                    "related_pages": [],
                    "relevance_score": "7",
                    "topic_argumentation": f"Based on semantic clustering - {summary.get('chunk_count', 0)} chunks identified",
                }
                fallback_pages.append(fallback_page)

            fallback_structure = {
                "title": "Construction Project Wiki (Fallback)",
                "description": "Automatically generated wiki based on document analysis",
                "pages": fallback_pages,
            }

            return fallback_structure

    def _parse_json_response(self, llm_response: str) -> Dict:
        """Robust JSON parsing that handles markdown code fences and various LLM response formats."""
        import json
        import re

        # Clean the response
        response = llm_response.strip()

        # Remove markdown code fences
        if response.startswith("```json"):
            response = response[7:]  # Remove ```json
        elif response.startswith("```"):
            response = response[3:]  # Remove ```

        if response.endswith("```"):
            response = response[:-3]  # Remove trailing ```

        # Remove any leading/trailing whitespace
        response = response.strip()

        # Try to find JSON content using regex if direct parsing fails
        json_pattern = r"\{.*\}"
        json_match = re.search(json_pattern, response, re.DOTALL)

        if json_match:
            response = json_match.group(0)

        try:
            # First attempt: direct parsing
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"⚠️  Direct JSON parsing failed: {str(e)}")
            print(f"⚠️  Attempting to clean response...")

            # Second attempt: try to extract JSON from the response
            try:
                # Look for JSON-like structure
                start_idx = response.find("{")
                end_idx = response.rfind("}")

                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_content = response[start_idx : end_idx + 1]
                    return json.loads(json_content)
                else:
                    raise ValueError("No valid JSON structure found in response")

            except (json.JSONDecodeError, ValueError) as e2:
                print(f"⚠️  JSON extraction also failed: {str(e2)}")
                print(f"⚠️  Raw response preview: {response[:200]}...")
                raise ValueError(f"Failed to parse JSON response: {str(e2)}")

    async def retrieve_page_content(
        self, wiki_structure: Dict, metadata: Dict
    ) -> Dict[str, Dict]:
        """Step 6: PAGE QUERY TO VECTOR DB - Retrieve specific content for each planned wiki page."""
        print(f"Trin 6: Henter indhold til wiki-sider via vector database...")

        pages = wiki_structure.get("pages", [])
        document_ids = [doc["id"] for doc in metadata["documents"]]
        page_content_results = {}

        for page in pages:
            page_id = page.get("id", "unknown")
            page_title = page.get("title", "Unknown Page")
            proposed_queries = page.get("proposed_queries", [])

            print(f"  Behandler side: {page_title} ({len(proposed_queries)} queries)")

            # Execute all proposed queries for this page
            page_chunks = []
            query_results = {}

            for i, query in enumerate(proposed_queries):
                print(f"    Query {i+1}/{len(proposed_queries)}: {query[:50]}...")

                try:
                    results = await self.vector_similarity_search(query, document_ids)
                    query_results[query] = {
                        "results_count": len(results),
                        "avg_similarity": (
                            np.mean([score for _, score in results]) if results else 0.0
                        ),
                        "chunks": [
                            {"chunk_id": chunk.get("id"), "similarity": score}
                            for chunk, score in results
                        ],
                    }

                    # Collect unique chunks for this page
                    for chunk, score in results:
                        chunk_id = chunk.get("id")

                        # Avoid duplicates within this page
                        if not any(
                            existing.get("id") == chunk_id for existing in page_chunks
                        ):
                            chunk_with_score = chunk.copy()
                            chunk_with_score["similarity_score"] = score
                            chunk_with_score["retrieved_by_query"] = query
                            page_chunks.append(chunk_with_score)

                except Exception as e:
                    print(f"      ⚠️  Query fejlede: {str(e)}")
                    query_results[query] = {
                        "results_count": 0,
                        "avg_similarity": 0.0,
                        "error": str(e),
                    }

            # Analyze source document diversity
            source_documents = {}
            for chunk in page_chunks:
                doc_id = chunk.get("document_id")
                if doc_id:
                    if doc_id not in source_documents:
                        source_documents[doc_id] = 0
                    source_documents[doc_id] += 1

            # Calculate content coverage metrics
            total_similarity = sum(
                chunk.get("similarity_score", 0) for chunk in page_chunks
            )
            avg_similarity = total_similarity / len(page_chunks) if page_chunks else 0.0

            content_coverage = (
                "høj"
                if len(source_documents) >= 5
                else "medium" if len(source_documents) >= 3 else "lav"
            )

            page_content = {
                "page_id": page_id,
                "page_title": page_title,
                "retrieved_chunks": page_chunks,
                "source_documents": source_documents,
                "query_results": query_results,
                "total_chunks": len(page_chunks),
                "unique_sources": len(source_documents),
                "avg_similarity": avg_similarity,
                "content_coverage": content_coverage,
            }

            page_content_results[page_id] = page_content

            print(
                f"    ✅ {len(page_chunks)} chunks fra {len(source_documents)} dokumenter (coverage: {content_coverage})"
            )

            # Warn if coverage is insufficient
            if len(source_documents) < 3:
                print(
                    f"    ⚠️  Lav kildediversitet for {page_title} - kun {len(source_documents)} dokumenter"
                )

        print(f"Indhold hentet til {len(page_content_results)} wiki-sider")
        return page_content_results

    def generate_wiki_page_llm(
        self, page_info: Dict, page_content: Dict, metadata: Dict
    ) -> str:
        """Step 7: PAGE LLM CALL - Generate comprehensive markdown wiki page."""
        page_title = page_info.get("title", "Unknown Page")
        page_description = page_info.get("description", "")

        print(f"    Generating markdown for: {page_title}")

        # Prepare document excerpts from retrieved chunks
        retrieved_chunks = page_content.get("retrieved_chunks", [])
        source_docs = page_content.get("source_documents", {})

        # Limit to top chunks to avoid token overflow
        top_chunks = sorted(
            retrieved_chunks, key=lambda x: x.get("similarity_score", 0), reverse=True
        )[:20]

        # Create document excerpts with source attribution
        document_excerpts = []
        source_counter = 1
        source_map = {}  # Map document_id to footnote number

        for chunk in top_chunks:
            content = chunk.get("content", "")
            doc_id = chunk.get("document_id", "unknown")
            metadata_chunk = chunk.get("metadata", {})
            page_number = (
                metadata_chunk.get("page_number", "N/A") if metadata_chunk else "N/A"
            )
            similarity = chunk.get("similarity_score", 0.0)

            # Create source reference
            if doc_id not in source_map:
                source_map[doc_id] = source_counter
                source_counter += 1

            source_ref = source_map[doc_id]

            excerpt = f"""
Excerpt {len(document_excerpts)+1}:
Source: [Document {source_ref}, page {page_number}]
Relevance: {similarity:.3f}
Content: {content[:600]}...
"""
            document_excerpts.append(excerpt)

        # Create source footnotes
        footnotes = []
        for doc_id, ref_num in source_map.items():
            # Find document info from metadata
            doc_info = None
            for doc in metadata.get("documents", []):
                if doc.get("id") == doc_id:
                    doc_info = doc
                    break

            filename = (
                doc_info.get("filename", f"document_{doc_id[:8]}")
                if doc_info
                else f"document_{doc_id[:8]}"
            )
            footnotes.append(f"[{ref_num}] {filename}")

        excerpts_text = "\n".join(
            document_excerpts[:12]
        )  # Limit excerpts to avoid token overflow
        footnotes_text = "\n".join(footnotes)

        # Create comprehensive English prompt for markdown generation
        prompt = f"""You are an expert construction project analyst and technical writer.

Your task is to generate a comprehensive and accurate construction project wiki page in Markdown format about a specific aspect, system, or component within a given construction project.

You will be given:

1. The "[PAGE_TITLE]" for the page you need to create and [PAGE_DESCRIPTION].

2. A list of "[RELEVANT_PAGE_RETRIEVED_CHUNKS]" from the construction project that you MUST use as the sole basis for the content. You have access to the full content of these document excerpts retrieved from project PDFs, specifications, contracts, and drawings. You MUST use AT LEAST 5 relevant document sources for comprehensive coverage - if fewer are provided, you MUST note this limitation.

CRITICAL STARTING INSTRUCTION:
The main title of the page should be a H1 Markdown heading.

Based ONLY on the content of the [RELEVANT_PAGE_RETRIEVED_CHUNKS]:

1. **Introduction:** Start with a concise introduction (1-2 paragraphs) explaining the purpose, scope, and high-level overview of "{page_title}" within the context of the overall construction project. Immediately after this, provide a table of the sections on this page with name of section and a short description of each section.

2. **Detailed Sections:** Break down "{page_title}" into logical sections using H2 (`##`) and H3 (`###`) Markdown headings. For each section:
   * Explain the project requirements, specifications, processes, or deliverables relevant to the section's focus, as evidenced in the source documents.
   * Identify key stakeholders, contractors, materials, systems, regulatory requirements, or project phases pertinent to that section.
   * Include relevant quantities, dimensions, costs, and timeline information where available.

3. **Mermaid Diagrams:**
   * EXTENSIVELY use Mermaid diagrams (e.g., `flowchart TD`, `sequenceDiagram`, `gantt`, `graph TD`, `Entity Relationship`, `Block`, `Git`, `Pie`, `Sankey`, `Timeline`) to visually represent project workflows, construction sequences, stakeholder relationships, and process flows found in the source documents.
   * Ensure diagrams are accurate and directly derived from information in the `[RELEVANT_PAGE_RETRIEVED_CHUNKS]`.
   * Provide a brief explanation before or after each diagram to give context.
   * CRITICAL: All diagrams MUST follow strict vertical orientation:
     - Use "graph TD" (top-down) directive for flow diagrams
     - NEVER use "graph LR" (left-right)
     - Maximum node width should be 3-4 words
     - For sequence diagrams:
       - Start with "sequenceDiagram" directive on its own line
       - Define ALL participants at the beginning (Client, Contractor, Architect, Engineer, Inspector, etc.)
       - Use descriptive but concise participant names
       - Use the correct arrow types:
         - ->> for submissions/requests
         - -->> for approvals/responses  
         - -x for rejections/failures
       - Include activation boxes using +/- notation
       - Add notes for clarification using "Note over" or "Note right of"
     - For Gantt charts:
       - Use "gantt" directive
       - Include project phases, milestones, and dependencies
       - Show timeline relationships and critical path activities

4. **Tables:**
   * Use Markdown tables to summarize information such as:
     * Key project requirements, specifications, and acceptance criteria
     * Material quantities, types, suppliers, and delivery schedules
     * Contractor responsibilities, deliverables, and completion dates
     * Regulatory requirements, permits, inspections, and compliance deadlines
     * Cost breakdowns, budget allocations, and payment milestones
     * Quality standards, testing procedures, and documentation requirements
     * Safety protocols, risk assessments, and mitigation measures

5. **Document Excerpts (ENTIRELY OPTIONAL):**
   * Include short, relevant excerpts directly from the `[RELEVANT_DOCUMENT_EXCERPTS]` to illustrate key project requirements, specifications, or contractual terms.
   * Ensure excerpts are well-formatted within Markdown quote blocks.
   * Use excerpts to support technical specifications, quality requirements, or critical project constraints.

6. **Source Citations (EXTREMELY IMPORTANT):**
   * For EVERY piece of significant information, explanation, diagram, table entry, or document excerpt, you MUST cite the specific source document(s) and relevant page numbers or sections from which the information was derived.
   * Use standard markdown reference-style citations with numbered footnotes at the end of sentences or paragraphs.
   * Format citations as: The project budget is €2.5 million[1][p. 5-7] where [1] links to the footnote reference. and [p. 5-7] links to the page number.
   * Place all footnote definitions on a new line each at the bottom of each section on the page using the format:
     [1]: contract.pdf, page 5-7
     [2]: specifications.pdf, section 3.2  
     [3]: drawings.dwg, sheet A1
     [4]: safety_plan.pdf, section 4.2
     [5]: material_specs.xlsx, concrete_sheet

   For multiple sources supporting one claim, use: Construction will begin in March 2024[1][2][3]
   IMPORTANT: You MUST cite AT LEAST 5 different source documents throughout the wiki page to ensure comprehensive coverage when available.

7. **Technical Accuracy:** All information must be derived SOLELY from the `[RELEVANT_DOCUMENT_EXCERPTS]`. Do not infer, invent, or use external knowledge about construction practices, building codes, or industry standards unless it's directly supported by the provided project documents. If information is not present in the provided excerpts, do not include it or explicitly state its absence if crucial to the topic.

8. **Construction Professional Language:** Use clear, professional, and concise technical language suitable for project managers, contractors, architects, engineers, inspectors, and other construction professionals working on or learning about the project. Use correct construction and engineering terminology, including Danish construction terms when they appear in the source documents.

9. **Image/table summaries:** If some of the sources you retrieve are tables and images, then list them in a table format like below: 

| Drawing | Area | Description |
| :--- | :--- | :--- |
| `112727-01_K07_H1_EK_61.101` | Basement | Shows location of main panel (HT) and main cross-field (HX). |
| `112727-01_K07_H1_E0_61.102` | Ground floor | Routing paths in common areas, café and multi-room. |

10. **Conclusion/Summary:** End with a brief summary paragraph if appropriate for "{page_title}", reiterating the key aspects covered, critical deadlines, major deliverables, and their significance within the overall construction project. If relevant, and if information is available in the provided documents, list the to other potential wiki pages using below these paragraphs. 

IMPORTANT: Generate the content in Danish language.

Remember:
- Ground every claim in the provided project document excerpts
- Prioritize accuracy and direct representation of the project's actual requirements, specifications, and constraints
- Structure the document logically for easy understanding by construction professionals
- Include specific quantities, dates, costs, and technical specifications when available in the documents
- Focus on practical project information that can guide construction activities
- Highlight critical path items, regulatory requirements, and quality control measures
- Emphasize safety requirements and compliance obligations throughout

PAGE_TITLE: {page_title}
PAGE_DESCRIPTION: {page_description}
RELEVANT_PAGE_RETRIEVED_CHUNKS:
{excerpts_text}

RELEVANT_DOCUMENT_EXCERPTS:
{footnotes_text}

Generate the comprehensive markdown wiki page:"""

        try:
            start_time = time.time()
            markdown_content = self.call_openrouter_api(prompt, max_tokens=4000)
            end_time = time.time()

            print(
                f"      Markdown generated in {end_time - start_time:.1f} seconds ({len(markdown_content)} characters)"
            )

            return markdown_content

        except Exception as e:
            print(f"      ⚠️  LLM markdown generation failed: {str(e)}")

            # Fallback markdown structure
            fallback_content = f"""# {page_title}

## Overview
{page_description}

## Content (Fallback Mode)
This is an automatically generated page based on {len(retrieved_chunks)} document excerpts from {len(source_docs)} different sources.

### Key Data
- Documents analyzed: {len(source_docs)}
- Text segments: {len(retrieved_chunks)}
- Average relevance: {page_content.get('avg_similarity', 0):.2f}

### Top Content
{retrieved_chunks[0].get('content', 'No content available')[:500] + '...' if retrieved_chunks else 'No chunks found'}

## Sources
{footnotes_text}

**Note:** This is fallback content generated automatically as the LLM API failed.
"""

            return fallback_content

    async def generate_complete_wiki(
        self, wiki_structure: Dict, page_content_results: Dict, metadata: Dict
    ) -> Dict[str, str]:
        """Generate all wiki pages as markdown files."""
        print(f"Trin 7: Genererer komplette markdown wiki-sider...")

        pages = wiki_structure.get("pages", [])
        wiki_pages = {}

        for page in pages:
            page_id = page.get("id", "unknown")
            page_title = page.get("title", "Unknown Page")

            # Get content for this page
            page_content = page_content_results.get(page_id, {})

            if not page_content.get("retrieved_chunks"):
                print(f"    ⚠️  Ingen indhold fundet for {page_title} - springer over")
                continue

            # Generate markdown content
            markdown_content = self.generate_wiki_page_llm(page, page_content, metadata)

            # Store with clean filename
            clean_filename = page_id.replace(" ", "-").lower()
            wiki_pages[f"{clean_filename}.md"] = markdown_content

            print(f"    ✅ {page_title} genereret ({len(markdown_content)} tegn)")

        print(f"Komplet wiki genereret: {len(wiki_pages)} markdown filer")
        return wiki_pages

    async def generate_complete_seven_step_wiki(
        self, index_run_id: str
    ) -> Dict[str, Any]:
        """Execute the complete 7-step wiki generation pipeline."""
        print(
            f"🚀 Starter komplet 7-trins wiki generering for indexing run: {index_run_id}"
        )
        print(f"Konfiguration: {self.language} sprog, {self.model} model")

        start_time = time.time()
        results = {"index_run_id": index_run_id}

        try:
            # Step 1: Collect metadata
            print(f"\n" + "=" * 50)
            metadata = self.fetch_project_metadata(index_run_id)
            results["metadata"] = metadata

            # Step 2: Query vector DB for overview
            print(f"\n" + "=" * 50)
            overview_data = await self.query_project_overview(metadata)
            results["overview_queries"] = overview_data

            # Step 3: Generate LLM overview
            print(f"\n" + "=" * 50)
            project_overview = self.generate_project_overview_llm(overview_data)
            results["project_overview"] = project_overview

            # Step 4: Semantic clustering for topic identification
            print(f"\n" + "=" * 50)
            semantic_analysis = self.semantic_clustering(
                metadata["chunks_with_embeddings"]
            )
            results["semantic_analysis"] = semantic_analysis

            # Step 5: Structure LLM call - create strategic wiki structure
            print(f"\n" + "=" * 50)
            wiki_structure = self.generate_wiki_structure_llm(
                project_overview, semantic_analysis, metadata
            )
            results["wiki_structure"] = wiki_structure

            # Step 6: Page query to vector DB - retrieve content for each page
            print(f"\n" + "=" * 50)
            page_content_results = await self.retrieve_page_content(
                wiki_structure, metadata
            )
            results["page_content"] = page_content_results

            # Step 7: Page LLM calls - generate markdown wiki pages
            print(f"\n" + "=" * 50)
            wiki_pages = await self.generate_complete_wiki(
                wiki_structure, page_content_results, metadata
            )
            results["wiki_pages"] = wiki_pages

            # Save all results and wiki files
            clean_results = self.clean_results_for_saving(results)
            output_dir = self.save_intermediate_results(
                index_run_id, "complete_seven_steps", clean_results
            )

            # Save individual wiki pages as files
            wiki_dir = os.path.join(output_dir, "wiki_pages")
            os.makedirs(wiki_dir, exist_ok=True)

            for filename, content in wiki_pages.items():
                wiki_file_path = os.path.join(wiki_dir, filename)
                with open(wiki_file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  📄 Wiki side gemt: {filename}")

            # Print comprehensive summary
            end_time = time.time()
            processing_time = end_time - start_time

            print(f"\n" + "=" * 60)
            print("KOMPLET 7-TRINS WIKI GENERERING FULDFØRT")
            print("=" * 60)
            print(f"Index Run ID: {index_run_id}")
            print(f"Samlet behandlingstid: {processing_time:.1f} sekunder")

            print(f"\n📊 PIPELINE RESULTATER:")
            print(f"Trin 1-4 - Grundlæggende analyse:")
            print(f"  • Dokumenter: {metadata['total_documents']}")
            print(f"  • Chunks: {metadata['total_chunks']}")
            print(f"  • Sider: {metadata['total_pages_analyzed']}")
            print(f"  • Semantiske klynger: {semantic_analysis['n_clusters']}")

            print(f"\nTrin 5 - Wiki struktur:")
            wiki_title = wiki_structure.get("title", "N/A")
            wiki_pages_count = len(wiki_structure.get("pages", []))
            print(f"  • Wiki titel: {wiki_title}")
            print(f"  • Planlagte sider: {wiki_pages_count}")

            print(f"\nTrin 6 - Indholdsopsamling:")
            total_retrieved_chunks = sum(
                content.get("total_chunks", 0)
                for content in page_content_results.values()
            )
            avg_sources_per_page = (
                np.mean(
                    [
                        content.get("unique_sources", 0)
                        for content in page_content_results.values()
                    ]
                )
                if page_content_results
                else 0
            )
            print(f"  • Samlede chunks hentet: {total_retrieved_chunks}")
            print(f"  • Gennemsnitlige kilder per side: {avg_sources_per_page:.1f}")

            print(f"\nTrin 7 - Wiki generering:")
            total_wiki_chars = sum(len(content) for content in wiki_pages.values())
            print(f"  • Genererede wiki-sider: {len(wiki_pages)}")
            print(f"  • Samlet indhold: {total_wiki_chars:,} tegn")
            print(
                f"  • Gennemsnitlig sidelængde: {total_wiki_chars // len(wiki_pages) if wiki_pages else 0:,} tegn"
            )

            print(f"\n📁 OUTPUT FILER:")
            print(f"  • Resultater gemt i: {output_dir}")
            print(f"  • Wiki markdown filer: {wiki_dir}")
            print(f"  • Wiki sider:")
            for filename in sorted(wiki_pages.keys()):
                print(f"    - {filename}")

            print(f"\n🎉 WIKI KLAR TIL BRUG!")

            return results

        except Exception as e:
            print(f"❌ Fejl under komplet wiki generering: {str(e)}")
            raise

    async def generate_first_four_steps(self, index_run_id: str) -> Dict[str, Any]:
        """Execute the first 4 steps of wiki generation pipeline (legacy method for compatibility)."""
        print(f"🚀 Starter wiki generering for indexing run: {index_run_id}")
        print(f"Konfiguration: {self.language} sprog, {self.model} model")

        start_time = time.time()
        results = {"index_run_id": index_run_id}

        try:
            # Step 1: Collect metadata
            metadata = self.fetch_project_metadata(index_run_id)
            results["metadata"] = metadata

            # Step 2: Query vector DB for overview
            overview_data = await self.query_project_overview(metadata)
            results["overview_queries"] = overview_data

            # Step 3: Generate LLM overview
            project_overview = self.generate_project_overview_llm(overview_data)
            results["project_overview"] = project_overview

            # Step 4: Semantic clustering for topic identification
            semantic_analysis = self.semantic_clustering(
                metadata["chunks_with_embeddings"]
            )
            results["semantic_analysis"] = semantic_analysis

            # Clean results for saving (remove large data)
            clean_results = self.clean_results_for_saving(results)

            # Save intermediate results
            output_dir = self.save_intermediate_results(
                index_run_id, "first_four_steps", clean_results
            )

            # Print summary
            end_time = time.time()
            processing_time = end_time - start_time

            print(f"\n" + "=" * 60)
            print("FØRSTE FIRE TRIN GENNEMFØRT")
            print("=" * 60)
            print(f"Index Run ID: {index_run_id}")
            print(f"Behandlingstid: {processing_time:.1f} sekunder")

            print(f"\nTrin 1 - Metadata:")
            print(f"  Dokumenter: {metadata['total_documents']}")
            print(f"  Chunks: {metadata['total_chunks']}")
            print(f"  Sider: {metadata['total_pages_analyzed']}")

            print(f"\nTrin 2 - Vector queries:")
            print(f"  Unikke chunks hentet: {overview_data['total_unique_chunks']}")
            print(
                f"  Gennemsnitlig relevans: {np.mean([result['avg_similarity'] for result in overview_data['query_results'].values()]):.2f}"
            )

            print(f"\nTrin 3 - LLM oversigt:")
            print(f"  Generet oversigt: {len(project_overview)} tegn")
            print(f"  Første linjer:")
            for line in project_overview.split("\n")[:3]:
                if line.strip():
                    print(f"    {line[:80]}...")

            print(f"\nTrin 4 - Semantisk analyse med LLM navngivning:")
            print(f"  Antal klynger: {semantic_analysis['n_clusters']}")
            print(f"  LLM-genererede navne:")
            for summary in semantic_analysis["cluster_summaries"][:3]:
                print(f"    {summary['cluster_name']}: {summary['chunk_count']} chunks")

            print(f"\nResultater gemt i: {output_dir}")

            return results

        except Exception as e:
            print(f"❌ Fejl under generering: {str(e)}")
            raise

    async def test_step_5_isolated(self, index_run_id: str = None) -> Dict:
        """Test Step 5 in isolation to validate JSON parsing and strategic thinking."""
        print(f"🧪 Testing Step 5 (Wiki Structure Generation) in isolation...")

        if index_run_id:
            # Use actual data from the specified index run
            print(f"Using actual data from index run: {index_run_id}")

            # Step 1: Collect metadata
            metadata = self.fetch_project_metadata(index_run_id)

            # Step 2: Query vector DB for overview
            overview_data = await self.query_project_overview(metadata)

            # Step 3: Generate LLM overview
            project_overview = self.generate_project_overview_llm(overview_data)

            # Step 4: Semantic clustering
            semantic_analysis = self.semantic_clustering(
                metadata["chunks_with_embeddings"]
            )

        else:
            # Use sample data for testing
            print(f"Using sample data for testing...")

            metadata = {
                "documents": [
                    {
                        "id": "doc1",
                        "filename": "electrical_specs.pdf",
                        "page_count": 50,
                        "file_size": 1024000,
                    },
                    {
                        "id": "doc2",
                        "filename": "safety_requirements.pdf",
                        "page_count": 30,
                        "file_size": 512000,
                    },
                    {
                        "id": "doc3",
                        "filename": "project_overview.pdf",
                        "page_count": 20,
                        "file_size": 256000,
                    },
                ],
                "section_headers_distribution": {
                    "Electrical Systems": 15,
                    "Safety Requirements": 12,
                    "Project Timeline": 8,
                    "Material Specifications": 6,
                },
            }

            project_overview = """This is a comprehensive construction project for a commercial building in Copenhagen. 
            The project involves electrical installations, safety systems, and material specifications. 
            The project is managed by a team of architects, engineers, and contractors."""

            semantic_analysis = {
                "cluster_summaries": [
                    {
                        "cluster_id": 0,
                        "cluster_name": "Electrical Systems",
                        "chunk_count": 45,
                    },
                    {
                        "cluster_id": 1,
                        "cluster_name": "Safety Requirements",
                        "chunk_count": 32,
                    },
                    {
                        "cluster_id": 2,
                        "cluster_name": "Project Timeline",
                        "chunk_count": 28,
                    },
                    {
                        "cluster_id": 3,
                        "cluster_name": "Material Specifications",
                        "chunk_count": 25,
                    },
                ]
            }

        # Step 5: Test wiki structure generation
        print(f"\n" + "=" * 50)
        print("TESTING STEP 5: WIKI STRUCTURE GENERATION")
        print("=" * 50)

        try:
            wiki_structure = self.generate_wiki_structure_llm(
                project_overview, semantic_analysis, metadata
            )

            print(f"\n✅ Step 5 test completed successfully!")
            print(f"📊 Results:")
            print(f"  - Wiki title: {wiki_structure.get('title', 'N/A')}")
            print(f"  - Number of pages: {len(wiki_structure.get('pages', []))}")
            print(
                f"  - Has overview page: {'Yes' if any('overview' in page.get('title', '').lower() for page in wiki_structure.get('pages', [])) else 'No'}"
            )

            print(f"\n📄 Generated pages:")
            for i, page in enumerate(wiki_structure.get("pages", []), 1):
                print(f"  {i}. {page.get('title', 'N/A')}")
                print(f"     - ID: {page.get('id', 'N/A')}")
                print(f"     - Description: {page.get('description', 'N/A')[:100]}...")
                print(f"     - Queries: {len(page.get('proposed_queries', []))}")
                print(f"     - Relevance score: {page.get('relevance_score', 'N/A')}")
                print(
                    f"     - Argumentation: {page.get('topic_argumentation', 'N/A')[:100]}..."
                )
                print()

            # Validate strategic thinking
            strategic_indicators = []
            pages = wiki_structure.get("pages", [])

            # Check for overview page
            if any("overview" in page.get("title", "").lower() for page in pages):
                strategic_indicators.append("✅ Has overview page")
            else:
                strategic_indicators.append("❌ Missing overview page")

            # Check for professional page titles (not just cluster names)
            professional_titles = []
            cluster_names = [
                summary["cluster_name"]
                for summary in semantic_analysis.get("cluster_summaries", [])
            ]

            for page in pages:
                title = page.get("title", "")
                if title not in cluster_names and len(title.split()) >= 2:
                    professional_titles.append(title)

            if (
                len(professional_titles) >= len(pages) * 0.5
            ):  # At least 50% should be professional
                strategic_indicators.append("✅ Professional page titles")
            else:
                strategic_indicators.append("❌ Too many cluster-based titles")

            # Check for adequate queries
            adequate_queries = all(
                len(page.get("proposed_queries", [])) >= 6 for page in pages
            )
            if adequate_queries:
                strategic_indicators.append("✅ Adequate queries per page (6-10)")
            else:
                strategic_indicators.append("❌ Insufficient queries per page")

            print(f"🎯 Strategic Analysis:")
            for indicator in strategic_indicators:
                print(f"  {indicator}")

            return wiki_structure

        except Exception as e:
            print(f"❌ Step 5 test failed: {str(e)}")
            raise

    async def test_step_5_with_real_data(self, index_run_id: str) -> Dict:
        """Test Step 5 with real data from a specific index run."""
        print(f"🧪 Testing Step 5 with real data from index run: {index_run_id}")

        try:
            # Execute first 4 steps to get real data
            results = await self.generate_first_four_steps(index_run_id)

            # Extract the data needed for Step 5
            metadata = results.get("metadata", {})
            project_overview = results.get("project_overview", "")
            semantic_analysis = results.get("semantic_analysis", {})

            # Test Step 5 with real data
            wiki_structure = self.generate_wiki_structure_llm(
                project_overview, semantic_analysis, metadata
            )

            print(f"\n✅ Step 5 test with real data completed!")
            return wiki_structure

        except Exception as e:
            print(f"❌ Step 5 test with real data failed: {str(e)}")
            raise


async def main():
    """Command line interface for wiki generation."""
    parser = argparse.ArgumentParser(
        description="Generate automatic wiki from indexing run"
    )
    parser.add_argument("--index-run-id", required=True, help="UUID of indexing run")
    parser.add_argument(
        "--language",
        default="danish",
        choices=["danish", "english"],
        help="Output language",
    )
    parser.add_argument(
        "--model", default="google/gemini-2.5-flash", help="OpenRouter model to use"
    )
    parser.add_argument(
        "--complete",
        action="store_true",
        help="Generate complete 7-step wiki (default: only first 4 steps)",
    )
    parser.add_argument(
        "--test-step-5",
        action="store_true",
        help="Test Step 5 (Wiki Structure Generation) in isolation",
    )
    parser.add_argument(
        "--test-step-5-real",
        action="store_true",
        help="Test Step 5 with real data from the specified index run",
    )

    args = parser.parse_args()

    try:
        generator = MarkdownWikiGenerator(language=args.language, model=args.model)

        if args.test_step_5:
            # Test Step 5 with sample data
            results = await generator.test_step_5_isolated()
            print(f"\n✅ Step 5 test completed successfully!")
            print(f"📄 Generated JSON structure:")
            import json

            print(json.dumps(results, indent=2, ensure_ascii=False))

        elif args.test_step_5_real:
            # Test Step 5 with real data
            results = await generator.test_step_5_with_real_data(args.index_run_id)
            print(f"\n✅ Step 5 test with real data completed!")
            print(f"📄 Generated JSON structure:")
            import json

            print(json.dumps(results, indent=2, ensure_ascii=False))

        elif args.complete:
            results = await generator.generate_complete_seven_step_wiki(
                args.index_run_id
            )
            print(f"\n✅ Complete 7-step wiki generation successful!")
        else:
            results = await generator.generate_first_four_steps(args.index_run_id)
            print(f"\n✅ First four steps completed successfully!")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
