"""Semantic clustering step for wiki generation pipeline."""

import ast
import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

try:
    import numpy as np
    from sklearn.cluster import KMeans
except ImportError:
    print("Warning: numpy and sklearn not available, clustering will fail")
    np = None
    KMeans = None

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from src.config.database import get_supabase_admin_client
from src.config.settings import get_settings
from src.shared.langchain_helpers import create_llm_client, call_llm_with_tracing
from src.models import StepResult
from src.services.config_service import ConfigService
from src.services.storage_service import StorageService
from src.shared.errors import ErrorCode
from src.utils.exceptions import AppError

from ...shared.base_step import PipelineStep

logger = logging.getLogger(__name__)


class SemanticClusteringStep(PipelineStep):
    """Step 4: Semantic clustering and LLM-based naming to identify 4-10 main topics."""

    def __init__(
        self,
        config: dict[str, Any],
        storage_service: StorageService | None = None,
        progress_tracker=None,
        db_client=None,
    ):
        super().__init__(config, progress_tracker)
        self.storage_service = storage_service or StorageService()
        # Allow DI of db client; default to admin for pipeline safety
        self.supabase = db_client or get_supabase_admin_client()

        # Use config passed from orchestrator (no fresh ConfigService calls)
        gen_cfg = config.get("generation", {})
        self.model = gen_cfg.get("model", "google/gemini-2.5-flash-lite")
        self.language = config.get("defaults", {}).get("language", "english")
        self.api_timeout = config.get("api_timeout_seconds", 30.0)

        # Semantic clustering configuration matching original
        self.semantic_clusters_config = config.get("semantic_clusters", {"min_clusters": 4, "max_clusters": 10})
        
        # Initialize LangChain OpenAI client using shared helper
        try:
            self.llm_client = create_llm_client(
                model_name=self.model,
                max_tokens=500,
                temperature=0.3
            )
        except Exception as e:
            logger.error(f"Failed to initialize LangChain ChatOpenAI client: {e}")
            raise


    async def execute(self, input_data: dict[str, Any]) -> StepResult:
        """Execute semantic clustering step."""
        start_time = datetime.utcnow()

        try:
            metadata = input_data["metadata"]
            chunks_with_embeddings = metadata["chunks_with_embeddings"]
            logger.info(f"Starting semantic clustering for {len(chunks_with_embeddings)} chunks")

            # Perform semantic clustering
            semantic_analysis = await self._perform_semantic_clustering(chunks_with_embeddings)

            # Create step result
            result = StepResult(
                step="semantic_clustering",
                status="completed",
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                summary_stats={
                    "n_clusters": semantic_analysis.get("n_clusters", 0),
                    "total_chunks": len(chunks_with_embeddings),
                    "cluster_names_generated": len(semantic_analysis.get("cluster_summaries", [])),
                },
                sample_outputs={
                    "cluster_examples": [
                        {
                            "id": summary.get("cluster_id"),
                            "name": summary.get("cluster_name"),
                            "chunk_count": summary.get("chunk_count", 0),
                        }
                        for summary in semantic_analysis.get("cluster_summaries", [])[:3]
                    ]
                },
                data=semantic_analysis,
                started_at=start_time,
                completed_at=datetime.utcnow(),
            )

            logger.info(f"Semantic clustering completed: {semantic_analysis.get('n_clusters', 0)} clusters generated")
            return result

        except Exception as e:
            logger.error(f"Semantic clustering failed: {e}")
            raise AppError(
                "Semantic clustering failed",
                error_code=ErrorCode.EXTERNAL_API_ERROR,
                details={"reason": str(e)},
            ) from e

    async def validate_prerequisites_async(self, input_data: dict[str, Any]) -> bool:
        """Validate that input data meets step requirements."""
        required_fields = ["metadata"]
        if not all(field in input_data for field in required_fields):
            return False

        metadata = input_data["metadata"]
        required_metadata_fields = ["chunks_with_embeddings"]
        return all(field in metadata for field in required_metadata_fields)

    def estimate_duration(self, input_data: dict[str, Any]) -> int:
        """Estimate step duration in seconds."""
        metadata = input_data.get("metadata", {})
        chunks_count = len(metadata.get("chunks_with_embeddings", []))
        # Clustering is compute-intensive: ~5 seconds per 100 chunks + LLM call
        return max(60, (chunks_count // 100) * 5 + 30)

    async def _perform_semantic_clustering(self, chunks_with_embeddings: list[dict]) -> dict[str, Any]:
        """Perform semantic clustering and LLM-based naming - matches original implementation."""
        print("Trin 4: Udfører semantisk clustering og LLM navngivning for emneidentifikation...")

        # Check if required libraries are available
        if np is None or KMeans is None:
            print("⚠️  numpy eller sklearn ikke tilgængelig - kan ikke lave clustering")
            return {"clusters": {}, "cluster_summaries": [], "n_clusters": 0}

        # Filter chunks with embeddings
        valid_chunks = [chunk for chunk in chunks_with_embeddings if chunk.get("embedding_1024") is not None]

        if len(valid_chunks) == 0:
            print("⚠️  Ingen embeddings fundet - kan ikke lave clustering")
            return {"clusters": {}, "cluster_summaries": [], "n_clusters": 0}

        print(f"Fundet {len(valid_chunks)} chunks med embeddings")

        # Parse embeddings - exactly matching original implementation
        embeddings = []
        for chunk in valid_chunks:
            embedding_str = chunk["embedding_1024"]
            try:
                if isinstance(embedding_str, str):
                    # Use ast.literal_eval like original
                    chunk_embedding = ast.literal_eval(embedding_str)

                    # Ensure it's a list of floats
                    if isinstance(chunk_embedding, list):
                        chunk_embedding = [float(x) for x in chunk_embedding]
                        embeddings.append(chunk_embedding)
                    else:
                        print(f"⚠️  Invalid embedding format for chunk {chunk['id']}")
                        continue
                else:
                    embeddings.append(embedding_str)
            except (ValueError, SyntaxError) as e:
                print(f"⚠️  Failed to parse embedding for chunk {chunk['id']}: {e}")
                continue

        if len(embeddings) == 0:
            print("⚠️  No valid embeddings could be parsed")
            return {"clusters": {}, "cluster_summaries": [], "n_clusters": 0}

        embeddings = np.array(embeddings)
        print(f"Parsed {len(embeddings)} valid embeddings")

        # Determine number of clusters - exactly matching original logic
        n_chunks = len(valid_chunks)
        n_clusters = min(
            self.semantic_clusters_config["max_clusters"],
            max(self.semantic_clusters_config["min_clusters"], n_chunks // 20),
        )

        print(f"Klyngedeling i {n_clusters} klynger...")

        # Perform clustering - exactly matching original parameters
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)

        # Group chunks by cluster
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            clusters[label].append(valid_chunks[i])

        # Create initial cluster summaries with sample content (without names yet)
        cluster_summaries = []
        for cluster_id, cluster_chunks in clusters.items():
            # Sample content for summary - exactly matching original
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
        cluster_names = await self._generate_cluster_names_llm(cluster_summaries)

        # Add the generated names to summaries
        for summary in cluster_summaries:
            cluster_id = summary["cluster_id"]
            summary["cluster_name"] = cluster_names.get(cluster_id, f"Temaområde {cluster_id}")

        print("Klynger oprettet:")
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

    async def _generate_cluster_names_llm(self, cluster_summaries: list[dict[str, Any]]) -> dict[int, str]:
        """Generate meaningful cluster names using LLM - exactly matching original implementation."""
        print(f"🤖 Genererer klyngenavne med LLM for {len(cluster_summaries)} klynger...")

        # Prepare cluster samples for LLM - exactly matching original
        cluster_samples = []
        for summary in cluster_summaries:
            cluster_id = summary["cluster_id"]
            sample_content = summary.get("sample_content", [])

            # Combine sample content into a representative text
            combined_sample = " | ".join(sample_content)
            cluster_samples.append(
                {
                    "cluster_id": cluster_id,
                    "sample_text": combined_sample[:800],  # Limit to avoid token overflow
                }
            )

        # Create language-aware prompt following plan guidelines
        samples_text = "\n".join([f"Cluster {item['cluster_id']}: {item['sample_text']}" for item in cluster_samples])
        
        language_names = {
            "english": "English",
            "danish": "Danish",
        }
        output_language = language_names.get(self.language, "English")

        prompt = f"""Based on the following document content from a construction project database, generate short, descriptive names for each cluster.

Names should be:
- Short and precise (2-4 words)
- Descriptive of cluster content
- Professional and technical
- Unique (no repetitions)

Document clusters:
{samples_text}

Generate names in the following format:
Cluster 0: [Name]
Cluster 1: [Name]
...

Output your response in {output_language}. Only respond with the names in the specified format."""

        try:
            start_time = datetime.utcnow()
            llm_response = await call_llm_with_tracing(
                llm_client=self.llm_client,
                prompt=prompt,
                run_name="semantic_clustering_generator",
                metadata={
                    "step": "semantic_clustering",
                    "model": self.model,
                    "max_tokens": 500,
                    "language": self.language,
                    "clusters_count": len(cluster_samples)
                }
            )
            end_time = datetime.utcnow()

            print(f"LLM klyngenavne genereret på {(end_time - start_time).total_seconds():.1f} sekunder")

            # Parse the response to extract cluster names - exactly matching original
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

            # Fallback for missing names - exactly matching original
            for summary in cluster_summaries:
                cluster_id = summary["cluster_id"]
                if cluster_id not in cluster_names:
                    fallback_name = f"Temaområde {cluster_id}"
                    cluster_names[cluster_id] = fallback_name
                    print(f"  Bruger fallback navn for klynge {cluster_id}: {fallback_name}")

            return cluster_names

        except Exception as e:
            print(f"⚠️  LLM klyngenavn generering fejlede: {str(e)}")
            print("⚠️  Falder tilbage til generiske navne...")

            # Fallback to generic names - language-aware as per plan
            generic_names = {
                "danish": [
                    "Tekniske Specifikationer",
                    "Projektdokumentation", 
                    "Bygningskomponenter",
                    "Systeminstallationer",
                    "Udførselsdetaljer",
                    "Drifts- og Vedligehold",
                    "Kvalitetssikring",
                    "Sikkerhedsforhold",
                ],
                "english": [
                    "Technical Specifications",
                    "Project Documentation",
                    "Building Components", 
                    "System Installations",
                    "Implementation Details",
                    "Operations & Maintenance",
                    "Quality Assurance",
                    "Safety Requirements",
                ]
            }
            fallback_names = generic_names.get(self.language, generic_names["english"])

            cluster_names = {}
            for i, summary in enumerate(cluster_summaries):
                cluster_id = summary["cluster_id"]
                if i < len(fallback_names):
                    cluster_names[cluster_id] = fallback_names[i]
                else:
                    # Language-aware overflow naming
                    if self.language == "danish":
                        cluster_names[cluster_id] = f"Temaområde {cluster_id}"
                    else:
                        cluster_names[cluster_id] = f"Topic Area {cluster_id}"

            return cluster_names

