# Visual Source Attribution Feature

**Feature Overview**: Enable users to see exactly where on a PDF page their query results came from through visual highlighting.

**Status**: Planning Phase  
**Priority**: Future Enhancement  
**Estimated Effort**: Medium (2-3 weeks)

## User Experience Vision

When users ask a question and receive an AI response, they can see:
- The source PDF page displayed alongside the answer
- Highlighted regions showing exactly where the information came from
- General area highlighting (not pixel-perfect, but clearly indicating the source region)

## Technical Implementation Strategy

### Architecture Overview

```
Query → Retrieve Chunks (with bbox) → Generate Page Image → Display with Highlights
```

### Phase 1: Bbox Tracking Foundation ✅ **IMPLEMENT NOW**

#### 1.1 Fix Bbox Capture in Partition Step
**Root Cause Discovery**: Bbox data IS available from PyMuPDF but gets **lost in two places**:

1. **Not captured during element creation** (`partition.py:1299`)  
2. **Stripped by metadata cleaning** (`partition.py:1038`)

**Files to modify:**
- `backend/src/pipeline/indexing/steps/partition.py`

**Implementation (2-line fix):**
```python
# Line ~1300: Add bbox to text element metadata
metadata = {
    "page_number": page_index,
    "bbox": block_bbox,  # ← ADD THIS LINE
    "font_size": self._get_font_size(block),
    # ... rest unchanged
}

# Line ~1038: Preserve bbox in metadata cleaning
essential_fields = ["page_number", "filename", "image_path", "bbox"]  # ← ADD "bbox"
```

#### 1.2 Add Bbox Transformation Logic to Chunking Pipeline
**Files to modify:**
- `backend/src/pipeline/indexing/steps/chunking.py`

**Required bbox transformations:**

**1. Semantic Text Splitting (lines 495-570):**
When large elements are split, estimate bbox portions proportionally:
```python
# When splitting element into multiple chunks
def calculate_split_bbox(original_bbox, chunk_text, full_text, chunk_index, total_chunks):
    if not original_bbox or len(original_bbox) != 4:
        return None
    
    x0, y0, x1, y1 = original_bbox
    height = y1 - y0
    
    # Estimate vertical position based on character position
    chars_per_chunk = len(full_text) / total_chunks
    estimated_start_ratio = chunk_index / total_chunks
    estimated_height_ratio = len(chunk_text) / len(full_text)
    
    new_y0 = y0 + (height * estimated_start_ratio)
    new_y1 = new_y0 + (height * estimated_height_ratio)
    
    return [x0, new_y0, x1, new_y1]
```

**2. Merge Small Chunks (lines 572-622):**
When chunks are merged, create encompassing bbox:
```python
def merge_bboxes(bbox_list):
    valid_bboxes = [b for b in bbox_list if b and len(b) == 4]
    if not valid_bboxes:
        return None
    
    # Calculate bounding rectangle that encompasses all bboxes
    min_x0 = min(bbox[0] for bbox in valid_bboxes)
    min_y0 = min(bbox[1] for bbox in valid_bboxes)  
    max_x1 = max(bbox[2] for bbox in valid_bboxes)
    max_y1 = max(bbox[3] for bbox in valid_bboxes)
    
    return [min_x0, min_y0, max_x1, max_y1]
```

**3. List Grouping (lines 269-423):**
When narrative + list items are combined, merge their bboxes:
```python
# In group_list_items(), when creating combined_element
combined_bbox = merge_bboxes([
    list_items[0].get("metadata", {}).get("bbox"),  # Narrative bbox
    *[item.get("metadata", {}).get("bbox") for item in list_items[1:]]  # List item bboxes
])
```

#### 1.3 Final Chunk Metadata Preservation
**Files to modify:**
- `backend/src/pipeline/indexing/steps/chunking.py` (lines 692-716)

**Add bbox to final chunk metadata:**
```python
# In create_final_chunks(), preserve bbox in chunk metadata
chunk = {
    "chunk_id": str(uuid.uuid4()),
    "content": content,
    "metadata": {
        "source_filename": meta.get("source_filename"),
        "page_number": meta.get("page_number"),
        "bbox": meta.get("bbox"),  # ← ADD THIS LINE
        "element_category": meta.get("element_category", "unknown"),
        # ... rest unchanged
    },
}
```

**Bbox Storage Schema in Final Chunks:**
```json
{
  "metadata": {
    "page_number": 1,
    "bbox": [100, 200, 500, 350],  // [x0, y0, x1, y1]
    "bbox_confidence": "precise|estimated|merged",
    "bbox_source": "pymupdf|unstructured|calculated",
    "element_category": "NarrativeText",
    // ... other metadata
  }
}
```

