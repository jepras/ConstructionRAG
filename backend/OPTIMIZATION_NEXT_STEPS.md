# Next Optimization Steps

## 1. Page-Level Parallelization (High Impact)

Split large PDFs into page ranges and process in parallel:

```python
# In orchestrator.py
async def process_document_pages_parallel(doc_input, pages_per_chunk=10):
    total_pages = get_page_count(doc_input.file_path)
    page_chunks = [(i, min(i+pages_per_chunk, total_pages)) 
                   for i in range(0, total_pages, pages_per_chunk)]
    
    # Process page chunks in parallel
    tasks = [process_page_range(doc_input, start, end) 
             for start, end in page_chunks]
    results = await asyncio.gather(*tasks)
    return merge_results(results)
```

**Expected improvement**: 5-10x faster for documents > 50 pages

## 2. VLM Batching for Images/Tables

Batch multiple images/tables in single API calls:

```python
# In enrichment.py
async def _enrich_with_vlm_async(self, metadata_output):
    # Collect all images and tables
    images_batch = []
    tables_batch = []
    
    # Batch process instead of one-by-one
    for batch in chunks(images_to_process, batch_size=5):
        caption_tasks = [self.caption_image_async(img) for img in batch]
        results = await asyncio.gather(*caption_tasks)
    
    # Similar for tables
```

**Benefits**:
- Reduce API calls by 5x
- Better rate limit management
- Lower costs (some providers offer batch discounts)

## 3. Implementation Priority

1. **Immediate**: VLM batching (easy, high impact)
2. **Next Sprint**: Page-level parallelization (complex, very high impact for large docs)
3. **Consider**: Beam's `.map()` for document-level distribution across containers

## Cost/Performance Tradeoff

| Optimization | Complexity | Speed Gain | Cost Impact |
|-------------|------------|------------|-------------|
| VLM Batching | Low | 2-3x | -20% (fewer API calls) |
| Page Parallel | High | 5-10x | +50% (more containers) |
| Combined | High | 10-20x | +30% (net) |