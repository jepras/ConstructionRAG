"""Orchestrator for checklist analysis pipeline."""

import logging
from typing import Optional

from src.models.checklist import AnalysisStatus
from src.services.checklist_service import ChecklistService
from .query_generator import generate_queries_from_checklist
from .retriever import retrieve_chunks_for_query, retrieve_chunks_for_queries_batch, deduplicate_chunks
from .analyzer import analyze_checklist_with_chunks
from .structurer import structure_analysis_output

logger = logging.getLogger(__name__)


class ChecklistAnalysisOrchestrator:
    """Orchestrator for the 4-step checklist analysis pipeline."""
    
    def __init__(self, db_client=None):
        self.checklist_service = ChecklistService(db_client=db_client)
    
    async def process_checklist_analysis(self, analysis_run_id: str):
        """
        Main orchestrator for the 4-step checklist analysis pipeline.
        
        Steps:
        1. Generate queries from checklist (LLM)
        2. Retrieve relevant chunks (Vector Search)
        3. Analyze chunks against checklist (LLM)
        4. Structure the output (LLM)
        """
        try:
            # Get analysis run details
            analysis_run = await self.checklist_service.get_analysis_run_by_id(
                analysis_run_id
            )
            if not analysis_run:
                raise ValueError(f"Analysis run {analysis_run_id} not found")
            
            # Fetch language from indexing run
            language = await self.checklist_service.get_language_from_indexing_run(
                str(analysis_run.indexing_run_id)
            )
            
            # Update status to running
            await self.checklist_service.update_analysis_status(
                analysis_run_id, AnalysisStatus.RUNNING
            )
            await self.checklist_service.update_progress(analysis_run_id, 0, 4)
            
            # STEP 1: Generate queries from checklist
            logger.info(f"Step 1/4: Parsing checklist for analysis {analysis_run_id}")
            parsed_data = await generate_queries_from_checklist(
                analysis_run.checklist_content,
                language,
                analysis_run.model_name
            )
            
            await self.checklist_service.update_progress(analysis_run_id, 1, 4)
            
            # STEP 2: Retrieve chunks for all queries (optimized batch processing)
            logger.info(
                f"Step 2/4: Retrieving documents for {len(parsed_data['queries'])} queries using batch processing"
            )
            
            # Use batch retrieval for better performance (single embedding API call instead of N calls)
            unique_chunks = await retrieve_chunks_for_queries_batch(
                parsed_data["queries"], 
                str(analysis_run.indexing_run_id)
            )
            logger.info(f"Retrieved {len(unique_chunks)} unique chunks")
            
            await self.checklist_service.update_progress(analysis_run_id, 2, 4)
            
            # STEP 3: Analyze chunks against checklist
            logger.info(
                f"Step 3/4: Analyzing {len(unique_chunks)} chunks against checklist"
            )
            raw_analysis = await analyze_checklist_with_chunks(
                parsed_data["items"],
                unique_chunks,
                language,
                analysis_run.model_name
            )
            
            # Store raw output
            await self.checklist_service.update_analysis_raw_output(
                analysis_run_id, raw_analysis
            )
            await self.checklist_service.update_progress(analysis_run_id, 3, 4)
            
            # STEP 4: Structure the analysis output
            logger.info(f"Step 4/4: Structuring analysis results")
            structured_results = await structure_analysis_output(
                raw_analysis,
                parsed_data["items"],
                language,
                analysis_run.model_name
            )
            
            # Store structured results
            await self.checklist_service.store_checklist_results(
                analysis_run_id, structured_results
            )
            await self.checklist_service.update_progress(analysis_run_id, 4, 4)
            
            # Mark as completed
            await self.checklist_service.update_analysis_status(
                analysis_run_id, AnalysisStatus.COMPLETED
            )
            logger.info(f"Checklist analysis {analysis_run_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error in checklist analysis {analysis_run_id}: {e}")
            await self.checklist_service.update_analysis_status(
                analysis_run_id, AnalysisStatus.FAILED
            )
            await self.checklist_service.update_analysis_error(
                analysis_run_id, str(e)
            )