**Cross-Page Chunks:** For chunks spanning multiple pages, store array of bboxes:
```json
{
  "metadata": {
    "bbox": null,  // Primary bbox is null for multi-page
    "bbox_multi_page": [
      {"page": 1, "bbox": [100, 200, 500, 600]},
      {"page": 2, "bbox": [100, 50, 500, 200]}
    ]
  }
}
```

#### 1.4 Database Schema Updates
**Table**: `document_chunks`
- **No schema changes needed** - bbox data stored in existing `metadata` JSONB column
- Backward compatible - existing chunks continue to work without bbox
- New chunks automatically include bbox data in metadata

### Phase 2: On-Demand Page Image Generation **IMPLEMENT LATER**

#### 2.1 Backend API Endpoint
**New endpoint**: `GET /api/documents/{doc_id}/pages/{page_num}/image`

**Features:**
- Generate page images on-demand from stored PDFs
- Support multiple DPI levels (150, 200, 300)
- Built-in caching with Redis/memory cache
- Optional bbox highlight overlays

**Implementation approach:**
```python
@router.get("/documents/{doc_id}/pages/{page_num}/image")
async def get_page_image(
    doc_id: str, 
    page_num: int,
    dpi: int = 200,
    format: str = "png"
):
    # 1. Check cache first
    cache_key = f"{doc_id}_page_{page_num}_{dpi}"
    if cached_image := cache.get(cache_key):
        return cached_image
    
    # 2. Retrieve PDF from storage
    pdf_bytes = await storage_service.download_pdf(doc_id)
    
    # 3. Generate page image using PyMuPDF
    doc = fitz.open("pdf", pdf_bytes)
    page = doc[page_num - 1]
    matrix = fitz.Matrix(dpi/72, dpi/72)
    pixmap = page.get_pixmap(matrix=matrix)
    
    # 4. Cache and return
    image_bytes = pixmap.tobytes()
    cache.set(cache_key, image_bytes, ttl=3600)  # 1 hour
    
    return StreamingResponse(io.BytesIO(image_bytes), media_type=f"image/{format}")
```

#### 2.2 Enhanced Search API Response
**Modify**: Query endpoints to include bbox metadata

**Example response:**
```json
{
  "chunks": [
    {
      "id": "chunk_123",
      "content": "Føringsvejene skal installeres i kælderen...",
      "similarity": 0.85,
      "document_id": "doc_456", 
      "page_number": 3,
      "bbox_data": {
        "primary": {
          "page": 3,
          "x0": 100, "y0": 200,
          "x1": 500, "y1": 350,
          "confidence": "precise"
        }
      }
    }
  ]
}
```

### Phase 3: Frontend Implementation **IMPLEMENT LATER**

#### 3.1 Visual Source Component
**New component**: `SourceAttributionViewer`

**Features:**
- Display page image alongside search results
- Overlay highlight rectangles based on bbox coordinates
- Support for multiple highlights per page
- Lazy loading of page images
- Zoom/pan functionality for detailed viewing

#### 3.2 UI Integration Points
- **Query results page**: Show source attribution for each result chunk
- **Chat interface**: Display relevant page sections during conversations  
- **Wiki pages**: Show source attribution for generated content

#### 3.3 Frontend Implementation Example
```javascript
const SourceAttributionViewer = ({ searchResult }) => {
  const { document_id, page_number, bbox_data } = searchResult;
  const pageImageUrl = `/api/documents/${document_id}/pages/${page_number}/image`;
  
  return (
    <div className="source-viewer">
      <div className="pdf-page-container">
        <img 
          src={pageImageUrl} 
          alt={`Page ${page_number}`}
          onLoad={() => setImageLoaded(true)}
        />
        {imageLoaded && bbox_data.primary && (
          <HighlightOverlay 
            bbox={bbox_data.primary}
            className="primary-highlight"
          />
        )}
        {bbox_data.additional?.map((bbox, idx) => (
          <HighlightOverlay 
            key={idx}
            bbox={bbox} 
            className="secondary-highlight"
          />
        ))}
      </div>
      <div className="chunk-content">
        {searchResult.content}
      </div>
    </div>
  );
};
```

## Performance Considerations

### Caching Strategy
- **Page image cache**: Redis/memory with 1-24 hour TTL
- **Cache keys**: `${doc_id}_page_${page_num}_${dpi}`
- **Cache warming**: Pre-generate images for frequently accessed pages
- **Cache invalidation**: When document is re-indexed

### Optimization Options
1. **Lazy loading**: Generate images only when user requests source view
2. **Multiple resolutions**: Thumbnail (150 DPI) + full quality (300 DPI)
3. **Background processing**: Pre-generate popular pages during off-peak hours
4. **CDN integration**: Cache generated images in CDN for global distribution

