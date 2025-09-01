-- Complete Timing Analysis for Indexing Run
-- Corrected for actual database structure
-- Run this directly in Supabase SQL Editor

WITH document_timings AS (
    SELECT 
        d.filename,
        d.page_count,
        -- Extract timing for each step using actual step names
        (d.step_results->'PartitionStep'->>'duration_seconds')::float as partition_sec,
        (d.step_results->'MetadataStep'->>'duration_seconds')::float as metadata_sec,
        (d.step_results->'EnrichmentStep'->>'duration_seconds')::float as enrichment_sec,
        (d.step_results->'ChunkingStep'->>'duration_seconds')::float as chunking_sec,
        -- Calculate total per document (embedding is at run level)
        COALESCE((d.step_results->'PartitionStep'->>'duration_seconds')::float, 0) +
        COALESCE((d.step_results->'MetadataStep'->>'duration_seconds')::float, 0) +
        COALESCE((d.step_results->'EnrichmentStep'->>'duration_seconds')::float, 0) +
        COALESCE((d.step_results->'ChunkingStep'->>'duration_seconds')::float, 0) as total_sec
    FROM documents d
    INNER JOIN indexing_run_documents ird ON d.id = ird.document_id
    WHERE ird.indexing_run_id = 'ca079abb-b746-45fb-b448-0c4f5f185f8c'
),
step_totals AS (
    SELECT 
        COUNT(*) as doc_count,
        SUM(page_count) as total_pages,
        ROUND(SUM(partition_sec)::numeric, 1) as total_partition,
        ROUND(SUM(metadata_sec)::numeric, 1) as total_metadata,
        ROUND(SUM(enrichment_sec)::numeric, 1) as total_enrichment,
        ROUND(SUM(chunking_sec)::numeric, 1) as total_chunking,
        ROUND(SUM(total_sec)::numeric, 1) as doc_processing_total
    FROM document_timings
),
indexing_run_info AS (
    SELECT 
        status,
        started_at,
        completed_at,
        EXTRACT(EPOCH FROM (completed_at - started_at)) as run_duration_sec,
        (step_results->'embedding'->>'duration_seconds')::float as embedding_sec
    FROM indexing_runs
    WHERE id = 'ca079abb-b746-45fb-b448-0c4f5f185f8c'
),
wiki_info AS (
    SELECT 
        status as wiki_status,
        started_at as wiki_started,
        completed_at as wiki_completed,
        EXTRACT(EPOCH FROM (completed_at - started_at)) as wiki_duration_sec
    FROM wiki_generation_runs
    WHERE indexing_run_id = 'ca079abb-b746-45fb-b448-0c4f5f185f8c'
    LIMIT 1
),
combined_totals AS (
    SELECT 
        st.*,
        ROUND(iri.embedding_sec::numeric, 1) as total_embedding,
        ROUND((st.doc_processing_total + COALESCE(iri.embedding_sec, 0))::numeric, 1) as grand_total
    FROM step_totals st, indexing_run_info iri
),
top_docs AS (
    SELECT 
        SUBSTRING(filename, 1, 40) || ': ' || ROUND(total_sec::numeric, 1) || ' sec' as doc_info,
        total_sec
    FROM document_timings
    ORDER BY total_sec DESC
    LIMIT 5
)

-- MAIN QUERY OUTPUT
SELECT 
    '========== TIMING SUMMARY ==========' as report
UNION ALL
SELECT 
    'Indexing Run Duration: ' || ROUND(run_duration_sec::numeric, 1) || ' seconds (' || 
    ROUND((run_duration_sec/60)::numeric, 1) || ' minutes)'
FROM indexing_run_info
UNION ALL
SELECT 
    'Documents Processed: ' || doc_count || ' docs, ' || 
    COALESCE(total_pages::text, 'N/A') || ' pages'
FROM combined_totals
UNION ALL
SELECT ''
UNION ALL
SELECT '========== STEP BREAKDOWN ==========' 
UNION ALL
SELECT 
    'Partition:   ' || total_partition || ' sec (' || 
    ROUND((total_partition/NULLIF(grand_total, 0)*100)::numeric, 1) || '%)'
FROM combined_totals
UNION ALL
SELECT 
    'Metadata:    ' || total_metadata || ' sec (' || 
    ROUND((total_metadata/NULLIF(grand_total, 0)*100)::numeric, 1) || '%)'
FROM combined_totals
UNION ALL
SELECT 
    'Enrichment:  ' || total_enrichment || ' sec (' || 
    ROUND((total_enrichment/NULLIF(grand_total, 0)*100)::numeric, 1) || '%) ⚠️ BOTTLENECK'
FROM combined_totals
WHERE total_enrichment/NULLIF(grand_total, 0) > 0.3
UNION ALL
SELECT 
    'Enrichment:  ' || total_enrichment || ' sec (' || 
    ROUND((total_enrichment/NULLIF(grand_total, 0)*100)::numeric, 1) || '%)'
FROM combined_totals
WHERE COALESCE(total_enrichment/NULLIF(grand_total, 0), 0) <= 0.3
UNION ALL
SELECT 
    'Chunking:    ' || total_chunking || ' sec (' || 
    ROUND((total_chunking/NULLIF(grand_total, 0)*100)::numeric, 1) || '%)'
FROM combined_totals
UNION ALL
SELECT 
    'Embedding:   ' || total_embedding || ' sec (' || 
    ROUND((total_embedding/NULLIF(grand_total, 0)*100)::numeric, 1) || '%) [Run-level]'
FROM combined_totals
UNION ALL
SELECT 
    '-----------------------------------'
UNION ALL
SELECT 
    'TOTAL:       ' || grand_total || ' sec (' || 
    ROUND((grand_total/60)::numeric, 1) || ' minutes)'
FROM combined_totals
UNION ALL
SELECT ''
UNION ALL
SELECT '========== WIKI GENERATION =========='
UNION ALL
SELECT 
    'Wiki Duration: ' || ROUND(wiki_duration_sec::numeric, 1) || ' seconds (' || 
    ROUND((wiki_duration_sec/60)::numeric, 1) || ' minutes)'
FROM wiki_info
UNION ALL
SELECT ''
UNION ALL
SELECT '========== TOP 5 SLOWEST DOCS =========='
UNION ALL
SELECT doc_info FROM top_docs
ORDER BY 1;

-- Alternative: Detailed per-document view
/*
SELECT 
    SUBSTRING(filename, 1, 30) as document,
    COALESCE(page_count, 0) as pages,
    ROUND(partition_sec::numeric, 1) as partition,
    ROUND(metadata_sec::numeric, 1) as metadata,
    ROUND(enrichment_sec::numeric, 1) as enrichment,
    ROUND(chunking_sec::numeric, 1) as chunking,
    ROUND(total_sec::numeric, 1) as total
FROM document_timings
ORDER BY total_sec DESC;
*/