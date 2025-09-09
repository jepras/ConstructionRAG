"""
Comprehensive tests for wiki generation pipeline.

This test suite validates the current wiki generation functionality to serve as 
regression tests during migration from sync HTTP requests to async LangChain.

Tests cover:
- End-to-end wiki generation pipeline
- Individual step validation with real/mock data strategies
- Error handling and timeout scenarios
- Output format validation
- Integration with existing database and storage
"""

import asyncio
import json
import re
import uuid
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.config.database import get_supabase_admin_client
from src.models import StepResult, WikiGenerationStatus
from src.pipeline.wiki_generation.models import (
    MarkdownGenerationOutput,
    MetadataCollectionOutput,
    OverviewGenerationOutput,
    PageContentRetrievalOutput,
    SemanticClusteringOutput,
    StructureGenerationOutput,
)
from src.pipeline.wiki_generation.orchestrator import WikiGenerationOrchestrator
from src.pipeline.wiki_generation.steps import (
    MarkdownGenerationStep,
    MetadataCollectionStep,
    OverviewGenerationStep,
    PageContentRetrievalStep,
    SemanticClusteringStep,
    StructureGenerationStep,
)


class TestWikiGenerationPipelineIntegration:
    """Integration tests for complete wiki generation pipeline."""

    @pytest.fixture
    def mock_config(self):
        """Provide test configuration."""
        return {
            "language": "danish",
            "similarity_threshold": 0.15,
            "max_chunks_per_query": 10,
            "overview_query_count": 12,
            "max_chunks_in_prompt": 10,
            "content_preview_length": 600,
            "api_timeout_seconds": 30.0,
            "temperature": 0.3,
            "structure_max_tokens": 6000,
            "page_max_tokens": 8000,
            "semantic_clusters": {"min_clusters": 4, "max_clusters": 10}
        }

    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for testing."""
        return {
            "indexing_run_id": "test-run-123",
            "total_documents": 2,
            "total_chunks": 10,
            "total_pages_analyzed": 20,
            "documents": [
                {
                    "id": "doc-1",
                    "filename": "contract.pdf",
                    "file_size": 2048000,
                    "page_count": 10
                },
                {
                    "id": "doc-2",
                    "filename": "specifications.pdf",
                    "file_size": 1024000,
                    "page_count": 8
                }
            ],
            "chunks": [
                {
                    "id": "chunk-1",
                    "document_id": "doc-1",
                    "content": "Project name is Downtown Tower construction project",
                    "metadata": {"page_number": 1}
                },
                {
                    "id": "chunk-2",
                    "document_id": "doc-1",
                    "content": "Building type is residential high-rise with 25 floors",
                    "metadata": {"page_number": 2}
                }
            ],
            "chunks_with_embeddings": [
                {
                    "id": "chunk-1",
                    "document_id": "doc-1",
                    "content": "Project name is Downtown Tower construction project",
                    "metadata": {"page_number": 1},
                    "embedding_1024": str([0.1] * 1024)  # Mock embedding
                },
                {
                    "id": "chunk-2",
                    "document_id": "doc-1",
                    "content": "Building type is residential high-rise with 25 floors",
                    "metadata": {"page_number": 2},
                    "embedding_1024": str([0.2] * 1024)  # Mock embedding
                }
            ],
            "section_headers_distribution": {
                "Project Overview": 5,
                "Technical Specifications": 8,
                "Safety Requirements": 3
            },
            "images_processed": 2,
            "tables_processed": 1,
            "document_filenames": ["contract.pdf", "specifications.pdf"],
            "document_ids": ["doc-1", "doc-2"]
        }

    @pytest.mark.asyncio
    async def test_wiki_pipeline_end_to_end_with_mocked_apis(self, mock_config, sample_metadata):
        """
        Test complete wiki generation pipeline end-to-end with mocked external APIs.
        
        This test validates the complete pipeline flow while mocking external dependencies.
        """
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")
        print("Reason: Testing pipeline flow without external API calls or real database operations")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.orchestrator")
        print("Test-Specific Overrides: OpenRouter API calls, database operations, VoyageAI embeddings")
        print("============================\n")

        # Mock database client
        mock_db = Mock()
        mock_table = Mock()
        mock_db.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.not_.return_value = mock_table
        mock_table.is_.return_value = mock_table
        mock_table.execute.return_value = SimpleNamespace(data=[
            {
                "id": "chunk-1",
                "document_id": "doc-1",
                "content": "Project name is Downtown Tower construction",
                "metadata": {"page_number": 1},
                "embedding_1024": str([0.1] * 1024)
            }
        ])

        # Mock successful API responses
        mock_overview_response = "Downtown Tower er et 25-etagers boligbyggeri i centrum"
        mock_structure_response = {
            "title": "Downtown Tower Wiki",
            "description": "Comprehensive project documentation",
            "pages": [
                {
                    "id": "page-overview",
                    "title": "Projektoversigt",
                    "description": "Projektets overordnede information",
                    "queries": ["projekt navn", "byggetype", "placering"],
                    "relevance_score": 10
                },
                {
                    "id": "page-technical",
                    "title": "Tekniske Specifikationer",
                    "description": "Tekniske krav og specifikationer",
                    "queries": ["teknik", "specifikationer", "krav"],
                    "relevance_score": 8
                }
            ]
        }
        mock_clustering_data = {
            "clusters": {
                0: [{"id": "chunk-1", "content": "test content"}],
                1: [{"id": "chunk-2", "content": "other content"}]
            },
            "cluster_summaries": [
                {"cluster_id": 0, "cluster_name": "Projekt Information", "chunk_count": 5},
                {"cluster_id": 1, "cluster_name": "Tekniske Detaljer", "chunk_count": 3}
            ],
            "n_clusters": 2
        }

        # Create orchestrator with mocked database
        orchestrator = WikiGenerationOrchestrator(config=mock_config, db_client=mock_db)

        # Mock all external dependencies
        with patch.multiple(
            'src.pipeline.wiki_generation.steps.overview_generation.OverviewGenerationStep',
            _call_openrouter_api=AsyncMock(return_value=mock_overview_response),
            _generate_query_embedding=AsyncMock(return_value=[0.1] * 1024),
            _vector_similarity_search=AsyncMock(return_value=[
                ({"id": "chunk-1", "content": "test content", "document_id": "doc-1", "metadata": {"page_number": 1}}, 0.8)
            ])
        ), patch.multiple(
            'src.pipeline.wiki_generation.steps.structure_generation.StructureGenerationStep',
            _call_openrouter_api=AsyncMock(return_value=json.dumps(mock_structure_response))
        ), patch.multiple(
            'src.pipeline.wiki_generation.steps.semantic_clustering.SemanticClusteringStep',
            _perform_semantic_clustering=AsyncMock(return_value=mock_clustering_data),
            _call_openrouter_api=AsyncMock(return_value="Klynge 0: Projekt Information\nKlynge 1: Tekniske Detaljer")
        ), patch.multiple(
            'src.pipeline.wiki_generation.steps.markdown_generation.MarkdownGenerationStep',
            _call_openrouter_api=AsyncMock(return_value="# Projektoversigt\n\nDetailed project content...")
        ), patch.multiple(
            'src.pipeline.wiki_generation.orchestrator.WikiGenerationOrchestrator',
            _create_wiki_run=AsyncMock(return_value=SimpleNamespace(id="wiki-run-123")),
            _update_wiki_run_status=AsyncMock(),
            _get_wiki_run=AsyncMock(return_value=SimpleNamespace(id="wiki-run-123", status="completed")),
            _save_wiki_to_storage=AsyncMock()
        ):
            
            # Execute pipeline
            result = await orchestrator.run_pipeline(
                index_run_id="test-run-123",
                user_id=uuid.uuid4(),
                project_id=uuid.uuid4()
            )

            # Validate results
            assert result is not None
            assert hasattr(result, 'id')
            assert result.id == "wiki-run-123"

    @pytest.mark.asyncio 
    async def test_orchestrator_step_initialization(self, mock_config):
        """Test that orchestrator initializes all required steps correctly."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")
        print("Reason: Testing component initialization without external dependencies")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.orchestrator.WikiGenerationOrchestrator")
        print("Test-Specific Overrides: Database client injection")
        print("============================\n")

        mock_db = Mock()
        orchestrator = WikiGenerationOrchestrator(config=mock_config, db_client=mock_db)

        # Verify all steps are initialized
        expected_steps = [
            "metadata_collection",
            "overview_generation", 
            "semantic_clustering",
            "structure_generation",
            "page_content_retrieval",
            "markdown_generation"
        ]

        for step_name in expected_steps:
            assert step_name in orchestrator.steps
            assert orchestrator.steps[step_name] is not None

        # Verify step types
        assert isinstance(orchestrator.steps["metadata_collection"], MetadataCollectionStep)
        assert isinstance(orchestrator.steps["overview_generation"], OverviewGenerationStep)
        assert isinstance(orchestrator.steps["semantic_clustering"], SemanticClusteringStep)
        assert isinstance(orchestrator.steps["structure_generation"], StructureGenerationStep)
        assert isinstance(orchestrator.steps["page_content_retrieval"], PageContentRetrievalStep)
        assert isinstance(orchestrator.steps["markdown_generation"], MarkdownGenerationStep)