## Technical Benefits

### Accuracy Advantages
- **PyMuPDF precision**: Text-only pages have exact character-level positioning
- **Coordinate alignment**: Generated images match original bbox coordinates perfectly
- **High confidence**: Much more accurate than OCR-based positioning

### Scalability Benefits
- **On-demand generation**: No need to pre-extract all pages
- **Storage efficiency**: Only generate images when needed
- **Memory efficient**: Cache frequently accessed pages only

## Implementation Timeline

### Phase 1: Foundation (Week 1-2) ✅ **PRIORITY**
- [ ] **Fix partition step** - Add bbox capture and preserve in metadata cleaning (2-line fix)
- [ ] **Add bbox transformation logic** to chunking pipeline:
  - [ ] Semantic text splitting bbox estimation  
  - [ ] Chunk merging bbox union calculation
  - [ ] List grouping bbox combination
- [ ] **Preserve bbox in final chunks** - Add to chunk metadata  
- [ ] **Test bbox flow** through entire pipeline (partition → chunking → database)
- [ ] **Validate bbox accuracy** with sample documents

### Phase 2: Backend API (Week 2-3)
- [ ] Implement page image generation endpoint
- [ ] Add caching layer with Redis
- [ ] Update search API to include bbox metadata
- [ ] Performance testing and optimization

### Phase 3: Frontend Integration (Week 4-5)  
- [ ] Create SourceAttributionViewer component
- [ ] Integrate with query results pages
- [ ] Add lazy loading and performance optimizations
- [ ] User testing and UX refinements

## Success Metrics

### User Experience Metrics
- **Source attribution usage rate**: % of users who click to view source
- **User satisfaction**: Qualitative feedback on source visibility
- **Query confidence**: Users report higher confidence in AI answers

### Performance Metrics  
- **Page image generation time**: <500ms average
- **Cache hit rate**: >80% for frequently accessed pages
- **Memory usage**: Stable memory consumption with cache limits

## Future Enhancements

### Advanced Features (Future)
- **Multi-chunk highlighting**: Show multiple related chunks on same page
- **Smart cropping**: Focus on relevant page regions instead of full page
- **Annotation tools**: Allow users to add notes to highlighted regions
- **Export functionality**: Save highlighted pages as images/PDFs

### Integration Opportunities
- **Wiki generation**: Show source attribution for auto-generated wiki content
- **Quality assurance**: Visual verification of chunk extraction accuracy
- **User feedback**: Allow users to correct/improve bbox positioning

## Dependencies

### Technical Dependencies
- **PyMuPDF**: Already available for PDF processing
- **Redis**: For caching (already in infrastructure)
- **Frontend framework**: React components for highlighting

### Infrastructure Dependencies  
- **Storage access**: Ability to retrieve original PDFs
- **Memory allocation**: Additional RAM for image generation and caching
- **CDN setup**: Optional but recommended for global performance

## Risk Mitigation

### Performance Risks
- **Memory usage**: Implement cache size limits and LRU eviction
- **Generation time**: Pre-generate popular pages, lazy load others
- **Storage growth**: Monitor cache size and implement cleanup policies

### Accuracy Risks
- **Coordinate drift**: Regular testing to ensure bbox accuracy
- **Cross-page chunks**: Clear UX for chunks spanning multiple pages
- **Edge cases**: Robust error handling for malformed PDFs

---

## Implementation Summary

### Key Discovery: Bbox Data Loss Root Cause
Through code analysis, we found bbox coordinates ARE available from PyMuPDF but get **lost in the partition step**:

1. **Available but not captured**: `block.get("bbox")` contains coordinates but isn't added to element metadata
2. **Stripped by cleaning**: `_clean_metadata()` only preserves 3 fields, dropping any bbox data

### Why Bbox Transformation Logic is Essential  
The chunking pipeline performs extensive element manipulation that requires bbox coordinate transformation:

- **Semantic Text Splitting**: Large elements (>2000 chars) split into multiple chunks need proportional bbox estimation  
- **Small Chunk Merging**: Adjacent small chunks (<100 chars) merged together need encompassing bbox calculation
- **List Grouping**: Narrative + list items combined need bbox union calculation

**Without transformation logic**, merged/split chunks would have incorrect or missing location data, making visual attribution inaccurate or impossible.

### Implementation Complexity
- **Partition fix**: Simple (2-line change)  
- **Chunking transformations**: Moderate complexity (bbox geometry calculations)
- **Testing & validation**: Critical to ensure accuracy across document types

**Next Steps**: Begin Phase 1 implementation starting with the 2-line partition fix, then add bbox transformation logic to handle chunking pipeline operations. This foundational work enables all future visual attribution features.