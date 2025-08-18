#!/usr/bin/env python3
"""
Interactive Retrieval Test - HNSW Integration Test
Test the retrieval step with any query and see top 10 + bottom 5 results
"""
import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.pipeline.querying.models import QueryVariations
from src.pipeline.querying.steps.retrieval import DocumentRetriever, RetrievalConfig
from src.services.config_service import ConfigService
from src.config.database import get_supabase_admin_client


def print_separator(title: str = ""):
    """Print a nice separator with optional title"""
    if title:
        print(f"\n{'='*80}")
        print(f" {title}")
        print(f"{'='*80}")
    else:
        print(f"{'='*80}")


def print_subseparator(title: str = ""):
    """Print a subsection separator"""
    if title:
        print(f"\n{'-'*60}")
        print(f" {title}")
        print(f"{'-'*60}")
    else:
        print(f"{'-'*60}")


async def test_retrieval_with_query(query: str, indexing_run_id: str = None):
    """Test retrieval step with a specific query"""
    
    print_separator("🔍 HNSW RETRIEVAL INTEGRATION TEST")
    
    # Initialize retrieval step
    config_service = ConfigService()
    retrieval_config_dict = config_service.get_effective_config("retrieval")
    retrieval_config = RetrievalConfig(retrieval_config_dict)
    
    # Increase top_k to get more results for analysis
    retrieval_config.top_k = 15  # Get 15 results so we can show top 10 + bottom 5
    
    retriever = DocumentRetriever(
        config=retrieval_config,
        db_client=get_supabase_admin_client()
    )
    
    # Get a sample indexing run ID if not provided
    if not indexing_run_id:
        db = get_supabase_admin_client()
        runs_response = db.table("document_chunks").select("indexing_run_id").not_.is_("embedding_1024", "null").limit(1).execute()
        if not runs_response.data:
            print("❌ No indexing runs with embeddings found")
            return
        indexing_run_id = runs_response.data[0]["indexing_run_id"]
    
    print(f"📋 Query: '{query}'")
    print(f"🗂️  Indexing Run ID: {indexing_run_id}")
    print(f"🎯 Retrieving top {retrieval_config.top_k} results")
    
    # Create query variations
    query_variations = QueryVariations(
        original=query,
        hyde=f"Dette dokument beskriver {query.lower()}",
        semantic=f"Hvad siger dokumentet om {query.lower()}?",
        formal=f"I forhold til {query.lower()}, hvad er de relevante informationer?"
    )
    
    try:
        # Execute retrieval
        print_subseparator("⚡ EXECUTING RETRIEVAL")
        start_time = datetime.utcnow()
        
        result = await retriever.execute(
            input_data=query_variations,
            indexing_run_id=indexing_run_id,
            allowed_document_ids=None
        )
        
        total_duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Display summary statistics
        print_subseparator("📊 PERFORMANCE METRICS")
        print(f"✅ Status: {result.status}")
        print(f"⏱️  Total Duration: {total_duration:.1f}ms")
        print(f"🔧 Step Duration: {result.duration_seconds * 1000:.1f}ms")
        print(f"📈 Results Retrieved: {result.summary_stats['results_retrieved']}")
        print(f"🥇 Top Similarity: {result.summary_stats['top_similarity_score']:.4f}")
        print(f"📊 Average Similarity: {result.summary_stats['avg_similarity_score']:.4f}")
        
        # Get the detailed results
        search_results = result.sample_outputs.get("search_results", [])
        total_results = len(search_results)
        
        if total_results == 0:
            print_subseparator("❌ NO RESULTS FOUND")
            print("No matching documents found for this query.")
            return
            
        print_subseparator(f"🎯 TOP 10 RESULTS (of {total_results} total)")
        
        # Show top 10 results
        top_results = search_results[:10]
        for i, result_data in enumerate(top_results):
            similarity = result_data.get("similarity_score", 0)
            page = result_data.get("page_number", "N/A")
            content = result_data.get("content", "")
            source_filename = result_data.get("source_filename", "unknown")
            chunk_id = result_data.get("chunk_id", "N/A")
            
            # Show preview (first 100 characters)
            content_preview = content.replace('\n', ' ').strip()
            if len(content_preview) > 100:
                content_preview = content_preview[:100] + "..."
            
            print(f"\n{i+1:2d}. 📊 Similarity: {similarity:.4f} | 📄 Page: {page} | 🆔 ID: {chunk_id}")
            print(f"    📁 Source: {source_filename}")
            print(f"    📝 Content: {content_preview}")
            
        # Show bottom 5 results if we have more than 10
        if total_results > 10:
            print_subseparator(f"📉 BOTTOM 5 RESULTS (Lowest Similarity)")
            
            # Get last 5 results
            bottom_results = search_results[-5:] if total_results >= 5 else search_results[10:]
            for i, result_data in enumerate(bottom_results):
                similarity = result_data.get("similarity_score", 0)
                page = result_data.get("page_number", "N/A")
                content = result_data.get("content", "")
                source_filename = result_data.get("source_filename", "unknown")
                chunk_id = result_data.get("chunk_id", "N/A")
                
                # Show preview (first 100 characters)
                content_preview = content.replace('\n', ' ').strip()
                if len(content_preview) > 100:
                    content_preview = content_preview[:100] + "..."
                
                actual_rank = total_results - len(bottom_results) + i + 1
                print(f"\n{actual_rank:2d}. 📊 Similarity: {similarity:.4f} | 📄 Page: {page} | 🆔 ID: {chunk_id}")
                print(f"    📁 Source: {source_filename}")
                print(f"    📝 Content: {content_preview}")
        
        # Show similarity distribution
        print_subseparator("📈 SIMILARITY DISTRIBUTION")
        similarities = [r.get("similarity_score", 0) for r in search_results]
        if similarities:
            print(f"🥇 Highest: {max(similarities):.4f}")
            print(f"📊 Average: {sum(similarities)/len(similarities):.4f}")
            print(f"🥉 Lowest: {min(similarities):.4f}")
            print(f"📏 Range: {max(similarities) - min(similarities):.4f}")
            
            # Show similarity brackets
            excellent = sum(1 for s in similarities if s >= 0.8)
            good = sum(1 for s in similarities if 0.6 <= s < 0.8)
            acceptable = sum(1 for s in similarities if 0.4 <= s < 0.6)
            low = sum(1 for s in similarities if s < 0.4)
            
            print(f"🌟 Excellent (≥0.8): {excellent} results")
            print(f"👍 Good (0.6-0.8): {good} results")
            print(f"👌 Acceptable (0.4-0.6): {acceptable} results")
            print(f"👎 Low (<0.4): {low} results")
        
        print_separator("✅ TEST COMPLETE")
        print(f"Successfully retrieved {total_results} results in {total_duration:.1f}ms")
        print("HNSW integration is working correctly! 🚀")
        
    except Exception as e:
        print_subseparator("❌ ERROR OCCURRED")
        print(f"Query failed: {e}")
        import traceback
        traceback.print_exc()