class TestOverviewGenerationStep:
    """Unit tests for overview generation step."""

    @pytest.fixture
    def mock_config(self):
        return {
            "language": "danish",
            "similarity_threshold": 0.15,
            "max_chunks_per_query": 10,
            "overview_query_count": 12,
            "max_chunks_in_prompt": 10,
            "content_preview_length": 600,
            "api_timeout_seconds": 30.0,
            "temperature": 0.3
        }

    @pytest.fixture
    def sample_input_data(self):
        return {
            "metadata": {
                "total_documents": 2,
                "chunks_with_embeddings": [
                    {
                        "id": "chunk-1",
                        "content": "Project Downtown Tower construction",
                        "document_id": "doc-1",
                        "embedding_1024": str([0.1] * 1024)
                    }
                ],
                "documents": [{"id": "doc-1", "filename": "contract.pdf"}]
            }
        }

    @pytest.mark.asyncio
    async def test_overview_generation_with_mocked_api(self, mock_config, sample_input_data):
        """Test overview generation with mocked OpenRouter API."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")  
        print("Reason: Testing business logic without external API dependency")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.overview_generation")
        print("Test-Specific Overrides: OpenRouter API calls, VoyageAI embeddings, database queries")
        print("============================\n")

        mock_db = Mock()
        
        # Create step with mocked dependencies
        step = OverviewGenerationStep(config=mock_config, db_client=mock_db)
        
        # Mock the API call
        expected_overview = "Downtown Tower er et stort byggeprojekt i centrum af byen"
        
        with patch.object(step, '_call_openrouter_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = expected_overview
            
            with patch.object(step, '_perform_vector_search', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = {
                    "retrieved_chunks": [
                        {
                            "id": "chunk-1",
                            "content": "test content",
                            "similarity_score": 0.8,
                            "retrieved_by_query": "test query"
                        }
                    ],
                    "query_results": {},
                    "total_unique_chunks": 1
                }
                
                # Execute step
                result = await step.execute(sample_input_data)
                
                # Validate result structure
                assert isinstance(result, StepResult)
                assert result.step == "overview_generation"
                assert result.status == "completed"
                assert result.data["project_overview"] == expected_overview
                assert "overview_queries" in result.data
                assert "overview_data" in result.data
                
                # Validate API was called with correct parameters
                mock_api.assert_called_once()
                args, kwargs = mock_api.call_args
                assert len(args) == 1  # prompt argument
                assert "max_tokens" in kwargs or len(args) == 2

    @pytest.mark.asyncio
    async def test_overview_generation_query_generation(self, mock_config, sample_input_data):
        """Test that overview queries are generated correctly for Danish language."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: REAL")
        print("Reason: Testing actual query generation logic and Danish language support")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES") 
        print("Import Source: src.pipeline.wiki_generation.steps.overview_generation")
        print("Test-Specific Overrides: None - testing real query generation logic")
        print("============================\n")

        mock_db = Mock()
        step = OverviewGenerationStep(config=mock_config, db_client=mock_db)
        
        # Test query generation
        queries = step._generate_overview_queries(sample_input_data["metadata"])
        
        # Validate Danish queries are generated
        assert len(queries) >= 10  # Should have multiple queries
        assert any("projekt" in query.lower() for query in queries)  # Danish "project"
        assert any("byggeri" in query.lower() for query in queries)  # Danish "construction"
        assert any("fagentreprenør" in query.lower() for query in queries)  # Danish "trade contractor"

    @pytest.mark.asyncio
    async def test_overview_generation_api_timeout_error(self, mock_config, sample_input_data):
        """Test error handling for API timeout scenarios."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")
        print("Reason: Testing error handling behavior without actual timeouts")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.overview_generation")
        print("Test-Specific Overrides: OpenRouter API to simulate timeout")
        print("============================\n")

        mock_db = Mock()
        step = OverviewGenerationStep(config=mock_config, db_client=mock_db)
        
        with patch.object(step, '_call_openrouter_api', new_callable=AsyncMock) as mock_api:
            # Simulate timeout error
            import requests
            mock_api.side_effect = requests.exceptions.Timeout("Request timed out")
            
            with patch.object(step, '_perform_vector_search', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = {"retrieved_chunks": [], "query_results": {}, "total_unique_chunks": 0}
                
                # Expect timeout to propagate as AppError
                with pytest.raises(Exception) as exc_info:
                    await step.execute(sample_input_data)
                    
                assert "timeout" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_overview_prerequisites_validation(self, mock_config):
        """Test prerequisite validation for overview generation."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")
        print("Reason: Testing validation logic with controlled input scenarios")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.overview_generation")
        print("Test-Specific Overrides: None - testing real validation logic")
        print("============================\n")

        mock_db = Mock()
        step = OverviewGenerationStep(config=mock_config, db_client=mock_db)
        
        # Test valid input
        valid_input = {
            "metadata": {
                "total_documents": 1,
                "chunks_with_embeddings": [{"id": "chunk-1"}]
            }
        }
        assert await step.validate_prerequisites_async(valid_input) is True
        
        # Test missing metadata
        invalid_input_1 = {}
        assert await step.validate_prerequisites_async(invalid_input_1) is False
        
        # Test missing chunks_with_embeddings
        invalid_input_2 = {
            "metadata": {
                "total_documents": 1
            }
        }
        assert await step.validate_prerequisites_async(invalid_input_2) is False


