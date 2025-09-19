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
            
            # Use @chain decorator approach for proper trace grouping
            from langchain_core.runnables import chain
            
            @chain
            async def checklist_analysis_chain(inputs):
                checklist_content = inputs["checklist_content"]
                language = inputs["language"] 
                model_name = inputs["model_name"]
                analysis_run_id = inputs["analysis_run_id"]
                indexing_run_id = inputs["indexing_run_id"]
                
                # STEP 1: Generate queries from checklist
                logger.info(f"Step 1/4: Parsing checklist for analysis {analysis_run_id}")
                parsed_data = await generate_queries_from_checklist(
                    checklist_content,
                    language,
                    model_name
                )
                
                await self.checklist_service.update_progress(analysis_run_id, 1, 4)
                
                # STEP 2: Retrieve chunks for all queries (optimized batch processing)
                logger.info(
                    f"Step 2/4: Retrieving documents for {len(parsed_data['queries'])} queries using batch processing"
                )
                
                # Use batch retrieval for better performance (single embedding API call instead of N calls)
                unique_chunks = await retrieve_chunks_for_queries_batch(
                    parsed_data["queries"], 
                    indexing_run_id
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
                    model_name
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
                    model_name
                )
                
                return {
                    "parsed_data": parsed_data,
                    "unique_chunks": unique_chunks, 
                    "raw_analysis": raw_analysis,
                    "structured_results": structured_results
                }
            
            # Execute the chain with metadata
            result = await checklist_analysis_chain.ainvoke(
                {
                    "checklist_content": analysis_run.checklist_content,
                    "language": language,
                    "model_name": analysis_run.model_name,
                    "analysis_run_id": analysis_run_id,
                    "indexing_run_id": str(analysis_run.indexing_run_id)
                },
                config={
                    "run_name": f"checklist_analysis_{analysis_run_id[:8]}",
                    "metadata": {
                        "analysis_run_id": analysis_run_id,
                        "indexing_run_id": str(analysis_run.indexing_run_id),
                        "checklist_id": analysis_run.checklist_id if hasattr(analysis_run, 'checklist_id') else None
                    },
                    "tags": [
                        "checklist_analysis",
                        analysis_run.model_name,
                        "production"
                    ]
                }
            )
            
            # Store structured results
            await self.checklist_service.store_checklist_results(
                analysis_run_id, result["structured_results"]
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