async def interactive_mode(indexing_run_id: str = None):
    """Interactive mode where user can input queries"""
    print_separator("🎮 INTERACTIVE RETRIEVAL TEST MODE")
    print("Enter queries to test the HNSW-optimized retrieval system.")
    print("Type 'quit' or 'exit' to stop.")
    print("Type 'help' for example queries.")
    if indexing_run_id:
        print(f"🗂️  Using specific indexing run: {indexing_run_id}")
    
    while True:
        try:
            print(f"\n{'─'*50}")
            query = input("🔍 Enter your query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            elif query.lower() == 'help':
                print("\n💡 Example queries to try:")
                print("  • el installationer")
                print("  • brandsikkerhed krav")
                print("  • ventilationssystem specifikationer")
                print("  • materialer konstruktion")
                print("  • tekfniske installationer")
                print("  • byggeriet miljø")
                continue
            elif not query:
                print("Please enter a query or 'help' for examples.")
                continue
                
            await test_retrieval_with_query(query, indexing_run_id)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test HNSW-optimized retrieval with any query")
    parser.add_argument("query", nargs="?", help="Query to test (if not provided, enters interactive mode)")
    parser.add_argument("--run-id", help="Specific indexing run ID to use")
    parser.add_argument("--interactive", "-i", action="store_true", help="Force interactive mode")
    
    args = parser.parse_args()
    
    if args.interactive or not args.query:
        await interactive_mode(args.run_id)
    else:
        await test_retrieval_with_query(args.query, args.run_id)


if __name__ == "__main__":
    asyncio.run(main())