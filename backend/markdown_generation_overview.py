#!/usr/bin/env python3
"""
ConstructionRAG - Advanced Markdown Wiki Generation

This script generates comprehensive multi-page wiki documentation from construction project data
using a sophisticated 3-step RAG approach with semantic clustering and vector similarity search.

Usage:
    python markdown_generation_overview.py --index-run-id 668ecac8-beb5-4f94-94d6-eee8c771044d
    python markdown_generation_overview.py --index-run-id <id> --language danish --model google/gemini-2.5-flash
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
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from config.database import get_supabase_admin_client

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


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
    
    def __init__(self, language: str = "danish", model: str = "google/gemini-2.5-flash"):
        self.language = language
        self.model = model
        self.supabase = get_supabase_admin_client()
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env file")
        
        # Initialize Voyage client for real vector search
        voyage_api_key = os.getenv("VOYAGE_API_KEY")
        if not voyage_api_key:
            raise ValueError("VOYAGE_API_KEY not found in .env file - needed for real vector similarity search")
        
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
            print(f"- API Key preview: {self.openrouter_api_key[:10]}...{self.openrouter_api_key[-4:]}")
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration settings."""
        return {
            "similarity_threshold": 0.3,  # Lower threshold for testing - more permissive
            "max_chunks_per_query": 10,   # Maximum chunks to return per query
            "overview_query_count": 12,   # Number of overview queries to use
            "semantic_clusters": {
                "min_clusters": 4,
                "max_clusters": 10
            }
        }
    
    def fetch_project_metadata(self, index_run_id: str) -> Dict[str, Any]:
        """Step 1: SUPABASE TABLES - Collect metadata about the project."""
        print(f"Trin 1: Henter projektmetadata for indexing run: {index_run_id}")
        
        # Get indexing run with step results
        indexing_run_response = self.supabase.table("indexing_runs").select("*").eq("id", index_run_id).execute()
        
        if not indexing_run_response.data:
            raise ValueError(f"Ingen indexing run fundet med ID: {index_run_id}")
        
        indexing_run = indexing_run_response.data[0]
        step_results = indexing_run.get("step_results", {})
        
        # Get documents
        documents_response = self.supabase.table("indexing_run_documents").select(
            "document_id, documents(*)"
        ).eq("indexing_run_id", index_run_id).execute()
        
        documents = [item["documents"] for item in documents_response.data if item["documents"]]
        document_ids = [doc["id"] for doc in documents]
        
        # Get chunks with embeddings (but don't store embeddings in output)
        chunks_response = self.supabase.table("document_chunks").select(
            "id, document_id, content, metadata, embedding_1024"
        ).in_("document_id", document_ids).execute()
        
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
                "metadata": metadata
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
            "chunks_with_embeddings": chunks_with_embeddings  # For processing only
        }
        
        # Extract pages analyzed (sum from all documents)
        total_pages = sum(doc.get("page_count", 0) for doc in documents if doc.get("page_count"))
        metadata["total_pages_analyzed"] = total_pages
        
        # Extract from chunking step
        chunking_data = step_results.get("chunking", {}).get("data", {})
        if chunking_data:
            summary_stats = chunking_data.get("summary_stats", {})
            metadata["section_headers_distribution"] = summary_stats.get("section_headers_distribution", {})
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
    
    async def vector_similarity_search(self, query_text: str, document_ids: List[str], top_k: int = None) -> List[Tuple[Dict, float]]:
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
                        similarity = self.cosine_similarity(query_embedding, chunk_embedding)
                        
                        # Convert to distance for sorting (like production pipeline)
                        distance = 1 - similarity
                        
                        results_with_scores.append({
                            "chunk": chunk,
                            "similarity": similarity,
                            "distance": distance
                        })
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
            
            print(f"  Fundet {len(results)} relevante unikke chunks (threshold: {self.config['similarity_threshold']})")
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
            "kvadratmeter etageareal størrelse dimensioner omfang"
        ]
        
        # Get document IDs for vector search
        document_ids = [doc["id"] for doc in metadata["documents"]]
        all_retrieved_chunks = []
        query_results = {}
        
        # Execute each query
        for i, query in enumerate(project_overview_queries[:self.config["overview_query_count"]]):
            print(f"  Query {i+1}/{self.config['overview_query_count']}: {query}")
            
            results = await self.vector_similarity_search(query, document_ids)
            query_results[query] = {
                "results_count": len(results),
                "chunks": [{"chunk_id": chunk.get("id"), "similarity_score": score, "content_preview": chunk.get("content", "")[:100] + "..."} 
                          for chunk, score in results],
                "avg_similarity": np.mean([score for _, score in results]) if results else 0.0
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
            "total_unique_chunks": len(all_retrieved_chunks)
        }
    
    def call_openrouter_api(self, prompt: str, max_tokens: int = 4000) -> str:
        """Call OpenRouter API with the given prompt."""
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://constructionrag.com",
            "X-Title": "ConstructionRAG Wiki Generator"
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
            raise Exception(f"OpenRouter API fejl: {response.status_code} - {response.text}")
        
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
            
            print(f"LLM projektoversigt genereret på {end_time - start_time:.1f} sekunder")
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
    
    def generate_cluster_name(self, text: str, cluster_id: int, used_names: set = None) -> str:
        """Generate meaningful cluster name based on content with uniqueness."""
        if used_names is None:
            used_names = set()
            
        # Danish construction terms to identify themes with more granular categories
        construction_themes = {
            "el_installation": ["elektrisk", "el-", "installation", "kabel", "stik", "ledning", "strøm", "el ", "elektro"],
            "el_system": ["elinstallation", "elsystem", "hovedbord", "fordeling", "sikring", "jordforbindelse"],
            "tegning_plan": ["plantegning", "plan", "grundplan", "etageplan", "situationsplan"],
            "tegning_snit": ["snit", "tværsnit", "længdesnit", "facade", "opstalt", "detalje"],  
            "sikkerhed_brand": ["brandsikkerhed", "branddetektorer", "sprinkler", "brandvæg", "flugtplan"],
            "sikkerhed_adgang": ["adgangskontrol", "dørtelefon", "kort", "låsning", "nøgle", "sikkerhedssystem"],
            "bygning_struktur": ["bærende", "konstruktion", "fundament", "etage", "dæk", "søjle", "bjælke"],
            "bygning_rum": ["rum", "lokale", "kælder", "loft", "toilet", "køkken", "kontor"],
            "materiale_beton": ["beton", "armering", "støbning", "betonkvalitet", "cement"],
            "materiale_staal": ["stål", "profiler", "svejsning", "galvaniseret", "korrosion"],
            "materiale_byg": ["murværk", "tegl", "isolering", "tagmateriale", "vinduer", "døre"],
            "ventilation_luft": ["ventilation", "luft", "luftskifte", "kanal", "ventilator"],
            "ventilation_vvs": ["vvs", "varme", "vand", "afløb", "radiator", "pumpe", "kedel"],
            "projekt_plan": ["projektplan", "tidsplan", "milepæl", "fase", "deadline", "planlægning"],
            "projekt_kontrakt": ["kontrakt", "udbud", "tilbud", "pris", "betaling", "leverandør"],
            "kvalitet": ["kvalitet", "kontrol", "inspektion", "test", "godkendelse", "certifikat"],
            "miljø": ["miljø", "bæredygtig", "energi", "affald", "genanvendelse", "klima"]
        }
        
        # Find most relevant themes with scores
        theme_scores = {}
        for theme, keywords in construction_themes.items():
            score = sum(text.lower().count(keyword.lower()) for keyword in keywords)
            if score > 0:  # Only consider themes with actual matches
                theme_scores[theme] = score
        
        # Sort themes by score (highest first)
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Theme name mappings with more specific names
        theme_names = {
            "el_installation": "Elektriske Installationer",
            "el_system": "El-systemer og Fordelinger", 
            "tegning_plan": "Plantegninger og Layouts",
            "tegning_snit": "Tegninger og Detaljer",
            "sikkerhed_brand": "Brandsikkerhed",
            "sikkerhed_adgang": "Adgangskontrol og Sikring",
            "bygning_struktur": "Bygningskonstruktion", 
            "bygning_rum": "Rum og Faciliteter",
            "materiale_beton": "Beton og Armering",
            "materiale_staal": "Stålkonstruktioner",
            "materiale_byg": "Byggematerialer",
            "ventilation_luft": "Ventilationssystemer",
            "ventilation_vvs": "VVS-installationer",
            "projekt_plan": "Projektplanlægning",
            "projekt_kontrakt": "Kontrakt og Økonomi", 
            "kvalitet": "Kvalitetssikring",
            "miljø": "Miljø og Bæredygtighed"
        }
        
        # Try to find unique theme name
        for theme, score in sorted_themes:
            candidate_name = theme_names.get(theme, f"Specialområde {cluster_id}")
            if candidate_name not in used_names:
                used_names.add(candidate_name)
                return candidate_name
        
        # Fallback: create unique generic name
        generic_names = [
            "Tekniske Specifikationer",
            "Projektdokumentation", 
            "Bygningskomponenter",
            "Systemintegration",
            "Udførselsdetaljer",
            "Driftsforhold",
            "Leverandørdokumentation",
            "Godkendelsesprocedurer"
        ]
        
        for generic_name in generic_names:
            if generic_name not in used_names:
                used_names.add(generic_name)
                return generic_name
        
        # Final fallback with cluster ID
        final_name = f"Temaområde {cluster_id}"
        while final_name in used_names:
            cluster_id += 1
            final_name = f"Temaområde {cluster_id}"
        
        used_names.add(final_name)
        return final_name
    
    def semantic_clustering(self, chunks: List[Dict]) -> Dict[str, Any]:
        """Step 4: SEMANTIC ANALYSIS - Perform semantic clustering to identify 4-10 main topics."""
        print(f"Trin 4: Udfører semantisk clustering for emneidentifikation...")
        
        # Filter chunks with embeddings
        chunks_with_embeddings = [
            chunk for chunk in chunks 
            if chunk.get("embedding_1024") is not None
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
                embedding_str = embedding_str.strip('[]')
                embedding_values = [float(x.strip()) for x in embedding_str.split(',')]
                embeddings.append(embedding_values)
            else:
                embeddings.append(embedding_str)
        
        embeddings = np.array(embeddings)
        
        # Determine number of clusters
        n_chunks = len(chunks_with_embeddings)
        n_clusters = min(
            self.config["semantic_clusters"]["max_clusters"], 
            max(self.config["semantic_clusters"]["min_clusters"], n_chunks // 20)
        )
        
        print(f"Klyngedeling i {n_clusters} klynger...")
        
        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        # Group chunks by cluster
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            clusters[label].append(chunks_with_embeddings[i])
        
        # Create cluster summaries with meaningful names - track used names for uniqueness
        used_names = set()
        cluster_summaries = []
        for cluster_id, cluster_chunks in clusters.items():
            # Sample content for summary
            sample_content = []
            for chunk in cluster_chunks[:3]:  # First 3 chunks as samples
                content_preview = chunk.get("content", "")[:150]
                sample_content.append(content_preview)
            
            # Generate cluster name based on most common terms with uniqueness
            all_text = " ".join([chunk.get("content", "") for chunk in cluster_chunks[:10]]).lower()
            cluster_name = self.generate_cluster_name(all_text, int(cluster_id), used_names)
            
            cluster_summary = {
                "cluster_id": int(cluster_id),  # Convert numpy int32 to Python int
                "cluster_name": cluster_name,
                "chunk_count": len(cluster_chunks),
                "sample_content": sample_content,
                "representative_content": " | ".join(sample_content)
            }
            cluster_summaries.append(cluster_summary)
        
        print(f"Klynger oprettet:")
        for summary in cluster_summaries:
            print(f"  {summary['cluster_name']} ({summary['chunk_count']} chunks): {summary['representative_content'][:100]}...")
        
        # Convert clusters dict to have int keys instead of numpy int32
        clusters_dict = {}
        for cluster_id, cluster_chunks in clusters.items():
            clusters_dict[int(cluster_id)] = cluster_chunks
        
        return {
            "clusters": clusters_dict,
            "cluster_summaries": cluster_summaries,
            "n_clusters": n_clusters
        }
    
    def save_intermediate_results(self, index_run_id: str, step_name: str, data: Dict[str, Any]) -> str:
        """Save intermediate results for debugging and analysis."""
        output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "internal", "wiki_generation")
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
                    "filenames": [doc.get("filename", "unknown") for doc in documents[:3]] + (["..."] if len(documents) > 3 else []),
                    "total_file_size": sum(doc.get("file_size", 0) for doc in documents if doc.get("file_size"))
                }
            
            # Replace chunks with minimal summary only
            if "chunks" in metadata:
                chunks = metadata["chunks"]
                metadata["chunks"] = {
                    "total_chunks": len(chunks),
                    "sample_chunk_ids": [chunk.get("id") for chunk in chunks[:3]],
                    "avg_content_length": sum(len(chunk.get("content", "")) for chunk in chunks[:10]) // min(10, len(chunks)) if chunks else 0
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
                    "top_similarities": [chunk.get("similarity_score", 0) for chunk in chunks[:5]],
                    "sample_sources": [f"doc_{chunk.get('document_id', 'unknown')[:8]}" for chunk in chunks[:3]]
                }
            
            # Keep query_results but clean them
            if "query_results" in query_data:
                query_results = query_data["query_results"]
                cleaned_query_results = {}
                for query, result in query_results.items():
                    cleaned_query_results[query[:50] + "..."] = {
                        "results_count": result.get("results_count", 0),
                        "avg_similarity": result.get("avg_similarity", 0.0)
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
                    cleaned_summaries.append({
                        "cluster_id": summary.get("cluster_id"),
                        "cluster_name": summary.get("cluster_name"),
                        "chunk_count": summary.get("chunk_count"),
                        "sample_preview": summary.get("representative_content", "")[:100] + "..." if summary.get("representative_content") else ""
                    })
                semantic_data["cluster_summaries"] = cleaned_summaries
            
            clean_results["semantic_analysis"] = semantic_data
        
        return clean_results
    
    async def generate_first_four_steps(self, index_run_id: str) -> Dict[str, Any]:
        """Execute the first 4 steps of wiki generation pipeline."""
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
            semantic_analysis = self.semantic_clustering(metadata["chunks_with_embeddings"])
            results["semantic_analysis"] = semantic_analysis
            
            # Clean results for saving (remove large data)
            clean_results = self.clean_results_for_saving(results)
            
            # Save intermediate results
            output_dir = self.save_intermediate_results(index_run_id, "first_four_steps", clean_results)
            
            # Print summary
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"\n" + "="*60)
            print("FØRSTE FIRE TRIN GENNEMFØRT")
            print("="*60)
            print(f"Index Run ID: {index_run_id}")
            print(f"Behandlingstid: {processing_time:.1f} sekunder")
            
            print(f"\nTrin 1 - Metadata:")
            print(f"  Dokumenter: {metadata['total_documents']}")
            print(f"  Chunks: {metadata['total_chunks']}")
            print(f"  Sider: {metadata['total_pages_analyzed']}")
            
            print(f"\nTrin 2 - Vector queries:")
            print(f"  Unikke chunks hentet: {overview_data['total_unique_chunks']}")
            print(f"  Gennemsnitlig relevans: {np.mean([result['avg_similarity'] for result in overview_data['query_results'].values()]):.2f}")
            
            print(f"\nTrin 3 - LLM oversigt:")
            print(f"  Generet oversigt: {len(project_overview)} tegn")
            print(f"  Første linjer:")
            for line in project_overview.split('\n')[:3]:
                if line.strip():
                    print(f"    {line[:80]}...")
            
            print(f"\nTrin 4 - Semantisk analyse:")
            print(f"  Antal klynger: {semantic_analysis['n_clusters']}")
            for summary in semantic_analysis['cluster_summaries'][:3]:
                print(f"    {summary['cluster_name']}: {summary['chunk_count']} chunks")
            
            print(f"\nResultater gemt i: {output_dir}")
            
            return results
            
        except Exception as e:
            print(f"❌ Fejl under generering: {str(e)}")
            raise


async def main():
    """Command line interface for wiki generation."""
    parser = argparse.ArgumentParser(description="Generer automatisk wiki fra indexing run")
    parser.add_argument("--index-run-id", required=True, help="UUID på indexing run")
    parser.add_argument("--language", default="danish", choices=["danish", "english"], help="Output sprog")
    parser.add_argument("--model", default="google/gemini-2.5-flash", help="OpenRouter model at bruge")
    
    args = parser.parse_args()
    
    try:
        generator = MarkdownWikiGenerator(language=args.language, model=args.model)
        results = await generator.generate_first_four_steps(args.index_run_id)
        print(f"\n✅ Første fire trin gennemført succesfuldt!")
        
    except Exception as e:
        print(f"❌ Fejl: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())