class TestStructureGenerationStep:
    """Unit tests for structure generation step."""

    @pytest.fixture
    def mock_config(self):
        return {
            "language": "danish",
            "structure_max_tokens": 6000,
            "temperature": 0.3,
            "api_timeout_seconds": 30.0
        }

    @pytest.fixture
    def sample_input_data(self):
        return {
            "metadata": {
                "total_documents": 2,
                "documents": [{"filename": "contract.pdf", "page_count": 10}],
                "section_headers_distribution": {"Overview": 5, "Technical": 3}
            },
            "project_overview": "Downtown Tower construction project overview",
            "semantic_analysis": {
                "cluster_summaries": [
                    {"cluster_id": 0, "cluster_name": "Project Info", "chunk_count": 5}
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_structure_generation_with_valid_json(self, mock_config, sample_input_data):
        """Test structure generation with valid JSON response."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")
        print("Reason: Testing JSON parsing and structure validation with controlled responses")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.structure_generation")
        print("Test-Specific Overrides: OpenRouter API calls")
        print("============================\n")

        mock_db = Mock()
        step = StructureGenerationStep(config=mock_config, db_client=mock_db)
        
        mock_structure = {
            "title": "Downtown Tower Wiki",
            "description": "Project documentation",
            "pages": [
                {
                    "id": "page-1", 
                    "title": "Projektoversigt",
                    "description": "Project overview",
                    "queries": ["projekt", "oversigt", "navn", "type"],
                    "relevance_score": 10
                },
                {
                    "id": "page-2",
                    "title": "Tekniske Specifikationer", 
                    "description": "Technical requirements",
                    "queries": ["teknik", "spec", "krav", "system"],
                    "relevance_score": 8
                }
            ]
        }
        
        with patch.object(step, '_call_openrouter_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = json.dumps(mock_structure)
            
            result = await step.execute(sample_input_data)
            
            # Validate result structure
            assert isinstance(result, StepResult)
            assert result.step == "structure_generation"
            assert result.status == "completed"
            assert "title" in result.data
            assert "pages" in result.data
            assert len(result.data["pages"]) == 2
            
            # Validate Danish overview page exists
            page_titles = [page["title"] for page in result.data["pages"]]
            assert any("oversigt" in title.lower() for title in page_titles)

    @pytest.mark.asyncio
    async def test_structure_generation_json_parsing_with_markdown_blocks(self, mock_config, sample_input_data):
        """Test JSON parsing when LLM returns JSON wrapped in markdown code blocks."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")
        print("Reason: Testing edge case JSON parsing scenarios that occur in production")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.structure_generation")
        print("Test-Specific Overrides: OpenRouter API responses")
        print("============================\n")

        mock_db = Mock()
        step = StructureGenerationStep(config=mock_config, db_client=mock_db)
        
        mock_structure = {
            "title": "Test Wiki",
            "pages": [{"id": "page-1", "title": "Test Page", "queries": ["test"]}]
        }
        
        # Test with markdown code blocks
        wrapped_response = f"```json\n{json.dumps(mock_structure)}\n```"
        
        with patch.object(step, '_call_openrouter_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = wrapped_response
            
            result = await step.execute(sample_input_data)
            
            # Should successfully parse despite markdown wrapping
            assert result.status == "completed"
            assert result.data["title"] == "Test Wiki"

    @pytest.mark.asyncio
    async def test_structure_validation_adds_missing_overview_page(self, mock_config, sample_input_data):
        """Test that structure validation adds overview page if missing."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: REAL")
        print("Reason: Testing actual validation logic that ensures required pages exist")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.structure_generation")
        print("Test-Specific Overrides: None - testing real validation logic")
        print("============================\n")

        mock_db = Mock()
        step = StructureGenerationStep(config=mock_config, db_client=mock_db)
        
        # Structure without overview page
        structure_without_overview = {
            "title": "Test Wiki",
            "pages": [
                {"id": "page-1", "title": "Technical Details", "queries": ["tech"]}
            ]
        }
        
        validated = step._validate_wiki_structure(structure_without_overview)
        
        # Should have added overview page
        assert len(validated["pages"]) == 2
        page_titles = [page["title"].lower() for page in validated["pages"]]
        assert any("oversigt" in title or "overview" in title for title in page_titles)

    @pytest.mark.asyncio  
    async def test_structure_generation_invalid_json_error(self, mock_config, sample_input_data):
        """Test error handling for invalid JSON responses."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")
        print("Reason: Testing error handling for malformed API responses")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES") 
        print("Import Source: src.pipeline.wiki_generation.steps.structure_generation")
        print("Test-Specific Overrides: OpenRouter API to return invalid JSON")
        print("============================\n")

        mock_db = Mock()
        step = StructureGenerationStep(config=mock_config, db_client=mock_db)
        
        with patch.object(step, '_call_openrouter_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = "Invalid JSON response that cannot be parsed"
            
            with pytest.raises(Exception) as exc_info:
                await step.execute(sample_input_data)
                
            assert "json" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()


class TestSemanticClusteringStep:
    """Unit tests for semantic clustering step."""

    @pytest.fixture
    def mock_config(self):
        return {
            "language": "danish",
            "api_timeout_seconds": 30.0,
            "temperature": 0.3,
            "semantic_clusters": {"min_clusters": 4, "max_clusters": 10}
        }

    @pytest.fixture  
    def sample_input_data(self):
        return {
            "metadata": {
                "chunks_with_embeddings": [
                    {
                        "id": "chunk-1",
                        "content": "Project overview and main objectives",
                        "embedding_1024": str([0.1] * 1024)
                    },
                    {
                        "id": "chunk-2", 
                        "content": "Technical specifications and requirements",
                        "embedding_1024": str([0.2] * 1024)
                    },
                    {
                        "id": "chunk-3",
                        "content": "Safety protocols and regulations",
                        "embedding_1024": str([0.3] * 1024)
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_semantic_clustering_with_valid_embeddings(self, mock_config, sample_input_data):
        """Test semantic clustering with valid embedding data."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")
        print("Reason: Testing clustering logic with controlled embedding data to ensure deterministic results")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.semantic_clustering")
        print("Test-Specific Overrides: LLM cluster naming API calls")
        print("============================\n")

        mock_db = Mock()
        step = SemanticClusteringStep(config=mock_config, db_client=mock_db)
        
        # Mock cluster name generation
        mock_cluster_names = "Klynge 0: Projekt Information\nKlynge 1: Tekniske Detaljer"
        
        with patch.object(step, '_call_openrouter_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = mock_cluster_names
            
            result = await step.execute(sample_input_data)
            
            # Validate result structure
            assert isinstance(result, StepResult)
            assert result.step == "semantic_clustering"
            assert result.status == "completed"
            assert "clusters" in result.data
            assert "cluster_summaries" in result.data
            assert "n_clusters" in result.data
            assert result.data["n_clusters"] > 0
            
            # Validate cluster summaries have names
            for summary in result.data["cluster_summaries"]:
                assert "cluster_name" in summary
                assert "chunk_count" in summary
                assert summary["cluster_name"] != f"Temaområde {summary['cluster_id']}"  # Not fallback

    @pytest.mark.asyncio
    async def test_semantic_clustering_with_no_embeddings(self, mock_config):
        """Test clustering behavior with no valid embeddings."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")
        print("Reason: Testing edge case behavior with empty or invalid embedding data")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.semantic_clustering")
        print("Test-Specific Overrides: None - testing real error handling")
        print("============================\n")

        mock_db = Mock()
        step = SemanticClusteringStep(config=mock_config, db_client=mock_db)
        
        input_data_no_embeddings = {
            "metadata": {
                "chunks_with_embeddings": []
            }
        }
        
        result = await step.execute(input_data_no_embeddings)
        
        # Should handle gracefully with empty results
        assert result.status == "completed"
        assert result.data["n_clusters"] == 0
        assert len(result.data["clusters"]) == 0
        assert len(result.data["cluster_summaries"]) == 0

    @pytest.mark.asyncio
    async def test_semantic_clustering_llm_naming_fallback(self, mock_config, sample_input_data):
        """Test fallback behavior when LLM cluster naming fails."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")
        print("Reason: Testing error resilience and fallback mechanisms")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.semantic_clustering")
        print("Test-Specific Overrides: LLM API to simulate failures")
        print("============================\n")

        mock_db = Mock()
        step = SemanticClusteringStep(config=mock_config, db_client=mock_db)
        
        with patch.object(step, '_call_openrouter_api', new_callable=AsyncMock) as mock_api:
            # Simulate API failure
            mock_api.side_effect = Exception("API call failed")
            
            result = await step.execute(sample_input_data)
            
            # Should complete with fallback names
            assert result.status == "completed"
            assert result.data["n_clusters"] > 0
            
            # All clusters should have fallback names
            for summary in result.data["cluster_summaries"]:
                cluster_name = summary["cluster_name"]
                assert any(fallback in cluster_name for fallback in [
                    "Tekniske Specifikationer", "Projektdokumentation", 
                    "Bygningskomponenter", "Temaområde"
                ])

    @pytest.mark.asyncio
    async def test_clustering_determines_appropriate_cluster_count(self, mock_config):
        """Test that clustering determines appropriate number of clusters based on data size."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: REAL")
        print("Reason: Testing actual cluster count determination logic")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.semantic_clustering")
        print("Test-Specific Overrides: None - testing real clustering logic")
        print("============================\n")

        mock_db = Mock()
        step = SemanticClusteringStep(config=mock_config, db_client=mock_db)
        
        # Test with small dataset (should use min_clusters)
        small_data = {
            "metadata": {
                "chunks_with_embeddings": [
                    {"id": f"chunk-{i}", "content": f"content {i}", "embedding_1024": str([i*0.1] * 1024)}
                    for i in range(10)  # 10 chunks
                ]
            }
        }
        
        with patch.object(step, '_call_openrouter_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = "Klynge 0: Test\nKlynge 1: Test2\nKlynge 2: Test3\nKlynge 3: Test4"
            
            result = await step.execute(small_data)
            
            # With 10 chunks, should use min_clusters (4) since 10//20 = 0 < min_clusters  
            assert result.data["n_clusters"] == 4


class TestMarkdownGenerationStep:
    """Unit tests for markdown generation step."""

    @pytest.fixture
    def mock_config(self):
        return {
            "language": "danish",
            "page_max_tokens": 8000,
            "temperature": 0.3,
            "api_timeout_seconds": 30.0
        }

    @pytest.fixture
    def sample_input_data(self):
        return {
            "metadata": {
                "total_documents": 2,
                "documents": [{"filename": "contract.pdf"}]
            },
            "wiki_structure": {
                "title": "Test Wiki",
                "pages": [
                    {
                        "id": "page-1",
                        "title": "Projektoversigt",
                        "description": "Project overview page"
                    },
                    {
                        "id": "page-2", 
                        "title": "Tekniske Specifikationer",
                        "description": "Technical specifications"
                    }
                ]
            },
            "page_contents": {
                "page-1": {
                    "retrieved_chunks": [
                        {
                            "id": "chunk-1",
                            "content": "Downtown Tower construction project details",
                            "document_id": "doc-1",
                            "metadata": {"page_number": 5},
                            "similarity_score": 0.95
                        }
                    ],
                    "source_documents": {
                        "doc-1": {"filename": "contract.pdf", "chunk_count": 10}
                    }
                },
                "page-2": {
                    "retrieved_chunks": [
                        {
                            "id": "chunk-2",
                            "content": "Technical requirements and specifications",
                            "document_id": "doc-1", 
                            "metadata": {"page_number": 12},
                            "similarity_score": 0.88
                        }
                    ],
                    "source_documents": {
                        "doc-1": {"filename": "contract.pdf", "chunk_count": 10}
                    }
                }
            }
        }

    @pytest.mark.asyncio
    async def test_markdown_generation_with_proper_citations(self, mock_config, sample_input_data):
        """Test markdown generation includes proper source citations."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK") 
        print("Reason: Testing citation format and content generation without external API costs")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.markdown_generation")
        print("Test-Specific Overrides: OpenRouter API calls")
        print("============================\n")

        mock_db = Mock()
        step = MarkdownGenerationStep(config=mock_config, db_client=mock_db)
        
        # Mock markdown responses with citations
        mock_responses = [
            "# Projektoversigt\n\nDowntown Tower er et stort byggeprojekt[contract.pdf, 5].",
            "# Tekniske Specifikationer\n\nKravene omfatter følgende[contract.pdf, 12]:"
        ]
        
        call_count = 0
        async def mock_api_call(prompt, **kwargs):
            nonlocal call_count
            response = mock_responses[call_count]
            call_count += 1
            return response
        
        with patch.object(step, '_call_openrouter_api', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = mock_api_call
            
            result = await step.execute(sample_input_data)
            
            # Validate result structure
            assert isinstance(result, StepResult)
            assert result.step == "markdown_generation"
            assert result.status == "completed"
            assert len(result.data) == 2  # Two pages generated
            
            # Validate each page has markdown content
            for page_id, page_data in result.data.items():
                assert "markdown_content" in page_data
                assert "title" in page_data
                assert "content_length" in page_data
                assert len(page_data["markdown_content"]) > 0
                
                # Check for proper citation format [filename, page]
                content = page_data["markdown_content"]
                assert "[contract.pdf," in content  # Should have citations

    @pytest.mark.asyncio
    async def test_markdown_generation_prompt_structure(self, mock_config, sample_input_data):
        """Test that markdown generation prompt includes required elements."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: REAL")
        print("Reason: Testing actual prompt generation logic to ensure quality instructions")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.markdown_generation")
        print("Test-Specific Overrides: None - testing real prompt generation")
        print("============================\n")

        mock_db = Mock()
        step = MarkdownGenerationStep(config=mock_config, db_client=mock_db)
        
        page = sample_input_data["wiki_structure"]["pages"][0]
        page_content = sample_input_data["page_contents"]["page-1"]
        metadata = sample_input_data["metadata"]
        
        # Test prompt creation
        prompt = step._create_markdown_prompt(page, page_content, metadata)
        
        # Validate prompt contains required elements
        assert "Projektoversigt" in prompt  # Page title
        assert "contract.pdf" in prompt  # Source document
        assert "Downtown Tower construction" in prompt  # Content excerpt
        assert "Mermaid" in prompt  # Diagram instructions
        assert "citation" in prompt.lower() or "source" in prompt.lower()  # Citation instructions
        assert "danish" in prompt.lower()  # Language instructions

    @pytest.mark.asyncio
    async def test_markdown_generation_handles_missing_content(self, mock_config):
        """Test markdown generation handles pages with no retrieved content."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")
        print("Reason: Testing edge case handling for pages with insufficient content")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.markdown_generation") 
        print("Test-Specific Overrides: OpenRouter API calls")
        print("============================\n")

        mock_db = Mock()
        step = MarkdownGenerationStep(config=mock_config, db_client=mock_db)
        
        input_with_empty_content = {
            "metadata": {"total_documents": 1, "documents": []},
            "wiki_structure": {
                "pages": [{"id": "page-1", "title": "Empty Page", "description": ""}]
            },
            "page_contents": {
                "page-1": {"retrieved_chunks": [], "source_documents": {}}
            }
        }
        
        with patch.object(step, '_call_openrouter_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = "# Empty Page\n\nNo content available for this page."
            
            result = await step.execute(input_with_empty_content)
            
            # Should complete successfully even with empty content
            assert result.status == "completed"
            assert len(result.data) == 1
            assert result.data["page-1"]["markdown_content"].startswith("# Empty Page")

    @pytest.mark.asyncio
    async def test_markdown_generation_prerequisites_validation(self, mock_config):
        """Test prerequisite validation for markdown generation."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")
        print("Reason: Testing validation logic with controlled input scenarios")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.steps.markdown_generation")
        print("Test-Specific Overrides: None - testing real validation logic")
        print("============================\n")

        mock_db = Mock()
        step = MarkdownGenerationStep(config=mock_config, db_client=mock_db)
        
        # Test valid input
        valid_input = {
            "metadata": {},
            "wiki_structure": {},
            "page_contents": {}
        }
        assert await step.validate_prerequisites_async(valid_input) is True
        
        # Test missing required fields
        assert await step.validate_prerequisites_async({}) is False
        assert await step.validate_prerequisites_async({"metadata": {}}) is False
        assert await step.validate_prerequisites_async({"metadata": {}, "wiki_structure": {}}) is False


class TestWikiGenerationErrorHandling:
    """Tests for error handling and edge cases across the wiki generation pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_handles_step_failures_gracefully(self):
        """Test that pipeline handles individual step failures appropriately."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: MOCK")
        print("Reason: Testing error propagation and handling without external dependencies")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.orchestrator")
        print("Test-Specific Overrides: Step execution to simulate failures")
        print("============================\n")

        mock_config = {"language": "danish"}
        mock_db = Mock()
        
        orchestrator = WikiGenerationOrchestrator(config=mock_config, db_client=mock_db)
        
        # Mock step to raise exception
        async def failing_step_execute(input_data):
            raise Exception("Simulated step failure")
        
        # Replace one step with failing version
        orchestrator.steps["overview_generation"].execute = failing_step_execute
        
        # Mock other dependencies to focus on error handling
        with patch.multiple(
            'src.pipeline.wiki_generation.orchestrator.WikiGenerationOrchestrator',
            _create_wiki_run=AsyncMock(return_value=SimpleNamespace(id="wiki-run-123")),
            _update_wiki_run_status=AsyncMock(),
            _get_wiki_run=AsyncMock(return_value=SimpleNamespace(id="wiki-run-123", status="failed")),
            _save_wiki_to_storage=AsyncMock()
        ):
            # Pipeline should handle step failure gracefully
            with pytest.raises(Exception) as exc_info:
                await orchestrator.run_pipeline(index_run_id="test-run-123")
            
            assert "simulated step failure" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_output_format_validation(self):
        """Test that all step outputs match expected format schemas."""
        print("\n=== Test Data Strategy ===")
        print("Data Type: REAL")
        print("Reason: Validating actual output schemas and data model compliance")
        print("========================\n")

        print("\n=== Method Usage Analysis ===")
        print("Using Production Methods: YES")
        print("Import Source: src.pipeline.wiki_generation.models")
        print("Test-Specific Overrides: None - testing real output model validation")
        print("============================\n")

        # Test MetadataCollectionOutput
        metadata_data = {
            "indexing_run_id": "test-123",
            "total_documents": 2,
            "total_chunks": 10,
            "documents": [],
            "chunks": [],
            "chunks_with_embeddings": []
        }
        metadata_output = MetadataCollectionOutput(**metadata_data)
        assert metadata_output.indexing_run_id == "test-123"
        assert metadata_output.total_documents == 2

        # Test OverviewGenerationOutput
        overview_data = {"project_overview": "Test project overview"}
        overview_output = OverviewGenerationOutput(**overview_data)
        assert overview_output.project_overview == "Test project overview"

        # Test SemanticClusteringOutput
        clustering_data = {
            "clusters": {0: [], 1: []},
            "cluster_summaries": [{"cluster_id": 0, "cluster_name": "Test"}],
            "n_clusters": 2
        }
        clustering_output = SemanticClusteringOutput(**clustering_data)
        assert clustering_output.n_clusters == 2

        # Test StructureGenerationOutput
        structure_data = {
            "wiki_structure": {
                "title": "Test Wiki",
                "pages": [{"id": "page-1", "title": "Test Page"}]
            }
        }
        structure_output = StructureGenerationOutput(**structure_data)
        assert structure_output.wiki_structure["title"] == "Test Wiki"

        # Test PageContentRetrievalOutput
        page_content_data = {
            "page_contents": {
                "page-1": {"retrieved_chunks": [], "source_documents": {}}
            }
        }
        page_output = PageContentRetrievalOutput(**page_content_data)
        assert "page-1" in page_output.page_contents

        # Test MarkdownGenerationOutput
        markdown_data = {
            "generated_pages": {
                "page-1": {
                    "title": "Test Page",
                    "markdown_content": "# Test\nContent here",
                    "content_length": 100
                }
            }
        }
        markdown_output = MarkdownGenerationOutput(**markdown_data)
        assert "page-1" in markdown_output.generated_pages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])